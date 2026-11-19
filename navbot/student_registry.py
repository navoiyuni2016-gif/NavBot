"""Student deletion snapshots with protected historical request information."""
import hashlib
import json
import secrets
import time
import workflow as w


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS student_delete_previews(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,targets TEXT NOT NULL,expires_at INTEGER NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS student_registry_migrations(name TEXT PRIMARY KEY)')
    with db:
        added=db.execute("INSERT OR IGNORE INTO student_registry_migrations VALUES ('initial_active_status_v1')").rowcount
        if added:
            count=db.execute("UPDATE students SET status='active' WHERE status!='active'").rowcount
            w.audit(db,None,'students_initial_active',{'count':count})


def fingerprint(student):
    return hashlib.sha256(json.dumps(dict(student),sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def preview(db,user,data):
    w.need(user,('admin',))
    ids=data.get('ids')
    if not isinstance(ids,list) or not ids or len(ids)>100000 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):
        raise w.Problem('Öçiriladigan talabalarni tanlang')
    rows=[]
    for sid in ids:
        w.validate_id(sid)
        row=db.execute('SELECT * FROM students WHERE hemis_id=?',(sid,)).fetchone()
        if row is None:
            raise w.Problem('Talabalar bazasi özgargan. Yangilang',409)
        rows.append(row)
    token=secrets.token_hex(32)
    db.execute('DELETE FROM student_delete_previews WHERE expires_at<=? OR user_id=?',(int(time.time()),user['id']))
    db.execute('INSERT INTO student_delete_previews VALUES (?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],json.dumps([[r['hemis_id'],fingerprint(r)] for r in rows]),int(time.time())+900))
    return {'token':token,'count':len(rows),'sample':[{'hemis_id':r['hemis_id'],'full_name':r['full_name']} for r in rows[:5]]}


def remove(db,user,data):
    w.need(user,('admin',))
    token=data.get('token')
    if not isinstance(token,str) or len(token)!=64:
        raise w.Problem('Öçirishni qayta tayyorlang')
    preview=db.execute('SELECT * FROM student_delete_previews WHERE token_hash=? AND user_id=? AND expires_at>?',(hashlib.sha256(token.encode()).hexdigest(),user['id'],int(time.time()))).fetchone()
    if preview is None:
        raise w.Problem('Öçirish tasdiği eskirgan. Qayta tayyorlang',409)
    targets=json.loads(preview['targets'])
    if type(data.get('confirm_count')) is not int or data['confirm_count']!=len(targets):
        raise w.Problem('Öçiriladigan yozuvlar sonini tasdiqlang')
    rows=[]
    for sid,version in targets:
        row=db.execute('SELECT * FROM students WHERE hemis_id=?',(sid,)).fetchone()
        if row is None or fingerprint(row)!=version:
            raise w.Problem('Talabalar bazasi özgargan. Yangilang',409)
        rows.append(dict(row))
    preserved=0
    for student in rows:
        preserved+=db.execute("UPDATE requests SET student_snapshot=?,version=version+1 WHERE student_id=? AND deleted_at IS NULL AND student_snapshot IS NULL",(json.dumps(student,ensure_ascii=False),student['hemis_id'])).rowcount
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='telegram_links'").fetchone():
            import telegram_bot
            telegram_bot.forget_student(db,student['hemis_id'])
        db.execute('DELETE FROM students WHERE hemis_id=?',(student['hemis_id'],))
    db.execute('DELETE FROM student_delete_previews WHERE token_hash=?',(preview['token_hash'],))
    w.audit(db,user,'students_delete',{'count':len(rows),'hemis_ids':[r['hemis_id'] for r in rows],'preserved_requests':preserved})
    return {'deleted':len(rows),'preserved_requests':preserved}


def set_status(db,user,data):
    w.need(user,('admin',))
    sid=w.validate_id(data.get('hemis_id'))
    status=data.get('status')
    if status not in ('active','inactive'):
        raise w.Problem('Faol yoki nofaol holatni tanlang')
    row=db.execute('SELECT status FROM students WHERE hemis_id=?',(sid,)).fetchone()
    if row is None:
        raise w.Problem('Talaba topilmadi',404)
    db.execute('UPDATE students SET status=? WHERE hemis_id=?',(status,sid))
    w.audit(db,user,'student_status',{'hemis_id':sid,'before':row['status'],'after':status})
    return {'hemis_id':sid,'status':status}
