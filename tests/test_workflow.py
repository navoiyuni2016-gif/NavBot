"""HTTP acceptance checks for the local v0.5 workflow.

Starts a real server and a disposable SQLite database. Run from any directory:
    python3 -m unittest discover -s tests -p test_workflow.py -v
"""
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from uuid import uuid4

APP = Path(__file__).resolve().parents[1] / 'navbot' / 'app.py'
PASSWORD = 'Navbot-Test-2026!'


class Client:
    def __init__(self, base):
        self.base = base
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, path, data=None, headers=None):
        request_headers = {'Accept': 'application/json'}
        if data is not None:
            request_headers['Content-Type'] = 'application/json'
        request_headers.update(headers or {})
        request = urllib.request.Request(
            self.base + path, data=None if data is None else json.dumps(data).encode('utf-8'),
            headers=request_headers,
        )
        try:
            response = self.opener.open(request, timeout=8)
        except urllib.error.HTTPError as error:
            response = error
        raw = response.read()
        content_type = response.headers.get('Content-Type', '')
        body = json.loads(raw) if 'application/json' in content_type else raw.decode('utf-8-sig')
        return response.status, body, response.headers

    def login(self, username, password=PASSWORD):
        return self.request('/api/login', {'username': username, 'password': password})


class WorkflowAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='navbot-acceptance-')
        self.addCleanup(self.temp.cleanup)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        self.log = open(Path(self.temp.name) / 'server.log', 'w+', encoding='utf-8')
        self.addCleanup(self.log.close)
        self.server = subprocess.Popen([
            sys.executable, str(APP), '--port', str(port),
            '--db', str(Path(self.temp.name) / 'test.sqlite3'), '--seed-demo',
        ], stdout=self.log, stderr=subprocess.STDOUT)
        self.addCleanup(self.stop_server)
        self.base = f'http://127.0.0.1:{port}'
        self.public = Client(self.base)
        ready = False
        for _ in range(160):
            if self.server.poll() is not None:
                break
            try:
                if self.public.request('/api/catalog')[0] == 200:
                    ready = True
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(.05)
        if not ready:
            self.log.flush()
            self.log.seek(0)
            self.fail('Server did not become ready:\n' + self.log.read())
        self.clients = {}

    def stop_server(self):
        if self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=5)

    def client(self, username):
        if username not in self.clients:
            client = Client(self.base)
            status, body, _ = client.login(username)
            self.assertEqual(status, 200, body)
            self.clients[username] = client
        return self.clients[username]

    def ok(self, client, path, data=None):
        status, body, _ = client.request(path, data)
        self.assertEqual(status, 200, f'{path}: {body}')
        return body

    def ticket(self, lang='uz', key=None):
        return self.ok(self.public, '/api/ticket', {
            'key': key or str(uuid4()), 'lang': lang, 'section': 0, 'service': 0,
        })

    def requests(self, username):
        return self.ok(self.client(username), '/api/requests')['requests']

    def active_request(self):
        ticket = self.ticket()
        manager = self.client('manager')
        self.ok(manager, '/api/action', {'operator': 1, 'action': 'call'})
        self.ok(manager, '/api/action', {'operator': 1, 'action': 'start'})
        request = next(r for r in self.requests('manager') if r['ticket_id'] == ticket['id'])
        return ticket, request

    def transition(self, username, request, action, **data):
        result = self.ok(self.client(username), '/api/request/action', {
            'id': request['id'], 'version': request['version'], 'action': action, **data,
        })['request']
        self.assertEqual(result['id'], request['id'])
        self.assertGreater(result['version'], request['version'])
        return result

    def linked_request(self):
        ticket, request = self.active_request()
        request = self.transition('manager', request, 'update', hemis_id='100000000001',
                                  content='Transkript olish', note='Ingliz tilidagi nusxa kerak')
        self.assertEqual(request['student']['hemis_id'], '100000000001')
        self.assertEqual(request['student']['full_name'], 'Sinov Talaba Bir')
        return ticket, request

    def assigned_request(self):
        ticket, request = self.linked_request()
        executor = next(u for u in self.ok(self.client('manager'), '/api/users')['users']
                        if u['username'] == 'executor')
        deadline = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(timespec='seconds')
        request = self.transition('manager', request, 'assign', assignee_id=executor['id'],
                                  deadline=deadline, internal_basis='SINOV ichki qoida 1-band',
                                  legal_basis='Huquqiy asos tasdiqlanmagan — faqat sinov', reason='Transkript tayyorlash')
        self.assertEqual(request['status'], 'in_progress')
        self.assertEqual(request['assignee_id'], executor['id'])
        self.assertEqual(request['note'], 'Ingliz tilidagi nusxa kerak')
        return ticket, request

    def test_auth_roles_and_cross_origin_protection(self):
        for path in ['/api/requests', '/api/users', '/api/notifications', '/api/report', '/api/audit']:
            status, body, _ = self.public.request(path)
            self.assertEqual(status, 401, f'{path}: {body}')
        self.assertEqual(self.public.request('/api/student', {'hemis_id': '100000000001'})[0], 401)
        self.assertEqual(self.public.request('/api/action', {'operator': 1, 'action': 'call'})[0], 401)
        self.assertEqual(self.client('executor').request('/api/action', {'operator': 1, 'action': 'call'})[0], 403)
        self.assertEqual(self.client('manager2').request('/api/action', {'operator': 1, 'action': 'call'})[0], 403)
        self.assertEqual(self.client('manager').request('/api/admin/settings', {'settings': {'volume': .5}})[0], 403)
        self.assertEqual(self.client('manager').request('/api/audit')[0], 403)
        self.assertEqual(self.client('executor').request('/api/report')[0], 403)
        status, _, headers = self.public.login('manager')
        self.assertEqual(status, 200)
        cookie = headers.get('Set-Cookie', '')
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Strict', cookie)
        self.assertEqual(self.public.request('/api/logout', {}, {'Origin': 'https://unrelated.example'})[0], 403)
        self.assertEqual(self.ok(self.public, '/api/me')['user']['username'], 'manager')
        self.ok(self.public, '/api/logout', {})
        self.assertIsNone(self.ok(self.public, '/api/me')['user'])

    def test_kiosk_idempotency_queue_lifecycle_and_public_privacy(self):
        key = str(uuid4())
        ticket = self.ticket(lang='ru', key=key)
        duplicate = self.ticket(lang='ru', key=key)
        self.assertEqual(ticket['id'], duplicate['id'])
        requests = self.requests('admin')
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]['ticket_id'], ticket['id'])
        self.assertEqual(requests[0]['content'], self.ok(self.public, '/api/catalog')[0][1][0][1])
        manager = self.client('manager')
        state = self.ok(self.public, '/api/state?1,-1')
        self.assertEqual([i['id'] for i in state['waiting']], [ticket['id']])
        self.ok(manager, '/api/action', {'operator': 1, 'action': 'call'})
        state = self.ok(self.public, '/api/state?1,0')
        self.assertEqual(state['current']['id'], ticket['id'])
        self.assertEqual(state['desk']['id'], ticket['id'])
        self.assertEqual(state['waiting'], [])
        self.assertEqual(state['events'][0]['lang'], 'ru')
        self.assertEqual(state['serving'], [])
        self.ok(manager, '/api/action', {'operator': 1, 'action': 'recall'})
        self.ok(manager, '/api/action', {'operator': 1, 'action': 'start'})
        state = self.ok(self.public, '/api/state?1,0')
        self.assertEqual([i['id'] for i in state['serving']], [ticket['id']])
        self.assertEqual(len(state['events']), 2)
        for forbidden in ['full_name', 'hemis_id', 'student', 'note', 'content', 'answer', 'password']:
            self.assertNotIn('"' + forbidden + '"', json.dumps(state))
        self.ok(manager, '/api/action', {'operator': 1, 'action': 'finish'})
        state = self.ok(self.public, '/api/state?1,-1')
        self.assertEqual(state['waiting'], [])
        self.assertEqual(state['serving'], [])
        self.assertIsNone(state['desk'])
        request = self.requests('manager')[0]
        self.assertNotEqual(request['status'], 'closed', 'Ending physical reception must not silently close an application')
        self.assertEqual(request['manager_id'], self.ok(manager, '/api/me')['user']['id'])

    def test_assign_return_reassign_approval_history_notifications_and_report(self):
        ticket, request = self.assigned_request()
        number, deadline, basis = request['number'], request['deadline'], request['internal_basis']
        # Re-routing an active application must not bypass head-only deadline changes.
        request = self.transition('manager', request, 'assign', assignee_id=request['assignee_id'],
                                  deadline=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec='seconds'),
                                  internal_basis='Attempted overwrite', legal_basis='Attempted overwrite',
                                  reason='Ijrochi qayta tekshirildi')
        self.assertEqual((request['deadline'], request['internal_basis']), (deadline, basis))
        self.assertTrue(number.startswith('NAV-'))
        self.assertEqual([r['id'] for r in self.requests('executor')], [request['id']])
        self.assertEqual(self.requests('manager2'), [])
        self.assertTrue(any(n['request_id'] == request['id'] for n in self.ok(self.client('executor'), '/api/notifications')['notifications']))
        status, _, _ = self.client('manager2').request('/api/request/action', {
            'id': request['id'], 'version': request['version'], 'action': 'resolve', 'answer': 'No access', 'result': 'No access',
        })
        self.assertEqual(status, 403)
        status, _, _ = self.client('executor').request('/api/request/action', {
            'id': request['id'], 'version': request['version'], 'action': 'return', 'reason': '',
        })
        self.assertEqual(status, 400)
        old_version = request['version']
        request = self.transition('executor', request, 'return', reason='Boshqa mas’ulga tegishli')
        self.assertEqual(request['status'], 'returned')
        self.assertEqual((request['number'], request['deadline']), (number, deadline))
        manager_notifications = self.ok(self.client('manager'), '/api/notifications')['notifications']
        notice = next(n for n in manager_notifications if n['request_id'] == request['id'])
        self.client('manager2').request('/api/notification/read', {'id': notice['id']})
        protected_notice = next(n for n in self.ok(self.client('manager'), '/api/notifications')['notifications'] if n['id'] == notice['id'])
        self.assertFalse(protected_notice['read'], 'Another user must not mark this notification read')
        self.ok(self.client('manager'), '/api/notification/read', {'id': notice['id']})
        updated_notice = next(n for n in self.ok(self.client('manager'), '/api/notifications')['notifications'] if n['id'] == notice['id'])
        self.assertTrue(updated_notice['read'])
        request = self.transition('manager', request, 'assign', assignee_id=request['assignee_id'],
                                  deadline=deadline, internal_basis=basis, legal_basis=request['legal_basis'],
                                  reason='Ma’lumot tekshirildi, qayta ijroga')
        self.assertEqual((request['number'], request['deadline'], request['internal_basis']), (number, deadline, basis))
        stale = self.client('manager').request('/api/request/action', {
            'id': request['id'], 'version': old_version, 'action': 'update', 'content': 'stale overwrite',
        })
        self.assertEqual(stale[0], 409)
        request = self.transition('executor', request, 'submit', answer='Transkript tayyorlandi')
        self.assertEqual(request['status'], 'pending_approval')
        self.assertTrue(any(n['request_id'] == request['id'] for n in self.ok(self.client('head'), '/api/notifications')['notifications']))
        self.assertEqual(self.client('manager').request('/api/request/action', {
            'id': request['id'], 'version': request['version'], 'action': 'approve', 'result': 'bad',
        })[0], 403)
        request = self.transition('head', request, 'correct', reason='Tarjima aniqlashtirilsin')
        self.assertEqual(request['status'], 'in_progress')
        request = self.transition('executor', request, 'submit', answer='Tarjima tekshirildi, yakuniy transkript tayyor')
        request = self.transition('head', request, 'approve', result='Talabaga transkript berildi')
        self.assertEqual(request['status'], 'closed')
        self.assertTrue(request['answered_at'])
        self.assertTrue(request['closed_at'])
        self.assertEqual((request['number'], request['deadline']), (number, deadline))
        history = json.dumps(request['history'], ensure_ascii=False)
        for required in ['Boshqa mas’ulga tegishli', 'Tarjima aniqlashtirilsin', 'Talabaga transkript berildi']:
            self.assertIn(required, history)
        report = self.ok(self.client('director'), '/api/report')
        self.assertEqual(report['summary']['total'], 1)
        self.assertEqual(report['summary']['closed'], 1)
        self.assertEqual(report['summary']['on_time'], 1)
        self.assertEqual(report['summary']['overdue'], 0)
        self.assertEqual(report['requests'][0]['number'], number)
        self.assertTrue(report['departments'])
        self.assertTrue(report['daily'])
        status, csv, headers = self.client('director').request('/api/report.csv')
        self.assertEqual(status, 200)
        self.assertIn('text/csv', headers.get('Content-Type', ''))
        self.assertIn(number, csv)
        self.assertIn('Sinov Talaba Bir', csv)
        self.assertIn('Transkript', csv)
        self.assertEqual(self.ok(self.client('director'), '/api/report?channel=phone')['summary']['total'], 0)

    def test_head_cannot_approve_or_change_another_department(self):
        _, request = self.assigned_request()
        request = self.transition('executor', request, 'submit', answer='Tasdiq uchun tayyor javob')
        self.ok(self.client('admin'), '/api/admin/user', {
            'username': 'foreignhead', 'full_name': 'Boshqa bo‘lim rahbari', 'role': 'head',
            'department': 'Moliya (sinov)', 'operator': None, 'password': 'Foreign-Head-2026!',
        })
        head = Client(self.base)
        self.assertEqual(head.login('foreignhead', 'Foreign-Head-2026!')[0], 200)
        self.ok(head, '/api/password', {'current_password': 'Foreign-Head-2026!', 'new_password': 'Changed-Head-2026!'})
        self.assertEqual(head.login('foreignhead', 'Changed-Head-2026!')[0], 200)
        self.assertEqual(self.ok(head, '/api/requests')['requests'], [])
        for action, extra in [('approve', {'result': 'Unauthorized closure'}),
                              ('correct', {'reason': 'Unauthorized correction'}),
                              ('deadline', {'deadline': (datetime.now(timezone.utc) + timedelta(days=20)).isoformat(),
                                            'reason': 'Unauthorized extension', 'internal_basis': 'x', 'legal_basis': 'y'})]:
            response = head.request('/api/request/action', {
                'id': request['id'], 'version': request['version'], 'action': action, **extra,
            })
            self.assertEqual(response[0], 403, response[1])
        self.assertEqual(self.ok(head, '/api/report')['summary']['total'], 0)
        unchanged = next(r for r in self.requests('admin') if r['id'] == request['id'])
        self.assertEqual((unchanged['status'], unchanged['version'], unchanged['deadline']),
                         (request['status'], request['version'], request['deadline']))

    def test_student_import_atomicity_and_h_prefixed_ids(self):
        admin = self.client('admin')
        student = {
            'hemis_id': 'H99011876', 'full_name': 'Sinov H Talaba', 'faculty': 'Test fakultet',
            'programme': 'Filologiya', 'course': 3, 'student_group': 'F-301',
            'education_form': 'Kunduzgi', 'status': 'Faol',
        }
        result = self.ok(admin, '/api/students/import', {'students': [student]})
        self.assertEqual((result['added'], result['updated']), (1, 0))
        updated = dict(student, full_name='Yangilangan Sinov Talaba')
        result = self.ok(admin, '/api/students/import', {'students': [updated]})
        self.assertEqual((result['added'], result['updated']), (0, 1))
        loaded = self.ok(self.client('manager'), '/api/student', {'hemis_id': 'H99011876'})['student']
        self.assertEqual(loaded['full_name'], updated['full_name'])
        self.assertEqual(loaded['education_form'], 'Kunduzgi')
        self.assertIsNone(self.ok(self.client('manager'), '/api/student', {'hemis_id': '999999999999'})['student'])
        self.assertEqual(self.client('manager').request('/api/students/import', {'students': [student]})[0], 403)
        new = dict(student, hemis_id='H99011877')
        invalid = dict(student, hemis_id='INVALID!')
        self.assertEqual(admin.request('/api/students/import', {'students': [new, invalid]})[0], 400)
        self.assertIsNone(self.ok(self.client('manager'), '/api/student', {'hemis_id': new['hemis_id']})['student'])
        for bad in [None, 123456, "' OR 1=1 --", '１２３４５６']:
            self.assertEqual(self.client('manager').request('/api/student', {'hemis_id': bad})[0], 400)

    def test_phone_has_no_ticket_and_is_idempotent(self):
        manager = self.client('manager')
        data = {'key': str(uuid4()), 'channel': 'phone', 'section': 0, 'service': 0, 'lang': 'uz',
                'hemis_id': '100000000001', 'identity_confirmed': False,
                'content': 'Telefon orqali transkript so‘rovi', 'note': 'Shaxsi sinov tartibida tasdiqlandi'}
        self.assertEqual(manager.request('/api/request/create', data)[0], 400)
        data['identity_confirmed'] = True
        first = self.ok(manager, '/api/request/create', data)['request']
        second = self.ok(manager, '/api/request/create', data)['request']
        self.assertEqual(first['id'], second['id'])
        self.assertIsNone(first['ticket_id'])
        self.assertIsNone(first['queue_number'])
        self.assertEqual(first['channel'], 'phone')
        self.assertEqual(first['student']['hemis_id'], '100000000001')
        self.assertEqual(len(self.requests('manager')), 1)
        state = self.ok(self.public, '/api/state?1,0')
        self.assertEqual(state['waiting'], [])
        self.assertEqual(state['events'], [])

    def test_local_resolution_requires_student_and_preserves_archive(self):
        ticket, request = self.active_request()
        self.assertEqual(self.client('manager').request('/api/request/action', {
            'id': request['id'], 'version': request['version'], 'action': 'resolve',
            'answer': 'Joyida tushuntirildi', 'result': 'Hal qilindi',
        })[0], 400)
        request = self.transition('manager', request, 'update', hemis_id='100000000001',
                                  content='Transkript olish', note='Joyida tushuntirish')
        request = self.transition('manager', request, 'resolve', answer='Joyida tushuntirildi', result='Hal qilindi')
        self.assertEqual(request['status'], 'closed')
        self.assertEqual(request['result'], 'Hal qilindi')
        self.assertTrue(request['closed_at'])
        self.assertIn(self.client('manager').request('/api/request/action', {
            'id': request['id'], 'version': request['version'], 'action': 'update',
            'content': 'Closed request overwrite',
        })[0], (400, 409))
        self.assertEqual(next(r for r in self.requests('manager') if r['id'] == request['id'])['content'], 'Transkript olish')

    def test_deadline_changes_record_old_and_new_values(self):
        _, request = self.assigned_request()
        old = request['deadline']
        new = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat(timespec='seconds')
        self.assertEqual(self.client('manager').request('/api/request/action', {
            'id': request['id'], 'version': request['version'], 'action': 'deadline',
            'deadline': new, 'reason': 'No permission', 'internal_basis': 'x', 'legal_basis': 'y',
        })[0], 403)
        request = self.transition('head', request, 'deadline', deadline=new, reason='Qo‘shimcha tekshiruv',
                                  internal_basis='SINOV yangi asos', legal_basis='Tasdiqlanmagan sinov')
        self.assertNotEqual(request['deadline'], old)
        self.assertEqual(datetime.fromisoformat(request['deadline']), datetime.fromisoformat(new))
        history = json.dumps(request['history'], ensure_ascii=False)
        self.assertIn(old, history)
        self.assertIn(request['deadline'], history)
        self.assertIn('Qo‘shimcha tekshiruv', history)

    def test_user_creation_password_change_and_reset(self):
        admin = self.client('admin')
        user = self.ok(admin, '/api/admin/user', {
            'username': 'newmanager', 'full_name': 'Yangi Menejer', 'role': 'manager',
            'department': 'Registrar', 'operator': 9, 'password': 'Initial-Test-2026!',
        })['user']
        self.assertNotIn('password', user)
        self.assertNotIn('password_hash', user)
        client = Client(self.base)
        status, body, _ = client.login('newmanager', 'Initial-Test-2026!')
        self.assertEqual(status, 200, body)
        self.assertTrue(body['user']['must_change_password'])
        self.assertEqual(client.request('/api/password', {
            'current_password': 'wrong', 'new_password': 'Changed-Test-2026!',
        })[0], 400)
        self.ok(client, '/api/password', {'current_password': 'Initial-Test-2026!', 'new_password': 'Changed-Test-2026!'})
        fresh = Client(self.base)
        self.assertNotEqual(fresh.login('newmanager', 'Initial-Test-2026!')[0], 200)
        status, body, _ = fresh.login('newmanager', 'Changed-Test-2026!')
        self.assertEqual(status, 200, body)
        self.assertFalse(body['user']['must_change_password'])
        self.ok(admin, '/api/admin/reset', {'user_id': user['id'], 'password': 'Reset-Test-2026!'})
        self.assertIsNone(self.ok(fresh, '/api/me')['user'], 'Reset must revoke old sessions')
        reset = Client(self.base)
        status, body, _ = reset.login('newmanager', 'Reset-Test-2026!')
        self.assertEqual(status, 200, body)
        self.assertTrue(body['user']['must_change_password'])

    def test_legacy_database_migration_keeps_students_and_queue(self):
        self.stop_server()
        database = Path(self.temp.name) / 'test.sqlite3'
        # Use exactly the original ZIP's table shape, including a completed ticket.
        database.unlink()
        with sqlite3.connect(database) as db:
            db.executescript("""
                CREATE TABLE students (hemis_id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
                    faculty TEXT NOT NULL, programme TEXT NOT NULL, course INTEGER NOT NULL,
                    student_group TEXT NOT NULL);
                CREATE TABLE tickets (id INTEGER PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
                    lang TEXT NOT NULL, section INTEGER NOT NULL, service INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'waiting', operator INTEGER, called INTEGER);
                CREATE UNIQUE INDEX operator_active ON tickets(operator) WHERE status IN ('called','serving');
                CREATE TABLE calls (id INTEGER PRIMARY KEY, ticket INTEGER NOT NULL, operator INTEGER NOT NULL, lang TEXT NOT NULL);
                INSERT INTO students VALUES ('700000000001','Old Student','Old Faculty','Old Programme',2,'OLD-1');
                INSERT INTO tickets VALUES (41,'00000000-0000-4000-8000-000000000041','uz',0,0,'waiting',NULL,NULL);
                INSERT INTO tickets VALUES (40,'00000000-0000-4000-8000-000000000040','ru',0,0,'done',1,1);
                INSERT INTO calls VALUES (1,40,1,'ru');
            """)
        self.log.seek(0)
        self.log.truncate()
        port = self.base.rsplit(':', 1)[1]
        self.server = subprocess.Popen([
            sys.executable, str(APP), '--port', port, '--db', str(database), '--seed-demo',
        ], stdout=self.log, stderr=subprocess.STDOUT)
        ready = False
        for _ in range(160):
            if self.server.poll() is not None:
                break
            try:
                if self.public.request('/api/catalog')[0] == 200:
                    ready = True
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(.05)
        if not ready:
            self.log.flush()
            self.log.seek(0)
            self.fail('Legacy migration server did not start:\n' + self.log.read())
        backups = list(Path(self.temp.name).glob('test.sqlite3.pre-v05-*.bak'))
        self.assertEqual(len(backups), 1, 'First migration must leave one recoverable pre-v0.5 backup')
        with sqlite3.connect(backups[0]) as backup:
            self.assertEqual(backup.execute('SELECT COUNT(*) FROM tickets').fetchone()[0], 2)
            self.assertEqual(backup.execute('SELECT full_name FROM students WHERE hemis_id=?', ('700000000001',)).fetchone()[0], 'Old Student')
        migrated = self.ok(self.client('manager'), '/api/student', {'hemis_id': '700000000001'})['student']
        self.assertEqual(migrated['full_name'], 'Old Student')
        state = self.ok(self.public, '/api/state?1,0')
        self.assertEqual([r['id'] for r in state['waiting']], [41])
        self.assertEqual(state['events'][0]['ticket'], 40)
        registry = self.requests('admin')
        self.assertEqual(sum(r['ticket_id'] == 41 for r in registry), 1)
        with sqlite3.connect(database) as db:
            self.assertEqual(db.execute('SELECT status FROM tickets WHERE id=40').fetchone()[0], 'done')

    def test_settings_snapshots_and_integrations_status(self):
        _, request = self.active_request()
        original_content = request['content']
        settings = self.ok(self.public, '/api/settings')['settings']
        settings['catalog'][0][1][0][0] = 'Yangi sinov nomi'
        settings['volume'] = .4
        self.ok(self.client('admin'), '/api/admin/settings', {'settings': settings})
        self.assertEqual(self.ok(self.public, '/api/settings')['settings']['volume'], .4)
        self.assertEqual(next(r for r in self.requests('manager') if r['id'] == request['id'])['content'], original_content)
        integration = self.ok(self.client('admin'), '/api/integrations')
        self.assertFalse(integration['lms']['connected'])
        self.assertFalse(integration['telegram']['connected'])
        self.assertTrue(self.ok(self.client('admin'), '/api/audit')['events'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
