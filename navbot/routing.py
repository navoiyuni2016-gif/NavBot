"""Section routing and immutable, independently numbered queue codes."""
from datetime import datetime, timezone, timedelta
import json
import re

DEFAULT_ROUTES = [{'section':i,'prefix':chr(65+i),'operator':i+1} for i in range(5)]
PREFIX_PATTERN = r'[A-ZÖĞŞÇ]'


def routes(db):
    row=db.execute('SELECT value FROM settings WHERE id=1').fetchone()
    return json.loads(row['value']).get('section_routes',DEFAULT_ROUTES) if row else DEFAULT_ROUTES


def valid(value):
    return (isinstance(value,list) and len(value)==5 and all(isinstance(r,dict) and set(r)=={'section','prefix','operator'} and
        type(r['section']) is int and 0<=r['section']<5 and isinstance(r['prefix'],str) and re.fullmatch(PREFIX_PATTERN,r['prefix']) and
        type(r['operator']) is int and 1<=r['operator']<=30 for r in value) and
        len({r['section'] for r in value})==len({r['prefix'] for r in value})==len({r['operator'] for r in value})==5)


def for_section(config, section):
    return next(r for r in config if r['section']==section)


def code(ticket):
    return f"{ticket['prefix']}-{ticket['queue_seq']:03d}"


def public_ticket(ticket):
    return dict(ticket)|{'code':code(ticket)}


def queue_day(stamp):
    if not stamp:return 'legacy'
    try:
        value=datetime.fromisoformat(str(stamp).replace('Z','+00:00'))
        if value.tzinfo is None:value=value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone(timedelta(hours=5))).date().isoformat()
    except ValueError:return 'legacy'


def initialize_daily_queue(db):
    columns={r[1] for r in db.execute('PRAGMA table_info(tickets)')}
    if 'queue_day' not in columns:db.execute("ALTER TABLE tickets ADD COLUMN queue_day TEXT NOT NULL DEFAULT ''")
    for ticket in db.execute("SELECT id,created_at FROM tickets WHERE queue_day='' ").fetchall():
        db.execute('UPDATE tickets SET queue_day=? WHERE id=?',(queue_day(ticket['created_at']),ticket['id']))
    # Keep existing receipt numbers intact; uniqueness now includes the issue date.
    db.execute('DROP INDEX IF EXISTS ticket_code')
    db.execute('CREATE UNIQUE INDEX IF NOT EXISTS ticket_day_code ON tickets(prefix,queue_day,queue_seq)')
