"""Administrative account lifecycle, preserving historical user references."""
import auth
import workflow as w


def users(db):
    return [dict(row) | {'active': row['state'] is None} for row in db.execute(
        f"SELECT {','.join('u.' + f for f in auth.FIELDS.split(','))},s.state FROM users u LEFT JOIN user_account_states s ON s.user_id=u.id WHERE s.state IS NULL OR s.state='inactive' ORDER BY u.full_name,u.id")]


def change(db, actor, data):
    w.need(actor, ('admin',))
    user_id, action = data.get('user_id'), data.get('action')
    if type(user_id) is not int or action not in ('update','deactivate','activate','delete'):
        raise w.Problem('Xodim va amalni tekşiring')
    target = next((u for u in users(db) if u['id'] == user_id), None)
    if not target:
        raise w.Problem('Foydalanuvchi topilmadi', 404)
    if action in ('deactivate','delete') and actor['id'] == user_id:
        raise w.Problem('Öz hisobingizni öçiriş yoki nofaol qiliş mumkin emas', 409)
    if target['role']=='admin' and target['active'] and (action in ('deactivate','delete') or action=='update' and data.get('role')!='admin'):
        if db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND id NOT IN (SELECT user_id FROM user_account_states)").fetchone()[0] <= 1:
            raise w.Problem('Oxirgi faol superadminni saqlaş kerak', 409)
    active_work = db.execute("SELECT 1 FROM requests WHERE deleted_at IS NULL AND status!='closed' AND (manager_id=? OR assignee_id=?) LIMIT 1", (user_id,user_id)).fetchone()
    if action == 'delete':
        if active_work:
            raise w.Problem('Xodimning yakunlanmagan murojaatlari bor. Avval ularni hal qiling yoki qayta biriktiring', 409)
        if data.get('confirm_username') != target['username']:
            raise w.Problem('Tasdiq uçun xodim loginini kiriting')
        db.execute("INSERT INTO user_account_states VALUES (?,'deleted') ON CONFLICT(user_id) DO UPDATE SET state='deleted'", (user_id,))
        db.execute('UPDATE users SET operator=NULL WHERE id=?', (user_id,))
        db.execute('DELETE FROM profile_photos WHERE user_id=?', (user_id,))
    elif action == 'deactivate':
        db.execute("INSERT INTO user_account_states VALUES (?,'inactive') ON CONFLICT(user_id) DO UPDATE SET state='inactive'", (user_id,))
    elif action == 'activate':
        db.execute('DELETE FROM user_account_states WHERE user_id=?', (user_id,))
    else:
        username,name,role,department,operator,employee_number = auth.account_fields(data)
        if actor['id']==user_id and role!=target['role']:
            raise w.Problem('Öz rolingizni özgartiriş mumkin emas', 409)
        if active_work and (role,department,operator)!=(target['role'],target['department'],target['operator']):
            raise w.Problem('Yakunlanmagan murojaatlar bor: rol, bölim yoki oynani özgartirişdan oldin ularni yakunlang', 409)
        import sqlite3
        try:
            db.execute('UPDATE users SET username=?,full_name=?,role=?,department=?,operator=?,employee_number=? WHERE id=?', (username,name,role,department,operator,employee_number,user_id))
        except sqlite3.IntegrityError as error:
            raise w.Problem('Login, operator yoki xodim raqami allaqachon mavjud', 409) from error
    if action!='activate':
        db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
    w.audit(db, actor, 'user_'+action, {'user_id':user_id,'username':target['username']})
    return {'ok':True}
