# Application browser policy hardening

This patch replaces script-src unsafe-inline with SHA-256 allowlists of the
trusted static page's exact inline script text. External JavaScript remains
same-origin only. CRLF and CR line endings are normalized as HTML does before
hashing, so Windows-edited HTML remains usable. Static HTML comes from the
repository, never from uploaded or user-generated HTML templates.

The error-page retry button now uses an ordinary JS event listener rather than
an inline onclick attribute. The page retains inline CSS for current templates;
this is a defence-in-depth change, not proof that all XSS or injection is absent.

Objects and frames are disabled; existing anti-framing and no-sniff headers are
retained. Permissions-Policy disables unused camera/microphone/location APIs.
Uploaded audio playback and SpeechSynthesis do not require microphone access.
Cross-origin opener/resource headers are added; some browser isolation guarantees
require HTTPS, which remains a separate deployment requirement. Runtime/Python
version information is removed from the application's Server header.

Evidence:

- Real Chromium: trusted UI and login, language/theme controls, escaped stored
  request text and retry-after-initial-load-failure all work. Injected inline
  script and onclick attribute produce policy violations and do not execute.
- The same browser check passes when the actual served index.html has Windows
  CRLF endings (staged code only; no live database copied).
- Workflow, enhancements and five-operator/500-audio browser regressions pass.
- HTTP tests verify policy script hashes against served bytes and the response
  headers. Browser tests do not use production accounts or student data.

Commands:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/security-browser.cjs
NAVBOT_TEST_CRLF=1 node tests/security-browser.cjs
```

Production rollout: take a verified backup, pull code, restart navbot.service,
check service status, GET/login response headers and a real staff login. No
schema migration or credential changes are introduced by this patch. Rollback
code/index.html together if necessary, then restart service; do not restore or
overwrite the database for a browser-policy rollback.

Still required before public release: HTTPS and reliable certificate renewal,
Secure cookies configured for verified TLS/proxy handling, application admin
MFA, off-host protected backups and staging disaster-recovery acceptance,
malware-scanning/quarantine policy for documents, monitoring and independent
security assessment. Passing regression tests is not an expert certification.
