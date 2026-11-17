import argparse
import json
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / 'catalog.json').read_text())
LANGUAGES = ('uz', 'ru', 'en')
PAGE = (ROOT / 'index.html').read_bytes()


def connection():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def snapshot(db, operator):
    items = [dict(row) for row in db.execute(
        'SELECT id,lang,section,service,status,operator,called FROM tickets WHERE status != ? ORDER BY id',
        ('done',)
    )]
    called = max((i for i in items if i['status'] == 'called'),
                 key=lambda i: i['called'], default=None)
    return {
        'waiting': [i for i in items if i['status'] == 'waiting'],
        'serving': sorted((i for i in items if i['status'] == 'serving'), key=lambda i: i['operator']),
        'current': called,
        'desk': next((i for i in items if i['operator'] == operator), None),
    }


def mutate(db, path, data):
    db.execute('BEGIN IMMEDIATE')
    if path == '/api/student':
        hemis_id = data.get('hemis_id')
        if not isinstance(hemis_id, str) or not hemis_id.isascii() or not hemis_id.isdigit() or not 6 <= len(hemis_id) <= 20:
            raise ValueError('HEMIS ID 6–20 ta raqamdan iborat bo‘lishi kerak')
        row = db.execute('SELECT hemis_id,full_name,faculty,programme,course,student_group FROM students WHERE hemis_id=?', (hemis_id,)).fetchone()
        return {'student': dict(row) if row else None, 'source': 'local'}
    if path == '/api/ticket':
        key = str(UUID(data['key']))
        lang, section, service = (data[k] for k in ('lang', 'section', 'service'))
        if lang not in LANGUAGES or type(section) is not int or type(service) is not int:
            raise ValueError('Invalid selection')
        if not 0 <= section < len(CATALOG) or not 0 <= service < len(CATALOG[section][1]):
            raise ValueError('Invalid selection')
        db.execute(
            'INSERT INTO tickets (request_key,lang,section,service) VALUES (?,?,?,?) '
            'ON CONFLICT(request_key) DO NOTHING', (key, lang, section, service)
        )
        return dict(db.execute(
            'SELECT id,lang,section,service FROM tickets WHERE request_key=?', (key,)
        ).fetchone())

    operator = data['operator']
    if type(operator) is not int or not 1 <= operator <= 30:
        raise ValueError('Invalid operator')
    action = data['action']
    desk = db.execute(
        "SELECT * FROM tickets WHERE operator=? AND status IN ('called','serving')", (operator,)
    ).fetchone()
    if action == 'call' and desk is None:
        ticket = db.execute("SELECT * FROM tickets WHERE status='waiting' ORDER BY id LIMIT 1").fetchone()
        if ticket is None:
            raise ValueError('Navbat böş')
        db.execute("UPDATE tickets SET status='called',operator=? WHERE id=?", (operator, ticket['id']))
        desk = ticket
    elif not desk or action == 'call':
        raise ValueError('Operator holati özgargan')
    elif action == 'start' and desk['status'] == 'called':
        db.execute("UPDATE tickets SET status='serving' WHERE id=?", (desk['id'],))
    elif action == 'finish' and desk['status'] == 'serving':
        db.execute("UPDATE tickets SET status='done' WHERE id=?", (desk['id'],))
    elif action != 'recall' or desk['status'] != 'called':
        raise ValueError('Bu amal joriy holatda bajarilmaydi')
    if action in ('call', 'recall'):
        event = db.execute('INSERT INTO calls (ticket,operator,lang) VALUES (?,?,?)',
                           (desk['id'], operator, desk['lang'])).lastrowid
        db.execute('UPDATE tickets SET called=? WHERE id=?', (event, desk['id']))
    return snapshot(db, operator)


class Handler(BaseHTTPRequestHandler):
    def send_body(self, body, mime, status=200):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def reply(self, value, status=200):
        self.send_body(json.dumps(value, ensure_ascii=False).encode(), 'application/json; charset=utf-8', status)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path in ('/', '/kiosk', '/operator', '/tv', '/tablo'):
            return self.send_body(PAGE, 'text/html; charset=utf-8')
        if url.path == '/api/catalog':
            return self.reply(CATALOG)
        if url.path != '/api/state':
            return self.reply({'error': 'Topilmadi'}, 404)
        try:
            operator, after = map(int, url.query.split(',') if url.query else ('0', '0'))
        except ValueError:
            return self.reply({'error': 'Notoğri parametr'}, 400)
        with closing(connection()) as db:
            db.execute('BEGIN')
            response = snapshot(db, operator)
            response['last'] = db.execute('SELECT COALESCE(MAX(id),0) FROM calls').fetchone()[0]
            response['events'] = [dict(row) for row in db.execute(
                'SELECT * FROM calls WHERE id>? ORDER BY id', (after,)
            )] if after >= 0 else []
        self.reply(response)

    def do_POST(self):
        if self.path not in ('/api/ticket', '/api/action', '/api/student'):
            return self.reply({'error': 'Topilmadi'}, 404)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError('Notoğri sörov')
            data = json.loads(self.rfile.read(length))
            with closing(connection()) as db, db:
                response = mutate(db, self.path, data)
        except (TypeError, KeyError, ValueError, AttributeError) as error:
            return self.reply({'error': str(error)}, 400)
        self.reply(response)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--db', type=Path, default=ROOT / 'navbot.sqlite3')
    parser.add_argument('--seed-demo', action='store_true', help='Add fictitious local test students')
    args = parser.parse_args()
    DATABASE = args.db
    with closing(connection()) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                hemis_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, faculty TEXT NOT NULL,
                programme TEXT NOT NULL, course INTEGER NOT NULL, student_group TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
                lang TEXT NOT NULL, section INTEGER NOT NULL, service INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'waiting', operator INTEGER, called INTEGER
            );
            CREATE UNIQUE INDEX IF NOT EXISTS operator_active ON tickets(operator)
                WHERE status IN ('called','serving');
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY, ticket INTEGER NOT NULL, operator INTEGER NOT NULL, lang TEXT NOT NULL
            );
        """)
    if args.seed_demo:
        with closing(connection()) as db, db:
            db.executemany('INSERT INTO students VALUES (?,?,?,?,?,?) ON CONFLICT(hemis_id) DO NOTHING', [
                ('100000000001', 'Sinov Talaba Bir', 'Filologiya (sinov)', 'O‘zbek tili', 2, 'TEST-201'),
                ('100000000002', 'Sinov Talaba Ikki', 'Tarjima (sinov)', 'Tarjima nazariyasi', 3, 'TEST-301'),
            ])
    print(f'NavBoT: http://127.0.0.1:{args.port}', flush=True)
    with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
        server.serve_forever()
