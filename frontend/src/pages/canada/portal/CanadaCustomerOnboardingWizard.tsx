import { useState, useEffect, useRef, useCallback, type ChangeEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowRight, ArrowLeft, CheckCircle2, Loader2, Upload, Plus, Trash2,
  Store, User, Wifi, Package, Users, Calendar, Camera, Shield,
  X, CreditCard, AlertCircle, FileText,
} from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import { useAuth } from '@/lib/auth'
import { supabase, getAuthHeaders } from '@/lib/supabase'
import POSSystemPicker from '@/components/POSSystemPicker'
import { getPlan as getCanadaPlan, closestMonthlyPlanCad } from '@/lib/canada-proposal-plans'

// ── Canada Theme ──
const T = {
  pageBg:    'bg-pm-canada-bg',
  cardBg:    'bg-pm-canada-surface',
  cardBorder:'border-pm-canada-border',
  inputBg:   'bg-pm-canada-bg',
  inputBorder:'border-pm-canada-border',
  accent:    '#00d4aa',
  accentBg:  'bg-pm-accent',
  accentHover:'hover:bg-pm-accent/90',
  accentTxt: 'text-pm-accent',
  accentBorder:'border-pm-accent',
  muted:     'text-pm-canada-text-muted',
  text:      'text-pm-text',
  focusBorder:'focus:border-pm-accent/50',
} as const

const inputCls = `w-full px-3 py-2.5 text-sm-tight rounded-lg ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-pm-canada-text-muted/40 ${T.focusBorder} focus:outline-none`
const btnPrimary = `flex items-center gap-2 px-6 py-2.5 text-sm-tight font-medium ${T.accentBg} text-pm-canada-bg rounded-lg ${T.accentHover} disabled:opacity-50 transition-colors`
const btnBack = `flex items-center gap-2 px-4 py-2.5 text-sm-tight ${T.muted} hover:text-pm-text transition-colors`
const cardCls = `rounded-xl p-6 ${T.cardBorder} ${T.cardBg}`

type Step = 'account' | 'sla' | 'pos' | 'inventory' | 'staff' | 'schedule' | 'checkout' | 'processing' | 'done'

const STEPS: { key: Step; label: string; icon: typeof Store }[] = [
  { key: 'account', label: 'Account', icon: User },
  { key: 'sla', label: 'Agreement', icon: FileText },
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
    setup: searchParams.get('setup') || '',
    freemonth: searchParams.get('freemonth') || '',
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
  // Whether Clover 1-click OAuth is configured server-side. Default false so we
  // never surface a button that 503s; flipped on once /api/clover/status confirms.
  const [cloverOAuthAvailable, setCloverOAuthAvailable] = useState(false)

  // SLA (Service Agreement)
  const [slaSignature, setSlaSignature] = useState('')
  const [slaAgreed, setSlaAgreed] = useState(false)
  const [slaSubmitted, setSlaSubmitted] = useState(false)

  // Inventory
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([])
  const [csvUploaded, setCsvUploaded] = useState(false)
  const [inventoryDocs, setInventoryDocs] = useState<{ file: File; preview: string | null; status: 'pending' | 'processing' | 'done' }[]>([])
  const inventoryDocRef = useRef<HTMLInputElement>(null)

  // Staff
  const [staffMembers, setStaffMembers] = useState<StaffMember[]>([])

  // Schedule
  const [scheduleImage, setScheduleImage] = useState<File | null>(null)
  const [schedulePreview, setSchedulePreview] = useState<string | null>(null)

  // Checkout
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [paymentComplete, setPaymentComplete] = useState(false)
  const [checkoutError, setCheckoutError] = useState<string | null>(null)
  // prefill.price comes from the rep portal link and is ALREADY in CAD — do not re-apply CAD_RATE.
  // Fall back to the CAD Standard plan price (USD 250 × 1.37 = CA$343) rather than a bare 250.
  const monthlyPriceCAD = prefill.price ? parseInt(prefill.price) : getCanadaPlan('standard').price
  // Setup fee + first-month-free flow through from the rep's custom setup in the
  // portal link so the agreement text and day-1 invoice match the rep's quote.
  const setupFeeCAD = prefill.setup ? Math.max(0, parseInt(prefill.setup) || 0) : 0
  const firstMonthFree = prefill.freemonth === '1' || prefill.freemonth === 'true'
  const dueTodayCAD = (firstMonthFree ? 0 : monthlyPriceCAD) + setupFeeCAD

  // Processing — 20-minute AI analysis timer (persists across page reloads)
  // Hard data (revenue, products, staff, schedules) is available immediately from POS.
  // The timer covers AI-generated analysis: insights, anomalies, forecasts, patterns.
  const PROCESSING_KEY = 'meridian_ca_processing_start'
  const PROCESSING_DONE_KEY = 'meridian_ca_processing_done'
  const TOTAL_DURATION = 20 * 60 // 1200 seconds

  const processingPhases = [
    { label: 'Connecting to POS system...', endsAt: 20, ai: false },
    { label: 'Syncing revenue & transaction data...', endsAt: 40, ai: false },
    { label: 'Loading products & menu items...', endsAt: 55, ai: false },
    { label: 'Importing staff & schedule records...', endsAt: 70, ai: false },
    { label: 'Analyzing revenue trends & seasonality...', endsAt: 190, ai: true },
    { label: 'Detecting sales anomalies & outliers...', endsAt: 310, ai: true },
    { label: 'Calculating profit margins per item...', endsAt: 430, ai: true },
    { label: 'Building menu engineering matrix...', endsAt: 550, ai: true },
    { label: 'Identifying peak hour patterns...', endsAt: 670, ai: true },
    { label: 'Modeling customer segments...', endsAt: 790, ai: true },
    { label: 'Generating staffing recommendations...', endsAt: 890, ai: true },
    { label: 'Forecasting next 30-day revenue...', endsAt: 1000, ai: true },
    { label: 'Ranking top actions for your business...', endsAt: 1100, ai: true },
    { label: 'Compiling AI insights report...', endsAt: 1170, ai: true },
    { label: 'Finalizing your dashboard...', endsAt: TOTAL_DURATION, ai: true },
  ]

  const [processingElapsed, setProcessingElapsed] = useState(0)

  const currentPhaseIdx = processingPhases.findIndex(p => processingElapsed < p.endsAt)
  const processingPct = Math.min(100, Math.round((processingElapsed / TOTAL_DURATION) * 100))
  const remainingSec = Math.max(0, TOTAL_DURATION - processingElapsed)
  const remainingMin = Math.ceil(remainingSec / 60)

  // Square checkout callback — clear param after handling to prevent re-trigger
  useEffect(() => {
    const checkoutStatus = searchParams.get('checkout')
    if (checkoutStatus === 'success') {
      const savedToken = sessionStorage.getItem('meridian_onboard_token')
      if (savedToken) sessionStorage.removeItem('meridian_onboard_token')
      setPaymentComplete(true)
      setStep('checkout')
      const cleaned = new URLSearchParams(searchParams)
      cleaned.delete('checkout')
      window.history.replaceState({}, '', `${window.location.pathname}${cleaned.toString() ? '?' + cleaned.toString() : ''}`)
    }
  }, [searchParams])

  // Probe whether Clover 1-click is configured (CLOVER_APP_ID/SECRET set), so we
  // only show the OAuth button when it would actually work instead of leading the
  // merchant to a 503.
  useEffect(() => {
    if (!org?.org_id) return
    let cancelled = false
    fetch(`${API_BASE}/api/clover/status?org_id=${encodeURIComponent(org.org_id)}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (!cancelled && d) setCloverOAuthAvailable(!!d.oauth_available) })
      .catch(() => { /* leave false — manual path still available downstream */ })
    return () => { cancelled = true }
  }, [org?.org_id])

  function updateAccount(key: string, value: string) {
    setAccount(a => ({ ...a, [key]: value }))
    setError(null)
  }

  // ── Account ──
  async function handleAccountNext() {
    if (!account.businessName.trim()) { setError('Business name is required'); return }
    if (!account.ownerName.trim()) { setError('Your name is required'); return }
    if (!account.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(account.email)) { setError('Please enter a valid email address'); return }
    if (!account.phone.trim()) { setError('Phone number is required'); return }
    if (!account.password || account.password.length < 8) { setError('Password must be at least 8 characters'); return }
    if (account.password !== account.confirmPassword) { setError("Passwords don't match"); return }
    setSaving(true); setError(null)
    try {
      const meta: Record<string, string> = { country: 'CA' }
      if (province) meta.province = province
      const err = await signup(account.email, account.password, account.ownerName, account.businessName, meta)
      if (err && err !== '__confirm_email__') { setError(err); setSaving(false); return }

      // Persist province as the primary business location
      if (province && supabase && org?.org_id) {
        try {
          await supabase.from('business_locations').upsert({
            business_id: org.org_id,
            name: 'Primary',
            state: province,
            is_primary: true,
          }, { onConflict: 'id' })
        } catch {}
      }

      setStep('sla')
    } catch (err: any) { setError(err.message || 'Signup failed') }
    finally { setSaving(false) }
  }

  // ── Service Agreement (SLA) ──
  async function handleSlaSubmit() {
    if (!slaSignature.trim() || slaSignature.trim().length < 2) {
      setError('Please type your full legal name as your signature.')
      return
    }
    if (!slaAgreed) {
      setError('Please confirm you have read and agree to the Service Agreement.')
      return
    }
    setSaving(true); setError(null)
    try {
      const headers = await getAuthHeaders()
      const resp = await fetch(`${API_BASE}/api/canada/sign-sla`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          customer_email: account.email,
          signature_name: slaSignature.trim(),
          business_name: account.businessName,
          province: province || null,
          org_id: org?.org_id || null,
          monthly_price_cad_cents: Math.round(monthlyPriceCAD * 100),
          setup_fee_cad_cents: Math.round(setupFeeCAD * 100),
          pos_system: posProvider || null,
          rep_id: searchParams.get('rep') || null,
          rep_name: searchParams.get('rep_name') || null,
        }),
      })
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        // Do NOT proceed on a failed SLA write — a signature silently vanishing
        // is a compliance problem. Surface the error and keep the customer on
        // this step so they can retry.
        console.error('[SLA] persistence failed:', body)
        setError(body.detail || body.message || 'We could not save your signed agreement. Please try again — if it keeps failing, contact your Meridian rep.')
        return
      }
      setSlaSubmitted(true)
      setStep('pos')
    } catch (err: any) {
      console.error('[SLA] error:', err)
      // Block on a failed SLA write — see above.
      setError(err?.message || 'We could not save your signed agreement. Please check your connection and try again.')
    } finally {
      setSaving(false)
    }
  }

  // ── POS ──
  async function handlePosNext() {
    if (!posProvider) { setError('Please select your POS provider'); return }
    setSaving(true); setError(null)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || ''
      const orgId = org?.org_id
      if (orgId) {
        const headers = await getAuthHeaders()
        await fetch(`${apiUrl}/api/pos/select`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ org_id: orgId, pos_system: posProvider, connection_status: 'pending' }),
        })
      } else {
        // P1: connectPos signature changed to credentials object. Pass
        // {} for the selection-only path (credential collection lives
        // in a later step / the rep-facing portal).
        // P2: forward the rep_id from the URL when the rep onboarded
        // the merchant via a `?rep=…` referral link, so future
        // credential connects pick it up for attribution.
        const repId = searchParams.get('rep') || null
        const err = await connectPos(posProvider, {}, repId)
        if (err) { setError(err); setSaving(false); return }
      }
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

  function handleInventoryDocUpload(e: ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files) return
    const newDocs = Array.from(files).map(file => {
      const isImage = file.type.startsWith('image/')
      return {
        file,
        preview: isImage ? URL.createObjectURL(file) : null,
        status: 'pending' as const,
      }
    })
    setInventoryDocs(prev => [...prev, ...newDocs])
    e.target.value = ''
  }

  function removeInventoryDoc(idx: number) {
    setInventoryDocs(prev => { const next = [...prev]; next.splice(idx, 1); return next })
  }

  async function handleInventoryNext() {
    if (!supabase || !org || !org.org_id) {
      if ((inventoryItems.length > 0 || inventoryDocs.length > 0) && !org?.org_id) {
        setError('Account not fully created — go back and retry signup'); return
      }
      setStep('staff'); return
    }
    setSaving(true)
    try {
      if (inventoryItems.length > 0) {
        // products has no category/cost_per_unit/supplier/unit columns — writing
        // them 400s the whole step. Map cost (dollars) → cost_cents (int).
        const rows = inventoryItems.filter(item => item.name.trim()).map(item => ({
          org_id: org.org_id, name: item.name, is_active: true,
          cost_cents: item.costPerUnit ? Math.round(parseFloat(item.costPerUnit) * 100) : null,
        }))
        if (rows.length > 0) await supabase.from('products').upsert(rows, { onConflict: 'org_id,name' })
      }
      for (const doc of inventoryDocs) {
        if (doc.status !== 'pending') continue
        const ext = doc.file.name.split('.').pop() || 'bin'
        const fileName = `${org.org_id}/inventory_doc_${Date.now()}.${ext}`
        await supabase.storage.from('inventory-docs').upload(fileName, doc.file)
        await supabase.from('inventory_document_uploads').insert({
          org_id: org.org_id,
          file_name: doc.file.name,
          file_path: fileName,
          file_type: doc.file.type,
          status: 'pending_processing',
        })
      }
    } catch (err: any) { setError(err.message || 'Failed to save inventory — please try again'); setSaving(false); return }
    finally { setSaving(false) }
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
      if (!org.org_id) { setError('Account not fully created — go back and retry signup'); return }
      setSaving(true)
      try {
        const rows = staffMembers.filter(m => m.name.trim()).map(m => ({
          business_id: org.org_id, email: `${m.name.trim().toLowerCase().replace(/\s+/g, '.')}@placeholder.local`,
          full_name: m.name, role: m.role === 'Manager' ? 'manager' : 'staff',
        }))
        if (rows.length > 0) await supabase.from('business_users').insert(rows)
      } catch (err: any) { setError(err.message || 'Failed to save staff — please try again'); setSaving(false); return }
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
      if (!org.org_id) { setError('Account not fully created — go back and retry signup'); return }
      setSaving(true)
      try {
        const fileName = `${org.org_id}/schedule_${Date.now()}.${scheduleImage.name.split('.').pop()}`
        await supabase.storage.from('schedules').upload(fileName, scheduleImage)
        await supabase.from('schedule_uploads').insert({
          org_id: org.org_id, event_type: 'schedule_upload', title: 'Staff Schedule Upload',
          notes: `Uploaded: ${scheduleImage.name}. Pending OCR processing.`,
          file_path: fileName, status: 'pending_processing',
        })
      } catch (err: any) { setError(err.message || 'Failed to upload schedule — please try again'); setSaving(false); return }
      finally { setSaving(false) }
    }
    setStep('checkout')
  }

  // ── Checkout ──
  async function handleSquareCheckout() {
    if (!org?.org_id) { setCheckoutError('Account not fully created — go back and retry signup'); return }
    setCheckoutLoading(true); setCheckoutError(null)
    const planLabel = prefill.plan
      ? prefill.plan.replace(/^\w/, (c: string) => c.toUpperCase())
      : closestMonthlyPlanCad(monthlyPriceCAD).label
    try {
      const authHeaders = await getAuthHeaders()
      // Day-1 invoice mirrors the rep's quote exactly: real setup fee + first
      // month, with the first month waived when the rep toggled it free.
      // Skipped entirely when nothing is due today (free month + no setup fee).
      const upfrontLabel = setupFeeCAD > 0
        ? (firstMonthFree ? 'Setup Fee — First Month Free' : 'Setup Fee + First Month')
        : 'First Month'
      const invoiceReqs: Promise<Response>[] = []
      if (dueTodayCAD > 0) {
        invoiceReqs.push(fetch(`${API_BASE}/api/billing/create-invoice`, {
          method: 'POST', headers: authHeaders,
          body: JSON.stringify({
            org_id: org?.org_id, amount_cents: dueTodayCAD * 100,
            customer_email: account.email,
            description: `Meridian AI Business Solutions (Canada) - ${planLabel} Plan (${upfrontLabel})`,
            due_days: 3,
            currency: 'CAD',
          }),
        }))
      }
      invoiceReqs.push(fetch(`${API_BASE}/api/billing/create-invoice`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({
          org_id: org?.org_id, amount_cents: monthlyPriceCAD * 100,
          customer_email: account.email,
          description: `Meridian AI Business Solutions (Canada) - ${planLabel} Plan (Monthly Recurring)`,
          due_days: 30,
          currency: 'CAD',
        }),
      }))
      const invoiceResults = await Promise.all(invoiceReqs)
      if (invoiceResults.every(r => r.ok)) {
        try {
          const provRes = await fetch(`${API_BASE}/api/onboarding/provision-customer`, {
            method: 'POST', headers: authHeaders,
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
          if (!provRes.ok) {
            const provBody = await provRes.json().catch(() => null)
            console.error('Provision failed:', provBody)
            setCheckoutError('Invoices sent but account setup had an issue. Contact support at help@meridian.tips if your dashboard isn\'t ready.')
          }
        } catch (provisionErr) {
          console.error('Provision call failed:', provisionErr)
          setCheckoutError('Invoices sent but account setup had an issue. Contact support at help@meridian.tips if your dashboard isn\'t ready.')
        }
        setPaymentComplete(true)
        return
      }
      const failedRes = invoiceResults.find(r => !r.ok)!
      const errorData = await failedRes.json().catch(() => null)
      setCheckoutError(errorData?.detail || 'Unable to create invoices. Please try again or contact support at help@meridian.tips')
    } catch (err: any) {
      console.error('Invoice creation failed:', err)
      setCheckoutError('Billing system is temporarily unavailable. Please try again in a moment or contact support at help@meridian.tips')
    } finally { setCheckoutLoading(false) }
  }

  // ── Processing timer (time-based, persists across reloads) ──
  const processingInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  const tickProcessing = useCallback(() => {
    try {
      const startStr = localStorage.getItem(PROCESSING_KEY)
      if (!startStr) return
      const elapsed = Math.floor((Date.now() - Number(startStr)) / 1000)
      if (elapsed >= TOTAL_DURATION) {
        if (processingInterval.current) clearInterval(processingInterval.current)
        processingInterval.current = null
        localStorage.removeItem(PROCESSING_KEY)
        localStorage.setItem(PROCESSING_DONE_KEY, '1')
        setProcessingElapsed(TOTAL_DURATION)
        setStep('done')
      } else {
        setProcessingElapsed(elapsed)
      }
    } catch { /* private browsing */ }
  }, [TOTAL_DURATION])

  // Resume processing on mount if timer is active, or skip to done if already completed
  useEffect(() => {
    try {
      if (localStorage.getItem(PROCESSING_DONE_KEY)) {
        setStep('done')
        return
      }
      const startStr = localStorage.getItem(PROCESSING_KEY)
      if (startStr && step !== 'done') {
        const elapsed = Math.floor((Date.now() - Number(startStr)) / 1000)
        if (elapsed >= TOTAL_DURATION) {
          localStorage.removeItem(PROCESSING_KEY)
          localStorage.setItem(PROCESSING_DONE_KEY, '1')
          setStep('done')
        } else {
          setStep('processing')
          setProcessingElapsed(elapsed)
          processingInterval.current = setInterval(tickProcessing, 1000)
        }
      }
    } catch { /* ignore */ }
    return () => {
      if (processingInterval.current) clearInterval(processingInterval.current)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function startProcessing() {
    try {
      // Already completed — skip straight to done
      if (localStorage.getItem(PROCESSING_DONE_KEY)) {
        setStep('done')
        return
      }
      // Timer already running — resume instead of restarting
      const existing = localStorage.getItem(PROCESSING_KEY)
      if (!existing) {
        localStorage.setItem(PROCESSING_KEY, String(Date.now()))
      }
    } catch { /* ignore */ }
    if (processingInterval.current) clearInterval(processingInterval.current)
    setStep('processing')
    tickProcessing()
    processingInterval.current = setInterval(tickProcessing, 1000)
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
          <span className="text-2xs font-semibold text-pm-accent uppercase tracking-widest">Canada</span>
        </div>

        {/* Progress */}
        {step !== 'done' && step !== 'processing' && (
          <div className="flex items-center gap-1 mb-8">
            {STEPS.map((s, i) => {
              const isActive = i === currentStepIdx
              const isDone = i < currentStepIdx
              return (
                <div key={s.key} className="flex-1 flex flex-col gap-1.5">
                  <div className={`h-1 rounded-full transition-all duration-500 ${isDone ? 'bg-pm-accent' : isActive ? 'bg-pm-accent' : 'bg-pm-canada-border'}`} />
                  <span className={`text-[9px] font-medium text-center ${isActive ? 'text-pm-text' : isDone ? 'text-pm-accent' : 'text-pm-canada-text-muted/30'}`}>
                    {s.label}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm-tight flex items-center gap-2">
            <AlertCircle size={14} /> {error}
          </div>
        )}

        {/* ═══ Account ═══ */}
        {step === 'account' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className={`text-xl font-bold ${T.text}`}>Welcome to Meridian</h1>
              <p className={`text-sm-tight ${T.muted} mt-1`}>Set up your account in a few minutes and start seeing insights</p>
            </div>
            <div className={`${cardCls} space-y-4`}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={`block text-2xs font-medium ${T.muted} mb-1.5`}>Business Name</label>
                  <input type="text" value={account.businessName} onChange={e => updateAccount('businessName', e.target.value)}
                    placeholder="Your business name" className={inputCls} />
                </div>
                <div>
                  <label className={`block text-2xs font-medium ${T.muted} mb-1.5`}>Your Name</label>
                  <input type="text" value={account.ownerName} onChange={e => updateAccount('ownerName', e.target.value)}
                    placeholder="Full name" className={inputCls} />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={`block text-2xs font-medium ${T.muted} mb-1.5`}>Email</label>
                  <input type="email" value={account.email} onChange={e => updateAccount('email', e.target.value)}
                    placeholder="you@business.ca" className={inputCls} />
                </div>
                <div>
                  <label className={`block text-2xs font-medium ${T.muted} mb-1.5`}>Phone</label>
                  <input type="tel" value={account.phone} onChange={e => updateAccount('phone', e.target.value)}
                    placeholder="(604) 555-1234" className={inputCls} />
                </div>
              </div>
              <div>
                <label className={`block text-2xs font-medium ${T.muted} mb-1.5`}>Province</label>
                <select value={province} onChange={e => setProvince(e.target.value)}
                  className={inputCls}>
                  <option value="">Select province...</option>
                  {PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={`block text-2xs font-medium ${T.muted} mb-1.5`}>Password</label>
                  <input type="password" value={account.password} onChange={e => updateAccount('password', e.target.value)}
                    placeholder="Min 6 characters" className={inputCls} />
                </div>
                <div>
                  <label className={`block text-2xs font-medium ${T.muted} mb-1.5`}>Confirm Password</label>
                  <input type="password" value={account.confirmPassword} onChange={e => updateAccount('confirmPassword', e.target.value)}
                    placeholder="Confirm password" className={inputCls} />
                </div>
              </div>
            </div>
            <div className={`flex items-center gap-2 text-2xs ${T.muted}/50`}>
              <Shield size={12} /> Your data is encrypted with bank-level security
            </div>
            <div className="flex justify-end">
              <button onClick={handleAccountNext} disabled={saving} className={btnPrimary}>
                {saving ? <Loader2 size={14} className="animate-spin" /> : null}
                {saving ? 'Creating Account...' : 'Next: Service Agreement'} <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* ═══ SLA ═══ */}
        {step === 'sla' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className={`text-xl font-bold ${T.text}`}>Service Agreement</h1>
              <p className={`text-sm-tight ${T.muted} mt-1`}>
                Please review and sign to activate your Meridian subscription.
                {province === 'Quebec' ? ' Includes Quebec Law 25 disclosures.' : ' PIPEDA-compliant.'}
              </p>
            </div>

            <div className={`${cardCls} max-h-96 overflow-y-auto space-y-3 text-xs ${T.text} leading-relaxed`}>
              <h2 className="text-sm font-bold">Meridian AI Analytics Services — Service Agreement</h2>
              <p className={T.muted}>
                This Agreement is entered into between <span className={T.text}>Meridian AI Business Solutions</span> ("Provider")
                and <span className={T.text}>{account.businessName || '[Business Name]'}</span> ("Client"),
                represented by <span className={T.text}>{account.ownerName || '[Owner Name]'}</span>.
              </p>

              <h3 className="text-sm-tight font-semibold mt-3">1. Services</h3>
              <p className={T.muted}>Provider will deliver AI-powered POS analytics, including transaction analysis,
                revenue forecasting, anomaly detection, and operational recommendations for the Client's business.</p>

              <h3 className="text-sm-tight font-semibold mt-3">2. Subscription &amp; Billing</h3>
              <p className={T.muted}>Monthly subscription of <span className={T.text}>CA${monthlyPriceCAD.toLocaleString()}</span>{' '}
                billed via Square.
                {setupFeeCAD > 0 && <> A one-time setup fee of <span className={T.text}>CA${setupFeeCAD.toLocaleString()}</span> is payable upon signup.</>}
                {firstMonthFree && <> The first month of service is free; recurring monthly billing begins in the second month.</>}
                {' '}Cancel anytime; no long-term commitment. All amounts in Canadian dollars.</p>

              <h3 className="text-sm-tight font-semibold mt-3">3. Data Privacy — PIPEDA</h3>
              <p className={T.muted}>Client data is collected, used, and disclosed in accordance with Canada's Personal
                Information Protection and Electronic Documents Act (PIPEDA). Client retains ownership of all transaction
                data. Provider acts as a data processor only and will not sell or share Client data with third parties for
                advertising. Data is encrypted at rest and in transit (AES-256, TLS 1.3).</p>

              {province === 'Quebec' && (
                <>
                  <h3 className="text-sm-tight font-semibold mt-3">4. Quebec — Law 25 (Loi 25)</h3>
                  <p className={T.muted}>For Quebec-based Clients, Provider complies with An Act respecting the protection of
                    personal information in the private sector, as amended by Law 25. Client is informed that personal
                    information may be stored on servers located in Canada and the United States. Client has the right to
                    access, correct, and delete personal information at any time by contacting <span className={T.text}>privacy@meridian.tips</span>.
                    Provider maintains a designated Privacy Officer reachable at the same address. Breach notifications will be
                    made to the Commission d'accès à l'information du Québec within the timeframes prescribed by Law 25.</p>
                </>
              )}

              <h3 className="text-sm-tight font-semibold mt-3">{province === 'Quebec' ? '5.' : '4.'} Term &amp; Termination</h3>
              <p className={T.muted}>Either party may terminate this Agreement at any time with 30 days' written notice.
                Upon termination, Provider will return or destroy all Client data within 60 days.</p>

              <h3 className="text-sm-tight font-semibold mt-3">{province === 'Quebec' ? '6.' : '5.'} Limitation of Liability</h3>
              <p className={T.muted}>Provider's total liability under this Agreement is limited to the fees paid by Client
                in the 12 months preceding the claim. Provider is not liable for indirect or consequential damages.</p>

              <h3 className="text-sm-tight font-semibold mt-3">{province === 'Quebec' ? '7.' : '6.'} Governing Law</h3>
              <p className={T.muted}>This Agreement is governed by the laws of {province || 'the Client\'s province of residence'},
                Canada. Disputes will be resolved in the courts of competent jurisdiction therein.</p>

              <p className={`${T.muted} mt-4 text-2xs italic`}>
                A copy of this signed agreement will be emailed to {account.email || 'your email address'} immediately after signing.
              </p>
            </div>

            <div className={`${cardCls} space-y-3`}>
              <div>
                <label className={`block text-2xs font-medium ${T.muted} mb-1.5`}>
                  Signature — type your full legal name to sign
                </label>
                <input
                  type="text"
                  value={slaSignature}
                  onChange={e => setSlaSignature(e.target.value)}
                  placeholder={account.ownerName || 'Your full legal name'}
                  className={inputCls}
                />
              </div>
              <label className={`flex items-start gap-2 text-xs ${T.text} cursor-pointer`}>
                <input
                  type="checkbox"
                  checked={slaAgreed}
                  onChange={e => setSlaAgreed(e.target.checked)}
                  className="mt-0.5"
                />
                <span>
                  I have read and agree to the Meridian Service Agreement above, and I confirm I have authority to bind
                  {' '}{account.businessName || 'my business'} to this Agreement.
                </span>
              </label>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
            )}

            <div className="flex justify-between items-center">
              <button onClick={() => setStep('account')} className={btnBack}>
                <ArrowLeft size={14} /> Back
              </button>
              <button
                onClick={handleSlaSubmit}
                disabled={saving || !slaSignature.trim() || !slaAgreed}
                className={btnPrimary}
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                {saving ? 'Signing...' : 'Sign &amp; Continue'} <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* ═══ POS ═══ */}
        {step === 'pos' && (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h1 className={`text-xl font-bold ${T.text}`}>Connect Your POS</h1>
              <p className={`text-sm-tight ${T.muted} mt-1`}>We'll pull in your transaction history to start generating insights</p>
            </div>
            <POSSystemPicker
              value={posProvider}
              onChange={(posKey: string) => setPosProvider(posKey)}
              mode="new-customer"
              portalContext="canada"
              currency="CAD"
            />
            {/* P2: real OAuth UX for Square and Clover. When the rep
                selects one of these providers, surface a "Connect with
                <Provider>" button that redirects to the backend
                authorize endpoint. The state token signs org_id +
                rep_id (when present in the URL `?rep=…` param) so the
                callback can write pos_connections.connected_by_rep_id
                without trusting an unsigned channel.

                The merchant ends the round-trip back at
                /app/settings?oauth=success — fine for the demo flow;
                a richer post-OAuth landing for the wizard is a P3
                follow-up. */}
            {posProvider === 'square' && org?.org_id && (
              <a
                href={`${import.meta.env.VITE_API_URL || ''}/api/square/authorize?org_id=${encodeURIComponent(org.org_id)}${searchParams.get('rep') ? `&rep_id=${encodeURIComponent(searchParams.get('rep') || '')}` : ''}`}
                className={btnPrimary + ' justify-center w-full'}
                target="_blank"
                rel="noopener noreferrer"
              >
                Connect with Square (OAuth)
              </a>
            )}
            {posProvider === 'clover' && org?.org_id && cloverOAuthAvailable && (
              <a
                href={`${import.meta.env.VITE_API_URL || ''}/api/clover/authorize?org_id=${encodeURIComponent(org.org_id)}&return_to=${encodeURIComponent('/canada/dashboard')}${searchParams.get('rep') ? `&rep_id=${encodeURIComponent(searchParams.get('rep') || '')}` : ''}`}
                className={btnPrimary + ' justify-center w-full'}
                target="_blank"
                rel="noopener noreferrer"
              >
                Connect with Clover (OAuth)
              </a>
            )}
            {posProvider === 'clover' && org?.org_id && !cloverOAuthAvailable && (
              <p className="text-xs text-pm-canada-text-muted">
                One-click Clover isn&rsquo;t available right now — continue, then connect
                Clover from your merchant dashboard once you&rsquo;re set up.
              </p>
            )}
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
              <p className={`text-sm-tight ${T.muted} mt-1`}>Upload your inventory to unlock margin analysis &amp; product insights</p>
            </div>
            <div className={`${cardCls} space-y-4`}>
              <div className="flex items-center gap-3">
                <button onClick={() => fileInputRef.current?.click()}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium ${T.text} ${T.cardBg} rounded-lg hover:bg-pm-canada-border ${T.cardBorder} transition-colors`}>
                  <Upload size={14} /> Upload CSV
                </button>
                <input ref={fileInputRef} type="file" accept=".csv" onChange={handleCsvUpload} className="hidden" />
                {csvUploaded && <span className={`text-2xs ${T.accentTxt} flex items-center gap-1`}><CheckCircle2 size={12} /> {inventoryItems.length} items imported</span>}
                <span className={`text-2xs ${T.muted}/40 ml-auto`}>Columns: name, category, cost, supplier, unit</span>
              </div>
              <div className={`text-2xs ${T.muted}/40 text-center py-1`}>— or add manually —</div>
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {inventoryItems.map((item) => (
                  <div key={item.id} className="grid grid-cols-12 gap-2 items-center">
                    <input type="text" value={item.name} onChange={e => updateInventoryItem(item.id, 'name', e.target.value)}
                      placeholder="Item name" className={`col-span-3 px-2 py-2 text-2xs rounded ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-pm-canada-text-muted/20 ${T.focusBorder} focus:outline-none`} />
                    <input type="text" value={item.category} onChange={e => updateInventoryItem(item.id, 'category', e.target.value)}
                      placeholder="Category" className={`col-span-2 px-2 py-2 text-2xs rounded ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-pm-canada-text-muted/20 ${T.focusBorder} focus:outline-none`} />
                    <input type="number" value={item.costPerUnit} onChange={e => updateInventoryItem(item.id, 'costPerUnit', e.target.value)}
                      placeholder="CA$" className={`col-span-2 px-2 py-2 text-2xs rounded ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-pm-canada-text-muted/20 ${T.focusBorder} focus:outline-none`} />
                    <input type="text" value={item.supplier} onChange={e => updateInventoryItem(item.id, 'supplier', e.target.value)}
                      placeholder="Supplier" className={`col-span-3 px-2 py-2 text-2xs rounded ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-pm-canada-text-muted/20 ${T.focusBorder} focus:outline-none`} />
                    <select value={item.unit} onChange={e => updateInventoryItem(item.id, 'unit', e.target.value)}
                      className={`col-span-1 px-1 py-2 text-2xs rounded ${T.inputBg} ${T.inputBorder} ${T.muted} focus:outline-none`}>
                      <option value="each">ea</option><option value="lb">lb</option><option value="oz">oz</option><option value="case">case</option>
                    </select>
                    <button onClick={() => removeInventoryItem(item.id)} className="col-span-1 p-1 text-pm-canada-text-muted/30 hover:text-red-400 transition-colors">
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
              <button onClick={addInventoryItem} className={`flex items-center gap-1.5 text-xs ${T.accentTxt} hover:text-pm-text transition-colors`}>
                <Plus size={14} /> Add Item
              </button>
            </div>
            <div className={`${cardCls} space-y-3`}>
              <div className="flex items-center gap-2 mb-1">
                <Package size={14} className={T.accentTxt} />
                <h3 className={`text-sm-tight font-semibold ${T.text}`}>Upload Inventory Documents</h3>
              </div>
              <p className={`text-2xs ${T.muted}`}>
                Upload invoices, supplier price lists, or inventory spreadsheets — our AI will extract product names, costs, and margins automatically.
              </p>
              <div onClick={() => inventoryDocRef.current?.click()}
                className={`flex flex-col items-center justify-center py-8 cursor-pointer rounded-lg border-2 border-dashed ${T.cardBorder} hover:border-pm-accent/30 transition-colors`}>
                <div className="w-12 h-12 rounded-full bg-pm-accent/10 flex items-center justify-center mb-2">
                  <Upload size={20} className={T.accentTxt} />
                </div>
                <p className={`text-xs font-medium ${T.text}`}>Drop files or click to upload</p>
                <p className={`text-2xs ${T.muted} mt-1`}>PDF, Excel, images of invoices — any format</p>
              </div>
              <input ref={inventoryDocRef} type="file" accept=".pdf,.xlsx,.xls,.csv,.jpg,.jpeg,.png,.heic" multiple onChange={handleInventoryDocUpload} className="sr-only" />
              {inventoryDocs.length > 0 && (
                <div className="space-y-2">
                  {inventoryDocs.map((doc, idx) => (
                    <div key={idx} className={`flex items-center gap-3 px-3 py-2 rounded-lg ${T.cardBg} border ${T.cardBorder}`}>
                      <Package size={14} className={T.accentTxt} />
                      <div className="flex-1 min-w-0">
                        <p className={`text-2xs font-medium ${T.text} truncate`}>{doc.file.name}</p>
                        <p className={`text-[9px] ${T.muted}`}>{(doc.file.size / 1024).toFixed(0)} KB</p>
                      </div>
                      <span className={`text-[9px] px-2 py-0.5 rounded-full ${doc.status === 'pending' ? 'bg-yellow-500/10 text-yellow-400' : doc.status === 'processing' ? 'bg-blue-500/10 text-blue-400' : 'bg-green-500/10 text-green-400'}`}>
                        {doc.status === 'pending' ? 'Ready to process' : doc.status === 'processing' ? 'Processing...' : 'Done'}
                      </span>
                      <button onClick={() => removeInventoryDoc(idx)} className="p-1 text-pm-canada-text-muted/30 hover:text-red-400 transition-colors">
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                  <p className={`text-2xs ${T.accentTxt} flex items-center gap-1`}>
                    <Shield size={10} /> AI bot will process these after setup — extracting products, costs &amp; margins into structured tables
                  </p>
                </div>
              )}
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep('pos')} className={btnBack}><ArrowLeft size={14} /> Back</button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep('staff')} className={`text-xs ${T.muted} hover:text-pm-text transition-colors`}>Skip for now</button>
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
              <p className={`text-sm-tight ${T.muted} mt-1`}>We'll use this for labor cost analysis and staffing optimization</p>
            </div>
            <div className={`${cardCls} space-y-3`}>
              {staffMembers.map((member) => (
                <div key={member.id} className="grid grid-cols-12 gap-2 items-center">
                  <input type="text" value={member.name} onChange={e => updateStaffMember(member.id, 'name', e.target.value)}
                    placeholder="Name" className={`col-span-4 px-3 py-2.5 text-xs rounded-lg ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-pm-canada-text-muted/20 ${T.focusBorder} focus:outline-none`} />
                  <select value={member.role} onChange={e => updateStaffMember(member.id, 'role', e.target.value)}
                    className={`col-span-4 px-3 py-2.5 text-xs rounded-lg ${T.inputBg} ${T.inputBorder} ${T.text} focus:outline-none`}>
                    <option value="">Role...</option>
                    <option value="Manager">Manager</option><option value="Cashier">Cashier</option>
                    <option value="Server">Server</option><option value="Cook">Cook</option>
                    <option value="Barista">Barista</option><option value="Bartender">Bartender</option>
                    <option value="Host">Host</option><option value="Other">Other</option>
                  </select>
                  <input type="number" value={member.hourlyRate} onChange={e => updateStaffMember(member.id, 'hourlyRate', e.target.value)}
                    placeholder="CA$/hr" className={`col-span-3 px-3 py-2.5 text-xs rounded-lg ${T.inputBg} ${T.inputBorder} ${T.text} placeholder-pm-canada-text-muted/20 ${T.focusBorder} focus:outline-none`} />
                  <button onClick={() => removeStaffMember(member.id)} className="col-span-1 p-1 text-pm-canada-text-muted/30 hover:text-red-400 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              <button onClick={addStaffMember} className={`flex items-center gap-1.5 text-xs ${T.accentTxt} hover:text-pm-text transition-colors`}>
                <Plus size={14} /> Add Staff Member
              </button>
              {staffMembers.length === 0 && (
                <p className={`text-2xs ${T.muted}/40 text-center py-4`}>
                  Add your team members to unlock labor cost insights and staffing recommendations
                </p>
              )}
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep('inventory')} className={btnBack}><ArrowLeft size={14} /> Back</button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep('schedule')} className={`text-xs ${T.muted} hover:text-pm-text transition-colors`}>Skip for now</button>
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
              <p className={`text-sm-tight ${T.muted} mt-1`}>Snap a photo of your weekly schedule — we'll extract the data automatically</p>
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
                  <div className={`flex items-center gap-2 text-2xs ${T.accentTxt}`}>
                    <CheckCircle2 size={12} /> Schedule photo ready — we'll process it with OCR
                  </div>
                </div>
              ) : (
                <div onClick={() => scheduleInputRef.current?.click()}
                  className={`flex flex-col items-center justify-center py-12 cursor-pointer rounded-lg border-2 border-dashed ${T.cardBorder} hover:border-pm-accent/30 transition-colors`}>
                  <div className="w-14 h-14 rounded-full bg-pm-accent/10 flex items-center justify-center mb-3">
                    <Camera size={24} className={T.accentTxt} />
                  </div>
                  <p className={`text-sm-tight font-medium ${T.text}`}>Take a photo or upload an image</p>
                  <p className={`text-2xs ${T.muted} mt-1`}>JPG, PNG, or PDF — we'll extract shift data</p>
                </div>
              )}
              <input ref={scheduleInputRef} type="file" accept="image/*,.pdf" onChange={handleScheduleUpload} className="sr-only" />
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep('staff')} className={btnBack}><ArrowLeft size={14} /> Back</button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep('checkout')} className={`text-xs ${T.muted} hover:text-pm-text transition-colors`}>Skip for now</button>
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
              <p className={`text-sm-tight ${T.muted} mt-1`}>
                {paymentComplete
                  ? 'Your dashboard is ready — pay the invoice from your email at your convenience'
                  : "We'll send a Square invoice to your email — pay when ready"}
              </p>
            </div>

            {paymentComplete ? (
              <div className="rounded-xl p-6 border border-pm-accent/30 bg-pm-accent/5 text-center">
                <div className="w-14 h-14 rounded-full bg-pm-accent/15 border border-pm-accent/30 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 size={28} className={T.accentTxt} />
                </div>
                <p className={`text-sm font-medium ${T.text}`}>Invoices Sent!</p>
                <p className={`text-xs ${T.muted} mt-1`}>
                  {dueTodayCAD > 0 ? 'Two invoices' : 'One invoice'} sent to <span className={T.text}>{account.email}</span>:
                </p>
                <div className={`mt-2 space-y-1 text-2xs ${T.muted}`}>
                  {dueTodayCAD > 0 && (
                    <p>1. <span className={T.text}>CA${dueTodayCAD.toLocaleString()}</span> — {setupFeeCAD > 0 ? (firstMonthFree ? 'Setup fee (first month free)' : 'Setup fee + first month') : 'First month'} (due in 3 days)</p>
                  )}
                  <p>{dueTodayCAD > 0 ? '2. ' : ''}<span className={T.text}>CA${monthlyPriceCAD.toLocaleString()}/mo</span> — Monthly recurring (due in 30 days)</p>
                </div>
                <p className={`text-2xs ${T.muted}/60 mt-2`}>
                  Pay via the links in your email — your dashboard is ready to use now
                </p>
              </div>
            ) : (
              <div className={`${cardCls} space-y-4`}>
                <div className={`rounded-lg p-4 ${T.pageBg} ${T.cardBorder}`}>
                  <div className="flex justify-between items-center mb-3">
                    <span className={`text-sm-tight font-medium ${T.text}`}>Meridian AI Business Solutions (Canada)</span>
                    <span className="text-2xs px-2 py-0.5 rounded-full bg-pm-accent/10 text-pm-accent font-medium border border-pm-accent/20">
                      {prefill.plan || 'Standard'}
                    </span>
                  </div>
                  <div className="space-y-2 text-xs">
                    {setupFeeCAD > 0 && (
                      <div className={`flex justify-between ${T.muted}`}>
                        <span>One-time setup fee</span>
                        <span className={T.text}>CA${setupFeeCAD.toLocaleString()}.00</span>
                      </div>
                    )}
                    <div className={`flex justify-between ${T.muted}`}>
                      <span>First month</span>
                      <span className={T.text}>{firstMonthFree ? 'Free' : `CA$${monthlyPriceCAD.toLocaleString()}.00`}</span>
                    </div>
                    <div className={`flex justify-between ${T.muted}`}>
                      <span>Due today (invoice due in 3 days)</span>
                      <span className={T.text}>CA${dueTodayCAD.toLocaleString()}.00</span>
                    </div>
                    <div className={`flex justify-between ${T.muted}`}>
                      <span>Monthly recurring (starts day 30)</span>
                      <span className={T.text}>CA${monthlyPriceCAD.toLocaleString()}.00/mo</span>
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
                  <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-start gap-2">
                    <AlertCircle size={14} className="mt-0.5 shrink-0" />
                    <div>
                      <p>{checkoutError}</p>
                      <button onClick={() => setCheckoutError(null)} className="text-2xs text-red-400/60 hover:text-red-400 mt-1 underline">Dismiss</button>
                    </div>
                  </div>
                )}

                <button onClick={handleSquareCheckout} disabled={checkoutLoading}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3.5 text-sm font-semibold text-white bg-[#006AFF] rounded-lg hover:bg-[#0055CC] disabled:opacity-50 transition-colors">
                  {checkoutLoading ? (
                    <><Loader2 size={16} className="animate-spin" /> Creating Invoice...</>
                  ) : (
                    <><CreditCard size={16} /> Send Invoice to My Email</>
                  )}
                </button>

                <div className={`flex items-center justify-center gap-2 text-2xs ${T.muted}/40`}>
                  <Shield size={10} /> Secured by Square &bull; 256-bit encryption
                </div>

                <div className="rounded-lg p-3 bg-pm-accent/5 border border-pm-accent/15">
                  <p className={`text-2xs ${T.muted} leading-relaxed`}>
                    <span className={`${T.accentTxt} font-medium`}>How billing works:</span> You'll receive {dueTodayCAD > 0 ? 'two Square invoices' : 'one Square invoice'} via email —{' '}
                    {dueTodayCAD > 0 && <>CA${dueTodayCAD.toLocaleString()} due now ({setupFeeCAD > 0 ? (firstMonthFree ? 'setup fee — your first month is free' : 'setup fee + first month') : 'first month'}), then </>}
                    your CA${monthlyPriceCAD.toLocaleString()}/mo recurring subscription. Pay at your convenience through the secure links.
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
                    className={`flex items-center gap-2 px-8 py-3 text-sm font-medium text-pm-canada-bg ${T.accentBg} rounded-lg ${T.accentHover} transition-colors shadow-[0_0_30px_rgba(0,212,170,0.15)]`}>
                    Launch My Dashboard <ArrowRight size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══ Processing ═══ */}
        {step === 'processing' && (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="w-16 h-16 rounded-full bg-pm-accent/15 border border-pm-accent/30 flex items-center justify-center mb-5 animate-pulse">
              <Loader2 size={28} className="text-pm-accent animate-spin" />
            </div>
            <h2 className={`text-lg font-bold ${T.text} mb-1`}>Analyzing Your Business Data</h2>
            <p className={`text-xs ${T.muted} mb-6 text-center max-w-sm`}>
              Your revenue, products, and staff data are already loaded. Our AI is now generating custom insights for your business.
            </p>

            {/* Progress bar */}
            <div className="w-full max-w-sm mb-2">
              <div className="h-2 rounded-full bg-pm-canada-border overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-pm-accent to-pm-blue transition-all duration-1000 ease-linear"
                  style={{ width: `${processingPct}%` }}
                />
              </div>
            </div>
            <div className="flex items-center justify-between w-full max-w-sm mb-6">
              <span className="text-2xs font-mono text-pm-accent">{processingPct}%</span>
              <span className={`text-2xs ${T.muted}/60`}>
                ~{remainingMin} min remaining
              </span>
            </div>

            {/* Phase list */}
            <div className="space-y-1.5 w-full max-w-sm">
              {processingPhases.map((phase, i) => {
                const done = currentPhaseIdx === -1 || i < currentPhaseIdx
                const active = i === currentPhaseIdx
                return (
                  <div key={phase.label} className={`flex items-center gap-2.5 text-xs transition-all duration-300 ${
                    done ? 'text-pm-accent' : active ? 'text-pm-text' : 'text-pm-canada-text-muted/20'
                  }`}>
                    {done ? <CheckCircle2 size={13} className="flex-shrink-0" /> : active ? <Loader2 size={13} className="animate-spin flex-shrink-0" /> : <div className="w-[13px] h-[13px] flex-shrink-0" />}
                    <span>{phase.label}</span>
                    {phase.ai && active && <span className="ml-auto text-[9px] font-mono text-pm-accent/50">AI</span>}
                  </div>
                )
              })}
            </div>

            {/* Safe-to-leave notice */}
            <div className="mt-8 px-4 py-3 rounded-xl bg-pm-canada-border/60 border border-pm-canada-border w-full max-w-sm">
              <p className={`text-2xs ${T.muted} text-center`}>
                You can close this page and come back anytime — your progress is saved automatically.
              </p>
            </div>
          </div>
        )}

        {/* ═══ Done ═══ */}
        {step === 'done' && (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-20 h-20 rounded-full bg-pm-accent/15 border border-pm-accent/30 flex items-center justify-center mb-6">
              <CheckCircle2 size={40} className={T.accentTxt} />
            </div>
            <h2 className={`text-2xl font-bold ${T.text} mb-2`}>You're All Set!</h2>
            <p className={`text-sm ${T.muted} text-center max-w-sm mb-8`}>
              Your dashboard is live. We're already analyzing your data and generating insights.
            </p>
            <button onClick={() => navigate('/canada/merchant')}
              className={`flex items-center gap-2 px-8 py-3 text-sm font-medium text-pm-canada-bg ${T.accentBg} rounded-lg ${T.accentHover} transition-colors shadow-[0_0_30px_rgba(0,212,170,0.2)]`}>
              Go to Dashboard <ArrowRight size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
