"""Explicit, read-only integration checks for the local pilot.

Credentials are owner-only files beside the database, NOT encrypted. Protect that
directory/volume and include it in protected backups (Windows also needs ACLs).
Only explicit test/sync actions access the network; saving never connects.
LMS sync accepts a documented normalized {students: [...]} JSON contract. It does
not pretend to implement an unspecified HEMIS/LMS vendor API or Telegram delivery.
"""
from datetime import datetime, timezone
import ipaddress
from http.client import HTTPSConnection
import json
import os
from pathlib import Path
import re
import secrets
import socket
import ssl
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

MAX_BODY = 4 * 1024 * 1024
TIMEOUT = 10


class IntegrationError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _admin(user):
    if not user:
        raise IntegrationError('Tizimga kiring', 401)
    if user.get('role') != 'admin':
        raise IntegrationError('Faqat Superadmin integratsiyani sozlay oladi', 403)


def _kind(kind):
    if kind not in ('lms', 'telegram'):
        raise IntegrationError('Integratsiya turini tekshiring')
    return kind


def _row(db, kind):
    cursor = db.execute('SELECT * FROM integration_config WHERE kind=?', (_kind(kind),))
    row = cursor.fetchone()
    return dict(zip((x[0] for x in cursor.description), row))


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS integration_config (
            kind TEXT PRIMARY KEY CHECK(kind IN ('lms','telegram')),
            url TEXT NOT NULL DEFAULT '',
            students_url TEXT NOT NULL DEFAULT '',
            token_ref TEXT,
            enabled INTEGER NOT NULL DEFAULT 0,
            connected INTEGER NOT NULL DEFAULT 0,
            last_checked TEXT,
            last_success TEXT,
            last_error TEXT NOT NULL DEFAULT '',
            bot_username TEXT NOT NULL DEFAULT '',
            last_sync TEXT,
            last_sync_actor INTEGER,
            last_added INTEGER NOT NULL DEFAULT 0,
            last_updated INTEGER NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO integration_config(kind) VALUES ('lms');
        INSERT OR IGNORE INTO integration_config(kind) VALUES ('telegram');
    ''')
    if 'last_success' not in [r[1] for r in db.execute('PRAGMA table_info(integration_config)')]:
        db.execute('ALTER TABLE integration_config ADD COLUMN last_success TEXT')


def _private_path(path):
    # Do not follow a symlink in the database/secret path, including its parents.
    path = Path(os.path.abspath(path))
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise IntegrationError('Integratsiya maxfiy fayllari yo‘li xavfsiz emas', 500)
    return path


def _secret_root(db, create=False):
    filename = next((r[2] for r in db.execute('PRAGMA database_list') if r[1] == 'main'), '')
    if not filename:
        raise IntegrationError('Integratsiya sozlamalari uchun faylli baza kerak', 500)
    database = _private_path(filename)
    directory = _private_path(database.parent / (database.name + '.integration-secrets'))
    if create:
        directory.mkdir(mode=0o700, exist_ok=True)
        if not directory.is_dir():
            raise IntegrationError('Maxfiy fayllar papkasi ochilmadi', 500)
        directory.chmod(0o700)
    return directory


def _secret_path(db, reference):
    if not isinstance(reference, str) or not re.fullmatch(r'[0-9a-f]{32}\.secret', reference):
        raise IntegrationError('Maxfiy fayl havolasi yaroqsiz', 500)
    return _private_path(_secret_root(db) / reference)


def _read_token(db, reference):
    if not reference:
        return ''
    try:
        path = _secret_path(db, reference)
        with path.open('rb') as stream:
            value = stream.read(4097)
        if len(value) > 4096:
            return ''
        return value.decode('ascii')
    except (OSError, UnicodeError):
        return ''


def _write_token(db, value):
    directory = _secret_root(db, create=True)
    reference = secrets.token_hex(16) + '.secret'
    target = _private_path(directory / reference)
    temporary = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix='.pending-', dir=directory)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(value.encode('ascii'))
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        return reference
    except OSError as error:
        raise IntegrationError('Maxfiy kalitni xavfsiz saqlash amalga oshmadi', 500) from None
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _remove_token(db, reference):
    if reference:
        try:
            _secret_path(db, reference).unlink(missing_ok=True)
        except OSError:
            # A failed removal is a storage error, never leak the filename/token.
            raise IntegrationError('Avvalgi maxfiy kalit faylini o‘chirish amalga oshmadi', 500) from None


def metadata(db):
    """Admin-only HTTP caller must guard this; never contains credential values."""
    result = {}
    for kind in ('lms', 'telegram'):
        row = _row(db, kind)
        row.pop('kind')
        reference = row.pop('token_ref')
        row['token_set'] = bool(_read_token(db, reference))
        row['enabled'] = bool(row['enabled'])
        row['connected'] = bool(row['connected']) and row['enabled']
        if kind == 'telegram':
            # Telegram token lives in the URL of getMe internally; do not expose it.
            row.pop('url')
            row.pop('students_url')
        result[kind] = row
    return result


def _url(value, resolve=False):
    if not isinstance(value, str) or not 1 <= len(value) <= 2048 or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise IntegrationError('HTTPS manzilni tekshiring')
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        if (parsed.scheme != 'https' or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.port not in (None, 443)
                or '%' in host or '\\' in value or host.endswith('.') or '.' not in host):
            raise ValueError
        if len(host) > 253 or not all(re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?', part) for part in host.split('.')):
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise IntegrationError('IP manzil o‘rniga ochiq HTTPS domenini kiriting')
        if host.lower().endswith(('.localhost', '.local', '.internal', '.home', '.lan', '.test', '.invalid', '.onion')):
            raise ValueError
        if resolve:
            try:
                addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            except (OSError, UnicodeError):
                raise IntegrationError('Domen DNS orqali topilmadi') from None
            if not addresses:
                raise IntegrationError('Domen DNS orqali topilmadi')
            for entry in addresses:
                address = ipaddress.ip_address(entry[4][0].split('%')[0])
                if not address.is_global or address.is_multicast or address.is_unspecified:
                    raise IntegrationError('Ichki yoki maxsus tarmoq manziliga ulanish taqiqlangan')
        return urlunsplit(('https', host.lower(), parsed.path or '/', '', ''))
    except (ValueError, UnicodeError):
        raise IntegrationError('Faqat ochiq HTTPS domeni, standart port va kalitsiz URL kiriting; query/fragment ishlatilmaydi') from None


def save(db, user, data):
    _admin(user)
    if not isinstance(data, dict):
        raise IntegrationError('Sozlama obyektini yuboring')
    kind = _kind(data.get('kind'))
    row = _row(db, kind)
    enabled = data.get('enabled', bool(row['enabled']))
    if type(enabled) is not bool:
        raise IntegrationError('Faollik qiymatini tekshiring')
    clear = data.get('clear_token', False)
    if type(clear) is not bool:
        raise IntegrationError('Kalitni tozalash qiymatini tekshiring')
    token = data.get('token', '')
    if not isinstance(token, str) or len(token) > 4096:
        raise IntegrationError('API kalitini tekshiring')
    token = token.strip()
    if token and (not token.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in token)):
        raise IntegrationError('API kalitida bo‘shliq yoki boshqaruv belgisi bo‘lmasin')
    if token and kind == 'telegram' and not re.fullmatch(r'[0-9]{5,20}:[A-Za-z0-9_-]{20,200}', token):
        raise IntegrationError('Telegram bot tokeni formatini tekshiring')
    if token and clear:
        raise IntegrationError('Kalitni kiritish yoki tozalashdan birini tanlang')
    url, students_url = row['url'], row['students_url']
    if kind == 'lms':
        if 'url' in data:
            url = _url(data['url']) if data['url'] else ''
        if 'students_url' in data:
            students_url = _url(data['students_url']) if data['students_url'] else ''
        if enabled and not url:
            raise IntegrationError('LMS tekshirish HTTPS manzilini kiriting')
        # Do not send an LMS bearer credential to a separate host on sync.
        if url and students_url and urlsplit(url).hostname != urlsplit(students_url).hostname:
            raise IntegrationError('LMS tekshirish va talabalar manzili bir domenda bo‘lsin')
    if enabled and kind == 'telegram' and not token and (clear or not _read_token(db, row['token_ref'])):
        raise IntegrationError('Faol Telegram uchun bot tokenini kiriting')
    changed = bool(token or clear or url != row['url'] or students_url != row['students_url'] or enabled != bool(row['enabled']))
    reference = _write_token(db, token) if token else (None if clear else row['token_ref'])
    try:
        db.execute('''UPDATE integration_config SET url=?,students_url=?,token_ref=?,enabled=?,
            connected=CASE WHEN ? THEN 0 ELSE connected END,
            last_checked=CASE WHEN ? THEN NULL ELSE last_checked END,
            last_error=CASE WHEN ? THEN '' ELSE last_error END,
            bot_username=CASE WHEN ? THEN '' ELSE bot_username END WHERE kind=?''',
                   (url, students_url, reference, int(enabled), changed, changed, changed, changed, kind))
    except Exception:
        if token:
            _remove_token(db, reference)
        raise
    # Old owner-only files remain until an explicit protected cleanup. Removing
    # them here would break the previous DB reference if the outer transaction rolls back.
    return metadata(db)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise IntegrationError('Yo‘naltirish rad etildi; yakuniy HTTPS API manzilini kiriting')


def _public_addresses(host, port):
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        raise IntegrationError('Domen DNS orqali topilmadi') from None
    if not addresses:
        raise IntegrationError('Domen DNS orqali topilmadi')
    for entry in addresses:
        address = ipaddress.ip_address(entry[4][0].split('%')[0])
        if not address.is_global or address.is_multicast or address.is_unspecified:
            raise IntegrationError('Ichki yoki maxsus tarmoq manziliga ulanish taqiqlangan')
    return addresses


class _SafeHTTPSConnection(HTTPSConnection):
    def connect(self):
        if self._tunnel_host:
            # Configured platform proxy is the trusted egress boundary. The
            # original target was checked above; the proxy resolves CONNECT.
            _public_addresses(self._tunnel_host, self._tunnel_port or 443)
            return super().connect()
        # Pin direct connections to the exact public addresses validated here,
        # avoiding a second resolver lookup (DNS rebinding / TOCTOU).
        addresses = _public_addresses(self.host, self.port)
        last_error = None
        for family, socktype, proto, _, address in addresses:
            candidate = socket.socket(family, socktype, proto)
            candidate.settimeout(self.timeout)
            try:
                if self.source_address:
                    candidate.bind(self.source_address)
                candidate.connect(address)
                self.sock = self._context.wrap_socket(candidate, server_hostname=self.host)
                return
            except OSError as error:
                last_error = error
                candidate.close()
        raise last_error or OSError('Connection failed')


class _SafeHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(_SafeHTTPSConnection, request, context=self._context,
                            check_hostname=self._check_hostname)


def _transport(url, headers):
    """Network boundary. Uses configured platform proxies and normal TLS trust."""
    opener = build_opener(_SafeHTTPSHandler(context=ssl.create_default_context()), _NoRedirect())
    request = Request(url, headers=headers, method='GET')
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            body = response.read(MAX_BODY + 1)
            return response.status, response.headers.get('Content-Type', ''), body
    except HTTPError as error:
        # Never use str(error): Telegram request URLs contain the bot token.
        raise IntegrationError('API HTTP xatosi (' + str(error.code) + ')') from None
    except (URLError, OSError, ValueError):
        raise IntegrationError('Tarmoq, vaqt tugashi yoki TLS tekshiruvi xatosi') from None


def _request_json(url, token='', telegram=False):
    _url(url, resolve=True)
    headers = {'Accept': 'application/json', 'User-Agent': 'NavBoT-local-pilot/0.5'}
    if token and not telegram:
        headers['Authorization'] = 'Bearer ' + token
    status, content_type, body = _transport(url, headers)
    if status != 200:
        raise IntegrationError('API javob kodi 200 emas')
    if len(body) > MAX_BODY:
        raise IntegrationError('API javobi belgilangan hajmdan katta')
    if content_type.split(';')[0].strip().lower() != 'application/json':
        raise IntegrationError('API application/json qaytarishi kerak; HTML sahifa qabul qilinmaydi')
    try:
        value = json.loads(body.decode('utf-8'))
    except (UnicodeError, ValueError):
        raise IntegrationError('API JSON javobi noto‘g‘ri') from None
    if not isinstance(value, dict):
        raise IntegrationError('API JSON obyekti qaytarishi kerak')
    if not telegram and (value.get('error') or value.get('success') is False or value.get('ok') is False):
        raise IntegrationError('API ulanishni tasdiqlamadi')
    return value


def _check_ready(db, kind):
    row = _row(db, kind)
    if not row['enabled']:
        raise IntegrationError('Avval integratsiyani faollashtiring')
    token = _read_token(db, row['token_ref'])
    if kind == 'telegram' and not token:
        raise IntegrationError('Telegram tokeni saqlanmagan yoki o‘qilmadi')
    return row, token


def _checked(db, kind, connected, error='', bot_username='', expected=None):
    stamp = _now()
    sql = 'UPDATE integration_config SET connected=?,last_checked=?,last_success=CASE WHEN ? THEN ? ELSE last_success END,last_error=?,bot_username=? WHERE kind=?'
    stamp = _now()
    values = [int(connected), stamp, int(connected), stamp, error, bot_username, kind]
    if expected is not None:
        sql += ' AND url=? AND students_url=? AND token_ref IS ? AND enabled=?'
        values.extend(expected[k] for k in ('url', 'students_url', 'token_ref', 'enabled'))
    if db.execute(sql, values).rowcount != 1:
        raise IntegrationError('Sozlama sinov vaqtida özgardi; qayta tekşiring', 409)



def test(db, user, kind):
    _admin(user)
    _kind(kind)
    row = None
    try:
        row, token = _check_ready(db, kind)
        if kind == 'telegram':
            # getMe is read-only and sends no message to any Telegram account.
            result = _request_json('https://api.telegram.org/bot' + token + '/getMe', telegram=True)
            bot = result.get('result')
            if result.get('ok') is not True or not isinstance(bot, dict) or bot.get('is_bot') is not True:
                raise IntegrationError('Telegram bot tokenini tasdiqlamadi')
            username = bot.get('username', '')
            if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9_]{5,64}', username):
                raise IntegrationError('Telegram bot ma’lumoti noto‘g‘ri')
            _checked(db, kind, True, bot_username=username, expected=row)
        else:
            _request_json(row['url'], token)
            _checked(db, kind, True, expected=row)
    except IntegrationError as error:
        _checked(db, kind, False, error.message, expected=row)
    return metadata(db)


def _normalize_students(value):
    rows = value.get('students')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise IntegrationError('LMS javobi students ro‘yxatida 1–10000 talaba qaytarishi kerak')
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise IntegrationError('LMS talaba maydonlari noto‘g‘ri')
        sid = row.get('hemis_id')
        if not isinstance(sid, str) or not re.fullmatch(r'(?:H[0-9]{5,19}|[0-9]{6,20})', sid) or sid in seen:
            raise IntegrationError('LMS HEMIS ID noto‘g‘ri yoki takrorlangan')
        seen.add(sid)
        course = row.get('course')
        if type(course) is not int or not 1 <= course <= 8:
            raise IntegrationError('LMS kurs qiymati 1–8 oralig‘ida bo‘lsin')
        student = {'hemis_id': sid, 'course': course}
        for key in ('full_name', 'faculty', 'programme', 'student_group', 'education_form'):
            field = row.get(key)
            if not isinstance(field, str) or not 1 <= len(field.strip()) <= 250:
                raise IntegrationError('LMS talaba maydonlari to‘liq emas')
            student[key] = field.strip()
        status = row.get('status', 'active')
        if not isinstance(status, str) or not 1 <= len(status.strip()) <= 50:
            raise IntegrationError('LMS talaba holati noto‘g‘ri')
        student['status'] = status.strip()
        result.append(student)
    return result


def fetch_students(db, user):
    """Fetch/validate only. Caller transactionally imports then calls mark_sync.

    On expected network/schema failure, persist last_checked/last_error and return
    None. Caller must commit that metadata, returning a sanitized API error/result
    without rolling it back. No partial student writes occur in this module.
    """
    _admin(user)
    row = None
    try:
        row, token = _check_ready(db, 'lms')
        if not row['students_url']:
            raise IntegrationError('LMS talabalar API manzilini kiriting')
        result = _normalize_students(_request_json(row['students_url'], token))
        _checked(db, 'lms', True, expected=row)
        return result
    except IntegrationError as error:
        _checked(db, 'lms', False, error.message, expected=row)
        return None


def mark_sync(db, user, added, updated):
    _admin(user)
    if type(added) is not int or type(updated) is not int or added < 0 or updated < 0:
        raise IntegrationError('Sinxronlash natijasini tekshiring')
    db.execute('''UPDATE integration_config SET last_sync=?,last_sync_actor=?,last_added=?,last_updated=?
        WHERE kind='lms' ''', (_now(), user['id'], added, updated))
    return metadata(db)


def cleanup(db):
    """Remove orphan secrets only after commit, under the same writer lock as save."""
    if db.in_transaction:
        raise IntegrationError('Maxfiy fayllarni tozalashdan oldin tranzaksiyani yakunlang', 500)
    db.execute('BEGIN IMMEDIATE')
    try:
        live = {r[0] for r in db.execute('SELECT token_ref FROM integration_config WHERE token_ref IS NOT NULL')}
        directory = _secret_root(db)
        if directory.is_dir():
            for path in directory.iterdir():
                if re.fullmatch(r'[0-9a-f]{32}\.secret', path.name) and path.name not in live:
                    _private_path(path).unlink(missing_ok=True)
        db.commit()
    except Exception:
        db.rollback()
        raise
