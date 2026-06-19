// Google Search Console auth for unattended cron.
//
// Preferred: a service-account JSON key (GSC_SA_KEY_FILE=/path/to/key.json). This signs a
// JWT and exchanges it for a short-lived access token on each run — no manual token refresh.
// Fallback: a pre-acquired bearer token (GSC_ACCESS_TOKEN) for quick manual testing.
//
// No secrets in code. The key file lives outside the repo and is referenced by env only.

import { readFile } from 'node:fs/promises'
import { createSign } from 'node:crypto'

const SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly'
const TOKEN_URL = 'https://oauth2.googleapis.com/token'

function b64url(input) {
  return Buffer.from(input).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

// Exchange a service-account key for an access token via the JWT bearer grant.
async function tokenFromServiceAccount(keyPath, nowSec) {
  const key = JSON.parse(await readFile(keyPath, 'utf8'))
  const iat = nowSec
  const exp = nowSec + 3600
  const header = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }))
  const claim = b64url(JSON.stringify({
    iss: key.client_email,
    scope: SCOPE,
    aud: TOKEN_URL,
    iat,
    exp,
  }))
  const signingInput = `${header}.${claim}`
  const signer = createSign('RSA-SHA256')
  signer.update(signingInput)
  const signature = b64url(signer.sign(key.private_key))
  const assertion = `${signingInput}.${signature}`

  const res = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion,
    }),
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`GSC token exchange failed: ${res.status} ${body}`)
  }
  const json = await res.json()
  return json.access_token
}

// Returns a usable access token, or null if GSC isn't configured.
// nowSec is passed in by the caller (scripts avoid Date.now() at module scope).
export async function getGscAccessToken(env = process.env, nowSec = Math.floor(Date.now() / 1000)) {
  if (env.GSC_SA_KEY_FILE) return tokenFromServiceAccount(env.GSC_SA_KEY_FILE, nowSec)
  if (env.GSC_ACCESS_TOKEN) return env.GSC_ACCESS_TOKEN
  return null
}
