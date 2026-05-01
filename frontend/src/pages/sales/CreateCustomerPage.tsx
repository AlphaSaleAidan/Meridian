import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, CheckCircle2, Copy, Send,
  Store, User, Mail, Phone, DollarSign, FileDown,
  Loader2, Eye, Gift, Sparkles,
} from 'lucide-react'
import { MeridianEmblem } from '@/components/MeridianLogo'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase } from '@/lib/supabase'
import { PLAN_TIERS, getPlan, type PlanTier } from '@/lib/proposal-plans'
import { downloadProposalPdf, type ProposalInput } from '@/lib/generate-proposal-pdf'

type Step = 'details' | 'plan' | 'customize' | 'preview'

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

function generateToken(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
  let token = ''
  for (let i = 0; i < 24; i++) token += chars.charAt(Math.floor(Math.random() * chars.length))
  return token
}

export default function CreateCustomerPage() {
  const navigate = useNavigate()
  const { rep } = useSalesAuth()
  const [step, setStep] = useState<Step>('details')
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [copied, setCopied] = useState(false)
  const [onboardingLink, setOnboardingLink] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [proposalGenerated, setProposalGenerated] = useState(false)

  const [form, setForm] = useState({
    businessName: '',
    ownerName: '',
    email: '',
    phone: '',
    vertical: '',
    plan: 'premium',
    customPrice: '',
    setupFee: '',
    firstMonthFree: false,
    notes: '',
  })

  function update(key: string, value: string | boolean) {
    setForm(f => ({ ...f, [key]: value }))
    setError(null)
  }

  const selectedPlan = getPlan(form.plan)
  const price = form.customPrice ? parseInt(form.customPrice) : selectedPlan.price
  const setupFee = form.setupFee ? parseInt(form.setupFee) : 0
  const dueToday = (form.firstMonthFree ? 0 : price) + setupFee

  function validateDetails(): boolean {
    if (!form.businessName.trim()) { setError('Business name is required'); return false }
    if (!form.ownerName.trim()) { setError('Owner name is required'); return false }
    if (!form.email.trim()) { setError('Email is required'); return false }
    if (!form.phone.trim()) { setError('Phone number is required'); return false }
    return true
  }

  const buildProposalInput = useCallback((): ProposalInput | null => {
    if (!rep) return null
    return {
      businessName: form.businessName,
      ownerName: form.ownerName,
      email: form.email,
      phone: form.phone,
      plan: selectedPlan,
      customPrice: form.customPrice ? parseInt(form.customPrice) : undefined,
      setupFee,
      firstMonthFree: form.firstMonthFree,
      rep,
    }
  }, [form, selectedPlan, setupFee, rep])

  async function handleGenerateProposal() {
    const input = buildProposalInput()
    if (!input) { setError('Please log in as a sales rep'); return }
    setGenerating(true)
    setError(null)
    try {
      await downloadProposalPdf(input)
      setProposalGenerated(true)
    } catch (err: any) {
      setError(err.message || 'Failed to generate proposal PDF')
    } finally {
      setGenerating(false)
    }
  }

  async function handleCreateCustomer() {
    setSaving(true)
    setError(null)
    try {
      const token = generateToken()
      const businessId = uuid()

      if (supabase) {
        const { error: bizErr } = await supabase.from('organizations').insert({
          id: businessId,
          name: form.businessName,
          slug: form.businessName.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
          email: form.email,
          phone: form.phone || null,
          vertical: (form.vertical as any) || 'other',
          metadata: {
            plan_tier: form.plan,
            monthly_price: price,
            setup_fee: setupFee,
            first_month_free: form.firstMonthFree,
            owner_name: form.ownerName,
            created_by_rep: rep?.rep_id || null,
          },
        })
        if (bizErr) throw new Error(bizErr.message)

        const { error: dealErr } = await supabase.from('deals').insert({
          id: uuid(),
          business_name: form.businessName,
          contact_name: form.ownerName,
          contact_email: form.email,
          contact_phone: form.phone,
          vertical: form.vertical || 'Other',
          stage: 'proposal_sent',
          monthly_value: price,
          commission_rate: rep?.commission_rate || 35,
          notes: form.notes || `Plan: ${selectedPlan.label} at $${price}/mo. Setup fee: $${setupFee}. First month free: ${form.firstMonthFree ? 'Yes' : 'No'}`,
          rep_id: rep?.rep_id || null,
        })
        if (dealErr) console.warn('Deal creation warning:', dealErr.message)
      } else {
        const existing = JSON.parse(localStorage.getItem('meridian_pending_customers') || '[]')
        existing.push({
          id: businessId, token, ...form, price, setupFee,
          plan: selectedPlan.label, repId: rep?.rep_id, repName: rep?.name,
          createdAt: new Date().toISOString(),
        })
        localStorage.setItem('meridian_pending_customers', JSON.stringify(existing))
      }

      const link = `${window.location.origin}/onboard?token=${token}&biz=${encodeURIComponent(form.businessName)}&name=${encodeURIComponent(form.ownerName)}&email=${encodeURIComponent(form.email)}&phone=${encodeURIComponent(form.phone)}`
      setOnboardingLink(link)
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
  const stepLabels = ['Business Details', 'Select Plan', 'Customize & Price', 'Generate Proposal']
  const steps: Step[] = ['details', 'plan', 'customize', 'preview']
  const currentIdx = steps.indexOf(step)

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => {
            if (step === 'details') navigate('/sales/leads')
            else setStep(steps[currentIdx - 1])
          }}
          className="p-2 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F7]">Generate Proposal</h1>
          <p className="text-[12px] text-[#A1A1A8]">Create a branded proposal and onboarding link for your customer</p>
        </div>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-1 mb-8">
        {stepLabels.map((label, i) => {
          const isActive = i === currentIdx
          const isDone = i < currentIdx
          return (
            <div key={label} className="flex-1 flex flex-col gap-1.5">
              <div className={`h-1 rounded-full transition-colors duration-300 ${isDone ? 'bg-[#7C5CFF]' : isActive ? 'bg-[#4FE3C1]' : 'bg-[#1F1F23]'}`} />
              <span className={`text-[10px] font-medium ${isActive ? 'text-[#F5F5F7]' : isDone ? 'text-[#7C5CFF]' : 'text-[#A1A1A8]/40'}`}>
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
          <div className="bg-[#111113] rounded-xl p-6 border border-[#1F1F23] space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Store size={16} className="text-[#7C5CFF]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Business Information</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Business Name *</label>
                <input
                  type="text" value={form.businessName}
                  onChange={e => update('businessName', e.target.value)}
                  placeholder="e.g. Lucky Dragon Kitchen"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#7C5CFF]/50 focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Business Type</label>
                <select
                  value={form.vertical} onChange={e => update('vertical', e.target.value)}
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] focus:border-[#7C5CFF]/50 focus:outline-none transition-colors"
                >
                  <option value="">Select type...</option>
                  {verticals.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2 mt-6 mb-2">
              <User size={16} className="text-[#4FE3C1]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Owner Contact</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Owner Name *</label>
                <input type="text" value={form.ownerName} onChange={e => update('ownerName', e.target.value)}
                  placeholder="e.g. James Chen"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#7C5CFF]/50 focus:outline-none transition-colors" />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Email *</label>
                <input type="email" value={form.email} onChange={e => update('email', e.target.value)}
                  placeholder="james@luckydragon.com"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#7C5CFF]/50 focus:outline-none transition-colors" />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Phone *</label>
                <input type="tel" value={form.phone} onChange={e => update('phone', e.target.value)}
                  placeholder="(555) 234-5678"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#7C5CFF]/50 focus:outline-none transition-colors" />
              </div>
            </div>
            <div className="mt-2">
              <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Notes (optional)</label>
              <textarea value={form.notes} onChange={e => update('notes', e.target.value)}
                placeholder="Any notes about this business..."
                rows={2}
                className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#7C5CFF]/50 focus:outline-none transition-colors resize-none" />
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={() => validateDetails() && setStep('plan')}
              className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#7C5CFF] rounded-lg hover:bg-[#6B4FE0] transition-colors">
              Next: Select Plan <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Plan Selection */}
      {step === 'plan' && (
        <div className="space-y-4">
          <div className="bg-[#111113] rounded-xl p-6 border border-[#1F1F23]">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles size={16} className="text-[#7C5CFF]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Select Plan for {form.businessName}</h2>
            </div>
            <div className="grid gap-3">
              {PLAN_TIERS.map(plan => (
                <button key={plan.id} onClick={() => update('plan', plan.id)}
                  className={`p-4 rounded-lg border text-left transition-all duration-200 ${
                    form.plan === plan.id
                      ? 'border-[#7C5CFF]/50 bg-[#7C5CFF]/10'
                      : 'border-[#1F1F23] hover:border-[#2A2A2E] bg-[#0A0A0B]'
                  }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-[14px] font-semibold text-[#F5F5F7]">{plan.label}</p>
                        {plan.tag && (
                          <span className="text-[10px] px-2 py-0.5 bg-[#7C5CFF] text-white font-semibold rounded">
                            {plan.tag}
                          </span>
                        )}
                      </div>
                      <p className="text-[12px] text-[#A1A1A8] mt-0.5">{plan.features.slice(0, 3).join(' · ')}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-[#F5F5F7]">${plan.price}</p>
                      <p className="text-[10px] text-[#A1A1A8]">/month</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep('details')}
              className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('customize')}
              className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#7C5CFF] rounded-lg hover:bg-[#6B4FE0] transition-colors">
              Next: Customize <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Customize Pricing */}
      {step === 'customize' && (
        <div className="space-y-4">
          <div className="bg-[#111113] rounded-xl p-6 border border-[#1F1F23]">
            <div className="flex items-center gap-2 mb-4">
              <DollarSign size={16} className="text-[#4FE3C1]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Customize Pricing</h2>
            </div>

            {/* Selected plan summary */}
            <div className="p-4 rounded-lg border border-[#7C5CFF]/20 bg-[#7C5CFF]/5 mb-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-[13px] font-semibold text-[#F5F5F7]">{selectedPlan.label} Plan</p>
                  <p className="text-[11px] text-[#A1A1A8]">{selectedPlan.features.length} features included</p>
                </div>
                <p className="text-lg font-bold text-[#7C5CFF]">${selectedPlan.price}/mo</p>
              </div>
            </div>

            {/* Custom price override */}
            <div className="mb-4">
              <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Custom Monthly Price (optional override)</label>
              <div className="relative">
                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
                <input type="number" value={form.customPrice}
                  onChange={e => update('customPrice', e.target.value)}
                  placeholder={selectedPlan.price.toString()}
                  className="w-full pl-8 pr-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#7C5CFF]/50 focus:outline-none transition-colors" />
              </div>
            </div>

            {/* Setup Fee */}
            <div className="mb-4">
              <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">
                Setup Fee <span className="text-[#4FE3C1]">(you keep 100%)</span>
              </label>
              <div className="relative">
                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
                <input type="number" value={form.setupFee}
                  onChange={e => update('setupFee', e.target.value)}
                  placeholder="0"
                  className="w-full pl-8 pr-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#7C5CFF]/50 focus:outline-none transition-colors" />
              </div>
              <p className="text-[10px] text-[#4FE3C1]/60 mt-1">Custom amount — goes directly to you</p>
            </div>

            {/* First Month Free Toggle */}
            <div className="flex items-center justify-between p-4 rounded-lg border border-[#1F1F23] bg-[#0A0A0B]">
              <div className="flex items-center gap-3">
                <Gift size={18} className={form.firstMonthFree ? 'text-[#7C5CFF]' : 'text-[#A1A1A8]/40'} />
                <div>
                  <p className="text-[13px] font-semibold text-[#F5F5F7]">First Month Free</p>
                  <p className="text-[11px] text-[#A1A1A8]">Waive month 1 subscription — great for closing hesitant prospects</p>
                </div>
              </div>
              <button
                onClick={() => update('firstMonthFree', !form.firstMonthFree)}
                className={`relative w-12 h-6 rounded-full transition-colors duration-200 ${
                  form.firstMonthFree ? 'bg-[#7C5CFF]' : 'bg-[#2A2A2E]'
                }`}
              >
                <div className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform duration-200 ${
                  form.firstMonthFree ? 'translate-x-6' : ''
                }`} />
              </button>
            </div>
          </div>

          {/* Summary Card */}
          <div className="bg-[#111113] rounded-xl p-6 border border-[#4FE3C1]/20 bg-gradient-to-b from-[#4FE3C1]/5 to-transparent">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 size={16} className="text-[#4FE3C1]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Proposal Summary</h2>
            </div>
            <div className="space-y-2 text-[13px]">
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Business</span>
                <span className="text-[#F5F5F7] font-medium">{form.businessName}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Plan</span>
                <span className="text-[#F5F5F7] font-medium">{selectedPlan.label} — ${price}/mo</span>
              </div>
              {setupFee > 0 && (
                <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                  <span className="text-[#A1A1A8]">Setup Fee <span className="text-[#4FE3C1]">(yours)</span></span>
                  <span className="text-[#4FE3C1] font-medium">${setupFee}</span>
                </div>
              )}
              {form.firstMonthFree && (
                <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                  <span className="text-[#A1A1A8]">First Month</span>
                  <span className="text-[#7C5CFF] font-medium">FREE</span>
                </div>
              )}
              <div className="flex justify-between py-3">
                <span className="text-[#A1A1A8] font-medium">Due Today</span>
                <span className="text-lg font-bold text-[#4FE3C1]">${dueToday.toLocaleString()}</span>
              </div>
            </div>
            {rep && (
              <div className="mt-3 pt-3 border-t border-[#1F1F23]">
                <p className="text-[11px] text-[#A1A1A8]">
                  Rep: <span className="text-[#F5F5F7] font-medium">{rep.name}</span> ·
                  Commission: <span className="text-[#4FE3C1] font-medium">{rep.commission_rate}%</span> =
                  <span className="text-[#4FE3C1] font-medium"> ${Math.round(price * (rep.commission_rate / 100))}/mo</span>
                  {setupFee > 0 && <span className="text-[#7C5CFF]"> + ${setupFee} setup</span>}
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep('plan')}
              className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('preview')}
              className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#7C5CFF] rounded-lg hover:bg-[#6B4FE0] transition-colors">
              Next: Generate <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Generate & Send */}
      {step === 'preview' && (
        <div className="space-y-4">
          {/* Final summary */}
          <div className="bg-[#111113] rounded-xl p-6 border border-[#7C5CFF]/20">
            <div className="flex items-center gap-2 mb-4">
              <Eye size={16} className="text-[#7C5CFF]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Proposal Ready</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 text-[13px]">
              <div className="p-3 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
                <div className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider mb-1">Business</div>
                <div className="text-[#F5F5F7] font-medium">{form.businessName}</div>
              </div>
              <div className="p-3 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
                <div className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider mb-1">Owner</div>
                <div className="text-[#F5F5F7] font-medium">{form.ownerName}</div>
              </div>
              <div className="p-3 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
                <div className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider mb-1">Plan</div>
                <div className="text-[#7C5CFF] font-medium">{selectedPlan.label} — ${price}/mo</div>
              </div>
              <div className="p-3 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
                <div className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider mb-1">Due Today</div>
                <div className="text-[#4FE3C1] font-medium">${dueToday.toLocaleString()}</div>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="grid grid-cols-1 gap-3">
            <button
              onClick={handleGenerateProposal}
              disabled={generating}
              className="flex items-center justify-center gap-2 px-6 py-4 text-[14px] font-semibold text-white bg-gradient-to-r from-[#7C5CFF] to-[#4FE3C1] rounded-xl hover:opacity-90 disabled:opacity-50 transition-all"
            >
              {generating ? (
                <><Loader2 size={18} className="animate-spin" /> Generating Proposal PDF...</>
              ) : proposalGenerated ? (
                <><CheckCircle2 size={18} /> Download Again</>
              ) : (
                <><FileDown size={18} /> Generate Proposal PDF</>
              )}
            </button>

            {proposalGenerated && (
              <div className="text-center text-[12px] text-[#4FE3C1]">
                ✓ Proposal downloaded! The 7-slide PDF includes your pricing, plan details, and contact info.
              </div>
            )}
          </div>

          {/* Create customer + send link */}
          <div className="bg-[#111113] rounded-xl p-6 border border-[#1F1F23]">
            <div className="flex items-center gap-2 mb-4">
              <Send size={16} className="text-[#4FE3C1]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Create Account & Send Onboarding Link</h2>
            </div>

            {!onboardingLink ? (
              <button
                onClick={handleCreateCustomer}
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 text-[13px] font-medium text-white bg-[#4FE3C1] text-[#0A0A0B] rounded-lg hover:bg-[#3DD4B2] disabled:opacity-50 transition-colors"
              >
                {saving ? <><Loader2 size={14} className="animate-spin" /> Creating...</> : <><CheckCircle2 size={14} /> Create Customer & Generate Link</>}
              </button>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-[13px] text-[#4FE3C1]">
                  <CheckCircle2 size={14} /> Customer created!
                </div>
                <div className="flex gap-2">
                  <input type="text" value={onboardingLink} readOnly
                    className="flex-1 px-3 py-2.5 text-[12px] rounded-lg bg-[#0A0A0B] border border-[#1F1F23] text-[#A1A1A8] font-mono truncate" />
                  <button onClick={copyLink}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-[12px] font-medium rounded-lg border transition-all duration-200 ${
                      copied ? 'bg-[#4FE3C1]/10 border-[#4FE3C1]/30 text-[#4FE3C1]' : 'bg-[#1F1F23] border-[#2A2A2E] text-[#F5F5F7] hover:bg-[#2A2A2E]'
                    }`}>
                    {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <button onClick={sendViaSms}
                    className="flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-white bg-[#7C5CFF] rounded-lg hover:bg-[#6B4FE0] transition-colors">
                    <Phone size={14} /> Text to Customer
                  </button>
                  <button onClick={() => {
                    const subject = `Your Meridian Account is Ready!`
                    const body = `Hi ${form.ownerName.split(' ')[0]},\n\nYour Meridian analytics account is set up! Click the link below to complete your onboarding — it only takes about 3 minutes:\n\n${onboardingLink}\n\nYou'll connect your POS and your dashboard will start lighting up with insights.\n\nLet me know if you have any questions!\n\n${rep?.name || 'Your Meridian Rep'}${rep?.phone ? '\n' + rep.phone : ''}`
                    window.open(`mailto:${form.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, '_blank')
                  }}
                    className="flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-[#F5F5F7] bg-[#1F1F23] rounded-lg hover:bg-[#2A2A2E] border border-[#2A2A2E] transition-colors">
                    <Mail size={14} /> Email to Customer
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep('customize')}
              className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => {
              setForm({ businessName: '', ownerName: '', email: '', phone: '', vertical: '', plan: 'premium', customPrice: '', setupFee: '', firstMonthFree: false, notes: '' })
              setStep('details')
              setOnboardingLink('')
              setProposalGenerated(false)
            }}
              className="text-[12px] text-[#7C5CFF] hover:text-[#F5F5F7] transition-colors">
              + Create Another Proposal
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
