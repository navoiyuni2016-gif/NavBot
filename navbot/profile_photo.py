"""Private, self-service profile photos; never accept a target user from clients."""
import base64
import binascii
from uuid import uuid4
import workflow as w


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS profile_photos(user_id INTEGER PRIMARY KEY, id TEXT NOT NULL, mime TEXT NOT NULL, body BLOB NOT NULL)')


def url(db, user):
    row = db.execute('SELECT id FROM profile_photos WHERE user_id=?', (user['id'],)).fetchone()
    return '/api/profile/photo/' + row['id'] if row else None


def update(db, user, data):
    if data.get('remove') is True:
        db.execute('DELETE FROM profile_photos WHERE user_id=?', (user['id'],))
    else:
        mime, encoded = data.get('mime'), data.get('data')
        if mime not in ('image/png', 'image/jpeg') or not isinstance(encoded, str) or len(encoded) > 2796204:
            raise w.Problem('PNG/JPEG va 2 MBgacha fayl tanlang')
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise w.Problem('Rasm fayli buzilgan')
        if not 0 < len(raw) <= 2 * 1024 * 1024:
            raise w.Problem('Rasm 2 MBdan oşmasligi kerak')
        if not raw.startswith(b'\x89PNG\r\n\x1a\n' if mime == 'image/png' else b'\xff\xd8\xff'):
            raise w.Problem('Rasm formati fayl bilan mos emas')
        db.execute('INSERT INTO profile_photos VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET id=excluded.id,mime=excluded.mime,body=excluded.body', (user['id'], str(uuid4()), mime, raw))
    w.audit(db, user, 'profile_photo_update', {'removed': data.get('remove') is True})
    return {'avatar_url': url(db, user)}


def read(db, user, photo_id):
    row = db.execute('SELECT body,mime FROM profile_photos WHERE user_id=? AND id=?', (user['id'], photo_id)).fetchone()
    if row is None:
        raise w.Problem('Rasm topilmadi', 404)
    return bytes(row['body']), row['mime']
