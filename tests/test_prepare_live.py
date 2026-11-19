"""One-time cleanup preserves configured data, backs up, and refuses demo passwords."""
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'navbot'))
import app,auth,audio_store,kiosk_printer
spec=importlib.util.spec_from_file_location('prepare_live',ROOT/'deploy/prepare-live.py')
live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)

class PrepareLive(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.db=Path(self.temp.name)/'test.sqlite3'
        self.previous=app.DATABASE;app.DATABASE=self.db;app.initialize(True)
    def tearDown(self):app.DATABASE=self.previous;self.temp.cleanup()
    def connect(self):
        db=sqlite3.connect(self.db);db.row_factory=sqlite3.Row;return db
    def test_default_report_is_read_only_and_lists_demo_accounts(self):
        with self.connect() as db:
            result=live.report(db)
            self.assertIn('admin',result['sinov_parolida_qolgan_loginlar'])
            self.assertGreater(result['saqlanadi']['students'],0)
    def test_cleanup_refuses_known_demo_password_without_any_deletion(self):
        before=self.db.read_bytes()
        with self.assertRaisesRegex(RuntimeError,'sinov parollari'):live.clean(self.db)
        self.assertEqual(self.db.read_bytes(),before)
        self.assertEqual(list(self.db.parent.glob('*.bak')),[])
    def test_verified_backup_and_configuration_survive_queue_reset(self):
        with self.connect() as db:
            # These are disposable fixture accounts, never a production credential.
            db.execute('UPDATE users SET password_hash=?',(auth._hash('Fixture-Unique-Password!'),))
            admin=dict(db.execute("SELECT * FROM users WHERE username='admin'").fetchone())
            audio_store.install_pack(db,admin)
            db.execute("INSERT INTO tickets(id,request_key,lang,section,service,prefix,queue_seq,target_operator) VALUES(1,'bd210bef-4116-4b38-bf45-b01311585c14','uz',0,0,'A',31,1)")
            db.execute("INSERT INTO calls(ticket,operator,lang) VALUES(1,1,'uz')")
            preserved={t:[tuple(row) for row in db.execute('SELECT * FROM '+t)] for t in ('users','students','settings','audio_clips','audio_modes','audio_layouts','kiosk_printer')}
        result=live.clean(self.db)
        self.assertTrue(Path(result['zaxira']).is_file())
        self.assertEqual(Path(result['zaxira']).stat().st_mode&0o777,0o600)
        with sqlite3.connect(result['zaxira']) as backup:self.assertEqual(backup.execute('SELECT queue_seq FROM tickets').fetchone()[0],31)
        with self.connect() as db:
            for t,rows in preserved.items():self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+t)],rows,t)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM calls').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM tickets').fetchone()[0],0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='production_test_cleanup'").fetchone()[0],1)
            self.assertEqual(kiosk_printer.ticket_status(db,{'key':'bd210bef-4116-4b38-bf45-b01311585c14'}),{'state':'cancelled'})
            ticket=app.mutate(db,'/api/ticket',{'key':'ad210bef-4116-4b38-bf45-b01311585c14','lang':'uz','section':0,'service':0},None)
            self.assertEqual(ticket['code'],'A-001')
        with self.assertRaisesRegex(RuntimeError,'allaqachon'):live.clean(self.db)
