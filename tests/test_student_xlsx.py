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


def workbook(rows, headers=None):
    stream=io.BytesIO()
    with ZipFile(stream,'w') as z:
        data='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        for i,row in enumerate([headers or student_xlsx.HEADERS]+rows,1):
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
    def test_eight_column_code_group_and_source_preserved(self):
        row=['123456789012','Example Student','2-kurs','Faculty','TEST-201','00123456','Bakalavr','Kunduzgi']
        raw=workbook([row],student_xlsx.CODE_HEADERS)
        self.assertEqual(student_xlsx.insert(self.db,self.user,raw)['added'],1)
        stored=dict(self.db.execute('SELECT * FROM students').fetchone())
        self.assertEqual(stored['programme'],'00123456');self.assertEqual(stored['student_group'],'TEST-201')
        self.assertEqual(stored['gender'],'');self.assertEqual(stored['status'],'active')
        self.assertEqual(list(json.loads(stored['source_json']).values()),row)
        self.assertEqual(student_xlsx.insert(self.db,self.user,raw)['skipped'],1)
        for code in ('1234567','12AB3456','123456789'):
            bad=row.copy();bad[5]=code
            with self.assertRaises(w.Problem):student_xlsx.parse(workbook([bad],student_xlsx.CODE_HEADERS))

    def test_new_layout_only_enriches_missing_code_group_on_existing_ids(self):
        student_xlsx.insert(self.db,self.user,workbook([self.row]))
        self.db.execute("UPDATE students SET status='inactive'")
        before=dict(self.db.execute('SELECT * FROM students').fetchone())
        row=[self.row[0],'Different name','3-kurs','Different faculty','TEST-301','60230100','Magistr','Sirtqi']
        result=student_xlsx.insert(self.db,self.user,workbook([row],student_xlsx.CODE_HEADERS))
        self.assertEqual(result,{'added':0,'updated':1,'skipped':0,'total':1})
        after=dict(self.db.execute('SELECT * FROM students').fetchone())
        self.assertEqual(after,{**before,'programme':'60230100','student_group':'TEST-301'})
        row[4]='OTHER';row[5]='99999999'
        self.assertEqual(student_xlsx.insert(self.db,self.user,workbook([row],student_xlsx.CODE_HEADERS))['skipped'],1)
        self.assertEqual(dict(self.db.execute('SELECT * FROM students').fetchone()),after)

    def test_only_admin_may_import(self):
        with self.assertRaises(w.Problem):student_xlsx.insert(self.db,{'id':2,'role':'manager'},workbook([self.row]))
