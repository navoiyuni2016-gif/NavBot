"""Telegram Mini App: signed Telegram identity, existing staff verification, own data only."""
import hashlib
import hmac
import json
import re
import time
from urllib.parse import parse_qsl, urlsplit
import integrations
import telegram_bot as bot
import workflow as w
from telegram_text import LANGS

MAX_AGE=3600


def initialize(db):
    db.execute("CREATE TABLE IF NOT EXISTS telegram_mini_config(id INTEGER PRIMARY KEY CHECK(id=1),url TEXT NOT NULL DEFAULT '')")
    db.execute("INSERT OR IGNORE INTO telegram_mini_config(id) VALUES (1)")


def config(db):
    row=db.execute('SELECT url FROM telegram_mini_config WHERE id=1').fetchone()
    return {'url':row['url'] if row else ''}


def save_config(db,user,data):
    w.need(user,('admin',))
    url=data.get('url','')
    if not isinstance(url,str) or len(url)>500:raise w.Problem('Mini App HTTPS manzilini tekshiring')
    url=url.strip()
    if url:
        parsed=urlsplit(url)
        if (parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path!='/student' or re.search(r'[\s\\]',url)):
            raise w.Problem('Manzil https://domen.uz/student ko‘rinishida bo‘lsin')
    db.execute('UPDATE telegram_mini_config SET url=? WHERE id=1',(url,))
    w.audit(db,user,'telegram_mini_config',{'url':url})
    return config(db)


def authenticate(db,raw):
    if not isinstance(raw,str) or not 1<=len(raw)<=16384:raise w.Problem('Ilovani Telegram bot orqali oching',401)
    try:
        pairs=parse_qsl(raw,keep_blank_values=True,strict_parsing=True,max_num_fields=32)
        values=dict(pairs)
        if len(values)!=len(pairs) or not re.fullmatch(r'[0-9a-f]{64}',values.get('hash','')):raise ValueError()
        auth_date=int(values['auth_date']);now=int(time.time())
        if not now-MAX_AGE<=auth_date<=now+30:raise ValueError()
        _,token=integrations._check_ready(db,'telegram')
        secret=hmac.new(b'WebAppData',token.encode(),hashlib.sha256).digest()
        signed='\n'.join(key+'='+value for key,value in sorted(pairs) if key!='hash')
        expected=hmac.new(secret,signed.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,values['hash']):raise ValueError()
        user=json.loads(values['user'])
        chat_id=user.get('id') if isinstance(user,dict) else None
        if type(chat_id) is not int or not 0<chat_id<2**63 or user.get('is_bot'):raise ValueError()
        if values.get('chat_type') not in (None,'private','sender'):raise ValueError()
        return chat_id
    except (ValueError,KeyError,TypeError,integrations.IntegrationError):
        raise w.Problem('Telegram tasdig‘i eskirgan yoki noto‘g‘ri. Ilovani botdan qayta oching',401) from None


def _link(db,chat_id):
    return db.execute("SELECT l.* FROM telegram_links l JOIN students s ON s.hemis_id=l.student_id WHERE l.chat_id=? AND s.status='active'",(chat_id,)).fetchone()


def _language(db,chat_id):
    row=db.execute('SELECT lang FROM telegram_chats WHERE chat_id=?',(chat_id,)).fetchone()
    return row['lang'] if row and row['lang'] in LANGS else 'uz'


def _time(db,request_id,actions):
    params=','.join('?' for _ in actions)
    row=db.execute('SELECT created_at FROM history WHERE request_id=? AND action IN ('+params+') ORDER BY id DESC LIMIT 1',(request_id,*actions)).fetchone()
    return row['created_at'] if row else None


def _request(db,link,row,lang,detail=False):
    release=db.execute('SELECT * FROM telegram_releases WHERE request_id=? AND student_id=?',(row['id'],link['student_id'])).fetchone()
    if release and not bot._release_valid(db,release):release=None
    result={'id':row['id'],'number':'NAV-'+str(row['id']).zfill(4),'service':bot._service(db,row,lang),'status':'approved' if release else row['status'],'channel':row['channel'],'created_at':row['created_at']}
    if not detail:return result
    state=row['status'];sent=bot.delivery(db,row['id'])['state']=='sent'
    result.update(content=row['content'],deadline=row['deadline'],answer=release['answer'] if release else None,result=release['result'] if release else None,files=[])
    sent_at=db.execute("SELECT MAX(sent_at) FROM telegram_outbox WHERE request_id=? AND batch_key LIKE 'release:%' AND state='sent'",(row['id'],)).fetchone()[0]
    result['timeline']=[
        {'key':'new','done':True,'at':row['created_at']},
        {'key':'assigned','done':state!='new','at':_time(db,row['id'],('assign',))},
        {'key':'prepared','done':state in ('pending_approval','closed'),'at':row['answered_at']},
        {'key':'approved','done':bool(release),'current':state=='pending_approval' and not release,'at':release['approved_at'] if release else _time(db,row['id'],('submit',))},
        {'key':'delivered','done':sent,'at':sent_at if sent else None}]
    if release:
        for file_id in json.loads(release['attachment_ids']):
            file=db.execute('SELECT id,name,mime,size FROM attachments WHERE id=? AND request_id=?',(file_id,row['id'])).fetchone()
            if file:result['files'].append(dict(file))
    return result


def handle(db,data):
    chat_id=authenticate(db,data.get('init_data'))
    action=data.get('action','state');lang=_language(db,chat_id)
    db.execute('INSERT OR IGNORE INTO telegram_chats(chat_id) VALUES (?)',(chat_id,))
    if action=='language':
        lang=data.get('lang')
        if lang not in LANGS:raise w.Problem('Tilni tekshiring')
        db.execute('UPDATE telegram_chats SET lang=? WHERE chat_id=?',(lang,chat_id))
        return {'ok':True,'lang':lang}
    link=_link(db,chat_id)
    if action=='link':
        if link:return {'ok':True,'linked':True,'lang':lang}
        sid=w.validate_id(data.get('hemis_id'))
        code=data.get('code')
        if not isinstance(code,str) or not 1<=len(code)<=32:raise w.Problem('Xodim bergan bir martalik kodni kiriting')
        outcome=bot._verify(db,chat_id,sid,code)
        if outcome!='linked':return {'ok':False,'error_code':outcome,'lang':lang}
        db.execute("UPDATE telegram_chats SET state='linked',pending_sid=NULL WHERE chat_id=?",(chat_id,))
        bot.schedule_releases(db)
        return {'ok':True,'linked':True,'lang':lang}
    if action=='state':
        if not link:return {'linked':False,'lang':lang}
        student=db.execute('SELECT * FROM students WHERE hemis_id=?',(link['student_id'],)).fetchone()
        fields=('hemis_id','full_name','course','faculty','student_group','programme','education_type','education_form')
        return {'linked':True,'lang':lang,'student':{key:student[key] for key in fields}}
    if not link:raise w.Problem('Avval HEMIS ID va bir martalik kod bilan bog‘laning',403)
    if action=='requests':
        page=data.get('page',1)
        if type(page) is not int or not 1<=page<=100000:raise w.Problem('Sahifani tekshiring')
        total=db.execute('SELECT COUNT(*) FROM requests WHERE student_id=? AND deleted_at IS NULL',(link['student_id'],)).fetchone()[0]
        rows=db.execute('SELECT * FROM requests WHERE student_id=? AND deleted_at IS NULL ORDER BY id DESC LIMIT 5 OFFSET ?',(link['student_id'],(page-1)*5)).fetchall()
        return {'requests':[_request(db,link,row,lang) for row in rows],'total':total,'page':page}
    if action in ('request','file'):
        request_id=data.get('id')
        if type(request_id) is not int or not 0<request_id<2**63:raise w.Problem('Murojaat raqamini tekshiring')
        row=bot._request(db,link,request_id)
        if not row:raise w.Problem('Murojaat topilmadi',404)
        result=_request(db,link,row,lang,True)
        if action=='request':return {'request':result}
        file_id=data.get('file_id')
        if not any(file['id']==file_id for file in result['files']):raise w.Problem('Fayl topilmadi',404)
        file=db.execute('SELECT body,mime,name FROM attachments WHERE id=? AND request_id=?',(file_id,request_id)).fetchone()
        bot.background_audit(db,'telegram_mini_download',{'request_id':request_id,'filename':file['name']})
        return bytes(file['body']),file['mime'],file['name']
    raise w.Problem('Noma’lum amal')
