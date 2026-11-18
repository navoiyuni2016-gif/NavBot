import io
import json
import sqlite3
import unittest
from xml.sax.saxutils import escape
from zipfile import ZipFile
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'navbot'))
import student_xlsx
import workflow as w


def workbook(rows):
    stream=io.BytesIO()
    with ZipFile(stream,'w') as z:
        data='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        for i,row in enumerate([student_xlsx.HEADERS]+rows,1):
            data+='<row>'+''.join(f'<c r="{chr(65+j)}{i}" t="inlineStr"><is><t>{escape(v)}</t></is></c>' for j,v in enumerate(row))+'</row>'
        z.writestr('xl/worksheets/sheet1.xml',data+'</sheetData></worksheet>')
    return stream.getvalue()

class StudentXlsxTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        self.db.execute("CREATE TABLE students(hemis_id TEXT PRIMARY KEY,full_name TEXT,faculty TEXT,course INTEGER,education_form TEXT,gender TEXT,education_type TEXT,source_json TEXT,programme TEXT,student_group TEXT,status TEXT DEFAULT 'active')")
        w.initialize(self.db);self.user={'id':1,'role':'admin'}
        self.row=['123456789012','Ism FAMILIYA O‘g‘li','Erkak','2-kurs','Fakultet','Bakalavr','Kunduzgi']
    def tearDown(self):self.db.close()
    def test_preserve_every_source_cell_and_repeat_without_changes(self):
        raw=workbook([self.row]);self.assertEqual(student_xlsx.insert(self.db,self.user,raw),{'added':1,'updated':0,'skipped':0,'total':1})
        stored=dict(self.db.execute('SELECT * FROM students').fetchone())
        self.assertEqual(list(json.loads(stored['source_json']).values()),self.row)
        self.assertEqual(stored['programme'],'');self.assertEqual(stored['student_group'],'')
        self.assertEqual(stored['course'],2);self.assertEqual(stored['status'],'active')
        changed=self.row.copy();changed[1]='Other value'
        result=student_xlsx.insert(self.db,self.user,workbook([changed]));self.assertEqual(result['skipped'],1)
        self.assertEqual(dict(self.db.execute('SELECT * FROM students').fetchone()),stored)
    def test_invalid_duplicate_rejects_whole_import(self):
        with self.assertRaises(w.Problem):student_xlsx.insert(self.db,self.user,workbook([self.row,self.row]))
        self.assertEqual(self.db.execute('SELECT count(*) FROM students').fetchone()[0],0)
    def test_bad_course_and_bad_archive_rejected(self):
        bad=self.row.copy();bad[3]='9-kurs'
        for raw in [b'not an archive',workbook([bad])]:
            with self.assertRaises(w.Problem):student_xlsx.parse(raw)
    def test_only_admin_may_import(self):
        with self.assertRaises(w.Problem):student_xlsx.insert(self.db,{'id':2,'role':'manager'},workbook([self.row]))
