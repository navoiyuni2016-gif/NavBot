import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('navbot_backup',Path(__file__).resolve().parents[1]/'deploy/navbot-backup.py')
backup=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup)

class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);self.data=root/'data';self.data.mkdir();self.code=root/'app';(self.code/'navbot').mkdir(parents=True)
        (self.code/'navbot/app.py').write_text('print("test application")')
        (self.code/'manifest.json').write_text('{"app":"test"}')
        (self.code/'.git').mkdir();(self.code/'.git/config').write_text('must not be archived')
        secrets=self.data/'navbot.sqlite3.integration-secrets';secrets.mkdir();(secrets/'test-key').write_text('test-secret-only')
        with sqlite3.connect(self.data/'navbot.sqlite3') as db:
            db.execute('CREATE TABLE students(id INTEGER PRIMARY KEY,name TEXT)')
            db.execute('INSERT INTO students VALUES(1,?)',('Preserve exact text',))
        self.out=root/'backups';self.events=[]
    @contextlib.contextmanager
    def pause(self):
        self.events.append('stop')
        try:yield
        finally:self.events.append('restart')
    def test_roundtrip_preserves_database_code_and_private_sidecar(self):
        archive,counts=backup.create_backup(self.data,self.code,self.out,self.pause)
        self.assertEqual(self.events,['stop','restart']);self.assertEqual(counts,{'students':1})
        self.assertEqual(backup.verify_backup(archive),counts)
        self.assertEqual(archive.stat().st_mode&0o777,0o600);self.assertEqual(self.out.stat().st_mode&0o777,0o700)
        with tarfile.open(archive) as tar:
            self.assertEqual(tar.extractfile('data/navbot.sqlite3.integration-secrets/test-key').read(),b'test-secret-only')
            self.assertNotIn('code/.git',tar.getnames())
    def test_copy_failure_resumes_service_and_publishes_nothing(self):
        with patch.object(backup,'copy_checked',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):backup.create_backup(self.data,self.code,self.out,self.pause)
        self.assertEqual(self.events,['stop','restart']);self.assertEqual(list(self.out.glob('*.tar.gz')),[])
    def test_tampered_archive_is_rejected(self):
        archive,_=backup.create_backup(self.data,self.code,self.out,self.pause)
        bad=self.out/'bad.tar.gz'
        with tarfile.open(archive) as src,tarfile.open(bad,'w:gz') as dst:
            for member in src:
                if member.name=='code/navbot/app.py':
                    raw=b'altered';member.size=len(raw);dst.addfile(member,io.BytesIO(raw))
                else:dst.addfile(member,src.extractfile(member) if member.isfile() else None)
        with self.assertRaisesRegex(RuntimeError,'checksums'):backup.verify_backup(bad)
    def test_archive_link_is_rejected(self):
        bad=self.out.parent/'link.tar.gz'
        with tarfile.open(bad,'w:gz') as tar:
            item=tarfile.TarInfo('data/link');item.type=tarfile.SYMTYPE;item.linkname='/etc/shadow';tar.addfile(item)
        with self.assertRaisesRegex(RuntimeError,'Unsafe'):backup.verify_backup(bad)
    def test_live_service_restarts_on_exception(self):
        with patch.object(backup.subprocess,'run') as run:
            run.return_value=subprocess.CompletedProcess([],0,'active\n','')
            with self.assertRaisesRegex(RuntimeError,'snapshot failure'):
                with backup.stopped_service('navbot.service'):raise RuntimeError('snapshot failure')
            calls=[call.args[0] for call in run.call_args_list]
            self.assertIn(['systemctl','stop','navbot.service'],calls)
            self.assertIn(['systemctl','start','navbot.service'],calls)

    def test_retention_only_removes_old_automatic_archives(self):
        self.out.mkdir()
        for stamp in ('20260101','20260102','20260103'):
            (self.out/f'navbot-backup-{stamp}T000000Z-1234abcd.tar.gz').write_bytes(b'test')
        other=self.out/'manual-backup.tar.gz';other.write_bytes(b'keep')
        backup.prune_backups(self.out,keep=2)
        self.assertFalse((self.out/'navbot-backup-20260101T000000Z-1234abcd.tar.gz').exists())
        self.assertEqual(len(list(self.out.glob('navbot-backup-*'))),2)
        self.assertTrue(other.is_file())

    def test_live_dropin_configuration_is_archived_and_verified(self):
        config=Path(self.tmp.name)/'service.d'/'20-hardening.conf'
        config.parent.mkdir();config.write_text('[Service]\nPrivateDevices=true\n')
        archive,_=backup.create_backup(self.data,self.code,self.out,self.pause,(config,))
        with tarfile.open(archive) as tar:
            saved='config/'+config.relative_to('/').as_posix()
            self.assertEqual(tar.extractfile(saved).read(),config.read_bytes())
        self.assertEqual(backup.verify_backup(archive),{'students':1})
