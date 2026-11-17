#!/usr/bin/env python3
"""Private, consistent offline backup with an isolated restore check (stdlib only)."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import uuid


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def database_check(path):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise RuntimeError('SQLite integrity check failed')
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {name: db.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
                for name in ('students', 'users', 'requests', 'audio_clips', 'attachments') if name in tables}
        if 'requests' in tables and 'deleted_at' in {r[1] for r in db.execute('PRAGMA table_info(requests)')}:
            counts['active_requests'] = db.execute('SELECT COUNT(*) FROM requests WHERE deleted_at IS NULL').fetchone()[0]
            counts['deleted_request_reservations'] = counts['requests'] - counts['active_requests']
        return counts


def verify_backup(archive):
    # Never restore over the live installation. Reject links and unsafe archive paths.
    with tempfile.TemporaryDirectory(prefix='navbot-restore-') as folder:
        root = Path(folder)
        with tarfile.open(archive, 'r:gz') as tar:
            for item in tar.getmembers():
                p = Path(item.name)
                if p.is_absolute() or '..' in p.parts or not (item.isfile() or item.isdir()):
                    raise RuntimeError('Unsafe backup member')
            tar.extractall(root, filter='data')
        manifest = json.loads((root / 'manifest.json').read_text())
        if manifest.get('format') != 1:
            raise RuntimeError('Unknown backup format')
        actual = {p.relative_to(root).as_posix(): digest(p) for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix() != 'manifest.json'}
        if actual != manifest['sha256']:
            raise RuntimeError('Backup file checksums do not match')
        counts = database_check(root / 'data' / 'navbot.sqlite3')
        if counts != manifest['counts']:
            raise RuntimeError('Restored record counts do not match')
        return counts


@contextmanager
def stopped_service(service):
    status = subprocess.run(['systemctl', 'is-active', service], capture_output=True, text=True)
    if status.stdout.strip() not in ('active', 'inactive', 'failed'):
        raise RuntimeError('Service state is unknown; backup not started')
    running = status.returncode == 0
    try:
        if running:
            subprocess.run(['systemctl', 'stop', service], check=True)
        yield
    finally:
        if running:
            subprocess.run(['systemctl', 'start', service], check=True)
            subprocess.run(['systemctl', 'is-active', '--quiet', service], check=True)


def copy_checked(source, destination):
    # Avoid archiving secrets outside the selected folders through symbolic links.
    for path in [source, *source.rglob('*')]:
        if path.is_symlink():
            raise RuntimeError('Symbolic link inside backup source: ' + str(path))
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))


def prune_backups(output, keep=30):
    archives = sorted((p for p in Path(output).iterdir()
        if re.fullmatch(r'navbot-backup-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}\.tar\.gz', p.name)
        and p.is_file() and not p.is_symlink()), key=lambda p:p.name, reverse=True)
    for old in archives[keep:]:
        old.unlink()


def create_backup(data, code, output, pause, configs=()):
    data, code, output = Path(data), Path(code), Path(output)
    if not (data / 'navbot.sqlite3').is_file() or not (code / 'navbot' / 'app.py').is_file():
        raise RuntimeError('Database or application files are missing')
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    with (output / '.backup.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix='.staging-', dir=output) as folder:
            stage = Path(folder)
            with pause():
                copy_checked(data, stage / 'data')
                copy_checked(code, stage / 'code')
                for source in map(Path, configs):
                    if not source.is_file() or source.is_symlink():
                        raise RuntimeError('Backup configuration missing or not a regular file: ' + str(source))
                    target = stage / 'config' / source.relative_to('/')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            # The live service has resumed before compression and restore verification.
            counts = database_check(stage / 'data' / 'navbot.sqlite3')
            hashes = {p.relative_to(stage).as_posix(): digest(p) for p in stage.rglob('*') if p.is_file()}
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            manifest = {'format': 1, 'created_utc': stamp, 'sha256': hashes, 'counts': counts}
            (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            partial = stage / 'archive.tmp'
            with tarfile.open(partial, 'w:gz') as tar:
                for name in ('data', 'code', 'config', 'manifest.json'):
                    if (stage / name).exists():
                        tar.add(stage / name, arcname=name)
            partial.chmod(0o600)
            verify_backup(partial)
            destination = output / f'navbot-backup-{stamp}-{uuid.uuid4().hex[:8]}.tar.gz'
            os.replace(partial, destination)
            prune_backups(output)
            return destination, counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', type=Path, help='Check an archive in isolation; never overwrite live data')
    args = parser.parse_args()
    os.umask(0o077)
    if args.verify:
        print('Restore check OK:', json.dumps(verify_backup(args.verify)))
        return
    if os.geteuid() != 0:
        parser.error('Run with sudo')
    configs = [Path('/etc/systemd/system/navbot.service'), Path('/etc/nginx/sites-available/navbot')]
    # Drop-ins are part of the live service configuration and must be restorable.
    configs.extend(sorted(Path('/etc/systemd/system/navbot.service.d').glob('*.conf')))
    destination, counts = create_backup('/var/lib/navbot', '/opt/navbot', '/var/backups/navbot',
        lambda: stopped_service('navbot.service'), configs)
    print('Verified backup:', destination)
    print('Restored record counts:', json.dumps(counts))


if __name__ == '__main__':
    main()
