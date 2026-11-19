"""Single-kiosk outbound Windows print agent; atomic queue, no browser print UI."""
import hashlib
import hmac
import json
import secrets
import time
from uuid import uuid4
import workflow as w


def initialize(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS kiosk_printer(id INTEGER PRIMARY KEY CHECK(id=1),enabled INTEGER NOT NULL DEFAULT 0,token_hash TEXT NOT NULL DEFAULT '',last_seen INTEGER NOT NULL DEFAULT 0,ready INTEGER NOT NULL DEFAULT 0,printer_name TEXT NOT NULL DEFAULT '');
      INSERT OR IGNORE INTO kiosk_printer(id) VALUES (1);
      CREATE TABLE IF NOT EXISTS kiosk_print_jobs(ticket_id INTEGER PRIMARY KEY,payload TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'pending',claim TEXT,worker TEXT,lease_until INTEGER NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL);
      CREATE INDEX IF NOT EXISTS kiosk_print_pending ON kiosk_print_jobs(state,created_at);
    ''')


def mode(db):
    row=db.execute('SELECT * FROM kiosk_printer WHERE id=1').fetchone()
    return 'agent' if row and row['enabled'] else 'browser'


def _expire(db):
    now=int(time.time())
    db.execute("UPDATE kiosk_print_jobs SET state='uncertain',error='agent_interrupted',updated_at=? WHERE state='printing' AND lease_until<?",(now,now))
    db.execute("UPDATE kiosk_print_jobs SET state='failed',error='queue_expired',updated_at=? WHERE state='pending' AND created_at<?",(now,now-900))


def metadata(db):
    row=db.execute('SELECT * FROM kiosk_printer WHERE id=1').fetchone()
    now=int(time.time())
    state="CASE WHEN state='printing' AND lease_until<"+str(now)+" THEN 'uncertain' WHEN state='pending' AND created_at<"+str(now-900)+" THEN 'failed' ELSE state END"
    counts={r['state']:r['total'] for r in db.execute('SELECT '+state+' state,COUNT(*) total FROM kiosk_print_jobs GROUP BY 1')}
    jobs=[dict(r) for r in db.execute('SELECT ticket_id,'+state+' state,error,updated_at FROM kiosk_print_jobs ORDER BY ticket_id DESC LIMIT 20')]
    return {'mode':mode(db),'ready':bool(row['ready'] and row['last_seen']>now-45),'printer_name':row['printer_name'],'last_seen':row['last_seen'],'counts':counts,'jobs':jobs}


def pair(db,user):
    w.need(user,('admin',));_expire(db)
    if db.execute("SELECT 1 FROM kiosk_print_jobs WHERE state IN ('pending','printing','uncertain','failed')").fetchone():raise w.Problem('Avval printerdagi tugallanmagan cheklarni tekshiring',409)
    token=secrets.token_urlsafe(32)
    db.execute('UPDATE kiosk_printer SET enabled=1,token_hash=?,last_seen=0,ready=0,printer_name=\'\' WHERE id=1',(hashlib.sha256(token.encode()).hexdigest(),))
    w.audit(db,user,'kiosk_printer_pair',{})
    return {'token':token,'worker_id':str(uuid4())}


def configure(db,user,data):
    w.need(user,('admin',));_expire(db)
    if data.get('action')=='pair':return pair(db,user)
    if data.get('action')=='browser':
        if db.execute("SELECT 1 FROM kiosk_print_jobs WHERE state IN ('pending','printing','uncertain','failed')").fetchone():raise w.Problem('Avval tugallanmagan cheklarni tekshiring',409)
        db.execute("UPDATE kiosk_printer SET enabled=0,token_hash='',ready=0 WHERE id=1")
        w.audit(db,user,'kiosk_printer_browser',{})
        return {'ok':True}
    if data.get('action') in ('retry','cancel'):
        ticket_id=data.get('ticket_id')
        if type(ticket_id) is not int:raise w.Problem('Chek raqamini tekshiring')
        reason=w.text(data,'reason',500,True)
        row=db.execute('SELECT * FROM kiosk_print_jobs WHERE ticket_id=?',(ticket_id,)).fetchone()
        if not row or row['state'] not in ('failed','uncertain'):raise w.Problem('Chek holati o‘zgargan',409)
        if data['action']=='retry' and data.get('confirm_duplicate') is not True:raise w.Problem('Takroriy chek chiqishi mumkinligini tasdiqlang')
        state='pending' if data['action']=='retry' else 'cancelled'
        now=int(time.time())
        db.execute('UPDATE kiosk_print_jobs SET state=?,claim=NULL,worker=NULL,lease_until=0,error=\'\',created_at=?,updated_at=? WHERE ticket_id=?',(state,now,now,ticket_id))
        w.audit(db,user,'kiosk_printer_'+data['action'],{'ticket_id':ticket_id,'reason':reason})
        return {'ok':True}
    raise w.Problem('Noma’lum amal')


def ensure_ready(db):
    if mode(db)=='browser':return
    row=db.execute('SELECT * FROM kiosk_printer WHERE id=1').fetchone()
    if not row['ready'] or row['last_seen']<time.time()-45:
        raise w.Problem('Printer yordamchisi ulanmagan. Xodimga murojaat qiling',503)
    if db.execute("SELECT 1 FROM kiosk_print_jobs WHERE state IN ('failed','uncertain') OR (state='printing' AND lease_until<?)",(int(time.time()),)).fetchone():
        raise w.Problem('Printerdagi oldingi chek holatini xodim tekshirishi kerak',503)


def enqueue(db,ticket,config):
    if mode(db)=='browser':return {'print_mode':'browser'}
    language=('uz','ru','en').index(ticket['lang'])
    import routing
    payload={'number':routing.code(ticket),'university':config['university'][language],'office':config['office'][language],'section':config['catalog'][ticket['section']][0][language],'service':ticket['content_name'],'created_at':ticket['created_at'],'footer':config['receipt_footer'][language]}
    now=int(time.time())
    db.execute('INSERT OR IGNORE INTO kiosk_print_jobs(ticket_id,payload,created_at,updated_at) VALUES (?,?,?,?)',(ticket['id'],json.dumps(payload,ensure_ascii=False),now,now))
    return {'print_mode':'agent','print_state':'queued'}


def authenticate(db,authorization):
    row=db.execute('SELECT * FROM kiosk_printer WHERE id=1').fetchone()
    token=authorization.removeprefix('Bearer ') if isinstance(authorization,str) and authorization.startswith('Bearer ') else ''
    digest=hashlib.sha256(token.encode()).hexdigest()
    if not row['enabled'] or not 20<=len(token)<=128 or not hmac.compare_digest(digest,row['token_hash']):raise w.Problem('Printer tasdig‘i noto‘g‘ri',401)


def agent(db,authorization,data):
    authenticate(db,authorization);_expire(db)
    worker=data.get('worker_id')
    try:
        if str(__import__('uuid').UUID(worker))!=worker:raise ValueError()
    except (ValueError,TypeError,AttributeError):raise w.Problem('Printer yordamchisi IDsi noto‘g‘ri')
    action=data.get('action','poll');now=int(time.time())
    if action=='ack':
        ticket_id=data.get('ticket_id');claim=data.get('claim');state=data.get('state')
        if type(ticket_id) is not int or not isinstance(claim,str) or state not in ('spooled','failed','uncertain'):raise w.Problem('Printer javobini tekshiring')
        row=db.execute('SELECT * FROM kiosk_print_jobs WHERE ticket_id=?',(ticket_id,)).fetchone()
        if not row or row['worker']!=worker or not hmac.compare_digest(row['claim'] or '',claim):raise w.Problem('Chek tasdig‘i eskirgan',409)
        if row['state']==state:return {'ok':True}
        if row['state'] not in ('printing','uncertain'):raise w.Problem('Chek holati o‘zgargan',409)
        failure='' if state=='spooled' else 'print_failed' if state=='failed' else 'agent_interrupted'
        db.execute('UPDATE kiosk_print_jobs SET state=?,error=?,lease_until=0,updated_at=? WHERE ticket_id=?',(state,failure,now,ticket_id))
        w.audit(db,None,'kiosk_print_'+state,{'ticket_id':ticket_id})
        return {'ok':True}
    if action!='poll' or type(data.get('ready')) is not bool:raise w.Problem('Printer holatini tekshiring')
    printer=data.get('printer_name','')
    if not isinstance(printer,str) or len(printer)>200:raise w.Problem('Printer nomini tekshiring')
    db.execute('UPDATE kiosk_printer SET last_seen=?,ready=?,printer_name=? WHERE id=1',(now,int(data['ready']),''.join(c for c in printer if c.isprintable())))
    if not data['ready']:return {'job':None}
    # A repeated poll returns the same claim; the agent's local durable journal
    # prevents a second print after an acknowledgement or process interruption.
    fresh=False
    row=db.execute("SELECT * FROM kiosk_print_jobs WHERE state IN ('printing','uncertain') AND worker=? ORDER BY ticket_id LIMIT 1",(worker,)).fetchone()
    if not row:
        if db.execute("SELECT 1 FROM kiosk_print_jobs WHERE state IN ('printing','uncertain','failed')").fetchone():return {'job':None}
        row=db.execute("SELECT * FROM kiosk_print_jobs WHERE state='pending' ORDER BY ticket_id LIMIT 1").fetchone()
        if not row:return {'job':None}
        live=db.execute('SELECT r.deleted_at FROM requests r WHERE r.ticket_id=?',(row['ticket_id'],)).fetchone()
        if not live or live['deleted_at']:
            db.execute("UPDATE kiosk_print_jobs SET state='cancelled',payload='{}',updated_at=? WHERE ticket_id=?",(now,row['ticket_id']));return {'job':None}
        fresh=True
        claim=secrets.token_urlsafe(24)
        db.execute("UPDATE kiosk_print_jobs SET state='printing',claim=?,worker=?,lease_until=?,updated_at=? WHERE ticket_id=?",(claim,worker,now+120,now,row['ticket_id']))
        row=db.execute('SELECT * FROM kiosk_print_jobs WHERE ticket_id=?',(row['ticket_id'],)).fetchone()
    return {'job':{'ticket_id':row['ticket_id'],'claim':row['claim'],'state':row['state'],'fresh':fresh,'receipt':json.loads(row['payload'])}}


def ticket_status(db,data):
    """Read only the state of a ticket identified by its unguessable request key."""
    from uuid import UUID
    try:
        raw=data.get('key')
        if not isinstance(raw,str) or str(UUID(raw))!=raw:raise ValueError()
    except (ValueError,TypeError,AttributeError):raise w.Problem('Chek so‘rov kalitini tekshiring')
    ticket=db.execute('SELECT t.id,r.deleted_at FROM tickets t JOIN requests r ON r.ticket_id=t.id WHERE t.request_key=?',(raw,)).fetchone()
    if not ticket:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='retired_test_tickets'").fetchone() and db.execute('SELECT 1 FROM retired_test_tickets WHERE request_key=?',(raw,)).fetchone():return {'state':'cancelled'}
        raise w.Problem('Chek topilmadi',404)
    if ticket['deleted_at']:return {'state':'cancelled'}
    _expire(db)
    job=db.execute('SELECT state FROM kiosk_print_jobs WHERE ticket_id=?',(ticket['id'],)).fetchone()
    return {'state':job['state'] if job else 'browser'}
