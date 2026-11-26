#!/usr/bin/env python3
"""Read-only deployment audit; no password hashes, tokens or names in output."""
import argparse
from contextlib import closing
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import sys
import os
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'navbot'))
import auth


def audit(database):
    with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        users=db.execute('SELECT u.password_hash,u.must_change_password FROM users u WHERE NOT EXISTS(SELECT 1 FROM user_account_states s WHERE s.user_id=u.id)').fetchall()
        default=sum(auth._verify(auth.DEMO_PASSWORD,row['password_hash']) for row in users)
        pending=sum(bool(row['must_change_password']) for row in users)
        owner=bool(db.execute('SELECT 1 FROM owner_account LIMIT 1').fetchone())
    return {'checked_at':datetime.now(timezone.utc).isoformat(),'demo_password_accounts':default,'pending_password_changes':pending,'owner_mfa_configured':owner}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--db',type=Path,default=Path('/var/lib/navbot/navbot.sqlite3'));parser.add_argument('--refresh',action='store_true');args=parser.parse_args()
    result=audit(args.db)
    if args.refresh:
        target=args.db.parent/'operations/security.json'
        fd,name=tempfile.mkstemp(dir=target.parent,prefix='.security-')
        try:
            with os.fdopen(fd,'w') as out:
                json.dump(result,out);out.flush();os.fsync(out.fileno());os.fchmod(out.fileno(),0o640)
                if os.geteuid()==0:os.fchown(out.fileno(),0,target.parent.stat().st_gid)
            os.replace(name,target)
        finally:
            if os.path.exists(name):os.unlink(name)
    print(json.dumps(result))


if __name__=='__main__':main()
