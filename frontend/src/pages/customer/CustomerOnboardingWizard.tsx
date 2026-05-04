import { useState, useEffect, useRef, type ChangeEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowRight, ArrowLeft, CheckCircle2, Loader2, Upload, Plus, Trash2,
  Store, User, Wifi, Package, Users, Calendar, Camera, Shield,
  X, CreditCard, AlertCircle, ExternalLink,
} from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import POSSelectorPanel from '@/components/POSSelectorPanel'
import type { POSSystem } from '@/data/pos-systems'

type Step = 'account' | 'pos' | 'inventory' | 'staff' | 'schedule' | 'checkout' | 'processing' | 'done'

const STEPS: { key: Step; label: string; icon: typeof Store }[] = [
  { key: 'account', label: 'Account', icon: User },
  { key: 'pos', label: 'Connect POS', icon: Wifi },
  { key: 'inventory', label: 'Inventory', icon: Package },
  { key: 'staff', label: 'Staff', icon: Users },
  { key: 'schedule', label: 'Schedule', icon: Calendar },
  { key: 'checkout', label: 'Payment', icon: CreditCard },
]

const POS_PROVIDERS = [
  { id: 'square', label: 'Square', color: '#006AFF', fields: [{ key: 'access_token', label: 'Access Token', placeholder: 'EAAAl...' }] },
  { id: 'clover', label: 'Clover', color: '#43B02A', fields: [{ key: 'api_key', label: 'API Key', placeholder: 'Your Clover API key' }, { key: 'merchant_id', label: 'Merchant ID', placeholder: 'XXXXXXXXXX' }] },
  { id: 'toast', label: 'Toast', color: '#FF6600', fields: [{ key: 'api_key', label: 'API Key', placeholder: 'Your Toast API key' }, { key: 'restaurant_guid', label: 'Restaurant GUID', placeholder: 'xxxxxxxx-xxxx-...' }] },
  { id: 'lightspeed', label: 'Lightspeed', color: '#E4002B', fields: [{ key: 'api_key', label: 'API Key', placeholder: 'Your Lightspeed API key' }] },
  { id: 'other', label: 'Other', color: '#7C5CFF', fields: [{ key: 'provider_name', label: 'Provider Name', placeholder: 'e.g. Revel, Shopify POS' }, { key: 'api_key', label: 'API Key', placeholder: 'Your API key' }] },
]

interface StaffMember {
  id: string
  name: string
  role: string
  hourlyRate: string
}

interface InventoryItem {
  id: string
  name: string
  category: string
  costPerUnit: string
  supplier: string
  unit: string
}

function uid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function CustomerOnboardingWizard() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { signup, connectPos, org } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const scheduleInputRef = useRef<HTMLInputElement>(null)

  // Pre-fill from SR link
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

  // POS
  const [posProvider, setPosProvider] = useState<string | null>(null)
  const [posFields, setPosFields] = useState<Record<string, string>>({})

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

  // Check for Square checkout callback
  useEffect(() => {
    const checkoutStatus = searchParams.get('checkout')
    if (checkoutStatus === 'success') {
      const savedToken = sessionStorage.getItem('meridian_onboard_token')
      if (savedToken) {
        sessionStorage.removeItem('meridian_onboard_token')
      }
      setPaymentComplete(true)
      setStep('checkout')
    }
  }, [searchParams])

  function updateAccount(key: string, value: string) {
    setAccount(a => ({ ...a, [key]: value }))
    setError(null)
  }

  // ── Account Step ──
  async function handleAccountNext() {
    if (!account.businessName.trim()) { setError('Business name is required'); return }
    if (!account.ownerName.trim()) { setError('Your name is required'); return }
    if (!account.email.trim()) { setError('Email is required'); return }
    if (!account.phone.trim()) { setError('Phone number is required'); return }
    if (!account.password || account.password.length < 6) { setError('Password must be at least 6 characters'); return }
    if (account.password !== account.confirmPassword) { setError('Passwords don\'t match'); return }

    setSaving(true)
    setError(null)

    try {
      const err = await signup(account.email, account.password, account.ownerName, account.businessName)
      if (err && err !== '__confirm_email__') {
        setError(err)
        setSaving(false)
        return
      }
      setStep('pos')
    } catch (err: any) {
      setError(err.message || 'Signup failed')
    } finally {
      setSaving(false)
    }
  }

  // ── POS Step ──
  async function handlePosNext() {
    if (!posProvider) { setError('Please select your POS provider'); return }

    const provider = POS_PROVIDERS.find(p => p.id === posProvider)
    if (provider) {
      const missing = provider.fields.find(f => !posFields[f.key]?.trim())
      if (missing) { setError(`${missing.label} is required`); return }
    }

    setSaving(true)
    setError(null)

    try {
      const apiKey = Object.values(posFields).join('::')
      const err = await connectPos(posProvider, apiKey)
      if (err) { setError(err); setSaving(false); return }
      setStep('inventory')
    } catch (err: any) {
      setError(err.message || 'Connection failed')
    } finally {
      setSaving(false)
    }
  }

  // ── Inventory Step ──
  function addInventoryItem() {
    setInventoryItems(items => [...items, { id: uid(), name: '', category: '', costPerUnit: '', supplier: '', unit: 'each' }])
  }

  function updateInventoryItem(id: string, key: keyof InventoryItem, value: string) {
    setInventoryItems(items => items.map(item => item.id === id ? { ...item, [key]: value } : item))
  }

  function removeInventoryItem(id: string) {
    setInventoryItems(items => items.filter(item => item.id !== id))
  }

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
          items.push({
            id: uid(),
            name: cols[nameIdx] || '',
            category: catIdx >= 0 ? (cols[catIdx] || '') : '',
            costPerUnit: costIdx >= 0 ? (cols[costIdx] || '') : '',
            supplier: supplierIdx >= 0 ? (cols[supplierIdx] || '') : '',
            unit: unitIdx >= 0 ? (cols[unitIdx] || 'each') : 'each',
          })
        }

        setInventoryItems(items)
        setCsvUploaded(true)
        setError(null)
      } catch {
        setError('Failed to parse CSV. Please check the format.')
      }
    }
    reader.readAsText(file)
  }

  async function handleInventoryNext() {
    if (inventoryItems.length > 0 && supabase && org) {
      setSaving(true)
      try {
        const rows = inventoryItems
          .filter(item => item.name.trim())
          .map(item => ({
            org_id: org.org_id,
            name: item.name,
            category: item.category || null,
            cost_per_unit: item.costPerUnit ? parseFloat(item.costPerUnit) : null,
            supplier: item.supplier || null,
            unit: item.unit || 'each',
          }))
        if (rows.length > 0) {
          await supabase.from('products').upsert(rows, { onConflict: 'org_id,name' })
        }
      } catch (err) { console.warn('Inventory save warning:', err) }
      finally { setSaving(false) }
    }
    setStep('staff')
  }

  // ── Staff Step ──
  function addStaffMember() {
    setStaffMembers(members => [...members, { id: uid(), name: '', role: '', hourlyRate: '' }])
  }

  function updateStaffMember(id: string, key: keyof StaffMember, value: string) {
    setStaffMembers(members => members.map(m => m.id === id ? { ...m, [key]: value } : m))
  }

  function removeStaffMember(id: string) {
    setStaffMembers(members => members.filter(m => m.id !== id))
  }

  async function handleStaffNext() {
    if (staffMembers.length > 0 && supabase && org) {
      setSaving(true)
      try {
        const rows = staffMembers
          .filter(m => m.name.trim())
          .map(m => ({
            org_id: org.org_id,
            name: m.name,
            role: m.role || 'Staff',
            hourly_rate: m.hourlyRate ? parseFloat(m.hourlyRate) : null,
          }))
        if (rows.length > 0) {
          await supabase.from('users').insert(rows)
        }
      } catch (err) { console.warn('Staff save warning:', err) }
      finally { setSaving(false) }
    }
    setStep('schedule')
  }

  // ── Schedule Step ──
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
          org_id: org.org_id,
          event_type: 'schedule_upload',
          title: 'Staff Schedule Upload',
          notes: `Uploaded: ${scheduleImage.name}. Pending OCR processing.`,
          file_path: fileName,
          status: 'pending_processing',
        })
      } catch (err) { console.warn('Schedule upload warning:', err) }
      finally { setSaving(false) }
    }
    setStep('checkout')
  }

  // ── Checkout Step ──
  async function handleSquareCheckout() {
    setCheckoutLoading(true)
    setCheckoutError(null)

    const planLabel = (prefill.plan || 'Standard').replace(/^\w/, (c: string) => c.toUpperCase())

    try {
      // Send both invoices in parallel: upfront fee + monthly recurring
      const [upfrontRes, recurringRes] = await Promise.all([
        fetch(`${API_BASE}/api/billing/create-invoice`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            org_id: org?.org_id,
            amount_cents: monthlyPrice * 100,
            customer_email: account.email,
            description: `Meridian Analytics - ${planLabel} Plan (Setup Fee)`,
            due_days: 3,
          }),
        }),
        fetch(`${API_BASE}/api/billing/create-invoice`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            org_id: org?.org_id,
            amount_cents: monthlyPrice * 100,
            customer_email: account.email,
            description: `Meridian Analytics - ${planLabel} Plan (Monthly Recurring)`,
            due_days: 30,
          }),
        }),
      ])

      const upfrontOk = upfrontRes.ok
      const recurringOk = recurringRes.ok

      if (upfrontOk && recurringOk) {
        setPaymentComplete(true)
        return
      }

      const failedRes = !upfrontOk ? upfrontRes : recurringRes
      const errorData = await failedRes.json().catch(() => null)
      setCheckoutError(
        errorData?.detail ||
        'Unable to create invoices. Please try again or contact support at help@meridian.tips'
      )
    } catch (err: any) {
      console.error('Invoice creation failed:', err)
      setCheckoutError(
        'Billing system is temporarily unavailable. Please try again in a moment or contact support at help@meridian.tips'
      )
    } finally {
      setCheckoutLoading(false)
    }
  }

  // ── Processing ──
  function startProcessing() {
    setStep('processing')
    setProcessingStep(0)
    let current = 0
    const interval = setInterval(() => {
      current++
      if (current >= processingSteps.length) {
        clearInterval(interval)
        setStep('done')
      } else {
        setProcessingStep(current)
      }
    }, 1200)
  }

  // ── Render ──
  const currentStepIdx = STEPS.findIndex(s => s.key === step)

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-xl">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-6">
          <MeridianEmblem size={32} />
          <MeridianWordmark className="text-lg" />
        </div>

        {/* Progress */}
        {step !== 'done' && step !== 'processing' && (
          <div className="flex items-center gap-1 mb-8">
            {STEPS.map((s, i) => {
              const isActive = i === currentStepIdx
              const isDone = i < currentStepIdx
              return (
                <div key={s.key} className="flex-1 flex flex-col gap-1.5">
                  <div className={`h-1 rounded-full transition-all duration-500 ${isDone ? 'bg-[#17C5B0]' : isActive ? 'bg-[#1A8FD6]' : 'bg-[#1F1F23]'}`} />
                  <span className={`text-[9px] font-medium text-center ${isActive ? 'text-[#F5F5F7]' : isDone ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/30'}`}>
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

        {/* ═══ Step: Account ═══ */}
        {step === 'account' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className="text-xl font-bold text-[#F5F5F7]">Welcome to Meridian</h1>
              <p className="text-[13px] text-[#A1A1A8] mt-1">Set up your account in a few minutes and start seeing insights</p>
            </div>

            <div className="rounded-xl p-6 border border-[#1F1F23] bg-[#0F0F12] space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Business Name</label>
                  <input type="text" value={account.businessName} onChange={e => updateAccount('businessName', e.target.value)}
                    placeholder="Your business name" className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none" />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Your Name</label>
                  <input type="text" value={account.ownerName} onChange={e => updateAccount('ownerName', e.target.value)}
                    placeholder="Full name" className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none" />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Email</label>
                  <input type="email" value={account.email} onChange={e => updateAccount('email', e.target.value)}
                    placeholder="you@business.com" className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none" />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Phone</label>
                  <input type="tel" value={account.phone} onChange={e => updateAccount('phone', e.target.value)}
                    placeholder="(555) 123-4567" className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none" />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Password</label>
                  <input type="password" value={account.password} onChange={e => updateAccount('password', e.target.value)}
                    placeholder="Min 6 characters" className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none" />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-[#A1A1A8] mb-1.5">Confirm Password</label>
                  <input type="password" value={account.confirmPassword} onChange={e => updateAccount('confirmPassword', e.target.value)}
                    placeholder="Confirm password" className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/50 focus:outline-none" />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 text-[11px] text-[#A1A1A8]/50">
              <Shield size={12} /> Your data is encrypted with bank-level security
            </div>

            <div className="flex justify-end">
              <button onClick={handleAccountNext} disabled={saving}
                className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] disabled:opacity-50 transition-colors">
                {saving ? <Loader2 size={14} className="animate-spin" /> : null}
                {saving ? 'Creating Account...' : 'Next: Connect POS'} <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* ═══ Step: POS ═══ */}
        {step === 'pos' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className="text-xl font-bold text-[#F5F5F7]">Connect Your POS</h1>
              <p className="text-[13px] text-[#A1A1A8] mt-1">We'll pull in your transaction history to start generating insights</p>
            </div>

            <POSSelectorPanel
              onSelect={(system: POSSystem) => {
                setPosProvider(system.key)
                setPosFields({})
              }}
              onConnect={(system: POSSystem) => {
                setPosProvider(system.key)
                handlePosNext()
              }}
            />

            <div className="flex justify-between">
              <button onClick={() => setStep('account')} className="flex items-center gap-2 px-4 py-2.5 text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
                <ArrowLeft size={14} /> Back
              </button>
              <button onClick={handlePosNext} disabled={saving || !posProvider}
                className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] disabled:opacity-50 transition-colors">
                {saving ? <Loader2 size={14} className="animate-spin" /> : null}
                {saving ? 'Connecting...' : 'Next: Inventory'} <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* ═══ Step: Inventory ═══ */}
        {step === 'inventory' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className="text-xl font-bold text-[#F5F5F7]">Inventory &amp; Cost of Goods</h1>
              <p className="text-[13px] text-[#A1A1A8] mt-1">Upload your inventory to unlock margin analysis &amp; product insights</p>
            </div>

            <div className="rounded-xl p-6 border border-[#1F1F23] bg-[#0F0F12] space-y-4">
              <div className="flex items-center gap-3">
                <button onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-2.5 text-[12px] font-medium text-[#F5F5F7] bg-[#1F1F23] rounded-lg hover:bg-[#2A2A2E] border border-[#2A2A2E] transition-colors">
                  <Upload size={14} /> Upload CSV
                </button>
                <input ref={fileInputRef} type="file" accept=".csv" onChange={handleCsvUpload} className="hidden" />
                {csvUploaded && <span className="text-[11px] text-[#17C5B0] flex items-center gap-1"><CheckCircle2 size={12} /> {inventoryItems.length} items imported</span>}
                <span className="text-[10px] text-[#A1A1A8]/40 ml-auto">Columns: name, category, cost, supplier, unit</span>
              </div>

              <div className="text-[10px] text-[#A1A1A8]/40 text-center py-1">— or add manually —</div>

              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {inventoryItems.map((item) => (
                  <div key={item.id} className="grid grid-cols-12 gap-2 items-center">
                    <input type="text" value={item.name} onChange={e => updateInventoryItem(item.id, 'name', e.target.value)}
                      placeholder="Item name" className="col-span-3 px-2 py-2 text-[11px] rounded bg-[#0A0A0B] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/20 focus:border-[#1A8FD6]/50 focus:outline-none" />
                    <input type="text" value={item.category} onChange={e => updateInventoryItem(item.id, 'category', e.target.value)}
                      placeholder="Category" className="col-span-2 px-2 py-2 text-[11px] rounded bg-[#0A0A0B] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/20 focus:border-[#1A8FD6]/50 focus:outline-none" />
                    <input type="number" value={item.costPerUnit} onChange={e => updateInventoryItem(item.id, 'costPerUnit', e.target.value)}
                      placeholder="Cost $" className="col-span-2 px-2 py-2 text-[11px] rounded bg-[#0A0A0B] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/20 focus:border-[#1A8FD6]/50 focus:outline-none" />
                    <input type="text" value={item.supplier} onChange={e => updateInventoryItem(item.id, 'supplier', e.target.value)}
                      placeholder="Supplier" className="col-span-3 px-2 py-2 text-[11px] rounded bg-[#0A0A0B] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/20 focus:border-[#1A8FD6]/50 focus:outline-none" />
                    <select value={item.unit} onChange={e => updateInventoryItem(item.id, 'unit', e.target.value)}
                      className="col-span-1 px-1 py-2 text-[10px] rounded bg-[#0A0A0B] border border-[#2A2A2E] text-[#A1A1A8] focus:outline-none">
                      <option value="each">ea</option><option value="lb">lb</option><option value="oz">oz</option><option value="case">case</option>
                    </select>
                    <button onClick={() => removeInventoryItem(item.id)} className="col-span-1 p-1 text-[#A1A1A8]/30 hover:text-red-400 transition-colors">
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>

              <button onClick={addInventoryItem}
                className="flex items-center gap-1.5 text-[12px] text-[#1A8FD6] hover:text-[#F5F5F7] transition-colors">
                <Plus size={14} /> Add Item
              </button>
            </div>

            <div className="flex justify-between">
              <button onClick={() => setStep('pos')} className="flex items-center gap-2 px-4 py-2.5 text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
                <ArrowLeft size={14} /> Back
              </button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep('staff')} className="text-[12px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">Skip for now</button>
                <button onClick={handleInventoryNext} disabled={saving}
                  className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] disabled:opacity-50 transition-colors">
                  {saving ? <Loader2 size={14} className="animate-spin" /> : null} Next: Staff <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ═══ Step: Staff ═══ */}
        {step === 'staff' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className="text-xl font-bold text-[#F5F5F7]">Add Your Team</h1>
              <p className="text-[13px] text-[#A1A1A8] mt-1">We'll use this for labor cost analysis and staffing optimization</p>
            </div>

            <div className="rounded-xl p-6 border border-[#1F1F23] bg-[#0F0F12] space-y-3">
              {staffMembers.map((member) => (
                <div key={member.id} className="grid grid-cols-12 gap-2 items-center">
                  <input type="text" value={member.name} onChange={e => updateStaffMember(member.id, 'name', e.target.value)}
                    placeholder="Name" className="col-span-4 px-3 py-2.5 text-[12px] rounded-lg bg-[#0A0A0B] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/20 focus:border-[#1A8FD6]/50 focus:outline-none" />
                  <select value={member.role} onChange={e => updateStaffMember(member.id, 'role', e.target.value)}
                    className="col-span-4 px-3 py-2.5 text-[12px] rounded-lg bg-[#0A0A0B] border border-[#2A2A2E] text-[#F5F5F7] focus:outline-none">
                    <option value="">Role...</option>
                    <option value="Manager">Manager</option>
                    <option value="Cashier">Cashier</option>
                    <option value="Server">Server</option>
                    <option value="Cook">Cook</option>
                    <option value="Barista">Barista</option>
                    <option value="Bartender">Bartender</option>
                    <option value="Host">Host</option>
                    <option value="Other">Other</option>
                  </select>
                  <input type="number" value={member.hourlyRate} onChange={e => updateStaffMember(member.id, 'hourlyRate', e.target.value)}
                    placeholder="$/hr" className="col-span-3 px-3 py-2.5 text-[12px] rounded-lg bg-[#0A0A0B] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/20 focus:border-[#1A8FD6]/50 focus:outline-none" />
                  <button onClick={() => removeStaffMember(member.id)} className="col-span-1 p-1 text-[#A1A1A8]/30 hover:text-red-400 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}

              <button onClick={addStaffMember}
                className="flex items-center gap-1.5 text-[12px] text-[#1A8FD6] hover:text-[#F5F5F7] transition-colors">
                <Plus size={14} /> Add Staff Member
              </button>

              {staffMembers.length === 0 && (
                <p className="text-[11px] text-[#A1A1A8]/40 text-center py-4">
                  Add your team members to unlock labor cost insights and staffing recommendations
                </p>
              )}
            </div>

            <div className="flex justify-between">
              <button onClick={() => setStep('inventory')} className="flex items-center gap-2 px-4 py-2.5 text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
                <ArrowLeft size={14} /> Back
              </button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep('schedule')} className="text-[12px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">Skip for now</button>
                <button onClick={handleStaffNext} disabled={saving}
                  className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] disabled:opacity-50 transition-colors">
                  Next: Schedule <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ═══ Step: Schedule ═══ */}
        {step === 'schedule' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className="text-xl font-bold text-[#F5F5F7]">Upload Your Schedule</h1>
              <p className="text-[13px] text-[#A1A1A8] mt-1">Snap a photo of your weekly schedule — we'll extract the data automatically</p>
            </div>

            <div className="rounded-xl p-6 border border-[#1F1F23] bg-[#0F0F12]">
              {schedulePreview ? (
                <div className="space-y-3">
                  <div className="relative rounded-lg overflow-hidden border border-[#1F1F23]">
                    <img src={schedulePreview} alt="Schedule" className="w-full max-h-[300px] object-contain bg-[#0A0A0B]" />
                    <button onClick={() => { setScheduleImage(null); setSchedulePreview(null) }}
                      className="absolute top-2 right-2 p-1.5 rounded-full bg-[#0A0A0B]/80 text-[#A1A1A8] hover:text-white transition-colors">
                      <X size={14} />
                    </button>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-[#17C5B0]">
                    <CheckCircle2 size={12} /> Schedule photo ready — we'll process it with OCR
                  </div>
                </div>
              ) : (
                <div onClick={() => scheduleInputRef.current?.click()}
                  className="flex flex-col items-center justify-center py-12 cursor-pointer rounded-lg border-2 border-dashed border-[#1F1F23] hover:border-[#1A8FD6]/30 transition-colors">
                  <div className="w-14 h-14 rounded-full bg-[#1A8FD6]/10 flex items-center justify-center mb-3">
                    <Camera size={24} className="text-[#1A8FD6]" />
                  </div>
                  <p className="text-[13px] font-medium text-[#F5F5F7]">Take a photo or upload an image</p>
                  <p className="text-[11px] text-[#A1A1A8] mt-1">JPG, PNG, or PDF — we'll extract shift data</p>
                </div>
              )}
              <input ref={scheduleInputRef} type="file" accept="image/*,.pdf" capture="environment" onChange={handleScheduleUpload} className="hidden" />
            </div>

            <div className="flex justify-between">
              <button onClick={() => setStep('staff')} className="flex items-center gap-2 px-4 py-2.5 text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
                <ArrowLeft size={14} /> Back
              </button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep('checkout')} className="text-[12px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">Skip for now</button>
                <button onClick={handleScheduleNext} disabled={saving}
                  className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] disabled:opacity-50 transition-colors">
                  {saving ? <Loader2 size={14} className="animate-spin" /> : null} Next: Payment <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ═══ Step: Checkout ═══ */}
        {step === 'checkout' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className="text-xl font-bold text-[#F5F5F7]">
                {paymentComplete ? 'Payment Confirmed!' : 'Activate Your Subscription'}
              </h1>
              <p className="text-[13px] text-[#A1A1A8] mt-1">
                {paymentComplete
                  ? 'Your dashboard is ready — pay the invoice from your email at your convenience'
                  : 'We\'ll send a Square invoice to your email — pay when ready'}
              </p>
            </div>

            {paymentComplete ? (
              <div className="rounded-xl p-6 border border-[#17C5B0]/30 bg-[#17C5B0]/5 text-center">
                <div className="w-14 h-14 rounded-full bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 size={28} className="text-[#17C5B0]" />
                </div>
                <p className="text-[14px] font-medium text-[#F5F5F7]">Invoices Sent!</p>
                <p className="text-[12px] text-[#A1A1A8] mt-1">
                  Two invoices sent to <span className="text-[#F5F5F7]">{account.email}</span>:
                </p>
                <div className="mt-2 space-y-1 text-[11px] text-[#A1A1A8]">
                  <p>1. <span className="text-[#F5F5F7]">${monthlyPrice}</span> — Setup fee (due in 3 days)</p>
                  <p>2. <span className="text-[#F5F5F7]">${monthlyPrice}/mo</span> — Monthly recurring (due in 30 days)</p>
                </div>
                <p className="text-[11px] text-[#A1A1A8]/60 mt-2">
                  Pay via the links in your email — your dashboard is ready to use now
                </p>
              </div>
            ) : (
              <div className="rounded-xl p-6 border border-[#1F1F23] bg-[#0F0F12] space-y-4">
                {/* Plan summary */}
                <div className="rounded-lg p-4 bg-[#0A0A0B] border border-[#1F1F23]">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-[13px] font-medium text-[#F5F5F7]">Meridian Analytics</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#1A8FD6]/10 text-[#1A8FD6] font-medium border border-[#1A8FD6]/20">
                      {prefill.plan || 'Standard'}
                    </span>
                  </div>
                  <div className="space-y-2 text-[12px]">
                    <div className="flex justify-between text-[#A1A1A8]">
                      <span>Setup fee (due in 3 days)</span>
                      <span className="text-[#F5F5F7]">${monthlyPrice}.00</span>
                    </div>
                    <div className="flex justify-between text-[#A1A1A8]">
                      <span>Monthly recurring (starts day 30)</span>
                      <span className="text-[#F5F5F7]">${monthlyPrice}.00/mo</span>
                    </div>
                    <div className="flex justify-between text-[#A1A1A8]">
                      <span>Commitment</span>
                      <span className="text-[#F5F5F7]">Cancel anytime</span>
                    </div>
                    <div className="border-t border-[#1F1F23] pt-2 flex justify-between">
                      <span className="font-medium text-[#A1A1A8]">Invoices sent to your email</span>
                    </div>
                  </div>
                </div>

                {checkoutError && (
                  <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[12px] flex items-start gap-2">
                    <AlertCircle size={14} className="mt-0.5 shrink-0" />
                    <div>
                      <p>{checkoutError}</p>
                      <button onClick={() => setCheckoutError(null)} className="text-[11px] text-red-400/60 hover:text-red-400 mt-1 underline">
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}

                {/* Square invoice button */}
                <button onClick={handleSquareCheckout} disabled={checkoutLoading}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3.5 text-[14px] font-semibold text-white bg-[#006AFF] rounded-lg hover:bg-[#0055CC] disabled:opacity-50 transition-colors">
                  {checkoutLoading ? (
                    <><Loader2 size={16} className="animate-spin" /> Creating Invoice...</>
                  ) : (
                    <><CreditCard size={16} /> Send Invoice to My Email</>
                  )}
                </button>

                <div className="flex items-center justify-center gap-2 text-[10px] text-[#A1A1A8]/40">
                  <Shield size={10} /> Secured by Square • 256-bit encryption
                </div>

                {/* Billing details */}
                <div className="rounded-lg p-3 bg-[#17C5B0]/5 border border-[#17C5B0]/15">
                  <p className="text-[11px] text-[#A1A1A8] leading-relaxed">
                    <span className="text-[#17C5B0] font-medium">How billing works:</span> You'll receive two Square invoices via email — a one-time
                    setup fee and your monthly recurring subscription. Pay at your convenience through the secure links.
                    We'll review and reconfirm your plan every 3 months. Cancel anytime from your dashboard settings.
                  </p>
                </div>
              </div>
            )}

            <div className="flex justify-between">
              {!paymentComplete && (
                <button onClick={() => setStep('schedule')} className="flex items-center gap-2 px-4 py-2.5 text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
                  <ArrowLeft size={14} /> Back
                </button>
              )}
              {paymentComplete && (
                <div className="w-full flex justify-center">
                  <button onClick={startProcessing}
                    className="flex items-center gap-2 px-8 py-3 text-[14px] font-medium text-white bg-[#17C5B0] rounded-lg hover:bg-[#14B09D] transition-colors shadow-[0_0_30px_rgba(23,197,176,0.15)]">
                    Launch My Dashboard <ArrowRight size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══ Step: Processing ═══ */}
        {step === 'processing' && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-16 h-16 rounded-full bg-[#1A8FD6]/15 border border-[#1A8FD6]/30 flex items-center justify-center mb-6 animate-pulse">
              <Loader2 size={28} className="text-[#1A8FD6] animate-spin" />
            </div>
            <h2 className="text-lg font-bold text-[#F5F5F7] mb-2">Setting Up Your Dashboard</h2>
            <div className="space-y-2 w-full max-w-xs">
              {processingSteps.map((label, i) => (
                <div key={label} className={`flex items-center gap-2 text-[12px] transition-all duration-300 ${
                  i < processingStep ? 'text-[#17C5B0]' : i === processingStep ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/20'
                }`}>
                  {i < processingStep ? <CheckCircle2 size={12} /> : i === processingStep ? <Loader2 size={12} className="animate-spin" /> : <div className="w-3 h-3" />}
                  {label}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═══ Step: Done ═══ */}
        {step === 'done' && (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-20 h-20 rounded-full bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center mb-6">
              <CheckCircle2 size={40} className="text-[#17C5B0]" />
            </div>
            <h2 className="text-2xl font-bold text-[#F5F5F7] mb-2">You're All Set!</h2>
            <p className="text-[14px] text-[#A1A1A8] text-center max-w-sm mb-8">
              Your dashboard is live. We're already analyzing your data and generating insights.
            </p>
            <button onClick={() => navigate('/app')}
              className="flex items-center gap-2 px-8 py-3 text-[14px] font-medium text-white bg-[#17C5B0] rounded-lg hover:bg-[#14B09D] transition-colors shadow-[0_0_30px_rgba(23,197,176,0.2)]">
              Go to Dashboard <ArrowRight size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
