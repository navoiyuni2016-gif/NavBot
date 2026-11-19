"""Request-aware audit, bounded detection rules and reversible private-API IP blocks."""
import hashlib
import ipaddress
import json
import time
from datetime import datetime, timezone
from urllib.parse import unquote
import workflow as w

COLUMNS={'ip':"TEXT NOT NULL DEFAULT ''",'method':"TEXT NOT NULL DEFAULT ''",'path':"TEXT NOT NULL DEFAULT ''",'http_status':'INTEGER NOT NULL DEFAULT 200','category':"TEXT NOT NULL DEFAULT 'business'",'severity':"TEXT NOT NULL DEFAULT 'info'",'actor_username':"TEXT NOT NULL DEFAULT ''",'actor_name':"TEXT NOT NULL DEFAULT ''",'actor_role':"TEXT NOT NULL DEFAULT ''",'filename':"TEXT NOT NULL DEFAULT ''",'request_bytes':'INTEGER NOT NULL DEFAULT 0','response_bytes':'INTEGER NOT NULL DEFAULT 0','hits':'INTEGER NOT NULL DEFAULT 1','request_ref':"TEXT NOT NULL DEFAULT ''",'user_agent':"TEXT NOT NULL DEFAULT ''",'rollup_key':'TEXT'}
PUBLIC_READ=('/', '/login','/kiosk','/tv','/tablo','/assets/i18n.js','/api/catalog','/api/state','/api/settings','/api/audio','/api/audio/plan','/api/branding')
POLL_PATHS=('/api/kiosk-printer/agent','/api/admin/kiosk-printer','/api/state','/api/settings','/api/catalog','/api/requests','/api/notifications','/api/me','/api/security/audit')
RECOVERY=('/api/me','/api/notifications','/api/profile/role','/api/security/audit','/api/security/unblock','/admin','/profile','/assets/i18n.js')


def initialize(db):
    existing={r[1] for r in db.execute('PRAGMA table_info(audit)')}
    for name,spec in COLUMNS.items():
        if name not in existing:db.execute(f'ALTER TABLE audit ADD COLUMN {name} {spec}')
    db.execute('CREATE UNIQUE INDEX IF NOT EXISTS audit_rollup ON audit(rollup_key) WHERE rollup_key IS NOT NULL')
    db.execute('CREATE INDEX IF NOT EXISTS audit_security_ip ON audit(ip,created_at)')
    db.execute('CREATE INDEX IF NOT EXISTS audit_security_action ON audit(action,created_at)')
    db.execute('CREATE TABLE IF NOT EXISTS security_ip_blocks(ip TEXT PRIMARY KEY,blocked_until INTEGER NOT NULL,reason TEXT NOT NULL,created_at TEXT NOT NULL)')
    if 'security_alert_id' not in {r[1] for r in db.execute('PRAGMA table_info(notifications)')}:
        db.execute('ALTER TABLE notifications ADD COLUMN security_alert_id INTEGER')


def client_ip(peer,headers):
    # Only the local reverse proxy is trusted; Nginx must overwrite X-Real-IP.
    address=peer
    if peer in ('127.0.0.1','::1') and headers.get('X-Real-IP'):
        address=headers['X-Real-IP']
    try:return str(ipaddress.ip_address(address))
    except ValueError:return str(ipaddress.ip_address(peer))


def clean(value,limit=200):
    return ''.join(c for c in str(value) if c.isprintable())[:limit]


def probe(path):
    path=unquote(path).lower()
    return any(path.startswith(p) for p in ('/.env','/.git','/wp-admin','/wp-login.php','/phpmyadmin','/cgi-bin','/etc/passwd')) or '../' in path


def gate(db,context,user):
    path,method=context['path'],context['method']
    block=db.execute('SELECT blocked_until FROM security_ip_blocks WHERE ip=? AND blocked_until>?',(context['ip'],int(time.time()))).fetchone()
    if probe(path):
        if block:
            context['blocked']=True
            return 429
        context['probe']=True
        return 403
    if not block:return None
    if method=='GET' and (path in PUBLIC_READ or path.startswith('/media/')):return None
    if user and (user.get('base_role') or user['role'])=='admin' and (method=='GET' or path in ('/api/security/unblock','/api/profile/role')):
        context['recovery']=True
        return None
    context['blocked']=True
    return 429


def metadata(data):
    result={}
    for key in ('id','user_id','section','operator'):
        if type(data.get(key)) is int:result[key]=data[key]
    sid=data.get('hemis_id')
    if isinstance(sid,str):
        try:result['hemis_id']=w.validate_id(sid)
        except w.Problem:pass
    action=data.get('action')
    if action in ('call','recall','start','finish','assign','update','submit','return','resolve','approve','correct','deadline','delete','deactivate','activate'):
        result['operation']=action
    return result


def write(db,context,user,action,detail,category='activity',severity='info',status=200,rollup=None):
    actor=user or {}
    values=(actor.get('id'),action,json.dumps(detail,ensure_ascii=False),w.now(),context.get('ip',''),context.get('method',''),context.get('path',''),status,category,severity,context.get('username') or actor.get('username',''),actor.get('full_name',''),actor.get('active_role') or actor.get('role',''),context.get('filename',''),context.get('request_bytes',0),context.get('response_bytes',0),context.get('request_ref',''),context.get('user_agent',''),rollup)
    if rollup:
        prior=db.execute('SELECT id FROM audit WHERE rollup_key=?',(rollup,)).fetchone()
        if prior:
            db.execute('UPDATE audit SET hits=hits+1,response_bytes=response_bytes+?,detail=? WHERE id=?',(context.get('response_bytes',0),json.dumps({'last_seen':w.now(),'last_path':context.get('path','')}),prior['id']))
            return prior['id']
    return db.execute('INSERT INTO audit(actor_id,action,detail,created_at,ip,method,path,http_status,category,severity,actor_username,actor_name,actor_role,filename,request_bytes,response_bytes,request_ref,user_agent,rollup_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',values).lastrowid


def alert(db,event_id,message):
    for admin in db.execute("SELECT id FROM users WHERE role='admin' AND id NOT IN (SELECT user_id FROM user_account_states)"):
        db.execute('INSERT INTO notifications(user_id,request_id,message,created_at,security_alert_id) VALUES (?,0,?,?,?)',(admin['id'],message,w.now(),event_id))


def record(db,context,user,status):
    if context.get('recovery'):context.setdefault('metadata',{})['recovery_access']=True
    now=int(time.time());ip=context['ip'];path=context['path']
    business=db.execute('SELECT id FROM audit WHERE request_ref=?',(context['request_ref'],)).fetchall()
    if business:
        db.execute('UPDATE audit SET http_status=?,response_bytes=? WHERE request_ref=?',(status,context.get('response_bytes',0),context['request_ref']))
    if context.get('blocked'):action,category,severity='ip_blocked_request','blocked','high'
    elif context.get('probe'):action,category,severity='sensitive_path_probe','security','high'
    elif path=='/api/login' and status in (401,429):action,category,severity='login_failed','login','warning'
    elif status==403:action,category,severity='permission_denied','security','warning'
    elif status>=500:action,category,severity='server_error','error','high'
    elif status>=400:action,category,severity='request_rejected','validation','info'
    elif context.get('filename') and context['method']=='GET':action,category,severity='file_download','download','info'
    elif context['method']=='POST' and (context.get('filename') or 'upload' in path or 'import' in path):action,category,severity='file_upload','upload','info'
    else:action,category,severity='http_request','traffic' if path in POLL_PATHS else 'activity','info'
    rollup=None
    if path in POLL_PATHS or context.get('blocked'):
        rollup=hashlib.sha256(json.dumps([ip,(user or {}).get('id'),'[blocked]' if context.get('blocked') else path,status,now//60]).encode()).hexdigest()
    if not business or status>=400:
        event_id=write(db,context,user,action,context.get('metadata',{}),category,severity,status,rollup)
    else:event_id=business[-1]['id']
    # Existing successful logins from a new IP are visible and generate an in-app alert.
    if path=='/api/login' and status==200 and user:
        known=db.execute("SELECT 1 FROM audit WHERE actor_id=? AND action='login' AND ip=? AND request_ref!=? LIMIT 1",(user['id'],ip,context['request_ref'])).fetchone()
        other=db.execute("SELECT 1 FROM audit WHERE actor_id=? AND action='login' AND ip!='' AND ip!=? LIMIT 1",(user['id'],ip)).fetchone()
        if other and not known:
            eid=write(db,context,user,'new_login_ip',{},'security','warning')
            alert(db,eid,'Xavfsizlik: '+clean(user['username'],64)+' hisobi yangi IPdan kirdi: '+ip)
    if category not in ('login','security') or action not in ('login_failed','sensitive_path_probe'):return
    since=datetime.fromtimestamp(now-(600 if action=='login_failed' else 300),timezone.utc).isoformat(timespec='seconds')
    failures=db.execute('SELECT COALESCE(SUM(hits),0) FROM audit WHERE ip=? AND action=? AND created_at>=?',(ip,action,since)).fetchone()[0]
    threshold=10 if action=='login_failed' else 3
    if failures<threshold:return
    existing=db.execute('SELECT 1 FROM security_ip_blocks WHERE ip=? AND blocked_until>?',(ip,now)).fetchone()
    if existing:return
    reason='Takroriy kirish xatolari' if action=='login_failed' else 'Maxfiy fayllarni qidirish urinishlari'
    db.execute('INSERT INTO security_ip_blocks VALUES (?,?,?,?) ON CONFLICT(ip) DO UPDATE SET blocked_until=excluded.blocked_until,reason=excluded.reason,created_at=excluded.created_at',(ip,now+900,reason,w.now()))
    eid=write(db,context,user,'ip_blocked',{'reason':reason,'minutes':15},'security','critical')
    alert(db,eid,'Xavfsizlik: '+ip+' IP 15 daqiqaga bloklandi. '+reason)


def unblock(db,user,data,context):
    w.need(user,('admin',))
    try:ip=str(ipaddress.ip_address(data.get('ip','')))
    except ValueError:raise w.Problem('IP manzilini tekşiring')
    reason=w.text(data,'reason',500,True)
    db.execute('DELETE FROM security_ip_blocks WHERE ip=?',(ip,))
    w.audit(db,user,'ip_unblocked',{'ip':ip,'reason':reason})
    return {'ok':True}


def page(db,user,query):
    w.need(user,('admin',))
    def value(key):return (query.get(key,[''])[0])[:200]
    try:number=max(1,int(value('page') or '1'))
    except ValueError:raise w.Problem('Sahifani tekşiring')
    clauses=[];params=[]
    for key,column in (('ip','a.ip'),('action','a.action'),('severity','a.severity'),('category','a.category')):
        if value(key):clauses.append(column+'=?');params.append(value(key))
    if value('actor'):
        clauses.append("(COALESCE(NULLIF(a.actor_name,''),u.full_name,'') LIKE ? OR a.actor_username LIKE ?)")
        params+=['%'+value('actor')+'%']*2
    from datetime import date,timedelta
    for key,op,hours in (('from','>=',0),('to','<',24)):
        if value(key):
            try:date.fromisoformat(value(key));bound=datetime.fromisoformat(value(key)+'T00:00:00+05:00')+timedelta(hours=hours)
            except ValueError:raise w.Problem('Sanani tekşiring')
            clauses.append('a.created_at'+op+'?');params.append(bound.astimezone(timezone.utc).isoformat(timespec='seconds'))
    outcome=value('result')
    if outcome=='failed':clauses.append('a.http_status>=400')
    elif outcome=='success':clauses.append('a.http_status<400')
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    source=' FROM audit a LEFT JOIN users u ON u.id=a.actor_id'
    total=db.execute('SELECT COUNT(*)'+source+where,params).fetchone()[0]
    pages=max(1,(total+49)//50);number=min(number,pages)
    rows=[dict(r) for r in db.execute("SELECT a.*,COALESCE(NULLIF(a.actor_name,''),u.full_name,'Tizim / mehmon') actor"+source+where+' ORDER BY a.id DESC LIMIT 50 OFFSET ?',(*params,(number-1)*50))]
    blocks=[dict(r) for r in db.execute('SELECT * FROM security_ip_blocks WHERE blocked_until>? ORDER BY blocked_until DESC',(int(time.time()),))]
    return {'events':rows,'total':total,'page':number,'pages':pages,'blocks':blocks,'actions':[r[0] for r in db.execute('SELECT DISTINCT action FROM audit ORDER BY action')],'categories':[r[0] for r in db.execute('SELECT DISTINCT category FROM audit ORDER BY category')]}
