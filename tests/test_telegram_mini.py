"""Signed Mini App authorization and disclosure checks (no Telegram network)."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
from unittest.mock import patch
from test_telegram_bot import TelegramBotTests,SID
import telegram_mini as mini
import telegram_bot as bot
import workflow as w
TOKEN='123456789:'+'X'*35

def signed(chat=101,age=0,**extra):
    values={'auth_date':str(int(time.time())-age),'user':json.dumps({'id':chat,'first_name':'Telegram name'},separators=(',',':')),'query_id':'test',**extra}
    secret=hmac.new(b'WebAppData',TOKEN.encode(),hashlib.sha256).digest()
    values['hash']=hmac.new(secret,'\n'.join(k+'='+v for k,v in sorted(values.items())).encode(),hashlib.sha256).hexdigest()
    return urlencode(values)

class TelegramMiniTests(TelegramBotTests):
    def setUp(self):
        super().setUp();self.secret_patch=patch.object(mini.integrations,'_check_ready',return_value=({},TOKEN));self.secret_patch.start();self.addCleanup(self.secret_patch.stop)
    def call(self,action='state',chat=101,**data):
        with self.db:return mini.handle(self.db,{'init_data':signed(chat),'action':action,**data})
    def test_signed_identity_tamper_expiry_duplicates_and_disabled_integration(self):
        self.assertEqual(mini.authenticate(self.db,signed()),101)
        for raw in ('',signed().replace('Telegram+name','Hacker+name'),signed(age=3601),signed(age=-120),signed()+'&auth_date=1',signed(chat=True),signed(chat=101,chat_type='group')):
            with self.assertRaises(w.Problem):mini.authenticate(self.db,raw)
        with patch.object(mini.integrations,'_check_ready',side_effect=mini.integrations.IntegrationError('disabled')):
            with self.assertRaises(w.Problem):mini.authenticate(self.db,signed())
    def test_id_alone_returns_no_student_and_otp_failures_commit(self):
        state=self.call();self.assertEqual(state,{'linked':False,'lang':'uz'})
        self.code()
        for _ in range(5):self.assertFalse(self.call('link',hemis_id=SID,code='WRONG')['ok'])
        self.assertEqual(self.call('link',hemis_id=SID,code='WRONG')['error_code'],'locked')
        self.assertEqual(self.call()['linked'],False)
        self.assertEqual(self.db.execute('SELECT attempts FROM telegram_codes WHERE student_id=?',(SID,)).fetchone()[0],5)
    def test_link_profile_and_languages_use_verified_database_record(self):
        code=self.code();self.assertTrue(self.call('link',hemis_id=SID,code=code)['ok'])
        state=self.call();self.assertEqual(state['student']['full_name'],'Sinov Talaba Bir')
        self.assertNotIn('source_json',state['student']);self.assertNotIn('gender',state['student']);self.assertNotIn('Telegram name',str(state))
        for lang in ('uz','ru','en'):
            self.call('language',lang=lang);self.assertEqual(self.call()['lang'],lang)
    def test_requests_paginate_and_cannot_access_other_students(self):
        self.link();self.link('100000000002',102)
        for _ in range(6):self.request()
        other=self.request('100000000002')
        first=self.call('requests');second=self.call('requests',page=2)
        self.assertEqual(len(first['requests']),5);self.assertEqual(first['total'],6);self.assertEqual(len(second['requests']),1)
        self.assertNotIn(other['id'],[r['id'] for r in first['requests']+second['requests']])
        with self.assertRaises(w.Problem):self.call('request',id=other['id'])
        for page in (True,0,-1,'1'):
            with self.assertRaises(w.Problem):self.call('requests',page=page)
    def test_drafts_hidden_selected_files_only_and_no_internal_history(self):
        self.link();row=self.pending()
        draft=self.call('request',id=row['id'])['request']
        self.assertIsNone(draft['answer']);self.assertEqual(draft['files'],[])
        self.assertNotIn('APPROVED ANSWER',json.dumps(draft));self.assertNotIn('PRIVATE BASIS',json.dumps(draft));self.assertNotIn('INTERNAL NOTE',json.dumps(draft))
        import attachments,base64
        for name in ('internal.txt','approved.txt'):
            with self.db:row=attachments.upload(self.db,self.users['admin'],{'id':row['id'],'version':row['version'],'key':__import__('uuid').uuid4().hex,'name':name,'data':base64.b64encode(name.encode()).decode()})['request']
        selected=row['attachments'][1]['id'];internal=row['attachments'][0]['id']
        self.action(row,'approve',result='Ready',telegram_attachment_ids=[selected])
        result=self.call('request',id=row['id'])['request']
        self.assertEqual(result['answer'],'APPROVED ANSWER');self.assertEqual([f['id'] for f in result['files']],[selected])
        self.assertEqual(result['timeline'][3]['done'],True);self.assertEqual(result['timeline'][-1]['done'],False)
        self.assertEqual(self.call('file',id=row['id'],file_id=selected)[0],b'approved.txt')
        with self.assertRaises(w.Problem):self.call('file',id=row['id'],file_id=internal)
    def test_deleted_inactive_and_revoked_links_are_rechecked_on_each_request(self):
        self.link();row=self.request()
        with self.db:self.db.execute("UPDATE students SET status='inactive' WHERE hemis_id=?",(SID,))
        self.assertFalse(self.call()['linked'])
        with self.assertRaises(w.Problem):self.call('request',id=row['id'])
        with self.db:self.db.execute("UPDATE students SET status='active' WHERE hemis_id=?",(SID,));self.db.execute('DELETE FROM telegram_links')
        with self.assertRaises(w.Problem):self.call('requests')
    def test_https_config_and_optional_native_chat_launch_button(self):
        self.assertEqual(mini.config(self.db)['url'],'')
        for url in ('http://example.com/student','https://user:pass@example.com/student','https://example.com/admin','https://example.com/student?secret=foo'):
            with self.assertRaises(w.Problem):mini.save_config(self.db,self.users['admin'],{'url':url})
        with self.assertRaises(w.Problem):mini.save_config(self.db,self.users['manager'],{'url':'https://example.com/student'})
        with self.db:mini.save_config(self.db,self.users['admin'],{'url':'https://example.com/student'})
        self.link();self.send('/start')
        launch=[json.loads(row[0]) for row in self.db.execute('SELECT payload FROM telegram_outbox') if 'web_app' in row[0]]
        self.assertTrue(launch);self.assertEqual(launch[-1]['reply_markup']['inline_keyboard'][0][0]['web_app']['url'],'https://example.com/student')
        self.assertNotIn('web_app',str(bot._keyboard(self.db,'uz')))
        with self.db:mini.save_config(self.db,self.users['admin'],{'url':''})
        self.assertNotIn('web_app',str(bot._keyboard(self.db,'uz')))

for name in list(TelegramBotTests.__dict__):
    if name.startswith('test_') and name not in TelegramMiniTests.__dict__:setattr(TelegramMiniTests,name,None)
del TelegramBotTests
