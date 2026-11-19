"""Exercise HTTPS request serialization without accessing Telegram or any network."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'navbot'))
from telegram_worker import API,TelegramError,NoRedirect

TOKEN='123456789:'+'X'*35
class Response:
    def __init__(self,data,status=200):self.data=json.dumps(data).encode();self.status=status
    def read(self,n):return self.data[:n]
    def __enter__(self):return self
    def __exit__(self,*args):pass

class TelegramTransportTests(unittest.TestCase):
    def test_fixed_verified_https_json_and_literal_user_text(self):
        api=API(TOKEN)
        with patch.object(api._opener,'open',return_value=Response({'ok':True,'result':{'message_id':8}})) as opened:
            self.assertEqual(api.call('sendMessage',{'chat_id':42,'text':'<b>Student</b>'})['message_id'],8)
        request=opened.call_args.args[0]
        self.assertEqual(request.full_url,'https://api.telegram.org/bot'+TOKEN+'/sendMessage')
        self.assertEqual(json.loads(request.data)['text'],'<b>Student</b>')
        self.assertNotIn('parse_mode',json.loads(request.data))
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'redirect',{},'https://untrusted.example'))
        with self.assertRaises(TelegramError):api.call('arbitraryMethod')
    def test_token_never_appears_in_sanitized_network_errors(self):
        api=API(TOKEN)
        with patch.object(api._opener,'open',side_effect=URLError('error at '+api._base)):
            with self.assertRaises(TelegramError) as caught:api.call('sendMessage',{'chat_id':42,'text':'answer'})
        self.assertEqual(str(caught.exception),'network');self.assertTrue(caught.exception.uncertain)
        self.assertNotIn(TOKEN,str(caught.exception))
    def test_retry_after_and_invalid_success_are_not_reported_sent(self):
        api=API(TOKEN)
        for body,code,uncertain,delay in [({'ok':False,'error_code':429,'parameters':{'retry_after':17}},429,False,17),({'ok':True,'result':None},'invalid_response',True,0)]:
            with patch.object(api._opener,'open',return_value=Response(body)):
                with self.assertRaises(TelegramError) as caught:api.call('sendMessage',{})
            self.assertEqual(caught.exception.code,str(code));self.assertEqual(caught.exception.uncertain,uncertain);self.assertEqual(caught.exception.retry_after,delay)
    def test_document_body_uses_bytes_and_safe_filename(self):
        api=API(TOKEN)
        with patch.object(api._opener,'open',return_value=Response({'ok':True,'result':{'message_id':9}})) as opened:
            api.call('sendDocument',{'chat_id':42,'caption':'Talaba javobi.pdf'},file={'name':'Talaba javobi.pdf','mime':'application/pdf','body':b'%PDF-test'})
        body=opened.call_args.args[0].data
        self.assertIn(b'%PDF-test',body);self.assertIn(b'filename="NAVBOT.pdf"',body);self.assertIn(b'Talaba javobi.pdf',body)
