# NAVBOT verified backups

`navbot-backup.py` runs as root. It briefly stops an active navbot.service, copies
/var/lib/navbot (including integration secret sidecars), application code without
.git, the systemd unit and Nginx site configuration. It restarts the application
in a finally block before compressing and checking the snapshot. A missing
configuration or failed copy does not publish a completed archive.

Each archive is unpacked into an isolated temporary directory. All file hashes,
SQLite integrity and record counts must match before publication. This tests
file and database recovery, not full application recovery on another machine.
Run a separate staging recovery and functional login/attachment/audio tests
before calling disaster recovery verified. Never extract over the live database.

Archives are in /var/backups/navbot, directory0700 and archives0600, with the last
30 automatic archives retained only after a successful backup. They contain
personal data, password hashes and potentially API credentials. Local archives
are not encrypted. Copy them through an encrypted channel to a separately
protected backup target; keep an off-host/offline copy. A VM snapshot or this
same-disk folder alone does not protect against loss of the Proxmox host.

Install script at /usr/local/sbin/navbot-backup.py mode0700 root-owned; units at
/etc/systemd/system/navbot-backup.{service,timer} mode0644. Create
/var/backups/navbot mode0700 root-owned first. Run the service manually and check
its logs, NAVBOT status and restored counts before enabling the timer. The timer
runs at03:00 Asia/Tashkent plus up to10minutes and catches missed runs on startup.

Commands:

```bash
sudo systemctl start navbot-backup.service
sudo journalctl -u navbot-backup.service -n 30 --no-pager
sudo systemctl is-active navbot
sudo systemctl enable --now navbot-backup.timer
sudo systemctl list-timers navbot-backup.timer --no-pager
```

Independent archive check (replace the path with the exact printed archive):

```bash
sudo python3 /usr/local/sbin/navbot-backup.py --verify /var/backups/navbot/navbot-backup-TIMESTAMP-ID.tar.gz
```

Code and state stay separate: /opt/navbot is code, /var/lib/navbot is private state.
Do not seed demo users or replace the state folder during a code update.

After request cleanup, counts distinguish total request ID reservations from
active_requests and deleted_request_reservations. Reserved IDs prevent old
printed tickets or retried request keys from being reused. They are not active
requests. Older backup archives retain their prior payloads under the retention
policy; application cleanup does not purge historical archives.
