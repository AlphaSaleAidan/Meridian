import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowRight, ArrowLeft, CheckCircle2, Loader2, Wifi, Store,
  AlertCircle, Clock, Sparkles,
} from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import { useAuth } from '@/lib/auth'
import { supabase, getAuthHeaders } from '@/lib/supabase'

// ── Canada theme (mirrors CanadaCustomerOnboardingWizard) ──
const T = {
  pageBg: 'bg-[#0a0f0d]',
  cardBg: 'bg-[#0f1512]',
  cardBorder: 'border-[#1a2420]',
  inputBg: 'bg-[#0a0f0d]',
  inputBorder: 'border-[#1a2420]',
  accentBg: 'bg-[#00d4aa]',
  accentHover: 'hover:bg-[#00d4aa]/90',
  accentTxt: 'text-[#00d4aa]',
  muted: 'text-[#6b7a74]',
  text: 'text-[#F5F5F7]',
  focusBorder: 'focus:border-[#00d4aa]/50',
} as const

const inputCls = `w-full px-3 py-2.5 text-[13px] rounded-lg ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-[#6b7a74]/40 ${T.focusBorder} focus:outline-none`
const btnPrimary = `flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium ${T.accentBg} text-[#0a0f0d] rounded-lg ${T.accentHover} disabled:opacity-50 transition-colors`
const btnBack = `flex items-center gap-2 px-4 py-2.5 text-[13px] ${T.muted} hover:text-[#F5F5F7] transition-colors`
const cardCls = `rounded-xl p-6 ${T.cardBorder} ${T.cardBg}`

const PROVINCES = [
  'Alberta', 'British Columbia', 'Manitoba', 'New Brunswick', 'Newfoundland and Labrador',
  'Northwest Territories', 'Nova Scotia', 'Nunavut', 'Ontario', 'Prince Edward Island',
  'Quebec', 'Saskatchewan', 'Yukon',
]

type Step = 'welcome' | 'connect' | 'sync' | 'confirm' | 'done'

const STEPS: { key: Step; label: string }[] = [
  { key: 'welcome', label: 'Welcome' },
  { key: 'connect', label: 'Connect POS' },
  { key: 'sync', label: 'First Sync' },
  { key: 'confirm', label: 'Confirm' },
]

const API_BASE = import.meta.env.VITE_API_URL || ''
const RETURN_TO = '/canada/merchant/onboard'
const MERCHANT_HOME = '/canada/merchant'

interface SquareStatus {
  connected: boolean
  merchant_id?: string
  status?: string
  last_sync_at?: string | null
  historical_import_complete?: boolean
}

export default function MerchantOnboardingWizard() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { org } = useAuth()
  const orgId = org?.org_id

  const [step, setStep] = useState<Step>('welcome')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [bootstrapped, setBootstrapped] = useState(false)

  // Sync status (server ground truth — never faked)
  const [status, setStatus] = useState<SquareStatus | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Confirm basics
  const [businessName, setBusinessName] = useState(org?.business_name || '')
  const [province, setProvince] = useState('')

  const progressKey = orgId ? `meridian_merchant_onboard_step_${orgId}` : ''

  const fetchStatus = useCallback(async (): Promise<SquareStatus | null> => {
    if (!orgId) return null
    try {
      const res = await fetch(`${API_BASE}/api/square/status?org_id=${encodeURIComponent(orgId)}`)
      if (!res.ok) return null
      return (await res.json()) as SquareStatus
    } catch {
      return null
    }
  }, [orgId])

  // ── Bootstrap: derive resume point from server truth + OAuth return param ──
  useEffect(() => {
    let cancelled = false
    async function boot() {
      const oauth = searchParams.get('oauth')
      // Clear the oauth param so a refresh doesn't re-trigger
      if (oauth) {
        const cleaned = new URLSearchParams(searchParams)
        cleaned.delete('oauth'); cleaned.delete('merchant_id'); cleaned.delete('error'); cleaned.delete('warning')
        window.history.replaceState({}, '', `${window.location.pathname}${cleaned.toString() ? '?' + cleaned.toString() : ''}`)
      }
      if (oauth === 'denied' || oauth === 'error') {
        if (!cancelled) {
          setError(searchParams.get('error') || 'Square authorization did not complete. You can try again.')
          setStep('connect')
          setBootstrapped(true)
        }
        return
      }

      const st = await fetchStatus()
      if (cancelled) return
      setStatus(st)

      // OAuth just returned successfully, or a connection already exists → resume at sync.
      if (oauth === 'success' || st?.connected) {
        setStep(st?.historical_import_complete ? 'confirm' : 'sync')
        setBootstrapped(true)
        return
      }

      // Otherwise resume the pre-connect step from local progress.
      try {
        const saved = progressKey ? localStorage.getItem(progressKey) : null
        if (saved === 'connect') setStep('connect')
      } catch { /* private browsing */ }
      setBootstrapped(true)
    }
    boot()
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId])

  // Persist pre-connect step locally (server truth covers post-connect)
  useEffect(() => {
    if (!bootstrapped || !progressKey) return
    try { localStorage.setItem(progressKey, step) } catch { /* ignore */ }
  }, [step, bootstrapped, progressKey])

  // ── Poll sync status while on the sync step ──
  useEffect(() => {
    if (step !== 'sync') {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      return
    }
    let active = true
    const tick = async () => {
      const st = await fetchStatus()
      if (active && st) setStatus(st)
    }
    tick()
    pollRef.current = setInterval(tick, 4000)
    return () => { active = false; if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null } }
  }, [step, fetchStatus])

  function startSquareConnect() {
    if (!orgId) { setError('Your account is still being set up — please refresh and try again.'); return }
    setError(null)
    const url = `${API_BASE}/api/square/authorize?org_id=${encodeURIComponent(orgId)}&return_to=${encodeURIComponent(RETURN_TO)}`
    window.location.href = url
  }

  function skipToPortal() {
    // Honest empty portal — no demo or seed data is written.
    navigate(MERCHANT_HOME)
  }

  async function handleConfirm() {
    setSaving(true); setError(null)
    try {
      if (supabase && orgId) {
        if (businessName.trim() && businessName.trim() !== org?.business_name) {
          await supabase.from('organizations').update({ name: businessName.trim() }).eq('id', orgId)
        }
        if (province) {
          // Constraint-agnostic upsert: update the existing primary location if
          // present, otherwise insert. Avoids depending on a named unique index.
          const { data: existing } = await supabase
            .from('business_locations')
            .select('id')
            .eq('business_id', orgId)
            .eq('is_primary', true)
            .limit(1)
          if (existing && existing.length > 0) {
            await supabase.from('business_locations').update({ state: province }).eq('id', existing[0].id)
          } else {
            await supabase.from('business_locations').insert({
              business_id: orgId,
              name: 'Primary',
              state: province,
              is_primary: true,
            })
          }
        }
      }
      try { if (progressKey) localStorage.removeItem(progressKey) } catch { /* ignore */ }
      setStep('done')
    } catch (err: any) {
      setError(err?.message || 'Could not save your details — please try again.')
    } finally {
      setSaving(false)
    }
  }

  const currentStepIdx = STEPS.findIndex(s => s.key === step)
  const syncStarted = !!(status?.last_sync_at) || !!status?.historical_import_complete

  return (
    <div className={`min-h-screen ${T.pageBg} flex flex-col items-center px-4 py-8`}>
      <div className="w-full max-w-xl">
        {/* Logo */}
        <div className="flex flex-col items-center gap-1 mb-6">
          <div className="flex items-center gap-2.5">
            <MeridianEmblem size={32} />
            <MeridianWordmark className="text-lg" />
          </div>
          <span className="text-[10px] font-semibold text-[#00d4aa] uppercase tracking-widest">Canada</span>
        </div>

        {/* Progress */}
        {step !== 'done' && (
          <div className="flex items-center gap-1 mb-8">
            {STEPS.map((s, i) => {
              const isActive = i === currentStepIdx
              const isDone = i < currentStepIdx
              return (
                <div key={s.key} className="flex-1 flex flex-col gap-1.5">
                  <div className={`h-1 rounded-full transition-all duration-500 ${isDone || isActive ? 'bg-[#00d4aa]' : 'bg-[#1a2420]'}`} />
                  <span className={`text-[9px] font-medium text-center ${isActive ? 'text-[#F5F5F7]' : isDone ? 'text-[#00d4aa]' : 'text-[#6b7a74]/30'}`}>
                    {s.label}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[13px] flex items-center gap-2">
            <AlertCircle size={14} /> {error}
          </div>
        )}

        {!bootstrapped ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="text-[#00d4aa] animate-spin" />
          </div>
        ) : (
          <>
            {/* ═══ Welcome ═══ */}
            {step === 'welcome' && (
              <div className="space-y-5">
                <div className="text-center">
                  <h1 className={`text-2xl font-bold ${T.text}`}>
                    Welcome{org?.business_name ? `, ${org.business_name}` : ''}
                  </h1>
                  <p className={`text-[13px] ${T.muted} mt-2 max-w-md mx-auto`}>
                    Meridian turns your point-of-sale data into inventory, scheduling, and
                    phone-order intelligence. Connect your POS once and your dashboard fills in
                    automatically — no spreadsheets, no manual entry.
                  </p>
                </div>
                <div className={`${cardCls} space-y-3`}>
                  {[
                    'Connect your point-of-sale in one click',
                    'We import your sales history securely',
                    'Your three pillars come to life: Inventory, Schedule, Phone Calls',
                  ].map((line, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-full bg-[#00d4aa]/10 flex items-center justify-center flex-shrink-0">
                        <span className="text-[11px] font-bold text-[#00d4aa]">{i + 1}</span>
                      </div>
                      <span className={`text-[13px] ${T.text}`}>{line}</span>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end">
                  <button onClick={() => setStep('connect')} className={btnPrimary}>
                    Get Started <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            )}

            {/* ═══ Connect POS ═══ */}
            {step === 'connect' && (
              <div className="space-y-5">
                <div className="text-center">
                  <h1 className={`text-xl font-bold ${T.text}`}>Connect Your POS</h1>
                  <p className={`text-[13px] ${T.muted} mt-1`}>
                    We'll securely import your transaction history to start generating insights.
                  </p>
                </div>

                {/* Square — live, one-click OAuth */}
                <button
                  onClick={startSquareConnect}
                  className={`w-full ${cardCls} flex items-center gap-4 text-left hover:border-[#00d4aa]/40 transition-colors`}
                >
                  <div className="w-11 h-11 rounded-lg bg-[#006AFF]/10 flex items-center justify-center flex-shrink-0">
                    <Wifi size={20} className="text-[#006AFF]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-[14px] font-semibold ${T.text}`}>Connect Square</p>
                    <p className={`text-[11px] ${T.muted}`}>One-click secure authorization — no API keys needed</p>
                  </div>
                  <ArrowRight size={16} className={T.accentTxt} />
                </button>

                {/* Clover — gated, coming soon */}
                <div className={`w-full ${cardCls} flex items-center gap-4 opacity-60`}>
                  <div className="w-11 h-11 rounded-lg bg-[#1DC167]/10 flex items-center justify-center flex-shrink-0">
                    <Store size={20} className="text-[#1DC167]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-[14px] font-semibold ${T.text}`}>Clover</p>
                    <p className={`text-[11px] ${T.muted}`}>We'll let you know when it's ready</p>
                  </div>
                  <span className="text-[10px] px-2.5 py-1 rounded-full bg-[#1a2420] text-[#6b7a74] font-medium flex items-center gap-1">
                    <Clock size={10} /> Coming soon
                  </span>
                </div>

                <div className="flex justify-between items-center pt-1">
                  <button onClick={() => setStep('welcome')} className={btnBack}>
                    <ArrowLeft size={14} /> Back
                  </button>
                  <button onClick={skipToPortal} className={`text-[12px] ${T.muted} hover:text-[#F5F5F7] transition-colors`}>
                    Skip for now
                  </button>
                </div>
              </div>
            )}

            {/* ═══ First Sync ═══ */}
            {step === 'sync' && (
              <div className="space-y-5">
                <div className="text-center">
                  <h1 className={`text-xl font-bold ${T.text}`}>
                    {syncStarted ? 'Your Data Is Importing' : 'Finishing the Connection'}
                  </h1>
                  <p className={`text-[13px] ${T.muted} mt-1`}>
                    {status?.connected
                      ? 'Square is connected. We\'re pulling in your sales history now.'
                      : 'Waiting for Square to confirm the connection…'}
                  </p>
                </div>

                <div className={`${cardCls} space-y-4`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center ${status?.connected ? 'bg-[#00d4aa]/15' : 'bg-[#1a2420]'}`}>
                      {status?.connected
                        ? <CheckCircle2 size={18} className={T.accentTxt} />
                        : <Loader2 size={18} className="text-[#6b7a74] animate-spin" />}
                    </div>
                    <div>
                      <p className={`text-[13px] font-medium ${T.text}`}>Square connection</p>
                      <p className={`text-[11px] ${T.muted}`}>
                        {status?.connected
                          ? `Connected${status.merchant_id ? ` · ${status.merchant_id}` : ''}`
                          : 'Pending…'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center ${status?.historical_import_complete ? 'bg-[#00d4aa]/15' : syncStarted ? 'bg-[#00d4aa]/10' : 'bg-[#1a2420]'}`}>
                      {status?.historical_import_complete
                        ? <CheckCircle2 size={18} className={T.accentTxt} />
                        : syncStarted
                          ? <Loader2 size={18} className="text-[#00d4aa] animate-spin" />
                          : <Sparkles size={18} className="text-[#6b7a74]" />}
                    </div>
                    <div>
                      <p className={`text-[13px] font-medium ${T.text}`}>Sales history import</p>
                      <p className={`text-[11px] ${T.muted}`}>
                        {status?.historical_import_complete
                          ? 'Import complete'
                          : syncStarted
                            ? 'Importing in the background — this can take a few minutes'
                            : 'Starts automatically once connected'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg p-3 bg-[#00d4aa]/5 border border-[#00d4aa]/15">
                  <p className={`text-[11px] ${T.muted} leading-relaxed`}>
                    You don't need to wait here — the import keeps running in the background.
                    Continue setup and your dashboard will keep filling in.
                  </p>
                </div>

                <div className="flex justify-between items-center">
                  <button onClick={() => setStep('connect')} className={btnBack}>
                    <ArrowLeft size={14} /> Back
                  </button>
                  <button
                    onClick={() => setStep('confirm')}
                    disabled={!status?.connected}
                    className={btnPrimary}
                  >
                    Continue <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            )}

            {/* ═══ Confirm basics ═══ */}
            {step === 'confirm' && (
              <div className="space-y-5">
                <div className="text-center">
                  <h1 className={`text-xl font-bold ${T.text}`}>Confirm Your Basics</h1>
                  <p className={`text-[13px] ${T.muted} mt-1`}>
                    A couple of details so your dashboard reads right.
                  </p>
                </div>
                <div className={`${cardCls} space-y-4`}>
                  <div>
                    <label className={`block text-[11px] font-medium ${T.muted} mb-1.5`}>Business Name</label>
                    <input
                      type="text"
                      value={businessName}
                      onChange={e => setBusinessName(e.target.value)}
                      placeholder="Your business name"
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={`block text-[11px] font-medium ${T.muted} mb-1.5`}>Province</label>
                    <select value={province} onChange={e => setProvince(e.target.value)} className={inputCls}>
                      <option value="">Select province…</option>
                      {PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <button onClick={() => setStep('sync')} className={btnBack}>
                    <ArrowLeft size={14} /> Back
                  </button>
                  <button onClick={handleConfirm} disabled={saving} className={btnPrimary}>
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                    {saving ? 'Saving…' : 'Finish Setup'} <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            )}

            {/* ═══ Done ═══ */}
            {step === 'done' && (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="w-20 h-20 rounded-full bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center mb-6">
                  <CheckCircle2 size={40} className={T.accentTxt} />
                </div>
                <h2 className={`text-2xl font-bold ${T.text} mb-2`}>You're All Set!</h2>
                <p className={`text-[14px] ${T.muted} text-center max-w-sm mb-8`}>
                  Your dashboard is live. As your sales history finishes importing, your
                  inventory, schedule, and phone-call insights keep filling in.
                </p>
                <button
                  onClick={() => navigate(MERCHANT_HOME)}
                  className={`flex items-center gap-2 px-8 py-3 text-[14px] font-medium text-[#0a0f0d] ${T.accentBg} rounded-lg ${T.accentHover} transition-colors shadow-[0_0_30px_rgba(0,212,170,0.2)]`}
                >
                  Go to Dashboard <ArrowRight size={16} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
