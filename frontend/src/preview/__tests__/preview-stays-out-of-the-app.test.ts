/**
 * The preview harness must never reach a merchant.
 *
 * `src/preview/` holds sales and internal tooling: the trade switcher, the
 * "Compare trades" screen, invented shop names, and a fixture backend that
 * answers /api/bookings with made-up guests. All of it is useful for showing
 * the product and none of it belongs in front of a paying merchant — a
 * customer who finds a screen comparing their trade to five others, or a book
 * full of invented names, has learned something about us we did not intend to
 * teach.
 *
 * Today that separation holds by convention: nothing outside the folder
 * imports it, and the production bundle contains none of it. Convention is not
 * enough through a rebuild that ports four of these surfaces INTO the product
 * one at a time — the obvious mistake is dragging a neighbour across with the
 * file you meant to move.
 *
 * So this test is the guard rail. If it fails, something in the app now
 * depends on the harness, and the fix is to move the shared piece OUT of
 * preview/ rather than to import from it.
 */
import { describe, expect, it } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

const SRC = resolve(__dirname, '../..')
const PREVIEW = join(SRC, 'preview')

/** Every .ts/.tsx file under src/, excluding the preview folder itself. */
function appFiles(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (full.startsWith(PREVIEW)) continue
    if (entry === 'node_modules' || entry === 'dist') continue
    if (statSync(full).isDirectory()) {
      appFiles(full, out)
    } else if (/\.tsx?$/.test(entry) && !/\.test\.tsx?$/.test(entry)) {
      out.push(full)
    }
  }
  return out
}

/** Names that exist only to demonstrate the product, never to run it. */
const HARNESS_ONLY = [
  'TradeVersions',       // the Compare trades screen — internal, not a merchant surface
  'fixtureApi',          // invented bookings
  'configureForTrade',   // rebuilds the whole merchant from a pack
  'resetToNewMerchant',
  'BASE_LOCATION',       // the fake depot the demo route starts from
]

describe('the preview harness stays out of the app', () => {
  const files = appFiles(SRC)

  it('finds the app source to check', () => {
    // Guards the guard: a broken walk would make every assertion below pass
    // vacuously, which is the worst possible failure for a test like this.
    expect(files.length).toBeGreaterThan(100)
  })

  it('nothing in the app imports from preview/', () => {
    const offenders: string[] = []
    for (const file of files) {
      const text = readFileSync(file, 'utf8')
      if (/from\s+['"](@\/preview\/|\.\.?\/preview\/|\.\/preview\/)/.test(text)) {
        offenders.push(relative(SRC, file))
      }
    }
    expect(offenders, 'move the shared piece out of preview/ instead').toEqual([])
  })

  it('nothing in the app references a harness-only export', () => {
    const offenders: string[] = []
    for (const file of files) {
      const text = readFileSync(file, 'utf8')
      for (const name of HARNESS_ONLY) {
        if (text.includes(name)) offenders.push(`${relative(SRC, file)} → ${name}`)
      }
    }
    expect(offenders, 'Compare trades and the fixtures are internal tools').toEqual([])
  })

  it('the harness owns its own entry point', () => {
    // preview.html is a separate Vite entry built by vite.preview.config.ts.
    // The app's entry is main.tsx and must never route to the harness.
    const appEntry = readFileSync(join(SRC, 'main.tsx'), 'utf8')
    expect(appEntry).not.toContain('preview')
  })
})
