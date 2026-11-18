import sqlite3
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'navbot'))
import student_registry
import workflow as w

class StudentStateTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE students(hemis_id TEXT PRIMARY KEY,status TEXT NOT NULL)')
        w.initialize(self.db)
        self.db.executemany('INSERT INTO students VALUES (?,?)',[('100000000001','unknown'),('100000000002','inactive')])
        student_registry.initialize(self.db)
        self.admin={'id':1,'role':'admin'}
    def tearDown(self):self.db.close()
    def test_existing_rows_active_once_then_manual_status_persists(self):
        self.assertEqual([r['status'] for r in self.db.execute('SELECT status FROM students')],['active','active'])
        result=student_registry.set_status(self.db,self.admin,{'hemis_id':'100000000001','status':'inactive'})
        self.assertEqual(result['status'],'inactive')
        student_registry.initialize(self.db)
        self.assertEqual(self.db.execute("SELECT status FROM students WHERE hemis_id='100000000001'").fetchone()[0],'inactive')
        student_registry.set_status(self.db,self.admin,{'hemis_id':'100000000001','status':'active'})
        self.assertEqual(self.db.execute("SELECT status FROM students WHERE hemis_id='100000000001'").fetchone()[0],'active')
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM audit WHERE action='student_status'").fetchone()[0],2)
    def test_permissions_invalid_status_and_missing_student(self):
        for user in (None,{'id':2,'role':'manager'},{'id':3,'role':'head'}):
            with self.assertRaises(w.Problem):student_registry.set_status(self.db,user,{'hemis_id':'100000000001','status':'inactive'})
        for payload in ({'hemis_id':'100000000001','status':'invalid'},{'hemis_id':'100000000001','status':None},{'hemis_id':1,'status':'inactive'},{'hemis_id':'999999999999','status':'inactive'}):
            with self.assertRaises(w.Problem):student_registry.set_status(self.db,self.admin,payload)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM students').fetchone()[0],2)
