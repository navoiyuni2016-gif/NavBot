"""Date-scoped immutable queue codes; IDs and history never reset."""
from pathlib import Path
import sqlite3
import tempfile
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'navbot'))
import app,workflow,routing

class DailyQueue(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.previous=app.DATABASE
        app.DATABASE=Path(self.temp.name)/'test.sqlite3';app.initialize(True)
        self.db=app.connection()
    def tearDown(self):self.db.close();app.DATABASE=self.previous;self.temp.cleanup()
    def issue(self,stamp,key=None,section=0):
        with patch.object(workflow,'now',return_value=stamp):
            return app.mutate(self.db,'/api/ticket',{'key':key or str(uuid4()),'lang':'uz','section':section,'service':0},None)
    def test_midnight_in_tashkent_restarts_only_codes_and_preserves_prior_queue(self):
        key=str(uuid4());old=self.issue('2026-11-21T18:59:59+00:00',key)
        self.assertEqual(self.issue('2026-11-21T18:59:59+00:00')['code'],'A-002')
        new=self.issue('2026-11-21T19:00:00+00:00')
        self.assertEqual((old['queue_day'],new['queue_day']),('2026-11-21','2026-11-22'))
        self.assertEqual((old['code'],new['code']),('A-001','A-001'))
        self.assertNotEqual(old['id'],new['id'])
        self.assertEqual(self.issue('2026-11-21T20:00:00+00:00',key)['id'],old['id'])
        self.assertEqual(self.issue('2026-11-21T20:00:00+00:00')['code'],'A-002')
        self.assertEqual(self.issue('2026-11-21T20:00:00+00:00',section=1)['code'],'B-001')
        state=app.snapshot(self.db,1)
        self.assertEqual(len(state['waiting']),5)
        self.assertEqual({r['queue_day'] for r in state['waiting']},{'2026-11-21','2026-11-22'})
    def test_existing_numbers_backfill_without_renumbering(self):
        self.db.execute('DROP INDEX ticket_day_code')
        self.db.execute('CREATE UNIQUE INDEX ticket_code ON tickets(prefix,queue_seq)')
        old=self.issue('2026-11-20T10:00:00+00:00')
        self.db.execute("UPDATE tickets SET queue_seq=54,queue_day='' WHERE id=?",(old['id'],))
        routing.initialize_daily_queue(self.db)
        row=self.db.execute('SELECT * FROM tickets WHERE id=?',(old['id'],)).fetchone()
        self.assertEqual((row['queue_day'],row['queue_seq']),('2026-11-20',54))
        self.assertEqual(self.issue('2026-11-21T10:00:00+00:00')['code'],'A-001')

    def test_claim_and_startup_repair_only_known_department(self):
        ticket=self.issue('2026-11-21T10:00:00+00:00')
        manager=dict(self.db.execute("SELECT * FROM users WHERE username='manager'").fetchone())
        app.mutate(self.db,'/api/action',{'operator':1,'action':'call','ticket_id':ticket['id']},manager)
        row=self.db.execute('SELECT * FROM requests WHERE ticket_id=?',(ticket['id'],)).fetchone()
        self.assertEqual(row['department'],manager['department'])
        self.db.execute("UPDATE requests SET department='' WHERE id=?",(row['id'],));self.db.commit()
        app.initialize()
        self.assertEqual(self.db.execute('SELECT department FROM requests WHERE id=?',(row['id'],)).fetchone()[0],manager['department'])

    def test_rename_catalog_keeps_historical_service_content(self):
        import copy,json
        config=copy.deepcopy(app.settings(self.db))
        config['catalog'][0][1][0]=['Transkript oliş','Получение транскрипта','Request a transcript']
        config['catalog'][3][1][0]=['Tölovlar','Платежи','Payments']
        self.db.execute('INSERT OR REPLACE INTO settings VALUES(1,?)',(json.dumps(config),))
        ticket=self.issue('2026-11-20T10:00:00+00:00');self.db.commit()
        app.initialize()
        self.assertEqual(app.settings(self.db)['catalog'][0][1][0][0],'Tibbiy ma’lumotnoma taqdim etiş')
        self.assertEqual(app.settings(self.db)['catalog'][3][1][0][0],'Tölov-kontrakt')
        self.assertEqual(self.db.execute('SELECT content_name FROM tickets WHERE id=?',(ticket['id'],)).fetchone()[0],'Transkript oliş')

    def test_section_title_updates_preserve_custom_translations(self):
        import copy,json
        config=copy.deepcopy(app.settings(self.db))
        config['catalog'][0][0][2]='Academic services'
        config['catalog'][4][0][2]='Placements and internships'
        config['catalog'][1][0][0]='Ilmiy va innovatsion'
        config['catalog'][1][0][1]='Custom Russian title'
        self.db.execute('INSERT OR REPLACE INTO settings VALUES(1,?)',(json.dumps(config),))
        self.db.commit();app.initialize()
        saved=app.settings(self.db)['catalog']
        self.assertEqual(saved[0][0][2],'ISSUES')
        self.assertEqual(saved[4][0][2],'Internships')
        self.assertEqual(saved[1][0][0],'Ilmiy va innovatsiya masalalari')
        self.assertEqual(saved[1][0][1],'Custom Russian title')
