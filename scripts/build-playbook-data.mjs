#!/usr/bin/env node
// Bundle docs/playbook/**/*.md into frontend/public/data/playbook.json — a
// STATIC ASSET the rep portal fetches on demand (PlaybookViewer). It used to
// land in src/data/ and get imported, which baked ~1MB of markdown-as-JS into
// the training chunk; as a public asset it ships once, uncompiled, and only
// to reps who open the playbook.
//
// Run: node scripts/build-playbook-data.mjs
// Auto-runs via `npm run dev` and `npm run build` (predev/prebuild hooks).

import { readFileSync, readdirSync, statSync, writeFileSync, mkdirSync, rmSync } from 'fs'
import { join, relative, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = join(__dirname, '..')
const playbookRoot = join(repoRoot, 'docs/playbook')
const outFile = join(repoRoot, 'frontend/public/data/playbook.json')
// Stale output from the old bundled-as-JS location — remove so nothing can
// accidentally re-import it into the bundle.
const legacyOutFile = join(repoRoot, 'frontend/src/data/playbook.json')

const files = {}

function walk(dir) {
  for (const entry of readdirSync(dir).sort()) {
    if (entry.startsWith('.')) continue
    const full = join(dir, entry)
    const stat = statSync(full)
    if (stat.isDirectory()) {
      walk(full)
    } else if (entry.endsWith('.md')) {
      const key = relative(playbookRoot, full).replace(/\\/g, '/')
      files[key] = readFileSync(full, 'utf-8')
    }
  }
}

walk(playbookRoot)

mkdirSync(dirname(outFile), { recursive: true })
writeFileSync(outFile, JSON.stringify(files, null, 2))
rmSync(legacyOutFile, { force: true })

console.log(`Bundled ${Object.keys(files).length} playbook files → ${relative(repoRoot, outFile)}`)
