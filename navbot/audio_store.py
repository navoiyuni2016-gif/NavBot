"""Recorded announcements stored locally; public media contains no student data."""
import base64
import binascii
import io
import re
import struct
import uuid
import wave
from pathlib import Path
import workflow as w

LANGUAGES = ('uz', 'ru', 'en')
MAX_BYTES = 5 * 1024 * 1024
MAX_TOTAL = 200 * 1024 * 1024


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS audio_clips (
            id TEXT PRIMARY KEY, lang TEXT NOT NULL, slot TEXT NOT NULL, label TEXT NOT NULL,
            mime TEXT NOT NULL, size INTEGER NOT NULL, body BLOB NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(lang,slot)
        );
        CREATE TABLE IF NOT EXISTS audio_modes (lang TEXT PRIMARY KEY, mode TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audio_layouts (lang TEXT PRIMARY KEY, layout TEXT NOT NULL);
    ''')


def metadata(db):
    modes = {lang: 'speech' for lang in LANGUAGES}
    modes.update({r['lang']: r['mode'] for r in db.execute('SELECT * FROM audio_modes')})
    clips = [dict(r) for r in db.execute('SELECT id,lang,slot,label,mime,size,created_at FROM audio_clips ORDER BY lang,slot')]
    for clip in clips:
        clip['url'] = '/media/audio/' + clip['id']
    layouts={lang:'legacy' for lang in LANGUAGES}
    layouts.update({r['lang']:r['layout'] for r in db.execute('SELECT * FROM audio_layouts')})
    return {'modes': modes, 'layouts':layouts, 'clips': clips}


def validate_slot(slot):
    if not isinstance(slot, str):
        raise w.Problem('Ovoz qismini tanlang')
    if slot in ('prefix', 'between', 'suffix','intro') or re.fullmatch(r'letter:[A-ZÖĞŞÇ]',slot):
        return slot
    match = re.fullmatch(r'(number|operator):([1-9][0-9]{0,8})', slot)
    if match and (match[1] != 'operator' or int(match[2]) <= 30):
        return slot
    match = re.fullmatch(r'call:(?:[A-ZÖĞŞÇ]:)?([1-9][0-9]{0,8}):([1-9][0-9]?)', slot)
    if match and int(match[2]) <= 30:
        return slot
    raise w.Problem('Ovoz qismi yoki raqam notoğri')


def validate_audio(raw, mime):
    if not 0 < len(raw) <= MAX_BYTES:
        raise w.Problem('Ovoz fayli 5 MBdan oşmasligi kerak')
    if mime == 'audio/wav':
        try:
            with wave.open(io.BytesIO(raw), 'rb') as sound:
                if sound.getnchannels() not in (1, 2) or not 8000 <= sound.getframerate() <= 96000 or sound.getsampwidth() not in (1, 2, 3, 4):
                    raise ValueError()
                frames = sound.getnframes()
                if not 0 < frames <= sound.getframerate() * 120:
                    raise ValueError()
                expected = frames * sound.getnchannels() * sound.getsampwidth()
                if len(sound.readframes(frames)) != expected:
                    raise ValueError()
        except (wave.Error, EOFError, ValueError, struct.error):
            raise w.Problem('WAV fayli buzilgan yoki qo‘llanmaydi (PCM, 120 soniyagaça)')
    elif mime == 'audio/mpeg':
        offset = 0
        if raw.startswith(b'ID3'):
            if len(raw) < 10 or any(b > 127 for b in raw[6:10]):
                raise w.Problem('MP3 fayli buzilgan')
            length = sum(b << shift for b, shift in zip(raw[6:10], (21, 14, 7, 0)))
            offset = 10 + length + (10 if raw[5] & 0x10 else 0)
        if len(raw) < offset + 4:
            raise w.Problem('MP3 ovoz ma’lumoti topilmadi')
        header = int.from_bytes(raw[offset:offset + 4], 'big')
        if (header >> 21 != 0x7ff or (header >> 19) & 3 == 1 or (header >> 17) & 3 == 0 or
                (header >> 12) & 15 in (0, 15) or (header >> 10) & 3 == 3):
            raise w.Problem('MP3 fayli sarlavhasi notoğri')
        version, layer = (header >> 19) & 3, (header >> 17) & 3
        bitrate_index, rate_index, padding = (header >> 12) & 15, (header >> 10) & 3, (header >> 9) & 1
        mpeg1 = {3: [32,64,96,128,160,192,224,256,288,320,352,384,416,448],
                 2: [32,48,56,64,80,96,112,128,160,192,224,256,320,384],
                 1: [32,40,48,56,64,80,96,112,128,160,192,224,256,320]}
        lower = [32,48,56,64,80,96,112,128,144,160,176,192,224,256] if layer == 3 else [8,16,24,32,40,48,56,64,80,96,112,128,144,160]
        bitrate = (mpeg1[layer] if version == 3 else lower)[bitrate_index - 1] * 1000
        rate = [44100,48000,32000][rate_index] // (1 if version == 3 else 2 if version == 2 else 4)
        frame_length = (12 * bitrate // rate + padding) * 4 if layer == 3 else ((72 if layer == 1 and version != 3 else 144) * bitrate // rate + padding)
        if len(raw) < offset + frame_length:
            raise w.Problem('MP3 ovoz ma’lumoti töliq emas')
    else:
        raise w.Problem('Faqat MP3 yoki WAV faylini yuklang')


def upload(db, user, data):
    w.need(user, ('admin',))
    lang = data.get('lang')
    if lang not in LANGUAGES:
        raise w.Problem('Ovoz tilini tanlang')
    slot = validate_slot(data.get('slot'))
    label = w.text(data, 'label', 150) or slot
    try:
        encoded = data.get('data')
        if not isinstance(encoded, str) or len(encoded) > (MAX_BYTES + 2) // 3 * 4:
            raise ValueError()
        raw = base64.b64decode(encoded, validate=True)
    except (TypeError, ValueError, binascii.Error):
        raise w.Problem('Ovoz fayli buzilgan yoki juda katta')
    mime = data.get('mime')
    validate_audio(raw, mime)
    used = db.execute('SELECT COALESCE(SUM(size),0) FROM audio_clips WHERE NOT(lang=? AND slot=?)', (lang, slot)).fetchone()[0]
    if used + len(raw) > MAX_TOTAL:
        raise w.Problem('Ovozlar uçun 200 MB limit töldi; eski fayllarni öçiring')
    clip_id = str(uuid.uuid4())
    db.execute('DELETE FROM audio_clips WHERE lang=? AND slot=?', (lang, slot))
    db.execute('INSERT INTO audio_clips VALUES (?,?,?,?,?,?,?,?)', (clip_id, lang, slot, label, mime, len(raw), raw, w.now()))
    w.audit(db, user, 'audio_upload', {'lang': lang, 'slot': slot, 'bytes': len(raw)})
    return {'saved':True,'id':clip_id} if data.get('compact') is True else metadata(db)


def remove(db, user, data):
    w.need(user, ('admin',))
    clip_id = data.get('id')
    if not isinstance(clip_id, str):
        raise w.Problem('Ovoz faylini tanlang')
    row = db.execute('SELECT lang,slot FROM audio_clips WHERE id=?', (clip_id,)).fetchone()
    if not row:
        raise w.Problem('Ovoz fayli topilmadi', 404)
    db.execute('DELETE FROM audio_clips WHERE id=?', (clip_id,))
    w.audit(db, user, 'audio_delete', {'lang': row['lang'], 'slot': row['slot']})
    return metadata(db)


def set_mode(db, user, data):
    w.need(user, ('admin',))
    lang, mode = data.get('lang'), data.get('mode')
    if lang not in LANGUAGES or mode not in ('speech', 'recorded'):
        raise w.Problem('Ovoz tili yoki usuli notoğri')
    layout=data.get('layout')
    if layout is not None and layout not in ('legacy','numbered'):
        raise w.Problem('Ovoz tartibini tanlang')
    if layout is not None:
        db.execute('INSERT INTO audio_layouts VALUES (?,?) ON CONFLICT(lang) DO UPDATE SET layout=excluded.layout',(lang,layout))
    db.execute('INSERT INTO audio_modes VALUES (?,?) ON CONFLICT(lang) DO UPDATE SET mode=excluded.mode', (lang, mode))
    w.audit(db, user, 'audio_mode', {'lang': lang, 'mode': mode})
    return metadata(db)


def plan(db, lang, ticket, operator, prefix='A'):
    if not isinstance(prefix,str) or not re.fullmatch(r'[A-ZÖĞŞÇ]',prefix):
        raise w.Problem('Navbat harfini tanlang')
    if lang not in LANGUAGES or type(ticket) is not int or not 1 <= ticket <= 999999999 or type(operator) is not int or not 1 <= operator <= 30:
        raise w.Problem('Ovoz tilini va çaqiruv raqamlarini tekşiring')
    mode = db.execute('SELECT mode FROM audio_modes WHERE lang=?', (lang,)).fetchone()
    if not mode or mode['mode'] == 'speech':
        return {'mode': 'speech', 'urls': [], 'missing': []}
    available = {r['slot']: '/media/audio/' + r['id'] for r in db.execute('SELECT slot,id FROM audio_clips WHERE lang=?', (lang,))}
    full_call = f'call:{prefix}:{ticket}:{operator}'
    if full_call not in available and prefix=='A':
        full_call=f'call:{ticket}:{operator}'
    if full_call in available:
        return {'mode': 'recorded', 'urls': [available[full_call]], 'missing': []}
    layout=db.execute('SELECT layout FROM audio_layouts WHERE lang=?',(lang,)).fetchone()
    numbered=[f'letter:{prefix}',f'number:{ticket}',f'operator:{operator}']
    legacy=['prefix',f'number:{ticket}','between',f'operator:{operator}','suffix']
    # A greeting is optional; the actual letter, number and operator never are.
    # Keep complete legacy sequences intact. Recognize numbered packs saved
    # before their layout was selected, without modifying recordings/settings.
    legacy_complete=prefix=='A' and all(slot in available for slot in legacy)
    use_numbered=(layout is not None and layout['layout']=='numbered') or (
        not legacy_complete and all(slot in available for slot in numbered))
    if use_numbered:
        slots=(['intro'] if 'intro' in available else [])+numbered
    elif prefix!='A':
        return {'mode':'incomplete','urls':[],'missing':[f'letter:{prefix}']}
    else:
        slots=legacy
    missing = [s for s in slots if s not in available]
    return {'mode': 'incomplete' if missing else 'recorded', 'urls': [] if missing else [available[s] for s in slots], 'missing': missing}


def read(db, clip_id):
    try:
        if str(uuid.UUID(clip_id)) != clip_id:
            raise ValueError()
    except (ValueError, AttributeError):
        raise w.Problem('Ovoz fayli topilmadi', 404)
    row = db.execute('SELECT body,mime FROM audio_clips WHERE id=?', (clip_id,)).fetchone()
    if not row:
        raise w.Problem('Ovoz fayli topilmadi', 404)
    return bytes(row['body']), row['mime']


def install_pack(db,user):
    w.need(user,('admin',))
    directory=Path(__file__).resolve().parent/'voice'/'uz'
    for filename,slot in [('default.wav','intro'),('sA.wav','letter:A'),('s1.wav','number:1'),('p1.wav','operator:1')]:
        raw=(directory/filename).read_bytes()
        upload(db,user,{'lang':'uz','slot':slot,'label':filename,'mime':'audio/wav','data':base64.b64encode(raw).decode('ascii'),'compact':True})
    return set_mode(db,user,{'lang':'uz','mode':'recorded','layout':'numbered'})
