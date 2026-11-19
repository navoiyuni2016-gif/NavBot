# One-time transition from test queues to live use

Use only when the owner confirms ALL existing requests/tickets are fictitious. Do not run this as a daily reset. Real requests must never be discarded to restart queue numbering.

`prepare-live.py --db /var/lib/navbot/navbot.sqlite3` is read-only by default. Check the database path against `systemctl show navbot -p ExecStart` first. It reports counts and active accounts still using the known demo password, without printing hashes or credentials. In the admin UI, change those passwords or deactivate unused accounts. Keep at least one active administrator. Retained staff with other weak passwords still require human review; this tool only detects the known seed password.

Before cleanup, take the full deployment backup (`sudo systemctl start navbot-backup.service`), check that it succeeded, and retain its private archive with integration sidecars. The cleanup additionally makes a private `.before-live-…bak` SQLite backup and verifies its integrity/counts before deletion. This copy is beside the database and contains the former test state. Never restore it over a running service.

Stop `navbot` and `navbot-telegram` (if installed), and pause the Windows printer helper. Ensure no test paper remains queued in Windows. A queued physical job cannot be retracted by this tool. The command refuses to apply if systemd reports active/unknown application or Telegram workers.

```
sudo systemctl stop navbot-telegram
sudo systemctl stop navbot
sudo -u navbot python3 /opt/navbot/deploy/prepare-live.py --db /var/lib/navbot/navbot.sqlite3 --apply --all-requests-are-tests
```

If no Telegram service is installed, skip its stop/start commands. On any error, the transaction is rolled back; do not assume cleanup completed. Restart the previously running services to restore access and investigate the error before retrying.

What is cleared: test tickets, calls, requests, request attachments, request history, notifications, Telegram releases/outbox, printer jobs, web sessions, expiring Telegram codes and student-delete previews. Old audit events are retained with an explicit transition marker; historical request IDs may refer to removed test records. New request/ticket IDs may be reused after cleanup. What stays: users/passwords/roles, student registry, audio recordings/settings, logos, routing, Telegram links/config/runtime offset, integration configuration/secrets, printer pairing and audit trail. Synthetic registry entries and user names are not automatically guessed/deleted; review them separately. No login credentials are reset silently. Existing sessions are invalidated: staff log in again.

Restart the application and any previously enabled Telegram worker, then the Windows helper. Reload all kiosk/TV/desk pages to discard old session state. The first new A/B/C/D/E ticket starts at 001; issue only a controlled real acceptance ticket and process it normally. Do not repeatedly clear the database. Enable the existing backup timer and startup units according to deployment policy; this cleanup does not change systemd enablement or Android/Windows autostart settings.

Before opening to students: test one ticket → paper → correct operator → TV number and recorded voice → completion. Check that recordings cover the numbers/prefixes/operators used in each enabled language; the successful A-001 sample does not prove s31.wav or the rest of the number library exists. Missing recordings are shown on the TV; the tool does not synthesize or replace uploaded audio. Confirm the backed-up app starts without `--seed-demo`. Live status cannot be asserted from a source checkout: target-server service/login/device checks are required.
