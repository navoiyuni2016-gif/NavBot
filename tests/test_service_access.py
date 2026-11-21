import test_daily_queue
import unittest
import app
import service_access,workflow

class ServiceAccess(unittest.TestCase):
    setUp=test_daily_queue.DailyQueue.setUp
    tearDown=test_daily_queue.DailyQueue.tearDown
    issue=test_daily_queue.DailyQueue.issue
    def test_suspension_preserves_read_scope_and_unblock_restores_actions(self):
        users={row['role']:dict(row) for row in self.db.execute('SELECT * FROM users')}
        head,manager=users['head'],users['manager']
        self.issue('2026-11-21T10:00:00+00:00')
        rows=workflow.requests(self.db,manager)
        self.assertEqual(len(rows),1)
        service_access.change(self.db,head,{'user_id':manager['id'],'action':'block','reason':'Takroriy xato'})
        self.assertEqual(len(workflow.requests(self.db,manager)),1)
        for path in service_access.SERVICE_PATHS:
            with self.assertRaises(workflow.Problem) as error:service_access.enforce(self.db,manager,path)
            self.assertEqual(error.exception.status,403)
            with self.assertRaises(workflow.Problem) as error:app.mutate(self.db,path,{},manager)
            self.assertEqual(error.exception.status,403)
        service_access.enforce(self.db,manager,'/api/students/search')
        with self.assertRaises(workflow.Problem):service_access.change(self.db,manager,{'user_id':head['id'],'action':'block','reason':'Xato'})
        with self.assertRaises(workflow.Problem):service_access.change(self.db,head,{'user_id':users['admin']['id'],'action':'block','reason':'Xato'})
        self.assertIn(manager['id'],[r['id'] for r in service_access.managers(self.db,head)['managers']])
        service_access.change(self.db,head,{'user_id':manager['id'],'action':'unblock','reason':'Tuzatildi'})
        service_access.enforce(self.db,manager,'/api/action')
        self.assertIsNone(service_access.status(self.db,manager['id']))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM audit WHERE action LIKE 'manager_service_%'").fetchone()[0],2)
