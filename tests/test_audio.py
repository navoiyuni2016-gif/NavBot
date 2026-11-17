"""Recorded-call storage and HTTP boundaries using valid, generated WAV clips."""
import base64
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_workflow import WorkflowAcceptance
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'navbot'))
import workflow
ADMIN = {'id': 1, 'role': 'admin', 'username': 'admin'}
MANAGER = {'id': 2, 'role': 'manager', 'username': 'manager'}


def short_wav():
    stream = BytesIO()
    with wave.open(stream, 'wb') as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(16000)
        sound.writeframes(b'\0\0' * 1600)
    return stream.getvalue()


def clip(slot='call:25:3', lang='uz'):
    return {'lang': lang, 'slot': slot, 'label': 'Sinov audio', 'mime': 'audio/wav',
            'data': base64.b64encode(short_wav()).decode('ascii')}


class AudioStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('navbot_audio_store', ROOT / 'navbot' / 'audio_store.py')
        cls.audio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.audio)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='navbot-audio-test-')
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / 'audio.sqlite3'
        self.db = sqlite3.connect(self.database)
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        workflow.initialize(self.db)
        self.audio.initialize(self.db)

    def upload(self, slot='call:25:3', lang='uz'):
        self.audio.upload(self.db, ADMIN, clip(slot, lang))
        return next(c for c in self.audio.metadata(self.db)['clips'] if c['slot'] == slot and c['lang'] == lang)

    def test_valid_wav_roundtrip_and_persistence(self):
        item = self.upload()
        self.assertEqual(item['mime'], 'audio/wav')
        self.assertEqual(item['size'], len(short_wav()))
        self.assertIn('/media/audio/', item['url'])
        data, mime = self.audio.read(self.db, item['id'])
        self.assertEqual(data, short_wav())
        self.assertEqual(mime, 'audio/wav')
        self.db.commit()
        with sqlite3.connect(self.database) as reopened:
            reopened.row_factory = sqlite3.Row
            metadata = self.audio.metadata(reopened)
            self.assertTrue(any(c['id'] == item['id'] for c in metadata['clips']))
            self.assertEqual(self.audio.read(reopened, item['id'])[0], short_wav())
        # Public metadata must not contain the binary/base64 upload payload.
        self.assertNotIn(base64.b64encode(short_wav()).decode(), json.dumps(metadata))

    def test_recorded_full_call_precedes_segments_and_incomplete_falls_back_whole(self):
        initial = self.audio.plan(self.db, 'uz', 25, 3)
        self.assertEqual(initial['mode'], 'speech')
        self.audio.set_mode(self.db, ADMIN, {'lang': 'uz', 'mode': 'recorded'})
        incomplete = self.audio.plan(self.db, 'uz', 25, 3)
        self.assertEqual(incomplete['mode'], 'incomplete')
        self.assertEqual(incomplete['urls'], [])
        self.assertTrue(incomplete['missing'])
        items = [self.upload(slot) for slot in ['prefix', 'number:25', 'between', 'operator:3', 'suffix']]
        plan = self.audio.plan(self.db, 'uz', 25, 3)
        self.assertEqual(plan['mode'], 'recorded')
        self.assertEqual(plan['urls'], [item['url'] for item in items])
        full = self.upload('call:25:3')
        self.assertEqual(self.audio.plan(self.db, 'uz', 25, 3)['urls'], [full['url']])
        # A different number must not reuse a matching operator/full call accidentally.
        self.assertEqual(self.audio.plan(self.db, 'uz', 26, 3)['mode'], 'incomplete')
        self.assertEqual(self.audio.plan(self.db, 'uz', 26, 3)['urls'], [])
        self.assertEqual(self.audio.plan(self.db, 'ru', 25, 3)['mode'], 'speech')

    def test_numbered_500_clips_and_prefix_specific_plans(self):
        for slot in ['intro','letter:A','operator:1']:
            self.upload(slot)
        for number in range(1,501):
            result=self.audio.upload(self.db,ADMIN,dict(clip('number:'+str(number)),label='s'+str(number)+'.wav',compact=True))
            self.assertTrue(result['saved'])
            self.assertNotIn('clips',result)
        self.audio.set_mode(self.db,ADMIN,{'lang':'uz','mode':'recorded','layout':'numbered'})
        manifest=self.audio.metadata(self.db)
        self.assertEqual(len(manifest['clips']),503)
        by_url={c['url']:c['slot'] for c in manifest['clips']}
        plan=self.audio.plan(self.db,'uz',500,1,'A')
        self.assertEqual([by_url[u] for u in plan['urls']],['intro','letter:A','number:500','operator:1'])
        self.assertEqual(self.audio.plan(self.db,'uz',500,1,'B')['mode'],'incomplete')
        self.upload('letter:B')
        plan=self.audio.plan(self.db,'uz',500,1,'B')
        self.assertEqual(plan['mode'],'recorded')
        self.assertEqual(self.audio.plan(self.db,'ru',500,1,'B')['mode'],'speech')

    def test_provided_pack_is_exact_four_file_sequence(self):
        from pathlib import Path
        self.audio.install_pack(self.db,ADMIN)
        manifest=self.audio.metadata(self.db)
        by_url={c['url']:c for c in manifest['clips']}
        plan=self.audio.plan(self.db,'uz',1,1,'A')
        self.assertEqual([by_url[u]['label'] for u in plan['urls']],['default.wav','sA.wav','s1.wav','p1.wav'])
        for url in plan['urls']:
            item=by_url[url]
            self.assertEqual(self.audio.read(self.db,item['id'])[0],(ROOT/'navbot'/'voice'/'uz'/item['label']).read_bytes())

    def test_language_modes_and_delete(self):
        item = self.upload(lang='ru')
        self.audio.set_mode(self.db, ADMIN, {'lang': 'ru', 'mode': 'recorded'})
        self.assertEqual(self.audio.plan(self.db, 'ru', 25, 3)['urls'], [item['url']])
        self.audio.remove(self.db, ADMIN, {'id': item['id']})
        self.assertFalse(any(c['id'] == item['id'] for c in self.audio.metadata(self.db)['clips']))
        self.assertEqual(self.audio.plan(self.db, 'ru', 25, 3)['mode'], 'incomplete')
        with self.assertRaises(Exception) as failure:
            self.audio.read(self.db, item['id'])
        self.assertEqual(getattr(failure.exception, 'status', None), 404)

    def test_role_validation_and_bad_uploads_do_not_change_storage(self):
        good = self.upload()
        original = self.audio.metadata(self.db)
        for operation, data in [(self.audio.upload, clip()), (self.audio.remove, {'id': good['id']}),
                                (self.audio.set_mode, {'lang': 'uz', 'mode': 'recorded'})]:
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(Exception) as failure:
                    operation(self.db, MANAGER, data)
                self.assertEqual(getattr(failure.exception, 'status', None), 403)
        bad_values = [dict(clip(), mime='audio/mpeg', data=base64.b64encode(bytes.fromhex('fffb9064')).decode()), dict(clip(), lang='xx'), dict(clip(), slot='../unsafe'),
                      dict(clip(), mime='text/html'), dict(clip(), data='not base64!'),
                      dict(clip(), data=base64.b64encode(b'<html>bad</html>').decode()),
                      dict(clip(), slot='operator:0'), dict(clip(), slot='operator:31'),
                      dict(clip(), mime='audio/mpeg', data=base64.b64encode(b'ID3'+b'\0'*20).decode()),
                      dict(clip(), mime='audio/mpeg', data=base64.b64encode(b'<html>bad</html>').decode())]
        for bad in bad_values:
            with self.subTest(bad={k: v for k, v in bad.items() if k != 'data'}):
                with self.assertRaises(Exception):
                    self.audio.upload(self.db, ADMIN, bad)
                self.assertEqual(self.audio.metadata(self.db), original)
        with self.assertRaises(Exception):
            self.audio.upload(self.db, ADMIN, dict(clip(), data=base64.b64encode(b'x' * (5 * 1024 * 1024 + 1)).decode()))
        self.assertEqual(self.audio.metadata(self.db), original)
        self.assertEqual(self.audio.read(self.db, good['id'])[0], short_wav())


class AudioEndpoint(WorkflowAcceptance):
    def test_upload_plan_media_and_admin_boundaries(self):
        admin = self.client('admin')
        payload = clip()
        self.assertEqual(self.public.request('/api/admin/audio/upload', payload)[0], 401)
        self.assertEqual(self.client('manager').request('/api/admin/audio/upload', payload)[0], 403)
        self.ok(admin, '/api/admin/audio/upload', payload)
        metadata = self.ok(self.public, '/api/audio')
        item = next(c for c in metadata['clips'] if c['slot'] == 'call:25:3' and c['lang'] == 'uz')
        self.ok(admin, '/api/admin/audio/settings', {'lang': 'uz', 'mode': 'recorded'})
        plan = self.ok(self.public, '/api/audio/plan?lang=uz&ticket=25&operator=3')
        self.assertEqual(plan['mode'], 'recorded')
        self.assertEqual(plan['urls'], [item['url']])
        response = self.public.opener.open(self.base + item['url'], timeout=8)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers.get_content_type(), 'audio/wav')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.read(), short_wav())
        response.close()
        self.assertEqual(self.client('manager').request('/api/admin/audio/delete', {'id': item['id']})[0], 403)
        self.assertEqual(self.public.request('/api/audio/plan?lang=xx&ticket=25&operator=3')[0], 400)
        self.ok(admin, '/api/admin/audio/delete', {'id': item['id']})
        self.assertEqual(self.ok(self.public, '/api/audio/plan?lang=uz&ticket=25&operator=3')['mode'], 'incomplete')


for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in AudioEndpoint.__dict__:
        setattr(AudioEndpoint, _name, None)
del WorkflowAcceptance

if __name__ == '__main__':
    unittest.main(verbosity=2)
