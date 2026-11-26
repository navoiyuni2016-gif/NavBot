"""Browser policy must allow trusted code, not arbitrary inline scripts."""
import base64
import hashlib
import re
from test_workflow import WorkflowAcceptance

class SecurityHeadersAcceptance(WorkflowAcceptance):
    def test_operational_report_is_admin_only_and_has_no_credentials(self):
        status,_,_=self.public.request('/api/admin/operations')
        self.assertIn(status,(401,403))
        from test_workflow import Client
        manager=Client(self.base);manager.login('manager')
        self.assertEqual(manager.request('/api/admin/operations')[0],403)
        admin=Client(self.base);admin.login('admin')
        status,report,_=admin.request('/api/admin/operations')
        self.assertEqual(status,200);self.assertIn('checks',report)
        for key in ('token','password','alert_chat_id','code_dir','data_dir'):self.assertNotIn(key,report)

    def test_static_pages_only_allow_hashes_of_their_actual_scripts(self):
        for path in ('/login','/kiosk','/tv'):
            status,body,headers=self.public.request(path)
            self.assertEqual(status,200)
            policy=headers['Content-Security-Policy']
            scripts=next(p.strip() for p in policy.split(';') if p.strip().startswith('script-src '))
            self.assertNotIn("'unsafe-inline'",scripts)
            self.assertNotIn("'unsafe-eval'",scripts)
            inline=re.findall(r'<script>(.*?)</script>',body,re.DOTALL)
            self.assertTrue(inline)
            for script in inline:
                expected=base64.b64encode(hashlib.sha256(script.encode('utf-8')).digest()).decode('ascii')
                self.assertIn("'sha256-"+expected+"'",scripts)
            self.assertIn("object-src 'none'",policy)
            self.assertIn("frame-ancestors 'none'",policy)
            self.assertNotIn('onclick="',body)

    def test_api_replies_hide_runtime_and_set_browser_boundaries(self):
        status,body,headers=self.public.request('/api/me')
        self.assertEqual(status,200)
        self.assertEqual(headers['Server'],'NAVBOT')
        self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        self.assertEqual(headers['X-Frame-Options'],'DENY')
        self.assertEqual(headers['Cross-Origin-Opener-Policy'],'same-origin')
        self.assertEqual(headers['Cross-Origin-Resource-Policy'],'same-origin')
        self.assertEqual(headers['Permissions-Policy'],'camera=(), microphone=(), geolocation=()')
        self.assertEqual(headers['Cache-Control'],'no-store')

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in SecurityHeadersAcceptance.__dict__:
        setattr(SecurityHeadersAcceptance,_name,None)
del WorkflowAcceptance
