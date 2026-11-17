# Additional NAVBOT service sandbox

Install navbot-hardening.conf as the root-owned regular file
/etc/systemd/system/navbot.service.d/20-hardening.conf (0644). Keep the existing
base unit, dedicated navbot-svc account and ReadWritePaths=/var/lib/navbot.
Do not apply these settings to ssh.service, nginx.service or the backup service.

The drop-in hides host devices, blocks kernel/control-group/hostname changes,
SUID/SGID creation, realtime scheduling, namespace creation and personality
changes, and clears the service's capability bounding/ambient sets. It does not
block TCP/UDP/Unix sockets, normal threads or database/data-folder writes. No
aggressive syscall filter, memory-execution or memory-limit setting is added
without application-specific runtime evidence.

Directive syntax was checked using systemd257's user-mode verifier with a
mock wrapper. The coding environment cannot run a full system service sandbox;
validate and exercise the real service on target Ubuntu24.04/systemd255 before
calling this deployed. The isolated backup/drop-in archive test passes.

Rollout:

1. Take a verified backup and pull code.
2. Reinstall the updated backup script at /usr/local/sbin/navbot-backup.py,
   root-owned0700. It now includes live navbot.service.d/*.conf in snapshots.
3. Install the drop-in. Verify with
   `sudo systemd-analyze verify /etc/systemd/system/navbot.service`.
4. Only if validation succeeds, daemon-reload and restart navbot.
5. Check service status, GET/login, real authenticated login, student lookup,
   attachment upload/download and Excel export; later check configured LMS
   networking when available. No database migration or password change needed.
6. Take another verified backup after successful target acceptance.

If startup fails: move only20-hardening.conf to a filename not ending in.conf,
then daemon-reload and restart NAVBOT. Do not change SSH or erase the database.
Inspect journalctl-u navbot for the actual failure before retrying.

This limits potential impact of an application compromise; it is not a complete
security boundary against every kernel exploit or a security certification.
