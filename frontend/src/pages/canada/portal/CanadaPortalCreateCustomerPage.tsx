import { useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, CheckCircle2, Copy, Send, Check,
  Store, User, Mail, Phone, DollarSign, FileDown,
  Loader2, Eye, Gift, Sparkles, QrCode, ExternalLink, X,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import { posSystems } from '@/data/pos-systems'
import { supabase, getAuthHeaders } from '@/lib/supabase'
import { PLAN_TIERS, getPlan, type PlanTier } from '@/lib/canada-proposal-plans'
import { downloadProposalPdf, type ProposalInput } from '@/lib/generate-proposal-pdf'
import { verticalsByGroup, findVerticalBySlug, DECK_BASE_URL, buildPersonalizedDeckUrl } from '@/data/cadVerticals'

type Step = 'details' | 'plan' | 'customize' | 'preview' | 'confirm'

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

function generateQrSvg(text: string, size: number = 256): string {
  const encoded = encodeURIComponent(text)
  return `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encoded}&bgcolor=0A0F0D&color=00d4aa&format=svg`
}

const API_URL = import.meta.env.VITE_API_URL || ''

/* ─── Proposal Slide Overlay ─── */
function ProposalOverlay({
  open,
  onClose,
  businessName,
  ownerName,
  plan,
  price,
  setupFee,
  firstMonthFree,
  repName,
  repEmail,
  repPhone,
  checkoutUrl,
  onDownloadPdf,
  verticalTitle,
  deckUrl,
}: {
  open: boolean
  onClose: () => void
  businessName: string
  ownerName: string
  plan: PlanTier
  price: number
  setupFee: number
  firstMonthFree: boolean
  repName: string
  repEmail: string
  repPhone?: string
  checkoutUrl: string
  onDownloadPdf: () => void
  verticalTitle?: string
  deckUrl?: string
}) {
  const [currentSlide, setCurrentSlide] = useState(0)
  const totalSlides = 8
  const firstName = ownerName.split(' ')[0]
  const interval = plan.interval === 'week' ? '/wk' : '/mo'
  const dueToday = (firstMonthFree ? 0 : price) + setupFee
  const today = new Date().toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' })

  if (!open) return null

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const slideIdx = Math.round(el.scrollTop / el.clientHeight)
    setCurrentSlide(slideIdx)
  }

  const scrollToSlide = (idx: number) => {
    const container = document.getElementById('proposal-slides')
    if (container) {
      container.scrollTo({ top: idx * container.clientHeight, behavior: 'smooth' })
    }
  }

  return (
    <div className="fixed inset-0 z-[9999] bg-pm-canada-bg">
      {/* Close button */}
      <button
        onClick={onClose}
        className="fixed top-4 right-4 z-[10001] w-10 h-10 rounded-full bg-pm-canada-border border border-pm-canada-border flex items-center justify-center text-white hover:bg-pm-canada-surface transition-colors"
      >
        <X size={18} />
      </button>

      {/* Download PDF button */}
      <button
        onClick={onDownloadPdf}
        className="fixed top-4 right-16 z-[10001] px-3 py-2 rounded-lg bg-pm-canada-border border border-pm-canada-border flex items-center gap-2 text-2xs text-pm-canada-text-muted hover:text-pm-accent transition-colors"
      >
        <FileDown size={14} /> PDF
      </button>

      {/* Dot navigation */}
      <div className="fixed right-4 top-1/2 -translate-y-1/2 z-[10001] flex flex-col gap-2">
        {Array.from({ length: totalSlides }).map((_, i) => (
          <button
            key={i}
            onClick={() => scrollToSlide(i)}
            className={`w-2 h-2 rounded-full transition-all duration-300 ${
              i === currentSlide ? 'bg-pm-accent scale-125' : 'bg-pm-canada-border hover:bg-pm-canada-text-faint'
            }`}
          />
        ))}
      </div>

      {/* Slide counter */}
      <div className="fixed bottom-4 right-4 z-[10001] text-2xs font-mono text-pm-canada-text-faint">
        {String(currentSlide + 1).padStart(2, '0')} / {String(totalSlides).padStart(2, '0')}
      </div>

      {/* Slides container */}
      <div
        id="proposal-slides"
        className="h-screen overflow-y-auto snap-y snap-mandatory scroll-smooth"
        onScroll={handleScroll}
        style={{ scrollSnapType: 'y mandatory' }}
      >
        {/* ═══ SLIDE 1: Cover ═══ */}
        <div className="min-h-screen snap-start relative flex flex-col justify-center items-start px-12 sm:px-20 overflow-hidden">
          {/* Animated diagonal lines */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="proposal-lines absolute inset-0" />
          </div>
          <div className="relative z-10">
            <p className="text-2xs font-mono tracking-[0.2em] text-pm-accent uppercase mb-8">
              MERIDIAN CANADA · {verticalTitle ? `${verticalTitle.toUpperCase()} ` : ''}PROPOSAL (CAD)
            </p>
            <p className="text-sm text-pm-canada-text-muted italic font-serif mb-2">Prepared for</p>
            <h1 className="text-4xl sm:text-6xl font-bold text-white leading-tight">{businessName}</h1>
            {verticalTitle && (
              <p className="mt-3 text-sm-tight font-mono tracking-[0.14em] text-pm-accent uppercase">
                {verticalTitle}
              </p>
            )}
            <div className="mt-8 space-y-1">
              <p className="text-sm-tight text-pm-canada-text-muted">{today}</p>
              <p className="text-sm-tight text-pm-canada-text-muted">{ownerName} · {repEmail}</p>
            </div>
          </div>
        </div>

        {/* ═══ SLIDE 2: Features ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-2xs font-mono tracking-[0.2em] text-pm-accent uppercase mb-4">WHAT YOU GET</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-10">Platform Features</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { title: 'POS Analytics', desc: 'Real-time revenue tracking, hourly trends, and anomaly detection.', icon: '📊' },
              { title: 'Revenue Forecasting', desc: 'AI predicts tomorrow\'s sales with 90%+ accuracy.', icon: '🔮' },
              { title: 'Inventory Tracking', desc: 'Know what sells, what sits, and when to reorder.', icon: '📦' },
              { title: 'Staff Performance', desc: 'Per-employee metrics for speed, upsells, and revenue.', icon: '👥' },
              { title: 'Customer Insights', desc: 'Repeat visit patterns, average spend, and churn risk.', icon: '💡' },
              { title: 'Alerts & Anomalies', desc: 'Instant notifications when something looks off.', icon: '🚨' },
            ].map(f => (
              <div key={f.title} className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5">
                <div className="text-2xl mb-3">{f.icon}</div>
                <h3 className="text-sm font-semibold text-white mb-1">{f.title}</h3>
                <p className="text-xs text-pm-canada-text-muted leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ SLIDE 3: Plan Details ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-2xs font-mono tracking-[0.2em] text-pm-accent uppercase mb-4">YOUR PLAN</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-10">Meridian {plan.label}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="bg-pm-canada-surface border border-pm-accent/20 rounded-xl p-6">
              <p className="text-2xs font-mono text-pm-accent tracking-wider mb-4">WHAT'S INCLUDED</p>
              <div className="space-y-3">
                {(plan.features || []).map(f => (
                  <div key={f} className="flex items-start gap-2">
                    <CheckCircle2 size={14} className="text-pm-accent mt-0.5 flex-shrink-0" />
                    <span className="text-sm-tight text-white">{f}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-6">
              <p className="text-2xs font-mono text-pm-purple tracking-wider mb-4">ALSO BUILT IN</p>
              <div className="space-y-3">
                {[
                  '5-minute onboarding',
                  'Square + Clover + Toast integration',
                  'AI-powered insights engine',
                  'Self-healing data pipelines',
                  'Real-time anomaly detection',
                  'Mobile-friendly dashboard',
                ].map(f => (
                  <div key={f} className="flex items-start gap-2">
                    <CheckCircle2 size={14} className="text-pm-purple mt-0.5 flex-shrink-0" />
                    <span className="text-sm-tight text-white">{f}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ═══ SLIDE 4: POS Analytics ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-2xs font-mono tracking-[0.2em] text-pm-accent uppercase mb-4">POS ANALYTICS ENGINE</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-10">Your Sales Data, Decoded</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                icon: '📊', title: 'Revenue Intelligence', titleClass: 'text-pm-accent',
                desc: 'Track hourly, daily, weekly revenue. Spot slow days before they drain cash.',
                example: '"Tuesday lunch dropped 18% vs 4-week avg."',
              },
              {
                icon: '🧮', title: 'Menu Engineering', titleClass: 'text-pm-purple',
                desc: 'Every item classified as Star, Plow Horse, Puzzle, or Dog.',
                example: '"Acai bowl has 62% margin but only 3% orders. Move to position #2."',
              },
              {
                icon: '🔮', title: 'Predictive Forecasting', titleClass: 'text-pm-accent',
                desc: 'AI predicts tomorrow\'s sales with 90%+ accuracy. Auto-suggested prep lists.',
                example: '"Friday predicted: CA$4,280 (+12%). Recommend 2 extra staff 11am-2pm."',
              },
            ].map(card => (
              <div key={card.title} className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5">
                <div className="text-2xl mb-3">{card.icon}</div>
                <h3 className={`text-sm font-semibold mb-2 ${card.titleClass}`}>{card.title}</h3>
                <p className="text-xs text-pm-canada-text-muted leading-relaxed mb-3">{card.desc}</p>
                <div className="bg-pm-canada-bg border border-pm-canada-border rounded-lg p-3">
                  <p className="text-2xs font-mono text-pm-canada-text-faint mb-1">EXAMPLE INSIGHT</p>
                  <p className="text-2xs text-white italic">{card.example}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ SLIDE 5: Value / ROI ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-2xs font-mono tracking-[0.2em] text-pm-accent uppercase mb-4">YOUR INVESTMENT</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-10">Simple, Transparent Pricing</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="bg-pm-canada-surface border border-pm-accent/20 rounded-xl p-6">
              <p className="text-2xs font-mono text-pm-accent tracking-wider mb-4">MERIDIAN {plan.label.toUpperCase()}</p>
              <div className="flex items-baseline gap-2 mb-6">
                <span className="text-4xl font-bold text-white font-mono">CA${price}</span>
                <span className="text-sm text-pm-canada-text-muted">{interval}</span>
              </div>
              <div className="space-y-2">
                {(plan.features || []).map(f => (
                  <div key={f} className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-pm-accent" />
                    <span className="text-xs text-pm-canada-text-muted">{f}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-6">
              <p className="text-2xs font-mono text-pm-purple tracking-wider mb-4">ORDER SUMMARY</p>
              <div className="space-y-3">
                <div className="flex justify-between py-2 border-b border-pm-canada-border">
                  <span className="text-sm-tight text-pm-canada-text-muted">{plan.label} Plan</span>
                  <span className="text-sm-tight text-white font-medium">CA${price}{interval}</span>
                </div>
                {setupFee > 0 && (
                  <div className="flex justify-between py-2 border-b border-pm-canada-border">
                    <span className="text-sm-tight text-pm-canada-text-muted">Setup Fee</span>
                    <span className="text-sm-tight text-white font-medium">CA${setupFee}</span>
                  </div>
                )}
                {firstMonthFree && (
                  <div className="flex justify-between py-2 border-b border-pm-canada-border">
                    <span className="text-sm-tight text-pm-canada-text-muted">First Month</span>
                    <span className="text-sm-tight text-pm-purple font-medium">FREE</span>
                  </div>
                )}
                <div className="flex justify-between py-3 mt-2">
                  <span className="text-sm text-white font-semibold">Due Today</span>
                  <span className="text-2xl font-bold text-pm-accent font-mono">CA${dueToday}</span>
                </div>
              </div>
              {/* Monthly value viz */}
              <div className="mt-4 bg-pm-canada-bg rounded-lg p-4 border border-pm-canada-border">
                <p className="text-2xs font-mono text-pm-canada-text-faint mb-2">MONTHLY VALUE</p>
                <div className="w-full h-3 bg-pm-canada-border rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-pm-accent to-pm-purple rounded-full" style={{ width: '75%' }} />
                </div>
                <p className="text-2xs text-pm-canada-text-muted mt-1">Avg. client sees 3-5x return in operational savings</p>
              </div>
            </div>
          </div>
        </div>

        {/* ═══ SLIDE 6: Camera Intelligence ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-2xs font-mono tracking-[0.2em] text-pm-purple uppercase mb-4">CAMERA INTELLIGENCE</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">POS + Camera = Meridian Insight</h2>
          <p className="text-sm text-pm-canada-text-muted mb-8 max-w-2xl">
            When we combine what your register knows with what the camera sees, you get insights no one else in your market has.
          </p>
          {/* Equation style */}
          <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6 mb-8">
            <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 flex-1 text-center">
              <p className="text-2xl mb-2">📷</p>
              <p className="text-sm-tight font-semibold text-white">Camera Feed</p>
              <p className="text-2xs text-pm-canada-text-muted">Foot traffic, dwell time, queue length</p>
            </div>
            <span className="text-2xl font-bold text-pm-purple">+</span>
            <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 flex-1 text-center">
              <p className="text-2xl mb-2">💳</p>
              <p className="text-sm-tight font-semibold text-white">POS Data</p>
              <p className="text-2xs text-pm-canada-text-muted">Sales, tickets, items, timing</p>
            </div>
            <span className="text-2xl font-bold text-pm-accent">=</span>
            <div className="bg-gradient-to-br from-pm-purple/10 to-pm-accent/10 border border-pm-purple/30 rounded-xl p-5 flex-1 text-center">
              <p className="text-2xl mb-2">🧠</p>
              <p className="text-sm-tight font-semibold text-pm-accent">Meridian Insight</p>
              <p className="text-2xs text-pm-canada-text-muted">Conversion rate, revenue per visitor, optimization</p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              'Foot traffic up but revenue flat? Conversion dropped — train staff on upsells.',
              'Long lines at noon? Open register 2 from 11:45am. Recover CA$2,380/week.',
              'Customers linger at display but don\'t buy? Try samples or price drop.',
              'Faster greeting = 47% higher ticket. Train all staff on top performer\'s flow.',
            ].map((insight, i) => (
              <div key={i} className="bg-pm-canada-surface border border-pm-canada-border rounded-lg p-3 flex items-start gap-2">
                <span className="text-pm-accent text-2xs mt-0.5">→</span>
                <p className="text-2xs text-white leading-relaxed">{insight}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ SLIDE 7: Social Proof ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-2xs font-mono tracking-[0.2em] text-pm-accent uppercase mb-4">SOCIAL PROOF</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-10">Businesses Like Yours</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                quote: '"We discovered our lunch conversion was only 44%. After adding a greeter, it jumped to 62%. That\'s CA$3K/month."',
                name: 'Marcus T.',
                biz: 'Quick-service restaurant, Vancouver',
              },
              {
                quote: '"Meridian told us our highest-margin item was buried on the menu. Moved it to #2 — sales tripled in a week."',
                name: 'Sarah L.',
                biz: 'Cafe & bakery, Toronto',
              },
              {
                quote: '"The camera intelligence showed we lose 8 customers per lunch rush to long lines. One extra staff member = CA$1,200/week recovered."',
                name: 'James K.',
                biz: 'Smoke shop, Calgary',
              },
            ].map(t => (
              <div key={t.name} className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 flex flex-col">
                <p className="text-xs text-white italic leading-relaxed flex-1">{t.quote}</p>
                <div className="mt-4 pt-3 border-t border-pm-canada-border">
                  <p className="text-xs font-semibold text-pm-accent">{t.name}</p>
                  <p className="text-2xs text-pm-canada-text-muted">{t.biz}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ SLIDE 8: CTA ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center items-center text-center px-12 sm:px-20">
          <p className="text-2xs font-mono tracking-[0.2em] text-pm-accent uppercase mb-6">READY TO GROW?</p>
          <h2 className="text-4xl sm:text-5xl font-bold text-white mb-2">
            Let's Go, <span className="text-pm-accent">{firstName}!</span>
          </h2>
          <p className="text-sm text-pm-canada-text-muted mt-4 max-w-lg">
            Connect your POS in 5 minutes. See your first insights today.
            {firstMonthFree ? ' First month is on us.' : ''}
          </p>

          {/* QR codes */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-10 max-w-lg w-full">
            {setupFee > 0 && (
              <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 flex flex-col items-center">
                <p className="text-2xs font-mono text-pm-canada-text-muted tracking-wider mb-3">SETUP FEE</p>
                <div className="w-28 h-28 bg-white rounded-lg flex items-center justify-center">
                  {checkoutUrl ? (
                    <img src={generateQrSvg(checkoutUrl, 112)} alt="QR" className="w-24 h-24" crossOrigin="anonymous" />
                  ) : (
                    <QrCode size={48} className="text-pm-canada-bg" />
                  )}
                </div>
                <p className="text-2xs text-white font-medium mt-3">CA${setupFee}</p>
              </div>
            )}
            <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 flex flex-col items-center">
              <p className="text-2xs font-mono text-pm-canada-text-muted tracking-wider mb-3">SUBSCRIPTION</p>
              <div className="w-28 h-28 bg-white rounded-lg flex items-center justify-center">
                {checkoutUrl ? (
                  <img src={generateQrSvg(checkoutUrl, 112)} alt="QR" className="w-24 h-24" crossOrigin="anonymous" />
                ) : (
                  <QrCode size={48} className="text-pm-canada-bg" />
                )}
              </div>
              <p className="text-2xs text-white font-medium mt-3">CA${price}{interval}</p>
            </div>
          </div>

          {deckUrl && (
            <div className="mt-8 max-w-xl w-full bg-gradient-to-br from-pm-accent/5 to-transparent border border-pm-accent/25 rounded-xl p-4 text-center">
              <p className="text-2xs font-mono tracking-[0.14em] text-pm-accent uppercase mb-2">
                Explore the full {verticalTitle || ''} deck
              </p>
              <a
                href={deckUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-white underline decoration-pm-accent/60 break-all"
              >
                {deckUrl}
              </a>
            </div>
          )}

          {/* Footer stats */}
          <div className="flex flex-wrap justify-center gap-8 mt-10 text-center">
            <div>
              <p className="text-2xs font-mono text-pm-canada-text-faint tracking-wider">YOUR REP</p>
              <p className="text-sm-tight text-white mt-1">{repName}</p>
            </div>
            <div>
              <p className="text-2xs font-mono text-pm-canada-text-faint tracking-wider">CONTACT</p>
              <p className="text-sm-tight text-white mt-1">{repEmail}</p>
            </div>
            <div>
              <p className="text-2xs font-mono text-pm-canada-text-faint tracking-wider">PLATFORM</p>
              <p className="text-sm-tight text-white mt-1">meridian.tips</p>
            </div>
            <div>
              <p className="text-2xs font-mono text-pm-canada-text-faint tracking-wider">SETUP TIME</p>
              <p className="text-sm-tight text-white mt-1">5 minutes</p>
            </div>
          </div>
        </div>
      </div>

      {/* CSS for animated diagonal lines */}
      <style>{`
        .proposal-lines {
          background: repeating-linear-gradient(
            -45deg,
            transparent,
            transparent 80px,
            rgba(0, 212, 170, 0.03) 80px,
            rgba(0, 212, 170, 0.03) 81px
          );
          animation: proposal-line-drift 20s linear infinite;
        }
        @keyframes proposal-line-drift {
          0% { transform: translateX(0) translateY(0); }
          100% { transform: translateX(113px) translateY(113px); }
        }
      `}</style>
    </div>
  )
}

/* ─── Main Page Component ─── */
export default function CanadaPortalCreateCustomerPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { rep } = useSalesAuth()
  const [step, setStep] = useState<Step>('details')
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [copied, setCopied] = useState(false)
  const [onboardingLink, setOnboardingLink] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [proposalGenerated, setProposalGenerated] = useState(false)
  const [showProposal, setShowProposal] = useState(false)

  const [creatingCheckout, setCreatingCheckout] = useState(false)
  const [checkoutUrl, setCheckoutUrl] = useState('')
  const [checkoutSessionId, setCheckoutSessionId] = useState('')
  const [copiedCheckout, setCopiedCheckout] = useState(false)

  // One org id for the whole customer record — generated once so the
  // create-checkout payment and the provision-customer account reconcile
  // (a payment must belong to the org we actually provision).
  const [orgId] = useState(() => uuid())

  const [form, setForm] = useState({
    businessName: searchParams.get('name') || '',
    ownerName: searchParams.get('contact') || '',
    email: searchParams.get('email') || '',
    phone: searchParams.get('phone') || '',
    vertical: searchParams.get('vertical') || '',
    pos: '',
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
  const interval = selectedPlan.interval === 'week' ? '/wk' : '/mo'

  function validateDetails(): boolean {
    if (!form.businessName.trim()) { setError('Business name is required'); return false }
    if (!form.ownerName.trim()) { setError('Owner name is required'); return false }
    if (!form.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) { setError('A valid email is required'); return false }
    return true
  }

  const buildProposalInput = useCallback((): ProposalInput | null => {
    if (!rep) return null
    const vertical = findVerticalBySlug(form.vertical)
    const deckUrl = vertical
      ? buildPersonalizedDeckUrl(
          vertical.slug,
          { name: rep.name, email: rep.email, phone: rep.phone },
          form.businessName || null,
        )
      : undefined
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
      checkoutUrl: checkoutUrl || undefined,
      verticalSlug: vertical?.slug,
      verticalTitle: vertical?.title,
      deckUrl,
    }
  }, [form, selectedPlan, setupFee, rep, checkoutUrl])

  async function handleGenerateProposal() {
    setShowProposal(true)
    setProposalGenerated(true)
  }

  async function handleDownloadPdf() {
    const input = buildProposalInput()
    if (!input) { setError('Please log in as a sales rep'); return }
    setGenerating(true)
    setError(null)
    try {
      await downloadProposalPdf(input)
    } catch (err: any) {
      setError(err.message || 'Failed to generate proposal PDF')
    } finally {
      setGenerating(false)
    }
  }

  async function handleCreateCheckout() {
    setCreatingCheckout(true)
    setError(null)
    try {
      const body = {
        org_id: orgId,
        monthly_amount_cents: form.customPrice ? parseInt(form.customPrice) * 100 : selectedPlan.price * 100,
        setup_fee_cents: setupFee * 100,
        first_month_free: form.firstMonthFree,
        business_name: form.businessName,
        currency: 'CAD',
      }

      const checkoutHeaders = await getAuthHeaders()
      const res = await fetch(`${API_URL}/api/stripe/subscribe-link`, {
        method: 'POST',
        headers: checkoutHeaders,
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Subscribe-link service unavailable' }))
        throw new Error(err.detail || `Server error ${res.status}`)
      }

      const data = await res.json()
      setCheckoutUrl(data.url)
      setCheckoutSessionId(data.token || '')
    } catch (err: any) {
      setError(err.message || 'Failed to create subscription link')
    } finally {
      setCreatingCheckout(false)
    }
  }

  const [customerLoginUrl, setCustomerLoginUrl] = useState('')
  const [customerPortalUrl, setCustomerPortalUrl] = useState('')
  const [customerTempPassword, setCustomerTempPassword] = useState('')
  const [tempPwCopied, setTempPwCopied] = useState(false)
  const [autoSendStatus, setAutoSendStatus] = useState<{ sms: boolean; email: boolean }>({ sms: false, email: false })

  async function handleCreateCustomer() {
    setSaving(true)
    setError(null)
    try {
      if (!form.email.trim()) {
        throw new Error('Customer email is required to create their login')
      }

      const token = generateToken()
      const apiUrl = import.meta.env.VITE_API_URL || ''

      const authHeaders = await getAuthHeaders()
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 30000)

      let provRes: Response
      try {
        provRes = await fetch(`${apiUrl}/api/onboarding/provision-customer`, {
          method: 'POST',
          headers: authHeaders,
          signal: controller.signal,
          body: JSON.stringify({
            org_id: orgId,
            email: form.email,
            phone: form.phone || null,
            owner_name: form.ownerName,
            business_name: form.businessName,
            plan: form.plan,
            monthly_price: price,
            setup_fee: setupFee,
            first_month_free: form.firstMonthFree,
            business_type: form.vertical || null,
            pos_provider: form.pos || null,
            rep_id: rep?.rep_id || null,
            rep_name: rep?.name || null,
          }),
        })
      } catch (fetchErr: any) {
        if (fetchErr.name === 'AbortError') {
          throw new Error('Request timed out. The server may be busy — please try again.')
        }
        throw new Error('Unable to reach the server. Check your connection and try again.')
      } finally {
        clearTimeout(timeout)
      }

      if (!provRes.ok) {
        const errBody = await provRes.json().catch(() => ({ detail: `Server error ${provRes.status}` }))
        throw new Error(errBody.detail || errBody.message || `Provisioning failed (${provRes.status})`)
      }

      const provData = await provRes.json()
      // The backend generates a temporary password, creates the auth user with it,
      // and emails it to the customer (Resend). Surface it here so the rep can also
      // share it directly. The customer is forced to reset it on first login.
      setCustomerTempPassword(provData.temporary_password || '')
      setCustomerLoginUrl(provData.login_url || `${window.location.origin}/canada/login`)
      setCustomerPortalUrl(provData.portal_url || '')

      if (supabase) {
        try {
          await supabase.from('canada_leads').insert({
            business_name: form.businessName,
            contact_name: form.ownerName,
            contact_email: form.email,
            contact_phone: form.phone || '',
            vertical: form.vertical || '',
            stage: 'closed_won',
            monthly_value: price,
            commission_rate: rep?.commission_rate ?? 70,
            notes: form.notes || `Plan: ${selectedPlan.label} at CA$${price}${interval}. Setup fee: CA$${setupFee}. First month free: ${form.firstMonthFree ? 'Yes' : 'No'}`,
            rep_id: rep?.rep_id || null,
          })
        } catch { }
      }

      const link = `${window.location.origin}/canada/onboard?token=${token}&biz=${encodeURIComponent(form.businessName)}&name=${encodeURIComponent(form.ownerName)}&email=${encodeURIComponent(form.email)}&phone=${encodeURIComponent(form.phone)}&plan=${encodeURIComponent(form.plan)}&price=${price}&rep=${encodeURIComponent(rep?.rep_id || '')}&rep_name=${encodeURIComponent(rep?.name || '')}`
      setOnboardingLink(link)

      // Reflect actual backend email delivery status. SMS is rep-initiated via the OS handler — no auto-send.
      setAutoSendStatus(s => ({ ...s, email: !!provData.welcome_email_sent }))

      setStep('confirm')
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

  async function copyCheckoutUrl() {
    try {
      await navigator.clipboard.writeText(checkoutUrl)
      setCopiedCheckout(true)
      setTimeout(() => setCopiedCheckout(false), 2000)
    } catch {
      setCopiedCheckout(true)
      setTimeout(() => setCopiedCheckout(false), 2000)
    }
  }

  function sendViaSms() {
    const msg = `Hey ${form.ownerName.split(' ')[0]}! Here's your Meridian setup link — takes about 3 minutes to get your analytics live: ${onboardingLink}`
    window.open(`sms:${form.phone}?body=${encodeURIComponent(msg)}`, '_blank')
  }

  // Grouped CAD verticals (43 total) — values are deck slugs (e.g. "ca-restaurant"),
  // matching the proposals catalog so the lead detail page can auto-link the right deck.
  const verticalGroups = verticalsByGroup()
  const selectedVertical = findVerticalBySlug(form.vertical)
  const stepLabels = ['Details', 'Plan', 'Price', 'Proposal', 'Confirm']
  const steps: Step[] = ['details', 'plan', 'customize', 'preview', 'confirm']
  const currentIdx = steps.indexOf(step)

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => {
            if (step === 'details') {
              const leadId = searchParams.get('lead')
              navigate(leadId ? `/canada/portal/leads/${leadId}` : '/canada/portal/leads')
            } else setStep(steps[currentIdx - 1])
          }}
          className="p-2 rounded-lg text-pm-canada-text-muted hover:text-white hover:bg-pm-canada-border transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-xl font-bold text-white">Generate Proposal</h1>
          <p className="text-xs text-pm-canada-text-muted">Create a branded proposal and checkout link for your customer</p>
        </div>
      </div>

      {/* Step Progress Indicator */}
      <div className="flex items-center justify-between mb-8 px-2">
        {stepLabels.map((label, i) => {
          const isActive = i === currentIdx
          const isDone = i < currentIdx
          return (
            <div key={label} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-300 ${
                    isDone
                      ? 'bg-pm-accent text-pm-canada-bg'
                      : isActive
                      ? 'border-2 border-pm-accent text-pm-accent'
                      : 'bg-pm-canada-border text-pm-canada-text-faint'
                  }`}
                >
                  {isDone ? <Check size={14} /> : i + 1}
                </div>
                <span className={`text-[9px] mt-1.5 font-medium ${
                  isActive ? 'text-white' : isDone ? 'text-pm-accent' : 'text-pm-canada-text-faint'
                }`}>
                  {label}
                </span>
              </div>
              {i < stepLabels.length - 1 && (
                <div className={`w-8 sm:w-12 h-[2px] mx-1 mt-[-14px] ${isDone ? 'bg-pm-accent' : 'bg-pm-canada-border'}`} />
              )}
            </div>
          )
        })}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm-tight">
          {error}
        </div>
      )}

      {/* ═══ STEP 1: Details ═══ */}
      {step === 'details' && (
        <div className="space-y-4">
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-canada-border space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Store size={16} className="text-pm-accent" />
              <h2 className="text-sm font-semibold text-white">Business Information</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-2xs font-medium text-pm-canada-text-muted mb-1.5">Business Name *</label>
                <input type="text" value={form.businessName} onChange={e => update('businessName', e.target.value)}
                  placeholder="e.g. Lucky Dragon Kitchen"
                  className="w-full px-3 py-2.5 text-sm-tight rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white placeholder-pm-canada-text-faint focus:border-pm-accent/50 focus:outline-none transition-colors" />
              </div>
              <div>
                <label className="block text-2xs font-medium text-pm-canada-text-muted mb-1.5">
                  Business Type
                  <span className="ml-1.5 text-2xs text-pm-canada-text-faint font-normal">(auto-links a proposal deck)</span>
                </label>
                <select
                  value={form.vertical}
                  onChange={e => update('vertical', e.target.value)}
                  className="w-full px-3 py-2.5 text-sm-tight rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white focus:border-pm-accent/50 focus:outline-none transition-colors"
                >
                  <option value="">Select industry…</option>
                  {verticalGroups.map(({ group, items }) => (
                    <optgroup key={group.key} label={group.label}>
                      {items.map(v => (
                        <option key={v.slug} value={v.slug}>{v.title}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
                {selectedVertical && (
                  <p className="mt-1.5 text-2xs text-pm-accent/80 leading-snug">
                    Deck linked: <span className="text-pm-accent font-medium">{selectedVertical.title}</span>
                    <span className="text-pm-canada-text-faint"> — {selectedVertical.blurb}</span>
                  </p>
                )}
              </div>
            </div>

            {/* POS question — plain qualification field only. Connecting the POS
                is done by the customer inside their own portal, never here. */}
            <div>
              <label className="block text-2xs font-medium text-pm-canada-text-muted mb-1.5">What POS do they currently run? (optional)</label>
              <select
                value={form.pos || ''}
                onChange={e => update('pos', e.target.value)}
                className="w-full px-3 py-2.5 text-sm-tight rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white focus:border-pm-accent/50 focus:outline-none transition-colors"
              >
                <option value="">Not sure / ask later</option>
                {posSystems.map(s => (
                  <option key={s.key} value={s.key}>{s.name}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 mt-6 mb-2">
              <User size={16} className="text-pm-accent" />
              <h2 className="text-sm font-semibold text-white">Owner Contact</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-2xs font-medium text-pm-canada-text-muted mb-1.5">Owner Name *</label>
                <input type="text" value={form.ownerName} onChange={e => update('ownerName', e.target.value)}
                  placeholder="e.g. James Chen"
                  className="w-full px-3 py-2.5 text-sm-tight rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white placeholder-pm-canada-text-faint focus:border-pm-accent/50 focus:outline-none transition-colors" />
              </div>
              <div>
                <label className="block text-2xs font-medium text-pm-canada-text-muted mb-1.5">Email *</label>
                <input type="email" value={form.email} onChange={e => update('email', e.target.value)}
                  placeholder="james@luckydragon.com"
                  className="w-full px-3 py-2.5 text-sm-tight rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white placeholder-pm-canada-text-faint focus:border-pm-accent/50 focus:outline-none transition-colors" />
              </div>
              <div>
                <label className="block text-2xs font-medium text-pm-canada-text-muted mb-1.5">Phone</label>
                <input type="tel" value={form.phone} onChange={e => update('phone', e.target.value)}
                  placeholder="(555) 234-5678"
                  className="w-full px-3 py-2.5 text-sm-tight rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white placeholder-pm-canada-text-faint focus:border-pm-accent/50 focus:outline-none transition-colors" />
              </div>
            </div>
            <div className="mt-2">
              <label className="block text-2xs font-medium text-pm-canada-text-muted mb-1.5">Notes (optional)</label>
              <textarea value={form.notes} onChange={e => update('notes', e.target.value)}
                placeholder="Any notes about this business..."
                rows={2}
                className="w-full px-3 py-2.5 text-sm-tight rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white placeholder-pm-canada-text-faint focus:border-pm-accent/50 focus:outline-none transition-colors resize-none" />
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={() => validateDetails() && setStep('plan')}
              className="flex items-center gap-2 px-6 py-2.5 text-sm-tight font-medium text-pm-canada-bg bg-pm-accent rounded-lg hover:bg-pm-accent transition-colors">
              Next: Select Plan <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ STEP 2: Plan ═══ */}
      {step === 'plan' && (
        <div className="space-y-4">
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-canada-border">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles size={16} className="text-pm-accent" />
              <h2 className="text-sm font-semibold text-white">Select Plan for {form.businessName}</h2>
            </div>
            <div className="grid gap-3">
              {PLAN_TIERS.map(plan => (
                <button key={plan.id} onClick={() => update('plan', plan.id)}
                  className={`p-4 rounded-xl border text-left transition-all duration-200 ${
                    form.plan === plan.id
                      ? 'border-pm-accent/50 bg-pm-accent/5'
                      : 'border-pm-canada-border hover:border-pm-canada-text-faint bg-pm-canada-bg'
                  }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-white">{plan.label}</p>
                        {plan.tag && (
                          <span className="text-2xs px-2 py-0.5 bg-pm-accent text-pm-canada-bg font-semibold rounded">
                            {plan.tag}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-pm-canada-text-muted mt-0.5">{(plan.features || []).slice(0, 3).join(' · ')}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-white">CA${plan.price}</p>
                      <p className="text-2xs text-pm-canada-text-muted">{plan.interval === 'week' ? '/week' : '/month'}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep('details')}
              className="flex items-center gap-2 px-4 py-2.5 text-sm-tight font-medium text-pm-canada-text-muted hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('customize')}
              className="flex items-center gap-2 px-6 py-2.5 text-sm-tight font-medium text-pm-canada-bg bg-pm-accent rounded-lg hover:bg-pm-accent transition-colors">
              Next: Customize <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ STEP 3: Customize ═══ */}
      {step === 'customize' && (
        <div className="space-y-4">
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-canada-border">
            <div className="flex items-center gap-2 mb-4">
              <DollarSign size={16} className="text-pm-accent" />
              <h2 className="text-sm font-semibold text-white">Customize Pricing</h2>
            </div>

            <div className="p-4 rounded-xl border border-pm-accent/20 bg-pm-accent/5 mb-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm-tight font-semibold text-white">{selectedPlan.label} Plan</p>
                  <p className="text-2xs text-pm-canada-text-muted">{(selectedPlan.features || []).length} features included</p>
                </div>
                <p className="text-lg font-bold text-pm-accent">CA${selectedPlan.price}{interval}</p>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-2xs font-medium text-pm-canada-text-muted mb-1.5">Custom Monthly Price (optional override)</label>
              <div className="relative">
                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-pm-canada-text-faint" />
                <input type="number" value={form.customPrice}
                  onChange={e => update('customPrice', e.target.value)}
                  placeholder={selectedPlan.price.toString()}
                  className="w-full pl-8 pr-3 py-2.5 text-sm-tight rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white placeholder-pm-canada-text-faint focus:border-pm-accent/50 focus:outline-none transition-colors" />
              </div>
              <p className="text-2xs text-pm-canada-text-faint mt-1">All amounts in CAD</p>
            </div>

            <div className="mb-4">
              <label className="block text-2xs font-medium text-pm-canada-text-muted mb-1.5">
                Setup Fee <span className="text-pm-accent">(you keep 100%)</span>
              </label>
              <div className="relative">
                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-pm-canada-text-faint" />
                <input type="number" value={form.setupFee}
                  onChange={e => update('setupFee', e.target.value)}
                  placeholder="0"
                  className="w-full pl-8 pr-3 py-2.5 text-sm-tight rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white placeholder-pm-canada-text-faint focus:border-pm-accent/50 focus:outline-none transition-colors" />
              </div>
              <p className="text-2xs text-pm-accent/60 mt-1">Custom amount — goes directly to you</p>
            </div>

            <div className="flex items-center justify-between p-4 rounded-xl border border-pm-canada-border bg-pm-canada-bg">
              <div className="flex items-center gap-3">
                <Gift size={18} className={form.firstMonthFree ? 'text-pm-accent' : 'text-pm-canada-text-faint'} />
                <div>
                  <p className="text-sm-tight font-semibold text-white">First Month Free</p>
                  <p className="text-2xs text-pm-canada-text-muted">Waive month 1 subscription — great for closing hesitant prospects</p>
                </div>
              </div>
              <button
                onClick={() => update('firstMonthFree', !form.firstMonthFree)}
                className={`relative w-12 h-6 rounded-full transition-colors duration-200 ${
                  form.firstMonthFree ? 'bg-pm-accent' : 'bg-pm-canada-border'
                }`}
              >
                <div className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform duration-200 ${
                  form.firstMonthFree ? 'translate-x-6' : ''
                }`} />
              </button>
            </div>
          </div>

          {/* Summary */}
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-accent/20">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 size={16} className="text-pm-accent" />
              <h2 className="text-sm font-semibold text-white">Proposal Summary</h2>
            </div>
            <div className="space-y-2 text-sm-tight">
              <div className="flex justify-between py-2 border-b border-pm-canada-border">
                <span className="text-pm-canada-text-muted">Business</span>
                <span className="text-white font-medium">{form.businessName}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-pm-canada-border">
                <span className="text-pm-canada-text-muted">Plan</span>
                <span className="text-white font-medium">{selectedPlan.label} — CA${price}{interval}</span>
              </div>
              {setupFee > 0 && (
                <div className="flex justify-between py-2 border-b border-pm-canada-border">
                  <span className="text-pm-canada-text-muted">Setup Fee <span className="text-pm-accent">(yours)</span></span>
                  <span className="text-pm-accent font-medium">CA${setupFee}</span>
                </div>
              )}
              {form.firstMonthFree && (
                <div className="flex justify-between py-2 border-b border-pm-canada-border">
                  <span className="text-pm-canada-text-muted">First Month</span>
                  <span className="text-pm-purple font-medium">FREE</span>
                </div>
              )}
              <div className="flex justify-between py-3">
                <span className="text-pm-canada-text-muted font-medium">Due Today</span>
                <span className="text-lg font-bold text-pm-accent">CA${dueToday.toLocaleString()}</span>
              </div>
            </div>
            {rep && (
              <div className="mt-3 pt-3 border-t border-pm-canada-border">
                <p className="text-2xs text-pm-canada-text-muted">
                  Rep: <span className="text-white font-medium">{rep.name}</span>
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep('plan')}
              className="flex items-center gap-2 px-4 py-2.5 text-sm-tight font-medium text-pm-canada-text-muted hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('preview')}
              className="flex items-center gap-2 px-6 py-2.5 text-sm-tight font-medium text-pm-canada-bg bg-pm-accent rounded-lg hover:bg-pm-accent transition-colors">
              Next: Generate <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ STEP 4: Preview & Generate ═══ */}
      {step === 'preview' && (
        <div className="space-y-4">
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-canada-border">
            <div className="flex items-center gap-2 mb-4">
              <Eye size={16} className="text-pm-accent" />
              <h2 className="text-sm font-semibold text-white">Proposal Ready</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm-tight">
              <div className="p-3 rounded-lg bg-pm-canada-bg border border-pm-canada-border">
                <div className="text-2xs text-pm-canada-text-faint uppercase tracking-wider mb-1">Business</div>
                <div className="text-white font-medium">{form.businessName}</div>
              </div>
              <div className="p-3 rounded-lg bg-pm-canada-bg border border-pm-canada-border">
                <div className="text-2xs text-pm-canada-text-faint uppercase tracking-wider mb-1">Owner</div>
                <div className="text-white font-medium">{form.ownerName}</div>
              </div>
              <div className="p-3 rounded-lg bg-pm-canada-bg border border-pm-canada-border">
                <div className="text-2xs text-pm-canada-text-faint uppercase tracking-wider mb-1">Plan</div>
                <div className="text-pm-accent font-medium">{selectedPlan.label} — CA${price}{interval}</div>
              </div>
              <div className="p-3 rounded-lg bg-pm-canada-bg border border-pm-canada-border">
                <div className="text-2xs text-pm-canada-text-faint uppercase tracking-wider mb-1">Due Today</div>
                <div className="text-pm-accent font-medium">CA${dueToday.toLocaleString()}</div>
              </div>
            </div>
          </div>

          {/* Checkout Link section */}
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-canada-border">
            <div className="flex items-center gap-2 mb-4">
              <QrCode size={16} className="text-pm-purple" />
              <h2 className="text-sm font-semibold text-white">Monthly Subscription Link</h2>
            </div>

            {!checkoutUrl ? (
              <div>
                <p className="text-xs text-pm-canada-text-muted mb-3">
                  Generate a unique Stripe subscription link for this customer. Includes the {selectedPlan.label} plan
                  {setupFee > 0 ? ` + CA$${setupFee} setup fee` : ''}
                  {form.firstMonthFree ? ' with first month free' : ''}. All amounts in CAD.
                </p>
                <button
                  onClick={handleCreateCheckout}
                  disabled={creatingCheckout}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 text-sm-tight font-medium text-white bg-pm-purple rounded-lg hover:bg-[#6b2fd4] disabled:opacity-50 transition-colors"
                >
                  {creatingCheckout ? (
                    <><Loader2 size={14} className="animate-spin" /> Creating Subscription Link...</>
                  ) : (
                    <><QrCode size={14} /> Generate Subscription Link & QR Code</>
                  )}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-sm-tight text-pm-accent">
                  <CheckCircle2 size={14} /> Checkout session created!
                </div>
                <div className="flex justify-center">
                  <div className="relative p-4 bg-white rounded-xl">
                    <img
                      src={generateQrSvg(checkoutUrl, 200)}
                      alt="Checkout QR Code"
                      className="w-[200px] h-[200px]"
                      crossOrigin="anonymous"
                    />
                  </div>
                </div>
                <p className="text-center text-2xs text-pm-canada-text-muted">
                  Customer scans to start their Monthly Subscription — {selectedPlan.label} CA${price}{interval}
                  {setupFee > 0 ? ` + CA$${setupFee} setup` : ''}
                  {form.firstMonthFree ? ' · 30-day free trial' : ''}
                </p>
                <div className="flex gap-2">
                  <input type="text" value={checkoutUrl} readOnly
                    className="flex-1 px-3 py-2.5 text-2xs rounded-lg bg-pm-canada-bg border border-pm-canada-border text-pm-canada-text-muted font-mono truncate" />
                  <button onClick={copyCheckoutUrl}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium rounded-lg border transition-all duration-200 ${
                      copiedCheckout ? 'bg-pm-accent/10 border-pm-accent/30 text-pm-accent' : 'bg-pm-canada-border border-pm-canada-border text-white hover:bg-pm-canada-surface'
                    }`}>
                    {copiedCheckout ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                    {copiedCheckout ? 'Copied!' : 'Copy'}
                  </button>
                  <a href={checkoutUrl} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium rounded-lg border border-pm-canada-border bg-pm-canada-border text-white hover:bg-pm-canada-surface transition-colors">
                    <ExternalLink size={14} />
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* Generate Proposal Button */}
          <div className="grid grid-cols-1 gap-3">
            <button
              onClick={handleGenerateProposal}
              className="flex items-center justify-center gap-2 px-6 py-4 text-sm font-semibold text-pm-canada-bg bg-gradient-to-r from-pm-accent to-pm-purple rounded-xl hover:opacity-90 transition-all"
            >
              <Eye size={18} /> View Proposal (8 Slides)
            </button>

            {proposalGenerated && (
              <button
                onClick={handleDownloadPdf}
                disabled={generating}
                className="flex items-center justify-center gap-2 px-6 py-3 text-sm-tight font-medium text-white border border-pm-canada-border rounded-xl hover:bg-pm-canada-surface transition-all disabled:opacity-50"
              >
                {generating ? (
                  <><Loader2 size={14} className="animate-spin" /> Generating PDF...</>
                ) : (
                  <><FileDown size={14} /> Download as PDF</>
                )}
              </button>
            )}
          </div>

          {/* Create Account */}
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-canada-border">
            <div className="flex items-center gap-2 mb-4">
              <Send size={16} className="text-pm-accent" />
              <h2 className="text-sm font-semibold text-white">Create Account & Send Onboarding Link</h2>
            </div>

            {!onboardingLink ? (
              <button
                onClick={handleCreateCustomer}
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 text-sm-tight font-medium bg-pm-accent text-pm-canada-bg rounded-lg hover:bg-pm-accent disabled:opacity-50 transition-colors"
              >
                {saving ? <><Loader2 size={14} className="animate-spin" /> Creating...</> : <><CheckCircle2 size={14} /> Create Customer & Generate Link</>}
              </button>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm-tight text-pm-accent">
                  <CheckCircle2 size={14} /> Customer account created!
                </div>

                <div className="p-4 rounded-xl border border-pm-accent/20 bg-pm-accent/5 space-y-2">
                  <p className="text-2xs font-mono text-pm-accent tracking-wider">CUSTOMER ACCOUNT</p>
                  <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm-tight">
                    <span className="text-pm-canada-text-muted">Email:</span>
                    <span className="text-white font-medium font-mono">{form.email}</span>
                    <span className="text-pm-canada-text-muted">Login:</span>
                    <a href={customerLoginUrl} target="_blank" rel="noopener noreferrer" className="text-pm-accent font-mono hover:underline truncate">{customerLoginUrl}</a>
                    {customerTempPassword && (
                      <>
                        <span className="text-pm-canada-text-muted">Temp password:</span>
                        <span className="flex items-center gap-2">
                          <span className="text-white font-medium font-mono">{customerTempPassword}</span>
                          <button type="button" onClick={() => { navigator.clipboard.writeText(customerTempPassword); setTempPwCopied(true); setTimeout(() => setTempPwCopied(false), 2000) }}
                            className="text-2xs text-pm-accent hover:underline">{tempPwCopied ? 'Copied!' : 'Copy'}</button>
                        </span>
                      </>
                    )}
                  </div>
                  <p className="text-2xs text-pm-canada-text-muted mt-2">A welcome email with these credentials has been sent to the customer. They can also use the temp password above to sign in — they'll be prompted to set their own password on first login.</p>
                </div>

                <div className="space-y-1.5">
                  <p className="text-2xs font-mono text-pm-canada-text-muted tracking-wider">ONBOARDING LINK</p>
                  <div className="flex gap-2">
                    <input type="text" value={onboardingLink} readOnly
                      className="flex-1 px-3 py-2.5 text-xs rounded-lg bg-pm-canada-bg border border-pm-canada-border text-pm-canada-text-muted font-mono truncate" />
                    <button onClick={copyLink}
                      className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium rounded-lg border transition-all duration-200 ${
                        copied ? 'bg-pm-accent/10 border-pm-accent/30 text-pm-accent' : 'bg-pm-canada-border border-pm-canada-border text-white hover:bg-pm-canada-surface'
                      }`}>
                      {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <button onClick={sendViaSms}
                    className="flex items-center justify-center gap-2 px-4 py-3 text-sm-tight font-medium text-pm-canada-bg bg-pm-accent rounded-lg hover:bg-pm-accent transition-colors">
                    <Phone size={14} /> Text to Customer
                  </button>
                  <button onClick={() => {
                    const subject = `Your Meridian Account is Ready!`
                    const body = `Hi ${form.ownerName.split(' ')[0]},\n\nYour Meridian analytics account is set up!\n\nEmail: ${form.email}\nLogin: ${customerLoginUrl}${customerTempPassword ? `\nTemporary password: ${customerTempPassword}` : ''}\n\nSign in with the temporary password above — you'll be prompted to set your own password on first login.\n\n${checkoutUrl ? `To activate your subscription, complete your payment here:\n${checkoutUrl}\n\n` : ''}You'll connect your POS and your dashboard will start lighting up with insights.\n\nAll amounts in CAD.\n\nLet me know if you have any questions!\n\n${rep?.name || 'Your Meridian Rep'}${rep?.phone ? '\n' + rep.phone : ''}`
                    window.open(`mailto:${form.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, '_blank')
                  }}
                    className="flex items-center justify-center gap-2 px-4 py-3 text-sm-tight font-medium text-white bg-pm-canada-border rounded-lg hover:bg-pm-canada-surface border border-pm-canada-border transition-colors">
                    <Mail size={14} /> Email to Customer
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep('customize')}
              className="flex items-center gap-2 px-4 py-2.5 text-sm-tight font-medium text-pm-canada-text-muted hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => {
              setForm({ businessName: '', ownerName: '', email: '', phone: '', vertical: '', pos: '', plan: 'premium', customPrice: '', setupFee: '', firstMonthFree: false, notes: '' })
              setStep('details')
              setOnboardingLink('')
              setCustomerLoginUrl('')
              setCustomerPortalUrl('')
              setCustomerTempPassword('')
              setTempPwCopied(false)
              setAutoSendStatus({ sms: false, email: false })
              setProposalGenerated(false)
              setShowProposal(false)
              setCheckoutUrl('')
              setCheckoutSessionId('')
            }}
              className="text-xs text-pm-accent hover:text-white transition-colors">
              + Create Another Proposal
            </button>
          </div>
        </div>
      )}

      {/* ═══ STEP 5: Confirmation & SOP Checklist ═══ */}
      {step === 'confirm' && (
        <div className="space-y-4">
          {/* Success Banner */}
          <div className="bg-pm-accent/5 rounded-xl p-6 border border-pm-accent/20">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-pm-accent flex items-center justify-center">
                <CheckCircle2 size={20} className="text-pm-canada-bg" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Customer Created Successfully</h2>
                <p className="text-xs text-pm-canada-text-muted">{form.businessName} — {form.ownerName}</p>
              </div>
            </div>
          </div>

          {/* SOP Checklist */}
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-canada-border">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 size={16} className="text-pm-accent" />
              <h2 className="text-sm font-semibold text-white">Onboarding SOP Checklist</h2>
            </div>
            <div className="space-y-3">
              {[
                { label: 'Account created in system', done: true },
                { label: 'Credentials email sent', done: autoSendStatus.email },
                { label: 'SMS notification sent', done: autoSendStatus.sms, skip: !form.phone.trim() },
                { label: 'Checkout/payment link generated', done: !!checkoutUrl },
                { label: 'Proposal shown to customer', done: proposalGenerated },
                { label: 'POS system selected', done: !!form.pos },
              ].filter(item => !('skip' in item && item.skip)).map(item => (
                <div key={item.label} className="flex items-center gap-3 py-2 px-3 rounded-lg bg-pm-canada-bg border border-pm-canada-border">
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                    item.done ? 'bg-pm-accent' : 'border-2 border-pm-canada-text-faint'
                  }`}>
                    {item.done && <Check size={12} className="text-pm-canada-bg" />}
                  </div>
                  <span className={`text-sm-tight ${item.done ? 'text-white' : 'text-pm-canada-text-muted'}`}>{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Customer Portal URL */}
          {customerPortalUrl && (
            <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-purple/30">
              <p className="text-2xs font-mono text-pm-purple tracking-wider mb-2">EXCLUSIVE CUSTOMER PORTAL URL</p>
              <p className="text-2xs text-pm-canada-text-muted mb-3">This is their unique, secure portal link. Share this with the customer.</p>
              <div className="flex gap-2">
                <input type="text" value={customerPortalUrl} readOnly
                  className="flex-1 px-3 py-2.5 text-xs rounded-lg bg-pm-canada-bg border border-pm-canada-border text-white font-mono truncate" />
                <button onClick={() => { navigator.clipboard.writeText(customerPortalUrl); }}
                  className="flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium rounded-lg border border-pm-purple/30 bg-pm-purple/10 text-pm-purple hover:bg-pm-purple/20 transition-colors">
                  <Copy size={14} /> Copy
                </button>
              </div>
            </div>
          )}

          {/* Customer Account Card */}
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-accent/20">
            <p className="text-2xs font-mono text-pm-accent tracking-wider mb-3">CUSTOMER ACCOUNT</p>
            <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-sm-tight">
              <span className="text-pm-canada-text-muted">Email:</span>
              <span className="text-white font-medium font-mono">{form.email}</span>
              <span className="text-pm-canada-text-muted">Login:</span>
              <a href={customerLoginUrl} target="_blank" rel="noopener noreferrer" className="text-pm-accent font-mono hover:underline truncate">{customerLoginUrl}</a>
              {customerTempPassword && (
                <>
                  <span className="text-pm-canada-text-muted">Temp password:</span>
                  <span className="flex items-center gap-2">
                    <span className="text-white font-medium font-mono">{customerTempPassword}</span>
                    <button type="button" onClick={() => { navigator.clipboard.writeText(customerTempPassword); setTempPwCopied(true); setTimeout(() => setTempPwCopied(false), 2000) }}
                      className="text-2xs text-pm-accent hover:underline">{tempPwCopied ? 'Copied!' : 'Copy'}</button>
                  </span>
                </>
              )}
            </div>
            <p className="text-2xs text-pm-canada-text-muted mt-3">A welcome email with these credentials has been sent. The customer signs in with the temp password and is prompted to set their own on first login.</p>
          </div>

          {/* Setup-link step — the customer completes setup (including POS
              connection) inside their OWN portal; the rep only sends the link. */}
          <div className="bg-pm-canada-surface rounded-xl p-6 border border-pm-canada-border">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} className="text-pm-purple" />
              <h2 className="text-sm font-semibold text-white">Next: Send Their Setup Link</h2>
            </div>
            <p className="text-xs text-pm-canada-text-muted mb-4">
              The customer completes setup — including connecting their POS — from their own
              portal. Getting them to open this link the same day is the #1 factor in activation success.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => {
                  const url = `${window.location.origin}/canada/onboard?token=${onboardingLink.split('token=')[1]?.split('&')[0] || ''}&biz=${encodeURIComponent(form.businessName)}&name=${encodeURIComponent(form.ownerName)}&email=${encodeURIComponent(form.email)}&phone=${encodeURIComponent(form.phone)}&plan=${encodeURIComponent(form.plan)}&price=${price}&rep=${encodeURIComponent(rep?.rep_id || '')}&rep_name=${encodeURIComponent(rep?.name || '')}`
                  window.open(url, '_blank')
                }}
                className="flex items-center justify-center gap-2 px-4 py-3 text-sm-tight font-medium text-pm-canada-bg bg-pm-accent rounded-lg hover:bg-pm-accent transition-colors"
              >
                <ExternalLink size={14} /> Open Their Setup Wizard
              </button>
              <button
                onClick={() => {
                  if (form.phone) {
                    const msg = `Hey ${form.ownerName.split(' ')[0]}! Your Meridian setup link — takes 3 min: ${onboardingLink}`
                    window.open(`sms:${form.phone}?body=${encodeURIComponent(msg)}`, '_blank')
                  } else {
                    const subject = `Connect your POS to Meridian`
                    const body = `Hi ${form.ownerName.split(' ')[0]},\n\nHere's your setup link to connect your POS and activate analytics:\n${onboardingLink}\n\nTakes about 3 minutes!\n\n${rep?.name || 'Your Meridian Rep'}`
                    window.open(`mailto:${form.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, '_blank')
                  }
                }}
                className="flex items-center justify-center gap-2 px-4 py-3 text-sm-tight font-medium text-white bg-pm-canada-border rounded-lg hover:bg-pm-canada-surface border border-pm-canada-border transition-colors"
              >
                <Send size={14} /> Send Setup Link
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-between pt-2">
            <button onClick={() => navigate('/canada/portal/leads')}
              className="flex items-center gap-2 px-4 py-2.5 text-sm-tight font-medium text-pm-canada-text-muted hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back to Leads
            </button>
            <button onClick={() => {
              setForm({ businessName: '', ownerName: '', email: '', phone: '', vertical: '', pos: '', plan: 'premium', customPrice: '', setupFee: '', firstMonthFree: false, notes: '' })
              setStep('details')
              setOnboardingLink('')
              setCustomerLoginUrl('')
              setCustomerPortalUrl('')
              setProposalGenerated(false)
              setShowProposal(false)
              setCheckoutUrl('')
              setCheckoutSessionId('')
              setAutoSendStatus({ sms: false, email: false })
            }}
              className="flex items-center gap-2 px-6 py-2.5 text-sm-tight font-medium text-pm-canada-bg bg-pm-accent rounded-lg hover:bg-pm-accent transition-colors">
              <Store size={14} /> Create Another Customer
            </button>
          </div>
        </div>
      )}

      {/* ═══ Proposal Overlay ═══ */}
      <ProposalOverlay
        open={showProposal}
        onClose={() => setShowProposal(false)}
        businessName={form.businessName}
        ownerName={form.ownerName}
        plan={selectedPlan}
        price={price}
        setupFee={setupFee}
        firstMonthFree={form.firstMonthFree}
        repName={rep?.name || ''}
        repEmail={rep?.email || ''}
        repPhone={rep?.phone || undefined}
        checkoutUrl={checkoutUrl}
        onDownloadPdf={handleDownloadPdf}
        verticalTitle={selectedVertical?.title}
        deckUrl={
          selectedVertical
            ? `${DECK_BASE_URL}/${selectedVertical.slug}` +
              (rep?.name || rep?.email || form.businessName
                ? `?${new URLSearchParams({
                    ...(rep?.name ? { rep: rep.name } : {}),
                    ...(rep?.email ? { email: rep.email } : {}),
                    ...(rep?.phone ? { phone: rep.phone } : {}),
                    ...(form.businessName ? { business: form.businessName } : {}),
                  }).toString()}`
                : '')
            : undefined
        }
      />
    </div>
  )
}
