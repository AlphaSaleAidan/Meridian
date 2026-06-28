import { useMemo, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Calendar, Check, Clock, Loader2 } from 'lucide-react'

import ScrollReveal from './ScrollReveal'
import MagneticButton from './MagneticButton'

const EASE = [0.16, 1, 0.3, 1] as const
const API_BASE = import.meta.env.VITE_API_URL || ''

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PHONE_RE = /^\+?[1-9]\d{7,14}$/

const WINDOWS = [
  { value: 'morning', label: 'Morning (8am–12pm)' },
  { value: 'afternoon', label: 'Afternoon (12pm–5pm)' },
  { value: 'evening', label: 'Evening (5pm–8pm)' },
]

interface DateOption {
  value: string
  label: string
}

interface Props {
  /** Primary accent (hex). */
  accent: string
  /** Secondary accent for the gradient flourish (hex). Defaults to accent. */
  accentSecondary?: string
  /** Where the lead came from — persisted server-side. */
  source: string
  /** Optional pricing-floor note rendered near the CTA (e.g. "Plans from CA$350/mo"). */
  priceNote?: string
  /** Optional heading override. */
  heading?: ReactNode
}

interface FormState {
  full_name: string
  business_name: string
  email: string
  phone: string
  preferred_date: string
  preferred_window: string
  notes: string
  company_website: string // honeypot
}

/** Build "today" + "tomorrow" date options from the visitor's local clock. */
function buildDateOptions(): DateOption[] {
  const fmt = new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
  const today = new Date()
  const tomorrow = new Date()
  tomorrow.setDate(today.getDate() + 1)
  const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return [
    { value: iso(today), label: `Today · ${fmt.format(today)}` },
    { value: iso(tomorrow), label: `Tomorrow · ${fmt.format(tomorrow)}` },
  ]
}

export default function ScheduleQuote({
  accent,
  accentSecondary,
  source,
  priceNote,
  heading,
}: Props) {
  const accent2 = accentSecondary || accent
  const dateOptions = useMemo(buildDateOptions, [])

  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState<FormState>({
    full_name: '',
    business_name: '',
    email: '',
    phone: '',
    preferred_date: dateOptions[0].value,
    preferred_window: WINDOWS[0].value,
    notes: '',
    company_website: '',
  })

  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm(prev => ({ ...prev, [k]: e.target.value }))

  const validate = (): string => {
    if (!form.full_name.trim()) return 'Please enter your full name.'
    if (!form.business_name.trim()) return 'Please enter your business name.'
    if (!EMAIL_RE.test(form.email.trim())) return 'Please enter a valid email address.'
    if (!PHONE_RE.test(form.phone.replace(/[\s\-().]/g, ''))) return 'Please enter a valid phone number.'
    if (!form.preferred_date) return 'Please choose a preferred date.'
    if (!form.preferred_window) return 'Please choose a preferred time window.'
    return ''
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const msg = validate()
    if (msg) {
      setError(msg)
      return
    }
    setError('')
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/quote-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, source }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setSubmitted(true)
    } catch {
      setError('Something went wrong sending your request. Please try again or email us directly.')
    } finally {
      setSubmitting(false)
    }
  }

  const inputCls =
    'w-full rounded-lg bg-[#0A0A0B] border border-[#1F1F23] px-3.5 py-2.5 text-[14px] text-[#F5F5F7] placeholder-[#A1A1A8]/40 outline-none transition-colors focus:border-[#2A2A30]'
  const labelCls = 'block text-[12px] font-medium text-[#A1A1A8] mb-1.5'

  return (
    <section id="quote" className="py-24 border-t border-[#1F1F23]/40 relative overflow-hidden">
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 aurora-glow"
        style={{ width: 600, height: 600, opacity: 0.08, background: `radial-gradient(circle, ${accent} 0%, transparent 70%)` }}
      />
      <div className="max-w-2xl mx-auto px-6 relative">
        <ScrollReveal className="text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight">
            {heading || (
              <>
                Schedule a{' '}
                <em className="font-serif italic font-normal bg-clip-text text-transparent" style={{ backgroundImage: `linear-gradient(to right, ${accent}, ${accent2})` }}>
                  Quote
                </em>
              </>
            )}
          </h2>
          <p className="mt-4 text-[#A1A1A8] text-[15px] leading-relaxed max-w-md mx-auto">
            Every business is different — so is every quote. Tell us when to call and a
            specialist will reach out <span className="text-[#F5F5F7]">within the next 48 hours</span>.
          </p>
          {priceNote && (
            <p className="mt-3 text-[13px] text-[#A1A1A8]/70">{priceNote}</p>
          )}
        </ScrollReveal>

        {/* Success state */}
        <AnimatePresence mode="wait">
          {submitted ? (
            <motion.div
              key="success"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: EASE }}
              className="mt-10 rounded-2xl border border-[#1F1F23] bg-[#111113] p-8 text-center"
            >
              <div className="flex justify-center mb-4">
                <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: `${accent}1A` }}>
                  <Check size={22} style={{ color: accent }} />
                </div>
              </div>
              <h3 className="text-[#F5F5F7] font-semibold text-lg">Thanks — we'll call you within your window.</h3>
              <p className="mt-2 text-[#A1A1A8] text-[14px] leading-relaxed max-w-sm mx-auto">
                Your request is in. A Meridian specialist will reach out within the next 48 hours
                to walk you through a quote tailored to your business.
              </p>
            </motion.div>
          ) : open ? (
            <motion.form
              key="form"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.5, ease: EASE }}
              onSubmit={handleSubmit}
              className="mt-10 rounded-2xl border border-[#1F1F23] bg-[#111113] p-6 md:p-8 overflow-hidden"
              noValidate
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls} htmlFor="sq-name">Full name</label>
                  <input id="sq-name" className={inputCls} value={form.full_name} onChange={set('full_name')} placeholder="Jane Doe" autoComplete="name" />
                </div>
                <div>
                  <label className={labelCls} htmlFor="sq-biz">Business name</label>
                  <input id="sq-biz" className={inputCls} value={form.business_name} onChange={set('business_name')} placeholder="Sunrise Coffee Co." autoComplete="organization" />
                </div>
                <div>
                  <label className={labelCls} htmlFor="sq-email">Email</label>
                  <input id="sq-email" type="email" className={inputCls} value={form.email} onChange={set('email')} placeholder="jane@business.com" autoComplete="email" />
                </div>
                <div>
                  <label className={labelCls} htmlFor="sq-phone">Phone</label>
                  <input id="sq-phone" type="tel" className={inputCls} value={form.phone} onChange={set('phone')} placeholder="+1 (555) 123-4567" autoComplete="tel" />
                </div>
                <div>
                  <label className={labelCls} htmlFor="sq-date">
                    <span className="inline-flex items-center gap-1.5"><Calendar size={12} /> Preferred date</span>
                  </label>
                  <select id="sq-date" className={inputCls} value={form.preferred_date} onChange={set('preferred_date')}>
                    {dateOptions.map(d => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={labelCls} htmlFor="sq-window">
                    <span className="inline-flex items-center gap-1.5"><Clock size={12} /> Preferred time</span>
                  </label>
                  <select id="sq-window" className={inputCls} value={form.preferred_window} onChange={set('preferred_window')}>
                    {WINDOWS.map(w => (
                      <option key={w.value} value={w.value}>{w.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4">
                <label className={labelCls} htmlFor="sq-notes">Anything we should know? <span className="text-[#A1A1A8]/40">(optional)</span></label>
                <textarea id="sq-notes" className={`${inputCls} resize-none`} rows={3} value={form.notes} onChange={set('notes')} placeholder="POS system, number of locations, what you're hoping to improve…" />
              </div>

              {/* Honeypot — hidden from real users; bots fill it in. */}
              <div aria-hidden="true" className="absolute -left-[9999px] top-0 h-0 w-0 overflow-hidden">
                <label htmlFor="sq-company-website">Company website</label>
                <input
                  id="sq-company-website"
                  type="text"
                  tabIndex={-1}
                  autoComplete="off"
                  value={form.company_website}
                  onChange={set('company_website')}
                />
              </div>

              {error && <p className="mt-4 text-[13px] text-[#F87171]">{error}</p>}

              <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
                <button
                  type="submit"
                  disabled={submitting}
                  className="group w-full sm:w-auto px-6 py-3 text-[14px] font-medium text-white rounded-lg transition-all duration-300 inline-flex items-center justify-center gap-2 hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed"
                  style={{ backgroundColor: accent, boxShadow: `0 0 32px ${accent}30` }}
                >
                  {submitting ? (
                    <><Loader2 size={15} className="animate-spin" /> Sending…</>
                  ) : (
                    <>Request my call <ArrowRight size={15} className="transition-transform duration-300 group-hover:translate-x-0.5" /></>
                  )}
                </button>
                <p className="text-[12px] text-[#A1A1A8]/50">No obligation · We'll call within 48 hours</p>
              </div>
            </motion.form>
          ) : (
            <motion.div
              key="cta"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4, ease: EASE }}
              className="mt-10 flex justify-center"
            >
              <MagneticButton
                onClick={() => setOpen(true)}
                className="group px-8 py-3.5 text-[15px] font-medium text-white rounded-lg transition-all duration-300 inline-flex items-center gap-2 hover:brightness-110"
                style={{ backgroundColor: accent, boxShadow: `0 0 40px ${accent}35` }}
              >
                Schedule a Quote
                <ArrowRight size={16} className="transition-transform duration-300 group-hover:translate-x-0.5" />
              </MagneticButton>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  )
}
