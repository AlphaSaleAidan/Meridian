# Remaining Tasks — Reasoning Log

## Status as of 2026-05-08

### Completed This Session
- [x] Push commit 9ebf7a4 to remote (all 11 email templates + Evolver integration)
- [x] Set WORKER_ENABLED=1 in services/evolver/.env
- [x] Set GITHUB_TOKEN in services/evolver/.env
- [x] Verified .env is gitignored (credential safety confirmed)
- [x] Created log directories: logs/agents/, logs/history/, logs/memory/
- [x] Smoke-tested Evolver — boots clean in review/prompt-only mode
- [x] Installed crontab: 3:30 AM daily repair-only, 4:00 AM Sunday harden
- [x] Installed Docker Engine on Ubuntu 24.04 server
- [x] Deployed Postal email stack (5 containers: web, smtp, worker, mariadb, rabbitmq)
- [x] Initialized Postal DB schema
- [x] Created admin user (aidanpierce72@gmail.com)
- [x] Created Meridian org + mail server + API credential
- [x] Added and verified meridian.tips sending domain
- [x] Sent test emails via Postal API (confirmed success response)
- [x] Set POSTAL_HOST + POSTAL_API_KEY in backend .env
- [x] Updated PostalClient with Host header for local Postal proxy
- [x] Updated .env.example with Postal placeholders
- [x] Created DNS setup documentation

### Remaining: DNS Configuration (User Action Required)
DNS records must be added at the domain registrar for full email delivery:
- MX record for bounce handling
- SPF record for send authorization
- DKIM record for message signing
- DMARC record for policy
- A record pointing postal.meridian.tips to this server's IP

See: docs/postal-dns-setup.md
