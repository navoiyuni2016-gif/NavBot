"""Outbound-only Telegram worker. No token or message contents are logged."""
import argparse
from contextlib import closing
import fcntl
import json
from http.client import HTTPException
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib import request, error
from uuid import uuid4
import integrations
import owner_control
import telegram_bot as bot
import workflow as w


class TelegramError(Exception):
    def __init__(self, code, retry_after=0, uncertain=False):
        self.code=str(code);self.retry_after=retry_after;self.uncertain=uncertain
        super().__init__(self.code)


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


class API:
    def __init__(self,token):
        if not re.fullmatch(r'[0-9]{5,20}:[A-Za-z0-9_-]{20,150}',token):raise TelegramError('invalid_token')
        self._base='https://api.telegram.org/bot'+token+'/'
        self._opener=request.build_opener(NoRedirect())

    def call(self,method,data=None,file=None):
        if method not in ('getMe','getUpdates','sendMessage','sendDocument','answerCallbackQuery','setChatMenuButton'):raise TelegramError('invalid_method')
        data=data or {}
        if file:
            boundary=uuid4().hex;body=bytearray()
            for key,value in data.items():
                body.extend(('--'+boundary+'\r\nContent-Disposition: form-data; name="'+key+'"\r\n\r\n'+str(value)+'\r\n').encode())
            # ASCII filename in transport, original Unicode name retained in caption.
            suffix=Path(file['name']).suffix
            body.extend(('--'+boundary+'\r\nContent-Disposition: form-data; name="document"; filename="NAVBOT'+suffix+'"\r\nContent-Type: '+file['mime']+'\r\n\r\n').encode())
            body.extend(file['body']);body.extend(('\r\n--'+boundary+'--\r\n').encode())
            mime='multipart/form-data; boundary='+boundary
        else:body=json.dumps(data).encode();mime='application/json'
        outgoing=method in ('sendMessage','sendDocument')
        try:
            req=request.Request(self._base+method,data=bytes(body),headers={'Content-Type':mime})
            try:response=self._opener.open(req,timeout=25)
            except error.HTTPError as failure:response=failure
            with response:
                raw=response.read(2*1024*1024+1)
                if len(raw)>2*1024*1024:raise TelegramError('oversized_response',uncertain=outgoing)
                try:result=json.loads(raw)
                except (ValueError,UnicodeError):raise TelegramError('invalid_response',uncertain=outgoing)
                if not isinstance(result,dict):raise TelegramError('invalid_response',uncertain=outgoing)
                if response.status!=200 or result.get('ok') is not True:
                    code=result.get('error_code',response.status)
                    delay=result.get('parameters',{}).get('retry_after',0)
                    delay=min(max(delay,1),86400) if type(delay) is int and code==429 else 0
                    raise TelegramError(code,delay,outgoing and (type(code) is not int or code>=500))
                value=result.get('result')
                if outgoing and (not isinstance(value,dict) or type(value.get('message_id')) is not int):raise TelegramError('invalid_response',uncertain=True)
                return value
        except TelegramError:raise
        except (OSError,error.URLError,ValueError,HTTPException):raise TelegramError('network',uncertain=outgoing) from None


def configured(db):
    try:
        row,token=integrations._check_ready(db,'telegram')
        return row['token_ref'],token
    except (integrations.IntegrationError,OSError):return None


def valid_job(db,job):
    if job['student_id']:
        link=db.execute("SELECT l.* FROM telegram_links l JOIN students s ON s.hemis_id=l.student_id WHERE l.student_id=? AND l.chat_id=? AND l.link_id=? AND s.status='active'",(job['student_id'],job['chat_id'],job['link_id'])).fetchone()
        if not link:return False
    if job['request_id']:
        row=db.execute('SELECT * FROM requests WHERE id=? AND deleted_at IS NULL',(job['request_id'],)).fetchone()
        if not row or row['student_id']!=job['student_id']:return False
        if job['batch_key'].startswith('release:') or job['kind']=='document' or json.loads(job['payload']).get('approved_answer'):
            release=db.execute('SELECT * FROM telegram_releases WHERE request_id=?',(job['request_id'],)).fetchone()
            if not release or not bot._release_valid(db,release):return False
            if job['kind']=='document' and json.loads(job['payload']).get('attachment_id') not in json.loads(release['attachment_ids']):return False
    return True


def recover(db):
    db.execute("UPDATE telegram_outbox SET state='uncertain',error='worker_interrupted',lease_until=0 WHERE state='sending' AND lease_until<?",(int(time.time()),))
    # Retain delivery metadata; discard private message bodies after a week.
    db.execute("UPDATE telegram_outbox SET payload='{}' WHERE state IN ('sent','cancelled') AND julianday(created_at)<julianday('now','-7 days')")
    db.execute('DELETE FROM telegram_codes WHERE expires_at<?',(int(time.time())-86400,))


def deliver_one(db,api,expected_config=None):
    if owner_control.suspended(db):return False
    now=int(time.time())
    if now<int(bot.runtime(db,'send_after','0')):return False
    db.execute('BEGIN IMMEDIATE')
    try:
        recover(db)
        job=db.execute("SELECT j.* FROM telegram_outbox j WHERE j.state='pending' AND j.next_attempt<=? AND NOT EXISTS (SELECT 1 FROM telegram_outbox p WHERE p.batch_key=j.batch_key AND p.part<j.part AND p.state!='sent') ORDER BY CASE WHEN j.kind='callback' THEN 0 ELSE 1 END,j.id LIMIT 1",(now,)).fetchone()
        if not job:db.commit();return False
        if not valid_job(db,job):
            db.execute("UPDATE telegram_outbox SET state='cancelled',payload='{}',error='access_changed' WHERE batch_key=? AND state IN ('pending','sending')",(job['batch_key'],));db.commit();return True
        db.execute("UPDATE telegram_outbox SET state='sending',attempts=attempts+1,lease_until=? WHERE id=?",(now+90,job['id']))
        db.commit()
    except BaseException:db.rollback();raise
    if expected_config is not None and configured(db)!=expected_config:
        with db:db.execute("UPDATE telegram_outbox SET state='pending',lease_until=0 WHERE id=?",(job['id'],))
        return False
    # Revalidate immediately before I/O. Network never holds a SQLite write lock.
    if not valid_job(db,job):
        with db:db.execute("UPDATE telegram_outbox SET state='cancelled',payload='{}',error='access_changed' WHERE batch_key=? AND state IN ('pending','sending')",(job['batch_key'],))
        return True
    payload=json.loads(job['payload']);payload.pop('approved_answer',None)
    try:
        file=None
        if job['kind']=='document':
            row=db.execute('SELECT * FROM attachments WHERE id=? AND request_id=?',(payload['attachment_id'],job['request_id'])).fetchone()
            if not row:raise TelegramError('attachment_missing')
            file=dict(row);file['body']=bytes(row['body']);payload={'chat_id':job['chat_id'],'caption':row['name']}
            method='sendDocument'
        elif job['kind']=='callback':method='answerCallbackQuery'
        else:method='sendMessage';payload['chat_id']=job['chat_id'];payload['link_preview_options']={'is_disabled':True}
        result=api.call(method,payload,file=file)
        with db:
            db.execute("UPDATE telegram_outbox SET state='sent',telegram_message_id=?,sent_at=?,lease_until=0,error='' WHERE id=? AND state='sending'",(result.get('message_id') if isinstance(result,dict) else None,w.now(),job['id']))
            bot.set_runtime(db,'last_send',w.now())
            if job['request_id']:bot.background_audit(db,'telegram_sent',{'request_id':job['request_id'],'kind':job['kind'],'outbox_id':job['id']})
        return True
    except TelegramError as failure:
        state='pending' if failure.retry_after else 'uncertain' if failure.uncertain else 'failed'
        with db:
            db.execute('UPDATE telegram_outbox SET state=?,error=?,next_attempt=?,lease_until=0 WHERE id=? AND state=\'sending\'',(state,failure.code,now+failure.retry_after,job['id']))
            if job['request_id']:bot.background_audit(db,'telegram_delivery_error',{'request_id':job['request_id'],'state':state,'code':failure.code,'outbox_id':job['id']})
            if failure.retry_after:bot.set_runtime(db,'send_after',now+failure.retry_after)
        return True


def sync_menu(db,api):
    """Sync the default private-chat menu; retry failures without blocking chat."""
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='telegram_mini_config'").fetchone()
    row=db.execute('SELECT url FROM telegram_mini_config WHERE id=1').fetchone() if exists else None
    url=row['url'] if row else ''
    if getattr(api,'_menu_url',None)==url or time.time()<getattr(api,'_menu_retry',0):return
    menu={'type':'web_app','text':'NAVBOT','web_app':{'url':url}} if url else {'type':'default'}
    try:
        if api.call('setChatMenuButton',{'menu_button':menu}) is not True:raise TelegramError('invalid_menu_response')
        api._menu_url=url
        with db:bot.set_runtime(db,'menu_error','')
    except TelegramError as failure:
        api._menu_retry=time.time()+max(60,failure.retry_after)
        with db:bot.set_runtime(db,'menu_error',failure.code)


def poll(db,api,expected_config=None):
    if owner_control.suspended(db):return
    offset=int(bot.runtime(db,'last_update_id','-1'))+1
    updates=api.call('getUpdates',{'offset':offset,'timeout':15,'limit':50,'allowed_updates':['message','callback_query']})
    if not isinstance(updates,list):raise TelegramError('invalid_updates')
    for update in updates:
        if owner_control.suspended(db):return
        with db:bot.process_update(db,update)
    with db:
        bot.set_runtime(db,'last_poll',w.now());bot.set_runtime(db,'worker_error','')
        # A successful authenticated poll is a real connection check. Match the
        # token reference so a response from a replaced bot cannot mark it ready.
        if expected_config is not None:
            stamp=w.now()
            db.execute("UPDATE integration_config SET connected=1,last_checked=?,last_success=?,last_error='',bot_username=? WHERE kind='telegram' AND enabled=1 AND token_ref=?",(stamp,stamp,bot.runtime(db,'bot_username'),expected_config[0]))
        bot.schedule_releases(db)


def identity(db,api):
    me=api.call('getMe')
    if not isinstance(me,dict) or type(me.get('id')) is not int or not me.get('is_bot'):raise TelegramError('invalid_bot')
    previous=bot.runtime(db,'bot_id')
    if previous and previous!=str(me['id']):raise TelegramError('bot_identity_changed')
    with db:
        bot.set_runtime(db,'bot_id',me['id'])
        bot.set_runtime(db,'bot_username',str(me.get('username',''))[:100])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--db',required=True,type=Path);args=parser.parse_args()
    os.umask(0o077)
    if not args.db.is_file():parser.error('Initialize NAVBOT database first')
    with args.db.with_suffix('.telegram.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with closing(sqlite3.connect(args.db.resolve().as_uri()+'?mode=rw',uri=True,timeout=15)) as db:
            db.row_factory=sqlite3.Row
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='telegram_outbox'").fetchone():parser.error('Update and start NAVBOT first')
            previous=None;api=None
            while True:
                if owner_control.suspended(db):
                    time.sleep(5);continue
                config=configured(db)
                if not config:
                    with db:bot.set_runtime(db,'worker_error','not_configured')
                    previous=None;time.sleep(5);continue
                try:
                    if config!=previous:
                        api=API(config[1]);identity(db,api);previous=config
                    sync_menu(db,api)
                    for _ in range(10):
                        if not deliver_one(db,api,config):break
                    poll(db,api,config)
                except TelegramError as failure:
                    with db:bot.set_runtime(db,'worker_error',failure.code)
                    time.sleep(max(3,min(failure.retry_after,30)))
                except sqlite3.Error:
                    db.rollback();time.sleep(3)


if __name__=='__main__':main()
