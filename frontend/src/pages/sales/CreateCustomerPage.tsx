import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, CheckCircle2, Copy, Send,
  Store, User, Mail, Phone, DollarSign, Tag,
} from 'lucide-react'
import { MeridianEmblem } from '@/components/MeridianLogo'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase } from '@/lib/supabase'

type Step = 'details' | 'plan' | 'confirm' | 'link'

const PLANS = [
  { id: 'insights', label: 'Insights', price: 500, desc: 'Core analytics + AI recommendations' },
  { id: 'optimize', label: 'Optimize', price: 750, desc: '+ Forecasting + smart notifications' },
  { id: 'command', label: 'Command', price: 1000, desc: '+ Benchmarking + what-if simulator' },
]

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

function generateToken(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
  let token = ''
  for (let i = 0; i < 24; i++) {
    token += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return token
}

export default function CreateCustomerPage() {
  const navigate = useNavigate()
  const { rep } = useSalesAuth()
  const [step, setStep] = useState<Step>('details')
  const [saving, setSaving] = useState(false)
  const [copied, setCopied] = useState(false)
  const [onboardingLink, setOnboardingLink] = useState('')
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState({
    businessName: '',
    ownerName: '',
    email: '',
    phone: '',
    vertical: '',
    plan: 'insights',
    customPrice: '',
    notes: '',
  })

  function update(key: string, value: string) {
    setForm(f => ({ ...f, [key]: value }))
    setError(null)
  }

  const selectedPlan = PLANS.find(p => p.id === form.plan) || PLANS[0]
  const price = form.customPrice ? parseInt(form.customPrice) : selectedPlan.price

  function validateDetails(): boolean {
    if (!form.businessName.trim()) { setError('Business name is required'); return false }
    if (!form.ownerName.trim()) { setError('Owner name is required'); return false }
    if (!form.email.trim()) { setError('Email is required'); return false }
    if (!form.phone.trim()) { setError('Phone number is required'); return false }
    return true
  }

  function goToConfirm() {
    setStep('confirm')
  }

  async function handleConfirm() {
    setSaving(true)
    setError(null)

    try {
      const token = generateToken()
      const businessId = uuid()

      if (supabase) {
        // Create the business record
        const { error: bizErr } = await supabase.from('organizations').insert({
          id: businessId,
          name: form.businessName,
          owner_name: form.ownerName,
          email: form.email,
          phone: form.phone,
          industry: form.vertical || null,
          plan_tier: form.plan,
          monthly_price: price,
          onboarded: false,
          created_by_rep: rep?.rep_id || null,
          access_token: token,
          pos_connected: false,
        })
        if (bizErr) throw new Error(bizErr.message)

        // Create a deal in the leads pipeline
        const { error: dealErr } = await supabase.from('deals').insert({
          id: uuid(),
          business_name: form.businessName,
          contact_name: form.ownerName,
          contact_email: form.email,
          contact_phone: form.phone,
          vertical: form.vertical || 'Other',
          stage: 'proposal_sent',
          monthly_value: price * 100,
          commission_rate: rep?.commission_rate || 35,
          notes: form.notes || `Created via Sales Portal. Plan: ${selectedPlan.label} at $${price}/mo`,
          rep_id: rep?.rep_id || null,
        })
        if (dealErr) console.warn('Deal creation warning:', dealErr.message)
      } else {
        // Local/demo mode — store in localStorage
        const existing = JSON.parse(localStorage.getItem('meridian_pending_customers') || '[]')
        existing.push({
          id: businessId,
          token,
          ...form,
          price,
          plan: selectedPlan.label,
          repId: rep?.rep_id,
          repName: rep?.name,
          createdAt: new Date().toISOString(),
        })
        localStorage.setItem('meridian_pending_customers', JSON.stringify(existing))
      }

      const link = `${window.location.origin}/onboard?token=${token}&biz=${encodeURIComponent(form.businessName)}&name=${encodeURIComponent(form.ownerName)}&email=${encodeURIComponent(form.email)}&phone=${encodeURIComponent(form.phone)}`
      setOnboardingLink(link)
      setStep('link')
    } catch (err: any) {
      setError(err.message || 'Failed to create customer')
    } finally {
      setSaving(false)
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(onboardingLink)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback
      const input = document.createElement('input')
      input.value = onboardingLink
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  function sendViaSms() {
    const msg = `Hey ${form.ownerName.split(' ')[0]}! Here's your Meridian setup link — takes about 3 minutes to get your analytics live: ${onboardingLink}`
    window.open(`sms:${form.phone}?body=${encodeURIComponent(msg)}`, '_blank')
  }

  const verticals = ['Restaurant', 'Café', 'Bar', 'Smoke Shop', 'Boutique', 'Salon', 'Food Truck', 'Convenience Store', 'Other']

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => step === 'details' ? navigate('/sales/leads') : setStep(step === 'confirm' ? 'plan' : step === 'plan' ? 'details' : 'details')}
          className="p-2 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F7]">New Customer</h1>
          <p className="text-[12px] text-[#A1A1A8]">Create an account and generate their onboarding link</p>
        </div>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-1 mb-8">
        {['Business Details', 'Select Plan', 'Confirm & Price', 'Send Link'].map((label, i) => {
          const steps: Step[] = ['details', 'plan', 'confirm', 'link']
          const currentIdx = steps.indexOf(step)
          const isActive = i === currentIdx
          const isDone = i < currentIdx
          return (
            <div key={label} className="flex-1 flex flex-col gap-1.5">
              <div className={`h-1 rounded-full transition-colors duration-300 ${isDone ? 'bg-[#17C5B0]' : isActive ? 'bg-[#1A8FD6]' : 'bg-[#1F1F23]'}`} />
              <span className={`text-[10px] font-medium ${isActive ? 'text-[#F5F5F7]' : isDone ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/40'}`}>
                {label}
              </span>
            </div>
          )
        })}
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[13px]">
          {error}
        </div>
      )}

      {/* Step 1: Business Details */}
      {step === 'details' && (
        <div className="space-y-4">
          <div className="card p-6 border border-[#1F1F23] space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Store size={16} className="text-[#1A8FD6]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Business Information</h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Business Name *</label>
                <input
                  type="text"
                  value={form.businessName}
                  onChange={e => update('businessName', e.target.value)}
                  placeholder="e.g. Lucky Dragon Kitchen"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Business Type</label>
                <select
                  value={form.vertical}
                  onChange={e => update('vertical', e.target.value)}
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] focus:border-[#1A8FD6]/50 focus:outline-none transition-colors"
                >
                  <option value="">Select type...</option>
                  {verticals.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2 mt-6 mb-2">
              <User size={16} className="text-[#17C5B0]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Owner Contact</h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Owner Name *</label>
                <input
                  type="text"
                  value={form.ownerName}
                  onChange={e => update('ownerName', e.target.value)}
                  placeholder="e.g. James Chen"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Email *</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={e => update('email', e.target.value)}
                  placeholder="james@luckydragon.com"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Phone *</label>
                <input
                  type="tel"
                  value={form.phone}
                  onChange={e => update('phone', e.target.value)}
                  placeholder="(555) 234-5678"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div className="mt-2">
              <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Notes (optional)</label>
              <textarea
                value={form.notes}
                onChange={e => update('notes', e.target.value)}
                placeholder="Any notes about this business..."
                rows={2}
                className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none transition-colors resize-none"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={() => validateDetails() && setStep('plan')}
              className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors"
            >
              Next: Select Plan <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Plan Selection */}
      {step === 'plan' && (
        <div className="space-y-4">
          <div className="card p-6 border border-[#1F1F23]">
            <div className="flex items-center gap-2 mb-4">
              <Tag size={16} className="text-[#1A8FD6]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Select Plan for {form.businessName}</h2>
            </div>

            <div className="grid gap-3">
              {PLANS.map(plan => (
                <button
                  key={plan.id}
                  onClick={() => update('plan', plan.id)}
                  className={`p-4 rounded-lg border text-left transition-all duration-200 ${
                    form.plan === plan.id
                      ? 'border-[#1A8FD6]/50 bg-[#1A8FD6]/10'
                      : 'border-[#1F1F23] hover:border-[#2A2A2E] bg-[#0A0A0B]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[14px] font-semibold text-[#F5F5F7]">{plan.label}</p>
                      <p className="text-[12px] text-[#A1A1A8] mt-0.5">{plan.desc}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-[#F5F5F7]">${plan.price}</p>
                      <p className="text-[10px] text-[#A1A1A8]">/month</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-4">
              <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Custom Price (optional override)</label>
              <div className="relative">
                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
                <input
                  type="number"
                  value={form.customPrice}
                  onChange={e => update('customPrice', e.target.value)}
                  placeholder={selectedPlan.price.toString()}
                  className="w-full pl-8 pr-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none transition-colors"
                />
              </div>
              <p className="text-[10px] text-[#A1A1A8]/40 mt-1">Leave blank to use standard pricing</p>
            </div>
          </div>

          <div className="flex justify-between">
            <button
              onClick={() => setStep('details')}
              className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
            >
              <ArrowLeft size={14} /> Back
            </button>
            <button
              onClick={goToConfirm}
              className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors"
            >
              Next: Confirm <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Confirm */}
      {step === 'confirm' && (
        <div className="space-y-4">
          <div className="card p-6 border border-[#17C5B0]/30 bg-[#17C5B0]/5">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 size={18} className="text-[#17C5B0]" />
              <h2 className="text-[15px] font-semibold text-[#F5F5F7]">Confirm Customer Setup</h2>
            </div>

            <div className="space-y-3 text-[13px]">
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Business</span>
                <span className="text-[#F5F5F7] font-medium">{form.businessName}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Owner</span>
                <span className="text-[#F5F5F7] font-medium">{form.ownerName}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Email</span>
                <span className="text-[#F5F5F7] font-medium">{form.email}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Phone</span>
                <span className="text-[#F5F5F7] font-medium">{form.phone}</span>
              </div>
              {form.vertical && (
                <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                  <span className="text-[#A1A1A8]">Type</span>
                  <span className="text-[#F5F5F7] font-medium">{form.vertical}</span>
                </div>
              )}
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Plan</span>
                <span className="text-[#F5F5F7] font-medium">{selectedPlan.label}</span>
              </div>
              <div className="flex justify-between py-3">
                <span className="text-[#A1A1A8] font-medium">Monthly Price</span>
                <span className="text-lg font-bold text-[#17C5B0]">${price}/mo</span>
              </div>
            </div>

            {rep && (
              <div className="mt-3 pt-3 border-t border-[#1F1F23]">
                <p className="text-[11px] text-[#A1A1A8]">
                  Signed up by <span className="text-[#F5F5F7] font-medium">{rep.name}</span> •
                  Commission: <span className="text-[#17C5B0] font-medium">{rep.commission_rate}%</span> =
                  <span className="text-[#17C5B0] font-medium"> ${Math.round(price * (rep.commission_rate / 100))}/mo</span>
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-between">
            <button
              onClick={() => setStep('plan')}
              className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
            >
              <ArrowLeft size={14} /> Back
            </button>
            <button
              onClick={handleConfirm}
              disabled={saving}
              className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#17C5B0] rounded-lg hover:bg-[#14B09D] disabled:opacity-50 transition-colors"
            >
              {saving ? 'Creating...' : 'Confirm & Generate Link'} <CheckCircle2 size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Link Generated */}
      {step === 'link' && (
        <div className="space-y-4">
          <div className="card p-6 border border-[#17C5B0]/30 bg-[#17C5B0]/5 text-center">
            <div className="w-14 h-14 rounded-full bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 size={28} className="text-[#17C5B0]" />
            </div>
            <h2 className="text-lg font-bold text-[#F5F5F7]">Customer Created!</h2>
            <p className="text-[13px] text-[#A1A1A8] mt-1">
              Send this link to <span className="text-[#F5F5F7] font-medium">{form.ownerName}</span> to complete their setup
            </p>
          </div>

          <div className="card p-4 border border-[#1F1F23]">
            <label className="block text-[11px] font-medium text-[#A1A1A8] mb-2">Onboarding Link</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={onboardingLink}
                readOnly
                className="flex-1 px-3 py-2.5 text-[12px] rounded-lg bg-[#0A0A0B] border border-[#1F1F23] text-[#A1A1A8] font-mono truncate"
              />
              <button
                onClick={copyLink}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-[12px] font-medium rounded-lg border transition-all duration-200 ${
                  copied
                    ? 'bg-[#17C5B0]/10 border-[#17C5B0]/30 text-[#17C5B0]'
                    : 'bg-[#1F1F23] border-[#2A2A2E] text-[#F5F5F7] hover:bg-[#2A2A2E]'
                }`}
              >
                {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={sendViaSms}
              className="flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors"
            >
              <Send size={14} /> Text to Customer
            </button>
            <button
              onClick={() => {
                const subject = `Your Meridian Account is Ready!`
                const body = `Hi ${form.ownerName.split(' ')[0]},\n\nYour Meridian analytics account is set up! Click the link below to complete your onboarding — it only takes about 3 minutes:\n\n${onboardingLink}\n\nYou'll connect your POS, upload your inventory, and your dashboard will start lighting up with insights.\n\nLet me know if you have any questions!\n\n${rep?.name || 'Your Meridian Rep'}`
                window.open(`mailto:${form.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, '_blank')
              }}
              className="flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-[#F5F5F7] bg-[#1F1F23] rounded-lg hover:bg-[#2A2A2E] border border-[#2A2A2E] transition-colors"
            >
              <Mail size={14} /> Email to Customer
            </button>
          </div>

          <div className="flex justify-between pt-4">
            <button
              onClick={() => navigate('/sales/leads')}
              className="text-[12px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
            >
              ← Back to Leads
            </button>
            <button
              onClick={() => {
                setForm({ businessName: '', ownerName: '', email: '', phone: '', vertical: '', plan: 'insights', customPrice: '', notes: '' })
                setStep('details')
                setOnboardingLink('')
              }}
              className="text-[12px] text-[#1A8FD6] hover:text-[#F5F5F7] transition-colors"
            >
              + Create Another Customer
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
