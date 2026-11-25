"""Real two-tenant HTTP isolation and clean distributable package checks."""
from pathlib import Path
import copy
import importlib.util
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sales'))
import tenant
import build_package
import auth,owner_control,tenant_instance
from test_workflow import Client,APP

PASSWORD_A='Tenant-A-Password-2026!'
PASSWORD_B='Tenant-B-Password-2026!'
SECRET_A='GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'
SECRET_B='JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'


def example(letter='a'):
    return json.loads((ROOT/f'sales/examples/university-{letter}.json').read_text())


class Planning(unittest.TestCase):
    def test_validation_conflicts_and_scoped_services(self):
        a,b=example(),example('b')
        with tempfile.TemporaryDirectory() as directory:
            one=tenant.generate(a,directory)
            tenant.generate(b,directory)
            for field in ('id','domain','port'):
                duplicate=copy.deepcopy(b);duplicate[field]=a[field]
                with self.assertRaises(ValueError):tenant.generate(duplicate,directory)
            web=(one/'navbot-university-a.service').read_text()
            self.assertIn('a.navbot.example.uz/kiosk',(one/'KIOSK-START.bat').read_text())
            self.assertNotIn('172.20.30.31',(one/'TV-START.bat').read_text())
            self.assertIn('User=nb-university-a',web)
            self.assertIn('--tenant university-a',web)
            self.assertIn('/var/lib/navbot-tenants/university-a/navbot.sqlite3',web)
            self.assertNotIn('university-b',web)
            nginx=(one/'nginx.conf').read_text()
            self.assertIn('listen 443 ssl;',nginx);self.assertNotIn('listen 80;',nginx)
            self.assertIn('X-Forwarded-Proto $scheme',nginx)
            self.assertIn('18081',nginx)
            self.assertIn('navbot-university-a-backup.service',(one/'navbot-university-a-backup.timer').read_text())
        for key,value in (('id','../../navbot'),('id','A B'),('domain','a.uz; include /etc/passwd;'),('domain','https://a.uz'),('domain','*.a.uz'),('port',8081),('port',True),('university',['Only Uzbek'])):
            invalid=copy.deepcopy(a);invalid[key]=value
            with self.assertRaises(ValueError):tenant.validate(invalid)

    def test_fresh_initialization_refuses_existing_database_and_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            dbpath=Path(directory)/'navbot.sqlite3';tenant.initialize_database(example(),dbpath)
            with self.assertRaises(ValueError):tenant.initialize_database(example('b'),dbpath)
            db=sqlite3.connect(dbpath);db.row_factory=sqlite3.Row
            for table in ('users','students','requests','owner_account','attachments'):
                self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0],0,table)
            self.assertEqual(tenant_instance.verify(db,'university-a',18081)['domain'],'a.navbot.example.uz')
            with self.assertRaises(ValueError):tenant_instance.verify(db,'university-b')
            with self.assertRaises(ValueError):tenant_instance.verify(db,'university-a',18082)
            self.assertTrue(tenant_instance.valid_host(tenant_instance.identity(db),'a.navbot.example.uz'))
            self.assertFalse(tenant_instance.valid_host(tenant_instance.identity(db),'b.navbot.example.uz'))
            db.close()
            self.assertEqual(dbpath.stat().st_mode&0o077,0)

    def test_custom_catalog_survives_tenant_restart(self):
        import app
        with tempfile.TemporaryDirectory() as directory:
            spec=example();spec['catalog']=copy.deepcopy(app.CATALOG)
            spec['catalog'][0][0][2]='Academic services'
            spec['catalog'][0][1][0][0]='Transkript olish'
            database=Path(directory)/'navbot.sqlite3';tenant.initialize_database(spec,database)
            previous=app.DATABASE;app.DATABASE=database
            try:
                app.initialize(False)
                db=app.connection()
                self.assertEqual(app.settings(db)['catalog'],spec['catalog']);db.close()
            finally:app.DATABASE=previous

    def test_package_has_no_customer_runtime_or_generated_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'release'
            for name,text in {'navbot/app.py':'# app','sales/tenant.py':'# tenant','sales/README.md':'# Readme','navbot/catalog.json':'[]','navbot/customer.sqlite3':'PRIVATE','navbot/local.json':'PRIVATE','navbot/customer.sqlite3.integration-secrets/abc.secret':'PRIVATE','sales/generated/a/tenant.json':'PRIVATE','sales/examples/a.json':'{}','.env':'PRIVATE'}.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
            target=Path(directory)/'sales.zip';manifest=build_package.build(target,root)
            self.assertEqual(build_package.verify(target),len(manifest['sha256']))
            self.assertEqual(set(manifest['sha256']),{'navbot/app.py','sales/tenant.py','sales/README.md','navbot/catalog.json','sales/examples/a.json'})
            self.assertTrue(target.with_suffix('.zip.sha256').is_file())


class TenantClient(Client):
    def __init__(self,base,domain):super().__init__(base);self.domain=domain
    def request(self,path,data=None,headers=None):return super().request(path,data,{'Host':self.domain,**(headers or {})})


class Isolation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='navbot-tenants-');self.addCleanup(self.temp.cleanup)
        self.instances={}
        for letter,password,secret in (('a',PASSWORD_A,SECRET_A),('b',PASSWORD_B,SECRET_B)):
            spec=example(letter)
            while True:
                with socket.socket() as listener:
                    listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
                if 10000<=port<=60000:break
            spec['port']=port
            dbpath=Path(self.temp.name)/letter/'navbot.sqlite3';tenant.initialize_database(spec,dbpath)
            db=sqlite3.connect(dbpath);db.row_factory=sqlite3.Row
            auth.create_user(db,{'username':'admin','full_name':'Admin '+letter,'role':'admin','department':'Registrar','operator':None,'password':password})
            db.execute('UPDATE users SET must_change_password=0')
            owner_control.configure(db,'owner',password,secret,owner_control.totp(secret,int(time.time())//30-1))
            db.commit();db.close()
            log=open(Path(self.temp.name)/(letter+'.log'),'w+');self.addCleanup(log.close)
            process=subprocess.Popen([sys.executable,str(APP),'--host','127.0.0.1','--port',str(port),'--db',str(dbpath),'--tenant',spec['id']],stdout=log,stderr=log)
            self.addCleanup(self.stop,process)
            client=TenantClient('http://127.0.0.1:'+str(port),spec['domain'])
            for _ in range(100):
                try:
                    if client.request('/api/catalog')[0]==200:break
                except (OSError,urllib.error.URLError):time.sleep(.05)
            else:self.fail('Tenant server did not start')
            self.assertEqual(client.login('admin',password)[0],200)
            self.instances[letter]=(spec,dbpath,client)

    @staticmethod
    def stop(process):
        if process.poll() is None:process.terminate();process.wait(timeout=5)

    def test_sessions_hosts_records_and_owner_suspension_are_isolated(self):
        a,adb,ca=self.instances['a'];b,bdb,cb=self.instances['b']
        self.assertEqual(ca.request('/api/settings')[1]['settings']['university_short'][0],'Namuna A')
        self.assertEqual(cb.request('/api/settings')[1]['settings']['university_short'][0],'Namuna B')
        self.assertEqual(ca.request('/api/catalog',headers={'Host':b['domain']})[0],421)
        self.assertEqual(ca.request('/downloads/NAVBOT-TV.apk')[0],404)
        cookie=next(c.value for c in ca.cookies if c.name==auth.COOKIE_NAME)
        self.assertEqual(cb.request('/api/requests',headers={'Cookie':auth.COOKIE_NAME+'='+cookie})[0],401)
        ticket=ca.request('/api/ticket',{'key':__import__('uuid').uuid4().hex,'lang':'uz','section':0,'service':0})
        self.assertEqual(ticket[0],200)
        self.assertEqual(len(ca.request('/api/requests')[1]['requests']),1)
        self.assertEqual(cb.request('/api/requests')[1]['requests'],[])
        self.assertEqual(cb.request('/api/state')[1]['waiting'],[])
        self.assertEqual(ca.request('/api/owner/login',{'username':'owner','password':PASSWORD_A,'code':owner_control.totp(SECRET_A,int(time.time())//30)})[0],200)
        owner_cookie=next(c.value for c in ca.cookies if c.name==owner_control.COOKIE)
        self.assertEqual(cb.request('/api/owner/status',headers={'Cookie':owner_control.COOKIE+'='+owner_cookie})[0],401)
        status=ca.request('/api/owner/status')[1]
        paused=ca.request('/api/owner/control',{'action':'suspend','password':PASSWORD_A,'reason':'Tenant A test pause','version':status['version']})
        self.assertEqual(paused[0],200)
        self.assertEqual(ca.request('/api/state')[0],503)
        self.assertEqual(cb.request('/api/state')[0],200)
        self.assertEqual(cb.request('/api/requests')[0],200)
        resumed=ca.request('/api/owner/control',{'action':'resume','password':PASSWORD_A,'reason':'Tenant A test resume','version':paused[1]['version']})
        self.assertEqual(resumed[0],200)
        self.assertEqual(len(ca.request('/api/requests')[1]['requests']),1)

    def test_verified_backup_restores_the_same_tenant_only(self):
        from contextlib import nullcontext
        spec=importlib.util.spec_from_file_location('tenant_backup_test',ROOT/'deploy/navbot-backup.py');backup=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup)
        a,dbpath,ca=self.instances['a']
        code=Path(self.temp.name)/'minimal-code';(code/'navbot').mkdir(parents=True);(code/'navbot/app.py').write_text('# Snapshot code')
        output=Path(self.temp.name)/'backups-a'
        archive,counts=backup.create_backup(dbpath.parent,code,output,nullcontext)
        self.assertEqual(backup.verify_backup(archive),counts)
        self.assertEqual(archive.stat().st_mode&0o077,0)
        import tarfile
        stage=Path(self.temp.name)/'restored-a';stage.mkdir()
        with tarfile.open(archive) as tar:tar.extractall(stage,filter='data')
        db=sqlite3.connect(stage/'data/navbot.sqlite3');db.row_factory=sqlite3.Row
        self.assertEqual(tenant_instance.verify(db,'university-a')['domain'],a['domain'])
        with self.assertRaises(ValueError):tenant_instance.verify(db,'university-b')
        db.close()
        self.assertEqual(self.instances['b'][2].request('/api/requests')[0],200)
