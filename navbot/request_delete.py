"""Admin-only, version-checked deletion; reserve IDs so old tickets never revive."""
import workflow as w


def remove(db, user, data):
    w.need(user, ('admin',))
    targets=data.get('targets')
    reason=w.text(data,'reason',1000,True)
    if (not isinstance(targets,list) or not 1<=len(targets)<=10000 or
        type(data.get('confirm_count')) is not int or data['confirm_count']!=len(targets)):
        raise w.Problem('Öçiriladigan yozuvlar sonini tasdiqlang')
    seen=set();rows=[]
    for target in targets:
        if not isinstance(target,dict) or type(target.get('id')) is not int or type(target.get('version')) is not int or target['id'] in seen:
            raise w.Problem('Ariza raqamini tekşiring')
        seen.add(target['id'])
        row=w.get_request(db,user,target['id'])
        if row['version']!=target['version']:
            raise w.Problem('Ariza özgargan. Yangilab qayta urinib köring',409)
        rows.append(row)
    stamp=w.now()
    for row in rows:
        for table in ('attachments','notifications','history'):
            db.execute(f'DELETE FROM {table} WHERE request_id=?',(row['id'],))
        # Keep only identity/counter tombstones; erase request payload and staff/student links.
        db.execute("UPDATE requests SET deleted_at=?,student_id=NULL,student_snapshot=NULL,content='',note='',manager_id=NULL,assignee_id=NULL,department='',deadline=NULL,internal_basis='',legal_basis='',answer='',result='',unresolved_reason='',answered_at=NULL,closed_at=NULL,status='closed',updated_at=?,version=version+1 WHERE id=?",(stamp,stamp,row['id']))
        if row['ticket_id']:
            db.execute("UPDATE tickets SET status='done',operator=NULL,called=NULL WHERE id=?",(row['ticket_id'],))
    w.audit(db,user,'requests_delete',{'request_ids':sorted(seen),'count':len(rows),'reason':reason})
    return {'deleted':len(rows)}
