import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Check, Sparkles, Wifi, X, Upload, Trash2, Clock,
  FileText, Mail, CheckCircle2, Loader2, Download, ChevronRight, Pencil, Save,
  AlertTriangle, CreditCard, RefreshCw, Send, Eye, ExternalLink, Copy, Tag,
} from 'lucide-react'
import {
  findVerticalByValue,
  buildPersonalizedDeckUrl,
  CAD_VERTICALS,
} from '@/data/cadVerticals'
import { type Deal, type DealStage } from '@/lib/canada-sales-demo-data'
import { closestMonthlyPlanCad, getPlan, PLAN_TIERS, REP_PRICE_HEADROOM_CAD, CAD_RATE, type PlanTier } from '@/lib/canada-proposal-plans'
import { canadaLeadsService } from '@/lib/canada-leads-service'
import {
  useCanadaLead,
  useUpdateCanadaLead,
  useUpdateCanadaLeadStage,
  useDeleteCanadaLead,
  canadaKeys,
} from '@/lib/canada-queries'
import { PortalPage, PortalLoadingSkeleton } from './PortalPage'
import QRCode from 'qrcode'
import { generateInvoicePdf, generateInvoiceNumber, generateInvoiceUrl, type InvoiceInput } from '@/lib/generate-invoice-pdf'
import { generateSlaDocument, type SlaInput } from '@/lib/generate-sla-pdf'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase, getAuthHeaders } from '@/lib/supabase'
import { useToast } from '@/components/Toast'
import { notifyStageChange } from '@/lib/notifications'

// POS connection is no longer part of the rep's pipeline — customers self-connect
// from their own dashboard. We keep pos_connected mapped to step 3 (now Customer
// Walkthrough) so existing leads in that stage still render correctly.
const STAGE_TO_STEP: Record<string, number> = {
  proposal_shown: 1,
  customer_checkout: 2,
  customer_walkthrough: 3,
  pos_connected: 3, // legacy alias — renders same step as walkthrough
  closed_lost: 0,
  // Legacy mappings
  appointment_set: 1,
  prospecting: 1,
  contacted: 1,
  demo_scheduled: 1,
  proposal_sent: 1,
  negotiation: 2,
  closed_won: 3,
}

const STEPS = [
  { num: 1, label: 'Proposal Shown' },
  { num: 2, label: 'Customer Checkout' },
  { num: 3, label: 'Customer Walkthrough' },
]

// Stable id for the generated SLA so it upserts (replaces) rather than
// stacking a new files row each time it's regenerated or signed.
const SLA_FILE_ID = 'sla-doc'

const DEMO_FILES = [
  { id: '1', name: 'proposal_v2.pdf', description: 'Monthly pricing proposal', tag: 'Proposal' },
  { id: '2', name: 'contract_draft.pdf', description: 'Service agreement draft', tag: 'Contract' },
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
                    ? 'bg-pm-accent text-white'
                    : step.num === currentStep
                    ? 'border-2 border-pm-accent text-pm-accent bg-transparent'
                    : 'bg-pm-canada-border text-pm-canada-text-muted'
                }`}
              >
                {step.num < currentStep ? <Check size={18} /> : step.num}
              </div>
              <span className={`text-2xs mt-1.5 whitespace-nowrap ${
                step.num <= currentStep ? 'text-pm-accent' : 'text-pm-canada-text-muted'
              }`}>
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {idx < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 mt-[-18px] ${
                step.num < currentStep ? 'bg-pm-accent' : 'bg-pm-canada-border'
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
  const { toast } = useToast()
  const qc = useQueryClient()
  const updateLead = useUpdateCanadaLead()
  const updateStage = useUpdateCanadaLeadStage()
  const deleteLead = useDeleteCanadaLead()
  const { data: dealData, isLoading, error } = useCanadaLead(id)
  const deal = dealData ?? null
  // Convenience helper: optimistically patch the cached deal so the UI
  // updates immediately while a mutation is in flight. Mutation onSuccess
  // invalidations will rewrite it again with the server's authoritative copy.
  const patchDeal = useCallback((updater: (prev: Deal | null) => Deal | null) => {
    if (!id) return
    qc.setQueryData<Deal | null>(canadaKeys.lead(id), (prev) => updater(prev ?? null))
  }, [id, qc])
  const dealRef = useRef<Deal | null>(null)
  // Records the stage we just wrote locally (optimistic advance / proposal
  // auto-advance) and when. The realtime subscription re-fetches the whole
  // list on any change; that re-fetch can race a read replica and echo back
  // the PRE-update row, clobbering our optimistic stage and making the button
  // look like it "did nothing until refresh." While this window is open we
  // keep our local stage instead of letting a staler echo regress it.
  const localStageRef = useRef<{ stage: DealStage; at: number } | null>(null)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({ business_name: '', contact_name: '', contact_email: '', contact_phone: '', notes: '' })
  const [editSaving, setEditSaving] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  // Step 2 state — price = tier base + rep adjustment (0..REP_PRICE_HEADROOM_CAD)
  const [planId, setPlanId] = useState<PlanTier['id']>('premium')
  const [priceBump, setPriceBump] = useState(0)
  // Per-order fee slider (cents): defaults to the tier's standard rate and
  // slides DOWN only, to the tier redline (orderFeeFloor). Backend re-clamps.
  const [orderFeeCents, setOrderFeeCents] = useState(() => Math.round(getPlan('premium').orderFee * 100))
  const selectedPlan = getPlan(planId)
  const monthlyPrice = selectedPlan.price + priceBump
  const orderFeeFloorCents = Math.round(selectedPlan.orderFeeFloor * 100)
  const orderFeeMaxCents = Math.round(selectedPlan.orderFee * 100)
  const [setupFee, setSetupFee] = useState('0')
  const [firstMonthFree, setFirstMonthFree] = useState(false)

  // Proposal state
  const [proposalGenerating, setProposalGenerating] = useState(false)
  const [proposalEmailing, setProposalEmailing] = useState(false)
  const [proposalSent, setProposalSent] = useState(false)

  // Deck-link card state (industry-specific personalized proposal deck)
  const [deckLinkCopied, setDeckLinkCopied] = useState(false)
  const [deckTagging, setDeckTagging] = useState(false)

  // Invoice state
  const [invoiceBlob, setInvoiceBlob] = useState<Blob | null>(null)
  const [invoiceGenerating, setInvoiceGenerating] = useState(false)
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [invoiceEmailing, setInvoiceEmailing] = useState(false)
  const [invoiceEmailed, setInvoiceEmailed] = useState(false)
  // Square checkout link + an on-screen QR the customer scans to pay. QR is
  // rendered client-side (qrcode lib) so it can't fail to appear when an
  // external QR image service is blocked.
  const [checkoutUrl, setCheckoutUrl] = useState('')
  // Ref mirror of checkoutUrl: handleEmailInvoice may run in the same tick as
  // the generate step, before the state update is visible.
  const checkoutUrlRef = useRef('')
  const [checkoutQr, setCheckoutQr] = useState('')
  const [checkoutCopied, setCheckoutCopied] = useState(false)

  // SLA state
  const [slaBlob, setSlaBlob] = useState<Blob | null>(null)
  const [slaGenerating, setSlaGenerating] = useState(false)
  const [slaSigned, setSlaSigned] = useState(false)
  const [slaSignature, setSlaSignature] = useState('')
  const [slaSigning, setSlaSigning] = useState(false)
  const [slaEmailing, setSlaEmailing] = useState(false)
  const [slaEmailed, setSlaEmailed] = useState(false)
  const [showSlaSign, setShowSlaSign] = useState(false)

  // Page-level action errors (payment notify, invoice/SLA/proposal email, save).
  const [pageError, setPageError] = useState<string | null>(null)

  // Customer account creation state
  const [customerCreating, setCustomerCreating] = useState(false)
  const creatingRef = useRef(false)
  const [customerCredentials, setCustomerCredentials] = useState<{ email: string; tempPassword?: string } | null>(null)
  const [customerError, setCustomerError] = useState<string | null>(null)
  const [credentialEmailing, setCredentialEmailing] = useState(false)
  const [credentialEmailed, setCredentialEmailed] = useState(false)

  // Payment status tracking
  const [paymentStatus, setPaymentStatus] = useState<'idle' | 'checking' | 'pending' | 'active' | 'past_due' | 'failed' | 'unavailable'>('idle')
  const [paymentNotifying, setPaymentNotifying] = useState(false)
  const [paymentNotified, setPaymentNotified] = useState(false)
  const [cardUpdateSending, setCardUpdateSending] = useState(false)
  const [cardUpdateUrl, setCardUpdateUrl] = useState<string | null>(null)

  async function handleCreateCustomerAccount() {
    // React state updates are async, so a fast double-click can enter twice
    // before `customerCreating` re-renders — guard with a synchronous ref.
    if (!deal || creatingRef.current) return
    creatingRef.current = true
    setCustomerCreating(true)
    setCustomerError(null)

    const email = deal.contact_email
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setCustomerError('Invalid email address. Edit the lead to fix it before creating an account.')
      creatingRef.current = false
      setCustomerCreating(false)
      return
    }

    try {
      if (!supabase) throw new Error('Database not connected')

      const API_BASE = import.meta.env.VITE_API_URL || ''
      const authHeaders = await getAuthHeaders()
      const res = await fetch(`${API_BASE}/api/canada/create-customer`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          email,
          business_name: deal.business_name,
          contact_name: deal.contact_name,
          phone: deal.contact_phone,
          vertical: deal.vertical,
          deal_id: deal.id,
          monthly_price: monthlyPrice,
          portal: 'canada',
          plan_id: planId,
          // Rep-negotiated per-order fee (cents, CAD). Only meaningful on
          // phone-agent tiers; the backend clamps to the tier redline.
          ...(selectedPlan.phoneAgent ? { order_fee_cents: Math.min(Math.max(orderFeeCents, orderFeeFloorCents), orderFeeMaxCents) } : {}),
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Failed to create customer account')
      }

      // Backend returns a readable temp password and flags the account for a
      // forced reset on first login. Surface it so the rep can share it directly.
      const data = await res.json().catch(() => ({}))
      setCustomerCredentials({ email, tempPassword: data.temporary_password || '' })
      // The fee seed is best-effort server-side — if it failed, creation still
      // succeeded but the merchant is on the tier default fee. Tell the rep.
      if (selectedPlan.phoneAgent && data.fee_seeded === false) {
        setCustomerError('Account created, but the negotiated per-order fee did NOT save — the merchant is on the plan default. Set it manually or re-try before the walkthrough.')
      }
      await updateStage.mutateAsync({ id: deal.id, stage: 'customer_walkthrough' })
      patchDeal(prev => prev ? { ...prev, stage: 'customer_walkthrough' } : prev)
    } catch (err) {
      setCustomerError(err instanceof Error ? err.message : 'Failed to create account')
    } finally {
      creatingRef.current = false
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
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          template: 'welcome',
          to: deal.contact_email,
          first_name: deal.contact_name.split(' ')[0],
          portal: 'canada',
          extra: {
            business_name: deal.business_name,
            email: customerCredentials.email,
            login_url: `${window.location.origin}/canada/login`,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setCredentialEmailed(true)
      toast('Login credentials emailed to ' + deal.contact_email, 'success')
    } catch {
      toast('Credentials email failed — share them manually', 'error')
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
      const headers = await getAuthHeaders()
      const res = await fetch(`${API_BASE}/api/billing/status/${deal.id}`, { headers })
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
      const headers = await getAuthHeaders()
      const res = await fetch(`${API_BASE}/api/billing/notify-payment-failed`, {
        method: 'POST',
        headers,
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
      setPageError('Failed to send payment notification. Try again.')
    } finally {
      setPaymentNotifying(false)
    }
  }

  async function handleSendCardUpdateLink() {
    if (!deal || !rep) return
    setCardUpdateSending(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const headers = await getAuthHeaders()
      const res = await fetch(`${API_BASE}/api/billing/update-payment-method`, {
        method: 'POST',
        headers,
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
      setPageError('Failed to create payment update link. Try again.')
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

      const planName = closestMonthlyPlanCad(monthlyPrice).label
      const priceCents = Math.round(monthlyPrice * 100)
      const setupFeeCents = Math.round((Number(setupFee) || 0) * 100)

      let checkoutUrl = generateInvoiceUrl(invNum)

      const API_BASE = import.meta.env.VITE_API_URL || ''
      try {
        const authHdrs = await getAuthHeaders()
        const checkoutRes = await fetch(`${API_BASE}/api/stripe/subscribe-link`, {
          method: 'POST',
          headers: authHdrs,
          body: JSON.stringify({
            // no org_id: deal.id is a LEAD, not an org — sending it as org_id
            // tripped the org-membership guard (403) for rep sessions and
            // silently downgraded the QR/PDF link to the local invoice page.
            lead_id: deal.id,
            monthly_amount_cents: priceCents,
            currency: 'CAD',
            business_name: deal.business_name,
            setup_fee_cents: setupFeeCents,
            first_month_free: firstMonthFree,
          }),
        })
        if (checkoutRes.ok) {
          const data = await checkoutRes.json()
          if (data.url) checkoutUrl = data.url
        }
      } catch {
        // Stripe subscribe-link unavailable — fall back to local invoice URL
      }

      // Surface the checkout link + an on-screen QR so the customer can scan
      // to pay right at the checkout step (not only inside the emailed PDF).
      checkoutUrlRef.current = checkoutUrl
      setCheckoutUrl(checkoutUrl)
      try {
        const qr = await QRCode.toDataURL(checkoutUrl, {
          width: 240,
          margin: 1,
          color: { dark: '#00d4aa', light: '#0a0f0d' },
        })
        setCheckoutQr(qr)
      } catch {
        setCheckoutQr('')
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
        await updateStage.mutateAsync({ id: deal.id, stage: 'customer_checkout' })
        patchDeal(prev => prev ? { ...prev, stage: 'customer_checkout' } : prev)
      }
    } catch (err) {
      console.error('[Invoice] Generation failed:', err)
    } finally {
      setInvoiceGenerating(false)
    }
  }

  function handleDownloadInvoice() {
    if (!invoiceBlob) return
    const url = URL.createObjectURL(invoiceBlob)
    window.open(url, '_blank')
  }

  async function handleEmailInvoice() {
    if (!deal) return
    if (!invoiceBlob) await handleGenerateInvoice()
    setInvoiceEmailing(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/email/send`, {
        method: 'POST',
        headers: await getAuthHeaders(),
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
            // Stripe subscribe short-link (opens hosted checkout) — the local
            // /canada/invoice page is only the last-resort fallback.
            invoice_url: checkoutUrlRef.current || checkoutUrl || generateInvoiceUrl(invoiceNumber),
            recurring: true,
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setInvoiceEmailed(true)
      toast('Invoice emailed to ' + deal.contact_email, 'success')
    } catch (err) {
      console.error('[Invoice] Email failed:', err)
      toast('Invoice email failed — try again or share the PDF directly', 'error')
      setPageError('Invoice email failed to send. Try again or share the PDF directly.')
    } finally {
      setInvoiceEmailing(false)
    }
  }

  async function handleGenerateSla() {
    if (!deal || !rep) return
    setSlaGenerating(true)
    try {
      const slaInput: SlaInput = {
        country: 'CA',
        clientCompanyName: deal.business_name,
        region: deal.province || 'Ontario',
        posSystem: 'N/A',
        repName: rep.name || 'Sales Representative',
        planName: closestMonthlyPlanCad(monthlyPrice).label,
        monthlyPriceCents: monthlyPrice * 100,
        setupFeeCents: (Number(setupFee) || 0) * 100,
        firstMonthFree,
        startDate: new Date().toISOString().slice(0, 10),
      }
      const blob = await generateSlaDocument(slaInput)
      setSlaBlob(blob)
      upsertSlaFile(deal.business_name, false)
    } catch (err) {
      console.error('[SLA] Generation failed:', err)
    } finally {
      setSlaGenerating(false)
    }
  }

  // Surface the generated SLA in the Project Files list (clicking it opens the
  // in-memory slaBlob via the files row handler, which keys off tag === 'Contract').
  function upsertSlaFile(businessName: string, signed: boolean) {
    const entry = {
      id: SLA_FILE_ID,
      name: `SLA_${businessName.replace(/\s+/g, '_')}.pdf`,
      description: signed ? 'Service Level Agreement — signed' : 'Service Level Agreement',
      tag: 'Contract',
    }
    setFiles(prev =>
      prev.some(f => f.id === SLA_FILE_ID)
        ? prev.map(f => (f.id === SLA_FILE_ID ? entry : f))
        : [...prev, entry],
    )
  }

  function handleDownloadSla() {
    if (!slaBlob) return
    const url = URL.createObjectURL(slaBlob)
    window.open(url, '_blank')
  }

  async function handleSignSla() {
    if (!slaSignature.trim() || !deal || !rep) return
    setSlaSigning(true)
    try {
      const slaInput: SlaInput = {
        country: 'CA',
        clientCompanyName: deal.business_name,
        region: deal.province || 'Ontario',
        posSystem: 'N/A',
        repName: rep.name || 'Sales Representative',
        planName: closestMonthlyPlanCad(monthlyPrice).label,
        monthlyPriceCents: monthlyPrice * 100,
        setupFeeCents: (Number(setupFee) || 0) * 100,
        firstMonthFree,
        startDate: new Date().toISOString().slice(0, 10),
        clientSignature: slaSignature,
      }
      const signedBlob = await generateSlaDocument(slaInput)
      setSlaBlob(signedBlob)
      setSlaSigned(true)
      upsertSlaFile(deal.business_name, true)
      setShowSlaSign(false)

      const API_BASE = import.meta.env.VITE_API_URL || ''
      const setupFeeNum = Number(setupFee) || 0
      try {
        const emailRes = await fetch(`${API_BASE}/api/email/send`, {
          method: 'POST',
          headers: await getAuthHeaders(),
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
              provider_signatory: `${rep.name || 'Meridian Sales'}, Account Representative`,
              monthly_price: `CA$${monthlyPrice.toLocaleString()}/mo`,
              setup_fee: setupFeeNum > 0 ? `CA$${setupFeeNum.toLocaleString()}` : '',
              first_month_free: firstMonthFree,
              due_today: `CA$${((firstMonthFree ? 0 : monthlyPrice) + setupFeeNum).toLocaleString()}`,
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
        headers: await getAuthHeaders(),
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
            provider_signatory: `${rep?.name || 'Meridian Sales'}, Account Representative`,
            monthly_price: `CA$${monthlyPrice.toLocaleString()}/mo`,
            setup_fee: (Number(setupFee) || 0) > 0 ? `CA$${(Number(setupFee) || 0).toLocaleString()}` : '',
            first_month_free: firstMonthFree,
            due_today: `CA$${((firstMonthFree ? 0 : monthlyPrice) + (Number(setupFee) || 0)).toLocaleString()}`,
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setSlaEmailed(true)
      toast('SLA emailed to ' + deal.contact_email, 'success')
    } catch (err) {
      console.error('[SLA] Email failed:', err)
      toast('SLA email failed — try again or share the PDF', 'error')
      setPageError('SLA email failed to send. Try again or download and share the PDF.')
    } finally {
      setSlaEmailing(false)
    }
  }

  // Opens the lead's industry-specific proposal deck (the live hosted deck on
  // meridian-decks.vercel.app, personalized with rep + business name) — the
  // current proposal format. Falls back to prompting the rep to tag the
  // business type, since the deck is selected from deal.vertical.
  function proposalDeckUrl(): string | null {
    if (!deal || !rep) return null
    const deck = findVerticalByValue(deal.vertical)
    if (!deck) return null
    return buildPersonalizedDeckUrl(deck.slug, rep, deal.business_name, {
      monthly: monthlyPrice,
      setup: Number(setupFee) || 0,
      currency: 'CAD',
      firstMonthFree,
    })
  }

  function openProposalDeck(): string | null {
    if (!deal || !rep) return null
    const url = proposalDeckUrl()
    if (!url) {
      toast("Tag this lead's business type first — the proposal is built from its industry deck.", 'info')
      return null
    }
    window.open(url, '_blank')
    return url
  }

  async function handleGenerateProposal() {
    if (!deal) return
    setProposalGenerating(true)
    try {
      const url = openProposalDeck()
      if (!url) return
      if (deal.stage === 'appointment_set' || deal.stage === 'prospecting' || deal.stage === 'contacted') {
        localStageRef.current = { stage: 'proposal_shown', at: Date.now() }
        patchDeal(prev => prev ? { ...prev, stage: 'proposal_shown' } : prev)
        await updateStage.mutateAsync({ id: deal.id, stage: 'proposal_shown' })
      }
    } catch (err) {
      console.error('[Proposal] Generation failed:', err)
    } finally {
      setProposalGenerating(false)
    }
  }

  function handleViewProposal() {
    openProposalDeck()
  }

  async function handleEmailProposal() {
    if (!deal) return
    setProposalEmailing(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/email/send`, {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          template: 'proposal_sent',
          to: deal.contact_email,
          first_name: deal.contact_name.split(' ')[0],
          portal: 'canada',
          extra: {
            business_name: deal.business_name,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
            plan_name: closestMonthlyPlanCad(monthlyPrice).label,
            monthly_price: `CA$${monthlyPrice.toLocaleString()}`,
            setup_fee: (Number(setupFee) || 0) > 0 ? `CA$${(Number(setupFee) || 0).toLocaleString()}` : '',
            due_today: `CA$${((firstMonthFree ? 0 : monthlyPrice) + (Number(setupFee) || 0)).toLocaleString()}`,
            proposal_url: proposalDeckUrl() || '',
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setProposalSent(true)
      toast('Proposal emailed to ' + deal.contact_email, 'success')
      if (deal.stage === 'appointment_set' || deal.stage === 'proposal_shown' || deal.stage === 'contacted' || deal.stage === 'demo_scheduled') {
        await updateStage.mutateAsync({ id: deal.id, stage: 'proposal_shown' })
        patchDeal(prev => prev ? { ...prev, stage: 'proposal_shown' } : prev)
      }
    } catch (err) {
      console.error('[Proposal] Email failed:', err)
      toast('Proposal email failed — try again or share the PDF', 'error')
      setPageError('Proposal email failed to send. Try again or download and share the PDF.')
    } finally {
      setProposalEmailing(false)
    }
  }

  // Files state
  const [files, setFiles] = useState(DEMO_FILES)

  useEffect(() => { dealRef.current = deal }, [deal])

  // Seed monthlyPrice from the lead's stored value ONCE per lead. Keying on
  // deal.id (not the whole deal object) is deliberate: the realtime
  // subscription and optimistic patches hand back a fresh `deal` reference on
  // every change, and re-running this on each one would snap the rep's
  // hand-tuned slider back to the stored value mid-edit — the price the
  // proposal/deck then used wouldn't match what the rep selected.
  const pricedForIdRef = useRef<string | null>(null)
  useEffect(() => {
    if (deal && deal.id !== pricedForIdRef.current) {
      pricedForIdRef.current = deal.id
      // Legacy stored values snap to the closest tier; any remainder above
      // the tier base becomes the rep adjustment (clamped to the headroom).
      const stored = deal.monthly_value || 0
      const plan = closestMonthlyPlanCad(stored || 500)
      setPlanId(plan.id)
      const bump = stored ? Math.round(stored - plan.price) : 0
      setPriceBump(Math.min(REP_PRICE_HEADROOM_CAD, Math.max(0, bump)))
    }
  }, [deal])

  // Bridge the realtime subscription into the query cache, but keep the
  // stage-change notification side-effect that's specific to this page.
  useEffect(() => {
    if (!id) return
    // Subscribe with the same rep filter the rest of the page uses, so the
    // realtime payload's scope matches the canadaKeys.leads(rep?.rep_id)
    // bucket we write through to below — prevents unfiltered deals from
    // bleeding into a scoped reader (e.g. a future admin/manager variant
    // holding a real rep_id while viewing this lead).
    const channel = canadaLeadsService.subscribe(rep?.rep_id, deals => {
      const updated = deals.find(d => d.id === id)
      if (updated) {
        const current = dealRef.current
        // Guard against a stale realtime echo regressing our optimistic stage:
        // if we advanced locally within the last few seconds and the echo
        // carries the OLD stage, keep ours. A genuinely newer stage (matches or
        // moves past our local one) is allowed through.
        const local = localStageRef.current
        const withinWindow = local && Date.now() - local.at < 8000
        const echoIsStale =
          withinWindow && updated.stage !== local!.stage && current?.stage === local!.stage
        const resolved = echoIsStale ? { ...updated, stage: local!.stage } : updated
        if (current && resolved.stage !== current.stage) {
          notifyStageChange(resolved.business_name, resolved.stage)
          toast(`${resolved.business_name} moved to ${resolved.stage.replace(/_/g, ' ')}`, 'info')
        }
        qc.setQueryData(canadaKeys.lead(id), resolved)
        qc.setQueryData(canadaKeys.leads(rep?.rep_id), deals)
      }
    })
    return () => { canadaLeadsService.unsubscribe(channel) }
  }, [id, qc, rep?.rep_id, toast])

  const notFoundEmptyState = (
    <div className="space-y-4">
      <Link to="/canada/portal/leads" className="inline-flex items-center gap-1.5 text-sm text-pm-canada-text-muted hover:text-white transition-colors">
        <ArrowLeft size={16} /> Leads
      </Link>
      <div className="text-center py-16 text-pm-canada-text-muted">Lead not found.</div>
    </div>
  )

  // Status-shell early return: PortalPage owns skeleton/error/not-found.
  // The happy-path body below only renders when `deal` is loaded.
  if (isLoading || error || !deal) {
    return (
      <PortalPage
        isLoading={isLoading}
        error={error}
        isEmpty={!deal}
        emptyState={notFoundEmptyState}
        loadingSkeleton={<PortalLoadingSkeleton char="S" />}
      >
        {/* Unreachable — wrapper handles all three branches above. */}
        <></>
      </PortalPage>
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
      setFiles(prev => [...prev, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, name: file.name, description: `Uploaded ${ext} file`, tag: ext }])
    }
    input.click()
  }

  const inputClass = 'w-full px-3 py-2.5 bg-pm-canada-surface border border-pm-canada-border rounded-lg text-sm text-white placeholder-pm-canada-text-muted focus:outline-none focus:border-pm-accent/50 focus:ring-1 focus:ring-pm-accent/20 transition-colors'

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Back link */}
      <Link to="/canada/portal/leads" className="inline-flex items-center gap-1.5 text-sm text-pm-canada-text-muted hover:text-white transition-colors">
        <ArrowLeft size={16} /> Leads
      </Link>

      {/* Header */}
      {editing ? (
        <div className="bg-pm-canada-surface border border-pm-accent/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-pm-accent">Edit Lead</h2>
            <button onClick={() => setEditing(false)} className="text-xs text-pm-canada-text-muted hover:text-white">Cancel</button>
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
              // Snapshot the fields we're about to overwrite so we can roll
              // back if the write fails. Optimistic-first: update the displayed
              // deal and close the editor immediately so a stalled Supabase
              // write can't trap the UI on an infinite spinner.
              const snapshot = {
                business_name: deal.business_name,
                contact_name: deal.contact_name,
                contact_email: deal.contact_email,
                contact_phone: deal.contact_phone,
                notes: deal.notes,
              }
              const next = { ...editForm }
              setEditSaving(true)
              patchDeal(prev => prev ? { ...prev, ...next } : prev)
              setEditing(false)
              try {
                await updateLead.mutateAsync({ id: deal.id, updates: next })
              } catch (err) {
                patchDeal(prev => prev ? { ...prev, ...snapshot } : prev)
                setEditForm(next)
                setEditing(true)
                setPageError(err instanceof Error ? `Save failed: ${err.message}` : 'Failed to save changes. Please try again.')
              } finally {
                setEditSaving(false)
              }
            }}
            className="flex items-center gap-2 px-4 py-2 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 disabled:opacity-50 transition-all"
          >
            {editSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save Changes
          </button>
        </div>
      ) : (
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{deal.business_name}</h1>
            <p className="text-sm text-pm-canada-text-muted mt-1">
              {deal.contact_name} &middot; <span className="text-pm-amber-gold font-semibold">CA${deal.monthly_value.toLocaleString()}/mo</span> &middot; {deal.contact_email}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
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
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-pm-canada-text-muted border border-pm-canada-border rounded-lg hover:text-white hover:border-[#2a3430] transition-colors"
            >
              <Pencil size={12} /> Edit
            </button>
            {/* Delete (hard delete — distinct from the soft "Mark as Lost" stage) */}
            <button
              onClick={() => setShowDelete(true)}
              data-testid="delete-lead-detail"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-pm-canada-text-muted border border-pm-canada-border rounded-lg hover:text-red-400 hover:border-red-500/30 transition-colors"
            >
              <Trash2 size={12} /> Delete
            </button>
          </div>
        </div>
      )}

      {/* Proposal deck for this lead (industry-specific) */}
      <LeadDeckCard
        deal={deal}
        rep={rep}
        monthly={monthlyPrice}
        setup={Number(setupFee) || 0}
        copied={deckLinkCopied}
        tagging={deckTagging}
        onCopy={async (url) => {
          try {
            await navigator.clipboard.writeText(url)
            setDeckLinkCopied(true)
            setTimeout(() => setDeckLinkCopied(false), 1800)
          } catch {
            toast('Could not copy link — try long-pressing the Open button.', 'error')
          }
        }}
        onTagVertical={async (slug) => {
          if (!deal) return
          setDeckTagging(true)
          try {
            await updateLead.mutateAsync({ id: deal.id, updates: { vertical: slug } })
            patchDeal(prev => prev ? { ...prev, vertical: slug } : prev)
          } catch (err) {
            toast(err instanceof Error ? `Could not tag lead: ${err.message}` : 'Could not tag lead.', 'error')
          } finally {
            setDeckTagging(false)
          }
        }}
      />

      {/* Stepper */}
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
        <HorizontalStepper currentStep={currentStep} />
      </div>

      {/* Page-level action errors */}
      {pageError && (
        <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
          <span className="text-xs text-red-400">{pageError}</span>
          <button onClick={() => setPageError(null)} className="text-2xs text-red-400/70 hover:text-red-400 font-medium flex-shrink-0">
            Dismiss
          </button>
        </div>
      )}

      {/* Step 1 - Proposal (always visible) */}
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Proposal</h2>

        {/* Plan tier + price adjustment */}
        <div>
          <label className="text-xs text-pm-canada-text-muted block mb-1.5">Plan (CAD)</label>
          <div className="grid grid-cols-3 gap-2 mb-3">
            {PLAN_TIERS.map(plan => (
              <button key={plan.id} onClick={() => { setPlanId(plan.id); setPriceBump(0); setOrderFeeCents(Math.round(plan.orderFee * 100)) }}
                className={`p-2.5 rounded-lg border text-left transition-colors ${
                  planId === plan.id
                    ? 'border-pm-accent/50 bg-pm-accent/5'
                    : 'border-pm-canada-border hover:border-pm-canada-text-faint bg-pm-canada-bg'
                }`}>
                <p className="text-xs font-semibold text-white">{plan.label}</p>
                <p className="text-sm font-bold text-pm-amber-gold">CA${plan.price}/mo</p>
                <p className="text-2xs text-pm-canada-text-muted mt-0.5">
                  {plan.phoneAgent ? `Phone agent · CA$${plan.orderFee.toFixed(2)}/order` : 'No phone agent'}
                </p>
              </button>
            ))}
          </div>
          <label className="text-xs text-pm-canada-text-muted block mb-1.5">
            Price Adjustment <span className="text-pm-canada-text-faint">(up to +CA${REP_PRICE_HEADROOM_CAD}/mo)</span>
          </label>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={0}
              max={REP_PRICE_HEADROOM_CAD}
              step={5}
              value={priceBump}
              onChange={e => setPriceBump(Number(e.target.value))}
              className="flex-1 h-2 bg-pm-canada-border rounded-full appearance-none cursor-pointer accent-pm-accent"
            />
            <span className="text-sm font-semibold text-pm-amber-gold w-28 text-right">CA${monthlyPrice.toLocaleString()}/mo</span>
          </div>
          <p className="text-2xs text-pm-canada-text-faint mt-1">~US${Math.round(monthlyPrice / CAD_RATE).toLocaleString()}/mo. Base price is the floor — no discounts.</p>

          {/* Per-order fee slider — phone-agent tiers only. Slides DOWN from the
              tier's standard rate to the redline; the backend clamps to the
              same floor so the redline is enforced server-side too. */}
          {selectedPlan.phoneAgent && (
            <div className="mt-4">
              <label className="text-xs text-pm-canada-text-muted block mb-1.5">
                Per-Order Fee <span className="text-pm-canada-text-faint">(redline CA${selectedPlan.orderFeeFloor.toFixed(2)}/order)</span>
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={orderFeeFloorCents}
                  max={orderFeeMaxCents}
                  step={1}
                  value={Math.min(Math.max(orderFeeCents, orderFeeFloorCents), orderFeeMaxCents)}
                  onChange={e => setOrderFeeCents(Number(e.target.value))}
                  className="flex-1 h-2 bg-pm-canada-border rounded-full appearance-none cursor-pointer accent-pm-accent"
                />
                <span className="text-sm font-semibold text-pm-amber-gold w-28 text-right">CA${(orderFeeCents / 100).toFixed(2)}/order</span>
              </div>
              <p className="text-2xs text-pm-canada-text-faint mt-1">
                Standard rate CA${selectedPlan.orderFee.toFixed(2)} — negotiate down only, never below the redline.
              </p>
              <p className="text-2xs text-pm-canada-text-muted mt-1.5 px-2.5 py-1.5 rounded-md bg-pm-canada-bg border border-pm-canada-border">
                Voice calls: first 3 minutes of every call included, then <span className="font-semibold text-pm-amber-gold">CA$0.45/min</span> billed automatically to the merchant's Meridian account. Calls end automatically at 5 minutes, so overage never exceeds CA$0.90/call.
              </p>
            </div>
          )}
        </div>

        {/* Setup Fee */}
        <div>
          <label className="text-xs text-pm-canada-text-muted block mb-1.5">Setup Fee</label>
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
          <div className={`w-9 h-5 rounded-full transition-colors relative ${firstMonthFree ? 'bg-pm-accent' : 'bg-pm-canada-border'}`}
            onClick={() => setFirstMonthFree(!firstMonthFree)}
          >
            <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${firstMonthFree ? 'translate-x-4' : 'translate-x-0.5'}`} />
          </div>
          <span className="text-sm text-white">First month free</span>
        </label>

        {/* First-month-free breakdown — only shown when toggle is on */}
        {firstMonthFree && (
          <div className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-pm-accent/5 border border-pm-accent/20">
            <span className="text-xs text-pm-canada-text-muted">First month</span>
            <span className="text-xs font-semibold text-pm-accent">
              CA$0 <span className="text-pm-canada-text-faint font-normal">(free — setup fee still due today)</span>
            </span>
          </div>
        )}

        {/* Due Today — always visible so the rep and customer always see the exact
            charge that will hit the card today, in both toggle states. */}
        <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-pm-canada-bg border border-pm-canada-border">
          <span className="text-xs text-pm-canada-text-muted">Due today</span>
          <span className="text-sm font-bold text-pm-accent">
            CA${((firstMonthFree ? 0 : monthlyPrice) + (Number(setupFee) || 0)).toLocaleString()}
          </span>
        </div>

        {/* Buttons */}
        <button
          onClick={handleGenerateProposal}
          disabled={proposalGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 disabled:opacity-50 transition-all"
        >
          {proposalGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating…</>
          ) : (
            <><Sparkles size={16} /> Generate Proposal</>
          )}
        </button>

        <div className="flex gap-3">
          <button
            onClick={handleViewProposal}
            disabled={proposalGenerating}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 disabled:opacity-50 transition-all"
          >
            {proposalGenerating ? (
              <><Loader2 size={16} className="animate-spin" /> Generating…</>
            ) : (
              <><Eye size={16} /> View Proposal</>
            )}
          </button>
          <button
            onClick={handleEmailProposal}
            disabled={proposalEmailing || proposalGenerating}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-pm-canada-border text-white text-sm font-medium rounded-lg hover:border-pm-accent/30 disabled:opacity-50 transition-all"
          >
            {proposalEmailing ? (
              <><Loader2 size={16} className="animate-spin" /> Sending…</>
            ) : proposalSent ? (
              <><CheckCircle2 size={16} className="text-pm-accent" /> Sent!</>
            ) : (
              <><Mail size={16} /> Email Proposal</>
            )}
          </button>
        </div>
      </div>

      {/* Step 2 - Invoice / Customer Checkout (visible at step 2+) */}
      {currentStep >= 2 && (
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Invoice &amp; Checkout</h2>
        <p className="text-xs text-pm-canada-text-muted">
          Generate a custom invoice in CAD with a QR code the customer can scan to view. Invoices recur monthly.
        </p>

        <button
          onClick={handleGenerateInvoice}
          disabled={invoiceGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 disabled:opacity-50 transition-all"
        >
          {invoiceGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating Invoice…</>
          ) : (
            <><FileText size={16} /> {invoiceBlob ? 'Regenerate Invoice' : 'Generate Invoice (CAD)'}</>
          )}
        </button>

        {invoiceBlob && (
          <>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-pm-accent/10 border border-pm-accent/20">
              <CheckCircle2 size={16} className="text-pm-accent" />
              <span className="text-xs text-pm-accent font-medium">
                Invoice #{invoiceNumber} ready — includes QR code for online viewing.
              </span>
              <button onClick={handleDownloadInvoice} className="ml-auto text-pm-accent hover:text-white transition-colors">
                <Download size={14} />
              </button>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleDownloadInvoice}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-pm-canada-border text-white text-sm font-medium rounded-lg hover:border-pm-accent/30 transition-all"
              >
                <Eye size={16} /> View Invoice
              </button>
              <button
                onClick={handleEmailInvoice}
                disabled={invoiceEmailing}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-pm-canada-border text-white text-sm font-medium rounded-lg hover:border-pm-accent/30 disabled:opacity-50 transition-all"
              >
                {invoiceEmailing ? (
                  <><Loader2 size={16} className="animate-spin" /> Sending…</>
                ) : invoiceEmailed ? (
                  <><CheckCircle2 size={16} className="text-pm-accent" /> Invoice Sent!</>
                ) : (
                  <><Mail size={16} /> Email Invoice</>
                )}
              </button>
            </div>
            {checkoutQr && (
              <div className="flex flex-col sm:flex-row items-center gap-4 p-4 rounded-lg bg-pm-canada-bg border border-pm-accent/20">
                <img src={checkoutQr} alt="Checkout QR code" className="w-28 h-28 rounded-lg shrink-0" />
                <div className="min-w-0 flex-1 text-center sm:text-left">
                  <p className="text-sm font-semibold text-white mb-0.5">Monthly Subscription — Scan to Subscribe</p>
                  <p className="text-2xs text-pm-canada-text-muted mb-2.5">
                    Customer scans this to start their monthly CA$ subscription — or tap the link below.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <a
                      href={checkoutUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-pm-accent text-pm-canada-bg text-xs font-semibold hover:bg-pm-accent/90 active:scale-[0.98] transition-all"
                    >
                      Open subscribe link <ExternalLink size={11} />
                    </a>
                    <button
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(checkoutUrl)
                          setCheckoutCopied(true)
                          setTimeout(() => setCheckoutCopied(false), 1800)
                        } catch {
                          toast('Could not copy — long-press the Open button instead.', 'error')
                        }
                      }}
                      className={`inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-medium transition-all ${
                        checkoutCopied
                          ? 'border-pm-accent/40 bg-pm-accent/10 text-pm-accent'
                          : 'border-pm-canada-border bg-pm-canada-surface text-pm-muted hover:border-[#1a3a30] hover:text-white active:scale-[0.98]'
                      }`}
                    >
                      {checkoutCopied ? <Check size={11} /> : <Copy size={11} />}
                      {checkoutCopied ? 'Copied' : 'Copy link'}
                    </button>
                  </div>
                </div>
              </div>
            )}
            <p className="text-2xs text-pm-canada-text-faint">
              Recurring monthly — customer will be billed CA${monthlyPrice.toLocaleString()}/mo automatically.
            </p>
          </>
        )}
      </div>
      )}

      {/* Payment Status & Card Management (visible at step 2+) */}
      {currentStep >= 2 && (
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CreditCard size={16} className="text-pm-accent" />
            <h2 className="text-sm font-semibold text-white">Payment Status</h2>
          </div>
          <button
            onClick={checkPaymentStatus}
            disabled={paymentStatus === 'checking'}
            className="flex items-center gap-1.5 px-3 py-1.5 text-2xs font-medium text-pm-canada-text-muted border border-pm-canada-border rounded-lg hover:text-pm-accent hover:border-pm-accent/30 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={10} className={paymentStatus === 'checking' ? 'animate-spin' : ''} />
            {paymentStatus === 'idle' ? 'Check Status' : 'Refresh'}
          </button>
        </div>

        {paymentStatus === 'idle' && (
          <p className="text-xs text-pm-canada-text-muted">Click "Check Status" to see if the customer has paid.</p>
        )}

        {paymentStatus === 'checking' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-pm-canada-border">
            <Loader2 size={14} className="text-pm-accent animate-spin" />
            <span className="text-xs text-pm-canada-text-muted">Checking payment status...</span>
          </div>
        )}

        {paymentStatus === 'active' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-pm-accent/10 border border-pm-accent/20">
            <CheckCircle2 size={16} className="text-pm-accent" />
            <div>
              <span className="text-xs text-pm-accent font-medium">Payment confirmed — subscription active</span>
              <p className="text-2xs text-pm-canada-text-faint mt-0.5">Card on file is being used for recurring billing.</p>
            </div>
          </div>
        )}

        {paymentStatus === 'pending' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-pm-amber-gold/10 border border-pm-amber-gold/20">
            <Clock size={16} className="text-pm-amber-gold" />
            <div>
              <span className="text-xs text-pm-amber-gold font-medium">Payment pending — invoice sent, awaiting payment</span>
              <p className="text-2xs text-pm-canada-text-faint mt-0.5">The customer has been invoiced but hasn't paid yet.</p>
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
                <p className="text-2xs text-pm-canada-text-faint mt-0.5">
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
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 disabled:opacity-50 transition-all"
              >
                {cardUpdateSending ? (
                  <><Loader2 size={14} className="animate-spin" /> Creating Link...</>
                ) : (
                  <><CreditCard size={14} /> Send Card Update Link</>
                )}
              </button>
            </div>

            {cardUpdateUrl && (
              <div className="p-3 rounded-lg bg-pm-canada-bg border border-pm-canada-border space-y-2">
                <p className="text-2xs text-pm-canada-text-muted">Payment update link (sent to customer):</p>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={cardUpdateUrl}
                    className="flex-1 px-2 py-1.5 bg-pm-canada-surface border border-pm-canada-border rounded text-2xs text-white font-mono truncate"
                  />
                  <button
                    onClick={() => { navigator.clipboard.writeText(cardUpdateUrl); }}
                    className="px-3 py-1.5 text-2xs text-pm-accent border border-pm-accent/30 rounded hover:bg-pm-accent/10 transition-colors"
                  >
                    Copy
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {paymentStatus === 'unavailable' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-pm-canada-border">
            <span className="text-xs text-pm-canada-text-muted">No billing record found yet — invoice may not have been created.</span>
          </div>
        )}
      </div>
      )}

      {/* Step 2b - SLA Document (visible at step 2+) */}
      {currentStep >= 2 && (
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-pm-accent" />
          <h2 className="text-sm font-semibold text-white">Service Level Agreement</h2>
        </div>
        <p className="text-xs text-pm-canada-text-muted">
          Generate an SLA document for the client to sign. {deal?.province && (deal.province.toLowerCase().includes('quebec') || deal.province.toLowerCase() === 'qc') ? 'Includes PIPEDA + Quebec Law 25 compliance.' : 'Includes PIPEDA compliance.'}
        </p>

        <button
          onClick={handleGenerateSla}
          disabled={slaGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-pm-canada-border border border-[#2a3830] text-white text-sm font-semibold rounded-lg hover:border-pm-accent/30 disabled:opacity-50 transition-all"
        >
          {slaGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating SLA…</>
          ) : (
            <><FileText size={16} /> {slaBlob ? 'Regenerate SLA' : 'Generate SLA Document'}</>
          )}
        </button>

        {slaBlob && (
          <>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-pm-accent/10 border border-pm-accent/20">
              <CheckCircle2 size={16} className="text-pm-accent" />
              <span className="text-xs text-pm-accent font-medium">
                SLA document ready{slaSigned ? ' — signed' : ''}.
              </span>
              <button onClick={handleDownloadSla} className="ml-auto text-pm-accent hover:text-white transition-colors">
                <Download size={14} />
              </button>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleDownloadSla}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-pm-canada-border text-white text-sm font-medium rounded-lg hover:border-pm-accent/30 transition-all"
              >
                <Eye size={16} /> View SLA
              </button>
              {!slaSigned ? (
                <button
                  onClick={() => setShowSlaSign(true)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 transition-all"
                >
                  <Pencil size={16} /> Sign SLA
                </button>
              ) : (
                <button
                  onClick={handleEmailSla}
                  disabled={slaEmailing}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-pm-canada-border text-white text-sm font-medium rounded-lg hover:border-pm-accent/30 disabled:opacity-50 transition-all"
                >
                  {slaEmailing ? (
                    <><Loader2 size={16} className="animate-spin" /> Sending…</>
                  ) : slaEmailed ? (
                    <><CheckCircle2 size={16} className="text-pm-accent" /> SLA Sent!</>
                  ) : (
                    <><Mail size={16} /> Email Signed SLA</>
                  )}
                </button>
              )}
            </div>

            {slaSigned && (
              <div className="text-2xs text-pm-canada-text-faint space-y-0.5">
                <p>Provider: Aidan Pierce, Founder & CEO — {new Date().toLocaleDateString('en-CA')}</p>
                <p>Client: {slaSignature} — {new Date().toLocaleDateString('en-CA')}</p>
                {slaEmailed && <p className="text-pm-accent">Signed copy emailed to {deal?.contact_email}</p>}
              </div>
            )}
          </>
        )}

        {/* Signature Modal */}
        {showSlaSign && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="w-full max-w-lg bg-pm-canada-surface border border-pm-canada-border rounded-xl p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-base font-semibold text-white">Sign Service Level Agreement</h3>
                <button onClick={() => setShowSlaSign(false)} className="p-1.5 rounded-lg hover:bg-pm-canada-border transition-colors">
                  <X size={18} className="text-pm-canada-text-muted" />
                </button>
              </div>
              <p className="text-xs text-pm-canada-text-muted mb-4">
                By typing your full legal name below, you acknowledge that you have read and agree to the terms of the Service Level Agreement between Meridian AI Business Solutions and {deal?.business_name}. A signed copy will be emailed to both parties.
              </p>
              <div className="space-y-4">
                {/* Provider signature — pre-filled */}
                <div className="p-4 bg-pm-canada-bg border border-pm-canada-border rounded-lg">
                  <p className="text-2xs text-pm-canada-text-muted mb-1">Provider — Meridian AI Business Solutions</p>
                  <p className="text-lg font-serif italic text-pm-accent">Aidan Pierce</p>
                  <p className="text-2xs text-pm-canada-text-faint mt-1">Founder & CEO</p>
                </div>

                {/* Client signature */}
                <div>
                  <label className="text-xs text-pm-canada-text-muted mb-1.5 block">Client — {deal?.business_name}</label>
                  <input
                    type="text"
                    value={slaSignature}
                    onChange={e => setSlaSignature(e.target.value)}
                    placeholder="Client signatory full legal name"
                    className="w-full px-3 py-2.5 bg-pm-canada-bg border border-pm-canada-border rounded-lg text-sm text-white placeholder-pm-canada-text-muted focus:outline-none focus:border-pm-accent/50 focus:ring-1 focus:ring-pm-accent/20 transition-colors"
                  />
                </div>
                {slaSignature.trim() && (
                  <div className="p-4 bg-pm-canada-bg border border-pm-canada-border rounded-lg">
                    <p className="text-2xs text-pm-canada-text-muted mb-1">Client signature preview</p>
                    <p className="text-xl font-serif italic text-white">{slaSignature}</p>
                  </div>
                )}

                <p className="text-2xs text-pm-canada-text-faint">
                  Date: {new Date().toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
                <div className="flex justify-end gap-2 mt-4">
                  <button onClick={() => setShowSlaSign(false)} className="px-4 py-2 text-sm text-pm-canada-text-muted hover:text-white transition-colors">Cancel</button>
                  <button
                    onClick={handleSignSla}
                    disabled={!slaSignature.trim() || slaSigning}
                    className="px-4 py-2 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 disabled:opacity-50 transition-all"
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

      {/* NO POS UI here by doctrine: POS connection is completed by the CUSTOMER
          inside their own portal (/canada/onboard wizard or portal settings).
          The deal stage flips to pos_connected via the backend when their data
          starts flowing — the rep portal carries no POS card at all. */}

      {/* Project Files */}
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Project Files</h2>
          <button onClick={handleUpload} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-pm-accent border border-pm-accent/30 rounded-lg hover:bg-pm-accent/10 transition-all">
            <Upload size={14} /> Upload
          </button>
        </div>

        <div className="space-y-2">
          {files.map(file => (
            <div key={file.id} className="flex items-center gap-3 p-3 bg-pm-canada-bg border border-pm-canada-border rounded-lg hover:border-pm-accent/20 transition-colors cursor-pointer group"
              onClick={() => {
                if (file.tag === 'Proposal') { openProposalDeck() }
                else if (file.tag === 'Contract' && slaBlob) { const u = URL.createObjectURL(slaBlob); window.open(u, '_blank') }
              }}
            >
              <FileText size={16} className="text-pm-canada-text-muted flex-shrink-0 group-hover:text-pm-accent transition-colors" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate group-hover:text-pm-accent transition-colors">{file.name}</p>
                <p className="text-2xs text-pm-canada-text-faint">{file.description}</p>
              </div>
              <span className="text-2xs px-2 py-0.5 rounded bg-pm-canada-border text-pm-canada-text-muted font-medium flex-shrink-0">
                {file.tag}
              </span>
              <ExternalLink size={14} className="text-pm-canada-text-faint group-hover:text-pm-accent transition-colors flex-shrink-0" />
              <button
                onClick={(e) => { e.stopPropagation(); removeFile(file.id) }}
                className="p-1 rounded hover:bg-red-500/10 transition-colors flex-shrink-0"
              >
                <Trash2 size={14} className="text-pm-canada-text-muted hover:text-red-400" />
              </button>
            </div>
          ))}
          {files.length === 0 && (
            <p className="text-xs text-pm-canada-text-faint text-center py-4">No files uploaded yet.</p>
          )}
        </div>
      </div>

      {/* Stage Advancement */}
      {currentStep > 0 && currentStep < 3 && deal.stage !== 'closed_lost' && (
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white">Advance Deal</h2>
          <button
            data-testid="advance-stage-button"
            disabled={updateStage.isPending}
            onClick={async () => {
              const pipeline: DealStage[] = ['proposal_shown', 'customer_checkout', 'customer_walkthrough']
              const currentIdx = pipeline.findIndex(s => STAGE_TO_STEP[s] === currentStep)
              const nextIdx = currentIdx < 0 ? 0 : currentIdx + 1
              if (nextIdx >= pipeline.length) {
                toast('Already at final stage', 'info')
                return
              }
              const nextStage = pipeline[nextIdx]
              // Mark the optimistic stage BEFORE awaiting so a realtime echo
              // that lands mid-flight can't regress it (see localStageRef).
              localStageRef.current = { stage: nextStage, at: Date.now() }
              patchDeal(prev => prev ? { ...prev, stage: nextStage } : prev)
              try {
                await updateStage.mutateAsync({ id: deal.id, stage: nextStage })
                toast(`Advanced to ${nextStage.replace(/_/g, ' ')}`, 'success')
              } catch (err) {
                const msg = err instanceof Error ? err.message : String(err)
                console.error('Stage advance failed:', err)
                // Roll back the optimistic patch so the UI matches reality.
                localStageRef.current = null
                patchDeal(prev => prev ? { ...prev, stage: deal.stage } : prev)
                // Most common silent-fail causes: stale Supabase JWT (RLS denies
                // auth.role() = 'authenticated'), or the new stage value isn't
                // in canada_leads_stage_check. Surface to the rep so they can
                // refresh / re-login instead of clicking a dead button.
                toast(`Couldn't advance: ${msg}. Try refreshing the page.`, 'error')
              }
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-pm-accent/30 text-pm-accent text-sm font-medium rounded-lg hover:bg-pm-accent/10 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {updateStage.isPending
              ? <><Loader2 size={16} className="animate-spin" /> Advancing…</>
              : <><ChevronRight size={16} /> Advance to Next Stage</>}
          </button>
        </div>
      )}

      {/* Create Customer Account Login (visible at step 3+) */}
      {currentStep >= 3 && (
        <div className="bg-pm-canada-surface border border-pm-accent/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-pm-accent" />
            <h2 className="text-sm font-semibold text-pm-accent">Create Customer Account Login</h2>
          </div>
          <p className="text-xs text-pm-canada-text-muted">
            Generate a login for {deal.contact_name} to access the Meridian customer portal. They'll be guided through an onboarding walkthrough to set up their account, configure cameras, and explore their dashboard.
          </p>

          {customerCredentials ? (
            <div className="space-y-3">
              <div className="p-4 rounded-lg bg-pm-canada-bg border border-pm-canada-border space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-pm-canada-text-muted">Email</span>
                  <span className="text-sm text-white font-mono">{customerCredentials.email}</span>
                </div>
                {customerCredentials.tempPassword && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-pm-canada-text-muted">Temp password</span>
                    <span className="flex items-center gap-2">
                      <span className="text-sm text-white font-mono">{customerCredentials.tempPassword}</span>
                      <button type="button" onClick={() => navigator.clipboard.writeText(customerCredentials.tempPassword || '')}
                        className="text-2xs text-pm-accent hover:underline">Copy</button>
                    </span>
                  </div>
                )}
                <p className="text-2xs text-pm-canada-text-faint mt-1">Share the temp password with the customer (a welcome email is also sent). They&apos;ll be prompted to set their own password on first login.</p>
              </div>
              <button
                onClick={handleEmailCredentials}
                disabled={credentialEmailing || credentialEmailed}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-pm-accent/30 text-pm-accent text-sm font-medium rounded-lg hover:bg-pm-accent/10 disabled:opacity-50 transition-all"
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
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 disabled:opacity-50 transition-all"
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
        <div className="bg-pm-canada-surface border border-pm-accent/20 rounded-xl p-5 space-y-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-pm-accent" />
            <h2 className="text-sm font-semibold text-pm-accent">Active Deal — Customer Onboarding</h2>
          </div>
          <p className="text-xs text-pm-canada-text-muted">
            This deal is active. The customer has been set up and is going through their onboarding walkthrough.
          </p>
        </div>
      )}

      {/* Mark as Lost */}
      {deal.stage !== 'customer_walkthrough' && deal.stage !== 'closed_won' && deal.stage !== 'closed_lost' && (
        <button
          onClick={async () => {
            try {
              await updateStage.mutateAsync({ id: deal.id, stage: 'closed_lost' })
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

      {/* Delete Confirmation Modal */}
      {showDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-pm-canada-surface border border-pm-canada-border rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-white">Delete lead?</h3>
              <button onClick={() => setShowDelete(false)} className="p-1.5 rounded-lg hover:bg-pm-canada-border transition-colors">
                <X size={18} className="text-pm-canada-text-muted" />
              </button>
            </div>
            <p className="text-sm text-pm-canada-text-muted mb-5">
              This permanently removes &ldquo;{deal.business_name}&rdquo; and can&rsquo;t be undone. Use &ldquo;Mark as Lost&rdquo; instead if you only want to close the deal.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDelete(false)}
                className="px-4 py-2 text-sm text-pm-canada-text-muted hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={deleteLead.isPending}
                onClick={async () => {
                  try {
                    await deleteLead.mutateAsync(deal.id)
                    toast('Lead deleted', 'success')
                    navigate('/canada/portal/leads')
                  } catch (err) {
                    toast(err instanceof Error ? err.message : 'Failed to delete lead', 'error')
                  }
                }}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/90 text-white text-sm font-semibold rounded-lg hover:bg-red-500 transition-all disabled:opacity-50"
              >
                {deleteLead.isPending && <Loader2 size={14} className="animate-spin" />}
                {deleteLead.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── LeadDeckCard ─────────────────────────────────────────────────────────
 * Industry-specific proposal-deck card.
 *  - If deal.vertical resolves to a known CAD deck → show deck title/blurb + share buttons.
 *  - If unknown/missing → show a quick-tag chip row with the most common verticals.
 * ──────────────────────────────────────────────────────────────────────── */
interface LeadDeckCardProps {
  deal: Deal
  rep: { name?: string | null; email?: string | null; phone?: string | null } | null
  monthly: number
  setup: number
  copied: boolean
  tagging: boolean
  onCopy: (url: string) => void | Promise<void>
  onTagVertical: (slug: string) => void | Promise<void>
}

function LeadDeckCard({ deal, rep, monthly, setup, copied, tagging, onCopy, onTagVertical }: LeadDeckCardProps) {
  const deck = useMemo(() => findVerticalByValue(deal.vertical), [deal.vertical])
  const personalizedUrl = useMemo(
    () => (deck ? buildPersonalizedDeckUrl(deck.slug, rep, deal.business_name, { monthly, setup, currency: 'CAD' }) : ''),
    [deck, rep, deal.business_name, monthly, setup],
  )

  // Quick-tag chip selection — 6 most common CAD verticals for fast tagging.
  const quickTagSlugs = ['ca-qsr', 'ca-coffee', 'ca-bar', 'ca-salon', 'ca-dental', 'ca-liquor']
  const quickTags = useMemo(
    () => quickTagSlugs.map(s => CAD_VERTICALS.find(v => v.slug === s)).filter(Boolean) as typeof CAD_VERTICALS,
    [],
  )

  if (!deck) {
    return (
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Tag size={14} className="text-pm-amber-gold" />
          <h2 className="text-sm font-semibold text-white">Tag this lead with a business type</h2>
        </div>
        <p className="text-xs text-pm-canada-text-muted">
          Pick the industry to auto-generate the matching personalized proposal deck for {deal.business_name}.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {quickTags.map(v => (
            <button
              key={v.slug}
              disabled={tagging}
              onClick={() => onTagVertical(v.slug)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-pm-canada-border bg-pm-canada-bg text-2xs text-pm-muted hover:border-pm-accent/40 hover:text-white disabled:opacity-50 transition-colors"
            >
              {tagging ? <Loader2 size={10} className="animate-spin" /> : null}
              {v.title}
            </button>
          ))}
        </div>
        <p className="text-2xs text-pm-canada-text-faint">
          Looking for something else? Edit the lead or visit the Proposals page for all 43 verticals.
        </p>
      </div>
    )
  }

  // Once a vertical is tagged, the proposal entry point lives in the Step 1
  // "Proposal" section below (price slider + Generate/View/Email), so the
  // redundant top-of-page "Open personalized deck" card is intentionally not
  // rendered. `personalizedUrl`/`onCopy`/`copied` remain wired for the
  // untagged tagging flow and any future reuse.
  void personalizedUrl
  return null
}
