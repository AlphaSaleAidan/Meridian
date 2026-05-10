# Playbook: Add Namecheap DNS Records

## Goal
Add or update DNS records for meridian.tips at Namecheap.

## Steps

1. Open https://ap.www.namecheap.com/domains/domaincontrolpanel/meridian.tips/advancedns
2. Log in to Namecheap if prompted
3. You should see the **Advanced DNS** tab for meridian.tips
4. To add a new record:
   - Click **Add New Record**
   - Select the record type (A, CNAME, TXT, MX)
   - Fill in Host, Value, and TTL
   - Click the checkmark to save
5. Wait 5-30 minutes for DNS propagation

## Current Required Records

### Postal Email (see docs/postal-dns-setup.md)

| Type | Host | Value | Note |
|------|------|-------|------|
| A | postal | `<server-ip>` | Postal mail server |
| CNAME | rp | postal.meridian.tips | Return path |
| MX | rp | postal.meridian.tips (pri 10) | Bounce handling |
| TXT | @ | `v=spf1 a mx include:spf.meridian.tips ~all` | SPF |
| TXT | _dmarc | `v=DMARC1; p=quarantine; rua=mailto:dmarc@meridian.tips` | DMARC |
| TXT | postal-*._domainkey | (from Postal DKIM output) | DKIM |

### API / Frontend

| Type | Host | Value | Note |
|------|------|-------|------|
| CNAME | api | Railway-provided CNAME | Backend API |
| CNAME | app | Vercel-provided CNAME | Frontend dashboard |

## Verification

```bash
# Check A record
dig A postal.meridian.tips +short

# Check CNAME
dig CNAME api.meridian.tips +short

# Check MX
dig MX rp.meridian.tips +short

# Check TXT (SPF)
dig TXT meridian.tips +short

# Check DMARC
dig TXT _dmarc.meridian.tips +short
```

## TTL
Use **Automatic** (default) or **1800** (30 min) for records you might change soon. Use **3600+** for stable records.
