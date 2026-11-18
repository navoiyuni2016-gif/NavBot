"""Local request registry. All mutations run in one SQLite transaction."""
import json
import routing
import re
import unicodedata
from datetime import datetime, timezone
from uuid import UUID


class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def text(data, key, maximum=4000, required=False):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise Problem(f'{key}: qiymatni tekşiring')
    return value.strip()


def need(user, roles):
    if not user:
        raise Problem('Tizimga kiring', 401)
    if user['role'] not in roles:
        raise Problem('Bu amal uçun vakolat yöq', 403)


def validate_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:H[0-9]{5,19}|[0-9]{6,20})', value):
        raise Problem('HEMIS ID 6–20 belgidan iborat raqam yoki H bilan boshlanuvçi ID bölişi kerak')
    return value


def student(db, hemis_id):
    row = db.execute('SELECT * FROM students WHERE hemis_id=?', (validate_id(hemis_id),)).fetchone()
    return dict(row) if row else None


def search_students(db, query):
    if not isinstance(query,str) or not 2<=len(query.strip())<=120:
        raise Problem('Ism-familiya yoki HEMIS IDni kiriting (2–120 belgi)')
    def normalized(value):
        text=unicodedata.normalize('NFKC',value or '').casefold()
        for source,target in (('ö','o'),('ğ','g'),('ş','sh'),('ç','ch')):
            text=text.replace(source,target)
        return ' '.join(''.join(c for c in text if c.isalnum() or c.isspace()).split())
    tokens=normalized(query).split()
    if not tokens or len(tokens)>8 or len(''.join(tokens))<2:
        raise Problem('Ism-familiya yoki HEMIS IDni kiriting (2–120 belgi)')
    db.create_function('student_search_text',1,normalized,deterministic=True)
    where=' AND '.join("student_search_text(hemis_id || ' ' || full_name) LIKE ?" for _ in tokens)
    rows=db.execute('SELECT * FROM students WHERE '+where+' ORDER BY CASE WHEN hemis_id=? THEN 0 ELSE 1 END,full_name,hemis_id LIMIT 21',tuple('%'+token+'%' for token in tokens)+(query.strip(),)).fetchall()
    return {'students':[dict(r) for r in rows[:20]],'more':len(rows)>20}


def audit(db, actor, action, detail):
    db.execute('INSERT INTO audit(actor_id,action,detail,created_at) VALUES (?,?,?,?)',
               (actor['id'] if actor else None, action, json.dumps(detail, ensure_ascii=False), now()))


def record(db, request_id, actor, action, detail):
    detail = json.dumps(detail, ensure_ascii=False)
    db.execute('INSERT INTO history(request_id,actor_id,action,detail,created_at) VALUES (?,?,?,?,?)',
               (request_id, actor['id'] if actor else None, action, detail, now()))
    audit(db, actor, action, {'request_id': request_id, 'detail': json.loads(detail)})


def notify(db, user_id, request_id, message):
    if user_id:
        db.execute('INSERT INTO notifications(user_id,request_id,message,created_at) VALUES (?,?,?,?)',
                   (user_id, request_id, message, now()))


def visible(user, row, db):
    role = user['role']
    return (role in ('admin', 'director') or row['manager_id'] == user['id'] or
            row['assignee_id'] == user['id'] or
            (role == 'manager' and row['manager_id'] is None and row['channel'] == 'kiosk' and db.execute('SELECT 1 FROM tickets WHERE id=? AND target_operator=?',(row['ticket_id'],user['operator'])).fetchone() is not None) or
            (role == 'head' and row['department'] == user['department']))


def serialize(db, row):
    result = dict(row)
    result['number'] = f"NAV-{row['id']:04d}"
    ticket=db.execute('SELECT prefix,queue_seq,target_operator FROM tickets WHERE id=?',(row['ticket_id'],)).fetchone() if row['ticket_id'] else None
    result['queue_number']=routing.code(ticket) if ticket else None
    result['queue_prefix']=ticket['prefix'] if ticket else None
    result['queue_seq']=ticket['queue_seq'] if ticket else None
    result['target_operator']=ticket['target_operator'] if ticket else None
    result['student'] = student(db, row['student_id']) if row['student_id'] else None
    for key in ('manager', 'assignee'):
        who = db.execute('SELECT full_name FROM users WHERE id=?', (row[key + '_id'],)).fetchone()
        result[key + '_name'] = who['full_name'] if who else None
    import attachments
    result['attachments'] = attachments.list_for(db, row['id'])
    result['history'] = [dict(i) for i in db.execute(
        "SELECT h.id,COALESCE(u.full_name,'Kiosk') actor,h.action,h.detail,h.created_at FROM history h "
        'LEFT JOIN users u ON u.id=h.actor_id WHERE request_id=? ORDER BY h.id', (row['id'],))]
    return result


def requests(db, user):
    return [serialize(db, r) for r in db.execute('SELECT * FROM requests WHERE deleted_at IS NULL ORDER BY id DESC') if visible(user, r, db)]


def get_request(db, user, request_id):
    if type(request_id) is not int:
        raise Problem('Ariza raqamini tekşiring')
    row = db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
    if not row or row['deleted_at'] is not None:
        raise Problem('Ariza topilmadi', 404)
    if not visible(user, row, db):
        raise Problem('Bu ariza uçun vakolat yöq', 403)
    return row


def kiosk_request(db, ticket, content):
    existing = db.execute('SELECT id FROM requests WHERE ticket_id=?', (ticket['id'],)).fetchone()
    if existing:
        return existing['id']
    stamp = ticket['created_at'] or now()
    rid = db.execute('INSERT INTO requests(ticket_id,lang,section,service,content,channel,created_at,updated_at) '
                     "VALUES (?,?,?,?,?,'kiosk',?,?)",
                     (ticket['id'], ticket['lang'], ticket['section'], ticket['service'], content, stamp, stamp)).lastrowid
    record(db, rid, None, 'created', {'channel': 'kiosk', 'ticket_id': ticket['id'], 'queue_code': routing.code(ticket), 'content': content})
    return rid


def deadline(value):
    if not isinstance(value, str) or not value or len(value) > 50:
        raise Problem('Muddatni sana va soat bilan kiriting')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ValueError()
        return dt.astimezone(timezone.utc).isoformat(timespec='seconds')
    except ValueError:
        raise Problem('Muddat vaqt mintaqasi bilan berilişi kerak')


def owner(user, row):
    if user['role'] != 'admin' and not (user['role'] == 'manager' and row['manager_id'] in (None, user['id'])):
        raise Problem('Faqat mas’ul menejer bajara oladi', 403)


def request_action(db, user, data):
    row = get_request(db, user, data.get('id'))
    if type(data.get('version')) is not int or data['version'] != row['version']:
        raise Problem('Ariza özgargan. Yangilab qayta urinib köring', 409)
    action = data.get('action')
    if row['status'] == 'closed':
        raise Problem('Yopilgan arizani özgartirib bölmaydi', 409)
    values = {}
    detail = {}
    if action in ('update', 'assign', 'resolve'):
        owner(user, row)
        if row['status'] == 'pending_approval':
            raise Problem('Ariza tasdiqda', 409)
        values['manager_id'] = row['manager_id'] or user['id']
    if action == 'update':
        if row['status'] == 'in_progress' and row['assignee_id'] not in (None, user['id']):
            raise Problem('Ijrodagi arizani avval mas’ul qaytarişi kerak', 409)
        sid = text(data, 'hemis_id', 20, True)
        if not student(db, sid):
            raise Problem('Talaba topilmadi', 404)
        values.update(student_id=sid, content=text(data, 'content', required=True), note=text(data, 'note'))
        detail = {'student_id': sid, 'content': values['content'], 'note': values['note']}
    elif action == 'assign':
        if not row['student_id']:
            raise Problem('Avval talabani biriktiring')
        target_id = data.get('assignee_id')
        if type(target_id) is not int:
            raise Problem('Mas’ulni tanlang')
        target = db.execute("SELECT * FROM users WHERE id=? AND role IN ('manager','executor','head','director','admin')", (target_id,)).fetchone()
        if not target:
            raise Problem('Mas’ul topilmadi')
        if row['deadline']:
            reason = text(data, 'reason', 1000, True)
            due, internal, legal = row['deadline'], row['internal_basis'], row['legal_basis']
        else:
            reason = text(data, 'reason', 1000)
            due = deadline(data.get('deadline'))
            if due <= now():
                raise Problem('Yangi muddat kelajakda bölişi kerak')
            internal = text(data, 'internal_basis', 2000, True)
            legal = text(data, 'legal_basis', 2000)
        values.update(assignee_id=target_id, department=target['department'], deadline=due,
                      internal_basis=internal, legal_basis=legal, status='in_progress')
        detail = {'assignee_id': target_id, 'department': target['department'], 'deadline': due,
                  'internal_basis': internal, 'legal_basis': legal, 'reason': reason}
        notify(db, target_id, row['id'], 'Yangi murojaat biriktirildi')
    elif action in ('return', 'submit'):
        if row['assignee_id'] != user['id']:
            raise Problem('Faqat joriy ijroçi bajara oladi', 403)
        if row['status'] != 'in_progress':
            raise Problem('Ariza ijroda emas', 409)
        if action == 'return':
            reason = text(data, 'reason', 1000, True)
            values.update(status='returned', unresolved_reason=reason)
            detail = {'reason': reason, 'deadline': row['deadline']}
            notify(db, row['manager_id'], row['id'], 'Murojaat sabab bilan qaytarildi')
        else:
            answer = text(data, 'answer', 10000, True)
            values.update(status='pending_approval', answer=answer, answered_at=now())
            detail = {'answer': answer}
            for head in db.execute("SELECT id FROM users WHERE role IN ('head','admin') AND (department=? OR role='admin')", (row['department'],)):
                notify(db, head['id'], row['id'], 'Javob tasdiq uçun yuborildi')
    elif action in ('approve', 'correct'):
        need(user, ('head', 'admin'))
        if user['role'] != 'admin' and user['department'] != row['department']:
            raise Problem('Bölim uçun vakolat yöq', 403)
        if row['status'] != 'pending_approval':
            raise Problem('Ariza tasdiqqa yuborilmagan', 409)
        if action == 'approve':
            if not row['answer']:
                raise Problem('Javob kiritilmagan')
            result = text(data, 'result', 4000, True)
            values.update(status='closed', closed_at=now(), result=result, unresolved_reason='')
            detail = {'result': result}
            notify(db, row['manager_id'], row['id'], 'Ariza tasdiqlandi va yopildi')
        else:
            reason = text(data, 'reason', 1000, True)
            values.update(status='in_progress', unresolved_reason=reason)
            detail = {'reason': reason}
            notify(db, row['assignee_id'], row['id'], 'Javob tuzatiş uçun qaytarildi')
    elif action == 'resolve':
        if row['status'] == 'in_progress' and row['assignee_id'] not in (None, user['id']):
            raise Problem('Mas’ulga yuborilgan ariza tasdiq orqali yopiladi', 409)
        if not row['student_id']:
            raise Problem('Avval talabani biriktiring')
        answer, result = text(data, 'answer', 10000, True), text(data, 'result', 4000, True)
        values.update(status='closed', answer=answer, result=result, answered_at=now(), closed_at=now(), unresolved_reason='')
        detail = {'answer': answer, 'result': result}
    elif action == 'deadline':
        need(user, ('head', 'admin'))
        if user['role'] == 'head' and row['department'] != user['department']:
            raise Problem('Bölim uçun vakolat yöq', 403)
        due = deadline(data.get('deadline'))
        reason = text(data, 'reason', 1000, True)
        internal = text(data, 'internal_basis', 2000, True)
        legal = text(data, 'legal_basis', 2000)
        detail = {'old_deadline': row['deadline'], 'new_deadline': due, 'reason': reason,
                  'old_internal_basis': row['internal_basis'], 'new_internal_basis': internal,
                  'old_legal_basis': row['legal_basis'], 'new_legal_basis': legal}
        values.update(deadline=due, internal_basis=internal, legal_basis=legal)
        notify(db, row['assignee_id'], row['id'], 'Ariza muddati özgardi')
        notify(db, row['manager_id'], row['id'], 'Ariza muddati özgardi')
    else:
        raise Problem('Noma’lum amal')
    values.update(updated_at=now(), version=row['version'] + 1)
    db.execute('UPDATE requests SET ' + ','.join(k + '=?' for k in values) + ' WHERE id=?', (*values.values(), row['id']))
    record(db, row['id'], user, action, detail)
    return serialize(db, db.execute('SELECT * FROM requests WHERE id=?', (row['id'],)).fetchone())


def phone_request(db, user, data, catalog):
    need(user, ('admin', 'manager'))
    key = str(UUID(data.get('key', '')))
    existing = db.execute('SELECT * FROM requests WHERE external_key=?', ('phone:' + key,)).fetchone()
    if existing:
        if existing['deleted_at'] is not None:
            raise Problem('Öçirilgan murojaatni qayta yaratib bölmaydi',409)
        if existing['manager_id'] != user['id']:
            raise Problem('Takror sörov kaliti', 409)
        return serialize(db, existing)
    section, service, lang = selection(data, catalog)
    sid = text(data, 'hemis_id', 20, True)
    if not student(db, sid):
        raise Problem('Talaba topilmadi', 404)
    if data.get('channel') != 'phone' or data.get('identity_confirmed') is not True:
        raise Problem('Telefon murojaati uçun şaxs tasdiği zarur')
    content, note = text(data, 'content', required=True), text(data, 'note')
    stamp = now()
    rid = db.execute('INSERT INTO requests(external_key,student_id,lang,section,service,content,note,channel,manager_id,department,created_at,updated_at) '
                     "VALUES (?,?,?,?,?,?,?,'phone',?,?,?,?)", ('phone:' + key, sid, lang, section, service, content, note,
                     user['id'], user['department'], stamp, stamp)).lastrowid
    record(db, rid, user, 'created', {'channel': 'phone', 'identity_confirmed': True})
    return serialize(db, db.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone())


def selection(data, catalog):
    lang, section, service = (data.get(k) for k in ('lang', 'section', 'service'))
    if lang not in ('uz', 'ru', 'en') or type(section) is not int or type(service) is not int:
        raise Problem('Tanlovni tekşiring')
    if not 0 <= section < len(catalog) or not 0 <= service < len(catalog[section][1]):
        raise Problem('Tanlovni tekşiring')
    return section, service, lang


def import_students(db, user, data):
    need(user, ('admin',))
    rows = data.get('students')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise Problem('1–10000 ta talaba yozuvi yuboring')
    added = updated = 0
    seen = set()
    for item in rows:
        if not isinstance(item, dict):
            raise Problem('Talaba maydonlarini tekşiring')
        sid = validate_id(item.get('hemis_id'))
        if sid in seen:
            raise Problem('Faylda takror HEMIS ID bor')
        seen.add(sid)
        course = item.get('course')
        if type(course) is not int or not 1 <= course <= 8:
            raise Problem('Kurs 1–8 oraliğida bölişi kerak')
        fields = [text(item, k, 250, True) for k in ('full_name', 'faculty', 'programme', 'student_group', 'education_form')]
        status = text(item, 'status', 50) or 'active'
        if student(db, sid):
            updated += 1
        else:
            added += 1
        db.execute('INSERT INTO students(hemis_id,full_name,faculty,programme,course,student_group,education_form,status) VALUES (?,?,?,?,?,?,?,?) '
                   'ON CONFLICT(hemis_id) DO UPDATE SET full_name=excluded.full_name,faculty=excluded.faculty,programme=excluded.programme,'
                   'course=excluded.course,student_group=excluded.student_group,education_form=excluded.education_form,status=excluded.status',
                   (sid, fields[0], fields[1], fields[2], course, fields[3], fields[4], status))
    audit(db, user, 'students_import', {'added': added, 'updated': updated})
    return {'added': added, 'updated': updated}


def report(db, user, query):
    need(user, ('admin', 'head', 'director'))
    rows = requests(db, user)
    def param(k):
        return query.get(k, [''])[0]
    for key in ('from', 'to'):
        value = param(key)
        if value:
            try:
                datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                raise Problem('Sana YYYY-MM-DD formatida bölişi kerak')
    if param('from') and param('to') and param('from') > param('to'):
        raise Problem('Sana oraliğini tekşiring')
    rows = [r for r in rows if (not param('from') or r['created_at'][:10] >= param('from')) and
            (not param('to') or r['created_at'][:10] <= param('to')) and all(
            not param(k) or str(r[k]) == param(k) for k in ('department', 'channel', 'status', 'manager_id', 'section', 'service'))]
    stamp = now()
    def overdue(r):
        return bool(r['deadline'] and r['status'] != 'closed' and r['deadline'] < stamp)
    summary = {'total': len(rows), 'in_progress': sum(r['status'] != 'closed' for r in rows),
               'overdue': sum(overdue(r) for r in rows), 'closed': sum(r['status'] == 'closed' for r in rows),
               'on_time': sum(r['status'] == 'closed' and bool(r['deadline']) and r['closed_at'] <= r['deadline'] for r in rows)}
    departments = []
    for dept in sorted(set(r['department'] or 'Biriktirilmagan' for r in rows)):
        members = [r for r in rows if (r['department'] or 'Biriktirilmagan') == dept]
        departments.append({'department': dept, 'total': len(members), 'closed': sum(r['status'] == 'closed' for r in members),
                            'overdue': sum(overdue(r) for r in members)})
    daily = [{'date': d, 'total': sum(r['created_at'][:10] == d for r in rows)} for d in sorted(set(r['created_at'][:10] for r in rows))]
    return {'summary': summary, 'departments': departments, 'daily': daily, 'requests': rows}


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY, ticket_id INTEGER UNIQUE, external_key TEXT UNIQUE,
            student_id TEXT, lang TEXT NOT NULL, section INTEGER NOT NULL, service INTEGER NOT NULL,
            content TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', channel TEXT NOT NULL,
            manager_id INTEGER, assignee_id INTEGER, department TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new', deadline TEXT, internal_basis TEXT NOT NULL DEFAULT '',
            legal_basis TEXT NOT NULL DEFAULT '', answer TEXT NOT NULL DEFAULT '', result TEXT NOT NULL DEFAULT '',
            unresolved_reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            answered_at TEXT, closed_at TEXT, template_version INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL, actor_id INTEGER,
            action TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, request_id INTEGER NOT NULL,
            message TEXT NOT NULL, read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY, actor_id INTEGER, action TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS request_assignee ON requests(assignee_id,status);
        CREATE INDEX IF NOT EXISTS request_manager ON requests(manager_id,status);
        CREATE INDEX IF NOT EXISTS notification_user ON notifications(user_id,read);
    ''')
    if 'deleted_at' not in {row['name'] for row in db.execute('PRAGMA table_info(requests)')}:
        db.execute('ALTER TABLE requests ADD COLUMN deleted_at TEXT')
