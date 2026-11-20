"""Bulk request loading must preserve data/permissions without N+1 reads."""
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'navbot'))
import app
import workflow as w

class RequestLoading(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.previous=app.DATABASE
        app.DATABASE=Path(self.temp.name)/'test.sqlite3';app.initialize(True)
        self.db=app.connection()
    def tearDown(self):self.db.close();app.DATABASE=self.previous;self.temp.cleanup()
    def test_bulk_results_equal_single_request_data_and_keep_query_count_bounded(self):
        admin=dict(self.db.execute("SELECT * FROM users WHERE username='admin'").fetchone())
        for i in range(405):
            ticket=app.mutate(self.db,'/api/ticket',{'key':str(uuid4()),'lang':'uz','section':i%5,'service':0},None)
            self.db.execute('UPDATE requests SET student_id=?,manager_id=?,assignee_id=? WHERE ticket_id=?',('100000000001',admin['id'],admin['id'],ticket['id']))
        self.db.execute("UPDATE requests SET student_snapshot=? WHERE id=1",('{"full_name":"Saved Snapshot","programme":"00123456"}',))
        self.db.execute("INSERT INTO attachments(id,request_id,request_key,name,mime,size,digest,body,uploader_id,created_at) VALUES('file',1,'key','test.txt','text/plain',4,'hash',X'74657374',?,?)",(admin['id'],w.now()))
        expected=[w.serialize(self.db,r) for r in self.db.execute('SELECT * FROM requests ORDER BY id DESC')]
        sql=[];self.db.set_trace_callback(sql.append)
        actual=w.requests(self.db,admin)
        self.db.set_trace_callback(None)
        self.assertEqual(actual,expected)
        self.assertLessEqual(len(sql),12,'List must batch related data across the SQLite parameter limit')
        self.assertEqual(actual[-1]['student']['full_name'],'Saved Snapshot')
        self.assertNotIn('body',actual[-1]['attachments'][0])
        self.assertEqual(actual[-1]['attachments'][0]['url'],'/api/attachment/file')
        executor=dict(self.db.execute("SELECT * FROM users WHERE username='executor'").fetchone())
        self.assertEqual(w.requests(self.db,executor),[])
        self.db.execute('UPDATE requests SET assignee_id=? WHERE id=1',(executor['id'],))
        self.assertEqual([r['id'] for r in w.requests(self.db,executor)],[1])
    def test_audit_request_lookup_does_not_scan_the_whole_journal(self):
        plan=[r['detail'] for r in self.db.execute("EXPLAIN QUERY PLAN SELECT id FROM audit WHERE request_ref=?",('example',))]
        self.assertTrue(any('SEARCH' in row and 'request_ref' in row for row in plan),plan)

    def test_warm_name_search_uses_current_rows_after_rename_and_deletion(self):
        self.assertTrue(w.search_students(self.db,'talaba bir')['students'])
        self.db.execute("UPDATE students SET full_name='Renamed Person' WHERE hemis_id='100000000001'")
        self.assertEqual(w.search_students(self.db,'talaba bir')['students'],[])
        self.assertEqual(w.search_students(self.db,'renamed')['students'][0]['hemis_id'],'100000000001')
        self.db.execute("DELETE FROM students WHERE hemis_id='100000000001'")
        self.assertEqual(w.search_students(self.db,'renamed')['students'],[])
