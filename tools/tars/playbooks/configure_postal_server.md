# Playbook: Configure Postal Email Server

## Goal
Set up or reconfigure the self-hosted Postal mail server for meridian.tips.

## Prerequisites
- Postal is running via Docker on this VPS
- DNS records are configured (see add_namecheap_dns.md)

## Access

- **Web UI**: http://localhost:5000
- **Login**: aidanpierce72@gmail.com
- **API Key**: stored in `/root/Meridian/.env` as `POSTAL_API_KEY`

## Steps: Add a Sending Domain

1. Open http://localhost:5000 in browser
2. Log in with aidanpierce72@gmail.com
3. Go to **Organizations** → select or create one
4. Go to **Servers** → select or create the mail server
5. Click **Domains** → **Add Domain**
6. Enter: `meridian.tips`
7. Postal will show required DNS records — add them at Namecheap (see add_namecheap_dns.md)
8. Click **Check DNS** to verify all records are green

## Steps: Get DKIM Key

```bash
docker exec meridian-postal-web postal default-dkim-record
```
Add the output as a TXT record at Namecheap.

## Steps: Verify Domain Health

```bash
docker exec meridian-postal-web sh -c 'postal console <<RUBY
domain = Domain.first
domain.check_dns!
puts "SPF: #{domain.spf_status}"
puts "DKIM: #{domain.dkim_status}"
puts "MX: #{domain.mx_status}"
puts "Return Path: #{domain.return_path_status}"
RUBY'
```

All should show `OK`.

## Steps: Update Meridian Env Vars

Ensure these are set in `/root/Meridian/.env`:
```
POSTAL_HOST=https://postal.meridian.tips
POSTAL_API_KEY=<your-api-key>
POSTAL_FROM=Meridian <hello@meridian.tips>
```

Then restart the backend:
```bash
# If running locally
kill $(lsof -t -i:8000) && uvicorn src.api.app:app --host 0.0.0.0 --port 8000 &

# On Railway — just push or trigger redeploy
```

## Test Email

```bash
curl -X POST https://api.meridian.tips/api/email/send \
  -H "Content-Type: application/json" \
  -d '{"to": "aidanpierce72@gmail.com", "subject": "Test", "body": "Postal is working"}'
```
