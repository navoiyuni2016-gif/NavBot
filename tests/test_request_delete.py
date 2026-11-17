import base64
import sqlite3
from pathlib import Path
from uuid import uuid4
from test_workflow import WorkflowAcceptance

class DeleteAcceptance(WorkflowAcceptance):
    def ticket(self):return self.ok(self.public,'/api/ticket',{'key':str(uuid4()),'lang':'uz','section':0,'service':0})
    def targets(self,client):return [{'id':r['id'],'version':r['version']} for r in self.ok(client,'/api/requests')['requests']]
    def remove(self,client,targets,password='Navbot-Test-2026!'):
        return client.request('/api/admin/requests/delete',{'targets':targets,'password':password,'reason':'Remove test requests','confirm_count':len(targets)})
    def test_admin_only_password_confirmation_and_atomic_stale_rejection(self):
        self.ticket();admin=self.client('admin');targets=self.targets(admin)
        self.assertEqual(self.remove(self.public,targets)[0],401)
        self.assertEqual(self.remove(self.client('manager'),targets)[0],403)
        self.assertEqual(self.remove(admin,targets,'Wrong-test-password-123')[0],401)
        self.assertEqual(len(self.targets(admin)),1)
        self.ticket();targets=self.targets(admin)
        stale=[targets[0],dict(targets[1],version=0)]
        self.assertEqual(self.remove(admin,stale)[0],409)
        self.assertEqual(self.targets(admin),targets)
        self.assertEqual(self.remove(admin,[targets[0],targets[0]])[0],400)
        self.assertEqual(self.targets(admin),targets)
        self.assertEqual(self.remove(admin,targets)[0],200)
        self.assertEqual(self.targets(admin),[])
        self.assertEqual(self.ok(admin,'/api/me')['user']['role'],'admin')
    def test_clear_preserves_students_users_settings_audio_and_counter(self):
        ticket=self.ticket();admin=self.client('admin');targets=self.targets(admin)
        students=self.ok(admin,'/api/students');users=self.ok(admin,'/api/users');settings=self.ok(admin,'/api/settings')
        self.ok(admin,'/api/admin/audio/install-pack',{})
        audio=self.ok(admin,'/api/audio')
        self.ok(self.client('manager'),'/api/action',{'operator':1,'action':'call'})
        # A queue call changes request version; fetch the current snapshot.
        targets=self.targets(admin)
        status,result,_=self.remove(admin,targets);self.assertEqual(status,200);self.assertEqual(result['deleted'],1)
        self.assertEqual(self.ok(admin,'/api/students'),students);self.assertEqual(self.ok(admin,'/api/users'),users)
        self.assertEqual(self.ok(admin,'/api/settings'),settings);self.assertEqual(self.ok(admin,'/api/audio'),audio)
        q=self.ok(self.public,'/api/state?1,0');self.assertEqual(q['waiting'],[]);self.assertIsNone(q['desk']);self.assertEqual(q['events'],[])
        self.assertEqual(self.ok(admin,'/api/report')['summary']['total'],0)
        next_ticket=self.ticket();self.assertEqual(next_ticket['code'],'A-002')
        self.assertGreater(next_ticket['id'],ticket['id'])
        with sqlite3.connect(Path(self.temp.name)/'test.sqlite3') as db:
            row=db.execute('SELECT student_id,content,note,manager_id,deleted_at FROM requests WHERE id=?',(targets[0]['id'],)).fetchone()
            self.assertEqual(row[:4],(None,'','',None));self.assertIsNotNone(row[4])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='requests_delete'").fetchone()[0],1)
    def test_deleted_attachment_unavailable_and_new_rows_survive_snapshot(self):
        self.ticket();admin=self.client('admin');request=self.ok(admin,'/api/requests')['requests'][0]
        payload={'id':request['id'],'version':request['version'],'key':str(uuid4()),'name':'test.txt','data':base64.b64encode(b'test-content').decode()}
        uploaded=self.ok(admin,'/api/attachment/upload',payload)['request'];url=uploaded['attachments'][0]['url']
        targets=[{'id':uploaded['id'],'version':uploaded['version']}]
        self.ticket()
        self.assertEqual(self.remove(admin,targets)[0],200)
        self.assertEqual(admin.request(url)[0],404)
        self.assertEqual(len(self.targets(admin)),1)
        with sqlite3.connect(Path(self.temp.name)/'test.sqlite3') as db:self.assertEqual(db.execute('SELECT count(*) FROM attachments').fetchone()[0],0)

    def test_replay_and_restart_do_not_resurrect_deleted_requests(self):
        import subprocess,time
        payload={'key':str(uuid4()),'lang':'uz','section':0,'service':0}
        self.ok(self.public,'/api/ticket',payload);admin=self.client('admin')
        self.assertEqual(self.remove(admin,self.targets(admin))[0],200)
        self.assertEqual(self.public.request('/api/ticket',payload)[0],409)
        args=self.server.args;self.stop_server()
        self.server=subprocess.Popen(args,stdout=self.log,stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                if self.public.request('/api/catalog')[0]==200:break
            except OSError:pass
            time.sleep(.05)
        self.assertEqual(self.targets(admin),[])
        self.assertEqual(self.ok(self.public,'/api/state?0,0')['waiting'],[])
        self.assertEqual(self.ticket()['code'],'A-002')
        phone={'key':str(uuid4()),'channel':'phone','identity_confirmed':True,'hemis_id':'100000000001','lang':'uz','section':0,'service':0,'content':'Phone test'}
        old=self.ok(admin,'/api/request/create',phone)['request']
        self.assertEqual(self.remove(admin,[{'id':old['id'],'version':old['version']}])[0],200)
        self.assertEqual(admin.request('/api/request/create',phone)[0],409)
        phone['key']=str(uuid4())
        self.assertGreater(self.ok(admin,'/api/request/create',phone)['request']['id'],old['id'])

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in DeleteAcceptance.__dict__:setattr(DeleteAcceptance,_name,None)
del WorkflowAcceptance
