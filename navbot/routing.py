"""Section routing and immutable, independently numbered queue codes."""
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
