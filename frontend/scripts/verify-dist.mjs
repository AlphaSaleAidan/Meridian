#!/usr/bin/env node
// verify-dist.mjs — AFTER `vite build`, prove the shipped bundle is NOT demo mode.
//
// How demo mode is detected in the code (src/lib/supabase.ts):
//   const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
//   ... if (!supabaseUrl || !supabaseAnonKey) console.error('...(demo mode)')
//   export const supabase = supabaseUrl && supabaseAnonKey ? createClient(...) : null
// Vite INLINES import.meta.env.VITE_SUPABASE_URL as a string literal at build
// time. So a correctly-built prod bundle contains the real Supabase host as a
// hard-coded string; a demo-mode bundle contains an empty string there and the
// live "(demo mode)" console.error marker survives in the emitted JS.
//
// This check greps dist/ for:
//   (a) the demo-mode marker string  -> FAIL if the bundle would announce demo mode
//   (b) the real Supabase host        -> FAIL if it is NOT inlined anywhere
//
// It reads the same .env.local the build consumed to know what the "real" host
// should be. It does NOT modify dist/ — pure post-build gate.

import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FRONTEND_DIR = resolve(__dirname, '..')
const DIST_DIR = resolve(FRONTEND_DIR, 'dist')
const ENV_PATH = resolve(FRONTEND_DIR, '.env.local')

const RED = '\x1b[31m'
const YELLOW = '\x1b[33m'
const GREEN = '\x1b[32m'
const BOLD = '\x1b[1m'
const RESET = '\x1b[0m'

function fail(lines) {
  console.error('')
  console.error(`${RED}${BOLD}${'='.repeat(72)}${RESET}`)
  console.error(`${RED}${BOLD}  VERIFY-DIST FAILED — the built bundle looks like DEMO MODE${RESET}`)
  console.error(`${RED}${BOLD}${'='.repeat(72)}${RESET}`)
  for (const l of lines) console.error(`${RED}  ${l}${RESET}`)
  console.error('')
  console.error(`${YELLOW}  Do NOT deploy this dist/. Fix ${BOLD}${ENV_PATH}${RESET}${YELLOW} and rebuild with:${RESET}`)
  console.error(`${YELLOW}      npm run build:prod${RESET}`)
  console.error(`${YELLOW}  See frontend/DEPLOY.md.${RESET}`)
  console.error('')
  process.exit(1)
}

// The literal demo-mode marker emitted by src/lib/supabase.ts. If this survives
// into the bundle, it means the runtime demo-mode branch is reachable AND (more
// tellingly) the creds were empty at build time. Kept in sync with that file.
const DEMO_MARKER = 'running without Supabase (demo mode)'

// ---------------------------------------------------------------------------
// Recursively collect built JS asset files.
// ---------------------------------------------------------------------------
function collectJs(dir, acc = []) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    const st = statSync(full)
    if (st.isDirectory()) collectJs(full, acc)
    else if (name.endsWith('.js')) acc.push(full)
  }
  return acc
}

function parseEnv(raw) {
  const out = {}
  for (const rawLine of raw.split('\n')) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const eq = line.indexOf('=')
    if (eq === -1) continue
    const key = line.slice(0, eq).trim()
    let val = line.slice(eq + 1).trim()
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

function main() {
  if (!existsSync(DIST_DIR)) {
    fail([`dist/ not found at ${DIST_DIR}. Did the build run? Expected preflight -> vite build -> verify.`])
  }

  const jsFiles = collectJs(DIST_DIR)
  if (jsFiles.length === 0) {
    fail([`No .js assets found under ${DIST_DIR}. The build produced no bundle.`])
  }

  // What host SHOULD be inlined? Read from the same .env.local the build used.
  let expectedHost = null
  if (existsSync(ENV_PATH)) {
    const url = (parseEnv(readFileSync(ENV_PATH, 'utf8')).VITE_SUPABASE_URL || '').trim()
    if (url) {
      try {
        expectedHost = new URL(url).host
      } catch {
        expectedHost = url // best effort; preflight already validated shape
      }
    }
  }

  const problems = []
  let demoMarkerHits = []
  let hostFound = false

  for (const file of jsFiles) {
    const content = readFileSync(file, 'utf8')
    if (content.includes(DEMO_MARKER)) {
      demoMarkerHits.push(file.replace(DIST_DIR + '/', ''))
    }
    if (expectedHost && content.includes(expectedHost)) {
      hostFound = true
    }
  }

  // (a) Demo marker must not be present.
  if (demoMarkerHits.length) {
    problems.push(
      `Demo-mode marker string "${DEMO_MARKER}" is present in the bundle ` +
        `(${demoMarkerHits.join(', ')}).`,
    )
    problems.push('That means supabase.ts hit its no-creds branch at build time.')
  }

  // (b) The real Supabase host must be inlined.
  if (!expectedHost) {
    problems.push(
      `Could not determine the expected Supabase host — ${ENV_PATH} is missing or ` +
        'has no VITE_SUPABASE_URL. Run preflight first (npm run build:prod).',
    )
  } else if (!hostFound) {
    problems.push(
      `Real Supabase host "${expectedHost}" was NOT found inlined in any dist/ JS. ` +
        'Vite did not bake the production creds — the bundle is demo mode.',
    )
  }

  if (problems.length) {
    fail(problems)
  }

  console.error(
    `${GREEN}${BOLD}[verify-dist]${RESET}${GREEN} OK — bundle carries real Supabase host ` +
      `"${expectedHost}", no demo-mode marker in ${jsFiles.length} JS asset(s). Safe to deploy.${RESET}`,
  )
}

main()
