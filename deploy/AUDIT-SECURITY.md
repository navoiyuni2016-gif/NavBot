# Application audit and IP protection

The admin Audit journal filters by Tashkent date range, actor/login, IP, action, risk, result and category. Pagination is server-side, fixed at 50 rows. Historical rows remain, with blank IP/method when these were not captured originally. New business audit rows store the actor's name/login and active role at event time. Generic request records cover application requests and failures; recurring polling and already-blocked requests are counted per minute instead of creating unbounded duplicate rows.

Uploads record the client-supplied filename where the browser provides it, request size, action and outcome; downloads record the server's download filename and response size. Names are metadata, not proof of file identity. Passwords, cookies, session tokens, authorization headers, query strings and file bytes are not copied into the security audit. Existing business audit details (request edits/answers, IDs, etc.) remain admin-only. Anonymous attempted usernames are unverified claims, not identified people.

## IP trust

The backend stays bound to 127.0.0.1:8081. Only loopback proxy connections may supply `X-Real-IP`; all other peers use the socket address. `X-Forwarded-For` is never accepted as identity. The existing Nginx site must retain:

```nginx
proxy_set_header X-Real-IP $remote_addr;
```

It must overwrite, not pass through, a client-supplied header. Do not expose 8081 externally. If another gateway/proxy terminates traffic, validate its topology before changing trust; the recorded address can be a NAT gateway shared by users.

## Detection and blocks

- 10 failed/rate-limited login attempts from one IP within 10 minutes: 15-minute IP block.
- 3 sensitive path probes within 5 minutes: 15-minute IP block. Examples are `.env`, `.git`, WordPress and phpMyAdmin paths, and traversal patterns.
- New successful login IP for an account with prior IP history: warning to active base-superadmin accounts, without blocking the legitimate login.
- Permission failures, validation errors and server failures are visible separately; a single rejected business action does not ban the user.

Blocks are stored in SQLite and survive restarts until expiry or manual release. They reject sensitive application requests with429. Safe public kiosk/TV reads remain available so a shared address does not black out displays. Existing authenticated base-superadmin sessions retain read access and role-switch/unblock recovery routes; write operations remain blocked until release. The admin can reload the application and unblock an IP from Audit. New unauthenticated logins from the blocked IP remain denied. This is application-level enforcement, not an OS firewall rule.

Every block and manual release is audited. Block alerts and new-IP alerts are delivered as ordinary security notifications to active base superadmins. An open admin page polls and displays a visible banner and notification badge. Browser notifications are opt-in and require a secure supported browser context; they work while the app is running. Closed-browser/background Web Push is not implemented and requires HTTPS plus a separately configured service worker/push service.

## Boundaries and operations

These rules identify specific behaviors, not every exploit or intrusion. An IP is not a person's identity. Requests rejected before reaching Python (Nginx body/rate limits, firewall, SSH/Fail2ban and network attacks) are in those components' own logs and are not imported into this table. Existing Nginx/UFW/SSH protection remains necessary. This feature does not certify the system or replace independent testing.

Audit tables have no application delete endpoint and are included in the existing verified database backups. A server/database administrator can still alter local data; the log is not an external tamper-proof evidence store. No silent retention purge is installed. Monitor disk usage and the service journal; `Security audit persistence failed` warns that a database/storage failure prevented recording. Never leave such a warning uninvestigated.
