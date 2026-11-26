#!/usr/bin/env python3
"""Bounded operational checks; private state, no student data in alerts."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.request import build_opener, ProxyHandler, Request


def atomic_json(path, value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o750)
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.status-')
    try:
        with os.fdopen(fd,'w') as out:
            json.dump(value,out,ensure_ascii=False);out.flush();os.fsync(out.fileno())
            os.fchmod(out.fileno(),0o640)
            if os.geteuid()==0:os.fchown(out.fileno(),0,path.parent.stat().st_gid)
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def service_state(name):
    result=subprocess.run(['systemctl','is-active',name],capture_output=True,text=True,timeout=10)
    return result.returncode==0 and result.stdout.strip()=='active'


def web_check(url):
    # Do not send the loopback probe through an inherited Internet proxy.
    with build_opener(ProxyHandler({})).open(url,timeout=8) as response:
        data=json.loads(response.read(1024*1024))
        return response.status==200 and isinstance(data,list) and bool(data)


def frontend_check(host):
    request=Request('http://127.0.0.1/login',headers={'Host':host})
    with build_opener(ProxyHandler({})).open(request,timeout=8) as response:
        return response.status==200 and b'login-form' in response.read(1024*1024)


def tls_days(host,connect_host):
    # Keep SNI and hostname validation on the public name even via the LAN Kerio.
    with socket.create_connection((connect_host,443),timeout=8) as raw:
        with ssl.create_default_context().wrap_socket(raw,server_hostname=host) as conn:
            return int((ssl.cert_time_to_seconds(conn.getpeercert()['notAfter'])-time.time())//86400)


def collect(config):
    checks=[]
    def add(key,state,detail):checks.append({'key':key,'state':state,'detail':detail})
    for name in ('navbot.service','navbot-telegram.service','nginx.service','navbot-backup.timer'):
        try:ok=service_state(name)
        except (OSError,subprocess.SubprocessError):ok=False
        add(name,'ok' if ok else 'error','active' if ok else 'inactive')
    try:ok=web_check('http://127.0.0.1:8081/api/catalog')
    except (OSError,ValueError):ok=False
    add('web','ok' if ok else 'error','HTTP OK' if ok else 'HTTP check failed')
    try:ok=frontend_check(config['tls_host'])
    except (OSError,ValueError,KeyError):ok=False
    add('frontend','ok' if ok else 'error','Nginx login OK' if ok else 'Nginx login check failed')
    data=Path(config.get('data_dir','/var/lib/navbot'))
    backup_dir=Path(config.get('backup_dir','/var/backups/navbot'))
    for key,path in (('data_disk',data),('backup_disk',backup_dir)):
        try:
            usage=shutil.disk_usage(path);free=usage.free//(1024*1024)
            ok=free>=config.get('min_free_mb',1024) and usage.used/usage.total<0.95
            add(key,'ok' if ok else 'error',str(free)+' MB free')
        except OSError:add(key,'error','Storage unavailable')
    try:archives=sorted(backup_dir.glob('navbot-backup-*.tar.gz'),key=lambda p:p.stat().st_mtime_ns)
    except OSError:archives=[]
    report={}
    try:
        report=json.loads((backup_dir/'last-verified.json').read_text())
        archive=backup_dir/report['archive']
        age=(time.time()-report['verified_at'])/3600
        ok=archive.parent==backup_dir and archive.is_file() and not archive.is_symlink() and archives and archive==archives[-1] and -1<=age<=36
        add('backup','ok' if ok else 'error','Verified backup age: '+str(round(age,1))+' hours')
    except (OSError,ValueError,KeyError,TypeError):add('backup','error','No recent verified backup')
    try:
        days=tls_days(config['tls_host'],config.get('tls_connect_host',config['tls_host']))
        add('tls','ok' if days>30 else 'warning' if days>7 else 'error','Certificate expires in '+str(days)+' days')
    except (OSError,ValueError,KeyError):add('tls','error','TLS trust, connection or certificate check failed')
    try:
        with closing(sqlite3.connect((data/'navbot.sqlite3').resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
            runtime=dict(db.execute("SELECT key,value FROM telegram_runtime WHERE key IN ('last_poll','worker_error')"))
            age=time.time()-datetime.fromisoformat(runtime.get('last_poll','')).timestamp()
            ok=not runtime.get('worker_error') and -5<=age<120
            add('telegram','ok' if ok else 'error','Polling OK' if ok else 'Polling stale or failed')
            try:
                count=db.execute("SELECT COUNT(*) FROM users u WHERE must_change_password=1 AND NOT EXISTS(SELECT 1 FROM user_account_states a WHERE a.user_id=u.id)").fetchone()[0]
                add('password_policy','warning' if count else 'ok','Active accounts awaiting password change: '+str(count))
            except sqlite3.Error:add('password_policy','warning','Password policy state unavailable')
    except (OSError,ValueError,sqlite3.Error):add('telegram','error','Polling state unavailable')
    try:
        private=[data/'navbot.sqlite3',*data.glob('*.integration-secrets'),*data.glob('*.integration-secrets/*')]
        ok=all(not p.is_symlink() and p.stat().st_mode&0o077==0 for p in private)
        add('private_files','ok' if ok else 'error','Private permissions OK' if ok else 'Private file permissions need review')
    except OSError:add('private_files','error','Private file check failed')
    mirror=config.get('offsite_dir')
    if mirror:
        try:
            latest=archives[-1]
            target=Path(mirror)/latest.name
            ok=report.get('offsite_ok') is True and Path(mirror).is_mount() and target.is_file() and target.stat().st_size==latest.stat().st_size
        except (OSError,IndexError):ok=False
        add('offsite','ok' if ok else 'error','Mounted backup copy OK' if ok else 'Mounted backup copy unavailable')
    else:add('offsite','warning','External backup target not configured')
    add('alert_destination','ok' if config.get('alert_chat_id') else 'warning','Telegram administrator configured' if config.get('alert_chat_id') else 'Alerts available locally only')
    try:
        audit=json.loads((data/'operations/security.json').read_text())
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(audit['checked_at'])).total_seconds()
        count=audit['demo_password_accounts']
        add('security_audit','error' if count else 'warning' if age>30*86400 else 'ok','Known demo-password accounts: '+str(count)+('; rerun security audit' if age>30*86400 else ''))
    except (OSError,ValueError,KeyError,TypeError):add('security_audit','warning','Deployment security audit not available')
    return {'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'ok':all(c['state']!='error' for c in checks)}


def notify(config,text):
    # Reuse the protected integration token; never duplicate or print it.
    sys.path.insert(0,str(Path(config.get('code_dir','/opt/navbot'))/'navbot'))
    import integrations
    import telegram_worker
    with closing(sqlite3.connect(str(Path(config.get('data_dir','/var/lib/navbot'))/'navbot.sqlite3'),timeout=5)) as db:
        db.row_factory=sqlite3.Row
        _,token=integrations._check_ready(db,'telegram')
    telegram_worker.API(token).call('sendMessage',{'chat_id':config['alert_chat_id'],'text':text,'link_preview_options':{'is_disabled':True}})


def run(config,state_dir):
    root=Path(state_dir);root.mkdir(parents=True,exist_ok=True,mode=0o750)
    with (root/'.monitor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status=collect(config)
        previous={}
        try:previous=json.loads((root/'alert-state.json').read_text())
        except (OSError,ValueError):pass
        issues=[c for c in status['checks'] if c['state']!='ok']
        signature=hashlib.sha256(json.dumps([(c['key'],c['state']) for c in issues]).encode()).hexdigest()
        changed=signature!=previous.get('signature')
        due=time.time()-previous.get('sent_at',0)>=21600
        # Avoid a healthy-start message, but send recovery after prior issues.
        if config.get('alert_chat_id') and (issues and (changed or due) or not issues and previous.get('had_issues')):
            text='NAVBOT monitoring\n'+('\n'.join(c['key']+': '+c['detail'] for c in issues) if issues else 'All monitored checks recovered.')
            try:
                notify(config,text)
                atomic_json(root/'alert-state.json',{'signature':signature,'sent_at':time.time(),'had_issues':bool(issues)})
                status['notification']='sent'
            except Exception:
                # Tokens can appear in third-party exceptions: log only a code.
                status['notification']='failed'
        else:status['notification']='unchanged'
        atomic_json(root/'status.json',status)
        print(json.dumps(status,ensure_ascii=False))
        return status


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,default=Path('/etc/navbot/operations.json'));parser.add_argument('--state-dir',default='/var/lib/navbot/operations');args=parser.parse_args()
    os.umask(0o077)
    config=json.loads(args.config.read_text())
    run(config,args.state_dir)


if __name__=='__main__':main()
