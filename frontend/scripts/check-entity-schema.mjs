#!/usr/bin/env node
// Validates the global JSON-LD entity graph in index.html: the @id cross-links that
// make Google resolve "Meridian AI Business Solutions" + founder Aidan Pierce into one
// entity. Fails loudly if a rename breaks the graph. Run: node scripts/check-entity-schema.mjs
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import assert from 'node:assert/strict'

const here = dirname(fileURLToPath(import.meta.url))
const html = await readFile(join(here, '..', 'index.html'), 'utf8')

const block = html.match(/<script type="application\/ld\+json">\s*([\s\S]*?)<\/script>/)
assert(block, 'no ld+json block in index.html')
const graph = JSON.parse(block[1])['@graph']
const byType = t => graph.find(n => n['@type'] === t)

const org = byType('Organization')
const site = byType('WebSite')
assert(org.alternateName.includes('Meridian AI Business Solutions'), 'Org missing target alternateName')
assert.equal(org['@id'], 'https://meridian.tips/#organization', 'Org @id drifted')
assert.equal(org.founder['@id'], 'https://meridian.tips/#aidan-pierce', 'founder @id not cross-linked')
assert.equal(site.publisher['@id'], org['@id'], 'WebSite.publisher does not point at Organization')
assert.equal(site.alternateName, 'Meridian AI Business Solutions', 'WebSite missing target alternateName')

console.log('OK entity graph: org+website+founder @ids resolve, target name present')
