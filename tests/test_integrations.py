"""Integration config and read-only outbound boundary tests; no real API calls."""
import json
import os
from pathlib import Path
import socket
import sqlite3
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'navbot'))
import integrations as integration

ADMIN = {'id': 1, 'role': 'admin'}
TOKEN = '123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_123456789'
STUDENT = dict(hemis_id='H24011876', full_name='Sinov Talaba', faculty='Sinov Fakulteti',
               programme='Filologiya', course=2, student_group='TEST-201', education_form='Kunduzgi', status='active')
PUBLIC_DNS = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = sqlite3.connect(str(Path(self.temp.name) / 'test.sqlite3'))
        integration.initialize(self.db)
        self.db.commit()
        self.dns = patch.object(integration.socket, 'getaddrinfo', return_value=PUBLIC_DNS)
        self.dns.start()

    def tearDown(self):
        self.dns.stop()
        self.db.close()
        self.temp.cleanup()

    def save_lms(self, **changes):
        data = dict(kind='lms', url='https://lms.example.edu/api/health',
                    students_url='https://lms.example.edu/api/students', token='private-LMS-bearer', enabled=True)
        data.update(changes)
        result = integration.save(self.db, ADMIN, data)
        self.db.commit()
        return result

    def save_telegram(self, **changes):
        data = dict(kind='telegram', token=TOKEN, enabled=True)
        data.update(changes)
        result = integration.save(self.db, ADMIN, data)
        self.db.commit()
        return result

    def response(self, data, mime='application/json', status=200):
        return status, mime, json.dumps(data).encode('utf-8')

    def test_defaults_disconnected_and_no_credentials(self):
        result = integration.metadata(self.db)
        self.assertFalse(result['lms']['connected'])
        self.assertFalse(result['telegram']['enabled'])
        self.assertFalse(result['telegram']['token_set'])
        self.assertNotIn('token_ref', json.dumps(result))

    def test_save_has_no_network_and_secrets_are_private_files(self):
        with patch.object(integration, '_transport') as network, patch.object(integration.socket, 'getaddrinfo') as dns:
            result = self.save_telegram()
            network.assert_not_called()
            dns.assert_not_called()
        self.assertTrue(result['telegram']['token_set'])
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertNotIn(TOKEN, '\n'.join(self.db.iterdump()))
        directory = Path(self.temp.name) / 'test.sqlite3.integration-secrets'
        files = list(directory.iterdir())
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].read_text(), TOKEN)
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(files[0].stat().st_mode), 0o600)

    def test_blank_token_preserves_clear_removes(self):
        self.save_telegram()
        original = self.db.execute("SELECT token_ref FROM integration_config WHERE kind='telegram'").fetchone()[0]
        result = integration.save(self.db, ADMIN, dict(kind='telegram', token='', enabled=True))
        self.assertTrue(result['telegram']['token_set'])
        self.assertEqual(self.db.execute("SELECT token_ref FROM integration_config WHERE kind='telegram'").fetchone()[0], original)
        result = integration.save(self.db, ADMIN, dict(kind='telegram', clear_token=True, enabled=False))
        self.assertFalse(result['telegram']['token_set'])
        self.db.commit()
        integration.cleanup(self.db)
        self.assertEqual(list((Path(self.temp.name) / 'test.sqlite3.integration-secrets').iterdir()), [])

    def test_secret_replacement_rollback_keeps_original_credential(self):
        self.save_telegram()
        old = self.db.execute("SELECT token_ref FROM integration_config WHERE kind='telegram'").fetchone()[0]
        integration.save(self.db, ADMIN, dict(kind='telegram', token=TOKEN + 'new', enabled=True))
        self.db.rollback()
        self.assertEqual(integration._read_token(self.db, old), TOKEN)
        integration.cleanup(self.db)
        self.assertTrue(integration.metadata(self.db)['telegram']['token_set'])
        files = list((Path(self.temp.name) / 'test.sqlite3.integration-secrets').iterdir())
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, old)

    def test_changed_configuration_during_check_is_not_marked_connected(self):
        self.save_lms()
        def changed(url, headers):
            with sqlite3.connect(str(Path(self.temp.name) / 'test.sqlite3')) as other:
                integration.save(other, ADMIN, dict(kind='lms', url='https://changed.example.edu/api', students_url='', enabled=True))
            return self.response({'healthy': True})
        with patch.object(integration, '_transport', side_effect=changed):
            with self.assertRaises(integration.IntegrationError):
                integration.test(self.db, ADMIN, 'lms')
        self.db.rollback()
        result = integration.metadata(self.db)['lms']
        self.assertFalse(result['connected'])
        self.assertEqual(result['url'], 'https://changed.example.edu/api')

    def test_only_admin_can_mutate_or_check(self):
        for user, code in [(None, 401), ({'id': 2, 'role': 'manager'}, 403)]:
            for method, args in [(integration.save, ({'kind': 'lms'},)), (integration.test, ('lms',)),
                                 (integration.fetch_students, ()), (integration.mark_sync, (1, 2))]:
                with self.subTest(method=method.__name__), self.assertRaises(integration.IntegrationError) as error:
                    method(self.db, user, *args)
                self.assertEqual(error.exception.status, code)

    def test_bad_urls_are_rejected_without_requests(self):
        for url in ['http://lms.example.edu/api', 'https://127.0.0.1/api', 'https://8.8.8.8/api',
                    'https://[::1]/', 'https://localhost/', 'https://metadata.google.internal/',
                    'https://admin:password@lms.example.edu/', 'https://lms.example.edu/?token=private',
                    'https://lms.example.edu/#secret', 'https://lms.example.edu:8443/api',
                    'https://lms.example.edu./', 'https://lms.example.edu\\@private/',
                    'https://lms.example.edu/\napi', 'file:///etc/passwd']:
            with self.subTest(url=url), self.assertRaises(integration.IntegrationError):
                self.save_lms(url=url)

    def test_lms_token_cannot_be_sent_to_different_sync_host(self):
        with self.assertRaises(integration.IntegrationError):
            self.save_lms(students_url='https://different.example.edu/students')

    def test_dns_private_and_mixed_answers_block_outbound(self):
        self.save_lms()
        for ip in ['127.0.0.1', '10.2.0.1', '192.168.1.1', '169.254.169.254', '100.64.0.1', '::1', 'fc00::1']:
            with patch.object(integration.socket, 'getaddrinfo', return_value=PUBLIC_DNS + [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443))]), patch.object(integration, '_transport') as transport:
                result = integration.test(self.db, ADMIN, 'lms')
                self.assertFalse(result['lms']['connected'])
                self.assertIn('taqiqlangan', result['lms']['last_error'])
                transport.assert_not_called()

    def test_telegram_getme_only_and_result_redaction(self):
        self.save_telegram()
        with patch.object(integration, '_transport', return_value=self.response({'ok': True, 'result': {'is_bot': True, 'username': 'Navbot_demo_bot'}})) as transport:
            result = integration.test(self.db, ADMIN, 'telegram')
        url, headers = transport.call_args.args
        self.assertEqual(url, 'https://api.telegram.org/bot' + TOKEN + '/getMe')
        self.assertNotIn('Authorization', headers)
        self.assertTrue(result['telegram']['connected'])
        self.assertEqual(result['telegram']['bot_username'], 'Navbot_demo_bot')
        self.assertTrue(result['telegram']['last_success'])
        self.assertNotIn(TOKEN, json.dumps(result))

    def test_telegram_rejects_user_or_invalid_bot_response(self):
        self.save_telegram()
        for response in [{'ok': False, 'description': TOKEN}, {'ok': True, 'result': {'is_bot': False}},
                         {'ok': True, 'result': {'is_bot': True, 'username': TOKEN}}]:
            with patch.object(integration, '_transport', return_value=self.response(response)):
                result = integration.test(self.db, ADMIN, 'telegram')
            self.assertFalse(result['telegram']['connected'])
            self.assertNotIn(TOKEN, json.dumps(result))

    def test_lms_test_requires_json_and_invalidates_on_change(self):
        self.save_lms()
        with patch.object(integration, '_transport', return_value=self.response({'status': 'ok'})) as transport:
            result = integration.test(self.db, ADMIN, 'lms')
        self.assertEqual(transport.call_args.args[1]['Authorization'], 'Bearer private-LMS-bearer')
        self.assertTrue(result['lms']['connected'])
        last_success = result['lms']['last_success']
        for response in [(200, 'text/html', b'<html>Login</html>'), (200, 'application/json', b'[]'),
                         (200, 'application/json', b'bad json'), (200, 'application/json', b'x' * (integration.MAX_BODY + 1)),
                         (503, 'application/json', b'{}')]:
            with patch.object(integration, '_transport', return_value=response):
                result = integration.test(self.db, ADMIN, 'lms')
            self.assertFalse(result['lms']['connected'])
            self.assertEqual(result['lms']['last_success'], last_success)
            self.assertTrue(result['lms']['last_error'])
        result = integration.save(self.db, ADMIN, dict(kind='lms', url='https://lms.example.edu/api/new-health'))
        self.assertFalse(result['lms']['connected'])
        self.assertIsNone(result['lms']['last_checked'])

    def test_normalized_sync_and_success_metadata(self):
        self.save_lms()
        with patch.object(integration, '_transport', return_value=self.response({'students': [STUDENT]})):
            rows = integration.fetch_students(self.db, ADMIN)
        self.assertEqual(rows, [STUDENT])
        self.assertIsNone(integration.metadata(self.db)['lms']['last_sync'])
        result = integration.mark_sync(self.db, ADMIN, 1, 0)
        self.assertEqual(result['lms']['last_added'], 1)
        self.assertEqual(result['lms']['last_updated'], 0)
        self.assertEqual(result['lms']['last_sync_actor'], 1)
        self.assertTrue(result['lms']['last_sync'])

    def test_malformed_sync_never_returns_partial_rows(self):
        self.save_lms()
        for value in [{'students': []}, {'students': [STUDENT, STUDENT]},
                      {'students': [dict(STUDENT, course=True)]},
                      {'students': [dict(STUDENT, education_form='')]},
                      {'data': [STUDENT]}]:
            with patch.object(integration, '_transport', return_value=self.response(value)):
                self.assertIsNone(integration.fetch_students(self.db, ADMIN))
            result = integration.metadata(self.db)['lms']
            self.assertFalse(result['connected'])
            self.assertIsNone(result['last_sync'])
            self.assertTrue(result['last_error'])

    def test_http_tls_failure_messages_are_sanitized(self):
        self.save_telegram()
        # Real boundary catches exception objects whose repr/string includes URL.
        for error in [HTTPError('https://api.telegram.org/bot' + TOKEN + '/getMe', 401, TOKEN, {}, None),
                      URLError(TOKEN), OSError(TOKEN)]:
            with patch.object(integration, 'build_opener') as opener:
                opener.return_value.open.side_effect = error
                result = integration.test(self.db, ADMIN, 'telegram')
            self.assertFalse(result['telegram']['connected'])
            self.assertNotIn(TOKEN, json.dumps(result))

    def test_redirect_is_refused(self):
        with self.assertRaises(integration.IntegrationError):
            integration._NoRedirect().redirect_request(None, None, 302, 'move', {}, 'http://169.254.169.254/')

    @unittest.skipIf(os.name == 'nt', 'Requires POSIX symlink support')
    def test_secret_directory_symlink_is_refused(self):
        directory = Path(self.temp.name) / 'test.sqlite3.integration-secrets'
        target = Path(self.temp.name) / 'different'
        target.mkdir()
        directory.symlink_to(target, target_is_directory=True)
        with self.assertRaises(integration.IntegrationError):
            self.save_telegram()
        self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
