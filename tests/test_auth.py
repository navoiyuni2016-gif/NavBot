"""Auth tests using real SQLite and password hashes, no HTTP mocks."""
import hashlib
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'navbot'))
import auth


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('PRAGMA foreign_keys=ON')
        auth.initialize(self.db, demo=True)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def login(self, username='manager', password=auth.DEMO_PASSWORD):
        return auth.login(self.db, username, password)

    def cookie(self, token):
        return f'{auth.COOKIE_NAME}={token}'

    def test_no_production_default_accounts(self):
        with sqlite3.connect(':memory:') as db:
            auth.initialize(db)
            self.assertEqual(auth.users(db), [])

    def test_hashed_password_and_token_not_exposed(self):
        token, user = self.login()
        self.assertEqual(user['operator'], 1)
        self.assertFalse(user['must_change_password'])
        self.assertNotIn('password_hash', user)
        self.assertNotIn('password_hash', auth.users(self.db)[0])
        password_hash = self.db.execute('SELECT password_hash FROM users WHERE username=?', ('manager',)).fetchone()[0]
        self.assertNotEqual(password_hash, auth.DEMO_PASSWORD)
        self.assertTrue(password_hash.startswith('pbkdf2_sha256$'))
        stored_token = self.db.execute('SELECT token_hash FROM sessions').fetchone()[0]
        self.assertNotEqual(token, stored_token)
        self.assertEqual(stored_token, hashlib.sha256(token.encode()).hexdigest())
        self.assertEqual(auth.current(self.db, self.cookie(token)), user)
        self.assertEqual(len(auth.users(self.db)), 6)

    def test_logout_and_expiry(self):
        token, _ = self.login()
        self.db.execute('UPDATE sessions SET expires_at=1')
        self.assertIsNone(auth.current(self.db, self.cookie(token)))
        token, _ = self.login()
        auth.logout(self.db, self.cookie(token))
        self.assertIsNone(auth.current(self.db, self.cookie(token)))
        for cookie in [None, '', 'navbot_session=not-token', 'wrong=abcd', 'x' * 9000]:
            self.assertIsNone(auth.current(self.db, cookie))

    def test_password_change_requires_current_and_revokes_all_sessions(self):
        token1, user = self.login()
        token2, _ = self.login()
        with self.assertRaises(auth.AuthError):
            auth.change_password(self.db, user, 'WrongPassword1!', 'Replacement-2026!')
        with self.assertRaises(auth.AuthError):
            auth.change_password(self.db, user, auth.DEMO_PASSWORD, auth.DEMO_PASSWORD)
        changed = auth.change_password(self.db, user, auth.DEMO_PASSWORD, 'Replacement-2026!')
        self.db.commit()
        self.assertFalse(changed['must_change_password'])
        for token in [token1, token2]:
            self.assertIsNone(auth.current(self.db, self.cookie(token)))
        with self.assertRaises(auth.AuthError) as error:
            self.login(password=auth.DEMO_PASSWORD)
        self.assertEqual(error.exception.status, 401)
        self.assertEqual(self.login(password='Replacement-2026!')[1]['id'], user['id'])

    def test_create_reset_and_demo_does_not_overwrite_password(self):
        user = auth.create_user(self.db, {
            'username': 'new.manager', 'full_name': 'Test Menejer', 'role': 'manager',
            'department': 'Registrar', 'operator': 3, 'password': 'Temporary-2026!'})
        self.db.commit()
        self.assertTrue(user['must_change_password'])
        token, _ = self.login('new.manager', 'Temporary-2026!')
        reset = auth.reset_password(self.db, user['id'], 'Temporary-2027!')
        self.db.commit()
        self.assertTrue(reset['must_change_password'])
        self.assertIsNone(auth.current(self.db, self.cookie(token)))
        self.login('new.manager', 'Temporary-2027!')
        manager_token, manager = self.login()
        auth.change_password(self.db, manager, auth.DEMO_PASSWORD, 'Changed-Demo-2026!')
        self.db.commit()
        auth.initialize(self.db, demo=True)
        self.db.commit()
        self.login('manager', 'Changed-Demo-2026!')
        self.assertEqual(len(auth.users(self.db)), 7)

    def test_create_validation_uniqueness_and_weak_password(self):
        base = dict(username='test.user', full_name='Test User', role='executor',
                    department='Test Department', password='Temporary-2026!')
        for change in [dict(role='root'), dict(username='a'), dict(username="x' OR 1=1"),
                       dict(password='weak'), dict(full_name=''), dict(operator=1),
                       dict(role='manager', operator=31), dict(role='manager', operator=True)]:
            with self.subTest(change=change), self.assertRaises(auth.AuthError):
                auth.create_user(self.db, dict(base, **change))
        auth.create_user(self.db, base)
        with self.assertRaises(auth.AuthError) as error:
            auth.create_user(self.db, dict(base, username='TEST.USER'))
        self.assertEqual(error.exception.status, 409)

    def test_rate_limit_commits_failures_and_recovers_after_window(self):
        with patch.object(auth.time, 'time', return_value=100000):
            for _ in range(5):
                with self.assertRaises(auth.AuthError) as error:
                    self.login(password='wrong')
                self.assertEqual(error.exception.status, 401)
                self.db.rollback()  # Handler's error cleanup must not erase a failure.
            with self.assertRaises(auth.AuthError) as error:
                self.login()
            self.assertEqual(error.exception.status, 429)
        with patch.object(auth.time, 'time', return_value=100901):
            token, _ = self.login()
            self.assertTrue(token)
        self.assertIsNone(self.db.execute('SELECT identity FROM auth_attempts WHERE identity=?', ('manager',)).fetchone())

    def test_unknown_user_errors_match_wrong_password(self):
        errors = []
        for username in ['manager', 'missing_user']:
            with self.assertRaises(auth.AuthError) as error:
                self.login(username=username, password='wrong')
            errors.append((error.exception.message, error.exception.status))
        self.assertEqual(errors[0], errors[1])


if __name__ == '__main__':
    unittest.main()
