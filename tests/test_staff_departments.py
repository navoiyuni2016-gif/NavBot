from uuid import uuid4
from test_workflow import WorkflowAcceptance, Client

DEPARTMENTS = ['O‘quv bo‘limi','Xalqaro aloqalar bo‘limi','Xodimlar bo‘limi','Ma’lumotlar bazasi menejeri']

class StaffDepartmentAcceptance(WorkflowAcceptance):
    def create(self, index, **extra):
        payload={'username':'department'+str(index),'full_name':'Department Staff '+str(index),'role':'executor','department':DEPARTMENTS[index],'operator':None,'password':'Temporary-Dept-2026!',**extra}
        return self.client('admin').request('/api/admin/user',payload)

    def test_departments_keep_executor_permissions_and_scoped_requests(self):
        admin=self.client('admin');manager=self.client('manager')
        for index in range(4):
            status,result,_=self.create(index,employee_number='007' if index==3 else None)
            self.assertEqual(status,200,result);user=result['user'];self.assertEqual(user['role'],'executor');self.assertIsNone(user['operator'])
            client=Client(self.base);self.ok(client,'/api/login',{'username':user['username'],'password':'Temporary-Dept-2026!'})
            self.ok(client,'/api/password',{'current_password':'Temporary-Dept-2026!','new_password':'Changed-Dept-2026!'})
            self.ok(client,'/api/login',{'username':user['username'],'password':'Changed-Dept-2026!'})
            self.assertEqual(self.ok(client,'/api/requests')['requests'],[])
            request=self.ok(manager,'/api/request/create',{'key':str(uuid4()),'channel':'phone','section':0,'service':0,'lang':'uz','hemis_id':'100000000001','identity_confirmed':True,'content':'Department work','note':''})['request']
            self.ok(manager,'/api/request/action',{'id':request['id'],'version':request['version'],'action':'assign','assignee_id':user['id'],'deadline':'2099-01-01T10:00:00+00:00','internal_basis':'Test','legal_basis':''})
            visible=self.ok(client,'/api/requests')['requests'];self.assertEqual([r['id'] for r in visible],[request['id']])
            self.assertEqual(client.request('/api/admin/users')[0],403)
            self.assertEqual(client.request('/api/report')[0],403)
            self.assertEqual(client.request('/api/action',{'operator':1,'action':'call'})[0],403)
            submitted=self.ok(client,'/api/request/action',{'id':request['id'],'version':visible[0]['version'],'action':'submit','answer':'Prepared answer'})['request']
            self.assertEqual(submitted['status'],'pending_approval')
        self.assertEqual(len(self.ok(admin,'/api/requests')['requests']),4)

    def test_staff_number_is_separate_optional_validated_and_unique(self):
        status,result,_=self.create(3,employee_number='0007');self.assertEqual(status,200)
        user=result['user'];self.assertEqual(user['employee_number'],'0007');self.assertIsNone(user['operator'])
        for number in ('not-a-number',7,'1'*21):
            self.assertEqual(self.create(3,username='invalid'+str(type(number).__name__),employee_number=number)[0],400)
        self.assertEqual(self.create(0,employee_number='12')[0],400)
        self.assertEqual(self.create(3,username='with.operator',operator=2)[0],400)
        self.assertEqual(self.create(3,username='duplicate.number',employee_number='0007')[0],409)
        self.assertEqual(self.create(3,username='optional.number')[0],200)
        payload={k:user[k] for k in ('username','full_name','role','department','operator')}
        self.ok(self.client('admin'),'/api/admin/user/action',{'user_id':user['id'],'action':'update',**payload,'employee_number':'0012'})
        edited=next(u for u in self.ok(self.client('admin'),'/api/admin/users')['users'] if u['id']==user['id'])
        self.assertEqual(edited['employee_number'],'0012');self.assertIsNone(edited['operator'])

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in StaffDepartmentAcceptance.__dict__:setattr(StaffDepartmentAcceptance,_name,None)
del WorkflowAcceptance
