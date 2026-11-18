from test_workflow import WorkflowAcceptance, Client

class RoleSwitchAcceptance(WorkflowAcceptance):
    def set_roles(self,admin,username,roles,operator=None):
        user=next(u for u in self.ok(admin,'/api/admin/users')['users'] if u['username']==username)
        fields={k:user[k] for k in ('username','full_name','role','department','employee_number')}
        result=admin.request('/api/admin/user/action',{'user_id':user['id'],'action':'update',**fields,'allowed_roles':roles,'operator':operator})
        return result,user
    def test_admin_switches_context_without_changing_owner_or_base_and_rotates_session(self):
        admin=self.client('admin');before=self.ok(admin,'/api/me')['user']
        old='; '.join(c.name+'='+c.value for c in admin.cookies)
        switched=self.ok(admin,'/api/profile/role',{'role':'executor_international'})['user']
        self.assertEqual(switched['id'],before['id']);self.assertEqual(switched['role'],'executor');self.assertEqual(switched['base_role'],'admin')
        self.assertEqual(switched['department'],'Xalqaro aloqalar bo‘limi')
        self.assertEqual(admin.request('/api/admin/users')[0],403)
        self.assertIsNone(self.ok(self.public,'/api/me')['user'])
        self.assertIsNone(self.public.request('/api/me',headers={'Cookie':old})[1]['user'])
        current=self.ok(admin,'/api/profile/role',{'role':'admin'})['user'];self.assertEqual(current['role'],'admin')
        self.assertEqual(admin.request('/api/admin/users')[0],200)
        self.assertEqual(admin.request('/api/profile/role',{'role':'manager','operator':1})[0],409)
        self.assertEqual(self.ok(admin,'/api/profile/role',{'role':'manager','operator':9})['user']['operator'],9)
        self.assertEqual(admin.request('/api/action',{'operator':1,'action':'call'})[0],403)
        self.ok(admin,'/api/profile/role',{'role':'admin'})
        audit=self.ok(admin,'/api/audit')['events'];self.assertTrue(any(e['action']=='role_switch' for e in audit))

    def test_head_can_only_use_granted_roles_and_never_admin(self):
        admin=self.client('admin');head=self.client('head')
        self.assertEqual(head.request('/api/profile/role',{'role':'director'})[0],403)
        result,user=self.set_roles(admin,'head',['head','executor_hr','director'])
        self.assertEqual(result[0],200)
        self.assertIsNone(self.ok(head,'/api/me')['user'])
        self.clients.pop('head');head=self.client('head')
        for role in ('admin','manager','executor_database'):
            self.assertEqual(head.request('/api/profile/role',{'role':role})[0],403)
        effective=self.ok(head,'/api/profile/role',{'role':'executor_hr'})['user']
        self.assertEqual(effective['department'],'Xodimlar bo‘limi');self.assertEqual(effective['base_role'],'head')
        self.assertEqual(head.request('/api/admin/users')[0],403)
        self.ok(head,'/api/profile/role',{'role':'director'});self.assertEqual(head.request('/api/report')[0],200)
        self.ok(head,'/api/profile/role',{'role':'head'})
        self.assertEqual(head.request('/api/admin/user/action',{'user_id':user['id'],'action':'update','role':'admin'})[0],403)
        self.set_roles(admin,'head',['head'])
        self.assertEqual(head.request('/api/profile/role',{'role':'director'})[0],401)

    def test_grants_validation_manager_operator_and_normal_accounts(self):
        admin=self.client('admin')
        self.assertEqual(self.set_roles(admin,'head',['head','admin'])[0][0],403)
        self.assertEqual(self.set_roles(admin,'head',['head','manager'])[0][0],400)
        self.assertEqual(self.set_roles(admin,'head',['head','manager'],9)[0][0],200)
        head=self.client('head');self.assertEqual(self.ok(head,'/api/profile/role',{'role':'manager'})['user']['operator'],9)
        self.assertEqual(head.request('/api/action',{'operator':1,'action':'call'})[0],403)
        self.assertEqual(self.set_roles(admin,'executor',['executor','director'])[0][0],403)
        executor=self.client('executor');self.assertEqual(executor.request('/api/profile/role',{'role':'admin'})[0],403)
        self.assertEqual(executor.request('/api/profile/role',{'role':'head'})[0],403)

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in RoleSwitchAcceptance.__dict__:setattr(RoleSwitchAcceptance,_name,None)
del WorkflowAcceptance
