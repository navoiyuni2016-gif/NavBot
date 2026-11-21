"""Audited suspension of manager service actions; read/login access remains."""
import workflow as w
SERVICE_PATHS={'/api/action','/api/request/create','/api/request/action','/api/attachment/upload','/api/telegram/code','/api/telegram/retry','/api/telegram/unlink'}

def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS manager_service_blocks(user_id INTEGER PRIMARY KEY REFERENCES users(id),reason TEXT NOT NULL,blocked_by INTEGER NOT NULL REFERENCES users(id),blocked_at TEXT NOT NULL)')

def status(db,user_id):
    row=db.execute('SELECT reason,blocked_by,blocked_at FROM manager_service_blocks WHERE user_id=?',(user_id,)).fetchone()
    return dict(row) if row else None

def enforce(db,user,path):
    if user and user['role']=='manager' and path in SERVICE_PATHS:
        blocked=status(db,user['id'])
        if blocked:raise w.Problem('Xizmat ko‘rsatish vaqtincha bloklangan. Sabab: '+blocked['reason'],403)

def managers(db,user):
    w.need(user,('admin','head'))
    rows=db.execute("SELECT u.id,u.full_name,u.username,u.department,u.operator,b.reason,b.blocked_at,actor.full_name blocked_by_name FROM users u LEFT JOIN manager_service_blocks b ON b.user_id=u.id LEFT JOIN users actor ON actor.id=b.blocked_by WHERE u.role='manager' AND NOT EXISTS(SELECT 1 FROM user_account_states s WHERE s.user_id=u.id AND s.state='deleted') ORDER BY u.operator,u.full_name")
    return {'managers':[dict(row) for row in rows]}

def change(db,user,data):
    w.need(user,('admin','head'))
    target=data.get('user_id');action=data.get('action');reason=w.text(data,'reason',1000,True)
    if type(target) is not int or action not in ('block','unblock') or len(reason)<3:raise w.Problem('Menejer, amal va sababni tekshiring')
    row=db.execute("SELECT id FROM users WHERE id=? AND role='manager' AND NOT EXISTS(SELECT 1 FROM user_account_states s WHERE s.user_id=users.id AND s.state='deleted')",(target,)).fetchone()
    if not row:raise w.Problem('Menejer topilmadi',404)
    before=status(db,target)
    if action=='block':
        if before:raise w.Problem('Menejer allaqachon bloklangan',409)
        db.execute('INSERT INTO manager_service_blocks VALUES(?,?,?,?)',(target,reason,user['id'],w.now()))
    else:
        if not before:raise w.Problem('Menejer bloklanmagan',409)
        db.execute('DELETE FROM manager_service_blocks WHERE user_id=?',(target,))
    w.audit(db,user,'manager_service_'+action,{'user_id':target,'reason':reason,'previous':before})
    return {'ok':True,**managers(db,user)}
