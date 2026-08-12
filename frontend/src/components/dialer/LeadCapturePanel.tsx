// Capture: get numbers INTO the dialing pool so reps open the tab and start
// calling. Two modes — add one lead, or paste a list (one lead per line:
// business, phone, POS, contact, city, est $/mo). Both land in
// canada_phone_leads via the backend; the queue refreshes.
import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Plus, Upload, X } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { dialerApi, type PhoneLeadInput } from '@/lib/dialer-api'

interface Props {
  open: boolean
  onClose: () => void
}

type Mode = 'one' | 'import'

// "Business, +1..., square, Contact, City, 420" -> PhoneLeadInput
function parseLine(line: string): PhoneLeadInput | null {
  const parts = line.split(/[\t,]/).map(s => s.trim())
  const phone = parts.find(p => /[+(]?\d[\d\s\-().]{6,}/.test(p))
  if (!phone) return null
  const [business, , posMaybe, contact, city, dollars] = parts
  const pos = ['square', 'clover', 'toast', 'lightspeed', 'shopify', 'none']
    .includes((posMaybe || '').toLowerCase()) ? (posMaybe || '').toLowerCase() : 'unknown'
  return {
    business_name: business || '',
    phone,
    pos_system: pos,
    contact_name: contact || '',
    city: city || '',
    est_monthly_value: dollars ? Math.round(Number(dollars.replace(/[^\d]/g, '')) * 100) : 0,
  }
}

export function LeadCapturePanel({ open, onClose }: Props) {
  const reduceMotion = useReducedMotion()
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<Mode>('one')
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  // single
  const [biz, setBiz] = useState('')
  const [phone, setPhone] = useState('')
  const [contact, setContact] = useState('')
  const [pos, setPos] = useState('unknown')
  const [city, setCity] = useState('')
  const [value, setValue] = useState('')
  // import
  const [source, setSource] = useState('')
  const [paste, setPaste] = useState('')

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['dialer', 'queue'] })

  const addOne = async () => {
    if (!phone.trim()) { setErr('A phone number is required'); return }
    setSaving(true); setErr(null); setResult(null)
    try {
      await dialerApi.createLead({
        business_name: biz, phone, contact_name: contact, pos_system: pos, city,
        est_monthly_value: value ? Math.round(Number(value) * 100) : 0,
      })
      setResult('Added to your queue.')
      setBiz(''); setPhone(''); setContact(''); setCity(''); setValue(''); setPos('unknown')
      refresh()
    } catch (e) { setErr(e instanceof Error ? e.message : 'Could not add') }
    finally { setSaving(false) }
  }

  const doImport = async () => {
    const leads = paste.split('\n').map(parseLine).filter(Boolean) as PhoneLeadInput[]
    if (leads.length === 0) { setErr('No valid rows found (each row needs a phone number)'); return }
    setSaving(true); setErr(null); setResult(null)
    try {
      const r = await dialerApi.importLeads(source || 'import', leads)
      setResult(`Imported ${r.imported}. Skipped ${r.skipped_duplicate} duplicate, ${r.skipped_invalid} invalid.`)
      setPaste('')
      refresh()
    } catch (e) { setErr(e instanceof Error ? e.message : 'Import failed') }
    finally { setSaving(false) }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="capture-overlay"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: reduceMotion ? 0.01 : 0.16 }}
          className="fixed inset-0 z-[75] bg-black/60 flex items-start justify-end p-4"
          onClick={onClose}
        >
          <motion.div
            key="capture-drawer"
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 24 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 380, damping: 34 } }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 24, transition: { duration: 0.14 } }}
            onClick={e => e.stopPropagation()}
            role="dialog" aria-modal="true" aria-label="Add leads"
            className="w-full max-w-md bg-pm-canada-surface border border-pm-canada-border rounded-2xl shadow-[0_24px_64px_-12px_rgba(0,0,0,0.7)] overflow-hidden"
          >
            <div className="px-5 py-3 border-b border-pm-canada-border flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Add leads to your queue</h2>
              <button onClick={onClose} aria-label="Close" className="text-pm-canada-text-faint hover:text-white"><X size={16} /></button>
            </div>

            <div className="px-5 pt-3 flex gap-1.5">
              {(['one', 'import'] as Mode[]).map(m => (
                <button
                  key={m} onClick={() => { setMode(m); setErr(null); setResult(null) }}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    mode === m ? 'bg-pm-accent/10 text-pm-accent border border-pm-accent/30'
                      : 'text-pm-canada-text-muted border border-transparent hover:text-white'
                  }`}
                >
                  {m === 'one' ? <Plus size={13} /> : <Upload size={13} />}
                  {m === 'one' ? 'Add one' : 'Import list'}
                </button>
              ))}
            </div>

            <div className="p-5 space-y-3">
              {mode === 'one' ? (
                <>
                  <Field label="Business"><input value={biz} onChange={e => setBiz(e.target.value)} className={inputCls} placeholder="Aloha Poke" /></Field>
                  <Field label="Phone *"><input value={phone} onChange={e => setPhone(e.target.value)} className={inputCls} placeholder="+1 808 555 0100" /></Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Contact"><input value={contact} onChange={e => setContact(e.target.value)} className={inputCls} placeholder="Kai" /></Field>
                    <Field label="POS">
                      <select value={pos} onChange={e => setPos(e.target.value)} className={inputCls}>
                        {['unknown', 'square', 'clover', 'toast', 'lightspeed', 'shopify', 'none'].map(p => (
                          <option key={p} value={p}>{p === 'none' ? 'No POS' : p === 'unknown' ? 'Unknown' : p[0].toUpperCase() + p.slice(1)}</option>
                        ))}
                      </select>
                    </Field>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="City"><input value={city} onChange={e => setCity(e.target.value)} className={inputCls} placeholder="Honolulu" /></Field>
                    <Field label="Est. $/mo"><input value={value} onChange={e => setValue(e.target.value)} className={inputCls} placeholder="420" inputMode="numeric" /></Field>
                  </div>
                  <button onClick={addOne} disabled={saving} className={primaryCls}>
                    <Plus size={15} />{saving ? 'Adding…' : 'Add to queue'}
                  </button>
                </>
              ) : (
                <>
                  <Field label="List name"><input value={source} onChange={e => setSource(e.target.value)} className={inputCls} placeholder="BC restaurants — Aug" /></Field>
                  <Field label="Paste rows — one per line">
                    <textarea
                      value={paste} onChange={e => setPaste(e.target.value)} rows={7}
                      placeholder={'Business, +1 604 555 0100, square, Contact, Vancouver, 420\nDiamond Cafe, 604-555-0102, clover, Leilani, Burnaby, 310'}
                      className={`${inputCls} resize-none font-mono text-2xs`}
                    />
                  </Field>
                  <p className="text-2xs text-pm-canada-text-faint">
                    Columns: business, phone (required), POS, contact, city, est $/mo. Commas or tabs. Duplicates are skipped.
                  </p>
                  <button onClick={doImport} disabled={saving} className={primaryCls}>
                    <Upload size={15} />{saving ? 'Importing…' : 'Import list'}
                  </button>
                </>
              )}

              {result && <p className="text-2xs text-pm-accent">{result}</p>}
              {err && <p className="text-2xs text-red-400">{err}</p>}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

const inputCls = 'w-full rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2 text-sm text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50'
const primaryCls = 'w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-pm-accent text-pm-canada-bg text-sm font-semibold hover:bg-pm-accent/90 active:scale-[0.98] disabled:opacity-60 transition-[background-color,transform]'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  )
}
