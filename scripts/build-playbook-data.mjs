#!/usr/bin/env node
// Bundle docs/playbook/**/*.md into frontend/src/data/playbook.json so the
// rep portal can render the playbook without runtime fetches.
//
// Run: node scripts/build-playbook-data.mjs
// Auto-runs via `npm run dev` and `npm run build` (predev/prebuild hooks).

import { readFileSync, readdirSync, statSync, writeFileSync, mkdirSync } from 'fs'
import { join, relative, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = join(__dirname, '..')
const playbookRoot = join(repoRoot, 'docs/playbook')
const outFile = join(repoRoot, 'frontend/src/data/playbook.json')

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

console.log(`Bundled ${Object.keys(files).length} playbook files → ${relative(repoRoot, outFile)}`)
