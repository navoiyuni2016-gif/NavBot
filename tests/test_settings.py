import base64
from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'navbot'
sys.path.insert(0, str(ROOT))
import app
import auth
import workflow


class SettingsAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(app, 'DATABASE', Path(self.tmp.name) / 'test.sqlite3')
        self.patch.start()
        app.initialize(True)
        self.db = app.connection()
        self.admin = next(u for u in auth.users(self.db) if u['role'] == 'admin')
        self.manager = next(u for u in auth.users(self.db) if u['username'] == 'manager')

    def tearDown(self):
        self.db.close()
        self.patch.stop()
        self.tmp.cleanup()

    def test_local_logo_upload_persistence_role_and_script_rejection(self):
        png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jQ1sAAAAASUVORK5CYII='
        payload = {'section': 0, 'mime': 'image/png', 'data': png}
        with self.db:
            result = app.mutate(self.db, '/api/admin/logo', payload, self.admin)
        self.assertEqual(result['settings']['section_logos'][0], 'data:image/png;base64,' + png)
        with closing(app.connection()) as other:
            self.assertEqual(app.settings(other)['section_logos'][0], 'data:image/png;base64,' + png)
        with self.assertRaises(workflow.Problem) as denied:
            app.mutate(self.db, '/api/admin/logo', payload, self.manager)
        self.assertEqual(denied.exception.status, 403)
        for mime, data in [('image/svg+xml', '<svg onload="alert(1)"/>'), ('image/png', '<script>alert(1)</script>')]:
            with self.assertRaises(workflow.Problem):
                app.mutate(self.db, '/api/admin/logo', {'section': 0, 'mime': mime, 'data': base64.b64encode(data.encode()).decode()}, self.admin)
        with self.assertRaises(workflow.Problem):
            app.save_settings(self.db, self.admin, {'settings': {'section_logos': ['javascript:alert(1)'] * 5}})

    def test_original_receipt_survives_request_and_catalog_edits(self):
        from uuid import uuid4
        payload = {'key': str(uuid4()), 'lang': 'en', 'section': 0, 'service': 0}
        with self.db:
            receipt = app.mutate(self.db, '/api/ticket', payload, None)
            self.db.execute("UPDATE requests SET content='Changed during interview' WHERE ticket_id=?", (receipt['id'],))
            catalog = app.settings(self.db)['catalog']
            catalog[0][1][0][2] = 'New display name'
            app.save_settings(self.db, self.admin, {'settings': {'catalog': catalog}})
            reprint = app.mutate(self.db, '/api/ticket', payload, None)
        self.assertEqual(reprint['id'], receipt['id'])
        self.assertEqual(reprint['content'], receipt['content'])
        self.assertEqual(reprint['content'], 'Submit a medical certificate')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM tickets').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM requests').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
