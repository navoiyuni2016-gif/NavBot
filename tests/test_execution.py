import unittest
import test_daily_queue
import workflow


class ExecutionVisibility(unittest.TestCase):
    setUp = test_daily_queue.DailyQueue.setUp
    tearDown = test_daily_queue.DailyQueue.tearDown
    issue = test_daily_queue.DailyQueue.issue

    def test_shared_execution_does_not_grant_write_scope(self):
        self.issue('2026-11-21T10:00:00+00:00')
        users = [dict(r) for r in self.db.execute('SELECT * FROM users')]
        executor = next(u for u in users if u['role'] == 'executor')
        self.db.execute("UPDATE requests SET manager_id=NULL,assignee_id=NULL,department='Other department'")
        row = self.db.execute('SELECT * FROM requests').fetchone()
        self.assertFalse(workflow.work_scope(executor, row, self.db))
        for status in ('in_progress', 'pending_approval', 'returned'):
            self.db.execute('UPDATE requests SET status=?', (status,))
            row = self.db.execute('SELECT * FROM requests').fetchone()
            for user in users:
                self.assertTrue(workflow.visible(user, row, self.db), user['role'])
            self.assertIn(row['id'], [r['id'] for r in workflow.requests(self.db, executor)])
            self.assertFalse(workflow.work_scope(executor, row, self.db))
            for action in ('update', 'submit', 'approve', 'resolve'):
                with self.assertRaises(workflow.Problem) as error:
                    workflow.request_action(self.db, executor, {'id': row['id'], 'version': row['version'], 'action': action})
                self.assertEqual(error.exception.status, 403)
        for status in ('new', 'closed'):
            self.db.execute('UPDATE requests SET status=?', (status,))
            row = self.db.execute('SELECT * FROM requests').fetchone()
            self.assertFalse(workflow.visible(executor, row, self.db))
