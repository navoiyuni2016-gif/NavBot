"""Private append-only request attachments. Downloads require request visibility."""
import base64
import binascii
import hashlib
import io
from pathlib import PurePosixPath
import re
import uuid
from zipfile import ZipFile, BadZipFile
import workflow as w

LIMIT = 10 * 1024 * 1024
MIMES = {'.pdf':'application/pdf', '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg',
         '.txt':'text/plain; charset=utf-8', '.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         '.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
         '.doc':'application/msword', '.xls':'application/vnd.ms-excel'}


def initialize(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS attachments (
        id TEXT PRIMARY KEY, request_id INTEGER NOT NULL, request_key TEXT NOT NULL,
        name TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL, digest TEXT NOT NULL,
        body BLOB NOT NULL, uploader_id INTEGER NOT NULL, created_at TEXT NOT NULL,
        UNIQUE(request_id,request_key)
    ); CREATE INDEX IF NOT EXISTS attachment_request ON attachments(request_id);''')


def list_for(db, request_id):
    result = [dict(row) for row in db.execute('SELECT a.id,a.name,a.mime,a.size,a.uploader_id,a.created_at,u.full_name uploader FROM attachments a LEFT JOIN users u ON u.id=a.uploader_id WHERE request_id=? ORDER BY a.rowid', (request_id,))]
    for item in result:
        item['url'] = '/api/attachment/' + item['id']
    return result


def validate(name, raw):
    if not isinstance(name, str) or not 1 <= len(name) <= 180 or name.strip() != name or re.search(r'[\\/\x00-\x1f\x7f]', name) or name in ('.','..'):
        raise w.Problem('Fayl nomini tekşiring')
    extension = PurePosixPath(name).suffix.lower()
    if extension not in MIMES:
        raise w.Problem('PDF, Word, Excel, TXT, PNG yoki JPG faylini tanlang')
    if not 0 < len(raw) <= LIMIT:
        raise w.Problem('Har bir fayl 10 MBdan oşmasligi kerak')
    if extension == '.pdf' and not raw.startswith(b'%PDF-'):
        raise w.Problem('PDF fayli buzilgan')
    if extension == '.png' and not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise w.Problem('PNG fayli buzilgan')
    if extension in ('.jpg','.jpeg') and not raw.startswith(b'\xff\xd8\xff'):
        raise w.Problem('JPG fayli buzilgan')
    if extension in ('.doc','.xls') and not raw.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        raise w.Problem('Word yoki Excel fayli buzilgan')
    if extension == '.txt':
        try:
            text = raw.decode('utf-8-sig')
            if '\x00' in text:
                raise ValueError()
        except (ValueError, UnicodeError):
            raise w.Problem('TXT fayli UTF-8 bölişi kerak')
    if extension in ('.docx','.xlsx'):
        try:
            with ZipFile(io.BytesIO(raw)) as archive:
                names = archive.namelist()
                part = 'word/document.xml' if extension == '.docx' else 'xl/workbook.xml'
                if len(names) > 5000 or part not in names or '[Content_Types].xml' not in names or sum(i.file_size for i in archive.infolist()) > 80 * 1024 * 1024:
                    raise ValueError()
                if any(n.lower().endswith(('vbaproject.bin','.exe','.js')) for n in names):
                    raise ValueError()
        except (BadZipFile, ValueError, OSError):
            raise w.Problem('Word/Excel fayli buzilgan yoki makrosli format qöllanmaydi')
    return MIMES[extension]


def upload(db, user, data):
    w.need(user, ('admin','manager','executor','head','director'))
    row = w.get_request(db, user, data.get('id'))
    if row['status'] == 'closed':
        raise w.Problem('Yopilgan arizaga yangi fayl biriktirib bölmaydi',409)
    key = str(uuid.UUID(data.get('key','')))
    name = data.get('name')
    encoded = data.get('data')
    try:
        if not isinstance(encoded,str) or len(encoded) > (LIMIT+2)//3*4:
            raise ValueError()
        raw = base64.b64decode(encoded,validate=True)
    except (ValueError,TypeError,binascii.Error):
        raise w.Problem('Fayl buzilgan yoki juda katta')
    mime = validate(name,raw)
    digest = hashlib.sha256(raw).hexdigest()
    existing = db.execute('SELECT * FROM attachments WHERE request_id=? AND request_key=?',(row['id'],key)).fetchone()
    if existing:
        if existing['digest'] != digest or existing['name'] != name:
            raise w.Problem('Fayl sörov kaliti boşqa faylga tegishli',409)
        return {'request':w.serialize(db,row)}
    if type(data.get('version')) is not int or data['version'] != row['version']:
        raise w.Problem('Ariza özgargan. Yangilab qayta urinib köring',409)
    count,total=db.execute('SELECT COUNT(*),COALESCE(SUM(size),0) FROM attachments WHERE request_id=?',(row['id'],)).fetchone()
    if count>=10 or total+len(raw)>50*1024*1024:
        raise w.Problem('Arizaga eng köpi 10 ta fayl va jami 50 MB biriktiriladi')
    file_id=str(uuid.uuid4())
    db.execute('INSERT INTO attachments VALUES (?,?,?,?,?,?,?,?,?,?)',(file_id,row['id'],key,name,mime,len(raw),digest,raw,user['id'],w.now()))
    db.execute('UPDATE requests SET version=version+1,updated_at=? WHERE id=?',(w.now(),row['id']))
    w.record(db,row['id'],user,'attachment_upload',{'name':name,'bytes':len(raw)})
    return {'request':w.serialize(db,db.execute('SELECT * FROM requests WHERE id=?',(row['id'],)).fetchone())}


def download(db,user,file_id):
    w.need(user, ('admin','manager','executor','head','director'))
    row=db.execute('SELECT * FROM attachments WHERE id=?',(file_id,)).fetchone()
    if not row:
        raise w.Problem('Fayl topilmadi',404)
    w.get_request(db,user,row['request_id'])
    return bytes(row['body']),row['mime'],row['name']
