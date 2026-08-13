import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Check, Sparkles, Wifi, X, Upload, Trash2, Clock,
  FileText, Mail, CheckCircle2, Loader2, Download, ChevronRight, Pencil, Save,
  AlertTriangle, CreditCard, RefreshCw, Send, Eye, ExternalLink, Copy, Tag,
} from 'lucide-react'
import {
  findUsVerticalByValue,
  buildPersonalizedUsDeckUrl,
  US_VERTICALS,
} from '@/data/usVerticals'
import QRCode from 'qrcode'
import POSSystemPicker from '@/components/POSSystemPicker'
import { type Deal, type DealStage } from '@/lib/canada-sales-demo-data'
import { usLeadsService } from '@/lib/us-leads-service'
import { getPlan, closestMonthlyPlan, PLAN_TIERS, ZERO_PER_ORDER_CARDS, REP_PRICE_HEADROOM, WEBSITE_MODULES, websiteMonthlyFree, CUSTOM_CRM_SERVICE, parseSetupServiceAmount, AD_SPOT_SERVICE, AD_SPOT_PLACEMENTS, AD_SPOT_AUDIO, VOICE_INCLUDED_MINUTES, VOICE_OVERAGE_PER_MIN, VOICE_MAX_CALL_MINUTES, type PlanTier } from '@/lib/proposal-plans'

// Website Buildout is sold as modular line items (WEBSITE_MODULES) — the
// one-time modules sum into the setup fee. Creating the customer fires the
// 48-hour build contest on Meridian Foundry.
const FOUNDRY_ORDER_URL = 'https://foundry.meridian.tips/agency/api/sites/order'
const FOUNDRY_JOB_BASE = 'https://foundry.meridian.tips/agency/jobs'
import { getPosSystem, validateCredentials, serializeCredentials } from '@/lib/pos-credentials'
import { generateProposalPdf } from '@/lib/generate-proposal-pdf'
import { generateInvoicePdf, generateInvoiceNumber, generateInvoiceUrl, type InvoiceInput } from '@/lib/generate-invoice-pdf-us'
import { generateSlaDocument, type SlaInput } from '@/lib/generate-sla-pdf'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase, getAuthHeaders } from '@/lib/supabase'
import { useToast } from '@/components/Toast'
import { notifyStageChange } from '@/lib/notifications'
import { openBlobInNewTab } from '@/lib/blob-url'

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

interface ProjectFile { id: string; name: string; description: string; tag: string }

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
                    ? 'bg-[#17C5B0] text-white'
                    : step.num === currentStep
                    ? 'border-2 border-[#17C5B0] text-[#17C5B0] bg-transparent'
                    : 'bg-[#1F1F23] text-[#A1A1A8]'
                }`}
              >
                {step.num < currentStep ? <Check size={18} /> : step.num}
              </div>
              <span className={`text-[10px] mt-1.5 whitespace-nowrap ${
                step.num <= currentStep ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'
              }`}>
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {idx < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 mt-[-18px] ${
                step.num < currentStep ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]'
              }`} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function USPortalLeadDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { rep } = useSalesAuth()
  const { toast } = useToast()
  const [deal, setDeal] = useState<Deal | null>(null)
  const dealRef = useRef<Deal | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({ business_name: '', contact_name: '', contact_email: '', contact_phone: '', notes: '' })
  const [editSaving, setEditSaving] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // Step 2 state — price = tier base + rep adjustment (0..REP_PRICE_HEADROOM)
  const [planId, setPlanId] = useState<PlanTier['id']>('premium')
  const [priceBump, setPriceBump] = useState(0)
  // Per-order fee slider (cents): defaults to the tier's standard rate and
  // slides DOWN only, to the tier redline (orderFeeFloor). Backend re-clamps.
  const [orderFeeCents, setOrderFeeCents] = useState(() => Math.round(getPlan('premium').orderFee * 100))
  // Pricing model (mirrors CreateCustomerPage): per_order is today's model;
  // zero_per_order is the minutes plan — $0/order, monthly minute bucket.
  // The monthly stays retail; only the per-order fee changes. Set at close, fixed after.
  const [pricingModel, setPricingModel] = useState<'per_order' | 'zero_per_order'>('per_order')
  const selectedPlan = getPlan(planId)
  const zpoCard = ZERO_PER_ORDER_CARDS[selectedPlan.id]
  const zeroPerOrder = pricingModel === 'zero_per_order' && !!zpoCard
  const monthlyPrice = selectedPlan.price + priceBump
  const orderFeeFloorCents = Math.round(selectedPlan.orderFeeFloor * 100)
  const orderFeeMaxCents = Math.round(selectedPlan.orderFee * 100)
  // Setup Services (Aidan 08-06): the manual setup fee is retired — the fee
  // is the sum of toggled services (Website Buildout today, more soon).
  const [website, setWebsite] = useState(false)
  const [websiteCurrentUrl, setWebsiteCurrentUrl] = useState('')
  const [websiteGoals, setWebsiteGoals] = useState('')
  const [websitePages, setWebsitePages] = useState('')
  const [websiteBrand, setWebsiteBrand] = useState('')
  const [websiteContent, setWebsiteContent] = useState<'ready' | 'none'>('none')
  const [websiteContestUrl, setWebsiteContestUrl] = useState('')
  // Buildout modules — all on by default (the full package); unchecking with
  // the owner makes the total visibly chosen, not quoted.
  const [websiteModules, setWebsiteModules] = useState<string[]>(WEBSITE_MODULES.map(m => m.id))
  function toggleModule(id: string) {
    const m = WEBSITE_MODULES.find(x => x.id === id)
    if (!m || m.core) return
    setWebsiteModules(cur => (cur.includes(id) ? cur.filter(x => x !== id) : [...cur, id]))
  }
  const websiteOneTime = WEBSITE_MODULES.filter(m => !m.monthly && websiteModules.includes(m.id)).reduce((t, m) => t + m.price, 0)
  const websiteMonthly = WEBSITE_MODULES.filter(m => m.monthly && websiteModules.includes(m.id)).reduce((t, m) => t + m.price, 0)
  // Maintenance + hosting come free with Premium and up — only Standard
  // pays the buildout's monthly line items.
  const monthlyFree = websiteMonthlyFree(selectedPlan.id)
  const websiteMonthlyDue = monthlyFree ? 0 : websiteMonthly
  // Custom CRM build — a Setup Service like the buildout, but rep-priced:
  // the build is scoped per deal, so the rep enters the amount they quoted.
  const [crm, setCrm] = useState(false)
  const [crmAmount, setCrmAmount] = useState('')
  const crmOneTime = crm ? parseSetupServiceAmount(crmAmount) : 0
  // 30-Second AI Advertisement — a fixed-price Setup Service. The brief the
  // rep takes here is what the generation pipeline boards the spot from.
  const [adSpot, setAdSpot] = useState(false)
  const [adGoal, setAdGoal] = useState('')
  const [adHighlights, setAdHighlights] = useState('')
  const [adBrand, setAdBrand] = useState('')
  const [adPlacement, setAdPlacement] = useState(AD_SPOT_PLACEMENTS[0].id)
  const [adAudio, setAdAudio] = useState(AD_SPOT_AUDIO[0].id)
  const [adSpotOrderId, setAdSpotOrderId] = useState('')
  const adSpotOneTime = adSpot ? AD_SPOT_SERVICE.price : 0
  const setupFee = String((website ? websiteOneTime : 0) + crmOneTime + adSpotOneTime)
  const [firstMonthFree, setFirstMonthFree] = useState(false)

  // Seed tier + adjustment from a lead's stored monthly value (legacy values
  // snap to the closest tier; any remainder above base becomes the adjustment).
  const seedPricing = useCallback((stored?: number | null) => {
    const plan = closestMonthlyPlan(stored || 350)
    setPlanId(plan.id)
    const bump = stored ? Math.round(stored - plan.price) : 0
    setPriceBump(Math.min(REP_PRICE_HEADROOM, Math.max(0, bump)))
  }, [])

  // Proposal state
  const [proposalBlob, setProposalBlob] = useState<Blob | null>(null)
  const [proposalGenerating, setProposalGenerating] = useState(false)
  const [proposalEmailing, setProposalEmailing] = useState(false)
  const [proposalSent, setProposalSent] = useState(false)

  // Industry proposal-deck state
  const [deckLinkCopied, setDeckLinkCopied] = useState(false)
  const [deckTagging, setDeckTagging] = useState(false)

  // Invoice state
  const [invoiceBlob, setInvoiceBlob] = useState<Blob | null>(null)
  const [invoiceGenerating, setInvoiceGenerating] = useState(false)
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [invoiceEmailing, setInvoiceEmailing] = useState(false)
  const [invoiceEmailed, setInvoiceEmailed] = useState(false)
  // Stripe subscribe-link: URL + client-side QR for the customer to scan at checkout
  const [checkoutUrl, setCheckoutUrl] = useState('')
  // Ref mirror of checkoutUrl: handleEmailInvoice can run in the same tick the
  // link resolves, before the state update flushes — so the emailed "View & Pay"
  // link reads from the ref, not stale state.
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

  // Step 4 state
  const [selectedPOS, setSelectedPOS] = useState<string | null>(null)
  const [posConnecting, setPosConnecting] = useState(false)
  const [posConnected, setPosConnected] = useState(false)
  const [posError, setPosError] = useState<string | null>(null)

  const [posVerifying, setPosVerifying] = useState(false)
  const [posPending, setPosPending] = useState<string | null>(null)

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
      const authHeaders = await getAuthHeaders()
      const res = await fetch(`${API_BASE}/api/onboarding/connect-pos`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          deal_id: deal?.id,
          provider,
          credentials: creds,
          business_name: deal?.business_name,
          table: 'us_leads',
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
        headers: authHeaders,
        body: JSON.stringify({ deal_id: deal?.id, provider, table: 'us_leads' }),
      }).catch(() => null)

      if (verifyRes && verifyRes.ok) {
        setPosConnected(true)
        setPosVerifying(false)
        if (deal) {
          await usLeadsService.updateStage(deal.id, 'pos_connected')
          setDeal(prev => prev ? { ...prev, stage: 'pos_connected' } : prev)
        }
      } else {
        setPosVerifying(false)
        setPosPending(`${system.name} credentials saved — waiting for data verification. The swarm will confirm data is flowing and notify you.`)
        if (deal && deal.stage !== 'pos_connected' && deal.stage !== 'customer_walkthrough') {
          await usLeadsService.updateStage(deal.id, 'customer_checkout')
          setDeal(prev => prev ? { ...prev, stage: 'customer_checkout' } : prev)
        }
      }
    } catch {
      setPosError(`Could not reach the server. Check your internet connection and try again.`)
      setPosConnecting(false)
    }
  }

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
    if (website && !websiteGoals.trim()) {
      setCustomerError('Website Buildout is on but the goals are empty — give the builders something to work from.')
      creatingRef.current = false
      setCustomerCreating(false)
      return
    }
    if (crm && crmOneTime <= 0) {
      setCustomerError(`${CUSTOM_CRM_SERVICE.label} is on but has no price — enter the amount you quoted.`)
      creatingRef.current = false
      setCustomerCreating(false)
      return
    }
    if (adSpot && !adGoal.trim()) {
      setCustomerError(`${AD_SPOT_SERVICE.label} is on but has no brief — say what the spot has to sell.`)
      creatingRef.current = false
      setCustomerCreating(false)
      return
    }

    try {
      if (!supabase) throw new Error('Database not connected')

      const API_BASE = import.meta.env.VITE_API_URL || ''
      const authHeaders = await getAuthHeaders()
      const res = await fetch(`${API_BASE}/api/us/create-customer`, {
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
          portal: 'us',
          plan_id: planId,
          // The pricing model the rep locked at close; backend forces the
          // per-order fee to 0 on zero_per_order and fills the minute bucket.
          pricing_model: pricingModel,
          // Rep-negotiated per-order fee (cents, USD). Only meaningful on
          // phone-agent tiers billing per order; the backend clamps to the tier redline.
          ...(selectedPlan.phoneAgent && !zeroPerOrder ? { order_fee_cents: Math.min(Math.max(orderFeeCents, orderFeeFloorCents), orderFeeMaxCents) } : {}),
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Failed to create customer account')
      }

      // The backend returns a rep-shareable temp password (must_reset_password
      // forces the customer to set their own on first login). The old
      // resetPasswordForEmail flow is gone: this Supabase project has no custom
      // SMTP, so those "secure setup emails" never actually delivered.
      const data = await res.json().catch(() => ({}))

      setCustomerCredentials({ email, tempPassword: data.temp_password })

      // Website Buildout sold → fire the 48-hour build contest on Meridian
      // Foundry (best-effort: a Foundry hiccup never blocks the account).
      if (website) {
        try {
          const rawUrl = websiteCurrentUrl.trim()
          const sprintRes = await fetch(FOUNDRY_ORDER_URL, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({
              company: deal.business_name,
              contactName: deal.contact_name,
              email,
              currentUrl: rawUrl ? (/^https?:\/\//i.test(rawUrl) ? rawUrl : `https://${rawUrl}`) : '',
              goals: websiteGoals.trim(),
              pages: websitePages.split(',').map(x => x.trim()).filter(Boolean).slice(0, 12),
              brandNotes: [websiteBrand.trim(), `Modules sold: ${WEBSITE_MODULES.filter(m => websiteModules.includes(m.id) || (m.monthly && monthlyFree)).map(m => m.label).join(', ')}.`, `Sold with Meridian ${selectedPlan.label} (US) by rep ${rep?.name || 'unknown'}.`].filter(Boolean).join(' '),
              contentReady: websiteContent,
              repEmail: '',
            }),
          })
          const sprintData = await sprintRes.json().catch(() => null)
          if ((sprintRes.ok || sprintRes.status === 409) && sprintData?.jobId) {
            setWebsiteContestUrl(`${FOUNDRY_JOB_BASE}/${sprintData.jobId}`)
          } else {
            setCustomerError('Account created, but the website build contest did not launch — start it manually at foundry.meridian.tips/agency/website.')
          }
        } catch {
          setCustomerError('Account created, but the website build contest did not launch — start it manually at foundry.meridian.tips/agency/website.')
        }
      }
      // 30-second spot sold → hand the brief to the generation pipeline
      // (best-effort, same as the website sprint above).
      if (adSpot) {
        try {
          const adRes = await fetch(`${API_BASE}/api/content/ad-spot/order`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify({
              market: 'us',
              leadId: deal.id,
              repId: rep?.rep_id || null,
              repName: rep?.name || null,
              businessName: deal.business_name,
              businessType: deal.vertical || 'retail',
              contactEmail: email,
              priceCents: AD_SPOT_SERVICE.price * 100,
              goal: adGoal.trim(),
              highlights: adHighlights.trim(),
              brandNotes: adBrand.trim(),
              placement: adPlacement,
              audio: adAudio,
            }),
          })
          const adData = await adRes.json().catch(() => null)
          if (adRes.ok && adData?.orderId) {
            setAdSpotOrderId(adData.orderId)
          } else {
            setCustomerError('Account created, but the 30-second spot did not queue — flag it so the spot gets boarded manually.')
          }
        } catch {
          setCustomerError('Account created, but the 30-second spot did not queue — flag it so the spot gets boarded manually.')
        }
      }
      // The fee seed is best-effort server-side — if it failed, creation still
      // succeeded but the merchant is on the tier default fee. Tell the rep.
      if (selectedPlan.phoneAgent && data.fee_seeded === false) {
        setCustomerError('Account created, but the negotiated per-order fee did NOT save — the merchant is on the plan default. Set it manually or re-try before the walkthrough.')
      }
      await usLeadsService.updateStage(deal.id, 'customer_walkthrough')
      setDeal(prev => prev ? { ...prev, stage: 'customer_walkthrough' } : prev)
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
          portal: 'us',
          extra: {
            business_name: deal.business_name,
            email: customerCredentials.email,
            login_url: `${window.location.origin}/customer/login`,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setCredentialEmailed(true)
      toast('Welcome email sent to ' + deal.contact_email, 'success')
    } catch {
      toast('Welcome email failed — ask the customer to check the setup link Supabase sent', 'error')
      setCustomerError('Failed to send welcome email. The customer should still receive the password-setup link from Supabase.')
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
      const res = await fetch(`${API_BASE}/api/billing/notify-payment-failed`, {
        method: 'POST',
        headers: await getAuthHeaders(),
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
        headers: await getAuthHeaders(),
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

      const planName = closestMonthlyPlan(monthlyPrice).label
      const priceCents = Math.round(monthlyPrice * 100)
      const setupFeeCents = Math.round((Number(setupFee) || 0) * 100)

      let resolvedCheckoutUrl = generateInvoiceUrl(invNum)

      const API_BASE = import.meta.env.VITE_API_URL || ''
      try {
        const checkoutRes = await fetch(`${API_BASE}/api/stripe/subscribe-link`, {
          method: 'POST',
          headers: await getAuthHeaders(),
          body: JSON.stringify({
            org_id: deal.id,
            lead_id: deal.id,
            monthly_amount_cents: priceCents,
            currency: 'USD',
            business_name: deal.business_name,
            setup_fee_cents: setupFeeCents,
            first_month_free: firstMonthFree,
          }),
        })
        if (checkoutRes.ok) {
          const data = await checkoutRes.json()
          if (data.url) resolvedCheckoutUrl = data.url
        }
      } catch {
        // Stripe subscribe-link unavailable — fall back to local invoice URL
      }

      // Surface the subscription link + on-screen QR so the customer can scan
      // to subscribe right at the checkout step (distinct from per-order phone fee).
      setCheckoutUrl(resolvedCheckoutUrl)
      checkoutUrlRef.current = resolvedCheckoutUrl
      try {
        const qr = await QRCode.toDataURL(resolvedCheckoutUrl, {
          width: 240,
          margin: 1,
          color: { dark: '#17C5B0', light: '#0A0A0B' },
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
        billingDate: now.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
        dueDate: dueDate.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
        repName: rep.name,
        repEmail: rep.email,
        recurring: true,
        invoiceUrl: resolvedCheckoutUrl,
      }

      const blob = await generateInvoicePdf(input)
      setInvoiceBlob(blob)

      if (deal.stage === 'proposal_shown' || deal.stage === 'appointment_set') {
        await usLeadsService.updateStage(deal.id, 'customer_checkout')
        setDeal(prev => prev ? { ...prev, stage: 'customer_checkout' } : prev)
      }
    } catch (err) {
      console.error('[Invoice] Generation failed:', err)
    } finally {
      setInvoiceGenerating(false)
    }
  }

  function handleDownloadInvoice() {
    if (!invoiceBlob) return
    openBlobInNewTab(invoiceBlob)
  }

  async function handleEmailInvoice() {
    if (!deal || invoiceEmailing) return
    // Set the loading flag BEFORE the await so a rapid double-click can't
    // race past us during invoice generation and queue up two send calls
    // (which Square would treat as two separate invoices).
    setInvoiceEmailing(true)
    if (!invoiceBlob) await handleGenerateInvoice()
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/email/send`, {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          template: 'invoice_sent',
          to: deal.contact_email,
          first_name: deal.contact_name.split(' ')[0],
          portal: 'us',
          extra: {
            business_name: deal.business_name,
            invoice_number: invoiceNumber,
            amount: `$${monthlyPrice.toLocaleString()}`,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
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
        country: 'US',
        clientCompanyName: deal.business_name,
        region: deal.province || 'New York',
        posSystem: selectedPOS || 'Unknown',
        repName: rep.name || 'Sales Representative',
        planName: selectedPlan.label,
        monthlyPriceCents: monthlyPrice * 100,
        setupFeeCents: (Number(setupFee) || 0) * 100,
        firstMonthFree,
        ...(selectedPlan.phoneAgent ? {
          phoneAgent: {
            orderFeeCents: Math.round(selectedPlan.orderFee * 100),
            includedMinutes: VOICE_INCLUDED_MINUTES,
            overageCentsPerMin: Math.round(VOICE_OVERAGE_PER_MIN * 100),
            maxCallMinutes: VOICE_MAX_CALL_MINUTES,
          },
        } : {}),
        ...(website ? { websiteMonthlyCents: websiteMonthlyDue * 100, websiteMonthlyIncluded: monthlyFree } : {}),
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
    if (!slaBlob) return
    openBlobInNewTab(slaBlob)
  }

  async function handleSignSla() {
    if (!slaSignature.trim() || !deal || !rep) return
    setSlaSigning(true)
    try {
      const slaInput: SlaInput = {
        country: 'US',
        clientCompanyName: deal.business_name,
        region: deal.province || 'New York',
        posSystem: selectedPOS || 'Unknown',
        repName: rep.name || 'Sales Representative',
        planName: selectedPlan.label,
        monthlyPriceCents: monthlyPrice * 100,
        setupFeeCents: (Number(setupFee) || 0) * 100,
        firstMonthFree,
        ...(selectedPlan.phoneAgent ? {
          phoneAgent: {
            orderFeeCents: Math.round(selectedPlan.orderFee * 100),
            includedMinutes: VOICE_INCLUDED_MINUTES,
            overageCentsPerMin: Math.round(VOICE_OVERAGE_PER_MIN * 100),
            maxCallMinutes: VOICE_MAX_CALL_MINUTES,
          },
        } : {}),
        ...(website ? { websiteMonthlyCents: websiteMonthlyDue * 100, websiteMonthlyIncluded: monthlyFree } : {}),
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
          headers: await getAuthHeaders(),
          body: JSON.stringify({
            to: deal.contact_email,
            template: 'sla_signed',
            portal: 'us',
            extra: {
              business_name: deal.business_name,
              rep_name: rep.name || '',
              rep_email: rep.email || '',
              signed_by: slaSignature,
              signed_date: new Date().toLocaleDateString('en-US'),
              provider_signatory: `${rep.name || 'Meridian Sales'}, Account Representative`,
              monthly_price: `$${monthlyPrice.toLocaleString()}/mo`,
              setup_fee: (Number(setupFee) || 0) > 0 ? `$${(Number(setupFee) || 0).toLocaleString()}` : '',
              first_month_free: firstMonthFree,
              due_today: `$${((firstMonthFree ? 0 : monthlyPrice) + (Number(setupFee) || 0)).toLocaleString()}`,
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
          portal: 'us',
          extra: {
            business_name: deal.business_name,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
            signed_by: slaSignature,
            signed_date: new Date().toLocaleDateString('en-US'),
            provider_signatory: `${rep?.name || 'Meridian Sales'}, Account Representative`,
            monthly_price: `$${monthlyPrice.toLocaleString()}/mo`,
            setup_fee: (Number(setupFee) || 0) > 0 ? `$${(Number(setupFee) || 0).toLocaleString()}` : '',
            first_month_free: firstMonthFree,
            due_today: `$${((firstMonthFree ? 0 : monthlyPrice) + (Number(setupFee) || 0)).toLocaleString()}`,
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setSlaEmailed(true)
      toast('SLA emailed to ' + deal.contact_email, 'success')
    } catch (err) {
      console.error('[SLA] Email failed:', err)
      toast('SLA email failed — try again or share the PDF', 'error')
      setPosError('SLA email failed to send. Try again or download and share the PDF.')
    } finally {
      setSlaEmailing(false)
    }
  }

  const buildProposalInput = useCallback(() => {
    if (!deal || !rep) return null
    const plan = selectedPlan
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
  }, [deal, rep, selectedPlan, monthlyPrice, setupFee, firstMonthFree])

  // Opens the lead's industry-specific proposal deck (the live hosted deck on
  // meridian-decks.vercel.app, personalized with rep + business name) — the
  // current proposal format. Falls back to prompting the rep to tag the
  // business type, since the deck is selected from deal.vertical.
  function proposalDeckUrl(): string | null {
    if (!deal || !rep) return null
    const deck = findUsVerticalByValue(deal.vertical)
    if (!deck) return null
    return buildPersonalizedUsDeckUrl(deck.slug, rep, deal.business_name, {
      monthly: monthlyPrice,
      setup: Number(setupFee) || 0,
      currency: 'USD',
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
        await usLeadsService.updateStage(deal.id, 'proposal_shown')
        setDeal(prev => prev ? { ...prev, stage: 'proposal_shown' } : prev)
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

  // PDF fallback — generates the slide-deck PDF locally for reps who need a
  // file to share offline. The primary proposal path is the live deck above.
  async function handleDownloadProposal() {
    const input = buildProposalInput()
    if (!input) return
    setProposalGenerating(true)
    try {
      const blob = await generateProposalPdf(input)
      setProposalBlob(blob)
      openBlobInNewTab(blob)
    } catch (err) {
      console.error('[Proposal] Generation failed:', err)
    } finally {
      setProposalGenerating(false)
    }
  }

  async function handleEmailProposal() {
    if (!deal || proposalEmailing) return
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
          portal: 'us',
          extra: {
            business_name: deal.business_name,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
            plan_name: closestMonthlyPlan(monthlyPrice).label,
            monthly_price: `$${monthlyPrice.toLocaleString()}`,
            setup_fee: (Number(setupFee) || 0) > 0 ? `$${(Number(setupFee) || 0).toLocaleString()}` : '',
            due_today: `$${((firstMonthFree ? 0 : monthlyPrice) + (Number(setupFee) || 0)).toLocaleString()}`,
            proposal_url: proposalDeckUrl() || '',
          },
        }),
      })
      if (!res.ok) throw new Error('Email delivery failed')
      setProposalSent(true)
      toast('Proposal emailed to ' + deal.contact_email, 'success')
      if (deal.stage === 'appointment_set' || deal.stage === 'proposal_shown' || deal.stage === 'contacted' || deal.stage === 'demo_scheduled') {
        await usLeadsService.updateStage(deal.id, 'proposal_shown')
        setDeal(prev => prev ? { ...prev, stage: 'proposal_shown' } : prev)
      }
    } catch (err) {
      console.error('[Proposal] Email failed:', err)
      toast('Proposal email failed — try again or share the PDF', 'error')
      setPosError('Proposal email failed to send. Try again or download and share the PDF.')
    } finally {
      setProposalEmailing(false)
    }
  }

  // Files state
  const [files, setFiles] = useState<ProjectFile[]>([])

  useEffect(() => { dealRef.current = deal }, [deal])

  useEffect(() => {
    if (!id) { setLoading(false); return }
    usLeadsService.getById(id).then(found => {
      setDeal(found)
      if (found) {
        seedPricing(found.monthly_value)
      }
    }).catch(() => {
      setDeal(null)
    }).finally(() => setLoading(false))
    const channel = usLeadsService.subscribe(undefined, deals => {
      const updated = deals.find(d => d.id === id)
      if (updated) {
        const current = dealRef.current
        if (current && updated.stage !== current.stage) {
          notifyStageChange(updated.business_name, updated.stage)
          toast(`${updated.business_name} moved to ${updated.stage.replace(/_/g, ' ')}`, 'info')
        }
        setDeal(updated)
        seedPricing(updated.monthly_value)
      }
    })
    return () => { usLeadsService.unsubscribe(channel) }
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#17C5B0] font-bold text-sm">S</span>
        </div>
      </div>
    )
  }

  if (!deal) {
    return (
      <div className="space-y-4">
        <Link to="/us/portal/leads" className="inline-flex items-center gap-1.5 text-sm text-[#A1A1A8] hover:text-white transition-colors">
          <ArrowLeft size={16} /> Leads
        </Link>
        <div className="text-center py-16 text-[#A1A1A8]">Lead not found.</div>
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
      setFiles(prev => [...prev, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, name: file.name, description: `Uploaded ${ext} file`, tag: ext }])
    }
    input.click()
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-white placeholder-[#A1A1A8] focus:outline-none focus:border-[#17C5B0]/50 focus:ring-1 focus:ring-[#17C5B0]/20 transition-colors'

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Back link */}
      <Link to="/us/portal/leads" className="inline-flex items-center gap-1.5 text-sm text-[#A1A1A8] hover:text-white transition-colors">
        <ArrowLeft size={16} /> Leads
      </Link>

      {/* Header */}
      {editing ? (
        <div className="bg-[#111113] border border-[#17C5B0]/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#17C5B0]">Edit Lead</h2>
            <button onClick={() => setEditing(false)} className="text-xs text-[#A1A1A8] hover:text-white">Cancel</button>
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
                await usLeadsService.update(deal.id, editForm)
                setDeal(prev => prev ? { ...prev, ...editForm } : prev)
                setEditing(false)
              } catch (err) {
                setPosError(err instanceof Error ? `Save failed: ${err.message}` : 'Failed to save changes. Please try again.')
              } finally {
                setEditSaving(false)
              }
            }}
            className="flex items-center gap-2 px-4 py-2 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-all"
          >
            {editSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save Changes
          </button>
        </div>
      ) : (
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{deal.business_name}</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              {deal.contact_name} &middot; <span className="text-[#f0b429] font-semibold">${deal.monthly_value.toLocaleString()}/mo</span> &middot; {deal.contact_email}
            </p>
            {/* Fee parity: read-only summary of the LOCKED fee terms — the deal's
                contract of record, written server-side at customer creation and
                provisioned straight into live billing (no manual re-entry). */}
            {deal.fee_terms_locked_at && (
              <p className="text-xs mt-1.5 flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold">
                  <CheckCircle2 size={11} /> Fees locked
                </span>
                <span className="text-[#A1A1A8]">
                  {(deal.plan_tier || 'premium').replace(/^./, c => c.toUpperCase())}
                  {deal.monthly_fee_cents != null && <> &middot; ${(deal.monthly_fee_cents / 100).toLocaleString()}/mo</>}
                  {deal.order_fee_cents != null && deal.order_fee_cents > 0 && <> &middot; ${(deal.order_fee_cents / 100).toFixed(2)}/order</>}
                  {deal.call_overage_cents_per_min != null && <> &middot; ${(deal.call_overage_cents_per_min / 100).toFixed(2)}/min after {deal.included_call_min ?? 3} min</>}
                </span>
              </p>
            )}
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
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:text-white hover:border-[#2a3430] transition-colors"
            >
              <Pencil size={12} /> Edit
            </button>
            {/* Delete (hard delete — distinct from the soft "Mark as Lost" stage) */}
            <button
              onClick={() => setShowDelete(true)}
              data-testid="delete-lead-detail"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:text-red-400 hover:border-red-500/30 transition-colors"
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
            await usLeadsService.update(deal.id, { vertical: slug })
            setDeal(prev => prev ? { ...prev, vertical: slug } : prev)
          } catch (err) {
            toast(err instanceof Error ? `Could not tag lead: ${err.message}` : 'Could not tag lead.', 'error')
          } finally {
            setDeckTagging(false)
          }
        }}
      />

      {/* Stepper */}
      <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-4">
        <HorizontalStepper currentStep={currentStep} />
      </div>

      {/* Step 1 - Proposal (always visible) */}
      <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Proposal</h2>

        {/* Plan tier + price adjustment */}
        <div>
          <label className="text-xs text-[#A1A1A8] block mb-1.5">Plan (USD)</label>
          <div className="grid grid-cols-3 gap-2 mb-3">
            {PLAN_TIERS.map(plan => (
              <button key={plan.id} onClick={() => { setPlanId(plan.id); setPriceBump(0); setOrderFeeCents(Math.round(plan.orderFee * 100)); if (!ZERO_PER_ORDER_CARDS[plan.id]) setPricingModel('per_order') }}
                className={`p-2.5 rounded-lg border text-left transition-colors ${
                  planId === plan.id
                    ? 'border-[#17C5B0]/50 bg-[#17C5B0]/5'
                    : 'border-[#1F1F23] hover:border-[#4a5550] bg-[#0A0A0B]'
                }`}>
                <p className="text-xs font-semibold text-white">{plan.label}</p>
                <p className="text-sm font-bold text-[#f0b429]">${plan.price}/mo</p>
                <p className="text-[10px] text-[#A1A1A8] mt-0.5">
                  {plan.phoneAgent ? `Phone agent · $${plan.orderFee.toFixed(2)}/order` : 'No phone agent'}
                </p>
              </button>
            ))}
          </div>
          <p className="text-[10px] text-[#4a5550] mt-1">Billed monthly in USD. Tier price is fixed — no adjustments, no discounts.</p>

          {/* Pricing Model — only phone-agent tiers with a minutes card offer the
              choice (mirrors CreateCustomerPage; set at close, fixed after). */}
          {selectedPlan.phoneAgent && zpoCard && (
            <div className="mt-4">
              <label className="block text-[10px] font-medium text-[#A1A1A8] mb-1.5">
                Pricing Model <span className="text-[#4a5550]">(how the phone agent bills — set now, fixed after)</span>
              </label>
              <div className="grid gap-2 sm:grid-cols-2">
                <button onClick={() => setPricingModel('per_order')}
                  className={`p-4 rounded-xl border text-left transition-all duration-200 ${
                    !zeroPerOrder ? 'border-[#17C5B0]/50 bg-[#17C5B0]/5' : 'border-[#1F1F23] hover:border-[#4a5550] bg-[#0A0A0B]'
                  }`}>
                  <p className="text-sm font-semibold text-white">Per-order pricing</p>
                  <p className="text-[10px] text-[#A1A1A8] mt-0.5">${monthlyPrice}/mo + ${selectedPlan.orderFee.toFixed(2)} per phone order</p>
                </button>
                <button onClick={() => setPricingModel('zero_per_order')}
                  className={`p-4 rounded-xl border text-left transition-all duration-200 ${
                    zeroPerOrder ? 'border-[#17C5B0]/50 bg-[#17C5B0]/5' : 'border-[#1F1F23] hover:border-[#4a5550] bg-[#0A0A0B]'
                  }`}>
                  <p className="text-sm font-semibold text-white">$0 per order — minutes plan</p>
                  <p className="text-[10px] text-[#A1A1A8] mt-0.5">Same ${monthlyPrice}/mo · {zpoCard.includedMinutes} min included · ${zpoCard.overagePerMin.toFixed(2)}/min after</p>
                  <p className="text-[10px] text-[#f0b429] mt-1.5 flex items-start gap-1.5">
                    <AlertTriangle size={12} className="flex-shrink-0 mt-[1px]" />
                    Lower commission on $0/order deals
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* Per-order fee — fixed per tier (the negotiation slider is retired;
              every deal sells at the tier rate). */}
          {selectedPlan.phoneAgent && !zeroPerOrder && (
            <div className="mt-4">
              <p className="text-xs text-[#A1A1A8]">
                Per-order fee: <span className="font-semibold text-[#f0b429]">${selectedPlan.orderFee.toFixed(2)}/order</span> — fixed for this tier
              </p>
              <p className="text-[10px] text-[#A1A1A8] mt-1.5 px-2.5 py-1.5 rounded-md bg-[#0A0A0B] border border-[#1F1F23]">
                Voice calls: <span className="font-semibold text-[#f0b429]">no per-minute charge</span> — call time is not billed. Calls end automatically at {VOICE_MAX_CALL_MINUTES} minutes. Phone ordering is Canada-first: phone orders are charged in <span className="font-semibold text-[#f0b429]">Canadian dollars (CAD)</span> for now, whichever market the merchant is in.
              </p>
            </div>
          )}

          {selectedPlan.phoneAgent && zeroPerOrder && zpoCard && (
            <div className="mt-4 p-4 rounded-xl border border-[#1F1F23] bg-[#0A0A0B]">
              <p className="text-sm font-semibold text-white">$0 per order — how it bills</p>
              <p className="text-[10px] text-[#A1A1A8] mt-1">
                The monthly stays ${monthlyPrice} — it now covers {zpoCard.includedMinutes} AI-call minutes each month, then ${zpoCard.overagePerMin.toFixed(2)}/min.
                There is no per-order fee. The {VOICE_MAX_CALL_MINUTES}-minute call cap still applies.
              </p>
            </div>
          )}
        </div>

        {/* Setup Services — priced toggles; their sum is the setup fee */}
        <div>
          <label className="text-xs text-[#A1A1A8] block mb-1.5">
            Setup Services <span className="text-[#4a5550]">(one-time — billed together as the setup fee)</span>
          </label>
          <div className="rounded-xl border border-[#1F1F23] bg-[#0A0A0B]">
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-sm font-semibold text-white">Website Buildout</p>
                <p className="text-[10px] text-[#A1A1A8]">Custom site or rebuild, built in 48 hours on the Meridian network</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-[#17C5B0]">
                  ${websiteOneTime}
                  {websiteMonthlyDue > 0 && <span className="text-[#A1A1A8] font-normal"> + ${websiteMonthlyDue}/mo</span>}
                </span>
                <div className={`w-9 h-5 rounded-full transition-colors relative cursor-pointer ${website ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]'}`}
                  onClick={() => setWebsite(!website)}
                >
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${website ? 'translate-x-4' : 'translate-x-0.5'}`} />
                </div>
              </div>
            </div>
            {website && (
              <div className="px-4 pb-4 pt-3 space-y-3 border-t border-[#1F1F23]">
                <div className="space-y-1.5">
                  {WEBSITE_MODULES.map(m => {
                    const included = m.core || (m.monthly && monthlyFree)
                    const on = websiteModules.includes(m.id) || included
                    return (
                      <label key={m.id}
                        className={`flex items-center gap-3 px-3 py-2 rounded-lg border cursor-pointer transition-colors ${
                          on ? 'border-[#17C5B0]/40 bg-[#17C5B0]/5' : 'border-[#1F1F23]'
                        } ${m.core ? 'cursor-default' : ''}`}>
                        <input type="checkbox" checked={on} disabled={included}
                          onChange={() => toggleModule(m.id)}
                          className="accent-[#17C5B0]" />
                        <span className="flex-1">
                          <span className="block text-sm text-white">{m.label}{m.core ? ' (included)' : ''}</span>
                          <span className="block text-[10px] text-[#A1A1A8]">{m.blurb}</span>
                        </span>
                        {m.monthly && monthlyFree ? (
                          <span className="text-[11px] font-semibold text-[#17C5B0]">Included with {selectedPlan.label}</span>
                        ) : (
                          <span className={`text-sm font-semibold ${on ? 'text-[#17C5B0]' : 'text-[#4a5550]'}`}>
                            ${m.price}{m.monthly ? '/mo' : ''}
                          </span>
                        )}
                      </label>
                    )
                  })}
                  <div className="flex justify-between px-3 pt-1.5 text-sm">
                    <span className="text-[#A1A1A8]">Buildout total</span>
                    <span className="text-white font-semibold">
                      ${websiteOneTime} one-time
                      {websiteMonthlyDue > 0 && <span className="text-[#A1A1A8] font-normal"> · ${websiteMonthlyDue}/mo ongoing</span>}
                      {monthlyFree && <span className="text-[#17C5B0] font-normal"> · maintenance &amp; hosting included with {selectedPlan.label}</span>}
                    </span>
                  </div>
                </div>
                <input type="text" value={websiteCurrentUrl} onChange={e => setWebsiteCurrentUrl(e.target.value)}
                  className={inputClass} placeholder="Current website — leave empty if none" />
                <textarea rows={2} value={websiteGoals} onChange={e => setWebsiteGoals(e.target.value)}
                  className={`${inputClass} resize-none`} placeholder="What must the site do? (required — the builders' brief)" />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input type="text" value={websitePages} onChange={e => setWebsitePages(e.target.value)}
                    className={inputClass} placeholder="Pages (comma-separated)" />
                  <select value={websiteContent} onChange={e => setWebsiteContent(e.target.value as 'ready' | 'none')}
                    className={inputClass}>
                    <option value="ready">Owner has content ready</option>
                    <option value="none">Write it for them</option>
                  </select>
                </div>
                <input type="text" value={websiteBrand} onChange={e => setWebsiteBrand(e.target.value)}
                  className={inputClass} placeholder="Brand notes — colors, tone, sites they like" />
                <p className="text-[10px] text-[#17C5B0]/60">Creating the customer launches a 48-hour build contest — the owner picks their site from real, clickable previews.</p>
              </div>
            )}
            <div className="flex items-center justify-between p-4 border-t border-[#1F1F23]">
              <div>
                <p className="text-sm font-semibold text-white">{CUSTOM_CRM_SERVICE.label}</p>
                <p className="text-[10px] text-[#A1A1A8]">{CUSTOM_CRM_SERVICE.blurb}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-[#17C5B0]">${crmOneTime}</span>
                <div className={`w-9 h-5 rounded-full transition-colors relative cursor-pointer ${crm ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]'}`}
                  onClick={() => setCrm(!crm)}
                >
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${crm ? 'translate-x-4' : 'translate-x-0.5'}`} />
                </div>
              </div>
            </div>
            {crm && (
              <div className="px-4 pb-4 pt-3 space-y-2 border-t border-[#1F1F23]">
                <input type="number" min={0} value={crmAmount} onChange={e => setCrmAmount(e.target.value)}
                  className={inputClass} placeholder="Build price — the amount you quoted (required)" />
                <p className="text-[10px] text-[#4a5550]">Scoped per deal. Adds to the one-time setup fee.</p>
              </div>
            )}
            <div className="flex items-center justify-between p-4 border-t border-[#1F1F23]">
              <div>
                <p className="text-sm font-semibold text-white">{AD_SPOT_SERVICE.label}</p>
                <p className="text-[10px] text-[#A1A1A8]">{AD_SPOT_SERVICE.blurb}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-[#17C5B0]">${AD_SPOT_SERVICE.price.toLocaleString()}</span>
                <div className={`w-9 h-5 rounded-full transition-colors relative cursor-pointer ${adSpot ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]'}`}
                  onClick={() => setAdSpot(!adSpot)}
                >
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${adSpot ? 'translate-x-4' : 'translate-x-0.5'}`} />
                </div>
              </div>
            </div>
            {adSpot && (
              <div className="px-4 pb-4 pt-3 space-y-2 border-t border-[#1F1F23]">
                <textarea rows={2} value={adGoal} onChange={e => setAdGoal(e.target.value)}
                  className={`${inputClass} resize-none`} placeholder="What must the ad sell? (required — this is the creative brief)" />
                <input type="text" value={adHighlights} onChange={e => setAdHighlights(e.target.value)}
                  className={inputClass} placeholder="Feature these — comma-separated" />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <select value={adPlacement} onChange={e => setAdPlacement(e.target.value)} className={inputClass}>
                    {AD_SPOT_PLACEMENTS.map(p => <option key={p.id} value={p.id}>{p.label} ({p.aspect})</option>)}
                  </select>
                  <select value={adAudio} onChange={e => setAdAudio(e.target.value)} className={inputClass}>
                    {AD_SPOT_AUDIO.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
                  </select>
                </div>
                <input type="text" value={adBrand} onChange={e => setAdBrand(e.target.value)}
                  className={inputClass} placeholder="Brand notes — colors, tone, ads they like" />
                <p className="text-[10px] text-[#17C5B0]/60">
                  {adSpotOrderId
                    ? `Spot boarded — order ${adSpotOrderId}`
                    : `Creating the account boards the spot into ${AD_SPOT_SERVICE.shotCount} shots and starts generating them.`}
                </p>
              </div>
            )}
          </div>
          <p className="text-[10px] text-[#4a5550] mt-1.5">More setup services are on the way — each lists its price and adds to the one-time setup fee.</p>
        </div>

        {/* First month free */}
        <label className="flex items-center gap-3 cursor-pointer">
          <div className={`w-9 h-5 rounded-full transition-colors relative ${firstMonthFree ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]'}`}
            onClick={() => setFirstMonthFree(!firstMonthFree)}
          >
            <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${firstMonthFree ? 'translate-x-4' : 'translate-x-0.5'}`} />
          </div>
          <span className="text-sm text-white">First month free</span>
        </label>

        {/* First-month-free breakdown — only shown when toggle is on */}
        {firstMonthFree && (
          <div className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-[#17C5B0]/5 border border-[#17C5B0]/20">
            <span className="text-xs text-[#A1A1A8]">First month</span>
            <span className="text-xs font-semibold text-[#17C5B0]">
              $0 <span className="text-[#4a5550] font-normal">(free — setup fee still due today)</span>
            </span>
          </div>
        )}

        {/* Due Today — always visible so rep and customer always see the exact charge */}
        <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
          <span className="text-xs text-[#A1A1A8]">Due today</span>
          <span className="text-sm font-bold text-[#17C5B0]">
            ${((firstMonthFree ? 0 : monthlyPrice) + (Number(setupFee) || 0)).toLocaleString()}
          </span>
        </div>

        {/* Buttons */}
        <button
          onClick={handleGenerateProposal}
          disabled={proposalGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-all"
        >
          {proposalGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating…</>
          ) : (
            <><Sparkles size={16} /> {proposalBlob ? 'Regenerate Proposal' : 'Generate Proposal'}</>
          )}
        </button>

        {proposalBlob && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20">
            <CheckCircle2 size={16} className="text-[#17C5B0]" />
            <span className="text-xs text-[#17C5B0] font-medium">Proposal ready — 9 slides, PDF generated.</span>
            <button onClick={handleDownloadProposal} className="ml-auto text-[#17C5B0] hover:text-white transition-colors">
              <Download size={14} />
            </button>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleViewProposal}
            disabled={proposalGenerating}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-all"
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
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1F1F23] text-white text-sm font-medium rounded-lg hover:border-[#17C5B0]/30 disabled:opacity-50 transition-all"
          >
            {proposalEmailing ? (
              <><Loader2 size={16} className="animate-spin" /> Sending…</>
            ) : proposalSent ? (
              <><CheckCircle2 size={16} className="text-[#17C5B0]" /> Sent!</>
            ) : (
              <><Mail size={16} /> Email Proposal</>
            )}
          </button>
        </div>
      </div>

      {/* Step 2 - Invoice / Customer Checkout (visible at step 2+) */}
      {currentStep >= 2 && (
      <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Invoice &amp; Checkout</h2>
        <p className="text-xs text-[#A1A1A8]">
          Generate a custom invoice in USD with a QR code the customer can scan to view. Invoices recur monthly.
        </p>

        <button
          onClick={handleGenerateInvoice}
          disabled={invoiceGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-all"
        >
          {invoiceGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating Invoice…</>
          ) : (
            <><FileText size={16} /> {invoiceBlob ? 'Regenerate Invoice' : 'Generate Invoice (USD)'}</>
          )}
        </button>

        {invoiceBlob && (
          <>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20">
              <CheckCircle2 size={16} className="text-[#17C5B0]" />
              <span className="text-xs text-[#17C5B0] font-medium">
                Invoice #{invoiceNumber} ready — includes QR code for online viewing.
              </span>
              <button onClick={handleDownloadInvoice} className="ml-auto text-[#17C5B0] hover:text-white transition-colors">
                <Download size={14} />
              </button>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleDownloadInvoice}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1F1F23] text-white text-sm font-medium rounded-lg hover:border-[#17C5B0]/30 transition-all"
              >
                <Eye size={16} /> View Invoice
              </button>
              <button
                onClick={handleEmailInvoice}
                disabled={invoiceEmailing}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1F1F23] text-white text-sm font-medium rounded-lg hover:border-[#17C5B0]/30 disabled:opacity-50 transition-all"
              >
                {invoiceEmailing ? (
                  <><Loader2 size={16} className="animate-spin" /> Sending…</>
                ) : invoiceEmailed ? (
                  <><CheckCircle2 size={16} className="text-[#17C5B0]" /> Invoice Sent!</>
                ) : (
                  <><Mail size={16} /> Email Invoice</>
                )}
              </button>
            </div>
            {checkoutQr && (
              <div className="flex flex-col sm:flex-row items-center gap-4 p-4 rounded-lg bg-[#0A0A0B] border border-[#17C5B0]/20">
                <img src={checkoutQr} alt="Monthly Subscription QR code" className="w-28 h-28 rounded-lg shrink-0" />
                <div className="min-w-0 flex-1 text-center sm:text-left">
                  <p className="text-sm font-semibold text-white mb-0.5">Monthly Subscription — Scan to Subscribe</p>
                  <p className="text-[10px] text-[#A1A1A8] mb-2.5">
                    Customer scans this to start their monthly USD subscription — or tap the link below.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <a
                      href={checkoutUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold hover:bg-[#17C5B0]/90 active:scale-[0.98] transition-all"
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
                          /* clipboard blocked */
                        }
                      }}
                      className={`inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-medium transition-all ${
                        checkoutCopied
                          ? 'border-[#17C5B0]/40 bg-[#17C5B0]/10 text-[#17C5B0]'
                          : 'border-[#1F1F23] bg-[#111113] text-[#A1A1A8] hover:border-[#17C5B0]/30 hover:text-white active:scale-[0.98]'
                      }`}
                    >
                      {checkoutCopied ? <Check size={11} /> : <Copy size={11} />}
                      {checkoutCopied ? 'Copied' : 'Copy link'}
                    </button>
                  </div>
                </div>
              </div>
            )}
            <p className="text-[10px] text-[#4a5550]">
              Monthly Subscription — customer will be billed ${monthlyPrice.toLocaleString()}/mo automatically.
            </p>
          </>
        )}
      </div>
      )}

      {/* Payment Status & Card Management (visible at step 2+) */}
      {currentStep >= 2 && (
      <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CreditCard size={16} className="text-[#17C5B0]" />
            <h2 className="text-sm font-semibold text-white">Payment Status</h2>
          </div>
          <button
            onClick={checkPaymentStatus}
            disabled={paymentStatus === 'checking'}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:text-[#17C5B0] hover:border-[#17C5B0]/30 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={10} className={paymentStatus === 'checking' ? 'animate-spin' : ''} />
            {paymentStatus === 'idle' ? 'Check Status' : 'Refresh'}
          </button>
        </div>

        {paymentStatus === 'idle' && (
          <p className="text-xs text-[#A1A1A8]">Click "Check Status" to see if the customer has paid.</p>
        )}

        {paymentStatus === 'checking' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#1F1F23]">
            <Loader2 size={14} className="text-[#17C5B0] animate-spin" />
            <span className="text-xs text-[#A1A1A8]">Checking payment status...</span>
          </div>
        )}

        {paymentStatus === 'active' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20">
            <CheckCircle2 size={16} className="text-[#17C5B0]" />
            <div>
              <span className="text-xs text-[#17C5B0] font-medium">Payment confirmed — subscription active</span>
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
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-all"
              >
                {cardUpdateSending ? (
                  <><Loader2 size={14} className="animate-spin" /> Creating Link...</>
                ) : (
                  <><CreditCard size={14} /> Send Card Update Link</>
                )}
              </button>
            </div>

            {cardUpdateUrl && (
              <div className="p-3 rounded-lg bg-[#0A0A0B] border border-[#1F1F23] space-y-2">
                <p className="text-[10px] text-[#A1A1A8]">Payment update link (sent to customer):</p>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={cardUpdateUrl}
                    className="flex-1 px-2 py-1.5 bg-[#111113] border border-[#1F1F23] rounded text-[11px] text-white font-mono truncate"
                  />
                  <button
                    onClick={() => { navigator.clipboard.writeText(cardUpdateUrl); }}
                    className="px-3 py-1.5 text-[10px] text-[#17C5B0] border border-[#17C5B0]/30 rounded hover:bg-[#17C5B0]/10 transition-colors"
                  >
                    Copy
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {paymentStatus === 'unavailable' && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#1F1F23]">
            <span className="text-xs text-[#A1A1A8]">No billing record found yet — invoice may not have been created.</span>
          </div>
        )}
      </div>
      )}

      {/* Step 2b - SLA Document (visible at step 2+) */}
      {currentStep >= 2 && (
      <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-[#17C5B0]" />
          <h2 className="text-sm font-semibold text-white">Service Level Agreement</h2>
        </div>
        <p className="text-xs text-[#A1A1A8]">
          Generate an SLA document for the client to sign. Includes data privacy compliance.
        </p>

        <button
          onClick={handleGenerateSla}
          disabled={slaGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#1F1F23] border border-[#2a3830] text-white text-sm font-semibold rounded-lg hover:border-[#17C5B0]/30 disabled:opacity-50 transition-all"
        >
          {slaGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating SLA…</>
          ) : (
            <><FileText size={16} /> {slaBlob ? 'Regenerate SLA' : 'Generate SLA Document'}</>
          )}
        </button>

        {slaBlob && (
          <>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20">
              <CheckCircle2 size={16} className="text-[#17C5B0]" />
              <span className="text-xs text-[#17C5B0] font-medium">
                SLA document ready{slaSigned ? ' — signed' : ''}.
              </span>
              <button onClick={handleDownloadSla} className="ml-auto text-[#17C5B0] hover:text-white transition-colors">
                <Download size={14} />
              </button>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleDownloadSla}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1F1F23] text-white text-sm font-medium rounded-lg hover:border-[#17C5B0]/30 transition-all"
              >
                <Eye size={16} /> View SLA
              </button>
              {!slaSigned ? (
                <button
                  onClick={() => setShowSlaSign(true)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all"
                >
                  <Pencil size={16} /> Sign SLA
                </button>
              ) : (
                <button
                  onClick={handleEmailSla}
                  disabled={slaEmailing}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1F1F23] text-white text-sm font-medium rounded-lg hover:border-[#17C5B0]/30 disabled:opacity-50 transition-all"
                >
                  {slaEmailing ? (
                    <><Loader2 size={16} className="animate-spin" /> Sending…</>
                  ) : slaEmailed ? (
                    <><CheckCircle2 size={16} className="text-[#17C5B0]" /> SLA Sent!</>
                  ) : (
                    <><Mail size={16} /> Email Signed SLA</>
                  )}
                </button>
              )}
            </div>

            {slaSigned && (
              <div className="text-[10px] text-[#4a5550] space-y-0.5">
                <p>Provider: Aidan Pierce, Founder & CEO — {new Date().toLocaleDateString('en-US')}</p>
                <p>Client: {slaSignature} — {new Date().toLocaleDateString('en-US')}</p>
                {slaEmailed && <p className="text-[#17C5B0]">Signed copy emailed to {deal?.contact_email}</p>}
              </div>
            )}
          </>
        )}

        {/* Signature Modal */}
        {showSlaSign && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="w-full max-w-lg bg-[#111113] border border-[#1F1F23] rounded-xl p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-base font-semibold text-white">Sign Service Level Agreement</h3>
                <button onClick={() => setShowSlaSign(false)} className="p-1.5 rounded-lg hover:bg-[#1F1F23] transition-colors">
                  <X size={18} className="text-[#A1A1A8]" />
                </button>
              </div>
              <p className="text-xs text-[#A1A1A8] mb-4">
                By typing your full legal name below, you acknowledge that you have read and agree to the terms of the Service Level Agreement between Meridian AI Business Solutions and {deal?.business_name}. A signed copy will be emailed to both parties.
              </p>
              <div className="space-y-4">
                {/* Provider signature — pre-filled */}
                <div className="p-4 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg">
                  <p className="text-[10px] text-[#A1A1A8] mb-1">Provider — Meridian AI Business Solutions</p>
                  <p className="text-lg font-serif italic text-[#17C5B0]">Aidan Pierce</p>
                  <p className="text-[10px] text-[#4a5550] mt-1">Founder & CEO</p>
                </div>

                {/* Client signature */}
                <div>
                  <label className="text-xs text-[#A1A1A8] mb-1.5 block">Client — {deal?.business_name}</label>
                  <input
                    type="text"
                    value={slaSignature}
                    onChange={e => setSlaSignature(e.target.value)}
                    placeholder="Client signatory full legal name"
                    className="w-full px-3 py-2.5 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-sm text-white placeholder-[#A1A1A8] focus:outline-none focus:border-[#17C5B0]/50 focus:ring-1 focus:ring-[#17C5B0]/20 transition-colors"
                  />
                </div>
                {slaSignature.trim() && (
                  <div className="p-4 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg">
                    <p className="text-[10px] text-[#A1A1A8] mb-1">Client signature preview</p>
                    <p className="text-xl font-serif italic text-white">{slaSignature}</p>
                  </div>
                )}

                <p className="text-[10px] text-[#4a5550]">
                  Date: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
                <div className="flex justify-end gap-2 mt-4">
                  <button onClick={() => setShowSlaSign(false)} className="px-4 py-2 text-sm text-[#A1A1A8] hover:text-white transition-colors">Cancel</button>
                  <button
                    onClick={handleSignSla}
                    disabled={!slaSignature.trim() || slaSigning}
                    className="px-4 py-2 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-all"
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
      <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Connect POS System</h2>

        <POSSystemPicker
          value={selectedPOS}
          onChange={k => { setSelectedPOS(k); setPosConnected(false); setPosError(null); setPosPending(null) }}
          onCredentialSubmit={handleCredentialSubmit}
          mode="lead-detail"
          portalContext="us"
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
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20">
            <CheckCircle2 size={16} className="text-[#17C5B0]" />
            <span className="text-xs text-[#17C5B0] font-medium">
              POS connected and verified — data is flowing. This deal is now active.
            </span>
          </div>
        )}
      </div>
      )}

      {/* Project Files */}
      <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Project Files</h2>
          <button onClick={handleUpload} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#17C5B0] border border-[#17C5B0]/30 rounded-lg hover:bg-[#17C5B0]/10 transition-all">
            <Upload size={14} /> Upload
          </button>
        </div>

        <div className="space-y-2">
          {files.map(file => (
            <div key={file.id} className="flex items-center gap-3 p-3 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg hover:border-[#17C5B0]/20 transition-colors cursor-pointer group"
              onClick={() => {
                if (file.tag === 'Proposal' && proposalBlob) openBlobInNewTab(proposalBlob)
                else if (file.tag === 'Contract' && slaBlob) openBlobInNewTab(slaBlob)
              }}
            >
              <FileText size={16} className="text-[#A1A1A8] flex-shrink-0 group-hover:text-[#17C5B0] transition-colors" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate group-hover:text-[#17C5B0] transition-colors">{file.name}</p>
                <p className="text-[11px] text-[#4a5550]">{file.description}</p>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-[#1F1F23] text-[#A1A1A8] font-medium flex-shrink-0">
                {file.tag}
              </span>
              <ExternalLink size={14} className="text-[#4a5550] group-hover:text-[#17C5B0] transition-colors flex-shrink-0" />
              <button
                onClick={(e) => { e.stopPropagation(); removeFile(file.id) }}
                className="p-1 rounded hover:bg-red-500/10 transition-colors flex-shrink-0"
              >
                <Trash2 size={14} className="text-[#A1A1A8] hover:text-red-400" />
              </button>
            </div>
          ))}
          {files.length === 0 && (
            <p className="text-xs text-[#4a5550] text-center py-4">No files uploaded yet.</p>
          )}
        </div>
      </div>

      {/* Stage Advancement */}
      {currentStep > 0 && currentStep < 3 && deal.stage !== 'closed_lost' && (
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white">Advance Deal</h2>
          <button
            onClick={async () => {
              try {
                const pipeline: DealStage[] = ['proposal_shown', 'customer_checkout', 'customer_walkthrough']
                const currentIdx = pipeline.findIndex(s => STAGE_TO_STEP[s] === currentStep)
                const nextIdx = currentIdx < 0 ? 0 : currentIdx + 1
                if (nextIdx >= pipeline.length) return
                const nextStage = pipeline[nextIdx]
                await usLeadsService.updateStage(deal.id, nextStage)
                setDeal(prev => prev ? { ...prev, stage: nextStage } : prev)
              } catch (err) {
                console.error('Stage advance failed:', err)
              }
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-[#17C5B0]/30 text-[#17C5B0] text-sm font-medium rounded-lg hover:bg-[#17C5B0]/10 transition-all"
          >
            <ChevronRight size={16} /> Advance to Next Stage
          </button>
        </div>
      )}

      {/* Create Customer Account Login (visible at step 3+) */}
      {currentStep >= 3 && (
        <div className="bg-[#111113] border border-[#17C5B0]/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-[#17C5B0]" />
            <h2 className="text-sm font-semibold text-[#17C5B0]">Create Customer Account Login</h2>
          </div>
          <p className="text-xs text-[#A1A1A8]">
            Generate a login for {deal.contact_name} to access the Meridian customer portal. They'll be guided through a walkthrough to verify their POS connection, set up cameras, and explore their dashboard.
          </p>

          {customerCredentials ? (
            <div className="space-y-3">
              {websiteContestUrl && (
                <div className="p-4 rounded-lg bg-[#17C5B0]/5 border border-[#17C5B0]/20">
                  <p className="text-[10px] font-mono text-[#17C5B0] tracking-wider mb-1.5">48-HOUR WEBSITE CONTEST — LIVE</p>
                  <a href={websiteContestUrl} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-white underline decoration-[#17C5B0]/60 break-all">
                    {websiteContestUrl}
                  </a>
                </div>
              )}
              <div className="p-4 rounded-lg bg-[#0A0A0B] border border-[#1F1F23] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#A1A1A8]">Email</span>
                  <span className="text-sm text-white font-mono">{customerCredentials.email}</span>
                </div>
                {customerCredentials.tempPassword && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#A1A1A8]">Temp password</span>
                    <span className="flex items-center gap-2">
                      <span className="text-sm text-white font-mono">{customerCredentials.tempPassword}</span>
                      <button type="button" onClick={() => navigator.clipboard.writeText(customerCredentials.tempPassword || '')}
                        className="text-[10px] text-[#17C5B0] hover:underline">Copy</button>
                    </span>
                  </div>
                )}
                <p className="text-[10px] text-[#4a5550] mt-1">Share the temp password with the customer (or use the email button below). They&apos;ll be prompted to set their own password on first login.</p>
              </div>
              <button
                onClick={handleEmailCredentials}
                disabled={credentialEmailing || credentialEmailed}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-[#17C5B0]/30 text-[#17C5B0] text-sm font-medium rounded-lg hover:bg-[#17C5B0]/10 disabled:opacity-50 transition-all"
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
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-all"
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
        <div className="bg-[#111113] border border-[#17C5B0]/20 rounded-xl p-5 space-y-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-[#17C5B0]" />
            <h2 className="text-sm font-semibold text-[#17C5B0]">Active Deal — Customer Onboarding</h2>
          </div>
          <p className="text-xs text-[#A1A1A8]">
            This deal is active. The customer has been set up and is going through their onboarding walkthrough.
          </p>
        </div>
      )}

      {/* Mark as Lost */}
      {deal.stage !== 'customer_walkthrough' && deal.stage !== 'closed_won' && deal.stage !== 'closed_lost' && (
        <button
          onClick={async () => {
            try {
              await usLeadsService.updateStage(deal.id, 'closed_lost')
              navigate('/us/portal/leads')
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
          <div className="w-full max-w-sm bg-[#111113] border border-[#1F1F23] rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-white">Delete lead?</h3>
              <button onClick={() => setShowDelete(false)} className="p-1.5 rounded-lg hover:bg-[#1F1F23] transition-colors">
                <X size={18} className="text-[#A1A1A8]" />
              </button>
            </div>
            <p className="text-sm text-[#A1A1A8] mb-5">
              This permanently removes &ldquo;{deal.business_name}&rdquo; and can&rsquo;t be undone. Use &ldquo;Mark as Lost&rdquo; instead if you only want to close the deal.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDelete(false)}
                className="px-4 py-2 text-sm text-[#A1A1A8] hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={deleting}
                onClick={async () => {
                  setDeleting(true)
                  try {
                    await usLeadsService.delete(deal.id)
                    toast('Lead deleted', 'success')
                    navigate('/us/portal/leads')
                  } catch (err) {
                    toast(err instanceof Error ? err.message : 'Failed to delete lead', 'error')
                    setDeleting(false)
                  }
                }}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/90 text-white text-sm font-semibold rounded-lg hover:bg-red-500 transition-all disabled:opacity-50"
              >
                {deleting && <Loader2 size={14} className="animate-spin" />}
                {deleting ? 'Deleting…' : 'Delete'}
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
 *  - If deal.vertical resolves to a known US deck → the proposal entry point
 *    lives in the Step 1 "Proposal" section, so this card renders nothing.
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
  const deck = useMemo(() => findUsVerticalByValue(deal.vertical), [deal.vertical])
  const personalizedUrl = useMemo(
    () => (deck ? buildPersonalizedUsDeckUrl(deck.slug, rep, deal.business_name, { monthly, setup, currency: 'USD' }) : ''),
    [deck, rep, deal.business_name, monthly, setup],
  )

  // Quick-tag chip selection — 6 most common US verticals for fast tagging.
  const quickTagSlugs = ['us-qsr', 'us-coffee', 'us-bar', 'us-salon', 'us-dental', 'us-liquor']
  const quickTags = useMemo(
    () => quickTagSlugs.map(s => US_VERTICALS.find(v => v.slug === s)).filter(Boolean) as typeof US_VERTICALS,
    [],
  )

  if (!deck) {
    return (
      <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Tag size={14} className="text-[#f0b429]" />
          <h2 className="text-sm font-semibold text-white">Tag this lead with a business type</h2>
        </div>
        <p className="text-xs text-[#A1A1A8]">
          Pick the industry to auto-generate the matching personalized proposal deck for {deal.business_name}.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {quickTags.map(v => (
            <button
              key={v.slug}
              disabled={tagging}
              onClick={() => onTagVertical(v.slug)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-[#1F1F23] bg-[#0A0A0B] text-[11px] text-[#A1A1A8] hover:border-[#17C5B0]/40 hover:text-white disabled:opacity-50 transition-colors"
            >
              {tagging ? <Loader2 size={10} className="animate-spin" /> : null}
              {v.title}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-[#4a5550]">
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
  void onCopy
  void copied
  return null
}
