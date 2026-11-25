"""Owner identity, TOTP, independent sessions and reversible HTTP service control."""
import sqlite3
import time
from unittest.mock import patch
from test_workflow import WorkflowAcceptance, Client
import test_daily_queue
import unittest
import owner_control as owner
import auth

SECRET='GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'
PASSWORD='Owner-Test-Password-2026!'


class OwnerModel(unittest.TestCase):
    setUp=test_daily_queue.DailyQueue.setUp
    tearDown=test_daily_queue.DailyQueue.tearDown

    def test_totp_rfc_vector_and_no_account_by_default(self):
        self.assertEqual(owner.totp(SECRET,1),'287082')  # RFC 6238 at Unix 59, truncated to 6 digits.
        self.assertIsNone(self.db.execute('SELECT * FROM owner_account').fetchone())
        self.assertFalse(owner.status(self.db)['suspended'])
        with patch.object(owner.time,'time',return_value=59):
            self.assertEqual(owner.counter_for(SECRET,'287082'),1)
            self.assertIsNone(owner.counter_for(SECRET,'287082',1))

    def test_telegram_worker_makes_no_network_calls_when_suspended(self):
        import telegram_worker
        from unittest.mock import Mock
        self.db.execute('UPDATE owner_license SET suspended=1');self.db.commit()
        network=Mock()
        self.assertFalse(telegram_worker.deliver_one(self.db,network))
        telegram_worker.poll(self.db,network)
        self.assertEqual(network.mock_calls,[])

    def test_rate_limit_persists_and_reset_preserves_license_state(self):
        with patch.object(owner.time,'time',return_value=1700000000):
            for _ in range(5):
                with self.assertRaises(auth.AuthError) as error:owner.login(self.db,{'username':'nobody','password':PASSWORD,'code':'123456'})
                self.assertEqual(error.exception.status,401)
            with self.assertRaises(auth.AuthError) as error:owner.login(self.db,{})
            self.assertEqual(error.exception.status,429)
            self.db.rollback()
            self.db.execute("UPDATE owner_license SET suspended=1,reason='Contract pause'")
            owner.configure(self.db,'owner',PASSWORD,SECRET,owner.totp(SECRET,1700000000//30),reset=True)
            self.assertTrue(owner.status(self.db)['suspended'])
            self.assertIsNone(self.db.execute('SELECT * FROM owner_attempts').fetchone())
            self.db.commit()


class OwnerHTTP(WorkflowAcceptance):
    def enroll(self):
        import pathlib
        db=sqlite3.connect(pathlib.Path(self.temp.name)/'test.sqlite3');db.row_factory=sqlite3.Row
        counter=int(time.time())//30
        owner.configure(db,'owner',PASSWORD,SECRET,owner.totp(SECRET,counter-1))
        db.commit();db.close()

    def owner_login(self):
        client=Client(self.base)
        self.used_code=owner.totp(SECRET,int(time.time())//30)
        result=self.ok(client,'/api/owner/login',{'username':'owner','password':PASSWORD,'code':self.used_code})
        self.assertTrue(result['ok'])
        return client

    def test_owner_is_separate_and_pause_resume_preserves_data(self):
        self.enroll()
        admin=self.client('admin')
        ticket=self.ticket()
        self.assertEqual(admin.request('/api/owner/status')[0],401)
        self.assertEqual(admin.request('/api/owner/control',{'action':'suspend','reason':'Test','password':PASSWORD,'version':0})[0],401)
        client=self.owner_login()
        state=self.ok(client,'/api/owner/status')
        self.assertFalse(state['suspended'])
        # Owner session grants no staff/admin data permissions.
        self.assertEqual(client.request('/api/requests')[0],401)
        self.assertEqual(Client(self.base).request('/api/owner/login',{'username':'owner','password':PASSWORD,'code':self.used_code})[0],401)
        paused=self.ok(client,'/api/owner/control',{'action':'suspend','password':PASSWORD,'reason':'License review','version':state['version']})
        self.assertTrue(paused['suspended'])
        self.assertEqual(self.public.request('/kiosk')[0],503)
        self.assertEqual(self.public.request('/tv')[0],503)
        self.assertEqual(self.public.request('/student')[0],503)
        for path in ('/api/state','/api/catalog','/api/settings','/api/requests','/api/admin/users'):
            self.assertEqual(admin.request(path)[0],503,path)
        for path,data in (('/api/ticket',{'key':'paused'}),('/api/action',{'operator':1,'action':'call'}),('/api/telegram/mini',{}),('/api/kiosk-printer/agent',{}),('/api/login',{'username':'admin','password':'Navbot-Test-2026!'})):
            self.assertEqual(admin.request(path,data)[0],503,path)
        self.assertEqual(self.public.request('/owner')[0],200)
        self.assertEqual(self.public.request('/assets/owner.js')[0],200)
        self.assertEqual(self.public.request('/api/owner/control',{'action':'resume'})[0],401)
        # Same-origin POST protection also applies to owner control.
        self.assertEqual(client.request('/api/owner/control',{}, {'Origin':'https://attacker.invalid'})[0],403)
        self.assertEqual(client.request('/api/owner/control',{'action':'resume','password':PASSWORD,'reason':'Paid','version':state['version']})[0],409)
        # Restart the real HTTP server: pause and owner session must both survive.
        import pathlib, subprocess, sys, urllib.error
        from test_workflow import APP
        self.stop_server()
        self.server=subprocess.Popen([sys.executable,str(APP),'--port',self.base.rsplit(':',1)[-1],'--db',str(pathlib.Path(self.temp.name)/'test.sqlite3')],stdout=self.log,stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                if self.public.request('/owner')[0]==200:break
            except (OSError,urllib.error.URLError):time.sleep(.05)
        self.assertTrue(self.ok(client,'/api/owner/status')['suspended'])
        resumed=self.ok(client,'/api/owner/control',{'action':'resume','password':PASSWORD,'reason':'License confirmed','version':paused['version']})
        self.assertFalse(resumed['suspended'])
        requests=self.ok(admin,'/api/requests')['requests']
        self.assertIn(ticket['id'],[row['ticket_id'] for row in requests])
        actions=[event['action'] for event in resumed['events']]
        self.assertIn('suspend',actions);self.assertIn('resume',actions)
        self.ok(client,'/api/owner/logout',{})
        self.assertEqual(client.request('/api/owner/status')[0],401)

    def test_owner_cookie_expiry_reset_and_audit_excludes_secrets(self):
        self.enroll();client=self.owner_login()
        cookie=next(cookie for cookie in client.cookies if cookie.name==owner.COOKIE)
        self.assertEqual(cookie.path,'/api/owner');self.assertIn('HttpOnly',cookie._rest)
        import pathlib
        db=sqlite3.connect(pathlib.Path(self.temp.name)/'test.sqlite3');db.row_factory=sqlite3.Row
        all_events=str([dict(row) for row in db.execute('SELECT * FROM owner_events')])
        self.assertNotIn(PASSWORD,all_events);self.assertNotIn(SECRET,all_events)
        db.execute('UPDATE owner_sessions SET expires_at=0');db.commit()
        self.assertEqual(client.request('/api/owner/status')[0],401)
        owner.configure(db,'owner2',PASSWORD,SECRET,owner.totp(SECRET,int(time.time())//30),reset=True);db.commit()
        self.assertEqual(db.execute('SELECT COUNT(*) FROM owner_sessions').fetchone()[0],0)
        db.close()


for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in OwnerHTTP.__dict__:setattr(OwnerHTTP,_name,None)
del WorkflowAcceptance
