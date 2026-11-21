import argparse
import base64
import binascii
import copy
import csv
import io
import json
import logging
import os
import hashlib
import re
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4
import auth
import routing
import branding
import profile_photo
import account_admin
import student_registry
import security_monitor
import student_xlsx
import request_delete
import attachments
import audio_store
import excel
import integrations
import telegram_bot
import telegram_mini
import kiosk_printer
import service_access
import workflow as w

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
LANGUAGES = ('uz', 'ru', 'en')
DATABASE = ROOT / 'navbot.sqlite3'
DEFAULT_SETTINGS = {
    'university': ['Alişer Navoiy nomidagi Toşkent davlat özbek tili va adabiyoti universiteti',
                   'Ташкентский государственный университет узбекского языка и литературы имени Алишера Навои',
                   'Alisher Navo’i Tashkent State University of Uzbek Language and Literature'],
    'office': ['Registrator ofisi', 'Офис регистратора', 'Registrar’s Office'],
    'tv_language': 'uz', 'warning_hours': 24, 'volume': 0.75, 'blink_count': 3,
    'tv_titles': [['Hozir çaqirilmoqda', 'Xizmat körsatilmoqda', 'Kutilayotgan navbatlar'],
                  ['Сейчас вызывается', 'Обслуживаются', 'Ожидают'], ['Now calling', 'Now serving', 'Waiting']],
    'operator_labels': {},
    'voice_templates': ['{navbat}. Iltimos, {operator}-operator oynasiga öting.',
                        'Номер {navbat}, подойдите к окну номер {operator}.',
                        'Ticket {navbat}, please proceed to counter {operator}.'],
    'receipt_footer': ['Navbatingizni TVda kuzating', 'Следите за очередью на экране', 'Watch the queue display'],
    'section_routes': routing.DEFAULT_ROUTES,
    'branding': {'system_logo': None, 'kiosk_logo': None, 'icons': {}},
    'catalog': CATALOG, 'hidden_services': [], 'section_logos': [None] * 5,
}


def connection():
    db = sqlite3.connect(DATABASE, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def settings(db):
    row = db.execute('SELECT value FROM settings WHERE id=1').fetchone()
    result = copy.deepcopy(DEFAULT_SETTINGS)
    if row:
        result.update(json.loads(row['value']))
    return result


def save_settings(db, user, data):
    w.need(user, ('admin',))
    incoming = data.get('settings')
    if not isinstance(incoming, dict) or not incoming or set(incoming) - set(DEFAULT_SETTINGS):
        raise w.Problem('Sozlama maydonlarini tekşiring')
    result = settings(db)
    result.update(incoming)
    def translations(value):
        return isinstance(value, list) and len(value) == 3 and all(isinstance(s, str) and 0 < len(s) <= 1000 for s in value)
    for key in ('university', 'office', 'receipt_footer', 'voice_templates'):
        if not translations(result[key]):
            raise w.Problem(key + ': uçta tarjima zarur')
    if result['tv_language'] not in LANGUAGES:
        raise w.Problem('TV tilini tanlang')
    if type(result['warning_hours']) is not int or not 1 <= result['warning_hours'] <= 720:
        raise w.Problem('Ogohlantiriş 1–720 soat oraliğida')
    if type(result['blink_count']) is not int or not 0 <= result['blink_count'] <= 5:
        raise w.Problem('Miltillaş soni 0–5 oraliğida')
    if type(result['volume']) not in (int, float) or not 0 <= result['volume'] <= 1:
        raise w.Problem('Ovoz darajasi 0–1 oraliğida')
    if not isinstance(result['tv_titles'], list) or len(result['tv_titles']) != 3 or not all(translations(v) for v in result['tv_titles']):
        raise w.Problem('TV sarlavhalarini tekşiring')
    labels = result['operator_labels']
    if not isinstance(labels, dict) or any(str(k) not in map(str, range(1, 31)) or not translations(v) for k, v in labels.items()):
        raise w.Problem('Operator yorliqlarini tekşiring')
    if result['branding'] != settings(db)['branding']:
        raise w.Problem('Logotip faylini yuklaş tugmasidan foydalaning')
    if result['section_logos'] != settings(db)['section_logos']:
        raise w.Problem('Logo faylini yuklaş tugmasidan foydalaning')
    if not routing.valid(result['section_routes']):
        raise w.Problem('5 ta bölimga takrorlanmaydigan harf va operator biriktiring')
    catalog = result['catalog']
    if not isinstance(catalog, list) or len(catalog) != len(CATALOG):
        raise w.Problem('Hozir 5 ta bölim saqlanişi kerak')
    for section in catalog:
        if not isinstance(section, list) or len(section) != 2 or not translations(section[0]) or not isinstance(section[1], list) or len(section[1]) != 5 or not all(translations(s) for s in section[1]):
            raise w.Problem('Katalog 5×5 va uç tilda bölişi kerak')
    hidden = result['hidden_services']
    if not isinstance(hidden, list) or any(i not in [f'{a}:{b}' for a in range(5) for b in range(5)] for i in hidden):
        raise w.Problem('Yashirilgan xizmatlar ro‘yxatini tekşiring')
    for template in result['voice_templates']:
        try:
            template.format(navbat='A-001', operator=1)
        except (KeyError, ValueError, IndexError, AttributeError):
            raise w.Problem('Ovoz şablonida faqat {navbat} va {operator} ishlating')
    db.execute('INSERT INTO settings(id,value) VALUES (1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value', (json.dumps(result, ensure_ascii=False),))
    w.audit(db, user, 'settings_update', {'fields': list(incoming)})
    return {'settings': result}


def snapshot(db, operator):
    # Public data is deliberately restricted: no student, request, notes, or staff names.
    items = [routing.public_ticket(row) for row in db.execute(
        "SELECT t.id,t.lang,t.section,t.service,t.status,t.operator,t.called,t.prefix,t.queue_seq,t.target_operator,t.queue_day FROM tickets t WHERE t.status!=? AND (t.status!='waiting' OR NOT EXISTS(SELECT 1 FROM requests r WHERE r.ticket_id=t.id AND (r.status='closed' OR r.deleted_at IS NOT NULL))) ORDER BY t.id", ('done',))]
    called = max((i for i in items if i['status'] == 'called'), key=lambda i: i['called'] or 0, default=None)
    return {'waiting': [i for i in items if i['status'] == 'waiting'],
            'serving': sorted((i for i in items if i['status'] == 'serving'), key=lambda i: i['operator']),
            'current': called, 'desk': next((i for i in items if i['operator'] == operator), None)}


def mutate(db, path, data, user):
    config = settings(db)
    if path == '/api/ticket':
        key = str(UUID(data.get('key', '')))
        section, service, lang = w.selection(data, config['catalog'])
        if kiosk_printer.mode(db)=='agent' and data.get('print_capability')!='native-v1':
            raise w.Problem('Kiosk oynasini yopib, yangi ishga tushirish fayli bilan qayta oching',409)
        existing = db.execute('SELECT * FROM tickets WHERE request_key=?', (key,)).fetchone()
        if existing:
            if (existing['lang'], existing['section'], existing['service']) != (lang, section, service):
                raise w.Problem('Sörov kaliti boşqa tanlov uçun ishlatilgan', 409)
            if db.execute('SELECT 1 FROM requests WHERE ticket_id=? AND deleted_at IS NOT NULL',(existing['id'],)).fetchone():
                raise w.Problem('Öçirilgan murojaatni qayta yaratib bölmaydi',409)
            ticket = dict(existing)
        else:
            kiosk_printer.ensure_ready(db)
            if f'{section}:{service}' in config['hidden_services']:
                raise w.Problem('Xizmat vaqtinça mavjud emas', 409)
            route = routing.for_section(config['section_routes'], section)
            stamp=w.now();day=routing.queue_day(stamp)
            sequence = db.execute('SELECT COALESCE(MAX(queue_seq),0)+1 FROM tickets WHERE prefix=? AND queue_day=?', (route['prefix'],day)).fetchone()[0]
            db.execute('INSERT INTO tickets(request_key,lang,section,service,created_at,content_name,prefix,queue_seq,target_operator,queue_day) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (key, lang, section, service, stamp, config['catalog'][section][1][service][LANGUAGES.index(lang)],route['prefix'],sequence,route['operator'],day))
            ticket = dict(db.execute('SELECT * FROM tickets WHERE request_key=?', (key,)).fetchone())
        w.kiosk_request(db, ticket, ticket['content_name'])
        print_result=kiosk_printer.enqueue(db,ticket,config)
        return {k: ticket[k] for k in ('id', 'lang', 'section', 'service', 'created_at','prefix','queue_seq','target_operator','queue_day')} | {'content': ticket['content_name'],'code':routing.code(ticket),**print_result}
    w.need(user, auth.ROLES)
    if path == '/api/manager-service':
        return service_access.change(db,user,data)
    service_access.enforce(db,user,path)
    if path == '/api/admin/kiosk-printer':
        return kiosk_printer.configure(db,user,data)
    if path == '/api/telegram/mini-config':
        return telegram_mini.save_config(db,user,data)
    if path == '/api/telegram/code':
        return telegram_bot.issue_code(db,user,data)
    if path == '/api/telegram/unlink':
        return telegram_bot.unlink(db,user,data)
    if path == '/api/telegram/retry':
        return telegram_bot.retry(db,user,data)
    if path == '/api/security/unblock':
        return security_monitor.unblock(db,user,data,w.REQUEST_CONTEXT.get())
    if path == '/api/admin/students/status':
        return student_registry.set_status(db, user, data)
    if path == '/api/admin/students/preview':
        return student_registry.preview(db, user, data)
    if path == '/api/admin/user/action':
        return account_admin.change(db, user, data)
    if path == '/api/profile/photo':
        return profile_photo.update(db, user, data)
    if path == '/api/attachment/upload':
        return attachments.upload(db, user, data)
    if path == '/api/admin/integrations':
        response = integrations.save(db, user, data)
        w.audit(db, user, 'integration_save', {'kind': data.get('kind')})
        return response
    if path == '/api/admin/audio/install-pack':
        return audio_store.install_pack(db,user)
    if path == '/api/admin/audio/upload':
        return audio_store.upload(db, user, data)
    if path == '/api/admin/audio/delete':
        return audio_store.remove(db, user, data)
    if path == '/api/admin/audio/settings':
        return audio_store.set_mode(db, user, data)
    if path == '/api/students/search':
        return w.search_students(db, data.get('query'))
    if path == '/api/student':
        return {'student': w.student(db, data.get('hemis_id')), 'source': 'local'}
    if path == '/api/request/create':
        return {'request': w.phone_request(db, user, data, config['catalog'])}
    if path == '/api/request/action':
        return {'request': w.request_action(db, user, data)}
    if path == '/api/students/import-xlsx':
        return student_xlsx.upload(db, user, data)
    if path == '/api/students/import':
        return w.import_students(db, user, data)
    if path == '/api/admin/branding':
        return branding.update(db, user, data, config)
    if path == '/api/admin/logo':
        w.need(user, ('admin',))
        section, mime = data.get('section'), data.get('mime')
        if data.get('remove') is True:
            if type(section) is not int or not 0 <= section < 5:
                raise w.Problem('Bölim va PNG/JPG formatini tekşiring')
            config['section_logos'][section] = None
            db.execute('INSERT INTO settings(id,value) VALUES (1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value', (json.dumps(config, ensure_ascii=False),))
            w.audit(db, user, 'section_logo_delete', {'section': section})
            return {'settings': config}
        if type(section) is not int or not 0 <= section < 5 or mime not in ('image/png', 'image/jpeg'):
            raise w.Problem('Bölim va PNG/JPG formatini tekşiring')
        try:
            raw = base64.b64decode(data.get('data', ''), validate=True)
        except (ValueError, TypeError, binascii.Error):
            raise w.Problem('Rasm fayli buzilgan')
        if not 0 < len(raw) <= 2 * 1024 * 1024:
            raise w.Problem('Rasm 2 MBdan oşmasligi kerak')
        if (mime == 'image/png' and not raw.startswith(b'\x89PNG\r\n\x1a\n')) or (mime == 'image/jpeg' and not raw.startswith(b'\xff\xd8\xff')):
            raise w.Problem('Rasm formati fayl bilan mos emas')
        config['section_logos'][section] = 'data:' + mime + ';base64,' + base64.b64encode(raw).decode('ascii')
        db.execute('INSERT INTO settings(id,value) VALUES (1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value', (json.dumps(config, ensure_ascii=False),))
        w.audit(db, user, 'section_logo_update', {'section': section, 'mime': mime, 'bytes': len(raw)})
        return {'settings': config}
    if path == '/api/admin/settings':
        return save_settings(db, user, data)
    if path in ('/api/admin/user', '/api/admin/reset'):
        w.need(user, ('admin',))
        if path.endswith('/user'):
            result = auth.create_user(db, data)
        else:
            result = auth.reset_password(db, data.get('user_id'), data.get('password'))
        w.audit(db, user, 'user_create' if path.endswith('/user') else 'password_reset', {'user_id': result['id']})
        return {'user': result}
    if path == '/api/notification/read':
        notification_id = data.get('id')
        if type(notification_id) is not int:
            raise w.Problem('Xabar raqamini tekşiring')
        db.execute('UPDATE notifications SET read=1 WHERE id=? AND user_id=?', (notification_id, user['id']))
        return {'ok': True}
    if path != '/api/action':
        raise w.Problem('Topilmadi', 404)
    w.need(user, ('admin', 'manager'))
    operator = data.get('operator')
    if type(operator) is not int or not 1 <= operator <= 30:
        raise w.Problem('Operator raqamini tekşiring')
    if user['role'] == 'manager' and user['operator'] != operator:
        raise w.Problem('Boşqa operator uçun vakolat yöq', 403)
    action = data.get('action')
    desk = db.execute("SELECT * FROM tickets WHERE operator=? AND status IN ('called','serving')", (operator,)).fetchone()
    expected=data.get('ticket_id')
    if action!='call' and expected is not None and (type(expected) is not int or not desk or expected!=desk['id']):
        raise w.Problem('Navbat o‘zgargan. Oynani yangilang.',409)
    if action=='no_show' and type(expected) is not int:
        raise w.Problem('Yopiladigan chekni tanlang',400)
    if action == 'call' and desk is None:
        ticket_id = data.get('ticket_id')
        if ticket_id is not None and type(ticket_id) is not int:
            raise w.Problem('Çek raqamini tekşiring')
        ticket = db.execute("SELECT t.* FROM tickets t JOIN requests r ON r.ticket_id=t.id WHERE t.status='waiting' AND r.deleted_at IS NULL AND r.status!='closed' AND (r.manager_id IS NULL OR r.manager_id=? OR ?) AND (? IS NULL OR t.id=?) ORDER BY t.id LIMIT 1", (user['id'],user['role']=='admin',ticket_id,ticket_id)).fetchone()
        if ticket is None:
            raise w.Problem('Navbat böş yoki çaqirilgan', 409)
        req = db.execute('SELECT * FROM requests WHERE ticket_id=?', (ticket['id'],)).fetchone()
        if req and req['manager_id'] not in (None, user['id']) and user['role'] != 'admin':
            raise w.Problem('Navbat boşqa menejerga biriktirilgan', 409)
        db.execute("UPDATE tickets SET status='called',operator=? WHERE id=?", (operator, ticket['id']))
        if req:
            db.execute("UPDATE requests SET manager_id=COALESCE(manager_id,?),department=CASE WHEN department='' THEN ? ELSE department END,version=version+1,updated_at=? WHERE id=?",
                       (user['id'],user['department'], w.now(), req['id']))
            w.record(db, req['id'], user, 'call', {'operator': operator,'queue_code':routing.code(ticket)})
        desk = ticket
    elif not desk or action == 'call':
        raise w.Problem('Operator holati özgargan', 409)
    elif action == 'no_show' and desk['status'] == 'called':
        req=db.execute('SELECT * FROM requests WHERE ticket_id=?',(desk['id'],)).fetchone()
        if not req or req['status']!='new' or req['assignee_id'] is not None or req['deleted_at'] is not None:
            raise w.Problem('Bu murojaat bo‘yicha ish boshlangan. Kelmadi deb yopib bo‘lmaydi.',409)
        db.execute("UPDATE tickets SET status='done' WHERE id=?",(desk['id'],))
        db.execute("UPDATE requests SET status='closed',closed_at=?,result=?,unresolved_reason=? WHERE id=?",(w.now(),'Talaba kelmadi','Chaqiruvga kelmadi',req['id']))
    elif action == 'start' and desk['status'] == 'called':
        db.execute("UPDATE tickets SET status='serving' WHERE id=?", (desk['id'],))
    elif action == 'finish' and desk['status'] == 'serving':
        db.execute("UPDATE tickets SET status='done' WHERE id=?", (desk['id'],))
    elif action != 'recall' or desk['status'] != 'called':
        raise w.Problem('Bu amal joriy holatda bajarilmaydi', 409)
    if action in ('call', 'recall'):
        event = db.execute('INSERT INTO calls(ticket,operator,lang) VALUES (?,?,?)', (desk['id'], operator, desk['lang'])).lastrowid
        db.execute('UPDATE tickets SET called=? WHERE id=?', (event, desk['id']))
    if action != 'call':
        req = db.execute('SELECT id FROM requests WHERE ticket_id=?', (desk['id'],)).fetchone()
        if req:
            db.execute('UPDATE requests SET version=version+1,updated_at=? WHERE id=?', (w.now(), req['id']))
            w.record(db, req['id'], user, 'queue_' + action, {'operator': operator,'queue_code':routing.code(desk),**({'reason':'Chaqiruvga kelmadi'} if action=='no_show' else {})})
    return snapshot(db, operator)


class Handler(BaseHTTPRequestHandler):
    server_version = 'NAVBOT'

    def send_response(self, code, message=None):
        self._response_status=code
        return super().send_response(code,message)

    def _audited(self, operation):
        self._audit_user=None
        self._response_status=500
        self._audit_context={'ip':security_monitor.client_ip(self.client_address[0],self.headers),'path':security_monitor.clean(urlsplit(self.path).path,500),'method':self.command,'request_ref':uuid4().hex,'user_agent':security_monitor.clean(self.headers.get('User-Agent',''))}
        context_token=w.REQUEST_CONTEXT.set(self._audit_context)
        try:
            with closing(connection()) as db:
                self._audit_user=self.user(db)
                denied=security_monitor.gate(db,self._audit_context,self._audit_user)
            if denied:
                return self.reply({'error':'IP vaqtincha bloklangan' if denied==429 else 'Sörov rad etildi'},denied)
            return operation()
        finally:
            try:
                with closing(connection()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    security_monitor.record(db,self._audit_context,self._audit_user,self._response_status)
            except sqlite3.Error:
                logging.warning('Security audit persistence failed; check database and disk')
            finally:
                w.REQUEST_CONTEXT.reset(context_token)

    def do_GET(self):
        return self._audited(self._do_GET)

    def do_POST(self):
        return self._audited(self._do_POST)

    def do_HEAD(self):
        return self._audited(lambda:self.reply({'error':'Usul qöllanmaydi'},405))

    do_PUT=do_PATCH=do_DELETE=do_OPTIONS=do_HEAD

    def version_string(self):
        return self.server_version

    def log_message(self, format, *args):
        # Do not write ID searches or request contents into access logs.
        logging.info('%s %s', self.command, urlsplit(self.path).path)

    def send_body(self, body, mime, status=200, cookie=None, filename=None):
        if hasattr(self,'_audit_context'):
            self._audit_context['response_bytes']=len(body)
            if filename:self._audit_context['filename']=security_monitor.clean(filename)
            elif mime=='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':self._audit_context['filename']='NavBoT-report.xlsx'
            elif mime.startswith('text/csv'):self._audit_context['filename']='NavBoT-report.csv'
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        mini_page=urlsplit(self.path).path=='/student' and mime.startswith('text/html')
        if not mini_page:self.send_header('X-Frame-Options', 'DENY')
        # Only the trusted static page's exact inline scripts are allowed. User
        # text is JSON/escaped DOM content, never an HTML response template.
        script_sources = ["'self'"]
        if mime.split(';', 1)[0] == 'text/html':
            for script in re.findall(rb'<script>(.*?)</script>', body, re.DOTALL):
                # HTML normalizes CRLF/CR before executing script text.
                script = script.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                digest = base64.b64encode(hashlib.sha256(script).digest()).decode('ascii')
                script_sources.append("'sha256-" + digest + "'")
        if mini_page:script_sources.append('https://telegram.org')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src " + ' '.join(script_sources) + "; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-src 'none'; frame-ancestors " + ("https://web.telegram.org https://*.web.telegram.org" if mini_page else "'none'") + "; base-uri 'none'; form-action 'self'")
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        if cookie is not None:
            self.send_header('Set-Cookie', cookie)
        if filename is not None:
            from urllib.parse import quote
            self.send_header('Content-Disposition', "attachment; filename=download; filename*=UTF-8''" + quote(filename, safe=''))
        elif mime == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            self.send_header('Content-Disposition', 'attachment; filename="NavBoT-report.xlsx"')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def reply(self, value, status=200, cookie=None):
        self.send_body(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8'), 'application/json; charset=utf-8', status, cookie)

    def user(self, db):
        user = auth.current(db, self.headers.get('Cookie', ''))
        if hasattr(self,'_audit_context'):self._audit_user=user
        if user:
            user['avatar_url'] = profile_photo.url(db, user)
            user['service_block']=service_access.status(db,user['id'])
        return user

    def guard(self, user, path):
        w.need(user, auth.ROLES)
        if user['must_change_password'] and path not in ('/api/me', '/api/password', '/api/logout'):
            raise w.Problem('Vaqtinçalik parolni profil orqali özgartiring', 403)

    def _do_GET(self):
        url = urlsplit(self.path)
        try:
            if url.path in ('/', '/kiosk', '/operator', '/manager', '/tv', '/tablo', '/login', '/executor', '/head', '/director', '/admin', '/profile'):
                return self.send_body((ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            if url.path == '/api/tv-version':
                import hashlib
                return self.reply({'version':hashlib.sha256(b''.join((ROOT/name).read_bytes() for name in ('index.html','i18n.js','dashboard.js','dashboard.css'))).hexdigest()})
            if url.path == '/downloads/NAVBOT-TV.apk':
                return self.send_body((ROOT.parent/'downloads'/'NAVBOT-TV.apk').read_bytes(),'application/vnd.android.package-archive',filename='NAVBOT-TV.apk')
            if url.path == '/downloads/NAVBOT-NATIVE.zip':
                return self.send_body((ROOT.parent / 'downloads' / 'NAVBOT-NATIVE.zip').read_bytes(),'application/zip',filename='NAVBOT-NATIVE.zip')
            if url.path == '/student':
                return self.send_body((ROOT / 'student.html').read_bytes(),'text/html; charset=utf-8')
            mini_assets={'/assets/dashboard.js':('dashboard.js','text/javascript; charset=utf-8'),'/assets/dashboard.css':('dashboard.css','text/css; charset=utf-8'),'/assets/student.js':('student.js','text/javascript; charset=utf-8'),'/assets/student.css':('student.css','text/css; charset=utf-8'),'/assets/student-pattern.svg':('student-pattern.svg','image/svg+xml')}
            if url.path in mini_assets:
                name,mime=mini_assets[url.path]
                return self.send_body((ROOT / name).read_bytes(),mime)
            if url.path == '/assets/tv-tone.wav':
                return self.send_body((ROOT/'tv-tone.wav').read_bytes(),'audio/wav')
            if url.path == '/assets/i18n.js':
                return self.send_body((ROOT / 'i18n.js').read_bytes(), 'text/javascript; charset=utf-8')
            with closing(connection()) as db:
                db.execute('BEGIN')
                if url.path == '/api/branding':
                    return self.reply(branding.targets())
                if url.path.startswith('/media/branding/'):
                    body, mime = branding.read(db, url.path.removeprefix('/media/branding/'))
                    return self.send_body(body, mime)
                if url.path == '/api/audio':
                    return self.reply(audio_store.metadata(db))
                if url.path == '/api/audio/plan':
                    q = parse_qs(url.query)
                    return self.reply(audio_store.plan(db, q.get('lang', ['uz'])[0], int(q.get('ticket', ['0'])[0]), int(q.get('operator', ['0'])[0]),q.get('prefix',['A'])[0]))
                if url.path.startswith('/media/audio/'):
                    body, mime = audio_store.read(db, url.path.removeprefix('/media/audio/'))
                    return self.send_body(body, mime)
                if url.path == '/api/catalog':
                    return self.reply(settings(db)['catalog'])
                if url.path == '/api/settings':
                    return self.reply({'settings': settings(db)})
                if url.path == '/api/state':
                    try:
                        operator, after = map(int, url.query.split(',') if url.query else ('0', '-1'))
                    except ValueError:
                        raise w.Problem('Notoğri parametr')
                    response = snapshot(db, operator)
                    response['last'] = db.execute('SELECT COALESCE(MAX(id),0) FROM calls').fetchone()[0]
                    response['events'] = [dict(row) for row in db.execute('SELECT c.*,t.prefix,t.queue_seq FROM calls c JOIN tickets t ON t.id=c.ticket JOIN requests r ON r.ticket_id=t.id WHERE c.id>? AND r.deleted_at IS NULL ORDER BY c.id', (after,))] if after >= 0 else []
                    return self.reply(response)
                user = self.user(db)
                if url.path == '/api/admin/users':
                    self.guard(user, url.path)
                    w.need(user, ('admin',))
                    return self.reply({'users': account_admin.users(db)})
                if url.path == '/api/me':
                    return self.reply({'user': user})
                self.guard(user, url.path)
                if url.path.startswith('/api/profile/photo/'):
                    body, mime = profile_photo.read(db, user, url.path.removeprefix('/api/profile/photo/'))
                    return self.send_body(body, mime)
                if url.path.startswith('/api/attachment/'):
                    body, mime, name = attachments.download(db, user, url.path.removeprefix('/api/attachment/'))
                    return self.send_body(body, mime, filename=name)
                if url.path == '/api/admin/kiosk-printer':
                    w.need(user,('admin',))
                    return self.reply(kiosk_printer.metadata(db))
                if url.path == '/api/telegram/mini-config':
                    w.need(user,('admin',))
                    return self.reply(telegram_mini.config(db))
                if url.path == '/api/telegram/student':
                    w.need(user,('admin','manager'))
                    sid=w.validate_id(parse_qs(url.query).get('hemis_id',[''])[0])
                    return self.reply(telegram_bot.status(db,sid))
                if url.path == '/api/telegram/request':
                    row=w.get_request(db,user,int(parse_qs(url.query).get('id',['0'])[0]))
                    return self.reply(telegram_bot.delivery(db,row['id']))
                if url.path == '/api/telegram/health':
                    w.need(user,('admin',))
                    return self.reply(telegram_bot.health(db))
                if url.path == '/api/manager-service':
                    return self.reply(service_access.managers(db,user))
                if url.path == '/api/users':
                    return self.reply({'users': auth.users(db)})
                if url.path == '/api/requests':
                    return self.reply({'requests': w.requests(db,user),'service_block':service_access.status(db,user['id'])})
                if url.path == '/api/students':
                    w.need(user, ('admin', 'head', 'director'))
                    return self.reply({'students': [dict(r) for r in db.execute('SELECT * FROM students ORDER BY full_name')]})
                if url.path == '/api/notifications':
                    return self.reply({'notifications': [dict(r) for r in db.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 200', (user['id'],))]})
                if url.path == '/api/integrations':
                    w.need(user, ('admin',))
                    return self.reply(integrations.metadata(db))
                if url.path == '/api/security/audit':
                    return self.reply(security_monitor.page(db,user,parse_qs(url.query)))
                if url.path == '/api/audit':
                    w.need(user, ('admin',))
                    return self.reply({'events': [dict(r) for r in db.execute("SELECT a.id,COALESCE(u.full_name,'Kiosk') actor,a.action,a.detail,a.created_at FROM audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 1000")]})
                if url.path in ('/api/report', '/api/report.csv', '/api/report.xlsx'):
                    report = w.report(db, user, parse_qs(url.query))
                    if url.path.endswith('.xlsx'):
                        query = parse_qs(url.query)
                        lang = query.get('lang', ['uz'])[0]
                        if lang not in LANGUAGES:
                            raise w.Problem('Tilni tekşiring')
                        period = ' — '.join(v for v in (query.get('from', [''])[0], query.get('to', [''])[0]) if v)
                        return self.send_body(excel.build(report, lang, period), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    if url.path.endswith('.csv'):
                        return self.send_body(report_csv(report).encode('utf-8-sig'), 'text/csv; charset=utf-8')
                    return self.reply(report)
                raise w.Problem('Topilmadi', 404)
        except (w.Problem, auth.AuthError, integrations.IntegrationError) as error:
            self.reply({'error': str(error)}, error.status)
        except (ValueError, TypeError, KeyError) as error:
            self.reply({'error': 'Sörov parametrlarini tekşiring'}, 400)

    def same_origin(self):
        origin = self.headers.get('Origin')
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise w.Problem('Boşqa saytdan sörov rad etildi', 403)
        if origin:
            parsed = urlsplit(origin)
            if parsed.scheme not in ('http', 'https') or parsed.netloc != self.headers.get('Host'):
                raise w.Problem('Boşqa saytdan sörov rad etildi', 403)
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            raise w.Problem('JSON sörov zarur', 415)

    def _do_POST(self):
        try:
            self.same_origin()
            length = int(self.headers.get('Content-Length', '0'))
            limit = 32768 if self.path == '/api/telegram/mini' else 16 * 1024 * 1024 if self.path == '/api/attachment/upload' else 8 * 1024 * 1024 if self.path in ('/api/admin/audio/upload','/api/students/import-xlsx') else 4 * 1024 * 1024
            if not 0 < length <= limit:
                raise w.Problem('Sörov hajmi belgilangan limitdan katta', 413)
            data = json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if not isinstance(data, dict):
                raise w.Problem('JSON obyekt yuboring')
            self._audit_context['request_bytes']=length
            self._audit_context['metadata']=security_monitor.metadata(data)
            upload_path='upload' in self.path or 'import' in self.path or self.path in ('/api/profile/photo','/api/admin/branding','/api/admin/logo')
            if upload_path and data.get('remove') is not True:
                filename=data.get('filename') or data.get('name')
                if isinstance(filename,str):self._audit_context['filename']=security_monitor.clean(filename)
                self._audit_context['category']='upload'
            if self.path in ('/api/students/search','/api/student'):
                # Lookups never reserve the sole SQLite writer slot.
                with closing(connection()) as db:
                    db.execute('PRAGMA query_only=ON')
                    db.execute('BEGIN')
                    user=self.user(db)
                    self.guard(user,self.path)
                    response=mutate(db,self.path,data,user)
                return self.reply(response)
            if self.path == '/api/kiosk-printer/status':
                with closing(connection()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    response=kiosk_printer.ticket_status(db,data)
                return self.reply(response)
            if self.path == '/api/kiosk-printer/agent':
                with closing(connection()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    response=kiosk_printer.agent(db,self.headers.get('Authorization',''),data)
                return self.reply(response)
            if self.path == '/api/telegram/mini':
                with closing(connection()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    response=telegram_mini.handle(db,data)
                if isinstance(response,tuple):
                    body,mime,name=response
                    return self.send_body(body,mime,filename=name)
                return self.reply(response)
            if self.path == '/api/login':
                self._audit_context['category']='login'
                if isinstance(data.get('username'),str):self._audit_context['username']=security_monitor.clean(data['username'],64)
                with closing(connection()) as db:
                    token, user = auth.login(db, data.get('username'), data.get('password'))
                    self._audit_user=user
                    with db:
                        w.audit(db, user, 'login', {})
                return self.reply({'user': user}, cookie=f'{auth.COOKIE_NAME}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={auth.SESSION_SECONDS}')
            if self.path in ('/api/admin/requests/delete','/api/admin/students/delete'):
                with closing(connection()) as db:
                    user = self.user(db)
                    self.guard(user, self.path)
                    w.need(user, ('admin',))
                    # Reuse persistent password-attempt limits on a dedicated connection.
                    # Revoke only the temporary verification session, keeping the browser session.
                    token, _ = auth.login(db, user['username'], data.get('password'))
                    auth.logout(db, auth.COOKIE_NAME + '=' + token)
                    db.commit()
                    with db:
                        db.execute('BEGIN IMMEDIATE')
                        user = self.user(db)
                        self.guard(user, self.path)
                        response = (student_registry.remove if self.path=='/api/admin/students/delete' else request_delete.remove)(db, user, data)
                return self.reply(response)
            if self.path in ('/api/admin/integrations/test', '/api/admin/integrations/sync'):
                with closing(connection()) as db, db:
                    user = self.user(db)
                    self.guard(user, self.path)
                    w.need(user, ('admin',))
                    if self.path.endswith('/test'):
                        response = integrations.test(db, user, data.get('kind'))
                        w.audit(db, user, 'integration_test', {'kind': data.get('kind')})
                    else:
                        students = integrations.fetch_students(db, user)
                        if students is None:
                            response = {'ok': False, 'integrations': integrations.metadata(db)}
                        else:
                            counts = w.import_students(db, user, {'students': students})
                            response = {'ok': True, **counts, 'integrations': integrations.mark_sync(db, user, counts['added'], counts['updated'])}
                return self.reply(response)
            cookie = None
            with closing(connection()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                user = self.user(db)
                if self.path != '/api/ticket':
                    self.guard(user, self.path)
                if self.path == '/api/logout':
                    auth.logout(db, self.headers.get('Cookie', ''))
                    response = {'ok': True}
                    cookie = f'{auth.COOKIE_NAME}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
                elif self.path == '/api/profile/role':
                    token, switched = auth.switch_role(db, self.headers.get('Cookie',''), data)
                    w.audit(db, user, 'role_switch', {'from':user['role'],'to':switched['role'],'context':switched['active_role']})
                    response={'user':switched}
                    cookie=f'{auth.COOKIE_NAME}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={auth.SESSION_SECONDS}'
                elif self.path == '/api/password':
                    auth.change_password(db, user, data.get('current_password'), data.get('new_password'))
                    w.audit(db, user, 'password_change', {})
                    response = {'ok': True}
                    cookie = f'{auth.COOKIE_NAME}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
                else:
                    response = mutate(db, self.path, data, user)
            if self.path == '/api/admin/integrations':
                with closing(connection()) as cleanup_db:
                    try:
                        integrations.cleanup(cleanup_db)
                    except (integrations.IntegrationError, OSError, sqlite3.Error):
                        logging.warning('Protected integration secret cleanup deferred')
            self.reply(response, cookie=cookie)
        except (w.Problem, auth.AuthError, integrations.IntegrationError) as error:
            self.reply({'error': str(error)}, error.status)
        except (TypeError, KeyError, ValueError, AttributeError, UnicodeError):
            self.reply({'error': 'Sörov maydonlarini tekşiring'}, 400)
        except sqlite3.IntegrityError:
            self.reply({'error': 'Yozuv özgargan yoki takrorlangan'}, 409)
        except sqlite3.OperationalError:
            logging.exception('Database operation failed')
            self.reply({'error': 'Baza band. Qayta urinib köring'}, 503)


def report_csv(report):
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['Sana', 'Ariza', 'Navbat', 'HEMIS ID', 'F.I.Sh.', 'Yo‘nalish', 'Kurs', 'Ta’lim shakli', 'Mazmun', 'Kanal', 'Menejer', 'Mas’ul', 'Bölim', 'Holat', 'Muddat', 'Ichki asos', 'Huquqiy asos', 'Javob', 'Natija', 'Hal etilmaganlik sababi', 'Javob vaqti', 'Yopilgan vaqt', 'Kechikish soniya', 'Talaba bahosi'])
    def safe(value):
        value = '' if value is None else str(value)
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value
    from datetime import datetime
    for r in report['requests']:
        s = r['student'] or {}
        late = ''
        if r['deadline']:
            end = r['closed_at'] or w.now()
            late = max(0, int((datetime.fromisoformat(end) - datetime.fromisoformat(r['deadline'])).total_seconds()))
        values = [r['created_at'], r['number'], r['queue_number'], r['student_id'], s.get('full_name'), s.get('programme'),
                  s.get('course'), s.get('education_form'), r['content'], r['channel'], r['manager_name'], r['assignee_name'],
                  r['department'], r['status'], r['deadline'], r['internal_basis'], r['legal_basis'], r['answer'], r['result'],
                  r['unresolved_reason'], r['answered_at'], r['closed_at'], late, '']
        writer.writerow(map(safe, values))
    return out.getvalue()


def initialize(demo=False):
    # Preserve a recoverable snapshot before the first v0.5 schema migration.
    if Path(DATABASE).is_file():
        with closing(sqlite3.connect(DATABASE)) as source:
            if source.execute('PRAGMA user_version').fetchone()[0] < 8:
                stamp = w.now().replace(':', '').replace('+', '_')
                backup_path = str(DATABASE) + '.pre-v05-' + stamp + '.bak'
                with closing(sqlite3.connect(backup_path)) as backup:
                    source.backup(backup)
                os.chmod(backup_path,0o600)
                print('Baza zaxirasi: ' + backup_path, flush=True)
    with closing(connection()) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS students (
                hemis_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, faculty TEXT NOT NULL,
                programme TEXT NOT NULL, course INTEGER NOT NULL, student_group TEXT NOT NULL,
                education_form TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
                lang TEXT NOT NULL, section INTEGER NOT NULL, service INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'waiting', operator INTEGER, called INTEGER, created_at TEXT, content_name TEXT, prefix TEXT, queue_seq INTEGER,target_operator INTEGER
            );
            CREATE UNIQUE INDEX IF NOT EXISTS operator_active ON tickets(operator) WHERE status IN ('called','serving');
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY, ticket INTEGER NOT NULL, operator INTEGER NOT NULL, lang TEXT NOT NULL
            );
        ''')
        for table, name, spec in [('students', 'education_form', "TEXT NOT NULL DEFAULT ''"),
                                  ('students', 'status', "TEXT NOT NULL DEFAULT 'active'"), ('students','gender',"TEXT NOT NULL DEFAULT ''"), ('students','education_type',"TEXT NOT NULL DEFAULT ''"), ('students','source_json',"TEXT NOT NULL DEFAULT ''"), ('tickets', 'created_at', 'TEXT'), ('tickets', 'content_name', 'TEXT'),('tickets','prefix','TEXT'),('tickets','queue_seq','INTEGER'),('tickets','target_operator','INTEGER')]:
            if name not in {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}:
                db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {spec}')
        auth.initialize(db, demo)
        w.initialize(db)
        security_monitor.initialize(db)
        attachments.initialize(db)
        branding.initialize(db)
        profile_photo.initialize(db)
        student_registry.initialize(db)
        audio_store.initialize(db)
        integrations.initialize(db)
        telegram_bot.initialize(db)
        telegram_mini.initialize(db)
        kiosk_printer.initialize(db)
        service_access.initialize(db)
        with db:
            config=settings(db)
            renamed=False
            for section,old_names in ((0,('Transkript oliş','Transkript olish')),(3,('Tölovlar','To‘lovlar',"To'lovlar"))):
                if config['catalog'][section][1][0][0] in old_names:
                    config['catalog'][section][1][0]=copy.deepcopy(CATALOG[section][1][0]);renamed=True
            if renamed:db.execute('UPDATE settings SET value=? WHERE id=1',(json.dumps(config,ensure_ascii=False),))

            for ticket in db.execute('SELECT * FROM tickets WHERE prefix IS NULL OR queue_seq IS NULL OR target_operator IS NULL').fetchall():
                route=routing.for_section(config['section_routes'],ticket['section'])
                db.execute('UPDATE tickets SET prefix=COALESCE(prefix,?),queue_seq=COALESCE(queue_seq,id),target_operator=COALESCE(target_operator,operator,?) WHERE id=?',('A',route['operator'],ticket['id']))
            routing.initialize_daily_queue(db)
            db.execute("UPDATE requests SET department=COALESCE(NULLIF((SELECT department FROM users WHERE id=requests.assignee_id),''),(SELECT department FROM users WHERE id=requests.manager_id),'') WHERE department='' AND (assignee_id IS NOT NULL OR manager_id IS NOT NULL)")
            if demo:
                db.executemany('INSERT INTO students(hemis_id,full_name,faculty,programme,course,student_group,education_form,status) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(hemis_id) DO NOTHING', [
                    ('100000000001', 'Sinov Talaba Bir', 'Filologiya (sinov)', 'Özbek tili', 2, 'TEST-201', 'Kunduzgi', 'active'),
                    ('100000000002', 'Sinov Talaba Ikki', 'Tarjima (sinov)', 'Tarjima nazariyasi', 3, 'TEST-301', 'Kunduzgi', 'active'),
                    ('H24011876', 'Sinov Mohinur Karimova', 'Filologiya (sinov)', 'Özbek tili', 3, 'TEST-301', 'Kunduzgi', 'active'),
                ])
            for ticket in db.execute('SELECT * FROM tickets WHERE content_name IS NULL').fetchall():
                content = CATALOG[ticket['section']][1][ticket['service']][LANGUAGES.index(ticket['lang'])]
                db.execute('UPDATE tickets SET content_name=? WHERE id=?', (content, ticket['id']))
            for ticket in db.execute('SELECT * FROM tickets WHERE id NOT IN (SELECT ticket_id FROM requests WHERE ticket_id IS NOT NULL)').fetchall():
                content = CATALOG[ticket['section']][1][ticket['service']][LANGUAGES.index(ticket['lang'])]
                rid = w.kiosk_request(db, ticket, content)
                if ticket['created_at'] is None:
                    w.record(db, rid, None, 'legacy_import', {'note': 'Eski çek; yaratilgan vaqt noma’lum. Ariza import vaqti bilan qayd etildi.', 'queue_status': ticket['status']})
            db.execute('PRAGMA user_version=8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8081)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--db', type=Path, default=ROOT / 'navbot.sqlite3')
    parser.add_argument('--ensure-admin', action='store_true', help='Create first admin if no accounts exist, then start server')
    parser.add_argument('--init-admin', action='store_true', help='Create first admin interactively; no server start')
    parser.add_argument('--seed-demo', action='store_true', help='Add fictitious local students and known demo accounts; local test only')
    args = parser.parse_args()
    DATABASE = args.db
    if args.host not in ('127.0.0.1', 'localhost', '::1') and args.seed_demo:
        parser.error('Demo hisoblar bilan faqat loopbackda işga tuşiring')
    initialize(args.seed_demo)
    if args.init_admin or args.ensure_admin:
        import getpass
        with closing(connection()) as db, db:
            has_users = db.execute('SELECT 1 FROM users').fetchone() is not None
            if has_users and args.init_admin:
                parser.error('Hisoblar mavjud. Birinçi admin allaqaçon yaratilgan.')
            while not has_users:
                try:
                    username = input('Admin login: ').strip()
                    password = getpass.getpass('Vaqtinçalik parol (kamida 12 belgi): ')
                    confirmation = getpass.getpass('Parolni takrorlang: ')
                except (EOFError, KeyboardInterrupt):
                    parser.exit(1, '\nAdmin yaratilmadi. Qayta işga tuşirib davom eting.\n')
                if password != confirmation:
                    print('Parollar mos emas. Qayta kiriting.', flush=True)
                    continue
                try:
                    user = auth.create_user(db, {'username': username, 'full_name': 'Superadmin', 'role': 'admin', 'department': 'Registrar', 'operator': None, 'password': password})
                except auth.AuthError as error:
                    print(str(error), flush=True)
                    continue
                w.audit(db, user, 'first_admin_create', {})
                has_users = True
                print('Admin yaratildi.', flush=True)
        if args.init_admin:
            print('Serverni START-WINDOWS.bat orqali işga tuşiring.', flush=True)
            raise SystemExit(0)
    print(f'NavBoT: http://{args.host}:{args.port}', flush=True)
    if args.seed_demo:
        print('LOKAL SINOV: demo loginlar admin / manager / manager2 / executor / head / director; parol Navbot-Test-2026!', flush=True)
    with ThreadingHTTPServer((args.host, args.port), Handler) as server:
        server.serve_forever()
