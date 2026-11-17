"""Admin-managed raster branding, served as images rather than executable markup."""
import base64
import binascii
import json
from uuid import uuid4, UUID
import workflow as w

ICONS = {
    'requests': ('Murojaatlar', '▤'), 'phone': ('Yangi murojaat', '＋'),
    'report': ('Hisobot', '▥'), 'students': ('Talabalar bazasi', '♧'),
    'archive': ('Arxiv', '▣'), 'notifications': ('Bildirişnomalar', '♧'),
    'profile': ('Mening profilim', '♙'), 'users': ('Xodimlar va loginlar', '♧'),
    'settings': ('Tizim sozlamalari', '⚙'), 'audit': ('Audit jurnali', '▤'),
    'audio': ('Ovozli çaqiruv', '♫'), 'integrations': ('Integratsiyalar', '↔'),
    'devices': ('Kiosk, TV va tablo', '▣'), 'service': ('Xizmat belgisi', '▤'),
    'add': ('Qöşiş belgisi', '＋'), 'back': ('Orqaga', '←'),
    'forward': ('Oldinga', '→'), 'open': ('Havolani oçiş', '↗'),
    'warning': ('Ogohlantiriş belgisi', '!'), 'confirm': ('Tasdiq belgisi', '✓'), 'clock': ('Muddat belgisi', '◷'),
    'light': ('Yoruğ rejim', '☀'), 'dark': ('Qorong‘i rejim', '☾'),
}


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS branding_assets(id TEXT PRIMARY KEY,mime TEXT NOT NULL,body BLOB NOT NULL)')


def targets():
    return {'targets': [{'key': k, 'label': v[0], 'glyph': v[1]} for k, v in ICONS.items()]}


def update(db, user, data, config):
    w.need(user, ('admin',))
    target, key = data.get('target'), data.get('key')
    if target not in ('system_logo', 'kiosk_logo', 'icon') or (target == 'icon' and (not isinstance(key, str) or key not in ICONS)):
        raise w.Problem('Belgi joyini tanlang')
    current = config['branding']
    old = current['icons'].get(key) if target == 'icon' else current.get(target)
    url = None
    if data.get('remove') is not True:
        mime = data.get('mime')
        encoded = data.get('data')
        if mime not in ('image/png', 'image/jpeg') or not isinstance(encoded, str) or len(encoded) > 2796204:
            raise w.Problem('PNG/JPEG va 2 MBgacha fayl tanlang')
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError, binascii.Error):
            raise w.Problem('Rasm fayli buzilgan')
        if not 0 < len(raw) <= 2 * 1024 * 1024:
            raise w.Problem('Rasm 2 MBdan oşmasligi kerak')
        if not raw.startswith(b'\x89PNG\r\n\x1a\n' if mime == 'image/png' else b'\xff\xd8\xff'):
            raise w.Problem('Rasm formati fayl bilan mos emas')
        used = db.execute('SELECT COALESCE(SUM(length(body)),0) FROM branding_assets WHERE id!=?', ((old or '').rsplit('/', 1)[-1],)).fetchone()[0]
        if used + len(raw) > 40 * 1024 * 1024:
            raise w.Problem('Rasmlar ombori töldi')
        asset_id = str(uuid4())
        db.execute('INSERT INTO branding_assets VALUES (?,?,?)', (asset_id, mime, raw))
        url = '/media/branding/' + asset_id
    if target == 'icon':
        if url:
            current['icons'][key] = url
        else:
            current['icons'].pop(key, None)
    else:
        current[target] = url
    db.execute('INSERT INTO settings(id,value) VALUES (1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value', (json.dumps(config, ensure_ascii=False),))
    if old:
        db.execute('DELETE FROM branding_assets WHERE id=?', (old.rsplit('/', 1)[-1],))
    w.audit(db, user, 'branding_update', {'target': target, 'key': key, 'removed': url is None})
    return {'settings': config}


def read(db, asset_id):
    try:
        if str(UUID(asset_id)) != asset_id:
            raise ValueError()
    except ValueError:
        raise w.Problem('Rasm topilmadi', 404)
    row = db.execute('SELECT body,mime FROM branding_assets WHERE id=?', (asset_id,)).fetchone()
    if row is None:
        raise w.Problem('Rasm topilmadi', 404)
    return bytes(row['body']), row['mime']
