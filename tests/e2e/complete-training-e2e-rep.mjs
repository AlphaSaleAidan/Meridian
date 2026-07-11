// Complete the Training Course for the dedicated e2e rep the same way the
// app does it: authenticated supabase-js writes to the rep's own RLS-scoped
// rows. Unlocks lead creation so the sweep can test the unlocked path.
import { createClient } from 'file:///root/meridian-us-ready/frontend/node_modules/@supabase/supabase-js/dist/index.mjs'
import { readFileSync } from 'node:fs'

const env = Object.fromEntries(
  readFileSync('/root/meridian-us-ready/frontend/.env.local', 'utf8')
    .split('\n').filter(l => l.includes('=')).map(l => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim()])
)
const sb = createClient(env.VITE_SUPABASE_URL, env.VITE_SUPABASE_ANON_KEY)

const EMAIL = 'e2e-usportal-test@meridian.tips'
const { data: auth, error: authErr } = await sb.auth.signInWithPassword({ email: EMAIL, password: 'E2eProbe!2026x' })
if (authErr) { console.error('login failed:', authErr.message); process.exit(1) }

const { data: rep } = await sb.from('sales_reps').select('id, email').eq('email', EMAIL).maybeSingle()
if (!rep) { console.error('no sales_reps row'); process.exit(1) }
const keys = { rep_id: rep.id, rep_email: rep.email.toLowerCase() }

const now = new Date().toISOString()
for (const moduleId of ['master', 'phone', 'pos', 'camera', 'csv']) {
  const { error } = await sb.from('rep_training_progress').upsert({
    ...keys, module_id: moduleId,
    video_watched: true, video_watched_at: now,
    attempts: 1, best_score: 4, passed: true, passed_at: now, updated_at: now,
  }, { onConflict: 'rep_email,module_id' })
  console.log(moduleId, error ? `ERROR: ${error.message}` : 'passed')
}
const { error: sigErr } = await sb.from('rep_conduct_signatures').insert({
  ...keys, signed_name: 'E2E Test Rep', conduct_version: '1.0',
})
console.log('conduct signature:', sigErr ? `ERROR: ${sigErr.message}` : 'signed')
