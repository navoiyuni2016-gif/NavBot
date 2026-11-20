from test_workflow import WorkflowAcceptance

class TelegramHTTPAcceptance(WorkflowAcceptance):
    def test_staff_codes_permissions_and_no_secret_readback(self):
        data={'hemis_id':'100000000001','identity_confirmed':True}
        self.assertEqual(self.public.request('/api/telegram/code',data)[0],401)
        self.assertEqual(self.client('executor').request('/api/telegram/code',data)[0],403)
        self.assertEqual(self.client('head').request('/api/telegram/code',data)[0],403)
        manager=self.client('manager');admin=self.client('admin')
        self.assertEqual(manager.request('/api/telegram/code',{'hemis_id':data['hemis_id']})[0],400)
        code=self.ok(manager,'/api/telegram/code',data)
        self.assertRegex(code['code'],r'^[A-Z2-9]{8}$')
        current=self.ok(manager,'/api/telegram/student?hemis_id='+data['hemis_id'])
        self.assertFalse(current['linked']);self.assertIsNotNone(current['code_expires_at']);self.assertNotIn('code',current)
        audit=self.ok(admin,'/api/security/audit')
        import json
        self.assertNotIn(code['code'],json.dumps(audit))
        health=self.ok(admin,'/api/telegram/health');self.assertFalse(health['active'])
        self.assertEqual(manager.request('/api/telegram/health')[0],403)
        self.assertEqual(manager.request('/api/telegram/unlink',{'hemis_id':data['hemis_id'],'reason':'test'})[0],403)
    def test_request_status_follows_visibility_and_rejects_bad_ids(self):
        _,row=self.linked_request()
        self.assertEqual(self.ok(self.client('manager'),'/api/telegram/request?id='+str(row['id']))['state'],'not_approved')
        self.assertEqual(self.client('manager2').request('/api/telegram/request?id='+str(row['id']))[0],200)
        self.assertEqual(self.client('manager2').request('/api/telegram/retry',{'id':row['id']})[0],403)
        self.assertEqual(self.client('admin').request('/api/telegram/request?id=oops')[0],400)
        self.assertEqual(self.public.request('/api/telegram/request?id='+str(row['id']))[0],401)

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in TelegramHTTPAcceptance.__dict__:setattr(TelegramHTTPAcceptance,_name,None)
del WorkflowAcceptance
