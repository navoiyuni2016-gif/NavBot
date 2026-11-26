#!/usr/bin/env python3
"""Restore a backup to a disposable directory and test HTTP login/read/download.

Never replaces production state, starts a Telegram worker or sends a message.
The app subprocess runs as a non-root account on an ephemeral loopback port.
"""
import argparse
from contextlib import closing
import hashlib
from http.cookiejar import CookieJar
import importlib.util
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('verified_backup',HERE/'navbot-backup.py')
backup=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup)


def drill(archive,run_as=None):
    if os.geteuid()==0 and not run_as:raise RuntimeError('Root must specify --run-as for the isolated app')
    account=pwd.getpwnam(run_as) if run_as else pwd.getpwuid(os.geteuid())
    if account.pw_uid==0:raise RuntimeError('The isolated app must not run as root')
    original=backup.digest(Path(archive))
    with tempfile.TemporaryDirectory(prefix='navbot-drill-') as folder:
        root=Path(folder);snapshot=root/'input.tar.gz';shutil.copyfile(archive,snapshot)
        counts=backup.verify_backup(snapshot)
        # verify_backup rejected traversal, links and checksum mismatches on this
        # private copy. Extract only that same private copy, never a live archive.
        with tarfile.open(snapshot) as tar:tar.extractall(root/'restore',filter='data')
        code=root/'restore/code/navbot';database=root/'restore/data/navbot.sqlite3'
        sys.path.insert(0,str(HERE.parent/'navbot'))
        import auth
        username='restore_'+secrets.token_hex(6);password='Drill9!'+secrets.token_urlsafe(24)
        with closing(sqlite3.connect(database)) as db,db:
            db.row_factory=sqlite3.Row
            user=auth.create_user(db,{'username':username,'password':password,'full_name':'Isolated recovery check','role':'admin','department':'Registrar','operator':None})
            db.execute('UPDATE users SET must_change_password=0 WHERE id=?',(user['id'],))
            row=db.execute('SELECT a.id,a.body FROM attachments a JOIN requests r ON r.id=a.request_id WHERE r.deleted_at IS NULL LIMIT 1').fetchone()
            attachment=(row['id'],hashlib.sha256(bytes(row['body'])).hexdigest()) if row else None
        if os.geteuid()==0:
            for path in [root,*root.rglob('*')]:os.chown(path,account.pw_uid,account.pw_gid)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        def drop_privileges():
            os.setgroups([]);os.setgid(account.pw_gid);os.setuid(account.pw_uid)
        environment={k:v for k,v in os.environ.items() if not k.startswith('NAVBOT_')}
        environment['NAVBOT_OPERATIONS_STATUS']=str(root/'absent-status.json')
        process=subprocess.Popen([sys.executable,str(code/'app.py'),'--host','127.0.0.1','--port',str(port),'--db',str(database)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=environment,preexec_fn=drop_privileges if os.geteuid()==0 else None)
        base='http://127.0.0.1:'+str(port)
        opener=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
        def get(path):
            with opener.open(base+path,timeout=5) as response:return response.read()
        try:
            for _ in range(100):
                if process.poll() is not None:raise RuntimeError('Restored app did not start')
                try:
                    if get('/login'):break
                except OSError:time.sleep(0.1)
            else:raise RuntimeError('Restored app did not become ready')
            payload=json.dumps({'username':username,'password':password}).encode()
            with opener.open(Request(base+'/api/login',data=payload,headers={'Content-Type':'application/json'}),timeout=5) as response:
                if response.status!=200:raise RuntimeError('Restored login failed')
            if not isinstance(json.loads(get('/api/requests')).get('requests'),list):raise RuntimeError('Restored request listing failed')
            if not json.loads(get('/api/settings')).get('settings'):raise RuntimeError('Restored settings failed')
            if not get('/student'):raise RuntimeError('Restored Mini App page failed')
            if attachment and hashlib.sha256(get('/api/attachment/'+attachment[0])).hexdigest()!=attachment[1]:raise RuntimeError('Restored attachment download mismatch')
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    if original!=backup.digest(Path(archive)):raise RuntimeError('Source archive changed during drill')
    return {'integrity':'ok','login':'ok','requests':'ok','settings':'ok','mini_page':'ok','attachment':'ok' if attachment else 'not_present','counts':counts}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',required=True,type=Path);parser.add_argument('--run-as');args=parser.parse_args()
    os.umask(0o077)
    print(json.dumps(drill(args.archive,args.run_as)))


if __name__=='__main__':main()
