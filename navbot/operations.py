"""Admin-only, bounded view of the root-owned operational report."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone

KEYS={'navbot.service','navbot-telegram.service','nginx.service','navbot-backup.timer','web','frontend','data_disk','backup_disk','backup','tls','telegram','private_files','offsite','alert_destination','password_policy','security_audit'}


def status():
    path=Path(os.environ.get('NAVBOT_OPERATIONS_STATUS','/var/lib/navbot/operations/status.json'))
    try:
        with path.open('rb') as source:raw=source.read(32769)
        if len(raw)>32768:raise ValueError()
        report=json.loads(raw)
        stamp=report['checked_at']
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(stamp)).total_seconds()
        checks=[{'key':c['key'],'state':c['state'],'detail':str(c['detail'])[:240]} for c in report['checks'] if c['key'] in KEYS and c['state'] in ('ok','warning','error')]
        return {'installed':True,'checked_at':stamp,'stale':not -30<=age<=900,'checks':checks,'notification':report.get('notification') in ('sent','unchanged')}
    except (OSError,ValueError,KeyError,TypeError):
        return {'installed':False,'stale':True,'checks':[]}
