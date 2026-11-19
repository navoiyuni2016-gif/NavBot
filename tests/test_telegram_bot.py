"""Offline student ownership, approval and delivery failure boundary checks."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'navbot'))
import app
import telegram_bot as bot
import telegram_worker as worker
import workflow as w

SID='100000000001'

class FakeAPI:
    def __init__(self,failure=None):self.calls=[];self.failure=failure
    def call(self,method,data=None,file=None):
        self.calls.append((method,data,file))
        if self.failure:raise self.failure
        return {'message_id':77}

class TelegramBotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.path=Path(cls.temp.name)/'base.sqlite3'
        old=app.DATABASE;app.DATABASE=cls.path
        try:app.initialize(demo=True)
        finally:app.DATABASE=old
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        with sqlite3.connect(self.path) as source:source.backup(self.db)
        self.addCleanup(self.db.close);self.update_id=0
        self.users={row['username']:dict(row) for row in self.db.execute('SELECT * FROM users')}
    def send(self,text='',chat=101,data=None):
        self.update_id+=1
        message={'chat':{'id':chat,'type':'private'},'from':{'id':chat},'text':text}
        update={'update_id':self.update_id,'message':message}
        if data is not None:update={'update_id':self.update_id,'callback_query':{'id':str(self.update_id),'from':{'id':chat},'message':message,'data':data}}
        with self.db:bot.process_update(self.db,update)
        return update
    def code(self,sid=SID):
        with self.db:return bot.issue_code(self.db,self.users['manager'],{'hemis_id':sid,'identity_confirmed':True})['code']
    def link(self,sid=SID,chat=101):
        code=self.code(sid);self.send('/start',chat);self.send(sid,chat);self.send(code,chat)
        self.assertEqual(self.db.execute('SELECT student_id FROM telegram_links WHERE chat_id=?',(chat,)).fetchone()[0],sid)
    def request(self,sid=SID):
        with self.db:return w.phone_request(self.db,self.users['manager'],{'key':str(uuid4()),'hemis_id':sid,'identity_confirmed':True,'channel':'phone','lang':'uz','section':0,'service':0,'content':'Student request','note':'INTERNAL NOTE'},app.CATALOG)
    def action(self,row,action,user='admin',**kwargs):
        with self.db:return w.request_action(self.db,self.users[user],{'id':row['id'],'version':row['version'],'action':action,**kwargs})
    def pending(self,sid=SID):
        row=self.request(sid)
        row=self.action(row,'assign',assignee_id=self.users['executor']['id'],deadline='2099-01-01T00:00:00+00:00',internal_basis='PRIVATE BASIS')
        return self.action(row,'submit',user='executor',answer='APPROVED ANSWER')
    def payloads(self):return '\n'.join(row[0] for row in self.db.execute('SELECT payload FROM telegram_outbox'))
    def test_identity_requires_staff_confirmation_and_one_time_secret(self):
        with self.assertRaises(w.Problem):bot.issue_code(self.db,self.users['manager'],{'hemis_id':SID})
        with self.assertRaises(w.Problem):bot.issue_code(self.db,self.users['head'],{'hemis_id':SID,'identity_confirmed':True})
        code=self.code();stored=self.db.execute('SELECT * FROM telegram_codes').fetchone()
        self.assertNotIn(code,str(tuple(stored)));self.assertTrue(all(code not in row[0] for row in self.db.execute('SELECT detail FROM audit')))
        self.send(SID);self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_links').fetchone()[0],0)
        self.send(code);self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_codes').fetchone()[0],0)
        self.send(SID,102);self.send(code,102);self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_links').fetchone()[0],1)
    def test_expiry_reissue_and_five_attempt_limit(self):
        old=self.code();new=self.code();self.assertNotEqual(old,new)
        self.send(SID)
        for _ in range(5):self.send('WRONG')
        self.send(new)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_links').fetchone()[0],0)
        self.assertIn('15 daqiqa',self.payloads())
        self.db.execute('DELETE FROM telegram_failures');self.db.execute('UPDATE telegram_codes SET attempts=0,expires_at=0');self.db.commit()
        self.send(new);self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_links').fetchone()[0],0)
    def test_groups_duplicate_updates_and_unknown_ids_do_not_disclose_records(self):
        update={'update_id':1,'message':{'chat':{'id':-7,'type':'group'},'from':{'id':101},'text':SID}}
        with self.db:bot.process_update(self.db,update)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_chats').fetchone()[0],0)
        self.update_id=1;update=self.send('999999999999')
        before=self.db.execute('SELECT COUNT(*) FROM telegram_outbox').fetchone()[0]
        with self.db:bot.process_update(self.db,update)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_outbox').fetchone()[0],before)
        self.assertNotIn('Sinov Talaba',self.payloads())
    def test_all_menus_languages_and_cross_student_callbacks(self):
        self.link();own=self.request();other=self.request('100000000002')
        for command in ('/requests','/track','/profile','/help','/language'):self.send(command)
        for lang in ('ru','en','uz'):self.send(data='lang:'+lang)
        self.send(data='req:'+str(other['id']));self.send(data='ans:'+str(other['id']))
        self.assertNotIn('INTERNAL NOTE',self.payloads());self.assertIn('ruxsat yo‘q',self.payloads())
        self.assertIn('Mutaxassislik',self.payloads());self.assertIn('NAV-'+str(own['id']).zfill(4),self.payloads())
    def test_draft_hidden_approved_selected_files_and_dedup(self):
        self.link();row=self.pending()
        import attachments,base64
        for name in ('internal.txt','student.txt'):
            with self.db:row=attachments.upload(self.db,self.users['admin'],{'id':row['id'],'version':row['version'],'key':str(uuid4()),'name':name,'data':base64.b64encode(name.encode()).decode()})['request']
        self.send(data='req:'+str(row['id']));self.send(data='ans:'+str(row['id']))
        self.assertNotIn('APPROVED ANSWER',self.payloads());self.assertNotIn('PRIVATE BASIS',self.payloads())
        selected=row['attachments'][1]['id'];row=self.action(row,'approve',result='Ready',telegram_attachment_ids=[selected])
        jobs=self.db.execute("SELECT * FROM telegram_outbox WHERE batch_key LIKE 'release:%'").fetchall()
        self.assertEqual([j['kind'] for j in jobs],['message','document'])
        self.assertEqual(json.loads(jobs[1]['payload'])['attachment_id'],selected)
        with self.db:bot.schedule_releases(self.db)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM telegram_outbox WHERE batch_key LIKE 'release:%'").fetchone()[0],2)
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'pending')
        self.db.commit();api=FakeAPI()
        while worker.deliver_one(self.db,api):pass
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'sent')
        docs=[c for c in api.calls if c[0]=='sendDocument'];self.assertEqual(len(docs),1);self.assertEqual(docs[0][2]['name'],'student.txt')
    def test_foreign_attachment_rolls_back_approval(self):
        row=self.pending()
        with self.assertRaises(w.Problem):self.action(row,'approve',result='Ready',telegram_attachment_ids=['foreign'])
        self.assertEqual(self.db.execute('SELECT status FROM requests WHERE id=?',(row['id'],)).fetchone()[0],'pending_approval')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_releases').fetchone()[0],0)
    def test_local_resolution_is_not_a_head_approval(self):
        self.link();row=self.request();self.action(row,'resolve',answer='LOCAL SECRET',result='Done')
        self.send(data='ans:'+str(row['id']));self.assertNotIn('LOCAL SECRET',self.payloads())
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'not_approved')
    def test_late_link_gets_approved_answer_and_unlink_scrubs_it(self):
        row=self.pending();self.action(row,'approve',result='Ready')
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'awaiting_link')
        self.link();self.assertEqual(bot.delivery(self.db,row['id'])['state'],'pending')
        with self.db:bot.unlink(self.db,self.users['admin'],{'hemis_id':SID,'reason':'Replacement account'})
        self.assertNotIn('APPROVED ANSWER',self.payloads());self.assertEqual(bot.status(self.db,SID)['linked'],False)
        self.link(chat=102)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_releases').fetchone()[0],1)
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'pending')
    def test_worker_handles_429_blocked_network_and_interrupted_delivery(self):
        self.link();self.db.execute('DELETE FROM telegram_outbox');row=self.pending();self.action(row,'approve',result='Ready');self.db.commit()
        worker.deliver_one(self.db,FakeAPI(worker.TelegramError(429,3)))
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'pending')
        self.assertFalse(worker.deliver_one(self.db,FakeAPI()))
        with self.db:bot.set_runtime(self.db,'send_after',0);self.db.execute('UPDATE telegram_outbox SET next_attempt=0')
        worker.deliver_one(self.db,FakeAPI(worker.TelegramError('network',uncertain=True)))
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'uncertain')
        self.assertFalse(worker.deliver_one(self.db,FakeAPI()))
        with self.db:bot.retry(self.db,self.users['admin'],{'id':row['id']})
        worker.deliver_one(self.db,FakeAPI(worker.TelegramError(403)))
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'failed')
        with self.db:self.db.execute("UPDATE telegram_outbox SET state='sending',lease_until=0");worker.recover(self.db)
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'uncertain')
    def test_changed_link_or_inactive_student_cancels_queued_data(self):
        self.link();row=self.pending();self.action(row,'approve',result='Ready')
        self.db.execute("UPDATE students SET status='inactive' WHERE hemis_id=?",(SID,));self.db.commit();api=FakeAPI()
        while worker.deliver_one(self.db,api):pass
        self.assertTrue(all('APPROVED ANSWER' not in str(call) and call[0]!='sendDocument' for call in api.calls))
    def test_disabled_integration_and_bot_identity_pin(self):
        self.assertIsNone(worker.configured(self.db))
        api=FakeAPI();api.call=lambda *a,**kw:{'id':1,'is_bot':True,'username':'test_bot'}
        worker.identity(self.db,api)
        api.call=lambda *a,**kw:{'id':2,'is_bot':True}
        with self.assertRaises(worker.TelegramError):worker.identity(self.db,api)
    def test_delete_student_and_request_remove_bot_payloads(self):
        import request_delete,student_registry
        self.link();row=self.pending();row=self.action(row,'approve',result='Ready')
        with self.db:request_delete.remove(self.db,self.users['admin'],{'targets':[{'id':row['id'],'version':row['version']}],'confirm_count':1,'reason':'Test purge'})
        self.assertEqual(bot.delivery(self.db,row['id'])['state'],'not_approved')
        self.assertNotIn('APPROVED ANSWER',self.payloads())
        row=self.pending();self.action(row,'approve',result='Ready')
        with self.db:
            preview=student_registry.preview(self.db,self.users['admin'],{'ids':[SID]})
            student_registry.remove(self.db,self.users['admin'],{'token':preview['token'],'confirm_count':1})
        self.assertFalse(bot.status(self.db,SID)['linked']);self.assertNotIn('APPROVED ANSWER',self.payloads())
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_releases').fetchone()[0],0)
    def test_checkpoint_and_jobs_roll_back_together(self):
        self.update_id=41
        update={'update_id':42,'message':{'chat':{'id':101,'type':'private'},'from':{'id':101},'text':'/start'}}
        try:
            with self.db:
                bot.process_update(self.db,update)
                raise RuntimeError('simulated process failure')
        except RuntimeError:pass
        self.assertEqual(bot.runtime(self.db,'last_update_id','-1'),'-1')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_outbox').fetchone()[0],0)
        with self.db:bot.process_update(self.db,update)
        self.assertEqual(bot.runtime(self.db,'last_update_id'),'42')
    def test_claim_is_revalidated_after_token_config_changes(self):
        self.link();self.db.execute('DELETE FROM telegram_outbox');row=self.pending();self.action(row,'approve',result='Ready');self.db.commit()
        api=FakeAPI()
        with patch.object(worker,'configured',return_value=None):
            self.assertFalse(worker.deliver_one(self.db,api,expected_config=('old-reference','old-secret')))
        self.assertEqual(api.calls,[]);self.assertEqual(bot.delivery(self.db,row['id'])['state'],'pending')

    def test_unicode_messages_stay_under_telegram_limit(self):
        text='😀'*6000+'abc';parts=list(bot.chunks(text))
        self.assertEqual(''.join(parts),text)
        self.assertTrue(all(len(p.encode('utf-16-le'))//2<=3500 for p in parts))

if __name__=='__main__':unittest.main()
