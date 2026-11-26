"""Operational boundaries: no live services, tokens or Telegram messages."""
import base64
from contextlib import nullcontext
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'navbot'))
import app
import attachments
import operations
import workflow as w


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'deploy'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


monitor=load('monitor','navbot-monitor.py')
backup=load('backup_ops','navbot-backup.py')
restore=load('restore_ops','navbot-restore-drill.py')
security=load('security_ops','navbot-security-check.py')


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def test_alerts_deduplicate_remind_and_recover_without_data_payloads(self):
        config={'alert_chat_id':42424242};state=self.root/'state'
        failed={'checked_at':datetime.now(timezone.utc).isoformat(),'ok':False,'checks':[{'key':'web','state':'error','detail':'HTTP check failed'}]}
        with patch.object(monitor,'collect',return_value=failed),patch.object(monitor,'notify') as send,patch('builtins.print'):
            monitor.run(config,state);monitor.run(config,state)
            self.assertEqual(send.call_count,1)
            self.assertEqual(send.call_args.args[0]['alert_chat_id'],42424242)
            self.assertEqual(send.call_args.args[1],'NAVBOT monitoring\nweb: HTTP check failed')
            saved=json.loads((state/'alert-state.json').read_text());saved['sent_at']=0
            monitor.atomic_json(state/'alert-state.json',saved)
            monitor.run(config,state);self.assertEqual(send.call_count,2)
        recovered={'checked_at':datetime.now(timezone.utc).isoformat(),'ok':True,'checks':[{'key':'web','state':'ok','detail':'HTTP OK'}]}
        with patch.object(monitor,'collect',return_value=recovered),patch.object(monitor,'notify') as send,patch('builtins.print'):
            monitor.run(config,state);monitor.run(config,state)
            self.assertEqual(send.call_count,1);self.assertIn('recovered',send.call_args.args[1])
        self.assertEqual((state/'status.json').stat().st_mode&0o777,0o640)

    def test_failed_alert_never_logs_exception_or_token_and_is_retried(self):
        result={'checked_at':datetime.now(timezone.utc).isoformat(),'ok':False,'checks':[{'key':'web','state':'error','detail':'HTTP check failed'}]}
        with patch.object(monitor,'collect',return_value=result),patch.object(monitor,'notify',side_effect=RuntimeError('SECRET URL')),patch('builtins.print') as output:
            monitor.run({'alert_chat_id':42424242},self.root)
        self.assertNotIn('SECRET',str(output.call_args));self.assertEqual(json.loads((self.root/'status.json').read_text())['notification'],'failed')
        self.assertFalse((self.root/'alert-state.json').exists())

    def test_missing_backup_stale_poll_and_tls_expiry_are_reported(self):
        data=self.root/'data';data.mkdir();out=self.root/'backups';out.mkdir()
        with sqlite3.connect(data/'navbot.sqlite3') as db:
            db.execute('CREATE TABLE telegram_runtime(key TEXT,value TEXT)')
            db.execute("INSERT INTO telegram_runtime VALUES('last_poll','2020-01-01T00:00:00+00:00')")
        (data/'navbot.sqlite3').chmod(0o600)
        with patch.object(monitor,'service_state',return_value=True),patch.object(monitor,'web_check',return_value=True),patch.object(monitor,'frontend_check',return_value=True),patch.object(monitor,'tls_days',return_value=20):
            status=monitor.collect({'data_dir':str(data),'backup_dir':str(out),'tls_host':'example.test','min_free_mb':0})
        checks={c['key']:c for c in status['checks']}
        self.assertEqual(checks['backup']['state'],'error');self.assertEqual(checks['telegram']['state'],'error');self.assertEqual(checks['tls']['state'],'warning');self.assertFalse(status['ok'])

    def test_admin_report_is_bounded_and_reports_stale_or_missing_state(self):
        path=self.root/'status.json'
        with patch.dict(os.environ,{'NAVBOT_OPERATIONS_STATUS':str(path)}):
            self.assertFalse(operations.status()['installed'])
            path.write_text(json.dumps({'checked_at':'2020-01-01T00:00:00+00:00','checks':[{'key':'web','state':'ok','detail':'HTTP OK'},{'key':'token','state':'ok','detail':'SECRET'}]}))
            report=operations.status();self.assertTrue(report['stale']);self.assertNotIn('SECRET',str(report))
            path.write_bytes(b'x'*32769);self.assertFalse(operations.status()['installed'])

    def test_external_copy_requires_mount_and_verifies_bytes(self):
        source=self.root/'navbot-backup-20261126T000000Z-1234abcd.tar.gz';source.write_bytes(b'verified snapshot')
        target=self.root/'mirror';target.mkdir()
        with self.assertRaisesRegex(RuntimeError,'mount'):backup.mirror_backup(source,target)
        with patch.object(Path,'is_mount',return_value=True):backup.mirror_backup(source,target)
        self.assertEqual((target/source.name).read_bytes(),source.read_bytes());self.assertEqual((target/source.name).stat().st_mode&0o777,0o600)

    def test_real_backup_restore_login_and_attachment_preserves_source(self):
        data=self.root/'data';data.mkdir();code=self.root/'code';code.mkdir()
        shutil.copytree(ROOT/'navbot',code/'navbot',ignore=shutil.ignore_patterns('__pycache__','*.sqlite3*'))
        database=data/'navbot.sqlite3';old=app.DATABASE;app.DATABASE=database
        try:app.initialize(demo=True)
        finally:app.DATABASE=old
        with sqlite3.connect(database) as db:
            db.row_factory=sqlite3.Row
            manager=dict(db.execute("SELECT * FROM users WHERE username='manager'").fetchone())
            admin=dict(db.execute("SELECT * FROM users WHERE username='admin'").fetchone())
            row=w.phone_request(db,manager,{'key':str(uuid4()),'hemis_id':'100000000001','identity_confirmed':True,'channel':'phone','lang':'uz','section':0,'service':0,'content':'Recovery test','note':'private'},app.CATALOG)
            attachments.upload(db,admin,{'id':row['id'],'version':row['version'],'key':str(uuid4()),'name':'recovery.txt','data':base64.b64encode(b'Exact recovery attachment').decode()})
        audit=security.audit(database)
        self.assertGreater(audit['demo_password_accounts'],0)
        self.assertNotIn('password_hash',str(audit));self.assertNotIn('Navbot-Test',str(audit))
        before=backup.digest(database)
        archive,counts=backup.create_backup(data,code,self.root/'backup',nullcontext)
        report=json.loads((self.root/'backup/last-verified.json').read_text());self.assertEqual(report['archive'],archive.name)
        self.assertEqual(report['counts'],counts)
        account=pwd.getpwuid(os.geteuid()).pw_name if os.geteuid()!=0 else 'nobody'
        result=restore.drill(archive,account)
        self.assertEqual(result['attachment'],'ok');self.assertEqual(result['login'],'ok');self.assertEqual(result['counts'],counts)
        self.assertEqual(backup.digest(database),before)


if __name__=='__main__':unittest.main()
