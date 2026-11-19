"""Public TV update fingerprint and APK distribution contract."""
import hashlib
import urllib.request
from pathlib import Path
from test_workflow import WorkflowAcceptance

class TVApkAcceptance(WorkflowAcceptance):
    def test_public_update_version_matches_deployed_assets(self):
        root=Path(__file__).resolve().parents[1]
        code,data,headers=self.public.request('/api/tv-version')
        self.assertEqual(code,200)
        self.assertEqual(data,{'version':hashlib.sha256((root/'navbot/index.html').read_bytes()+(root/'navbot/i18n.js').read_bytes()).hexdigest()})
        self.assertEqual(headers.get('Cache-Control'),'no-store')
    def test_signed_apk_can_be_downloaded_without_login(self):
        with urllib.request.urlopen(self.public.base+'/downloads/NAVBOT-TV.apk') as response:
            self.assertEqual(response.status,200)
            self.assertEqual(response.headers.get('Content-Type'),'application/vnd.android.package-archive')
            self.assertTrue(response.read().startswith(b'PK'))

for name in list(WorkflowAcceptance.__dict__):
    if name.startswith('test_') and name not in TVApkAcceptance.__dict__:setattr(TVApkAcceptance,name,None)
del WorkflowAcceptance
