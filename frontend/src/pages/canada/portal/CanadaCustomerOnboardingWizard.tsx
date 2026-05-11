import { useState, useEffect, useRef, type ChangeEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowRight, ArrowLeft, CheckCircle2, Loader2, Upload, Plus, Trash2,
  Store, User, Wifi, Package, Users, Calendar, Camera, Shield,
  X, CreditCard, AlertCircle,
} from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import POSSystemPicker from '@/components/POSSystemPicker'
import { CAD_RATE } from '@/lib/canada-proposal-plans'

// ── Canada Theme ──
const T = {
  pageBg:    'bg-[#0a0f0d]',
  cardBg:    'bg-[#0f1512]',
  cardBorder:'border-[#1a2420]',
  inputBg:   'bg-[#0a0f0d]',
  inputBorder:'border-[#1a2420]',
  accent:    '#00d4aa',
  accentBg:  'bg-[#00d4aa]',
  accentHover:'hover:bg-[#00d4aa]/90',
  accentTxt: 'text-[#00d4aa]',
  accentBorder:'border-[#00d4aa]',
  muted:     'text-[#6b7a74]',
  text:      'text-[#F5F5F7]',
  focusBorder:'focus:border-[#00d4aa]/50',
} as const

const inputCls = `w-full px-3 py-2.5 text-[13px] rounded-lg ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-[#6b7a74]/40 ${T.focusBorder} focus:outline-none`
const btnPrimary = `flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium ${T.accentBg} text-[#0a0f0d] rounded-lg ${T.accentHover} disabled:opacity-50 transition-colors`
const btnBack = `flex items-center gap-2 px-4 py-2.5 text-[13px] ${T.muted} hover:text-[#F5F5F7] transition-colors`
const cardCls = `rounded-xl p-6 ${T.cardBorder} ${T.cardBg}`

type Step = 'account' | 'pos' | 'inventory' | 'staff' | 'schedule' | 'checkout' | 'processing' | 'done'

const STEPS: { key: Step; label: string; icon: typeof Store }[] = [
  { key: 'account', label: 'Account', icon: User },
  { key: 'pos', label: 'Connect POS', icon: Wifi },
  { key: 'inventory', label: 'Inventory', icon: Package },
  { key: 'staff', label: 'Staff', icon: Users },
  { key: 'schedule', label: 'Schedule', icon: Calendar },
  { key: 'checkout', label: 'Payment', icon: CreditCard },
]

const PROVINCES = [
  'Alberta','British Columbia','Manitoba','New Brunswick','Newfoundland and Labrador',
  'Northwest Territories','Nova Scotia','Nunavut','Ontario','Prince Edward Island',
  'Quebec','Saskatchewan','Yukon',
]

interface StaffMember { id: string; name: string; role: string; hourlyRate: string }
interface InventoryItem { id: string; name: string; category: string; costPerUnit: string; supplier: string; unit: string }

function uid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function CanadaCustomerOnboardingWizard() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { signup, connectPos, org } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const scheduleInputRef = useRef<HTMLInputElement>(null)

  const prefill = {
    token: searchParams.get('token') || '',
    businessName: searchParams.get('biz') || '',
    ownerName: searchParams.get('name') || '',
    email: searchParams.get('email') || '',
    phone: searchParams.get('phone') || '',
    plan: searchParams.get('plan') || '',
    price: searchParams.get('price') || '',
  }

  const [step, setStep] = useState<Step>('account')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // Account
  const [account, setAccount] = useState({
    businessName: prefill.businessName,
    ownerName: prefill.ownerName,
    email: prefill.email,
    phone: prefill.phone,
    password: '',
    confirmPassword: '',
  })
  const [province, setProvince] = useState('')

  // POS
  const [posProvider, setPosProvider] = useState<string | null>(null)

  // Inventory
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([])
  const [csvUploaded, setCsvUploaded] = useState(false)

  // Staff
  const [staffMembers, setStaffMembers] = useState<StaffMember[]>([])

  // Schedule
  const [scheduleImage, setScheduleImage] = useState<File | null>(null)
  const [schedulePreview, setSchedulePreview] = useState<string | null>(null)

  // Checkout
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [paymentComplete, setPaymentComplete] = useState(false)
  const [checkoutError, setCheckoutError] = useState<string | null>(null)
  const monthlyPrice = prefill.price ? parseInt(prefill.price) : 250
  const monthlyPriceCAD = Math.round(monthlyPrice * CAD_RATE)

  // Processing
  const [processingStep, setProcessingStep] = useState(0)
  const processingSteps = [
    'Activating your subscription...',
    'Connecting to POS system...',
    'Importing transaction history...',
    'Analyzing inventory costs...',
    'Building staff profiles...',
    'Processing schedule data...',
    'Generating initial insights...',
    'Preparing your dashboard...',
  ]

  // Square checkout callback
  useEffect(() => {
    const checkoutStatus = searchParams.get('checkout')
    if (checkoutStatus === 'success') {
      const savedToken = sessionStorage.getItem('meridian_onboard_token')
      if (savedToken) sessionStorage.removeItem('meridian_onboard_token')
      setPaymentComplete(true)
      setStep('checkout')
    }
  }, [searchParams])

  function updateAccount(key: string, value: string) {
    setAccount(a => ({ ...a, [key]: value }))
    setError(null)
  }

  // ── Account ──
  async function handleAccountNext() {
    if (!account.businessName.trim()) { setError('Business name is required'); return }
    if (!account.ownerName.trim()) { setError('Your name is required'); return }
    if (!account.email.trim()) { setError('Email is required'); return }
    if (!account.phone.trim()) { setError('Phone number is required'); return }
    if (!account.password || account.password.length < 6) { setError('Password must be at least 6 characters'); return }
    if (account.password !== account.confirmPassword) { setError("Passwords don't match"); return }
    setSaving(true); setError(null)
    try {
      const err = await signup(account.email, account.password, account.ownerName, account.businessName)
      if (err && err !== '__confirm_email__') { setError(err); setSaving(false); return }
      setStep('pos')
    } catch (err: any) { setError(err.message || 'Signup failed') }
    finally { setSaving(false) }
  }

  // ── POS ──
  async function handlePosNext() {
    if (!posProvider) { setError('Please select your POS provider'); return }
    setSaving(true); setError(null)
    try {
      const err = await connectPos(posProvider, posProvider)
      if (err) { setError(err); setSaving(false); return }
      setStep('inventory')
    } catch (err: any) { setError(err.message || 'Connection failed') }
    finally { setSaving(false) }
  }

  // ── Inventory helpers ──
  function addInventoryItem() {
    setInventoryItems(items => [...items, { id: uid(), name: '', category: '', costPerUnit: '', supplier: '', unit: 'each' }])
  }
  function updateInventoryItem(id: string, key: keyof InventoryItem, value: string) {
    setInventoryItems(items => items.map(item => item.id === id ? { ...item, [key]: value } : item))
  }
  function removeInventoryItem(id: string) { setInventoryItems(items => items.filter(item => item.id !== id)) }

  function handleCsvUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string
        const lines = text.split('\n').filter(l => l.trim())
        if (lines.length < 2) { setError('CSV must have a header row and at least one data row'); return }
        const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
        const nameIdx = headers.findIndex(h => h.includes('name') || h.includes('item') || h.includes('product'))
        const catIdx = headers.findIndex(h => h.includes('cat') || h.includes('type'))
        const costIdx = headers.findIndex(h => h.includes('cost') || h.includes('price') || h.includes('cogs'))
        const supplierIdx = headers.findIndex(h => h.includes('supplier') || h.includes('vendor'))
        const unitIdx = headers.findIndex(h => h.includes('unit'))
        const items: InventoryItem[] = []
        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(',').map(c => c.trim().replace(/^["']|["']$/g, ''))
          if (nameIdx < 0 || !cols[nameIdx]) continue
          items.push({ id: uid(), name: cols[nameIdx] || '', category: catIdx >= 0 ? (cols[catIdx] || '') : '', costPerUnit: costIdx >= 0 ? (cols[costIdx] || '') : '', supplier: supplierIdx >= 0 ? (cols[supplierIdx] || '') : '', unit: unitIdx >= 0 ? (cols[unitIdx] || 'each') : 'each' })
        }
        setInventoryItems(items); setCsvUploaded(true); setError(null)
      } catch { setError('Failed to parse CSV. Please check the format.') }
    }
    reader.readAsText(file)
  }

  async function handleInventoryNext() {
    if (inventoryItems.length > 0 && supabase && org) {
      setSaving(true)
      try {
        const rows = inventoryItems.filter(item => item.name.trim()).map(item => ({
          org_id: org.org_id, name: item.name, category: item.category || null,
          cost_per_unit: item.costPerUnit ? parseFloat(item.costPerUnit) : null,
          supplier: item.supplier || null, unit: item.unit || 'each',
        }))
        if (rows.length > 0) await supabase.from('products').upsert(rows, { onConflict: 'org_id,name' })
      } catch (err) { console.warn('Inventory save warning:', err) }
      finally { setSaving(false) }
    }
    setStep('staff')
  }

  // ── Staff helpers ──
  function addStaffMember() { setStaffMembers(m => [...m, { id: uid(), name: '', role: '', hourlyRate: '' }]) }
  function updateStaffMember(id: string, key: keyof StaffMember, value: string) {
    setStaffMembers(m => m.map(s => s.id === id ? { ...s, [key]: value } : s))
  }
  function removeStaffMember(id: string) { setStaffMembers(m => m.filter(s => s.id !== id)) }

  async function handleStaffNext() {
    if (staffMembers.length > 0 && supabase && org) {
      setSaving(true)
      try {
        const rows = staffMembers.filter(m => m.name.trim()).map(m => ({
          org_id: org.org_id, name: m.name, role: m.role || 'Staff',
          hourly_rate: m.hourlyRate ? parseFloat(m.hourlyRate) : null,
        }))
        if (rows.length > 0) await supabase.from('users').insert(rows)
      } catch (err) { console.warn('Staff save warning:', err) }
      finally { setSaving(false) }
    }
    setStep('schedule')
  }

  // ── Schedule ──
  function handleScheduleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setScheduleImage(file)
    const reader = new FileReader()
    reader.onload = (event) => setSchedulePreview(event.target?.result as string)
    reader.readAsDataURL(file)
  }

  async function handleScheduleNext() {
    if (scheduleImage && supabase && org) {
      setSaving(true)
      try {
        const fileName = `${org.org_id}/schedule_${Date.now()}.${scheduleImage.name.split('.').pop()}`
        await supabase.storage.from('schedules').upload(fileName, scheduleImage)
        await supabase.from('scheduled_events').insert({
          org_id: org.org_id, event_type: 'schedule_upload', title: 'Staff Schedule Upload',
          notes: `Uploaded: ${scheduleImage.name}. Pending OCR processing.`,
          file_path: fileName, status: 'pending_processing',
        })
      } catch (err) { console.warn('Schedule upload warning:', err) }
      finally { setSaving(false) }
    }
    setStep('checkout')
  }

  // ── Checkout ──
  async function handleSquareCheckout() {
    setCheckoutLoading(true); setCheckoutError(null)
    const planLabel = (prefill.plan || 'Standard').replace(/^\w/, (c: string) => c.toUpperCase())
    try {
      const [upfrontRes, recurringRes] = await Promise.all([
        fetch(`${API_BASE}/api/billing/create-invoice`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            org_id: org?.org_id, amount_cents: monthlyPriceCAD * 100,
            customer_email: account.email,
            description: `Meridian Analytics (Canada) - ${planLabel} Plan (Setup Fee)`,
            due_days: 3,
          }),
        }),
        fetch(`${API_BASE}/api/billing/create-invoice`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            org_id: org?.org_id, amount_cents: monthlyPriceCAD * 100,
            customer_email: account.email,
            description: `Meridian Analytics (Canada) - ${planLabel} Plan (Monthly Recurring)`,
            due_days: 30,
          }),
        }),
      ])
      if (upfrontRes.ok && recurringRes.ok) {
        // Provision customer: create business record, subscription, and send welcome email
        try {
          await fetch(`${API_BASE}/api/onboarding/provision-customer`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              org_id: org?.org_id || prefill.token,
              email: account.email,
              phone: account.phone || null,
              owner_name: account.ownerName,
              business_name: account.businessName,
              plan: prefill.plan || 'starter',
              monthly_price: monthlyPriceCAD,
              rep_id: searchParams.get('rep') || null,
              rep_name: searchParams.get('rep_name') || null,
            }),
          })
        } catch (provisionErr) {
          console.warn('Provision call failed (non-blocking):', provisionErr)
        }
        setPaymentComplete(true)
        return
      }
      const failedRes = !upfrontRes.ok ? upfrontRes : recurringRes
      const errorData = await failedRes.json().catch(() => null)
      setCheckoutError(errorData?.detail || 'Unable to create invoices. Please try again or contact support at help@meridian.tips')
    } catch (err: any) {
      console.error('Invoice creation failed:', err)
      setCheckoutError('Billing system is temporarily unavailable. Please try again in a moment or contact support at help@meridian.tips')
    } finally { setCheckoutLoading(false) }
  }

  // ── Processing ──
  function startProcessing() {
    setStep('processing'); setProcessingStep(0)
    let current = 0
    const interval = setInterval(() => {
      current++
      if (current >= processingSteps.length) { clearInterval(interval); setStep('done') }
      else setProcessingStep(current)
    }, 1200)
  }

  const currentStepIdx = STEPS.findIndex(s => s.key === step)

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
        {step !== 'done' && step !== 'processing' && (
          <div className="flex items-center gap-1 mb-8">
            {STEPS.map((s, i) => {
              const isActive = i === currentStepIdx
              const isDone = i < currentStepIdx
              return (
                <div key={s.key} className="flex-1 flex flex-col gap-1.5">
                  <div className={`h-1 rounded-full transition-all duration-500 ${isDone ? 'bg-[#00d4aa]' : isActive ? 'bg-[#00d4aa]' : 'bg-[#1a2420]'}`} />
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

        {/* ═══ Account ═══ */}
        {step === 'account' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className={`text-xl font-bold ${T.text}`}>Welcome to Meridian</h1>
              <p className={`text-[13px] ${T.muted} mt-1`}>Set up your account in a few minutes and start seeing insights</p>
            </div>
            <div className={`${cardCls} space-y-4`}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={`block text-[11px] font-medium ${T.muted} mb-1.5`}>Business Name</label>
                  <input type="text" value={account.businessName} onChange={e => updateAccount('businessName', e.target.value)}
                    placeholder="Your business name" className={inputCls} />
                </div>
                <div>
                  <label className={`block text-[11px] font-medium ${T.muted} mb-1.5`}>Your Name</label>
                  <input type="text" value={account.ownerName} onChange={e => updateAccount('ownerName', e.target.value)}
                    placeholder="Full name" className={inputCls} />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={`block text-[11px] font-medium ${T.muted} mb-1.5`}>Email</label>
                  <input type="email" value={account.email} onChange={e => updateAccount('email', e.target.value)}
                    placeholder="you@business.ca" className={inputCls} />
                </div>
                <div>
                  <label className={`block text-[11px] font-medium ${T.muted} mb-1.5`}>Phone</label>
                  <input type="tel" value={account.phone} onChange={e => updateAccount('phone', e.target.value)}
                    placeholder="(604) 555-1234" className={inputCls} />
                </div>
              </div>
              <div>
                <label className={`block text-[11px] font-medium ${T.muted} mb-1.5`}>Province</label>
                <select value={province} onChange={e => setProvince(e.target.value)}
                  className={inputCls}>
                  <option value="">Select province...</option>
                  {PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={`block text-[11px] font-medium ${T.muted} mb-1.5`}>Password</label>
                  <input type="password" value={account.password} onChange={e => updateAccount('password', e.target.value)}
                    placeholder="Min 6 characters" className={inputCls} />
                </div>
                <div>
                  <label className={`block text-[11px] font-medium ${T.muted} mb-1.5`}>Confirm Password</label>
                  <input type="password" value={account.confirmPassword} onChange={e => updateAccount('confirmPassword', e.target.value)}
                    placeholder="Confirm password" className={inputCls} />
                </div>
              </div>
            </div>
            <div className={`flex items-center gap-2 text-[11px] ${T.muted}/50`}>
              <Shield size={12} /> Your data is encrypted with bank-level security
            </div>
            <div className="flex justify-end">
              <button onClick={handleAccountNext} disabled={saving} className={btnPrimary}>
                {saving ? <Loader2 size={14} className="animate-spin" /> : null}
                {saving ? 'Creating Account...' : 'Next: Connect POS'} <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* ═══ POS ═══ */}
        {step === 'pos' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className={`text-xl font-bold ${T.text}`}>Connect Your POS</h1>
              <p className={`text-[13px] ${T.muted} mt-1`}>We'll pull in your transaction history to start generating insights</p>
            </div>
            <POSSystemPicker
              value={posProvider}
              onChange={(posKey: string) => setPosProvider(posKey)}
              mode="new-customer"
              portalContext="canada"
              currency="CAD"
            />
            <div className="flex justify-between">
              <button onClick={() => setStep('account')} className={btnBack}><ArrowLeft size={14} /> Back</button>
              <button onClick={handlePosNext} disabled={saving || !posProvider} className={btnPrimary}>
                {saving ? <Loader2 size={14} className="animate-spin" /> : null}
                {saving ? 'Connecting...' : 'Next: Inventory'} <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* ═══ Inventory ═══ */}
        {step === 'inventory' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className={`text-xl font-bold ${T.text}`}>Inventory &amp; Cost of Goods</h1>
              <p className={`text-[13px] ${T.muted} mt-1`}>Upload your inventory to unlock margin analysis &amp; product insights</p>
            </div>
            <div className={`${cardCls} space-y-4`}>
              <div className="flex items-center gap-3">
                <button onClick={() => fileInputRef.current?.click()}
                  className={`flex items-center gap-2 px-4 py-2.5 text-[12px] font-medium ${T.text} ${T.cardBg} rounded-lg hover:bg-[#1a2420] ${T.cardBorder} transition-colors`}>
                  <Upload size={14} /> Upload CSV
                </button>
                <input ref={fileInputRef} type="file" accept=".csv" onChange={handleCsvUpload} className="hidden" />
                {csvUploaded && <span className={`text-[11px] ${T.accentTxt} flex items-center gap-1`}><CheckCircle2 size={12} /> {inventoryItems.length} items imported</span>}
                <span className={`text-[10px] ${T.muted}/40 ml-auto`}>Columns: name, category, cost, supplier, unit</span>
              </div>
              <div className={`text-[10px] ${T.muted}/40 text-center py-1`}>— or add manually —</div>
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {inventoryItems.map((item) => (
                  <div key={item.id} className="grid grid-cols-12 gap-2 items-center">
                    <input type="text" value={item.name} onChange={e => updateInventoryItem(item.id, 'name', e.target.value)}
                      placeholder="Item name" className={`col-span-3 px-2 py-2 text-[11px] rounded ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-[#6b7a74]/20 ${T.focusBorder} focus:outline-none`} />
                    <input type="text" value={item.category} onChange={e => updateInventoryItem(item.id, 'category', e.target.value)}
                      placeholder="Category" className={`col-span-2 px-2 py-2 text-[11px] rounded ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-[#6b7a74]/20 ${T.focusBorder} focus:outline-none`} />
                    <input type="number" value={item.costPerUnit} onChange={e => updateInventoryItem(item.id, 'costPerUnit', e.target.value)}
                      placeholder="CA$" className={`col-span-2 px-2 py-2 text-[11px] rounded ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-[#6b7a74]/20 ${T.focusBorder} focus:outline-none`} />
                    <input type="text" value={item.supplier} onChange={e => updateInventoryItem(item.id, 'supplier', e.target.value)}
                      placeholder="Supplier" className={`col-span-3 px-2 py-2 text-[11px] rounded ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-[#6b7a74]/20 ${T.focusBorder} focus:outline-none`} />
                    <select value={item.unit} onChange={e => updateInventoryItem(item.id, 'unit', e.target.value)}
                      className={`col-span-1 px-1 py-2 text-[10px] rounded ${T.inputBg} ${T.inputBorder} ${T.muted} focus:outline-none`}>
                      <option value="each">ea</option><option value="lb">lb</option><option value="oz">oz</option><option value="case">case</option>
                    </select>
                    <button onClick={() => removeInventoryItem(item.id)} className="col-span-1 p-1 text-[#6b7a74]/30 hover:text-red-400 transition-colors">
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
              <button onClick={addInventoryItem} className={`flex items-center gap-1.5 text-[12px] ${T.accentTxt} hover:text-[#F5F5F7] transition-colors`}>
                <Plus size={14} /> Add Item
              </button>
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep('pos')} className={btnBack}><ArrowLeft size={14} /> Back</button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep('staff')} className={`text-[12px] ${T.muted} hover:text-[#F5F5F7] transition-colors`}>Skip for now</button>
                <button onClick={handleInventoryNext} disabled={saving} className={btnPrimary}>
                  {saving ? <Loader2 size={14} className="animate-spin" /> : null} Next: Staff <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ═══ Staff ═══ */}
        {step === 'staff' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className={`text-xl font-bold ${T.text}`}>Add Your Team</h1>
              <p className={`text-[13px] ${T.muted} mt-1`}>We'll use this for labor cost analysis and staffing optimization</p>
            </div>
            <div className={`${cardCls} space-y-3`}>
              {staffMembers.map((member) => (
                <div key={member.id} className="grid grid-cols-12 gap-2 items-center">
                  <input type="text" value={member.name} onChange={e => updateStaffMember(member.id, 'name', e.target.value)}
                    placeholder="Name" className={`col-span-4 px-3 py-2.5 text-[12px] rounded-lg ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-[#6b7a74]/20 ${T.focusBorder} focus:outline-none`} />
                  <select value={member.role} onChange={e => updateStaffMember(member.id, 'role', e.target.value)}
                    className={`col-span-4 px-3 py-2.5 text-[12px] rounded-lg ${T.inputBg} ${T.inputBorder} ${T.text} focus:outline-none`}>
                    <option value="">Role...</option>
                    <option value="Manager">Manager</option><option value="Cashier">Cashier</option>
                    <option value="Server">Server</option><option value="Cook">Cook</option>
                    <option value="Barista">Barista</option><option value="Bartender">Bartender</option>
                    <option value="Host">Host</option><option value="Other">Other</option>
                  </select>
                  <input type="number" value={member.hourlyRate} onChange={e => updateStaffMember(member.id, 'hourlyRate', e.target.value)}
                    placeholder="CA$/hr" className={`col-span-3 px-3 py-2.5 text-[12px] rounded-lg ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-[#6b7a74]/20 ${T.focusBorder} focus:outline-none`} />
                  <button onClick={() => removeStaffMember(member.id)} className="col-span-1 p-1 text-[#6b7a74]/30 hover:text-red-400 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              <button onClick={addStaffMember} className={`flex items-center gap-1.5 text-[12px] ${T.accentTxt} hover:text-[#F5F5F7] transition-colors`}>
                <Plus size={14} /> Add Staff Member
              </button>
              {staffMembers.length === 0 && (
                <p className={`text-[11px] ${T.muted}/40 text-center py-4`}>
                  Add your team members to unlock labor cost insights and staffing recommendations
                </p>
              )}
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep('inventory')} className={btnBack}><ArrowLeft size={14} /> Back</button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep('schedule')} className={`text-[12px] ${T.muted} hover:text-[#F5F5F7] transition-colors`}>Skip for now</button>
                <button onClick={handleStaffNext} disabled={saving} className={btnPrimary}>
                  Next: Schedule <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ═══ Schedule ═══ */}
        {step === 'schedule' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className={`text-xl font-bold ${T.text}`}>Upload Your Schedule</h1>
              <p className={`text-[13px] ${T.muted} mt-1`}>Snap a photo of your weekly schedule — we'll extract the data automatically</p>
            </div>
            <div className={cardCls}>
              {schedulePreview ? (
                <div className="space-y-3">
                  <div className={`relative rounded-lg overflow-hidden ${T.cardBorder}`}>
                    <img src={schedulePreview} alt="Schedule" className={`w-full max-h-[300px] object-contain ${T.pageBg}`} />
                    <button onClick={() => { setScheduleImage(null); setSchedulePreview(null) }}
                      className={`absolute top-2 right-2 p-1.5 rounded-full ${T.pageBg}/80 ${T.muted} hover:text-white transition-colors`}>
                      <X size={14} />
                    </button>
                  </div>
                  <div className={`flex items-center gap-2 text-[11px] ${T.accentTxt}`}>
                    <CheckCircle2 size={12} /> Schedule photo ready — we'll process it with OCR
                  </div>
                </div>
              ) : (
                <div onClick={() => scheduleInputRef.current?.click()}
                  className={`flex flex-col items-center justify-center py-12 cursor-pointer rounded-lg border-2 border-dashed ${T.cardBorder} hover:border-[#00d4aa]/30 transition-colors`}>
                  <div className="w-14 h-14 rounded-full bg-[#00d4aa]/10 flex items-center justify-center mb-3">
                    <Camera size={24} className={T.accentTxt} />
                  </div>
                  <p className={`text-[13px] font-medium ${T.text}`}>Take a photo or upload an image</p>
                  <p className={`text-[11px] ${T.muted} mt-1`}>JPG, PNG, or PDF — we'll extract shift data</p>
                </div>
              )}
              <input ref={scheduleInputRef} type="file" accept="image/*,.pdf" capture="environment" onChange={handleScheduleUpload} className="hidden" />
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep('staff')} className={btnBack}><ArrowLeft size={14} /> Back</button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep('checkout')} className={`text-[12px] ${T.muted} hover:text-[#F5F5F7] transition-colors`}>Skip for now</button>
                <button onClick={handleScheduleNext} disabled={saving} className={btnPrimary}>
                  {saving ? <Loader2 size={14} className="animate-spin" /> : null} Next: Payment <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ═══ Checkout ═══ */}
        {step === 'checkout' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className={`text-xl font-bold ${T.text}`}>
                {paymentComplete ? 'Payment Confirmed!' : 'Activate Your Subscription'}
              </h1>
              <p className={`text-[13px] ${T.muted} mt-1`}>
                {paymentComplete
                  ? 'Your dashboard is ready — pay the invoice from your email at your convenience'
                  : "We'll send a Square invoice to your email — pay when ready"}
              </p>
            </div>

            {paymentComplete ? (
              <div className="rounded-xl p-6 border border-[#00d4aa]/30 bg-[#00d4aa]/5 text-center">
                <div className="w-14 h-14 rounded-full bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 size={28} className={T.accentTxt} />
                </div>
                <p className={`text-[14px] font-medium ${T.text}`}>Invoices Sent!</p>
                <p className={`text-[12px] ${T.muted} mt-1`}>
                  Two invoices sent to <span className={T.text}>{account.email}</span>:
                </p>
                <div className={`mt-2 space-y-1 text-[11px] ${T.muted}`}>
                  <p>1. <span className={T.text}>CA${monthlyPriceCAD}</span> — Setup fee (due in 3 days)</p>
                  <p>2. <span className={T.text}>CA${monthlyPriceCAD}/mo</span> — Monthly recurring (due in 30 days)</p>
                </div>
                <p className={`text-[11px] ${T.muted}/60 mt-2`}>
                  Pay via the links in your email — your dashboard is ready to use now
                </p>
              </div>
            ) : (
              <div className={`${cardCls} space-y-4`}>
                <div className={`rounded-lg p-4 ${T.pageBg} ${T.cardBorder}`}>
                  <div className="flex justify-between items-center mb-3">
                    <span className={`text-[13px] font-medium ${T.text}`}>Meridian Analytics (Canada)</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#00d4aa]/10 text-[#00d4aa] font-medium border border-[#00d4aa]/20">
                      {prefill.plan || 'Standard'}
                    </span>
                  </div>
                  <div className="space-y-2 text-[12px]">
                    <div className={`flex justify-between ${T.muted}`}>
                      <span>Setup fee (due in 3 days)</span>
                      <span className={T.text}>CA${monthlyPriceCAD}.00</span>
                    </div>
                    <div className={`flex justify-between ${T.muted}`}>
                      <span>Monthly recurring (starts day 30)</span>
                      <span className={T.text}>CA${monthlyPriceCAD}.00/mo</span>
                    </div>
                    <div className={`flex justify-between ${T.muted}`}>
                      <span>Commitment</span>
                      <span className={T.text}>Cancel anytime</span>
                    </div>
                    <div className={`border-t ${T.cardBorder} pt-2 flex justify-between`}>
                      <span className={`font-medium ${T.muted}`}>Invoices sent to your email</span>
                    </div>
                  </div>
                </div>

                {checkoutError && (
                  <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[12px] flex items-start gap-2">
                    <AlertCircle size={14} className="mt-0.5 shrink-0" />
                    <div>
                      <p>{checkoutError}</p>
                      <button onClick={() => setCheckoutError(null)} className="text-[11px] text-red-400/60 hover:text-red-400 mt-1 underline">Dismiss</button>
                    </div>
                  </div>
                )}

                <button onClick={handleSquareCheckout} disabled={checkoutLoading}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3.5 text-[14px] font-semibold text-white bg-[#006AFF] rounded-lg hover:bg-[#0055CC] disabled:opacity-50 transition-colors">
                  {checkoutLoading ? (
                    <><Loader2 size={16} className="animate-spin" /> Creating Invoice...</>
                  ) : (
                    <><CreditCard size={16} /> Send Invoice to My Email</>
                  )}
                </button>

                <div className={`flex items-center justify-center gap-2 text-[10px] ${T.muted}/40`}>
                  <Shield size={10} /> Secured by Square &bull; 256-bit encryption
                </div>

                <div className="rounded-lg p-3 bg-[#00d4aa]/5 border border-[#00d4aa]/15">
                  <p className={`text-[11px] ${T.muted} leading-relaxed`}>
                    <span className={`${T.accentTxt} font-medium`}>How billing works:</span> You'll receive two Square invoices via email — a one-time
                    setup fee and your monthly recurring subscription. Pay at your convenience through the secure links.
                    We'll review and reconfirm your plan every 3 months. Cancel anytime from your dashboard settings.
                  </p>
                </div>
              </div>
            )}

            <div className="flex justify-between">
              {!paymentComplete && (
                <button onClick={() => setStep('schedule')} className={btnBack}><ArrowLeft size={14} /> Back</button>
              )}
              {paymentComplete && (
                <div className="w-full flex justify-center">
                  <button onClick={startProcessing}
                    className={`flex items-center gap-2 px-8 py-3 text-[14px] font-medium text-[#0a0f0d] ${T.accentBg} rounded-lg ${T.accentHover} transition-colors shadow-[0_0_30px_rgba(0,212,170,0.15)]`}>
                    Launch My Dashboard <ArrowRight size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══ Processing ═══ */}
        {step === 'processing' && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-16 h-16 rounded-full bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center mb-6 animate-pulse">
              <Loader2 size={28} className="text-[#00d4aa] animate-spin" />
            </div>
            <h2 className={`text-lg font-bold ${T.text} mb-2`}>Setting Up Your Dashboard</h2>
            <div className="space-y-2 w-full max-w-xs">
              {processingSteps.map((label, i) => (
                <div key={label} className={`flex items-center gap-2 text-[12px] transition-all duration-300 ${
                  i < processingStep ? 'text-[#00d4aa]' : i === processingStep ? 'text-[#F5F5F7]' : 'text-[#6b7a74]/20'
                }`}>
                  {i < processingStep ? <CheckCircle2 size={12} /> : i === processingStep ? <Loader2 size={12} className="animate-spin" /> : <div className="w-3 h-3" />}
                  {label}
                </div>
              ))}
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
              Your dashboard is live. We're already analyzing your data and generating insights.
            </p>
            <button onClick={() => navigate('/canada/dashboard')}
              className={`flex items-center gap-2 px-8 py-3 text-[14px] font-medium text-[#0a0f0d] ${T.accentBg} rounded-lg ${T.accentHover} transition-colors shadow-[0_0_30px_rgba(0,212,170,0.2)]`}>
              Go to Dashboard <ArrowRight size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
