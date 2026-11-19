import json
from test_workflow import WorkflowAcceptance
from test_telegram_mini import signed,TOKEN

class TelegramMiniHTTPTests(WorkflowAcceptance):
    def configure(self):
        return self.ok(self.client('admin'),'/api/admin/integrations',{'kind':'telegram','token':TOKEN,'enabled':True})
    def test_public_page_has_scoped_telegram_csp_without_relaxing_admin(self):
        status,body,headers=self.public.request('/student')
        self.assertEqual(status,200);self.assertIn('student.js',body);self.assertIsNone(headers.get('X-Frame-Options'))
        self.assertIn('https://telegram.org',headers['Content-Security-Policy']);self.assertIn('https://web.telegram.org',headers['Content-Security-Policy'])
        _,_,staff_headers=self.public.request('/admin')
        self.assertEqual(staff_headers['X-Frame-Options'],'DENY');self.assertNotIn('https://telegram.org',staff_headers['Content-Security-Policy'])
        for asset in ('student.js','student.css','student-pattern.svg'):self.assertEqual(self.public.request('/assets/'+asset)[0],200)
    def test_signed_public_api_refuses_cookie_only_and_cross_origin(self):
        self.configure()
        self.assertEqual(self.public.request('/api/telegram/mini',{'action':'state'})[0],401)
        self.assertEqual(self.client('admin').request('/api/telegram/mini',{'action':'state'})[0],401)
        data={'init_data':signed(),'action':'state'}
        self.assertEqual(self.ok(self.public,'/api/telegram/mini',data),{'linked':False,'lang':'uz'})
        self.assertEqual(self.public.request('/api/telegram/mini',data,headers={'Origin':'https://malicious.example'})[0],403)
        self.assertEqual(self.public.request('/api/telegram/mini',{'init_data':signed()+'&user=bad','action':'state'})[0],401)
    def test_link_failures_persist_and_sensitive_payloads_never_enter_audit(self):
        self.configure();admin=self.client('admin');sid='100000000001'
        code=self.ok(admin,'/api/telegram/code',{'hemis_id':sid,'identity_confirmed':True})['code']
        init=signed()
        for _ in range(5):
            result=self.ok(self.public,'/api/telegram/mini',{'init_data':init,'action':'link','hemis_id':sid,'code':'WRONG'})
            self.assertFalse(result['ok'])
        result=self.ok(self.public,'/api/telegram/mini',{'init_data':init,'action':'link','hemis_id':sid,'code':code})
        self.assertEqual(result['error_code'],'locked')
        audit=json.dumps(self.ok(admin,'/api/security/audit'))
        self.assertNotIn(init,audit);self.assertNotIn(code,audit);self.assertNotIn(TOKEN,audit)
        self.assertEqual(self.client('manager').request('/api/telegram/mini-config')[0],403)
        self.ok(admin,'/api/telegram/mini-config',{'url':'https://example.com/student'})
        self.assertEqual(self.ok(admin,'/api/telegram/mini-config')['url'],'https://example.com/student')

for name in list(WorkflowAcceptance.__dict__):
    if name.startswith('test_') and name not in TelegramMiniHTTPTests.__dict__:setattr(TelegramMiniHTTPTests,name,None)
del WorkflowAcceptance
