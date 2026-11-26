#!/usr/bin/env python3
"""Install verified backups and monitoring without replacing live app units/state."""
import argparse
import grp
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import importlib.util


def command(*args):
    return subprocess.run(args,check=True,text=True,capture_output=True,timeout=60).stdout.strip()


def install_file(source,target,mode=0o644):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_symlink():raise RuntimeError('Refusing a symbolic-link installation target')
    shutil.copyfile(source,target);target.chmod(mode);os.chown(target,0,0)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--alert-chat',type=int)
    parser.add_argument('--offsite-dir',type=Path)
    parser.add_argument('--tls-host')
    parser.add_argument('--tls-connect-host')
    parser.add_argument('--rotate-login-password',metavar='USER',help='Interactively change the exposed Linux login password after installation')
    args=parser.parse_args()
    if os.geteuid()!=0:parser.error('Run with sudo')
    here=Path(__file__).resolve().parent
    if not Path('/var/lib/navbot/navbot.sqlite3').is_file():parser.error('Live database not found; nothing installed')
    for name in ('navbot.service','navbot-telegram.service'):
        if command('systemctl','show',name,'-p','LoadState','--value')!='loaded':parser.error(name+' is not installed')
    account=command('systemctl','show','navbot.service','-p','User','--value')
    group=command('systemctl','show','navbot.service','-p','Group','--value')
    if not account or account=='root':parser.error('NAVBOT must run as a dedicated non-root account')
    user=pwd.getpwnam(account);gid=grp.getgrnam(group).gr_gid if group else user.pw_gid
    if args.rotate_login_password:
        login=pwd.getpwnam(args.rotate_login_password)
        if login.pw_uid==0 or login.pw_uid==user.pw_uid:parser.error('Choose the human Linux login account, not root or the service account')
    config_path=Path('/etc/navbot/operations.json')
    config=json.loads(config_path.read_text()) if config_path.exists() else {}
    config.setdefault('tls_host','navbot.tsuull.uz');config.setdefault('tls_connect_host','172.20.4.254')
    for key,value in (('alert_chat_id',args.alert_chat),('tls_host',args.tls_host),('tls_connect_host',args.tls_connect_host)):
        if value is not None:config[key]=value
    if args.offsite_dir is not None:config['offsite_dir']=str(args.offsite_dir.resolve())
    mirror=config.get('offsite_dir')
    if mirror and (not re.fullmatch(r'/[A-Za-z0-9_./-]+',mirror) or not Path(mirror).is_mount() or Path(mirror).is_symlink()):
        parser.error('External backup path must be an existing mounted directory without spaces')
    config_path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    config_path.write_text(json.dumps(config,indent=2)+'\n');config_path.chmod(0o600);os.chown(config_path,0,0)
    state=Path('/var/lib/navbot/operations');state.mkdir(exist_ok=True,mode=0o750);state.chmod(0o750);os.chown(state,0,gid)
    spec=importlib.util.spec_from_file_location('security_check',here/'navbot-security-check.py')
    security=importlib.util.module_from_spec(spec);spec.loader.exec_module(security)
    audit=security.audit('/var/lib/navbot/navbot.sqlite3')
    audit_path=state/'security.json';audit_path.write_text(json.dumps(audit));audit_path.chmod(0o640);os.chown(audit_path,0,gid)
    if audit['demo_password_accounts']:print('WARNING: active accounts still use the known demo password. Reset or deactivate them in the admin panel.',flush=True)
    backups=Path('/var/backups/navbot');backups.mkdir(parents=True,exist_ok=True,mode=0o700);backups.chmod(0o700);os.chown(backups,0,0)
    for name in ('navbot-backup.py','navbot-monitor.py'):
        install_file(here/name,Path('/usr/local/sbin')/name,0o700)
    for name in ('navbot-backup.service','navbot-backup.timer','navbot-monitor.service','navbot-monitor.timer'):
        install_file(here/name,Path('/etc/systemd/system')/name)
    if mirror:
        drop=Path('/etc/systemd/system/navbot-backup.service.d/30-offsite.conf');drop.parent.mkdir(exist_ok=True)
        drop.write_text('[Service]\nReadWritePaths='+mirror+'\n');drop.chmod(0o644)
    # Preserve service User, environment, TLS/proxy and all unrelated drop-ins.
    for name in ('navbot.service','navbot-telegram.service'):
        drop=Path('/etc/systemd/system')/(name+'.d')/'30-restart.conf';drop.parent.mkdir(exist_ok=True)
        drop.write_text('[Unit]\nStartLimitIntervalSec=0\n[Service]\nRestart=on-failure\nRestartSec=5\n');drop.chmod(0o644)
    command('systemctl','daemon-reload')
    command('systemd-analyze','verify','navbot-backup.service','navbot-monitor.service','navbot-backup.timer','navbot-monitor.timer')
    command('systemctl','enable','navbot.service','navbot-telegram.service')
    if command('systemctl','show','nginx.service','-p','LoadState','--value')=='loaded':command('systemctl','enable','nginx.service')
    # First backup stops both writers only during copying, then resumes both.
    print('Creating and restoring the first backup in isolation...',flush=True)
    subprocess.run(['systemctl','start','navbot-backup.service'],check=True)
    command('systemctl','enable','--now','navbot-backup.timer','navbot-monitor.timer')
    report=json.loads((backups/'last-verified.json').read_text())
    print('Testing restored login, requests, settings and attachment download...',flush=True)
    subprocess.run([sys.executable,str(here/'navbot-restore-drill.py'),'--archive',str(backups/report['archive']),'--run-as',account],check=True)
    command('systemctl','start','navbot-monitor.service')
    print('Installed. Daily backup: 03:00 Asia/Tashkent; monitoring: every 5 minutes.')
    if not mirror:print('External backup target not configured; local backups do not protect against host loss.')
    print('Status: sudo cat /var/lib/navbot/operations/status.json')
    if args.rotate_login_password:
        print('Enter a NEW Linux login password twice. It is not shown or sent to NAVBOT.',flush=True)
        subprocess.run(['passwd',args.rotate_login_password],check=True)


if __name__=='__main__':main()
