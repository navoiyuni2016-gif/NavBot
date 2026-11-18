"""SQLite authentication for NavBoT's local HTTP server.

Call ``login`` using a dedicated connection: it commits login attempts so failed
attempts survive the caller's error handling. Other mutations belong to the
caller's transaction. The HTTP handler must enforce authorization and same-origin
POST requests, and set navbot_session with HttpOnly, SameSite=Strict, Path=/.
"""
import hashlib
import hmac
from http.cookies import CookieError, SimpleCookie
import re
import secrets
import sqlite3
import time

COOKIE_NAME = 'navbot_session'
SESSION_SECONDS = 12 * 60 * 60
ITERATIONS = 260_000
ROLES = ('admin', 'manager', 'executor', 'head', 'director')
FIELDS = 'id,username,full_name,role,department,operator,must_change_password'
DEMO_PASSWORD = 'Navbot-Test-2026!'


class AuthError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _one(db, sql, values=()):
    cursor = db.execute(sql, values)
    row = cursor.fetchone()
    return dict(zip((x[0] for x in cursor.description), row)) if row else None


def _user(db, user_id):
    row = _one(db, f'SELECT {FIELDS} FROM users WHERE id=? AND id NOT IN (SELECT user_id FROM user_account_states)', (user_id,))
    if row:
        row['must_change_password'] = bool(row['must_change_password'])
    return row


def _validate_password(password):
    if (not isinstance(password, str) or not 12 <= len(password) <= 128
            or not any(c.isalpha() for c in password)
            or not any(c.isdigit() for c in password)):
        raise AuthError('Parol 12–128 belgi, kamida bitta harf va raqamdan iborat bo‘lsin')


def _hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}'


def _verify(password, stored):
    try:
        scheme, iterations, salt, expected = stored.split('$')
        if scheme != 'pbkdf2_sha256' or not 1 <= int(iterations) <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), expected)
    except (AttributeError, TypeError, ValueError, UnicodeError):
        return False


def initialize(db, demo=False):
    """Create tables; only explicit demo mode seeds fictitious local accounts."""
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','manager','executor','head','director')),
            department TEXT NOT NULL,
            operator INTEGER UNIQUE CHECK(operator BETWEEN 1 AND 30),
            password_hash TEXT NOT NULL,
            must_change_password INTEGER NOT NULL DEFAULT 1 CHECK(must_change_password IN (0,1))
        );
        CREATE TABLE IF NOT EXISTS user_account_states (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            state TEXT NOT NULL CHECK(state IN ('inactive','deleted'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
        CREATE TABLE IF NOT EXISTS auth_attempts (
            identity TEXT PRIMARY KEY,
            failures INTEGER NOT NULL,
            window_start INTEGER NOT NULL
        );
    ''')
    if demo:
        demo_users = [
            ('admin', 'Sinov Superadmin', 'admin', 'Registrar', None),
            ('manager', 'Sinov Menejer 1', 'manager', 'Registrar', 1),
            ('manager2', 'Sinov Menejer 2', 'manager', 'Registrar', 2),
            ('manager3', 'Sinov Menejer 3', 'manager', 'Registrar', 3),
            ('manager4', 'Sinov Menejer 4', 'manager', 'Registrar', 4),
            ('manager5', 'Sinov Menejer 5', 'manager', 'Registrar', 5),
            ('executor', 'Sinov Ijrochi', 'executor', 'O‘quv bo‘limi', None),
            ('head', 'Sinov Bo‘lim boshlig‘i', 'head', 'O‘quv bo‘limi', None),
            ('director', 'Sinov Direktor', 'director', 'Direktor', None),
        ]
        for username, name, role, department, operator in demo_users:
            if not _one(db, 'SELECT id FROM users WHERE username=?', (username,)) and (operator is None or not _one(db,'SELECT id FROM users WHERE operator=?',(operator,))):
                db.execute('''INSERT INTO users
                    (username,full_name,role,department,operator,password_hash,must_change_password)
                    VALUES (?,?,?,?,?,?,0)''', (username, name, role, department, operator, _hash(DEMO_PASSWORD)))


def users(db):
    """Return routing-directory user records, never password hashes/session data."""
    cursor = db.execute(f'SELECT {FIELDS} FROM users WHERE id NOT IN (SELECT user_id FROM user_account_states) ORDER BY full_name,id')
    names = [x[0] for x in cursor.description]
    result = [dict(zip(names, row)) for row in cursor]
    for row in result:
        row['must_change_password'] = bool(row['must_change_password'])
    return result


def account_fields(data):
    if not isinstance(data, dict):
        raise AuthError('Noto‘g‘ri foydalanuvchi')
    username = data.get('username')
    if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{2,63}', username):
        raise AuthError('Login 3–64 ta lotin harfi, raqam, nuqta, tire yoki pastki chiziqdan iborat bo‘lsin')
    role = data.get('role')
    if role not in ROLES:
        raise AuthError('Rol noto‘g‘ri')
    name, department = data.get('full_name'), data.get('department')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 150:
        raise AuthError('F.I.Sh. kiritilishi kerak (150 belgigacha)')
    if not isinstance(department, str) or not 1 <= len(department.strip()) <= 150:
        raise AuthError('Bo‘lim kiritilishi kerak (150 belgigacha)')
    operator = data.get('operator')
    if operator in ('', None):
        operator = None
    if role == 'manager' and (type(operator) is not int or not 1 <= operator <= 30):
        raise AuthError('Menejer uchun 1–30 oralig‘ida operator raqami kerak')
    if role != 'manager' and operator is not None:
        raise AuthError('Operator raqami faqat menejerga beriladi')
    return username.lower(), name.strip(), role, department.strip(), operator


def create_user(db, data):
    """Create one account with a temporary password; caller authorizes admin."""
    username, name, role, department, operator = account_fields(data)
    password = data.get('password')
    _validate_password(password)
    try:
        user_id = db.execute('''INSERT INTO users
            (username,full_name,role,department,operator,password_hash,must_change_password)
            VALUES (?,?,?,?,?,?,1)''', (username.lower(), name.strip(), role, department.strip(), operator, _hash(password))).lastrowid
    except sqlite3.IntegrityError as error:
        raise AuthError('Login yoki operator raqami allaqachon mavjud', 409) from error
    return _user(db, user_id)


def _token(cookie_header):
    if not isinstance(cookie_header, str) or len(cookie_header) > 8192:
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
        value = cookie.get(COOKIE_NAME)
        value = value.value if value else None
    except CookieError:
        return None
    return value if value and re.fullmatch('[0-9a-f]{64}', value) else None


def current(db, cookie_header):
    """Resolve an unexpired cookie to a sanitized user, or None."""
    token = _token(cookie_header)
    if not token:
        return None
    session = _one(db, 'SELECT user_id FROM sessions WHERE token_hash=? AND expires_at>?',
                   (hashlib.sha256(token.encode()).hexdigest(), int(time.time())))
    return _user(db, session['user_id']) if session else None


def login(db, username, password):
    """Return (opaque_token, user). Commits rate limits and session issuance."""
    if not isinstance(username, str) or not isinstance(password, str) or len(username) > 64 or len(password) > 128:
        raise AuthError('Login yoki parol noto‘g‘ri', 401)
    identity = username.lower().strip()
    now = int(time.time())
    db.execute('DELETE FROM auth_attempts WHERE window_start<?', (now - 86400,))
    db.execute('DELETE FROM sessions WHERE expires_at<=?', (now,))
    for key, limit, window in ((identity, 5, 900), ('!global', 100, 60)):
        entry = _one(db, 'SELECT failures,window_start FROM auth_attempts WHERE identity=?', (key,))
        if entry and entry['failures'] >= limit and now - entry['window_start'] < window:
            db.commit()
            raise AuthError('Juda ko‘p urinish. Keyinroq qayta urinib ko‘ring', 429)
    row = _one(db, 'SELECT id,password_hash FROM users WHERE username=? AND id NOT IN (SELECT user_id FROM user_account_states)', (identity,))
    # Run PBKDF2 even for missing accounts to avoid a cheap username timing oracle.
    stored = row['password_hash'] if row else f'pbkdf2_sha256${ITERATIONS}$' + '00' * 16 + '$' + '00' * 32
    valid = _verify(password, stored)
    if not row or not valid:
        for key, window in ((identity, 900), ('!global', 60)):
            db.execute('''INSERT INTO auth_attempts(identity,failures,window_start) VALUES (?,1,?)
                ON CONFLICT(identity) DO UPDATE SET
                failures=CASE WHEN window_start<=? THEN 1 ELSE failures+1 END,
                window_start=CASE WHEN window_start<=? THEN excluded.window_start ELSE window_start END''',
                       (key, now, now - window, now - window))
        # Keep attacker-generated nonexistent usernames bounded.
        db.execute('''DELETE FROM auth_attempts WHERE identity IN
            (SELECT identity FROM auth_attempts WHERE identity!='!global'
             ORDER BY window_start DESC,identity LIMIT -1 OFFSET 10000)''')
        db.commit()
        raise AuthError('Login yoki parol noto‘g‘ri', 401)
    db.execute('DELETE FROM auth_attempts WHERE identity=?', (identity,))
    token = secrets.token_hex(32)
    db.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES (?,?,?)',
               (hashlib.sha256(token.encode()).hexdigest(), row['id'], now + SESSION_SECONDS))
    db.commit()
    return token, _user(db, row['id'])


def logout(db, cookie_header):
    """Revoke the presented session; caller clears its browser cookie."""
    token = _token(cookie_header)
    if token:
        db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))


def change_password(db, user, current_password, new_password):
    """Verify current password, set replacement, revoke every session. Returns user."""
    row = _one(db, 'SELECT password_hash FROM users WHERE id=?', (user['id'],))
    if not row or not isinstance(current_password, str) or not _verify(current_password, row['password_hash']):
        raise AuthError('Joriy parol noto‘g‘ri', 400)
    _validate_password(new_password)
    if hmac.compare_digest(current_password.encode('utf-8'), new_password.encode('utf-8')):
        raise AuthError('Yangi parol joriy paroldan farq qilishi kerak')
    db.execute('UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?', (_hash(new_password), user['id']))
    db.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
    return _user(db, user['id'])


def reset_password(db, user_id, password):
    """Admin-authorized temporary password reset, revoking all old sessions."""
    if type(user_id) is not int or not _user(db, user_id):
        raise AuthError('Foydalanuvchi topilmadi', 404)
    _validate_password(password)
    db.execute('UPDATE users SET password_hash=?,must_change_password=1 WHERE id=?', (_hash(password), user_id))
    db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
    return _user(db, user_id)
