import base64
import sqlite3
import time
import unittest
from test_workflow import WorkflowAcceptance, Client
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'navbot'))
import security_monitor as security

class SecurityHelpers(unittest.TestCase):
    def test_proxy_trust_and_path_detection(self):
        self.assertEqual(security.client_ip('198.51.100.4',{'X-Real-IP':'1.2.3.4','X-Forwarded-For':'5.6.7.8'}),'198.51.100.4')
        self.assertEqual(security.client_ip('127.0.0.1',{'X-Real-IP':'203.0.113.4'}),'203.0.113.4')
        self.assertEqual(security.client_ip('127.0.0.1',{'X-Forwarded-For':'1.2.3.4'}),'127.0.0.1')
        self.assertEqual(security.client_ip('127.0.0.1',{'X-Real-IP':'invalid'}),'127.0.0.1')
        self.assertTrue(security.probe('/%2eenv'));self.assertTrue(security.probe('/.git/config'))
        self.assertFalse(security.probe('/favicon.ico'));self.assertFalse(security.probe('/api/admin/users'))

    def test_expired_blocks_and_admin_recovery(self):
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        db.execute('CREATE TABLE security_ip_blocks(ip TEXT PRIMARY KEY,blocked_until INTEGER)')
        db.execute('INSERT INTO security_ip_blocks VALUES (?,?)',('203.0.113.9',int(time.time())-1))
        context={'ip':'203.0.113.9','path':'/api/students','method':'GET'}
        self.assertIsNone(security.gate(db,context,None))
        db.execute('UPDATE security_ip_blocks SET blocked_until=?',(int(time.time())+900,))
        self.assertEqual(security.gate(db,context,None),429)
        self.assertIsNone(security.gate(db,{**context,'path':'/api/security/audit'},{'role':'admin'}))
        db.close()

class SecurityMonitorAcceptance(WorkflowAcceptance):
    def audit(self,admin,query=''):
        return self.ok(admin,'/api/security/audit?'+query)
    def until(self,fn):
        for _ in range(60):
            result=fn()
            if result:return result
            time.sleep(.03)
        self.fail('Audit event was not persisted')

    def test_audit_permissions_ip_upload_metadata_and_secret_redaction(self):
        admin=self.client('admin');head=self.client('head')
        self.assertEqual(self.public.request('/api/security/audit')[0],401)
        self.assertEqual(head.request('/api/security/audit')[0],403)
        png=base64.b64encode(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVZkAAAAASUVORK5CYII=')).decode()
        result=admin.request('/api/profile/photo',{'mime':'image/png','data':png,'filename':'proof.png'},headers={'X-Real-IP':'203.0.113.10','X-Forwarded-For':'1.2.3.4'})
        self.assertEqual(result[0],200)
        row=self.until(lambda:next((e for e in self.audit(admin,'ip=203.0.113.10')['events'] if e['filename']=='proof.png'),None))
        self.assertEqual(row['http_status'],200);self.assertEqual(row['actor_username'],'admin');self.assertEqual(row['category'],'upload')
        self.assertEqual(admin.request('/api/admin/branding',{'target':'system_logo','mime':'image/png','data':png,'filename':'university.png'},headers={'X-Real-IP':'203.0.113.10'})[0],200)
        brand=self.until(lambda:next((e for e in self.audit(admin,'ip=203.0.113.10')['events'] if e['filename']=='university.png'),None))
        self.assertEqual(brand['category'],'upload')
        secret='Do-Not-Log-This-Password!'
        self.assertEqual(self.public.request('/api/login',{'username':'unknown.login','password':secret},headers={'X-Real-IP':'198.51.100.11'})[0],401)
        events=self.until(lambda:self.audit(admin,'ip=198.51.100.11')['events'])
        self.assertEqual(events[0]['actor_username'],'unknown.login');self.assertEqual(events[0]['action'],'login_failed')
        all_events=str(self.audit(admin)['events'])
        self.assertNotIn(secret,all_events);self.assertNotIn(png,all_events)
        for cookie in admin.cookies:self.assertNotIn(cookie.value,all_events)

    def test_brute_force_ban_notification_recovery_and_expiry(self):
        admin=self.client('admin');headers={'X-Real-IP':'198.51.100.20'}
        for index in range(10):
            self.assertEqual(self.public.request('/api/login',{'username':'wrong'+str(index),'password':'invalid-password'},headers=headers)[0],401)
        self.until(lambda:any(b['ip']=='198.51.100.20' for b in self.audit(admin)['blocks']))
        self.assertEqual(self.public.request('/api/login',{'username':'admin','password':'Navbot-Test-2026!'},headers=headers)[0],429)
        self.assertEqual(self.public.request('/api/students',headers=headers)[0],429)
        self.assertEqual(self.public.request('/tv',headers=headers)[0],200)
        notifications=self.ok(admin,'/api/notifications')['notifications']
        self.assertTrue(any(n['security_alert_id'] and '198.51.100.20' in n['message'] for n in notifications))
        self.assertEqual(admin.request('/api/security/audit',headers=headers)[0],200)
        self.assertEqual(admin.request('/api/security/unblock',{'ip':'198.51.100.20','reason':'Verified administrator test'},headers=headers)[0],200)
        self.assertFalse(any(b['ip']=='198.51.100.20' for b in self.audit(admin)['blocks']))
        self.assertEqual(self.public.request('/api/login',{'username':'admin','password':'Navbot-Test-2026!'},headers=headers)[0],200)

    def test_sensitive_probes_are_banned_and_pagination_filters_are_50(self):
        admin=self.client('admin');headers={'X-Real-IP':'203.0.113.21'}
        for path in ('/.env','/.git/config','/wp-login.php'):
            self.assertEqual(self.public.request(path,headers=headers)[0],403)
        self.until(lambda:any(b['ip']=='203.0.113.21' for b in self.audit(admin)['blocks']))
        self.assertEqual(self.public.request('/api/students',headers=headers)[0],429)
        self.assertEqual(self.public.request('/.env.local',headers=headers)[0],429)
        self.assertEqual(self.public.request('/.git/HEAD',headers=headers)[0],429)
        for index in range(55):
            self.assertEqual(admin.request('/login',headers={'X-Real-IP':'203.0.113.22'})[0],200)
        result=self.until(lambda:(lambda r:r if r['total']>=55 else None)(self.audit(admin,'ip=203.0.113.22')))
        self.assertEqual(len(result['events']),50);self.assertGreaterEqual(result['pages'],2)
        page=self.audit(admin,'ip=203.0.113.22&page=2');self.assertTrue(page['events'])
        self.assertTrue(all(e['ip']=='203.0.113.22' and e['http_status']==200 for e in result['events']))
        self.assertEqual(self.audit(admin,'ip=%27+OR+1%3D1')['total'],0)
        self.assertTrue(self.audit(admin,'severity=high&category=security')['events'])

    def test_new_ip_login_alert_is_deduplicated_and_denials_are_visible(self):
        admin=self.client('admin');client=Client(self.base);headers={'X-Real-IP':'203.0.113.45'}
        self.assertEqual(client.request('/api/login',{'username':'admin','password':'Navbot-Test-2026!'},headers=headers)[0],200)
        self.until(lambda:self.audit(admin,'action=new_login_ip')['events'])
        self.assertEqual(client.request('/api/login',{'username':'admin','password':'Navbot-Test-2026!'},headers=headers)[0],200)
        self.assertEqual(len(self.audit(admin,'action=new_login_ip')['events']),1)
        head=self.client('head')
        self.assertEqual(head.request('/api/security/audit',headers={'X-Real-IP':'203.0.113.46'})[0],403)
        row=self.until(lambda:next(iter(self.audit(admin,'ip=203.0.113.46')['events']),None))
        self.assertEqual(row['action'],'permission_denied');self.assertEqual(row['actor_username'],'head')

    def test_poll_requests_are_counted_not_lost(self):
        admin=self.client('admin');headers={'X-Real-IP':'203.0.113.30'}
        for _ in range(3):self.assertEqual(admin.request('/api/requests',headers=headers)[0],200)
        rows=self.until(lambda:(lambda r:r if sum(e['hits'] for e in r)>=3 else None)(self.audit(admin,'ip=203.0.113.30')['events']))
        self.assertLessEqual(len(rows),2);self.assertGreaterEqual(sum(e['hits'] for e in rows),3)

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in SecurityMonitorAcceptance.__dict__:setattr(SecurityMonitorAcceptance,_name,None)
del WorkflowAcceptance
