import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, CheckCircle2, Copy, Send, Loader2,
  Store, User, Mail, Phone, DollarSign, Tag, Key,
  AlertCircle,
} from 'lucide-react'
import { MeridianEmblem } from '@/components/MeridianLogo'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase } from '@/lib/supabase'

type Step = 'details' | 'plan' | 'confirm' | 'provisioned'

const PLANS = [
  { id: 'starter', label: 'Starter', price: 339, desc: 'Core analytics + AI recommendations' },
  { id: 'growth', label: 'Growth', price: 675, desc: '+ Forecasting + smart notifications' },
  { id: 'enterprise', label: 'Enterprise', price: 1350, desc: '+ Benchmarking + what-if simulator' },
]

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

function formatCAD(amount: number): string {
  return 'CA$' + amount.toLocaleString('en-CA')
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function CanadaPortalCreateCustomerPage() {
  const navigate = useNavigate()
  const { rep } = useSalesAuth()
  const [step, setStep] = useState<Step>('details')
  const [saving, setSaving] = useState(false)
  const [copied, setCopied] = useState<'password' | 'link' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [credentials, setCredentials] = useState<{
    email: string
    password: string
    loginUrl: string
    invoicesSent: boolean
  } | null>(null)

  const [form, setForm] = useState({
    businessName: '',
    ownerName: '',
    email: '',
    phone: '',
    vertical: '',
    plan: 'starter',
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

  async function handleConfirmAndProvision() {
    setSaving(true)
    setError(null)
    try {
      const orgId = uuid()
      if (supabase) {
        const { error: bizErr } = await supabase.from('organizations').insert({
          id: orgId,
          name: form.businessName,
          slug: form.businessName.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
          email: form.email,
          phone: form.phone || null,
          vertical: (form.vertical as any) || 'other',
          metadata: {
            plan_tier: form.plan,
            monthly_price: price,
            currency: 'CAD',
            owner_name: form.ownerName,
            created_by_rep: rep?.rep_id || null,
          },
        })
        if (bizErr) throw new Error(bizErr.message)

        await supabase.from('deals').insert({
          id: uuid(),
          business_name: form.businessName,
          contact_name: form.ownerName,
          contact_email: form.email,
          contact_phone: form.phone,
          vertical: form.vertical || 'Other',
          stage: 'closed_won',
          monthly_value: price,
          commission_rate: rep?.commission_rate || 35,
          notes: form.notes || `Canada portal. Plan: ${selectedPlan.label} at CA$${price}/mo`,
          rep_id: rep?.rep_id || null,
        }).then(({ error: dealErr }) => {
          if (dealErr) console.warn('Deal creation warning:', dealErr.message)
        })
      }

      const response = await fetch(`${API_BASE}/api/onboarding/provision-customer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: orgId,
          email: form.email,
          owner_name: form.ownerName,
          business_name: form.businessName,
          plan: form.plan,
          monthly_price: price,
          currency: 'CAD',
          rep_id: rep?.rep_id || null,
          rep_name: rep?.name || null,
        }),
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => null)
        throw new Error(errData?.detail || 'Failed to provision customer account')
      }

      const result = await response.json()
      setCredentials({
        email: result.email,
        password: result.temporary_password,
        loginUrl: result.login_url,
        invoicesSent: result.invoices_sent,
      })
      setStep('provisioned')
    } catch (err: any) {
      setError(err.message || 'Failed to create customer')
    } finally {
      setSaving(false)
    }
  }

  async function copyToClipboard(text: string, type: 'password' | 'link') {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      const input = document.createElement('input')
      input.value = text
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
    }
    setCopied(type)
    setTimeout(() => setCopied(null), 2000)
  }

  const verticals = ['Restaurant', 'Café', 'Bar', 'Smoke Shop', 'Boutique', 'Salon', 'Food Truck', 'Convenience Store', 'Other']
  const INPUT = 'w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none transition-colors'

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => step === 'details' ? navigate('/canada/portal/leads') : setStep(step === 'confirm' ? 'plan' : step === 'plan' ? 'details' : 'details')}
          className="p-2 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F7]">New Customer</h1>
          <p className="text-[12px] text-[#A1A1A8]">Create account, send invoices, and activate their Canadian portal</p>
        </div>
      </div>

      <div className="flex items-center gap-1 mb-8">
        {['Business Details', 'Select Plan', 'Confirm & Provision', 'Account Ready'].map((label, i) => {
          const steps: Step[] = ['details', 'plan', 'confirm', 'provisioned']
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
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[13px] flex items-center gap-2">
          <AlertCircle size={14} /> {error}
        </div>
      )}

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
                <input type="text" value={form.businessName} onChange={e => update('businessName', e.target.value)} placeholder="e.g. Maple Leaf Bistro" className={INPUT} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Business Type</label>
                <select value={form.vertical} onChange={e => update('vertical', e.target.value)} className={INPUT}>
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
                <input type="text" value={form.ownerName} onChange={e => update('ownerName', e.target.value)} placeholder="e.g. Sarah Thompson" className={INPUT} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Email *</label>
                <input type="email" value={form.email} onChange={e => update('email', e.target.value)} placeholder="sarah@mapleleaf.ca" className={INPUT} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Phone *</label>
                <input type="tel" value={form.phone} onChange={e => update('phone', e.target.value)} placeholder="(416) 555-0199" className={INPUT} />
              </div>
            </div>
            <div className="mt-2">
              <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Notes (optional)</label>
              <textarea value={form.notes} onChange={e => update('notes', e.target.value)} placeholder="Any notes about this business..." rows={2} className={`${INPUT} resize-none`} />
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={() => validateDetails() && setStep('plan')} className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors">
              Next: Select Plan <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {step === 'plan' && (
        <div className="space-y-4">
          <div className="card p-6 border border-[#1F1F23]">
            <div className="flex items-center gap-2 mb-4">
              <Tag size={16} className="text-[#1A8FD6]" />
              <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Select Plan for {form.businessName}</h2>
            </div>
            <div className="grid gap-3">
              {PLANS.map(plan => (
                <button key={plan.id} onClick={() => update('plan', plan.id)}
                  className={`p-4 rounded-lg border text-left transition-all duration-200 ${form.plan === plan.id ? 'border-[#1A8FD6]/50 bg-[#1A8FD6]/10' : 'border-[#1F1F23] hover:border-[#2A2A2E] bg-[#0A0A0B]'}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[14px] font-semibold text-[#F5F5F7]">{plan.label}</p>
                      <p className="text-[12px] text-[#A1A1A8] mt-0.5">{plan.desc}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-[#F5F5F7]">{formatCAD(plan.price)}</p>
                      <p className="text-[10px] text-[#A1A1A8]">/month</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
            <div className="mt-4">
              <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Custom Price (optional override, CA$)</label>
              <div className="relative">
                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
                <input type="number" value={form.customPrice} onChange={e => update('customPrice', e.target.value)} placeholder={selectedPlan.price.toString()} className={`${INPUT} pl-8`} />
              </div>
              <p className="text-[10px] text-[#A1A1A8]/40 mt-1">Leave blank to use standard pricing</p>
            </div>
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep('details')} className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('confirm')} className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors">
              Next: Confirm <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {step === 'confirm' && (
        <div className="space-y-4">
          <div className="card p-6 border border-[#17C5B0]/30 bg-[#17C5B0]/5">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 size={18} className="text-[#17C5B0]" />
              <h2 className="text-[15px] font-semibold text-[#F5F5F7]">Confirm & Activate Customer</h2>
            </div>
            <div className="space-y-3 text-[13px]">
              {[
                ['Business', form.businessName],
                ['Owner', form.ownerName],
                ['Email', form.email],
                ['Phone', form.phone],
                ...(form.vertical ? [['Type', form.vertical]] : []),
                ['Plan', selectedPlan.label],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between py-2 border-b border-[#1F1F23]">
                  <span className="text-[#A1A1A8]">{label}</span>
                  <span className="text-[#F5F5F7] font-medium">{value}</span>
                </div>
              ))}
              <div className="flex justify-between py-3">
                <span className="text-[#A1A1A8] font-medium">Monthly Price</span>
                <span className="text-lg font-bold text-[#17C5B0]">{formatCAD(price)}/mo</span>
              </div>
            </div>
            {rep && (
              <div className="mt-3 pt-3 border-t border-[#1F1F23]">
                <p className="text-[11px] text-[#A1A1A8]">
                  Signed up by <span className="text-[#F5F5F7] font-medium">{rep.name}</span> &middot;
                  Commission: <span className="text-[#17C5B0] font-medium">{rep.commission_rate}%</span> =
                  <span className="text-[#17C5B0] font-medium"> {formatCAD(Math.round(price * (rep.commission_rate / 100)))}/mo</span>
                </p>
              </div>
            )}
            <div className="mt-4 rounded-lg p-3 bg-[#1A8FD6]/5 border border-[#1A8FD6]/15">
              <p className="text-[11px] text-[#A1A1A8] leading-relaxed">
                <span className="text-[#1A8FD6] font-medium">What happens when you confirm:</span> The system will create
                the customer's portal login (email + generated password), send invoices in CAD,
                and prepare their dashboard. You'll see the credentials to share with the customer.
              </p>
            </div>
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep('plan')} className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={handleConfirmAndProvision} disabled={saving} className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#17C5B0] rounded-lg hover:bg-[#14B09D] disabled:opacity-50 transition-colors">
              {saving ? <><Loader2 size={14} className="animate-spin" /> Provisioning...</> : <>Confirm & Activate <CheckCircle2 size={14} /></>}
            </button>
          </div>
        </div>
      )}

      {step === 'provisioned' && credentials && (
        <div className="space-y-4">
          <div className="card p-6 border border-[#17C5B0]/30 bg-[#17C5B0]/5 text-center">
            <div className="w-14 h-14 rounded-full bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 size={28} className="text-[#17C5B0]" />
            </div>
            <h2 className="text-lg font-bold text-[#F5F5F7]">Account Activated!</h2>
            <p className="text-[13px] text-[#A1A1A8] mt-1">
              Portal is live for <span className="text-[#F5F5F7] font-medium">{form.businessName}</span>
            </p>
          </div>
          <div className="card p-6 border border-[#1A8FD6]/30 bg-[#1A8FD6]/5">
            <div className="flex items-center gap-2 mb-4">
              <Key size={16} className="text-[#1A8FD6]" />
              <h3 className="text-[14px] font-semibold text-[#F5F5F7]">Customer Login Credentials</h3>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-[10px] font-medium text-[#A1A1A8] mb-1">Portal URL</label>
                <div className="flex gap-2">
                  <input type="text" value={credentials.loginUrl} readOnly className="flex-1 px-3 py-2.5 text-[12px] rounded-lg bg-[#0A0A0B] border border-[#1F1F23] text-[#A1A1A8] font-mono" />
                  <button onClick={() => copyToClipboard(credentials.loginUrl, 'link')}
                    className={`px-3 py-2 rounded-lg border text-[11px] font-medium transition-all ${copied === 'link' ? 'bg-[#17C5B0]/10 border-[#17C5B0]/30 text-[#17C5B0]' : 'bg-[#1F1F23] border-[#2A2A2E] text-[#F5F5F7] hover:bg-[#2A2A2E]'}`}>
                    {copied === 'link' ? <CheckCircle2 size={12} /> : <Copy size={12} />}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-medium text-[#A1A1A8] mb-1">Email</label>
                  <div className="px-3 py-2.5 text-[13px] rounded-lg bg-[#0A0A0B] border border-[#1F1F23] text-[#F5F5F7] font-mono">{credentials.email}</div>
                </div>
                <div>
                  <label className="block text-[10px] font-medium text-[#A1A1A8] mb-1">Temporary Password</label>
                  <div className="flex gap-2">
                    <div className="flex-1 px-3 py-2.5 text-[13px] rounded-lg bg-[#0A0A0B] border border-[#1A8FD6]/30 text-[#1A8FD6] font-mono font-bold">{credentials.password}</div>
                    <button onClick={() => copyToClipboard(credentials.password, 'password')}
                      className={`px-3 py-2 rounded-lg border text-[11px] font-medium transition-all ${copied === 'password' ? 'bg-[#17C5B0]/10 border-[#17C5B0]/30 text-[#17C5B0]' : 'bg-[#1F1F23] border-[#2A2A2E] text-[#F5F5F7] hover:bg-[#2A2A2E]'}`}>
                      {copied === 'password' ? <CheckCircle2 size={12} /> : <Copy size={12} />}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button onClick={() => {
                if (!credentials) return
                const subject = `Your Meridian Canada Dashboard is Live!`
                const body = `Hi ${form.ownerName.split(' ')[0]},\n\nYour Meridian Canada analytics dashboard for ${form.businessName} is ready!\n\nPortal: ${credentials.loginUrl}\nEmail: ${credentials.email}\nPassword: ${credentials.password}\n\nPlease change your password after your first login.\n\n${rep?.name || 'Your Meridian Canada Rep'}`
                window.open(`mailto:${form.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, '_blank')
              }}
              className="flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors">
              <Mail size={14} /> Email Credentials
            </button>
            <button onClick={() => {
                if (!credentials) return
                const msg = `Hey ${form.ownerName.split(' ')[0]}! Your Meridian Canada dashboard is live. Log in at ${credentials.loginUrl} with email ${credentials.email} and password ${credentials.password}`
                window.open(`sms:${form.phone}?body=${encodeURIComponent(msg)}`, '_blank')
              }}
              className="flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-[#F5F5F7] bg-[#1F1F23] rounded-lg hover:bg-[#2A2A2E] border border-[#2A2A2E] transition-colors">
              <Send size={14} /> Text Credentials
            </button>
          </div>
          <div className="flex justify-between pt-4">
            <button onClick={() => navigate('/canada/portal/leads')} className="text-[12px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              Back to Leads
            </button>
            <button onClick={() => { setForm({ businessName: '', ownerName: '', email: '', phone: '', vertical: '', plan: 'starter', customPrice: '', notes: '' }); setStep('details'); setCredentials(null) }}
              className="text-[12px] text-[#1A8FD6] hover:text-[#F5F5F7] transition-colors">
              + Create Another Customer
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
