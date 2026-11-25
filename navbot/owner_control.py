"""Explicit local license control, isolated from customer staff accounts.

No default credentials, remote activation server, expiry timer or data deletion.
The server/DB administrator remains a trusted party.
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
import struct
import time
from http.cookies import SimpleCookie, CookieError
import auth

COOKIE = 'navbot_owner'
SESSION_SECONDS = 600
AUTHOR = 'Quvonchbek Rustamov'


def initialize(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS owner_account (
      id INTEGER PRIMARY KEY CHECK(id=1),username TEXT NOT NULL,password_hash TEXT NOT NULL,
      totp_secret TEXT NOT NULL,last_counter INTEGER NOT NULL DEFAULT -1);
    CREATE TABLE IF NOT EXISTS owner_sessions(token_hash TEXT PRIMARY KEY,expires_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS owner_license (
      id INTEGER PRIMARY KEY CHECK(id=1),suspended INTEGER NOT NULL DEFAULT 0,
      reason TEXT NOT NULL DEFAULT '',updated_at INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 0);
    INSERT OR IGNORE INTO owner_license(id) VALUES(1);
    CREATE TABLE IF NOT EXISTS owner_attempts(id INTEGER PRIMARY KEY CHECK(id=1),failures INTEGER NOT NULL,window_start INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS owner_events(id INTEGER PRIMARY KEY,created_at INTEGER NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL);
    ''')


def event(db, action, detail):
    db.execute('INSERT INTO owner_events(created_at,action,detail) VALUES(?,?,?)',
               (int(time.time()), action, json.dumps(detail, ensure_ascii=False)))


def status(db):
    row = dict(db.execute('SELECT suspended,reason,updated_at,version FROM owner_license WHERE id=1').fetchone())
    row['suspended'] = bool(row['suspended'])
    return row


def suspended(db):
    # A separately managed worker may briefly run before the web schema migration.
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owner_license'").fetchone():
        return False
    return status(db)['suspended']


def totp(secret, counter):
    key = base64.b32decode(secret)
    digest = hmac.new(key, struct.pack('>Q', counter), hashlib.sha1).digest()
    start = digest[-1] & 15
    return str((struct.unpack('>I', digest[start:start+4])[0] & 0x7fffffff) % 1000000).zfill(6)


def counter_for(secret, code, last=-1):
    if not isinstance(code, str) or not re.fullmatch(r'[0-9]{6}', code):
        return None
    current = int(time.time()) // 30
    for counter in (current, current-1, current+1):
        if counter > last and hmac.compare_digest(totp(secret, counter), code):
            return counter
    return None


def configure(db, username, password, secret, code, reset=False):
    if not isinstance(username, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{3,64}', username):
        raise auth.AuthError('Login 3–64 ta lotin harfi, raqam, nuqta yoki chiziqdan iborat bo‘lsin')
    auth._validate_password(password)
    counter = counter_for(secret, code)
    if counter is None:
        raise auth.AuthError('Autentifikator kodi noto‘g‘ri')
    if db.execute('SELECT 1 FROM owner_account').fetchone() and not reset:
        raise auth.AuthError('Egasi hisobi mavjud. Tiklash uchun --reset-owner ishlating', 409)
    db.execute('INSERT OR REPLACE INTO owner_account VALUES(1,?,?,?,?)', (username, auth._hash(password), secret, counter))
    db.execute('DELETE FROM owner_sessions')
    db.execute('DELETE FROM owner_attempts')
    event(db, 'credentials_reset' if reset else 'configured', {'username': username, 'author': AUTHOR})


def check_attempts(db):
    row = db.execute('SELECT * FROM owner_attempts WHERE id=1').fetchone()
    if row and row['failures'] >= 5 and row['window_start'] > int(time.time())-900:
        raise auth.AuthError('Ko‘p noto‘g‘ri urinish. 15 daqiqadan keyin qayta urining', 429)


def fail(db):
    now = int(time.time())
    db.execute('''INSERT INTO owner_attempts VALUES(1,1,?) ON CONFLICT(id) DO UPDATE SET
      failures=CASE WHEN window_start<=?-900 THEN 1 ELSE failures+1 END,
      window_start=CASE WHEN window_start<=?-900 THEN ? ELSE window_start END''', (now, now, now, now))
    event(db, 'authentication_failed', {})
    db.commit()  # Failed attempts must survive HTTP error handling.
    raise auth.AuthError('Egasi login/parol yoki autentifikator kodi noto‘g‘ri', 401)


def login(db, data):
    db.execute('BEGIN IMMEDIATE')
    check_attempts(db)
    row = db.execute('SELECT * FROM owner_account WHERE id=1').fetchone()
    password = data.get('password')
    # Fixed-cost password check even before owner enrollment or with unknown login.
    valid_password = isinstance(password, str) and len(password)<=128 and auth._verify(password, row['password_hash'] if row else DUMMY_HASH)
    counter = counter_for(row['totp_secret'], data.get('code'), row['last_counter']) if row else None
    if not row or data.get('username') != row['username'] or not valid_password or counter is None:
        fail(db)
    db.execute('UPDATE owner_account SET last_counter=? WHERE id=1', (counter,))
    db.execute('DELETE FROM owner_attempts')
    db.execute('DELETE FROM owner_sessions WHERE expires_at<=?', (int(time.time()),))
    token = secrets.token_urlsafe(32)
    db.execute('INSERT INTO owner_sessions VALUES(?,?)', (hashlib.sha256(token.encode()).hexdigest(), int(time.time())+SESSION_SECONDS))
    event(db, 'login', {})
    db.commit()
    return token


DUMMY_HASH = 'pbkdf2_sha256$260000$00000000000000000000000000000000$' + '0'*64


def session_hash(db, cookie):
    try:
        parsed = SimpleCookie(); parsed.load(cookie or '')
        token = parsed[COOKIE].value
    except (CookieError, KeyError):
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    return digest if db.execute('SELECT 1 FROM owner_sessions WHERE token_hash=? AND expires_at>?', (digest, int(time.time()))).fetchone() else None


def require(db, cookie):
    digest = session_hash(db, cookie)
    if not digest:
        raise auth.AuthError('Egasi hisobiga kiring', 401)
    return digest


def overview(db, cookie):
    require(db, cookie)
    return {'author': AUTHOR, **status(db), 'events': [dict(row) for row in db.execute('SELECT created_at,action,detail FROM owner_events ORDER BY id DESC LIMIT 50')]}


def change(db, cookie, data):
    db.execute('BEGIN IMMEDIATE')
    require(db, cookie)
    check_attempts(db)
    row = db.execute('SELECT password_hash FROM owner_account WHERE id=1').fetchone()
    password = data.get('password')
    if not row or not isinstance(password, str) or len(password)>128 or not auth._verify(password, row['password_hash']):
        fail(db)
    action, reason = data.get('action'), data.get('reason')
    if action not in ('suspend', 'resume') or not isinstance(reason, str) or not 3<=len(reason.strip())<=500:
        raise auth.AuthError('Amal va sababni tekshiring (3–500 belgi)')
    current = status(db)
    if type(data.get('version')) is not int or data['version'] != current['version']:
        raise auth.AuthError('Holat o‘zgargan. Sahifani yangilang', 409)
    if current['suspended'] == (action == 'suspend'):
        raise auth.AuthError('Bu holat allaqachon o‘rnatilgan', 409)
    db.execute('UPDATE owner_license SET suspended=?,reason=?,updated_at=?,version=version+1 WHERE id=1', (int(action=='suspend'), reason.strip(), int(time.time())))
    db.execute('DELETE FROM owner_attempts')
    event(db, action, {'reason': reason.strip(), 'version': current['version']+1})
    db.commit()
    return overview(db, cookie)


def logout(db, cookie):
    digest = require(db, cookie)
    db.execute('DELETE FROM owner_sessions WHERE token_hash=?', (digest,))
    event(db, 'logout', {})
    db.commit()
    return {'ok': True}


MAINTENANCE = '''<!doctype html><html lang="uz"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="15"><link rel="stylesheet" href="/assets/owner.css"><title>NAVBOT — xizmat vaqtincha to‘xtatilgan</title><body><main><h1>Xizmat vaqtincha to‘xtatilgan</h1><p>Litsenziya egasi tomonidan xizmat vaqtincha to‘xtatilgan. Universitetning mas’ul xodimiga murojaat qiling.</p><p>Ma’lumotlar saqlangan. Xizmat qayta yoqilgach sahifa avtomatik yangilanadi.</p></main></body></html>'''
