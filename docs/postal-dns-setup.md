# Postal DNS Setup for meridian.tips

## Required DNS Records

Add these records at your domain registrar (Cloudflare, Namecheap, etc.):

### 1. MX Record (receive bounces)
```
Type: MX
Host: rp
Value: postal.meridian.tips
Priority: 10
```

### 2. SPF Record (authorize sending)
```
Type: TXT
Host: @
Value: v=spf1 a mx include:spf.meridian.tips ~all
```

### 3. DKIM Record
Get the DKIM public key from Postal:
```bash
docker exec meridian-postal-web postal default-dkim-record
```
Then add:
```
Type: TXT
Host: postal-<identifier>._domainkey
Value: (output from above command)
```

### 4. DMARC Record
```
Type: TXT
Host: _dmarc
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc@meridian.tips
```

### 5. Return Path CNAME
```
Type: CNAME
Host: rp
Value: postal.meridian.tips
```

### 6. A Record for Postal
```
Type: A
Host: postal
Value: <this server's public IP>
```

## Verification

After adding DNS records, verify domain in Postal:
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

## Server IP

Get this server's public IP:
```bash
curl -s ifconfig.me
```

## Current Postal Credentials

- **Web UI**: http://localhost:5000 (login: aidanpierce72@gmail.com)
- **API Key**: Set in /root/Meridian/.env as POSTAL_API_KEY
- **SMTP Port**: 25
