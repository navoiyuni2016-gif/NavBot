from pathlib import Path
import sqlite3
from test_workflow import WorkflowAcceptance

class StudentSearchAcceptance(WorkflowAcceptance):
    def search(self,client,query):return client.request('/api/students/search',{'query':query})
    def test_private_exact_id_name_order_case_and_apostrophes(self):
        self.assertEqual(self.search(self.public,'Talaba')[0],401)
        manager=self.client('manager')
        result=self.search(manager,'100000000001');self.assertEqual(result[0],200)
        self.assertEqual(result[1]['students'][0]['hemis_id'],'100000000001')
        for query in ('sinov talaba bir','BIR TALABA','talaba'):
            status,result,_=self.search(manager,query);self.assertEqual(status,200)
            self.assertIn('100000000001',[s['hemis_id'] for s in result['students']])
        with sqlite3.connect(Path(self.temp.name)/'test.sqlite3') as db:
            db.execute("INSERT INTO students(hemis_id,full_name,faculty,programme,course,student_group) VALUES ('123456789012',?, 'F', 'P', 1, 'G')",("RO‘ZIBOYEV SHOHJAHON",))
            db.execute("INSERT INTO students(hemis_id,full_name,faculty,programme,course,student_group) VALUES ('123456789013',?, 'F', 'P', 1, 'G')",('АЛИЕВ ШОҲЖАҲОН',))
        for query in ("ro'ziboyev",'röziboyev','şohjahon'):
            self.assertEqual(self.search(manager,query)[1]['students'][0]['hemis_id'],'123456789012')
        self.assertEqual(self.search(manager,'алиев')[1]['students'][0]['hemis_id'],'123456789013')
    def test_bounded_results_and_invalid_or_injected_query(self):
        manager=self.client('manager')
        for query in (None,12,'','a','%'*10,'x'*121):self.assertEqual(self.search(manager,query)[0],400)
        status,result,_=self.search(manager,"' OR 1=1 --");self.assertEqual(status,200);self.assertEqual(result['students'],[])
        with sqlite3.connect(Path(self.temp.name)/'test.sqlite3') as db:
            for n in range(25):
                db.execute("INSERT INTO students(hemis_id,full_name,faculty,programme,course,student_group) VALUES (?,?, 'F', 'P', 1, 'G')",(str(200000000000+n),'Shared Family '+str(n)))
        status,result,_=self.search(manager,'shared');self.assertEqual(status,200)
        self.assertEqual(len(result['students']),20);self.assertTrue(result['more'])

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in StudentSearchAcceptance.__dict__:setattr(StudentSearchAcceptance,_name,None)
del WorkflowAcceptance
