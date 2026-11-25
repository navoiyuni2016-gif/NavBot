"""Immutable instance binding for process-isolated university tenants."""
from urllib.parse import urlsplit


def identity(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='tenant_instance' AND type='table'").fetchone():
        return None
    row=db.execute('SELECT tenant_id,domain,port FROM tenant_instance WHERE id=1').fetchone()
    return dict(row) if row else None


def bind(db, tenant_id, domain, port):
    if identity(db):raise ValueError('Tenant already bound; do not reuse a database')
    db.execute('CREATE TABLE tenant_instance(id INTEGER PRIMARY KEY CHECK(id=1),tenant_id TEXT NOT NULL,domain TEXT NOT NULL,port INTEGER NOT NULL)')
    db.execute('INSERT INTO tenant_instance VALUES(1,?,?,?)',(tenant_id,domain,port))


def verify(db, expected, port=None):
    row=identity(db)
    if not row or row['tenant_id']!=expected or (port is not None and row['port']!=port):
        raise ValueError('Tenant ID/port does not match this database; startup refused')
    return row


def valid_host(binding, host):
    if not binding:return True  # Existing single-university installations are unchanged.
    try:
        parsed=urlsplit('//'+(host or ''))
        parsed.port  # Validate malformed port syntax too.
        return parsed.hostname==binding['domain'] and parsed.username is None and parsed.password is None and not parsed.path and not parsed.query and not parsed.fragment
    except ValueError:return False
