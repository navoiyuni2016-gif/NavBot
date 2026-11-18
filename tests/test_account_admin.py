from test_workflow import WorkflowAcceptance, Client

class AccountAdminAcceptance(WorkflowAcceptance):
    def action(self, client, user, action, **fields):
        return client.request('/api/admin/user/action', {'user_id':user['id'],'action':action,**fields})

    def test_edit_permissions_validation_and_session_revocation(self):
        admin=self.client('admin'); manager=self.client('manager')
        accounts=self.ok(admin,'/api/admin/users')['users']; target=next(u for u in accounts if u['username']=='executor')
        self.assertEqual(self.public.request('/api/admin/users')[0],401)
        self.assertEqual(manager.request('/api/admin/users')[0],403)
        self.assertEqual(self.action(manager,target,'deactivate')[0],403)
        executor=self.client('executor')
        fields={k:target[k] for k in ('username','full_name','role','department','operator')}
        self.assertEqual(self.action(admin,target,'update',**{**fields,'username':'?bad'})[0],400)
        self.assertEqual(self.action(admin,target,'update',**{**fields,'username':'manager'})[0],409)
        self.assertEqual(self.action(admin,target,'update',**{**fields,'full_name':'Edited Name','username':'edited.executor'})[0],200)
        self.assertIsNone(self.ok(executor,'/api/me')['user'])
        changed=Client(self.base);self.assertEqual(changed.request('/api/login',{'username':'edited.executor','password':'Navbot-Test-2026!'})[0],200)
        self.assertEqual(self.ok(changed,'/api/me')['user']['full_name'],'Edited Name')

    def test_deactivation_reactivation_and_assignments(self):
        admin=self.client('admin'); executor=self.client('executor'); manager=self.client('manager')
        target=next(u for u in self.ok(admin,'/api/admin/users')['users'] if u['username']=='executor')
        self.assertEqual(self.action(admin,target,'deactivate')[0],200)
        self.assertIsNone(self.ok(executor,'/api/me')['user'])
        self.assertEqual(Client(self.base).request('/api/login',{'username':'executor','password':'Navbot-Test-2026!'})[0],401)
        self.assertNotIn(target['id'],[u['id'] for u in self.ok(admin,'/api/users')['users']])
        self.assertFalse(next(u for u in self.ok(admin,'/api/admin/users')['users'] if u['id']==target['id'])['active'])
        created=self.ok(manager,'/api/request/create',{'key':'00000000-0000-4000-8000-000000000001','channel':'phone','section':0,'service':0,'lang':'uz','hemis_id':'100000000001','identity_confirmed':True,'content':'Test','note':''})['request']
        self.assertEqual(manager.request('/api/request/action',{'id':created['id'],'version':created['version'],'action':'assign','assignee_id':target['id'],'deadline':'2099-01-01T10:00:00+00:00','internal_basis':'Test','legal_basis':''})[0],400)
        self.assertEqual(self.action(admin,target,'activate')[0],200)
        self.assertEqual(Client(self.base).request('/api/login',{'username':'executor','password':'Navbot-Test-2026!'})[0],200)

    def test_delete_protects_self_open_work_and_preserves_history(self):
        admin=self.client('admin'); manager=self.client('manager')
        accounts=self.ok(admin,'/api/admin/users')['users']; me=next(u for u in accounts if u['username']=='admin'); target=next(u for u in accounts if u['username']=='manager')
        for action in ('delete','deactivate'):
            self.assertEqual(self.action(admin,me,action,confirm_username='admin')[0],409)
        fields={k:me[k] for k in ('username','full_name','department','operator')}
        self.assertEqual(self.action(admin,me,'update',role='director',**fields)[0],409)
        created=self.ok(manager,'/api/request/create',{'key':'00000000-0000-4000-8000-000000000002','channel':'phone','section':0,'service':0,'lang':'uz','hemis_id':'100000000001','identity_confirmed':True,'content':'Preserve this','note':''})['request']
        self.assertEqual(self.action(admin,target,'delete',confirm_username='manager')[0],409)
        self.ok(manager,'/api/request/action',{'id':created['id'],'version':created['version'],'action':'resolve','answer':'Done','result':'Resolved'})
        self.assertEqual(self.action(admin,target,'delete',confirm_username='wrong')[0],400)
        self.assertEqual(self.action(admin,target,'delete',confirm_username='manager')[0],200)
        self.assertIsNone(self.ok(manager,'/api/me')['user'])
        self.assertEqual(Client(self.base).request('/api/login',{'username':'manager','password':'Navbot-Test-2026!'})[0],401)
        self.assertNotIn(target['id'],[u['id'] for u in self.ok(admin,'/api/admin/users')['users']])
        request=self.ok(admin,'/api/requests')['requests'][0]
        self.assertEqual(request['content'],'Preserve this');self.assertEqual(request['manager_name'],target['full_name'])
        self.assertEqual(self.action(admin,target,'activate')[0],404)

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in AccountAdminAcceptance.__dict__:setattr(AccountAdminAcceptance,_name,None)
del WorkflowAcceptance
