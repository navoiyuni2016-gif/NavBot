"""Private student bot state machine and transactional approved-answer outbox.

No network calls occur here. Staff verify identity before issuing an expiring code.
Only an explicit head/admin approval creates a releasable answer.
"""
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from pathlib import Path
import workflow as w
from telegram_text import LANGS, t, main_keyboard, languages, uz, labels, card, status_icon

DEFAULT_CATALOG=json.loads(Path(__file__).with_name('catalog.json').read_text(encoding='utf-8'))
CODE_TTL=600
CODE_ALPHABET='23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def initialize(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS telegram_links(student_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL UNIQUE,link_id TEXT NOT NULL UNIQUE,verified_by INTEGER NOT NULL,linked_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS telegram_codes(student_id TEXT PRIMARY KEY,salt TEXT NOT NULL,code_hash TEXT NOT NULL,expires_at INTEGER NOT NULL,issued_by INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS telegram_chats(chat_id INTEGER PRIMARY KEY,state TEXT NOT NULL DEFAULT 'id',pending_sid TEXT,lang TEXT NOT NULL DEFAULT 'uz',window_start INTEGER NOT NULL DEFAULT 0,events INTEGER NOT NULL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS telegram_failures(identity TEXT PRIMARY KEY,failures INTEGER NOT NULL,window_start INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS telegram_runtime(key TEXT PRIMARY KEY,value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS telegram_releases(request_id INTEGER PRIMARY KEY,student_id TEXT NOT NULL,answer TEXT NOT NULL,result TEXT NOT NULL,attachment_ids TEXT NOT NULL,approved_by INTEGER NOT NULL,approved_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS telegram_outbox(id INTEGER PRIMARY KEY,batch_key TEXT NOT NULL,part INTEGER NOT NULL,chat_id INTEGER NOT NULL,student_id TEXT,link_id TEXT,request_id INTEGER,kind TEXT NOT NULL,payload TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,next_attempt INTEGER NOT NULL DEFAULT 0,lease_until INTEGER NOT NULL DEFAULT 0,telegram_message_id INTEGER,error TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,sent_at TEXT,UNIQUE(batch_key,part));
      CREATE INDEX IF NOT EXISTS telegram_jobs_pending ON telegram_outbox(state,next_attempt,id);
      CREATE INDEX IF NOT EXISTS telegram_jobs_request ON telegram_outbox(request_id);
    ''')


def _keyboard(db,lang):
    return main_keyboard(lang)


def _launch_button(db,chat_id,batch,student=None):
    # Inline Web App launches provide signed initData. Keyboard-button launches
    # may omit it, so do not use ReplyKeyboardButton.web_app for authentication.
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='telegram_mini_config'").fetchone()
    row=db.execute('SELECT url FROM telegram_mini_config WHERE id=1').fetchone() if exists else None
    if not row or not row['url']:return
    chat=db.execute('SELECT lang FROM telegram_chats WHERE chat_id=?',(chat_id,)).fetchone()
    lang=chat['lang'] if chat else 'uz'
    label=t('app_open',lang)
    _job(db,chat_id,'message',{'text':card('NAVBOT · '+t('portal',lang),t('app_note',lang)),'reply_markup':{'inline_keyboard':[[{'text':label,'web_app':{'url':row['url']}}]]}},batch,student)


def background_audit(db,action,detail):
    import security_monitor
    actor={'id':None,'username':'telegram-bot','full_name':'NAVBOT Telegram','role':'bot'}
    security_monitor.write(db,{'method':'BOT','path':'/telegram'},actor,action,detail,'telegram')


def runtime(db,key,default=''):
    row=db.execute('SELECT value FROM telegram_runtime WHERE key=?',(key,)).fetchone()
    return row['value'] if row else default


def set_runtime(db,key,value):
    db.execute('INSERT INTO telegram_runtime VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))


def _code_hash(code,salt):
    return hashlib.pbkdf2_hmac('sha256',code.encode(),bytes.fromhex(salt),100000).hex()


def issue_code(db,user,data):
    w.need(user,('admin','manager'))
    sid=w.validate_id(data.get('hemis_id'))
    student=w.student(db,sid)
    if not student or student.get('status')!='active':
        raise w.Problem('Faol talaba topilmadi',404)
    if data.get('identity_confirmed') is not True:
        raise w.Problem('Avval talaba shaxsini tekshiring')
    if db.execute('SELECT 1 FROM telegram_links WHERE student_id=?',(sid,)).fetchone():
        raise w.Problem('Talaba Telegramga bog‘langan. Qayta bog‘lash uchun superadminga murojaat qiling',409)
    code=''.join(secrets.choice(CODE_ALPHABET) for _ in range(8));salt=secrets.token_hex(16)
    expires=int(time.time())+CODE_TTL
    db.execute('INSERT INTO telegram_codes VALUES (?,?,?,?,?,0) ON CONFLICT(student_id) DO UPDATE SET salt=excluded.salt,code_hash=excluded.code_hash,expires_at=excluded.expires_at,issued_by=excluded.issued_by,attempts=0',(sid,salt,_code_hash(code,salt),expires,user['id']))
    w.audit(db,user,'telegram_code_issued',{'student_id':sid,'expires_at':expires})
    return {'code':code,'expires_at':expires,'hemis_id':sid}


def unlink(db,user,data):
    w.need(user,('admin',));sid=w.validate_id(data.get('hemis_id'));reason=w.text(data,'reason',500,True)
    db.execute('DELETE FROM telegram_links WHERE student_id=?',(sid,))
    db.execute('DELETE FROM telegram_codes WHERE student_id=?',(sid,))
    db.execute("UPDATE telegram_outbox SET state='cancelled',payload='{}',error='unlinked' WHERE student_id=?",(sid,))
    w.audit(db,user,'telegram_unlinked',{'student_id':sid,'reason':reason})
    return {'ok':True}


def forget_student(db,sid):
    db.execute('DELETE FROM telegram_links WHERE student_id=?',(sid,))
    db.execute('DELETE FROM telegram_codes WHERE student_id=?',(sid,))
    db.execute("UPDATE telegram_outbox SET state='cancelled',payload='{}',error='student_removed' WHERE student_id=?",(sid,))
    db.execute('DELETE FROM telegram_releases WHERE student_id=?',(sid,))


def forget_request(db,request_id):
    row=db.execute('SELECT student_id FROM requests WHERE id=?',(request_id,)).fetchone()
    if row and row['student_id']:
        db.execute("UPDATE telegram_outbox SET state='cancelled',payload='{}',error='request_removed' WHERE student_id=? AND request_id IS NULL AND kind='message'",(row['student_id'],))
    db.execute("UPDATE telegram_outbox SET state='cancelled',payload='{}',error='request_removed' WHERE request_id=?",(request_id,))
    db.execute('DELETE FROM telegram_releases WHERE request_id=?',(request_id,))


def status(db,sid):
    linked=db.execute('SELECT linked_at FROM telegram_links WHERE student_id=?',(sid,)).fetchone()
    code=db.execute('SELECT expires_at FROM telegram_codes WHERE student_id=?',(sid,)).fetchone()
    return {'linked':bool(linked),'linked_at':linked['linked_at'] if linked else None,'code_expires_at':code['expires_at'] if code and code['expires_at']>time.time() else None}


def delivery(db,request_id):
    released=db.execute('SELECT 1 FROM telegram_releases WHERE request_id=?',(request_id,)).fetchone()
    if not released:return {'approved':False,'state':'not_approved'}
    jobs=db.execute("SELECT state,COUNT(*) total FROM telegram_outbox WHERE request_id=? AND batch_key LIKE 'release:%' GROUP BY state",(request_id,)).fetchall()
    counts={r['state']:r['total'] for r in jobs}
    state='awaiting_link' if not counts else 'uncertain' if counts.get('uncertain') else 'failed' if counts.get('failed') else 'pending' if counts.get('pending') or counts.get('sending') else 'sent' if counts.get('sent') else 'cancelled'
    return {'approved':True,'state':state,'counts':counts}


def approve(db,user,row,data):
    w.need(user,('head','admin'))
    sid=row['student_id'];selected=data.get('telegram_attachment_ids',[])
    if not isinstance(selected,list) or len(selected)>10 or not all(isinstance(x,str) for x in selected) or len(set(selected))!=len(selected):
        raise w.Problem('Talabaga yuboriladigan fayllarni tekshiring')
    for file_id in selected:
        if not db.execute('SELECT 1 FROM attachments WHERE id=? AND request_id=?',(file_id,row['id'])).fetchone():
            raise w.Problem('Tanlangan fayl bu murojaatga tegishli emas')
    if not sid:raise w.Problem('Avval talabani biriktiring')
    db.execute('INSERT INTO telegram_releases VALUES (?,?,?,?,?,?,?)',(row['id'],sid,row['answer'],row['result'],json.dumps(selected),user['id'],w.now()))
    w.audit(db,user,'telegram_answer_approved',{'request_id':row['id'],'student_id':sid,'files':len(selected)})
    schedule_releases(db,request_id=row['id'])


def chunks(text,limit=3500):
    part=[];length=0
    for char in text:
        size=2 if ord(char)>0xffff else 1
        if length+size>limit:
            yield ''.join(part);part=[];length=0
        part.append(char);length+=size
    if part:yield ''.join(part)


def _job(db,chat_id,kind,payload,batch,student=None,request_id=None):
    if batch.startswith(('update:','ack:')) and db.execute("SELECT COUNT(*) FROM telegram_outbox WHERE chat_id=? AND state IN ('pending','sending') AND batch_key NOT LIKE 'release:%'",(chat_id,)).fetchone()[0]>=60:return
    part=db.execute('SELECT COUNT(*) FROM telegram_outbox WHERE batch_key=?',(batch,)).fetchone()[0]
    db.execute('INSERT INTO telegram_outbox(batch_key,part,chat_id,student_id,link_id,request_id,kind,payload,created_at) VALUES (?,?,?,?,?,?,?,?,?)',(batch,part,chat_id,student['student_id'] if student else None,student['link_id'] if student else None,request_id,kind,json.dumps(payload,ensure_ascii=False),w.now()))


def _message(db,chat_id,text,keyboard,batch,student=None,request_id=None,approved=False):
    pieces=list(chunks(text))
    for index,piece in enumerate(pieces):
        payload={'text':piece}
        if approved:payload['approved_answer']=True
        if keyboard and index==len(pieces)-1:payload['reply_markup']=keyboard
        _job(db,chat_id,'message',payload,batch,student,request_id)
    if keyboard and 'keyboard' in keyboard:_launch_button(db,chat_id,batch,student)


def _release_valid(db,release):
    row=db.execute('SELECT * FROM requests WHERE id=? AND deleted_at IS NULL',(release['request_id'],)).fetchone()
    return bool(row and row['status']=='closed' and row['student_id']==release['student_id'] and row['answer']==release['answer'] and row['result']==release['result'])


def _release_messages(db,link,release,batch,lang):
    if not _release_valid(db,release):return
    text=card('✅ NAV-'+str(release['request_id']).zfill(4)+' · '+t('approved',lang),release['answer'])
    if release['result'] and release['result']!=release['answer']:text+='\n\n'+release['result']
    keyboard={'inline_keyboard':[[{'text':t('details',lang),'callback_data':'req:'+str(release['request_id'])},{'text':t('requests',lang),'callback_data':'list:1'}]]}
    _message(db,link['chat_id'],text,keyboard,batch,link,release['request_id'],approved=True)
    for file_id in json.loads(release['attachment_ids']):
        if db.execute('SELECT 1 FROM attachments WHERE id=? AND request_id=?',(file_id,release['request_id'])).fetchone():
            _job(db,link['chat_id'],'document',{'attachment_id':file_id},batch,link,release['request_id'])


def schedule_releases(db,request_id=None):
    query="SELECT r.*,l.chat_id,l.link_id,c.lang FROM telegram_releases r JOIN telegram_links l ON l.student_id=r.student_id JOIN students s ON s.hemis_id=r.student_id LEFT JOIN telegram_chats c ON c.chat_id=l.chat_id WHERE s.status='active'"
    args=()
    if request_id is not None:query+=' AND r.request_id=?';args=(request_id,)
    for row in db.execute(query,args).fetchall():
        batch='release:'+str(row['request_id'])+':'+row['link_id']
        if db.execute('SELECT 1 FROM telegram_outbox WHERE batch_key=?',(batch,)).fetchone():continue
        _release_messages(db,row,row,batch,row['lang'] or 'uz')


def _failed(db,chat_id,sid):
    now=int(time.time())
    for identity in ('chat:'+str(chat_id),'student:'+sid):
        db.execute('INSERT INTO telegram_failures VALUES (?,1,?) ON CONFLICT(identity) DO UPDATE SET failures=CASE WHEN window_start<? THEN 1 ELSE failures+1 END,window_start=CASE WHEN window_start<? THEN excluded.window_start ELSE window_start END',(identity,now,now-900,now-900))
    db.execute('DELETE FROM telegram_failures WHERE window_start<?',(now-86400,))
    background_audit(db,'telegram_link_failed',{'chat_ref':hashlib.sha256(str(chat_id).encode()).hexdigest()[:12]})


def _verify(db,chat_id,sid,code):
    now=int(time.time())
    for identity in ('chat:'+str(chat_id),'student:'+sid):
        row=db.execute('SELECT failures,window_start FROM telegram_failures WHERE identity=?',(identity,)).fetchone()
        if row and row['failures']>=5 and row['window_start']>now-900:return 'locked'
    row=db.execute('SELECT * FROM telegram_codes WHERE student_id=?',(sid,)).fetchone()
    value=_code_hash(code.strip().upper(),row['salt'] if row else '00'*16)
    good=row is not None and hmac.compare_digest(value,row['code_hash']) and row['expires_at']>now and row['attempts']<5
    student=db.execute("SELECT 1 FROM students WHERE hemis_id=? AND status='active'",(sid,)).fetchone()
    conflict=db.execute('SELECT 1 FROM telegram_links WHERE student_id=? OR chat_id=?',(sid,chat_id)).fetchone()
    if not good or not student or conflict:
        _failed(db,chat_id,sid)
        db.execute('UPDATE telegram_codes SET attempts=attempts+1 WHERE student_id=?',(sid,))
        return 'bad_code'
    db.execute('INSERT INTO telegram_links VALUES (?,?,?,?,?)',(sid,chat_id,uuid4().hex,row['issued_by'],w.now()))
    db.execute('DELETE FROM telegram_codes WHERE student_id=?',(sid,))
    db.execute('DELETE FROM telegram_failures WHERE identity IN (?,?)',('chat:'+str(chat_id),'student:'+sid))
    background_audit(db,'telegram_linked',{'student_id':sid,'verified_by':row['issued_by']})
    return 'linked'


def _date(value):
    if not value:return '—'
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone(timedelta(hours=5))).strftime('%d.%m.%Y %H:%M')
    except ValueError:return '—'


def _service(db,row,lang):
    settings=db.execute('SELECT value FROM settings WHERE id=1').fetchone()
    catalog=json.loads(settings['value']).get('catalog',DEFAULT_CATALOG) if settings else DEFAULT_CATALOG
    try:
        name=catalog[row['section']][1][row['service']][LANGS.index(lang)]
        return uz(name) if lang=='uz' else name
    except (KeyError,IndexError,TypeError):return (row['content'] or '')[:160]


def _request(db,link,request_id):
    return db.execute('SELECT * FROM requests WHERE id=? AND student_id=? AND deleted_at IS NULL',(request_id,link['student_id'])).fetchone()


def _list(db,link,page,lang,batch,tracking=False):
    total=db.execute('SELECT COUNT(*) FROM requests WHERE student_id=? AND deleted_at IS NULL',(link['student_id'],)).fetchone()[0]
    page=min(max(1,page),max(1,(total+4)//5))
    rows=db.execute('SELECT * FROM requests WHERE student_id=? AND deleted_at IS NULL ORDER BY id DESC LIMIT 5 OFFSET ?',(link['student_id'],(page-1)*5)).fetchall()
    if not rows:
        _message(db,link['chat_id'],t('none',lang),_keyboard(db,lang),batch,link);return
    buttons=[];lines=[card('📍 '+t('track',lang).lstrip('📍 ') if tracking else t('requests',lang),t('choose_request' if tracking else 'your_requests',lang))]
    for row in rows:
        released=db.execute('SELECT 1 FROM telegram_releases WHERE request_id=?',(row['id'],)).fetchone()
        state=t('approved' if released else row['status'],lang)
        label='NAV-'+str(row['id']).zfill(4)+' · '+_service(db,row,lang)
        lines.append(label+'\n'+status_icon('approved' if released else row['status'])+' '+state+'\n📅 '+_date(row['created_at'])+' · '+t(row['channel'] if row['channel'] in ('phone','kiosk') else 'kiosk',lang))
        buttons.append([{'text':label[:80],'callback_data':('track:' if tracking else 'req:')+str(row['id'])}])
    paging=[]
    if page>1:paging.append({'text':t('previous',lang),'callback_data':('tracks:' if tracking else 'list:')+str(page-1)})
    if page*5<total:paging.append({'text':t('next',lang),'callback_data':('tracks:' if tracking else 'list:')+str(page+1)})
    if paging:buttons.append(paging)
    lines.append(t('page',lang)+' '+str(page)+' / '+str(max(1,(total+4)//5)))
    _message(db,link['chat_id'],'\n\n'.join(lines),{'inline_keyboard':buttons},batch,link)


def _detail(db,link,row,lang,batch,tracking=False):
    release=db.execute('SELECT * FROM telegram_releases WHERE request_id=?',(row['id'],)).fetchone()
    title='NAV-'+str(row['id']).zfill(4)+' · '+_service(db,row,lang)
    state=t('approved' if release else row['status'],lang)
    if tracking:
        stages=[('new',True),('assigned',row['status']!='new'),('prepared',row['status'] in ('pending_approval','closed')),('approved' if release else 'pending_approval',bool(release)),('delivered',delivery(db,row['id'])['state']=='sent')]
        text=card(title,status_icon('approved' if release else row['status'])+' '+state)+'\n\n'+'\n'.join(('✅ ' if done else '🟠 ' if key=='pending_approval' and row['status']=='pending_approval' else '○ ')+t(key,lang) for key,done in stages)
        text+='\n\n'+t('wait' if not release else 'approved',lang)
    else:
        text=card(title,status_icon('approved' if release else row['status'])+' '+state+'\n📅 '+t('created',lang)+': '+_date(row['created_at']))+'\n\n'+(row['content'] or '')[:2000]
        if row['deadline']:text+='\n'+t('deadline',lang)+': '+_date(row['deadline'])
    if row['status']=='closed' and not release:text+='\n'+t('not_approved',lang)
    buttons=[[{'text':t('update' if tracking else 'track',lang),'callback_data':'track:'+str(row['id'])}]]
    if release:buttons.append([{'text':t('answer',lang),'callback_data':'ans:'+str(row['id'])}])
    buttons.append([{'text':t('back',lang),'callback_data':'list:1'}])
    _message(db,link['chat_id'],text,{'inline_keyboard':buttons},batch,link,row['id'])


def process_update(db,update):
    if not isinstance(update,dict) or type(update.get('update_id')) is not int or not 0<=update['update_id']<2**63:return
    update_id=update['update_id']
    if update_id<=int(runtime(db,'last_update_id','-1')):return
    set_runtime(db,'last_update_id',update_id)
    callback=update.get('callback_query');callback=callback if isinstance(callback,dict) else None
    message=callback.get('message') if callback else update.get('message')
    sender=callback.get('from') if callback else message.get('from') if isinstance(message,dict) else None
    if not isinstance(message,dict) or not isinstance(sender,dict) or sender.get('is_bot'):return
    chat=message.get('chat')
    if not isinstance(chat,dict) or chat.get('type')!='private' or type(chat.get('id')) is not int or not 0<chat['id']<2**63 or sender.get('id')!=chat['id']:return
    chat_id=chat['id'];now=int(time.time());batch='update:'+str(update_id)
    db.execute('INSERT OR IGNORE INTO telegram_chats(chat_id) VALUES (?)',(chat_id,))
    state=db.execute('SELECT * FROM telegram_chats WHERE chat_id=?',(chat_id,)).fetchone();lang=state['lang']
    if state['window_start']<now-60:db.execute('UPDATE telegram_chats SET window_start=?,events=1 WHERE chat_id=?',(now,chat_id))
    else:
        db.execute('UPDATE telegram_chats SET events=events+1 WHERE chat_id=?',(chat_id,))
        if state['events']>=20:
            if state['events']==20:_message(db,chat_id,t('flood',lang),None,batch)
            return
    if callback and isinstance(callback.get('id'),str) and len(callback['id'])<=128:
        _job(db,chat_id,'callback',{'callback_query_id':callback['id']},'ack:'+str(update_id))
    text=message.get('text','')
    if not isinstance(text,str) or len(text)>4096:text=''
    data=callback.get('data') if callback else None
    if data is not None and (not isinstance(data,str) or len(data)>64):return
    if isinstance(data,str) and data.startswith('lang:'):
        chosen=data.split(':',1)[1]
        if chosen in LANGS:lang=chosen;db.execute('UPDATE telegram_chats SET lang=? WHERE chat_id=?',(lang,chat_id))
        linked=db.execute('SELECT 1 FROM telegram_links WHERE chat_id=?',(chat_id,)).fetchone()
        _message(db,chat_id,t('menu' if linked else 'code' if state['pending_sid'] else 'welcome',lang),_keyboard(db,lang) if linked else None,batch);return
    link=db.execute('SELECT * FROM telegram_links WHERE chat_id=?',(chat_id,)).fetchone()
    if not link:
        if text.startswith('/start') or not state['pending_sid']:
            try:sid=w.validate_id(text.strip()) if not text.startswith('/') else None
            except w.Problem:sid=None
            if sid:
                db.execute("UPDATE telegram_chats SET state='code',pending_sid=? WHERE chat_id=?",(sid,chat_id))
                _message(db,chat_id,t('code',lang),None,batch)
            else:
                db.execute("UPDATE telegram_chats SET state='id',pending_sid=NULL WHERE chat_id=?",(chat_id,))
                _message(db,chat_id,t('welcome',lang),{'remove_keyboard':True},batch)
                _message(db,chat_id,t('choose_language',lang),languages(),batch)
                _launch_button(db,chat_id,batch)
            return
        outcome=_verify(db,chat_id,state['pending_sid'],text)
        if outcome=='linked':
            db.execute("UPDATE telegram_chats SET state='linked',pending_sid=NULL WHERE chat_id=?",(chat_id,))
            link=db.execute('SELECT * FROM telegram_links WHERE chat_id=?',(chat_id,)).fetchone()
            _message(db,chat_id,t('linked',lang)+'\n'+t('menu',lang),_keyboard(db,lang),batch,link)
            schedule_releases(db)
        else:_message(db,chat_id,t(outcome,lang),None,batch)
        return
    student=db.execute("SELECT * FROM students WHERE hemis_id=? AND status='active'",(link['student_id'],)).fetchone()
    if not student:
        _message(db,chat_id,t('inactive',lang),None,batch);return
    op,arg=(data.split(':',1)+[''])[:2] if data else ('','')
    if op in ('req','track','ans','list','tracks'):
        if not arg.isascii() or not arg.isdigit() or not 1<=len(arg)<=18:return
        number=int(arg)
        if op in ('list','tracks'):_list(db,link,number,lang,batch,op=='tracks');return
        row=_request(db,link,number)
        if not row:_message(db,chat_id,t('missing',lang),None,batch,link);return
        if op=='ans':
            release=db.execute('SELECT * FROM telegram_releases WHERE request_id=? AND student_id=?',(number,link['student_id'])).fetchone()
            if release:_release_messages(db,link,release,batch,lang)
            else:_message(db,chat_id,t('not_approved',lang),None,batch,link,number)
        else:_detail(db,link,row,lang,batch,op=='track')
        return
    if text in ('/requests',*labels('requests')):_list(db,link,1,lang,batch)
    elif text in ('/track',*labels('track')):_list(db,link,1,lang,batch,True)
    elif text in ('/profile',*labels('profile')):
        fields=[('HEMIS ID',student['hemis_id']),(t('course',lang),student['course']),(t('faculty',lang),student['faculty']),(t('group',lang),student['student_group']),(t('specialty',lang),student['programme']),(t('type',lang),student['education_type']),(t('form',lang),student['education_form'])]
        _message(db,chat_id,card('👤 '+student['full_name'],'\n'.join(str(key)+': '+str(value or '—') for key,value in fields))+'\n\n✅ '+t('verified',lang),_keyboard(db,lang),batch,link)
    elif text in ('/help',*labels('help')):_message(db,chat_id,t('help_text',lang),_keyboard(db,lang),batch,link)
    elif text in ('/language',*labels('language')):_message(db,chat_id,t('choose_language',lang),languages(),batch,link)
    else:_message(db,chat_id,card('🏛 NAVBOT · '+t('portal',lang),student['full_name']+'\n\n'+t('menu_note',lang)),_keyboard(db,lang),batch,link)


def retry(db,user,data):
    row=w.get_request(db,user,data.get('id'))
    w.need(user,('admin','manager','head'))
    if user['role']=='manager' and row['manager_id']!=user['id']:raise w.Problem('Vakolat yo‘q',403)
    if user['role']=='head' and row['department']!=user['department']:raise w.Problem('Vakolat yo‘q',403)
    db.execute("UPDATE telegram_outbox SET state='pending',next_attempt=0,error='',lease_until=0 WHERE request_id=? AND state IN ('failed','uncertain') AND batch_key LIKE 'release:%'",(row['id'],))
    w.audit(db,user,'telegram_retry',{'request_id':row['id']})
    return {'ok':True}


def health(db):
    result={key:runtime(db,key) for key in ('last_poll','last_send','worker_error','bot_username')}
    try:result['active']=not result['worker_error'] and time.time()-datetime.fromisoformat(result['last_poll']).timestamp()<60
    except ValueError:result['active']=False
    return result
