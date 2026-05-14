import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Check, Sparkles, Wifi, X, Upload, Trash2, Clock,
  FileText, Mail, CheckCircle2, Loader2, Download, ChevronRight, Pencil, Save,
  AlertTriangle, CreditCard, RefreshCw, Send,
} from 'lucide-react'
import POSSystemPicker from '@/components/POSSystemPicker'
import { type Deal, type DealStage } from '@/lib/canada-sales-demo-data'
import { canadaLeadsService } from '@/lib/canada-leads-service'
import { getPlan } from '@/lib/canada-proposal-plans'
import { getPosSystem, validateCredentials, serializeCredentials } from '@/lib/pos-credentials'
import { generateProposalPdf } from '@/lib/generate-proposal-pdf'
import { generateInvoicePdf, generateInvoiceNumber, generateInvoiceUrl, type InvoiceInput } from '@/lib/generate-invoice-pdf'
import { generateSlaDocument, type SlaInput } from '@/lib/generate-sla-pdf'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase } from '@/lib/supabase'

const STAGE_TO_STEP: Record<string, number> = {
  proposal_shown: 1,
  customer_checkout: 2,
  pos_connected: 3,
  customer_walkthrough: 4,
  closed_lost: 0,
  // Legacy mappings
  appointment_set: 1,
  prospecting: 1,
  contacted: 1,
  demo_scheduled: 1,
  proposal_sent: 1,
  negotiation: 2,
  closed_won: 4,
}

const STEPS = [
  { num: 1, label: 'Proposal Shown' },
  { num: 2, label: 'Customer Checkout' },
  { num: 3, label: 'POS Connected' },
  { num: 4, label: 'Customer Walkthrough' },
]

const DEMO_FILES = [
  { id: '1', name: 'proposal_v2.pdf', description: 'Monthly pricing proposal', tag: 'Proposal' },
  { id: '2', name: 'contract_draft.pdf', description: 'Service agreement draft', tag: 'Contract' },
  { id: '3', name: 'pos_setup_guide.pdf', description: 'POS integration instructions', tag: 'Setup' },
]

function HorizontalStepper({ currentStep }: { currentStep: number }) {
  return (
    <div className="w-full py-6">
      <div className="flex items-center justify-between">
        {STEPS.map((step, idx) => (
          <div key={step.num} className="flex items-center flex-1 last:flex-none">
            {/* Circle */}
            <div className="flex flex-col items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${
                  step.num < currentStep
                    ? 'bg-[#00d4aa] text-white'
                    : step.num === currentStep
                    ? 'border-2 border-[#00d4aa] text-[#00d4aa] bg-transparent'
                    : 'bg-[#1a2420] text-[#6b7a74]'
                }`}
              >
                {step.num < currentStep ? <Check size={18} /> : step.num}
              </div>
              <span className={`text-[10px] mt-1.5 whitespace-nowrap ${
                step.num <= currentStep ? 'text-[#00d4aa]' : 'text-[#6b7a74]'
              }`}>
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {idx < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 mt-[-18px] ${
                step.num < currentStep ? 'bg-[#00d4aa]' : 'bg-[#1a2420]'
              }`} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function CanadaPortalLeadDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { rep } = useSalesAuth()
  const [deal, setDeal] = useState<Deal | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({ business_name: '', contact_name: '', contact_email: '', contact_phone: '', notes: '' })
  const [editSaving, setEditSaving] = useState(false)

  // Step 2 state
  const [monthlyPrice, setMonthlyPrice] = useState(500)
  const [setupFee, setSetupFee] = useState('0')
  const [firstMonthFree, setFirstMonthFree] = useState(false)

  // Proposal state
  const [proposalBlob, setProposalBlob] = useState<Blob | null>(null)
  const [proposalGenerating, setProposalGenerating] = useState(false)
  const [proposalEmailing, setProposalEmailing] = useState(false)
  const [proposalSent, setProposalSent] = useState(false)

  // Invoice state
  const [invoiceBlob, setInvoiceBlob] = useState<Blob | null>(null)
  const [invoiceGenerating, setInvoiceGenerating] = useState(false)
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [invoiceEmailing, setInvoiceEmailing] = useState(false)
  const [invoiceEmailed, setInvoiceEmailed] = useState(false)

  // SLA state
  const [slaBlob, setSlaBlob] = useState<Blob | null>(null)
  const [slaGenerating, setSlaGenerating] = useState(false)
  const [slaSigned, setSlaSigned] = useState(false)
  const [slaSignature, setSlaSignature] = useState('')
  const [slaSigning, setSlaSigning] = useState(false)
  const [slaEmailing, setSlaEmailing] = useState(false)
  const [slaEmailed, setSlaEmailed] = useState(false)
  const [showSlaSign, setShowSlaSign] = useState(false)

  // Step 4 state
  const [selectedPOS, setSelectedPOS] = useState<string | null>(null)
  const [posConnecting, setPosConnecting] = useState(false)
  const [posConnected, setPosConnected] = useState(false)
  const [posError, setPosError] = useState<string | null>(null)

  const [posVerifying, setPosVerifying] = useState(false)
  const [posPending, setPosPending] = useState<string | null>(null)

  // Customer account creation state
  const [customerCreating, setCustomerCreating] = useState(false)
  const [customerCredentials, setCustomerCredentials] = useState<{ email: string; password: string } | null>(null)
  const [customerError, setCustomerError] = useState<string | null>(null)
  const [credentialEmailing, setCredentialEmailing] = useState(false)
  const [credentialEmailed, setCredentialEmailed] = useState(false)

  // Payment status tracking
  const [paymentStatus, setPaymentStatus] = useState<'idle' | 'checking' | 'pending' | 'active' | 'past_due' | 'failed' | 'unavailable'>('idle')
  const [paymentNotifying, setPaymentNotifying] = useState(false)
  const [paymentNotified, setPaymentNotified] = useState(false)
  const [cardUpdateSending, setCardUpdateSending] = useState(false)
  const [cardUpdateUrl, setCardUpdateUrl] = useState<string | null>(null)

  async function handleCredentialSubmit(posKey: string, credentials: Record<string, string>) {
    const system = getPosSystem(posKey)
    if (!system) return

    const { valid, errors } = validateCredentials(system, credentials)
    if (!valid) {
      const allErrors = Object.values(errors)
      setPosError(allErrors.length > 1 ? `Missing fields: ${allErrors.join(', ')}` : allErrors[0])
      return
    }

    const filledCount = Object.values(credentials).filter(v => v.trim()).length
    if (filledCount === 0) {
      setPosError('Please fill in the required credential fields above.')
      return
    }

    setPosConnecting(true)
    setPosError(null)
    setPosPending(null)

    const { provider, credentials: creds } = serializeCredentials(system, credentials)

    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/onboarding/connect-pos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deal_id: deal?.id,
          provider,
          credentials: creds,
          business_name: deal?.business_name,
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setPosError(body.detail || `Connection failed for ${system.name}. Double-check your credentials and try again.`)
        setPosConnecting(false)
        return
      }

      setPosConnecting(false)
      setPosVerifying(true)

      const verifyRes = await fetch(`${API_BASE}/api/onboarding/verify-pos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deal_id: deal?.id, provider }),
      }).catch(() => null)

      if (verifyRes && verifyRes.ok) {
        setPosConnected(true)
        setPosVerifying(false)
        if (deal) {
          await canadaLeadsService.updateStage(deal.id, 'pos_connected')
          setDeal(prev => prev ? { ...prev, stage: 'pos_connected' } : prev)
        }
      } else {
        setPosVerifying(false)
        setPosPending(`${system.name} credentials saved — waiting for data verification. The swarm will confirm data is flowing and notify you.`)
        if (deal && deal.stage !== 'pos_connected' && deal.stage !== 'customer_walkthrough') {
          await canadaLeadsService.updateStage(deal.id, 'customer_checkout')
          setDeal(prev => prev ? { ...prev, stage: 'customer_checkout' } : prev)
        }
      }
    } catch {
      setPosError(`Could not reach the server. Check your internet connection and try again.`)
      setPosConnecting(false)
    }
  }

  function generatePassword(): string {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    let pw = ''
    for (let i = 0; i < 12; i++) pw += chars[Math.floor(Math.random() * chars.length)]
    return pw
  }

  async function handleCreateCustomerAccount() {
    if (!deal) return
    setCustomerCreating(true)
    setCustomerError(null)

    const email = deal.contact_email
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setCustomerError('Invalid email address. Edit the lead to fix it before creating an account.')
      setCustomerCreating(false)
      return
    }
    const password = generatePassword()

    try {
      if (!supabase) throw new Error('Database not connected')

      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/canada/create-customer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          business_name: deal.business_name,
          contact_name: deal.contact_name,
          phone: deal.contact_phone,
          vertical: deal.vertical,
          deal_id: deal.id,
          monthly_price: monthlyPrice,
          portal: 'canada',
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Failed to create customer account')
      }

      setCustomerCredentials({ email, password })
      await canadaLeadsService.updateStage(deal.id, 'customer_walkthrough')
      setDeal(prev => prev ? { ...prev, stage: 'customer_walkthrough' } : prev)
    } catch (err) {
      setCustomerError(err instanceof Error ? err.message : 'Failed to create account')
    } finally {
      setCustomerCreating(false)
    }
  }

  async function handleEmailCredentials() {
    if (!deal || !customerCredentials) return
    setCredentialEmailing(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/email/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template: 'customer_credentials',
          to: deal.contact_email,
          first_name: deal.contact_name.split(' ')[0],
          portal: 'canada',
          extra: {
            business_name: deal.business_name,
            email: customerCredentials.email,
            password: customerCredentials.password,
            login_url: `${window.location.origin}/canada/login`,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setCredentialEmailed(true)
    } catch {
      setCustomerError('Failed to send email — you can share the credentials manually.')
    } finally {
      setCredentialEmailing(false)
    }
  }

  async function checkPaymentStatus() {
    if (!deal) return
    setPaymentStatus('checking')
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/billing/status/${deal.id}`)
      if (!res.ok) { setPaymentStatus('unavailable'); return }
      const data = await res.json()
      const status = data.status as string
      if (status === 'active') setPaymentStatus('active')
      else if (status === 'past_due') setPaymentStatus('past_due')
      else if (status === 'canceled') setPaymentStatus('failed')
      else if (status === 'pending_payment') setPaymentStatus('pending')
      else if (status === 'none' || status === 'unavailable') setPaymentStatus('unavailable')
      else setPaymentStatus('pending')
    } catch {
      setPaymentStatus('unavailable')
    }
  }

  async function handleNotifyPaymentFailed() {
    if (!deal || !rep) return
    setPaymentNotifying(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/billing/notify-payment-failed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: deal.id,
          customer_email: deal.contact_email,
          contact_name: deal.contact_name,
          business_name: deal.business_name,
          rep_name: rep.name,
          rep_email: rep.email,
        }),
      })
      if (!res.ok) throw new Error('Failed to send notification')
      const data = await res.json()
      setPaymentNotified(true)
      if (data.update_url) setCardUpdateUrl(data.update_url)
    } catch (err) {
      setPosError('Failed to send payment notification. Try again.')
    } finally {
      setPaymentNotifying(false)
    }
  }

  async function handleSendCardUpdateLink() {
    if (!deal || !rep) return
    setCardUpdateSending(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/billing/update-payment-method`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: deal.id,
          customer_email: deal.contact_email,
          customer_name: deal.contact_name,
          business_name: deal.business_name,
        }),
      })
      if (!res.ok) throw new Error('Failed to create payment link')
      const data = await res.json()
      setCardUpdateUrl(data.invoice_url)
    } catch (err) {
      setPosError('Failed to create payment update link. Try again.')
    } finally {
      setCardUpdateSending(false)
    }
  }

  async function handleGenerateInvoice() {
    if (!deal || !rep) return
    setInvoiceGenerating(true)
    try {
      const invNum = invoiceNumber || generateInvoiceNumber()
      if (!invoiceNumber) setInvoiceNumber(invNum)

      const now = new Date()
      const dueDate = new Date(now)
      dueDate.setDate(dueDate.getDate() + 30)

      const planName = monthlyPrice >= 1000 ? 'Command' : monthlyPrice >= 500 ? 'Premium' : 'Standard'
      const priceCents = Math.round(monthlyPrice * 100)
      const setupFeeCents = Math.round((Number(setupFee) || 0) * 100)

      let checkoutUrl = generateInvoiceUrl(invNum)

      const API_BASE = import.meta.env.VITE_API_URL || ''
      try {
        const checkoutRes = await fetch(`${API_BASE}/api/billing/create-checkout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            org_id: deal.id,
            plan: planName.toLowerCase(),
            monthly_price_cents: priceCents,
            customer_email: deal.contact_email,
            customer_name: deal.contact_name,
            business_name: deal.business_name,
            return_url: `${window.location.origin}/canada/login`,
            setup_fee_cents: setupFeeCents,
            first_month_free: firstMonthFree,
            rep_id: rep.rep_id || '',
            rep_name: rep.name,
          }),
        })
        if (checkoutRes.ok) {
          const data = await checkoutRes.json()
          if (data.checkout_url) checkoutUrl = data.checkout_url
        }
      } catch {
        // Square checkout unavailable — fall back to local invoice URL
      }

      const input: InvoiceInput = {
        invoiceNumber: invNum,
        businessName: deal.business_name,
        contactName: deal.contact_name,
        contactEmail: deal.contact_email,
        contactPhone: deal.contact_phone,
        monthlyPrice,
        setupFee: Number(setupFee) || 0,
        firstMonthFree,
        planName,
        billingDate: now.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' }),
        dueDate: dueDate.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' }),
        repName: rep.name,
        repEmail: rep.email,
        recurring: true,
        invoiceUrl: checkoutUrl,
      }

      const blob = await generateInvoicePdf(input)
      setInvoiceBlob(blob)

      if (deal.stage === 'proposal_shown' || deal.stage === 'appointment_set') {
        await canadaLeadsService.updateStage(deal.id, 'customer_checkout')
        setDeal(prev => prev ? { ...prev, stage: 'customer_checkout' } : prev)
      }
    } catch (err) {
      console.error('[Invoice] Generation failed:', err)
    } finally {
      setInvoiceGenerating(false)
    }
  }

  function handleDownloadInvoice() {
    if (!invoiceBlob || !deal) return
    const url = URL.createObjectURL(invoiceBlob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Meridian_Invoice_${invoiceNumber || 'draft'}_${deal.business_name.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  async function handleEmailInvoice() {
    if (!deal) return
    if (!invoiceBlob) await handleGenerateInvoice()
    setInvoiceEmailing(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/email/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template: 'invoice_sent',
          to: deal.contact_email,
          first_name: deal.contact_name.split(' ')[0],
          portal: 'canada',
          extra: {
            business_name: deal.business_name,
            invoice_number: invoiceNumber,
            amount: `CA$${monthlyPrice.toLocaleString()}`,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
            invoice_url: generateInvoiceUrl(invoiceNumber),
            recurring: true,
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setInvoiceEmailed(true)
    } catch (err) {
      console.error('[Invoice] Email failed:', err)
      setPosError('Invoice email failed to send. Try again or share the PDF directly.')
    } finally {
      setInvoiceEmailing(false)
    }
  }

  async function handleGenerateSla() {
    if (!deal || !rep) return
    setSlaGenerating(true)
    try {
      const slaInput: SlaInput = {
        clientCompanyName: deal.business_name,
        province: deal.province || 'Ontario',
        posSystem: selectedPOS || 'Unknown',
        repName: rep.name || 'Sales Representative',
        monthlyPriceCad: monthlyPrice * 100,
        setupFeeCad: (Number(setupFee) || 0) * 100,
        startDate: new Date().toISOString().slice(0, 10),
      }
      const blob = await generateSlaDocument(slaInput)
      setSlaBlob(blob)
    } catch (err) {
      console.error('[SLA] Generation failed:', err)
    } finally {
      setSlaGenerating(false)
    }
  }

  function handleDownloadSla() {
    if (!slaBlob || !deal) return
    const url = URL.createObjectURL(slaBlob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Meridian_SLA_${deal.business_name.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  async function handleSignSla() {
    if (!slaSignature.trim() || !deal || !rep) return
    setSlaSigning(true)
    try {
      const slaInput: SlaInput = {
        clientCompanyName: deal.business_name,
        province: deal.province || 'Ontario',
        posSystem: selectedPOS || 'Unknown',
        repName: rep.name || 'Sales Representative',
        monthlyPriceCad: monthlyPrice * 100,
        setupFeeCad: (Number(setupFee) || 0) * 100,
        startDate: new Date().toISOString().slice(0, 10),
        clientSignature: slaSignature,
      }
      const signedBlob = await generateSlaDocument(slaInput)
      setSlaBlob(signedBlob)
      setSlaSigned(true)
      setShowSlaSign(false)

      const API_BASE = import.meta.env.VITE_API_URL || ''
      try {
        const emailRes = await fetch(`${API_BASE}/api/email/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: deal.contact_email,
            template: 'sla_signed',
            portal: 'canada',
            extra: {
              business_name: deal.business_name,
              rep_name: rep.name || '',
              rep_email: rep.email || '',
              signed_by: slaSignature,
              signed_date: new Date().toLocaleDateString('en-CA'),
              provider_signatory: 'Aidan Pierce, Founder & CEO',
            },
          }),
        })
        if (emailRes.ok) setSlaEmailed(true)
      } catch {
        // Email send is best-effort — SLA is still signed
      }
    } catch (err) {
      console.error('[SLA] Sign failed:', err)
    } finally {
      setSlaSigning(false)
    }
  }

  async function handleEmailSla() {
    if (!deal || !slaBlob) return
    setSlaEmailing(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/email/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: deal.contact_email,
          template: 'sla_signed',
          portal: 'canada',
          extra: {
            business_name: deal.business_name,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
            signed_by: slaSignature,
            signed_date: new Date().toLocaleDateString('en-CA'),
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setSlaEmailed(true)
    } catch (err) {
      console.error('[SLA] Email failed:', err)
      setPosError('SLA email failed to send. Try again or download and share the PDF.')
    } finally {
      setSlaEmailing(false)
    }
  }

  const buildProposalInput = useCallback(() => {
    if (!deal || !rep) return null
    const closestPlan = monthlyPrice >= 1000 ? 'command' : monthlyPrice >= 500 ? 'premium' : 'standard'
    const plan = getPlan(closestPlan)
    return {
      businessName: deal.business_name,
      ownerName: deal.contact_name,
      email: deal.contact_email,
      phone: deal.contact_phone || '',
      plan,
      customPrice: monthlyPrice,
      setupFee: Number(setupFee) || 0,
      firstMonthFree,
      rep,
    }
  }, [deal, rep, monthlyPrice, setupFee, firstMonthFree])

  async function handleGenerateProposal() {
    const input = buildProposalInput()
    if (!input) return
    setProposalGenerating(true)
    try {
      const blob = await generateProposalPdf(input)
      setProposalBlob(blob)
      if (deal && (deal.stage === 'appointment_set' || deal.stage === 'prospecting' || deal.stage === 'contacted')) {
        await canadaLeadsService.updateStage(deal.id, 'proposal_shown')
        setDeal(prev => prev ? { ...prev, stage: 'proposal_shown' } : prev)
      }
    } catch (err) {
      console.error('[Proposal] Generation failed:', err)
    } finally {
      setProposalGenerating(false)
    }
  }

  async function handleViewProposal() {
    let blob = proposalBlob
    if (!blob) {
      const input = buildProposalInput()
      if (!input) return
      setProposalGenerating(true)
      try {
        blob = await generateProposalPdf(input)
        setProposalBlob(blob)
      } finally {
        setProposalGenerating(false)
      }
    }
    if (blob && deal) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Meridian_Proposal_${deal.business_name.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  function handleDownloadProposal() {
    if (!proposalBlob || !deal) return
    const url = URL.createObjectURL(proposalBlob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Meridian_Proposal_${deal.business_name.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  async function handleEmailProposal() {
    if (!deal) return
    if (!proposalBlob) await handleGenerateProposal()
    setProposalEmailing(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/email/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template: 'proposal_sent',
          to: deal.contact_email,
          first_name: deal.contact_name.split(' ')[0],
          portal: 'canada',
          extra: {
            business_name: deal.business_name,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
            plan_name: monthlyPrice >= 750 ? 'Command' : monthlyPrice >= 375 ? 'Premium' : 'Standard',
            monthly_price: `CA$${monthlyPrice.toLocaleString()}`,
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setProposalSent(true)
      if (deal.stage === 'appointment_set' || deal.stage === 'proposal_shown' || deal.stage === 'contacted' || deal.stage === 'demo_scheduled') {
        await canadaLeadsService.updateStage(deal.id, 'proposal_shown')
        setDeal(prev => prev ? { ...prev, stage: 'proposal_shown' } : prev)
      }
    } catch (err) {
      console.error('[Proposal] Email failed:', err)
      setPosError('Proposal email failed to send. Try again or download and share the PDF.')
    } finally {
      setProposalEmailing(false)
    }
  }

  // Files state
  const [files, setFiles] = useState(DEMO_FILES)

  useEffect(() => {
    canadaLeadsService.getById(id!).then(found => {
      setDeal(found)
      if (found) {
        setMonthlyPrice(found.monthly_value || 500)
      }
      setLoading(false)
    })
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#00d4aa] font-bold text-sm">S</span>
        </div>
      </div>
    )
  }

  if (!deal) {
    return (
      <div className="space-y-4">
        <Link to="/canada/portal/leads" className="inline-flex items-center gap-1.5 text-sm text-[#6b7a74] hover:text-white transition-colors">
          <ArrowLeft size={16} /> Leads
        </Link>
        <div className="text-center py-16 text-[#6b7a74]">Lead not found.</div>
      </div>
    )
  }

  const currentStep = STAGE_TO_STEP[deal.stage]

  function removeFile(fileId: string) {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }

  function handleUpload() {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf,.doc,.docx,.xls,.xlsx,.csv,.png,.jpg,.jpeg'
    input.onchange = () => {
      const file = input.files?.[0]
      if (!file) return
      const ext = file.name.split('.').pop()?.toUpperCase() || 'File'
      setFiles(prev => [...prev, { id: String(Date.now()), name: file.name, description: `Uploaded ${ext} file`, tag: ext }])
    }
    input.click()
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#0f1512] border border-[#1a2420] rounded-lg text-sm text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50 focus:ring-1 focus:ring-[#00d4aa]/20 transition-colors'

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Back link */}
      <Link to="/canada/portal/leads" className="inline-flex items-center gap-1.5 text-sm text-[#6b7a74] hover:text-white transition-colors">
        <ArrowLeft size={16} /> Leads
      </Link>

      {/* Header */}
      {editing ? (
        <div className="bg-[#0f1512] border border-[#00d4aa]/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#00d4aa]">Edit Lead</h2>
            <button onClick={() => setEditing(false)} className="text-xs text-[#6b7a74] hover:text-white">Cancel</button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input value={editForm.business_name} onChange={e => setEditForm(f => ({ ...f, business_name: e.target.value }))} className={inputClass} placeholder="Business Name" />
            <input value={editForm.contact_name} onChange={e => setEditForm(f => ({ ...f, contact_name: e.target.value }))} className={inputClass} placeholder="Contact Name" />
            <input value={editForm.contact_email} onChange={e => setEditForm(f => ({ ...f, contact_email: e.target.value }))} className={inputClass} placeholder="Email" />
            <input value={editForm.contact_phone} onChange={e => setEditForm(f => ({ ...f, contact_phone: e.target.value }))} className={inputClass} placeholder="Phone" />
            <textarea value={editForm.notes} onChange={e => setEditForm(f => ({ ...f, notes: e.target.value }))} className={inputClass + ' sm:col-span-2 resize-none h-20'} placeholder="Notes" />
          </div>
          <button
            disabled={editSaving}
            onClick={async () => {
              setEditSaving(true)
              try {
                await canadaLeadsService.update(deal.id, editForm)
                setDeal(prev => prev ? { ...prev, ...editForm } : prev)
                setEditing(false)
              } catch (err) {
                setPosError(err instanceof Error ? `Save failed: ${err.message}` : 'Failed to save changes. Please try again.')
              } finally {
                setEditSaving(false)
              }
            }}
            className="flex items-center gap-2 px-4 py-2 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
          >
            {editSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save Changes
          </button>
        </div>
      ) : (
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{deal.business_name}</h1>
            <p className="text-sm text-[#6b7a74] mt-1">
              {deal.contact_name} &middot; <span className="text-[#f0b429] font-semibold">CA${deal.monthly_value.toLocaleString()}/mo</span> &middot; {deal.contact_email}
            </p>
          </div>
          <button
            onClick={() => {
              setEditForm({
                business_name: deal.business_name,
                contact_name: deal.contact_name,
                contact_email: deal.contact_email,
                contact_phone: deal.contact_phone,
                notes: deal.notes,
              })
              setEditing(true)
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#6b7a74] border border-[#1a2420] rounded-lg hover:text-white hover:border-[#2a3430] transition-colors"
          >
            <Pencil size={12} /> Edit
          </button>
        </div>
      )}

      {/* Stepper */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
        <HorizontalStepper currentStep={currentStep} />
      </div>

      {/* Step 1 - Proposal (always visible) */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Proposal</h2>

        {/* Monthly Price Slider */}
        <div>
          <label className="text-xs text-[#6b7a74] block mb-1.5">Monthly Price (CAD)</label>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={350}
              max={1400}
              step={50}
              value={monthlyPrice}
              onChange={e => setMonthlyPrice(Number(e.target.value))}
              className="flex-1 h-2 bg-[#1a2420] rounded-full appearance-none cursor-pointer accent-[#00d4aa]"
            />
            <span className="text-sm font-semibold text-[#f0b429] w-28 text-right">CA${monthlyPrice.toLocaleString()}/mo</span>
          </div>
          <p className="text-[10px] text-[#4a5550] mt-1">~US${Math.round(monthlyPrice / 1.37).toLocaleString()}/mo</p>
        </div>

        {/* Setup Fee */}
        <div>
          <label className="text-xs text-[#6b7a74] block mb-1.5">Setup Fee</label>
          <input
            type="text"
            value={setupFee}
            onChange={e => setSetupFee(e.target.value)}
            className={inputClass}
            placeholder="e.g. 250"
          />
        </div>

        {/* First month free */}
        <label className="flex items-center gap-3 cursor-pointer">
          <div className={`w-9 h-5 rounded-full transition-colors relative ${firstMonthFree ? 'bg-[#00d4aa]' : 'bg-[#1a2420]'}`}
            onClick={() => setFirstMonthFree(!firstMonthFree)}
          >
            <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${firstMonthFree ? 'translate-x-4' : 'translate-x-0.5'}`} />
          </div>
          <span className="text-sm text-white">First month free</span>
        </label>

        {/* Buttons */}
        <button
          onClick={handleGenerateProposal}
          disabled={proposalGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
        >
          {proposalGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating…</>
          ) : (
            <><Sparkles size={16} /> {proposalBlob ? 'Regenerate Proposal' : 'Generate Proposal'}</>
          )}
        </button>

        {proposalBlob && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
            <CheckCircle2 size={16} className="text-[#00d4aa]" />
            <span className="text-xs text-[#00d4aa] font-medium">Proposal ready — 9 slides, PDF generated.</span>
            <button onClick={handleDownloadProposal} className="ml-auto text-[#00d4aa] hover:text-white transition-colors">
              <Download size={14} />
            </button>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleViewProposal}
            disabled={proposalGenerating}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 disabled:opacity-50 transition-all"
          >
            <Download size={16} /> Download Proposal
          </button>
          <button
            onClick={handleEmailProposal}
            disabled={proposalEmailing || proposalGenerating}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 disabled:opacity-50 transition-all"
          >
            {proposalEmailing ? (
              <><Loader2 size={16} className="animate-spin" /> Sending…</>
            ) : proposalSent ? (
              <><CheckCircle2 size={16} className="text-[#00d4aa]" /> Sent!</>
            ) : (
              <><Mail size={16} /> Email Proposal</>
            )}
          </button>
        </div>
      </div>

      {/* Step 2 - Invoice / Customer Checkout (visible at step 2+) */}
      {currentStep >= 2 && (
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Invoice &amp; Checkout</h2>
        <p className="text-xs text-[#6b7a74]">
          Generate a custom invoice in CAD with a QR code the customer can scan to view. Invoices recur monthly.
        </p>

        <button
          onClick={handleGenerateInvoice}
          disabled={invoiceGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
        >
          {invoiceGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating Invoice…</>
          ) : (
            <><FileText size={16} /> {invoiceBlob ? 'Regenerate Invoice' : 'Generate Invoice (CAD)'}</>
          )}
        </button>

        {invoiceBlob && (
          <>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
              <CheckCircle2 size={16} className="text-[#00d4aa]" />
              <span className="text-xs text-[#00d4aa] font-medium">
                Invoice #{invoiceNumber} ready — includes QR code for online viewing.
              </span>
              <button onClick={handleDownloadInvoice} className="ml-auto text-[#00d4aa] hover:text-white transition-colors">
                <Download size={14} />
              </button>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleDownloadInvoice}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 transition-all"
              >
                <Download size={16} /> Download Invoice
              </button>
              <button
                onClick={handleEmailInvoice}
                disabled={invoiceEmailing}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 disabled:opacity-50 transition-all"
              >
                {invoiceEmailing ? (
                  <><Loader2 size={16} className="animate-spin" /> Sending…</>
                ) : invoiceEmailed ? (
                  <><CheckCircle2 size={16} className="text-[#00d4aa]" /> Invoice Sent!</>
                ) : (
                  <><Mail size={16} /> Email Invoice</>
                )}
              </button>
            </div>
            <p className="text-[10px] text-[#4a5550]">
              Recurring monthly — customer will be billed CA${monthlyPrice.toLocaleString()}/mo automatically.
            </p>
          </>
        )}
      </div>
      )}

      {/* Payment Status & Card Management (visible at step 2+) */}
      {currentStep >= 2 && (
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CreditCard size={16} className="text-[#00d4aa]" />
            <h2 className="text-sm font-semibold text-white">Payment Status</h2>
          </div>
          <button
            onClick={checkPaymentStatus}
            disabled={paymentStatus === 'checking'}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium text-[#6b7a74] border border-[#1a2420] rounded-lg hover:text-[#00d4aa] hover:border-[#00d4aa]/30 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={10} className={paymentStatus === 'checking' ? 'animate-spin' : ''} />
            {paymentStatus === 'idle' ? 'Check Status' : 'Refresh'}
          </button>
        </div>

        {paymentStatus === 'idle' && (
          <p className="text-xs text-[#6b7a74]">Click "Check Status" to see if the customer has paid.</p>
        )}

        {paymentStatus === 'checking' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#1a2420]">
            <Loader2 size={14} className="text-[#00d4aa] animate-spin" />
            <span className="text-xs text-[#6b7a74]">Checking payment status...</span>
          </div>
        )}

        {paymentStatus === 'active' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
            <CheckCircle2 size={16} className="text-[#00d4aa]" />
            <div>
              <span className="text-xs text-[#00d4aa] font-medium">Payment confirmed — subscription active</span>
              <p className="text-[10px] text-[#4a5550] mt-0.5">Card on file is being used for recurring billing.</p>
            </div>
          </div>
        )}

        {paymentStatus === 'pending' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20">
            <Clock size={16} className="text-[#f0b429]" />
            <div>
              <span className="text-xs text-[#f0b429] font-medium">Payment pending — invoice sent, awaiting payment</span>
              <p className="text-[10px] text-[#4a5550] mt-0.5">The customer has been invoiced but hasn't paid yet.</p>
            </div>
          </div>
        )}

        {(paymentStatus === 'past_due' || paymentStatus === 'failed') && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <AlertTriangle size={16} className="text-red-400" />
              <div>
                <span className="text-xs text-red-400 font-medium">
                  {paymentStatus === 'past_due' ? 'Payment past due' : 'Payment failed'}
                </span>
                <p className="text-[10px] text-[#4a5550] mt-0.5">
                  {paymentStatus === 'past_due'
                    ? 'Invoice is overdue. Notify the customer or send a new payment link.'
                    : 'The customer\'s payment was declined. Send them a link to update their card.'}
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleNotifyPaymentFailed}
                disabled={paymentNotifying || paymentNotified}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-red-500/30 text-red-400 text-sm font-medium rounded-lg hover:bg-red-500/10 disabled:opacity-50 transition-all"
              >
                {paymentNotifying ? (
                  <><Loader2 size={14} className="animate-spin" /> Sending...</>
                ) : paymentNotified ? (
                  <><CheckCircle2 size={14} /> Customer Notified</>
                ) : (
                  <><Send size={14} /> Notify Customer</>
                )}
              </button>
              <button
                onClick={handleSendCardUpdateLink}
                disabled={cardUpdateSending}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
              >
                {cardUpdateSending ? (
                  <><Loader2 size={14} className="animate-spin" /> Creating Link...</>
                ) : (
                  <><CreditCard size={14} /> Send Card Update Link</>
                )}
              </button>
            </div>

            {cardUpdateUrl && (
              <div className="p-3 rounded-lg bg-[#0a0f0d] border border-[#1a2420] space-y-2">
                <p className="text-[10px] text-[#6b7a74]">Payment update link (sent to customer):</p>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={cardUpdateUrl}
                    className="flex-1 px-2 py-1.5 bg-[#0f1512] border border-[#1a2420] rounded text-[11px] text-white font-mono truncate"
                  />
                  <button
                    onClick={() => { navigator.clipboard.writeText(cardUpdateUrl); }}
                    className="px-3 py-1.5 text-[10px] text-[#00d4aa] border border-[#00d4aa]/30 rounded hover:bg-[#00d4aa]/10 transition-colors"
                  >
                    Copy
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {paymentStatus === 'unavailable' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#1a2420]">
            <span className="text-xs text-[#6b7a74]">No billing record found yet — invoice may not have been created.</span>
          </div>
        )}
      </div>
      )}

      {/* Step 2b - SLA Document (visible at step 2+) */}
      {currentStep >= 2 && (
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-[#00d4aa]" />
          <h2 className="text-sm font-semibold text-white">Service Level Agreement</h2>
        </div>
        <p className="text-xs text-[#6b7a74]">
          Generate an SLA document for the client to sign. {deal?.province && (deal.province.toLowerCase().includes('quebec') || deal.province.toLowerCase() === 'qc') ? 'Includes PIPEDA + Quebec Law 25 compliance.' : 'Includes PIPEDA compliance.'}
        </p>

        <button
          onClick={handleGenerateSla}
          disabled={slaGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#1a2420] border border-[#2a3830] text-white text-sm font-semibold rounded-lg hover:border-[#00d4aa]/30 disabled:opacity-50 transition-all"
        >
          {slaGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating SLA…</>
          ) : (
            <><FileText size={16} /> {slaBlob ? 'Regenerate SLA' : 'Generate SLA Document'}</>
          )}
        </button>

        {slaBlob && (
          <>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
              <CheckCircle2 size={16} className="text-[#00d4aa]" />
              <span className="text-xs text-[#00d4aa] font-medium">
                SLA document ready{slaSigned ? ' — signed' : ''}.
              </span>
              <button onClick={handleDownloadSla} className="ml-auto text-[#00d4aa] hover:text-white transition-colors">
                <Download size={14} />
              </button>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleDownloadSla}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 transition-all"
              >
                <Download size={16} /> Download SLA
              </button>
              {!slaSigned ? (
                <button
                  onClick={() => setShowSlaSign(true)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
                >
                  <Pencil size={16} /> Sign SLA
                </button>
              ) : (
                <button
                  onClick={handleEmailSla}
                  disabled={slaEmailing}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 disabled:opacity-50 transition-all"
                >
                  {slaEmailing ? (
                    <><Loader2 size={16} className="animate-spin" /> Sending…</>
                  ) : slaEmailed ? (
                    <><CheckCircle2 size={16} className="text-[#00d4aa]" /> SLA Sent!</>
                  ) : (
                    <><Mail size={16} /> Email Signed SLA</>
                  )}
                </button>
              )}
            </div>

            {slaSigned && (
              <div className="text-[10px] text-[#4a5550] space-y-0.5">
                <p>Provider: Aidan Pierce, Founder & CEO — {new Date().toLocaleDateString('en-CA')}</p>
                <p>Client: {slaSignature} — {new Date().toLocaleDateString('en-CA')}</p>
                {slaEmailed && <p className="text-[#00d4aa]">Signed copy emailed to {deal?.contact_email}</p>}
              </div>
            )}
          </>
        )}

        {/* Signature Modal */}
        {showSlaSign && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="w-full max-w-lg bg-[#0f1512] border border-[#1a2420] rounded-xl p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-base font-semibold text-white">Sign Service Level Agreement</h3>
                <button onClick={() => setShowSlaSign(false)} className="p-1.5 rounded-lg hover:bg-[#1a2420] transition-colors">
                  <X size={18} className="text-[#6b7a74]" />
                </button>
              </div>
              <p className="text-xs text-[#6b7a74] mb-4">
                By typing your full legal name below, you acknowledge that you have read and agree to the terms of the Service Level Agreement between Meridian AI Business Solutions and {deal?.business_name}. A signed copy will be emailed to both parties.
              </p>
              <div className="space-y-4">
                {/* Provider signature — pre-filled */}
                <div className="p-4 bg-[#0a0f0d] border border-[#1a2420] rounded-lg">
                  <p className="text-[10px] text-[#6b7a74] mb-1">Provider — Meridian AI Business Solutions</p>
                  <p className="text-lg font-serif italic text-[#00d4aa]">Aidan Pierce</p>
                  <p className="text-[10px] text-[#4a5550] mt-1">Founder & CEO</p>
                </div>

                {/* Client signature */}
                <div>
                  <label className="text-xs text-[#6b7a74] mb-1.5 block">Client — {deal?.business_name}</label>
                  <input
                    type="text"
                    value={slaSignature}
                    onChange={e => setSlaSignature(e.target.value)}
                    placeholder="Client signatory full legal name"
                    className="w-full px-3 py-2.5 bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-sm text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50 focus:ring-1 focus:ring-[#00d4aa]/20 transition-colors"
                  />
                </div>
                {slaSignature.trim() && (
                  <div className="p-4 bg-[#0a0f0d] border border-[#1a2420] rounded-lg">
                    <p className="text-[10px] text-[#6b7a74] mb-1">Client signature preview</p>
                    <p className="text-xl font-serif italic text-white">{slaSignature}</p>
                  </div>
                )}

                <p className="text-[10px] text-[#4a5550]">
                  Date: {new Date().toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
                <div className="flex justify-end gap-2 mt-4">
                  <button onClick={() => setShowSlaSign(false)} className="px-4 py-2 text-sm text-[#6b7a74] hover:text-white transition-colors">Cancel</button>
                  <button
                    onClick={handleSignSla}
                    disabled={!slaSignature.trim() || slaSigning}
                    className="px-4 py-2 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
                  >
                    {slaSigning ? 'Signing…' : 'Sign & Send Copies'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      )}

      {/* Step 3 - Connect POS (visible at step 3+) */}
      {currentStep >= 3 && (
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Connect POS System</h2>

        <POSSystemPicker
          value={selectedPOS}
          onChange={k => { setSelectedPOS(k); setPosConnected(false); setPosError(null); setPosPending(null) }}
          onCredentialSubmit={handleCredentialSubmit}
          mode="lead-detail"
          portalContext="canada"
        />

        {posConnecting && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20">
            <Loader2 size={16} className="text-[#f0b429] animate-spin" />
            <span className="text-xs text-[#f0b429] font-medium">Connecting — saving credentials...</span>
          </div>
        )}

        {posVerifying && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20">
            <Loader2 size={16} className="text-[#f0b429] animate-spin" />
            <span className="text-xs text-[#f0b429] font-medium">Verifying — checking if we can pull data with these credentials...</span>
          </div>
        )}

        {posError && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
            {posError}
          </div>
        )}

        {posPending && !posError && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20">
            <Clock size={16} className="text-[#f0b429]" />
            <span className="text-xs text-[#f0b429] font-medium">{posPending}</span>
          </div>
        )}

        {posConnected && !posVerifying && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
            <CheckCircle2 size={16} className="text-[#00d4aa]" />
            <span className="text-xs text-[#00d4aa] font-medium">
              POS connected and verified — data is flowing. This deal is now active.
            </span>
          </div>
        )}
      </div>
      )}

      {/* Project Files */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Project Files</h2>
          <button onClick={handleUpload} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#00d4aa] border border-[#00d4aa]/30 rounded-lg hover:bg-[#00d4aa]/10 transition-all">
            <Upload size={14} /> Upload
          </button>
        </div>

        <div className="space-y-2">
          {files.map(file => (
            <div key={file.id} className="flex items-center gap-3 p-3 bg-[#0a0f0d] border border-[#1a2420] rounded-lg">
              <FileText size={16} className="text-[#6b7a74] flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate">{file.name}</p>
                <p className="text-[11px] text-[#4a5550]">{file.description}</p>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-[#1a2420] text-[#6b7a74] font-medium flex-shrink-0">
                {file.tag}
              </span>
              <button
                onClick={() => removeFile(file.id)}
                className="p-1 rounded hover:bg-red-500/10 transition-colors flex-shrink-0"
              >
                <Trash2 size={14} className="text-[#6b7a74] hover:text-red-400" />
              </button>
            </div>
          ))}
          {files.length === 0 && (
            <p className="text-xs text-[#4a5550] text-center py-4">No files uploaded yet.</p>
          )}
        </div>
      </div>

      {/* Stage Advancement */}
      {currentStep > 0 && currentStep < 4 && deal.stage !== 'closed_lost' && (
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white">Advance Deal</h2>
          <button
            onClick={async () => {
              try {
                const order: DealStage[] = ['proposal_shown', 'customer_checkout', 'pos_connected', 'customer_walkthrough']
                const currentNorm = order.find(s => STAGE_TO_STEP[s] === currentStep) || deal.stage as DealStage
                const idx = order.indexOf(currentNorm)
                if (idx < 0) {
                  const nextStage: DealStage = 'proposal_shown'
                  await canadaLeadsService.updateStage(deal.id, nextStage)
                  setDeal(prev => prev ? { ...prev, stage: nextStage } : prev)
                  return
                }
                if (idx < order.length - 1) {
                  const nextStage = order[idx + 1]
                  await canadaLeadsService.updateStage(deal.id, nextStage)
                  setDeal(prev => prev ? { ...prev, stage: nextStage } : prev)
                }
              } catch (err) {
                console.error('Stage advance failed:', err)
              }
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-[#00d4aa]/30 text-[#00d4aa] text-sm font-medium rounded-lg hover:bg-[#00d4aa]/10 transition-all"
          >
            <ChevronRight size={16} /> Advance to Next Stage
          </button>
        </div>
      )}

      {/* Create Customer Account Login (visible at step 3+) */}
      {currentStep >= 3 && (
        <div className="bg-[#0f1512] border border-[#00d4aa]/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-[#00d4aa]" />
            <h2 className="text-sm font-semibold text-[#00d4aa]">Create Customer Account Login</h2>
          </div>
          <p className="text-xs text-[#6b7a74]">
            Generate a login for {deal.contact_name} to access the Meridian customer portal. They'll be guided through a walkthrough to verify their POS connection, set up cameras, and explore their dashboard.
          </p>

          {customerCredentials ? (
            <div className="space-y-3">
              <div className="p-4 rounded-lg bg-[#0a0f0d] border border-[#1a2420] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#6b7a74]">Email</span>
                  <span className="text-sm text-white font-mono">{customerCredentials.email}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#6b7a74]">Password</span>
                  <span className="text-sm text-white font-mono">{customerCredentials.password}</span>
                </div>
                <p className="text-[10px] text-[#4a5550] mt-1">Share these credentials with the customer. They can change their password after first login.</p>
              </div>
              <button
                onClick={handleEmailCredentials}
                disabled={credentialEmailing || credentialEmailed}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-[#00d4aa]/30 text-[#00d4aa] text-sm font-medium rounded-lg hover:bg-[#00d4aa]/10 disabled:opacity-50 transition-all"
              >
                {credentialEmailing ? (
                  <><Loader2 size={16} className="animate-spin" /> Sending...</>
                ) : credentialEmailed ? (
                  <><CheckCircle2 size={16} /> Login Emailed to {deal.contact_name}</>
                ) : (
                  <><Mail size={16} /> Email Login to {deal.contact_name}</>
                )}
              </button>
            </div>
          ) : (
            <>
              {customerError && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                  {customerError}
                </div>
              )}
              <button
                onClick={handleCreateCustomerAccount}
                disabled={customerCreating}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
              >
                {customerCreating ? (
                  <><Loader2 size={16} className="animate-spin" /> Creating Account...</>
                ) : (
                  <><Sparkles size={16} /> Create Customer Account Login</>
                )}
              </button>
            </>
          )}
        </div>
      )}

      {/* Customer Walkthrough status */}
      {deal.stage === 'customer_walkthrough' && (
        <div className="bg-[#0f1512] border border-[#00d4aa]/20 rounded-xl p-5 space-y-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-[#00d4aa]" />
            <h2 className="text-sm font-semibold text-[#00d4aa]">Active Deal — Customer Onboarding</h2>
          </div>
          <p className="text-xs text-[#6b7a74]">
            This deal is active. The customer has been set up and is going through their onboarding walkthrough.
          </p>
        </div>
      )}

      {/* Mark as Lost */}
      {deal.stage !== 'customer_walkthrough' && deal.stage !== 'closed_won' && deal.stage !== 'closed_lost' && (
        <button
          onClick={async () => {
            try {
              await canadaLeadsService.updateStage(deal.id, 'closed_lost')
              navigate('/canada/portal/leads')
            } catch (err) {
              console.error('Mark as lost failed:', err)
            }
          }}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium rounded-lg hover:bg-red-500/15 transition-all"
        >
          <X size={16} /> Mark as Lost
        </button>
      )}
    </div>
  )
}
