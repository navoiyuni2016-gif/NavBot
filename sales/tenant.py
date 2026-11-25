#!/usr/bin/env python3
"""Provision isolated NAVBOT tenants. Generate first; installing needs root on Ubuntu."""
import argparse
from contextlib import closing, contextmanager, ExitStack
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import socket
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CODE/'navbot'))
import app
import tenant_instance


def validate(raw):
    allowed={'id','domain','port','university','university_short','office','catalog','footer_text'}
    if not isinstance(raw,dict) or set(raw)-allowed:raise ValueError('Unknown tenant fields')
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,20}',str(raw.get('id',''))):raise ValueError('Tenant ID: 2–21 lowercase letters/digits/hyphens; start with a letter')
    domain=raw.get('domain','')
    if not isinstance(domain,str) or len(domain)>253 or len(domain.split('.'))<2 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',part) for part in domain.split('.')):
        raise ValueError('Use a lowercase DNS domain, without scheme, port or path')
    if type(raw.get('port')) is not int or not 10000<=raw['port']<=60000:raise ValueError('Use a unique loopback port 10000–60000')
    result=dict(raw)
    for key in ('university','university_short','office'):
        if not isinstance(result.get(key),list) or len(result[key])!=3 or any(not isinstance(s,str) or not s.strip() or len(s)>1000 for s in result[key]):raise ValueError(key+': supply Uzbek, Russian and English text')
    result.setdefault('footer_text',[f'© {datetime.now().year} {name}' for name in result['university_short']])
    if not isinstance(result['footer_text'],list) or len(result['footer_text'])!=3 or any(not isinstance(s,str) or not s or len(s)>1000 for s in result['footer_text']):raise ValueError('footer_text: three translations required')
    if 'catalog' in result and (not isinstance(result['catalog'],list) or len(result['catalog'])!=5):raise ValueError('catalog must have 5 sections, each with 5 services in three languages')
    # Use application validation too, before any installation side effects.
    import sqlite3
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    try:
        db.executescript('CREATE TABLE settings(id INTEGER PRIMARY KEY,value TEXT);CREATE TABLE audit(id INTEGER PRIMARY KEY,actor_id INTEGER,action TEXT,detail TEXT,created_at TEXT);')
        app.save_settings(db,{'id':None,'role':'admin'},{'settings':{k:v for k,v in result.items() if k not in ('id','domain','port')}})
    finally:db.close()
    return result


def read_spec(path):return validate(json.loads(Path(path).read_text(encoding='utf-8')))


def paths(spec):
    ident=spec['id']
    return {'user':'nb-'+ident,'service':'navbot-'+ident,'data':f'/var/lib/navbot-tenants/{ident}',
            'profile':f'/etc/navbot-tenants/{ident}.json','backup':f'/var/backups/navbot-tenants/{ident}'}


def safe_code_root(code):
    code=Path(code).resolve()
    if not re.fullmatch(r'/[a-zA-Z0-9_./-]+',str(code)) or not (code/'navbot/app.py').is_file():raise ValueError('Code root must be an absolute application path without spaces')
    return code


def render(raw,code=CODE):
    s=validate(raw);code=safe_code_root(code);p=paths(s);name=p['service'];port=s['port'];domain=s['domain'];user=p['user'];data=p['data'];zone=s['id'].replace('-','_')
    base=f'''[Service]
User={user}
Group={user}
WorkingDirectory={code}
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
CapabilityBoundingSet=
ReadWritePaths={data}
InaccessiblePaths=-/var/lib/navbot
'''
    web=f'''[Unit]
Description=NAVBOT university tenant {s['id']}
After=network.target
{base}ExecStart=/usr/bin/python3 {code}/navbot/app.py --host 127.0.0.1 --port {port} --db {data}/navbot.sqlite3 --tenant {s['id']}

[Install]
WantedBy=multi-user.target
'''
    telegram=f'''[Unit]
Description=NAVBOT Telegram tenant {s['id']}
After=network-online.target {name}.service
Wants=network-online.target
{base}ExecStart=/usr/bin/python3 {code}/navbot/telegram_worker.py --db {data}/navbot.sqlite3
TimeoutStopSec=35

[Install]
WantedBy=multi-user.target
'''
    bootstrap=f'''server {{
    listen 80;
    server_name {domain};
    location ^~ /.well-known/acme-challenge/ {{ root /var/www/navbot-acme; }}
    location / {{ return 308 https://{domain}$request_uri; }}
}}
'''
    nginx=f'''limit_req_zone $binary_remote_addr zone=nb_{zone}_login:1m rate=10r/m;
limit_conn_zone $binary_remote_addr zone=nb_{zone}_connections:1m;
server {{
    listen 443 ssl;
    server_name {domain};
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    server_tokens off;
    client_max_body_size 16m;
    client_header_timeout 15s;
    client_body_timeout 30s;
    keepalive_timeout 15s;
    limit_conn nb_{zone}_connections 32;
    limit_conn_status 429;
    limit_req_status 429;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 90s;
    location ~ ^/api/(owner/)?login$ {{
        limit_req zone=nb_{zone}_login burst=5 nodelay;
        proxy_pass http://127.0.0.1:{port};
    }}
    location / {{ proxy_pass http://127.0.0.1:{port}; }}
}}
'''
    backup=f'''[Unit]
Description=Verified backup for NAVBOT tenant {s['id']}
After={name}.service

[Service]
Type=oneshot
User=root
UMask=0077
ExecStart=/usr/bin/python3 {code}/sales/tenant.py backup {s['id']}
'''
    timer=f'''[Unit]
Description=Daily backup for NAVBOT tenant {s['id']}

[Timer]
OnCalendar=*-*-* 02:30:00
RandomizedDelaySec=1h
Persistent=true
Unit={name}-backup.service

[Install]
WantedBy=timers.target
'''
    command=f'sudo -u {user} /usr/bin/python3 {code}/navbot/app.py --db {data}/navbot.sqlite3'
    instructions=f'''TENANT: {s['id']}\nHTTPS: https://{domain}\nBACKEND: 127.0.0.1:{port}\nUSER: {user}\nDATABASE: {data}/navbot.sqlite3\n
After installing, create customer admin interactively:\n{command} --init-admin\n
Create owner separately (never copy another tenant's owner secret):\n{command} --init-owner\nOwner login: https://{domain}/owner\nOwner recovery: {command} --reset-owner\n
Start only this tenant:\nsudo systemctl enable --now {name}.service {name}-backup.timer\nCheck: curl -H 'Host: {domain}' http://127.0.0.1:{port}/api/catalog\nOptional Telegram after configuring its own bot:\nsudo systemctl enable --now {name}-telegram.service\n
Backup: sudo python3 {code}/sales/tenant.py backup {s['id']}\nVerify a backup: sudo python3 {code}/deploy/navbot-backup.py --verify ARCHIVE\nNever restore A's database over B. Stop only this tenant's web/Telegram before restore.\n'''
    def launcher(route):
        printing='--kiosk-printing' if route=='kiosk' else ''
        return rf'''@echo off
setlocal
set "chrome=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%chrome%" set "chrome=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%chrome%" set "chrome=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not exist "%chrome%" (
  echo Install Google Chrome first.
  pause
  exit /b 1
)
start "NAVBOT {s['id']}" "%chrome%" --user-data-dir="%LOCALAPPDATA%\NAVBOT\{s['id']}\{route}" --no-first-run --kiosk {printing} "https://{domain}/{route}"
endlocal
'''
    return {'KIOSK-START.bat':launcher('kiosk'),'TV-START.bat':launcher('tv'),'tenant.json':json.dumps(s,ensure_ascii=False,indent=2)+'\n',f'{name}.service':web,f'{name}-telegram.service':telegram,f'{name}-backup.service':backup,f'{name}-backup.timer':timer,'nginx-acme.conf':bootstrap,'nginx.conf':nginx,'ACCESS.txt':instructions}


def generate(raw,output,code=CODE):
    import fcntl
    validate(raw);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with (output/'.registry.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _generate(raw,output,code)


def _generate(raw,output,code=CODE):
    s=validate(raw);output=Path(output)
    # A plan directory is a registry: refuse duplicate domains, ports or IDs.
    for existing in output.glob('*/tenant.json'):
        other=read_spec(existing)
        if other['id']==s['id'] or other['domain']==s['domain'] or other['port']==s['port']:raise ValueError('Tenant ID, domain or port already used in this plan registry')
    destination=output/s['id'];destination.mkdir(parents=True,exist_ok=False)
    for name,body in render(s,code).items():(destination/name).write_text(body,encoding='utf-8')
    return destination


def initialize_database(raw,database):
    s=validate(raw);database=Path(database)
    # Never import or clear an existing customer database.
    if database.exists() or database.is_symlink():raise ValueError('Target database already exists; initialization refused')
    database.parent.mkdir(parents=True,exist_ok=True)
    previous_mask=os.umask(0o077)
    lock=database.with_name(database.name+'.provision.lock')
    lock_fd=None
    previous=app.DATABASE;app.DATABASE=database
    try:
        # One initializer per target; do not create a fake empty 'old database'.
        lock_fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        if database.exists() or database.is_symlink():raise ValueError('Target database appeared during initialization')
        app.initialize(False)
        with closing(app.connection()) as db,db:
            app.save_settings(db,{'id':None,'role':'admin'},{'settings':{k:v for k,v in s.items() if k not in ('id','domain','port')}})
            tenant_instance.bind(db,s['id'],s['domain'],s['port'])
    finally:
        app.DATABASE=previous
        if lock_fd is not None:
            os.close(lock_fd);lock.unlink()
        os.umask(previous_mask)


def run(args):subprocess.run(list(map(str,args)),check=True)


def root_only():
    if os.geteuid()!=0:raise ValueError('This action requires sudo on the target Ubuntu server')


def write_new(path,body):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as target:target.write(body)
    path.chmod(0o644)


def bootstrap(raw):
    root_only();s=validate(raw);name=paths(s)['service']+'-acme.conf';target=Path('/etc/nginx/sites-available')/name;link=Path('/etc/nginx/sites-enabled')/name
    if target.exists() or link.exists() or link.is_symlink():raise ValueError('ACME site already exists; inspect it instead of overwriting')
    Path('/var/www/navbot-acme').mkdir(parents=True,exist_ok=True,mode=0o755)
    write_new(target,render(s)['nginx-acme.conf']);link.symlink_to(target)
    try:run(['nginx','-t'])
    except Exception:
        link.unlink()  # Roll back only the link created by this invocation; no live reload occurred.
        raise
    run(['systemctl','reload','nginx'])
    print('ACME ready. Obtain certificate:')
    print(f"sudo certbot certonly --webroot -w /var/www/navbot-acme -d {s['domain']}")


def install(raw):
    root_only()
    import fcntl
    with Path('/run/lock/navbot-tenants.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _install(raw)


def _install(raw):
    root_only();s=validate(raw);p=paths(s);code=safe_code_root(CODE)
    # Root backup services execute this release: require the release to be root owned/read-only.
    for target in (code,*code.parents,*code.rglob('*')):
        if target.is_symlink():raise ValueError('Release must not contain symlinks')
        stat=target.stat()
        if stat.st_uid!=0 or stat.st_mode&0o022:raise ValueError('Release path and all release files must be root-owned and not group/world-writable')
    for directory in ('/var/lib/navbot-tenants','/etc/navbot-tenants','/var/backups/navbot-tenants'):
        path=Path(directory)
        if path.is_symlink() or (path.exists() and (path.stat().st_uid!=0 or path.stat().st_mode&0o022)):
            raise ValueError('Tenant registry/data parent must be root-owned and not writable by other users')
    for cert in ('fullchain.pem','privkey.pem'):
        if not (Path('/etc/letsencrypt/live')/s['domain']/cert).is_file():raise ValueError('Issue this domain HTTPS certificate before install')
    for existing in Path('/etc/navbot-tenants').glob('*.json'):
        other=read_spec(existing)
        if any(other[key]==s[key] for key in ('id','domain','port')):raise ValueError('Registered tenant ID/domain/port conflict')
    try:pwd.getpwnam(p['user'])
    except KeyError:pass
    else:raise ValueError('Service user already exists; installation refused')
    targets=[Path(p['data']),Path(p['profile']),Path('/etc/nginx/sites-available')/(p['service']+'.conf'),Path('/etc/nginx/sites-enabled')/(p['service']+'.conf')]
    targets.extend(Path('/etc/systemd/system')/name for name in render(s,code) if name.endswith(('.service','.timer')))
    for target in targets:
        if target.exists() or target.is_symlink():raise ValueError('Installation target already exists: '+str(target))
    with socket.socket() as listener:listener.bind(('127.0.0.1',s['port']))
    run(['useradd','--system','--user-group','--no-create-home','--home-dir',p['data'],'--shell','/usr/sbin/nologin',p['user']])
    parent=Path(p['data']).parent;parent.mkdir(parents=True,exist_ok=True,mode=0o711)
    Path(p['data']).mkdir(mode=0o700);account=pwd.getpwnam(p['user']);os.chown(p['data'],account.pw_uid,account.pw_gid)
    files=render(s,code);write_new(p['profile'],files['tenant.json'])
    run(['runuser','-u',p['user'],'--','/usr/bin/python3',code/'sales/tenant.py','init-db',p['profile'],'--db',p['data']+'/navbot.sqlite3'])
    units=[]
    for name,body in files.items():
        if name.endswith(('.service','.timer')):
            target=Path('/etc/systemd/system')/name;write_new(target,body);units.append(target)
    target=Path('/etc/nginx/sites-available')/(p['service']+'.conf');link=Path('/etc/nginx/sites-enabled')/target.name
    if link.exists() or link.is_symlink():raise ValueError('Nginx link already exists')
    write_new(target,files['nginx.conf']);link.symlink_to(target)
    try:
        run(['systemd-analyze','verify',*units]);run(['nginx','-t'])
    except Exception:
        link.unlink();raise
    run(['systemctl','daemon-reload']);run(['systemctl','reload','nginx'])
    # Deliberately no automatic start: provision owner/admin interactively first.
    print(files['ACCESS.txt'])


def backup(ident):
    root_only()
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,20}',ident):raise ValueError('Invalid tenant ID')
    s=read_spec(Path('/etc/navbot-tenants')/(ident+'.json'));p=paths(s)
    spec=importlib.util.spec_from_file_location('tenant_backup',CODE/'deploy/navbot-backup.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    @contextmanager
    def pause():
        with ExitStack() as stack:
            stack.enter_context(module.stopped_service(p['service']+'-telegram.service'))
            stack.enter_context(module.stopped_service(p['service']+'.service'))
            yield
    configs=[p['profile'],str(Path('/etc/nginx/sites-available')/(p['service']+'.conf'))]
    configs.extend(str(Path('/etc/systemd/system')/(p['service']+suffix)) for suffix in ('.service','-telegram.service','-backup.service','-backup.timer'))
    acme=Path('/etc/nginx/sites-available')/(p['service']+'-acme.conf')
    if acme.is_file():configs.append(str(acme))
    destination,counts=module.create_backup(p['data'],CODE,p['backup'],pause,configs)
    print('Verified tenant backup:',destination);print(json.dumps(counts))


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    create=commands.add_parser('generate');create.add_argument('spec',type=Path);create.add_argument('--output',type=Path,required=True);create.add_argument('--code-root',type=Path,default=CODE)
    for name in ('bootstrap','install'):commands.add_parser(name).add_argument('spec',type=Path)
    init=commands.add_parser('init-db');init.add_argument('spec',type=Path);init.add_argument('--db',type=Path,required=True)
    commands.add_parser('backup').add_argument('id')
    args=parser.parse_args()
    try:
        if args.command=='backup':return backup(args.id)
        spec=read_spec(args.spec)
        if args.command=='generate':print(generate(spec,args.output,args.code_root))
        elif args.command=='init-db':initialize_database(spec,args.db);print('Fresh tenant database initialized; no accounts or student data seeded.')
        elif args.command=='bootstrap':bootstrap(spec)
        else:install(spec)
    except (ValueError,OSError,app.w.Problem,subprocess.CalledProcessError) as error:parser.exit(1,str(error)+'\n')


if __name__=='__main__':main()
