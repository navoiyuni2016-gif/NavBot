# LAN Nginx request limits

The current deployment serves NAVBOT on loopback8081 and exposes only LAN HTTP
through Nginx. The files here do not configure TLS or change UFW. Do not publish
the site on the Internet as a result of installing these files.

Install navbot-nginx-lan.conf at /etc/nginx/sites-available/navbot. The standard
Ubuntu configuration includes sites-enabled inside its http context; the zone
definitions at the top must remain outside the server block. Keep only one
enabled link to this file. Back up the original site first. Never reload before
`nginx -t` succeeds. If validation fails, restore the original site; the running
Nginx configuration remains unchanged until a reload. The existing NAVBOT
backup script captures this whole site file, including its zone definitions.

Limits:

- Login POST endpoint:10 requests/minute per source IP, burst10, excess429.
  Nginx limits all requests to that exact endpoint, not just failed passwords.
  The application retains its separate account-based failed-login limits.
- Concurrent requests:32/source IP. NAT-sharing clients share this allowance;
  monitor429 responses before increasing limits.
- Body16MiB, header/body/send idle timeouts, server version hidden.
- Uploads, TV polling and normal APIs have no generic request-per-second limit,
  preserving sequential500-file audio batches. Authentication and application
  upload type/size/count checks remain necessary. This is not malware scanning
  or a complete denial-of-service defence.

The real-process test was run with upstream Nginx1.26.3 compiled in an isolated
workspace, using a test HTTP backend. It checks login limiting (including spoofed
forwarding headers),500 sequential uploads, polling, oversized-body rejection,
32 active connections/429 overflow and recovery, and hidden server versions.
Run `python3 tests/nginx-security.py --nginx /usr/sbin/nginx` to repeat on the
target. Validate on the installed Ubuntu Nginx1.24 as well. Check `nginx -t`, then reload and confirm GET/login,
GET/api/me and authenticated workflows. Do not use `curl -I`: app HEAD is not
implemented. Never test rate limits with real passwords or deliberately trigger
account lockout. Use empty JSON requests from loopback if a controlled rate test
is needed, and wait for the limiter to refill afterward.

This file is for the current single LAN server, not a template to overwrite
an already configured TLS site. When HTTPS is installed, carry the same zones
and login/connection limits into the443 server while preserving certificates.
