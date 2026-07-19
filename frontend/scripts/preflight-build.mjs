#!/usr/bin/env node
// preflight-build.mjs — refuse to start a PRODUCTION build unless the
// frontend/.env.local that Vite will bake into the bundle is REAL.
//
// Why this exists: the Canada frontend is a MANUAL Contabo nginx build. The #1
// recurring footgun is forgetting frontend/.env.local — Vite then inlines empty
// strings for VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY, src/lib/supabase.ts
// falls back to `supabase = null` ("demo mode"), and the site silently ships
// with broken auth. Nobody notices until a customer can't log in.
//
// This script asserts BEFORE `vite build` that .env.local exists and carries a
// real Supabase URL + anon key. It exits non-zero with a loud, specific error
// telling the operator exactly what is missing and where to fix it.
//
// It does NOT touch the build output or app behavior — pure guardrail.

import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FRONTEND_DIR = resolve(__dirname, '..')
const ENV_PATH = resolve(FRONTEND_DIR, '.env.local')

// ---------------------------------------------------------------------------
// Loud output helpers
// ---------------------------------------------------------------------------
const RED = '\x1b[31m'
const YELLOW = '\x1b[33m'
const GREEN = '\x1b[32m'
const BOLD = '\x1b[1m'
const RESET = '\x1b[0m'

function fail(lines) {
  console.error('')
  console.error(`${RED}${BOLD}${'='.repeat(72)}${RESET}`)
  console.error(`${RED}${BOLD}  PREFLIGHT FAILED — refusing to build (would ship DEMO MODE)${RESET}`)
  console.error(`${RED}${BOLD}${'='.repeat(72)}${RESET}`)
  for (const l of lines) console.error(`${RED}  ${l}${RESET}`)
  console.error('')
  console.error(`${YELLOW}  Fix: create/repair ${BOLD}${ENV_PATH}${RESET}${YELLOW} then re-run the build.${RESET}`)
  console.error(`${YELLOW}  Template: ${resolve(FRONTEND_DIR, '.env.example')}${RESET}`)
  console.error(`${YELLOW}  See frontend/DEPLOY.md for the manual Contabo build procedure.${RESET}`)
  console.error('')
  process.exit(1)
}

// ---------------------------------------------------------------------------
// Minimal .env parser (KEY=VALUE, strips surrounding quotes, ignores comments)
// ---------------------------------------------------------------------------
function parseEnv(raw) {
  const out = {}
  for (const rawLine of raw.split('\n')) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const eq = line.indexOf('=')
    if (eq === -1) continue
    const key = line.slice(0, eq).trim()
    let val = line.slice(eq + 1).trim()
    // strip a single pair of matching surrounding quotes
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1)
    }
    out[key] = val
  }
  return out
}

// Values that are technically present but are NOT a real config.
const PLACEHOLDER_TOKENS = [
  'your-',
  'your_',
  'changeme',
  'change-me',
  'placeholder',
  'example',
  'xxxx',
  'todo',
  '<',
  '...',
]

function looksPlaceholder(val) {
  const v = val.toLowerCase()
  return PLACEHOLDER_TOKENS.some((t) => v.includes(t))
}

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------
function main() {
  // 1. .env.local must exist
  if (!existsSync(ENV_PATH)) {
    fail([
      `${ENV_PATH} does NOT exist.`,
      'Without it, Vite bakes empty Supabase creds into the bundle and the',
      'site ships in demo mode with broken login.',
    ])
  }

  const env = parseEnv(readFileSync(ENV_PATH, 'utf8'))
  const url = (env.VITE_SUPABASE_URL || '').trim()
  const key = (env.VITE_SUPABASE_ANON_KEY || '').trim()
  const problems = []

  // 2. VITE_SUPABASE_URL — present, a real https URL, not localhost/placeholder
  if (!url) {
    problems.push('VITE_SUPABASE_URL is missing or empty.')
  } else if (looksPlaceholder(url)) {
    problems.push(`VITE_SUPABASE_URL looks like a placeholder: "${url}"`)
  } else {
    let parsed
    try {
      parsed = new URL(url)
    } catch {
      problems.push(`VITE_SUPABASE_URL is not a valid URL: "${url}"`)
    }
    if (parsed) {
      if (parsed.protocol !== 'https:') {
        problems.push(`VITE_SUPABASE_URL must be https, got "${parsed.protocol}//" in "${url}"`)
      }
      const host = parsed.hostname.toLowerCase()
      if (host === 'localhost' || host === '127.0.0.1' || host.endsWith('.local')) {
        problems.push(`VITE_SUPABASE_URL points at a local host ("${host}") — not a production Supabase URL.`)
      }
    }
  }

  // 3. VITE_SUPABASE_ANON_KEY — present and not a placeholder
  if (!key) {
    problems.push('VITE_SUPABASE_ANON_KEY is missing or empty.')
  } else if (looksPlaceholder(key)) {
    problems.push(`VITE_SUPABASE_ANON_KEY looks like a placeholder: "${key.slice(0, 24)}..."`)
  } else if (key.length < 40) {
    // Real Supabase anon keys are long JWTs (>100 chars). 40 is a safe floor.
    problems.push(`VITE_SUPABASE_ANON_KEY is suspiciously short (${key.length} chars) — expected a Supabase JWT.`)
  }

  if (problems.length) {
    fail(problems)
  }

  // Passed. Confirm loudly (short host echo, never print the key).
  const host = (() => {
    try {
      return new URL(url).host
    } catch {
      return url
    }
  })()
  console.error(
    `${GREEN}${BOLD}[preflight]${RESET}${GREEN} OK — real Supabase config found ` +
      `(host=${host}, anon key length=${key.length}). Proceeding with production build.${RESET}`,
  )
}

main()
