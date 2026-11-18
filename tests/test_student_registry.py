from uuid import uuid4
from test_workflow import WorkflowAcceptance

class StudentRegistryAcceptance(WorkflowAcceptance):
    def preview(self, client, ids):
        return self.ok(client,'/api/admin/students/preview',{'ids':ids})

    def remove(self, client, preview, **extra):
        return client.request('/api/admin/students/delete',{'token':preview['token'],'confirm_count':preview['count'],'password':'Navbot-Test-2026!',**extra})

    def test_permissions_reauthentication_snapshot_and_replay(self):
        admin=self.client('admin');manager=self.client('manager');head=self.client('head')
        students=self.ok(admin,'/api/students')['students'];ids=[s['hemis_id'] for s in students]
        self.assertEqual(self.public.request('/api/admin/students/preview',{'ids':ids})[0],401)
        self.assertEqual(head.request('/api/admin/students/preview',{'ids':ids})[0],403)
        preview=self.preview(admin,ids[:1])
        self.assertEqual(self.remove(manager,preview)[0],403)
        self.assertEqual(self.remove(admin,preview,password='incorrect')[0],401)
        self.assertEqual(self.remove(admin,preview,confirm_count=999)[0],400)
        self.assertEqual(len(self.ok(admin,'/api/students')['students']),len(students))
        # Arrivals after the preview are not implicitly deleted.
        added={**students[0],'hemis_id':'900000000001','full_name':'New Arrival'}
        self.ok(admin,'/api/students/import',{'students':[added]})
        self.assertEqual(self.remove(admin,preview)[0],200)
        self.assertEqual(self.remove(admin,preview)[0],409)
        self.assertIsNotNone(self.ok(admin,'/api/me')['user'])
        remaining=self.ok(admin,'/api/students')['students']
        self.assertIn(added['hemis_id'],[s['hemis_id'] for s in remaining]);self.assertNotIn(ids[0],[s['hemis_id'] for s in remaining])

    def test_changed_rows_abort_whole_delete_and_new_preview_expires_old(self):
        admin=self.client('admin');students=self.ok(admin,'/api/students')['students'];ids=[s['hemis_id'] for s in students]
        preview=self.preview(admin,ids)
        self.ok(admin,'/api/students/import',{'students':[{**students[-1],'full_name':'Changed Student'}]})
        self.assertEqual(self.remove(admin,preview)[0],409)
        self.assertEqual(len(self.ok(admin,'/api/students')['students']),len(students))
        next_preview=self.preview(admin,ids)
        self.assertEqual(self.remove(admin,preview)[0],409)
        self.assertEqual(self.remove(admin,next_preview)[1]['deleted'],len(students))
        self.assertEqual(self.ok(admin,'/api/students')['students'],[])

    def test_historical_student_snapshot_survives_delete_and_reimport(self):
        admin=self.client('admin');manager=self.client('manager')
        student=self.ok(admin,'/api/student',{'hemis_id':'100000000001'})['student']
        request=self.ok(manager,'/api/request/create',{'key':str(uuid4()),'channel':'phone','section':0,'service':0,'lang':'uz','hemis_id':student['hemis_id'],'identity_confirmed':True,'content':'Keep this request','note':''})['request']
        before={name:self.ok(admin,path) for name,path in [('users','/api/users'),('settings','/api/settings'),('audio','/api/audio')]}
        preview=self.preview(admin,[student['hemis_id']]);status,result,_=self.remove(admin,preview)
        self.assertEqual(status,200);self.assertEqual(result['preserved_requests'],1)
        current=self.ok(manager,'/api/requests')['requests'][0]
        self.assertEqual(current['student'],student);self.assertEqual(current['content'],request['content']);self.assertEqual(current['student_id'],student['hemis_id'])
        self.assertIsNone(self.ok(admin,'/api/student',{'hemis_id':student['hemis_id']})['student'])
        for name,path in [('users','/api/users'),('settings','/api/settings'),('audio','/api/audio')]:self.assertEqual(self.ok(admin,path),before[name])
        self.ok(admin,'/api/students/import',{'students':[{**student,'full_name':'Reimported Name'}]})
        self.assertEqual(self.ok(manager,'/api/requests')['requests'][0]['student']['full_name'],student['full_name'])
        current=self.ok(manager,'/api/requests')['requests'][0]
        self.ok(manager,'/api/request/action',{'id':current['id'],'version':current['version'],'action':'update','hemis_id':student['hemis_id'],'content':current['content'],'note':''})
        self.assertEqual(self.ok(manager,'/api/requests')['requests'][0]['student']['full_name'],'Reimported Name')

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in StudentRegistryAcceptance.__dict__:setattr(StudentRegistryAcceptance,_name,None)
del WorkflowAcceptance
