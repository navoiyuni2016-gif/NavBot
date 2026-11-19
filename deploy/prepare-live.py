#!/usr/bin/env python3
"""One-time test-data cleanup. Dry-run by default; never replace the database."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'navbot'))
import auth

CLEAR=('telegram_outbox','telegram_releases','kiosk_print_jobs','attachments','notifications','history','calls','requests','tickets','sessions','telegram_codes','student_delete_previews')
REQUIRED={'users','students','settings','requests','tickets','calls','audit'}

def report(db):
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not REQUIRED<=tables:raise RuntimeError('Bu NAVBOT bazasi emas yoki sxema eskirgan.')
    active="NOT EXISTS(SELECT 1 FROM user_account_states s WHERE s.user_id=u.id)" if 'user_account_states' in tables else '1=1'
    weak=[r['username'] for r in db.execute('SELECT u.* FROM users u WHERE '+active) if auth._verify(auth.DEMO_PASSWORD,r['password_hash'])]
    audio={r['lang']:r['n'] for r in db.execute('SELECT lang,COUNT(*) n FROM audio_clips GROUP BY lang')} if 'audio_clips' in tables else {}
    return {'tozalash':{t:db.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0] for t in CLEAR if t in tables},'saqlanadi':{t:db.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0] for t in ('users','students','settings','audio_clips','branding_assets','telegram_links') if t in tables},'audio_tillar':audio,'sinov_parolida_qolgan_loginlar':weak}

def require_stopped():
    for service in ('navbot','navbot-telegram'):
        result=subprocess.run(['systemctl','show',service,'-p','LoadState','-p','ActiveState'],capture_output=True,text=True)
        values=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
        if service=='navbot-telegram' and values.get('LoadState')=='not-found':continue
        if values.get('LoadState')!='loaded' or values.get('ActiveState') not in ('inactive','failed'):
            raise RuntimeError(service+' to‘xtatilmagan yoki holati aniqlanmadi. Avval xizmatni to‘xtating.')

def clean(db_path):
    # Caller must stop the app and Telegram workers before entering this function.
    db_path=Path(db_path).resolve()
    with closing(sqlite3.connect(db_path)) as db:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE')
        try:
            if db.execute("SELECT 1 FROM audit WHERE action='production_test_cleanup' LIMIT 1").fetchone():
                raise RuntimeError('Bu baza allaqachon real ishga tayyorlangan. Qayta tozalash bloklandi.')
            before=report(db)
            if before['sinov_parolida_qolgan_loginlar']:
                raise RuntimeError('Faol sinov parollari bor. Admin panelida ularni almashtiring yoki hisoblarni faolsizlantiring: '+', '.join(before['sinov_parolida_qolgan_loginlar']))
            if not db.execute("SELECT 1 FROM users u WHERE role='admin' AND NOT EXISTS(SELECT 1 FROM user_account_states s WHERE s.user_id=u.id)").fetchone():
                raise RuntimeError('Faol administrator topilmadi.')
            backup=db_path.with_name(db_path.name+'.before-live-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]+'.bak')
            descriptor=os.open(backup,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(descriptor)
            with closing(sqlite3.connect(db_path)) as source,closing(sqlite3.connect(backup)) as target:
                source.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Zaxira tekshiruvi o‘tmadi.')
                target.row_factory=sqlite3.Row
                if report(target)!=before:raise RuntimeError('Zaxira bazaga mos kelmadi.')
            # Existing kiosk pages may still poll an accepted test receipt after reset.
            db.execute('CREATE TABLE IF NOT EXISTS retired_test_tickets(request_key TEXT PRIMARY KEY)')
            db.execute('INSERT OR IGNORE INTO retired_test_tickets SELECT request_key FROM tickets')
            for table in CLEAR:
                if table in before['tozalash']:db.execute('DELETE FROM "'+table+'"')
            # Preserve device pairing but require a fresh worker heartbeat after restart.
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='kiosk_printer'").fetchone():
                db.execute('UPDATE kiosk_printer SET last_seen=0,ready=0')
            after=report(db)
            if after['saqlanadi']!=before['saqlanadi'] or any(after['tozalash'].values()):raise RuntimeError('Tozalash tekshiruvi o‘tmadi.')
            if db.execute('PRAGMA foreign_key_check').fetchone():raise RuntimeError('Baza bog‘lanishlari tekshiruvi o‘tmadi.')
            db.execute('INSERT INTO audit(actor_id,action,detail,created_at) VALUES(NULL,?,?,?)',('production_test_cleanup',json.dumps({'counts':before['tozalash'],'backup':backup.name}),datetime.now(timezone.utc).isoformat()))
            db.commit()
            return {'zaxira':str(backup),'natija':after}
        except Exception:
            db.rollback();raise

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--all-requests-are-tests',action='store_true')
    args=parser.parse_args()
    if not args.db.is_file():parser.error('Baza topilmadi; yangi baza yaratilmaydi.')
    if args.apply:
        if not args.all_requests_are_tests:parser.error('--all-requests-are-tests tasdig‘i kerak.')
        require_stopped()
        result=clean(args.db)
    else:
        with closing(sqlite3.connect(args.db.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row;result=report(db)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except (RuntimeError,sqlite3.Error,OSError) as error:
        print(str(error),file=sys.stderr);sys.exit(1)
