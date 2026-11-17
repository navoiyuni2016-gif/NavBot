"""Exercise interrupted first-run recovery through the actual CLI."""
import pathlib
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

APP=pathlib.Path(__file__).resolve().parents[1]/'navbot/app.py'

class BootstrapTests(unittest.TestCase):
    def test_failed_confirmation_can_be_retried_in_same_run(self):
        with tempfile.TemporaryDirectory() as folder:
            db=pathlib.Path(folder)/'db.sqlite3'
            result=subprocess.run([sys.executable,str(APP),'--db',str(db),'--init-admin'],input='admin\nBootstrap-Only-123!\nWrong-Only-123!\nadmin\nBootstrap-Only-123!\nBootstrap-Only-123!\n',text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('Parollar mos emas',result.stdout)
            self.assertNotIn('Bootstrap-Only-123!',result.stdout+result.stderr)
            with sqlite3.connect(db) as c:self.assertEqual(c.execute('SELECT count(*) FROM users').fetchone()[0],1)
    def test_restart_recovers_empty_database_and_keeps_existing_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            db=pathlib.Path(folder)/'db.sqlite3'
            failed=subprocess.run([sys.executable,str(APP),'--db',str(db),'--init-admin'],input='admin\nBootstrap-Only-123!\nWrong-Only-123!\n',text=True,capture_output=True,timeout=10)
            self.assertNotEqual(failed.returncode,0)
            self.assertTrue(db.is_file())
            for attempt in range(2):
                with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
                process=subprocess.Popen([sys.executable,str(APP),'--db',str(db),'--port',str(port),'--ensure-admin'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    if attempt==0:
                        process.stdin.write('admin\nBootstrap-Only-123!\nBootstrap-Only-123!\n');process.stdin.flush()
                    else:process.stdin.close()
                    ready=False
                    for _ in range(100):
                        try:
                            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/me',timeout=.2) as response:
                                ready=response.status==200
                                if ready:break
                        except OSError:time.sleep(.05)
                    self.assertTrue(ready,'Server did not start')
                    with sqlite3.connect(db) as c:
                        current=c.execute('SELECT username,password_hash FROM users').fetchall()
                        if attempt==0:saved=current
                        else:self.assertEqual(current,saved)
                finally:
                    process.terminate();process.wait(timeout=5)
                    if not process.stdin.closed:process.stdin.close()
                    process.stdout.close();process.stderr.close()
