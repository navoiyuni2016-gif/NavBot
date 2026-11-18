"""Read the university's seven-column XLSX without changing source text."""
import base64
import io
import json
import re
from zipfile import ZipFile, BadZipFile
from xml.etree import ElementTree as ET
import workflow as w

HEADERS = ['Talaba ID', 'To‘liq ismi', 'Jins', 'Kurs', 'Fakultet', 'Ta’lim turi', 'Ta’lim shakli']
NS = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def parse(raw):
    if len(raw) > 5 * 1024 * 1024:
        raise w.Problem('Excel fayli 5 MBdan oşmasligi kerak')
    try:
        with ZipFile(io.BytesIO(raw)) as z:
            if sum(i.file_size for i in z.infolist()) > 30 * 1024 * 1024:
                raise ValueError()
            strings = []
            if 'xl/sharedStrings.xml' in z.namelist():
                strings = [''.join(t.text or '' for t in si.iterfind('.//s:t', NS)) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
            rows = []
            for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('s:sheetData/s:row', NS):
                values = [''] * 7
                for cell in row.findall('s:c', NS):
                    if cell.find('s:f', NS) is not None:
                        raise ValueError()
                    col = re.fullmatch(r'([A-Z]+)[0-9]+', cell.attrib['r'])[1]
                    if col not in 'ABCDEFG' or len(col) != 1:
                        if cell.find('s:v', NS) is not None:
                            raise ValueError()
                        continue
                    v = cell.find('s:v', NS)
                    text = v.text or '' if v is not None else ''
                    if cell.get('t') == 's':
                        text = strings[int(text)]
                    elif cell.get('t') == 'inlineStr':
                        text = ''.join(t.text or '' for t in cell.iterfind('.//s:t', NS))
                    values[ord(col)-65] = text
                if any(values):
                    rows.append(values)
        if not rows or rows[0] != HEADERS or not 1 <= len(rows)-1 <= 10000:
            raise ValueError()
        result, seen = [], set()
        for values in rows[1:]:
            sid, name, gender, course, faculty, education_type, form = values
            # Keep all original fields, including the displayed course, in source_json.
            w.validate_id(sid)
            match = re.fullmatch(r'([1-8])(?:-kurs)?', course)
            if sid in seen or not match or not all(values) or any(len(v)>250 for v in values):
                raise ValueError()
            seen.add(sid)
            result.append((sid,name,faculty,int(match[1]),form,gender,education_type,json.dumps(dict(zip(HEADERS,values)),ensure_ascii=False)))
        return result
    except (BadZipFile, KeyError, IndexError, TypeError, ValueError, ET.ParseError):
        raise w.Problem('Excel ustunlari yoki talaba yozuvlarini tekşiring; import bekor qilindi')


def insert(db, user, raw):
    w.need(user, ('admin',))
    rows = parse(raw)
    added = 0
    for row in rows:
        cursor=db.execute("INSERT INTO students(hemis_id,full_name,faculty,course,education_form,gender,education_type,source_json,programme,student_group,status) VALUES (?,?,?,?,?,?,?,?,'','','active') ON CONFLICT(hemis_id) DO NOTHING", row)
        added += cursor.rowcount
    w.audit(db,user,'students_import',{'added':added,'updated':0,'skipped':len(rows)-added,'source':'xlsx'})
    return {'added':added,'updated':0,'skipped':len(rows)-added,'total':len(rows)}


def upload(db,user,data):
    w.need(user,('admin',))
    encoded=data.get('data')
    if not isinstance(encoded,str) or len(encoded)>6990508:
        raise w.Problem('Excel fayli 5 MBdan oşmasligi kerak')
    try:
        raw=base64.b64decode(encoded,validate=True)
    except ValueError:
        raise w.Problem('Excel faylini tekşiring')
    return insert(db,user,raw)
