import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, CheckCircle2, Copy, Send, Check,
  Store, User, Mail, Phone, DollarSign, FileDown,
  Loader2, Eye, Gift, Sparkles, QrCode, ExternalLink, X,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import POSSystemPicker from '@/components/POSSystemPicker'
import { supabase } from '@/lib/supabase'
import { PLAN_TIERS, getPlan, type PlanTier } from '@/lib/canada-proposal-plans'
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
    <div className="fixed inset-0 z-[9999] bg-[#0a0f0d]">
      {/* Close button */}
      <button
        onClick={onClose}
        className="fixed top-4 right-4 z-[10001] w-10 h-10 rounded-full bg-[#1a2420] border border-[#1a2420] flex items-center justify-center text-white hover:bg-[#0f1512] transition-colors"
      >
        <X size={18} />
      </button>

      {/* Download PDF button */}
      <button
        onClick={onDownloadPdf}
        className="fixed top-4 right-16 z-[10001] px-3 py-2 rounded-lg bg-[#1a2420] border border-[#1a2420] flex items-center gap-2 text-[11px] text-[#6b7a74] hover:text-[#00d4aa] transition-colors"
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
              i === currentSlide ? 'bg-[#00d4aa] scale-125' : 'bg-[#1a2420] hover:bg-[#4a5550]'
            }`}
          />
        ))}
      </div>

      {/* Slide counter */}
      <div className="fixed bottom-4 right-4 z-[10001] text-[11px] font-mono text-[#4a5550]">
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
            <p className="text-[11px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-8">
              MERIDIAN CANADA · PROPOSAL (CAD)
            </p>
            <p className="text-[15px] text-[#6b7a74] italic font-serif mb-2">Prepared for</p>
            <h1 className="text-4xl sm:text-6xl font-bold text-white leading-tight">{businessName}</h1>
            <div className="mt-8 space-y-1">
              <p className="text-[13px] text-[#6b7a74]">{today}</p>
              <p className="text-[13px] text-[#6b7a74]">{ownerName} · {repEmail}</p>
            </div>
          </div>
        </div>

        {/* ═══ SLIDE 2: Features ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-[11px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-4">WHAT YOU GET</p>
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
              <div key={f.title} className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
                <div className="text-2xl mb-3">{f.icon}</div>
                <h3 className="text-[14px] font-semibold text-white mb-1">{f.title}</h3>
                <p className="text-[12px] text-[#6b7a74] leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ SLIDE 3: Plan Details ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-[11px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-4">YOUR PLAN</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-10">Meridian {plan.label}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="bg-[#0f1512] border border-[#00d4aa]/20 rounded-xl p-6">
              <p className="text-[11px] font-mono text-[#00d4aa] tracking-wider mb-4">WHAT'S INCLUDED</p>
              <div className="space-y-3">
                {plan.features.map(f => (
                  <div key={f} className="flex items-start gap-2">
                    <CheckCircle2 size={14} className="text-[#00d4aa] mt-0.5 flex-shrink-0" />
                    <span className="text-[13px] text-white">{f}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-6">
              <p className="text-[11px] font-mono text-[#7c3aed] tracking-wider mb-4">ALSO BUILT IN</p>
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
                    <CheckCircle2 size={14} className="text-[#7c3aed] mt-0.5 flex-shrink-0" />
                    <span className="text-[13px] text-white">{f}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ═══ SLIDE 4: POS Analytics ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-[11px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-4">POS ANALYTICS ENGINE</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-10">Your Sales Data, Decoded</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                icon: '📊', title: 'Revenue Intelligence', color: '#00d4aa',
                desc: 'Track hourly, daily, weekly revenue. Spot slow days before they drain cash.',
                example: '"Tuesday lunch dropped 18% vs 4-week avg."',
              },
              {
                icon: '🧮', title: 'Menu Engineering', color: '#7c3aed',
                desc: 'Every item classified as Star, Plow Horse, Puzzle, or Dog.',
                example: '"Acai bowl has 62% margin but only 3% orders. Move to position #2."',
              },
              {
                icon: '🔮', title: 'Predictive Forecasting', color: '#00d4aa',
                desc: 'AI predicts tomorrow\'s sales with 90%+ accuracy. Auto-suggested prep lists.',
                example: '"Friday predicted: $4,280 (+12%). Recommend 2 extra staff 11am-2pm."',
              },
            ].map(card => (
              <div key={card.title} className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
                <div className="text-2xl mb-3">{card.icon}</div>
                <h3 className="text-[14px] font-semibold mb-2" style={{ color: card.color }}>{card.title}</h3>
                <p className="text-[12px] text-[#6b7a74] leading-relaxed mb-3">{card.desc}</p>
                <div className="bg-[#0a0f0d] border border-[#1a2420] rounded-lg p-3">
                  <p className="text-[10px] font-mono text-[#4a5550] mb-1">EXAMPLE INSIGHT</p>
                  <p className="text-[11px] text-white italic">{card.example}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ SLIDE 5: Value / ROI ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-[11px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-4">YOUR INVESTMENT</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-10">Simple, Transparent Pricing</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="bg-[#0f1512] border border-[#00d4aa]/20 rounded-xl p-6">
              <p className="text-[11px] font-mono text-[#00d4aa] tracking-wider mb-4">MERIDIAN {plan.label.toUpperCase()}</p>
              <div className="flex items-baseline gap-2 mb-6">
                <span className="text-4xl font-bold text-white font-mono">CA${price}</span>
                <span className="text-[14px] text-[#6b7a74]">{interval}</span>
              </div>
              <div className="space-y-2">
                {plan.features.map(f => (
                  <div key={f} className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#00d4aa]" />
                    <span className="text-[12px] text-[#6b7a74]">{f}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-6">
              <p className="text-[11px] font-mono text-[#7c3aed] tracking-wider mb-4">ORDER SUMMARY</p>
              <div className="space-y-3">
                <div className="flex justify-between py-2 border-b border-[#1a2420]">
                  <span className="text-[13px] text-[#6b7a74]">{plan.label} Plan</span>
                  <span className="text-[13px] text-white font-medium">CA${price}{interval}</span>
                </div>
                {setupFee > 0 && (
                  <div className="flex justify-between py-2 border-b border-[#1a2420]">
                    <span className="text-[13px] text-[#6b7a74]">Setup Fee</span>
                    <span className="text-[13px] text-white font-medium">CA${setupFee}</span>
                  </div>
                )}
                {firstMonthFree && (
                  <div className="flex justify-between py-2 border-b border-[#1a2420]">
                    <span className="text-[13px] text-[#6b7a74]">First Month</span>
                    <span className="text-[13px] text-[#7c3aed] font-medium">FREE</span>
                  </div>
                )}
                <div className="flex justify-between py-3 mt-2">
                  <span className="text-[14px] text-white font-semibold">Due Today</span>
                  <span className="text-2xl font-bold text-[#00d4aa] font-mono">CA${dueToday}</span>
                </div>
              </div>
              {/* Monthly value viz */}
              <div className="mt-4 bg-[#0a0f0d] rounded-lg p-4 border border-[#1a2420]">
                <p className="text-[10px] font-mono text-[#4a5550] mb-2">MONTHLY VALUE</p>
                <div className="w-full h-3 bg-[#1a2420] rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-[#00d4aa] to-[#7c3aed] rounded-full" style={{ width: '75%' }} />
                </div>
                <p className="text-[10px] text-[#6b7a74] mt-1">Avg. client sees 3-5x return in operational savings</p>
              </div>
            </div>
          </div>
        </div>

        {/* ═══ SLIDE 6: Camera Intelligence ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-[11px] font-mono tracking-[0.2em] text-[#7c3aed] uppercase mb-4">CAMERA INTELLIGENCE</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">POS + Camera = Meridian Insight</h2>
          <p className="text-[14px] text-[#6b7a74] mb-8 max-w-2xl">
            When we combine what your register knows with what the camera sees, you get insights no one else in your market has.
          </p>
          {/* Equation style */}
          <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6 mb-8">
            <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 flex-1 text-center">
              <p className="text-2xl mb-2">📷</p>
              <p className="text-[13px] font-semibold text-white">Camera Feed</p>
              <p className="text-[11px] text-[#6b7a74]">Foot traffic, dwell time, queue length</p>
            </div>
            <span className="text-2xl font-bold text-[#7c3aed]">+</span>
            <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 flex-1 text-center">
              <p className="text-2xl mb-2">💳</p>
              <p className="text-[13px] font-semibold text-white">POS Data</p>
              <p className="text-[11px] text-[#6b7a74]">Sales, tickets, items, timing</p>
            </div>
            <span className="text-2xl font-bold text-[#00d4aa]">=</span>
            <div className="bg-gradient-to-br from-[#7c3aed]/10 to-[#00d4aa]/10 border border-[#7c3aed]/30 rounded-xl p-5 flex-1 text-center">
              <p className="text-2xl mb-2">🧠</p>
              <p className="text-[13px] font-semibold text-[#00d4aa]">Meridian Insight</p>
              <p className="text-[11px] text-[#6b7a74]">Conversion rate, revenue per visitor, optimization</p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              'Foot traffic up but revenue flat? Conversion dropped — train staff on upsells.',
              'Long lines at noon? Open register 2 from 11:45am. Recover $2,380/week.',
              'Customers linger at display but don\'t buy? Try samples or price drop.',
              'Faster greeting = 47% higher ticket. Train all staff on top performer\'s flow.',
            ].map((insight, i) => (
              <div key={i} className="bg-[#0f1512] border border-[#1a2420] rounded-lg p-3 flex items-start gap-2">
                <span className="text-[#00d4aa] text-[11px] mt-0.5">→</span>
                <p className="text-[11px] text-white leading-relaxed">{insight}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ SLIDE 7: Social Proof ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center px-12 sm:px-20">
          <p className="text-[11px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-4">SOCIAL PROOF</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-10">Businesses Like Yours</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                quote: '"We discovered our lunch conversion was only 44%. After adding a greeter, it jumped to 62%. That\'s $3K/month."',
                name: 'Marcus T.',
                biz: 'Quick-service restaurant, Vancouver',
              },
              {
                quote: '"Meridian told us our highest-margin item was buried on the menu. Moved it to #2 — sales tripled in a week."',
                name: 'Sarah L.',
                biz: 'Cafe & bakery, Toronto',
              },
              {
                quote: '"The camera intelligence showed we lose 8 customers per lunch rush to long lines. One extra staff member = $1,200/week recovered."',
                name: 'James K.',
                biz: 'Smoke shop, Calgary',
              },
            ].map(t => (
              <div key={t.name} className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 flex flex-col">
                <p className="text-[12px] text-white italic leading-relaxed flex-1">{t.quote}</p>
                <div className="mt-4 pt-3 border-t border-[#1a2420]">
                  <p className="text-[12px] font-semibold text-[#00d4aa]">{t.name}</p>
                  <p className="text-[10px] text-[#6b7a74]">{t.biz}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ SLIDE 8: CTA ═══ */}
        <div className="min-h-screen snap-start flex flex-col justify-center items-center text-center px-12 sm:px-20">
          <p className="text-[11px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-6">READY TO GROW?</p>
          <h2 className="text-4xl sm:text-5xl font-bold text-white mb-2">
            Let's Go, <span className="text-[#00d4aa]">{firstName}!</span>
          </h2>
          <p className="text-[14px] text-[#6b7a74] mt-4 max-w-lg">
            Connect your POS in 5 minutes. See your first insights today.
            {firstMonthFree ? ' First month is on us.' : ''}
          </p>

          {/* QR codes */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-10 max-w-lg w-full">
            {setupFee > 0 && (
              <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 flex flex-col items-center">
                <p className="text-[10px] font-mono text-[#6b7a74] tracking-wider mb-3">SETUP FEE</p>
                <div className="w-28 h-28 bg-white rounded-lg flex items-center justify-center">
                  {checkoutUrl ? (
                    <img src={generateQrSvg(checkoutUrl, 112)} alt="QR" className="w-24 h-24" crossOrigin="anonymous" />
                  ) : (
                    <QrCode size={48} className="text-[#0a0f0d]" />
                  )}
                </div>
                <p className="text-[11px] text-white font-medium mt-3">CA${setupFee}</p>
              </div>
            )}
            <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 flex flex-col items-center">
              <p className="text-[10px] font-mono text-[#6b7a74] tracking-wider mb-3">SUBSCRIPTION</p>
              <div className="w-28 h-28 bg-white rounded-lg flex items-center justify-center">
                {checkoutUrl ? (
                  <img src={generateQrSvg(checkoutUrl, 112)} alt="QR" className="w-24 h-24" crossOrigin="anonymous" />
                ) : (
                  <QrCode size={48} className="text-[#0a0f0d]" />
                )}
              </div>
              <p className="text-[11px] text-white font-medium mt-3">CA${price}{interval}</p>
            </div>
          </div>

          {/* Footer stats */}
          <div className="flex flex-wrap justify-center gap-8 mt-10 text-center">
            <div>
              <p className="text-[10px] font-mono text-[#4a5550] tracking-wider">YOUR REP</p>
              <p className="text-[13px] text-white mt-1">{repName}</p>
            </div>
            <div>
              <p className="text-[10px] font-mono text-[#4a5550] tracking-wider">CONTACT</p>
              <p className="text-[13px] text-white mt-1">{repEmail}</p>
            </div>
            <div>
              <p className="text-[10px] font-mono text-[#4a5550] tracking-wider">PLATFORM</p>
              <p className="text-[13px] text-white mt-1">meridian.tips</p>
            </div>
            <div>
              <p className="text-[10px] font-mono text-[#4a5550] tracking-wider">SETUP TIME</p>
              <p className="text-[13px] text-white mt-1">5 minutes</p>
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

  const [form, setForm] = useState({
    businessName: '',
    ownerName: '',
    email: '',
    phone: '',
    vertical: '',
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
      checkoutUrl: checkoutUrl || undefined,
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
      const tempOrgId = uuid()
      const body = {
        org_id: tempOrgId,
        plan: form.plan,
        monthly_price_cents: form.customPrice ? parseInt(form.customPrice) * 100 : selectedPlan.price * 100,
        setup_fee_cents: setupFee * 100,
        first_month_free: form.firstMonthFree,
        customer_email: form.email,
        customer_name: form.ownerName,
        business_name: form.businessName,
        country: 'CA',
        rep_id: rep?.rep_id || '',
        rep_name: rep?.name || '',
        return_url: `${window.location.origin}/canada/onboard?checkout=success`,
      }

      const res = await fetch(`${API_URL}/api/billing/create-checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Checkout service unavailable' }))
        throw new Error(err.detail || `Server error ${res.status}`)
      }

      const data = await res.json()
      setCheckoutUrl(data.checkout_url)
      setCheckoutSessionId(data.checkout_id || data.order_id || '')
    } catch (err: any) {
      setError(err.message || 'Failed to create checkout session')
    } finally {
      setCreatingCheckout(false)
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
            country: 'CA',
            square_checkout_id: checkoutSessionId || null,
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
          country: 'CA',
          notes: form.notes || `Plan: ${selectedPlan.label} at $${price}${interval}. Setup fee: $${setupFee}. First month free: ${form.firstMonthFree ? 'Yes' : 'No'}`,
          rep_id: rep?.rep_id || null,
        })
        if (dealErr) console.warn('Deal creation warning:', dealErr.message)
      } else {
        const existing = JSON.parse(localStorage.getItem('meridian_pending_customers_ca') || '[]')
        existing.push({
          id: businessId, token, ...form, price, setupFee,
          plan: selectedPlan.label, repId: rep?.rep_id, repName: rep?.name,
          country: 'CA', createdAt: new Date().toISOString(),
        })
        localStorage.setItem('meridian_pending_customers_ca', JSON.stringify(existing))
      }

      // Provision customer: create Supabase Auth user, send invoices + welcome email
      // Only call if email is provided — rep can add it later
      const API_URL = import.meta.env.VITE_API_URL || ''
      if (form.email.trim()) {
        try {
          const provRes = await fetch(`${API_URL}/api/onboarding/provision-customer`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              org_id: businessId,
              email: form.email,
              owner_name: form.ownerName,
              business_name: form.businessName,
              plan: form.plan,
              monthly_price: price,
              rep_id: rep?.rep_id || null,
              rep_name: rep?.name || null,
            }),
          })
          if (provRes.ok) {
            const provData = await provRes.json()
            console.info('Customer provisioned:', provData.email, '— temp password generated, welcome email sent')
          }
        } catch (provisionErr) {
          console.warn('Provision call failed (non-blocking):', provisionErr)
        }
      }

      const link = `${window.location.origin}/canada/onboard?token=${token}&biz=${encodeURIComponent(form.businessName)}&name=${encodeURIComponent(form.ownerName)}&email=${encodeURIComponent(form.email)}&phone=${encodeURIComponent(form.phone)}&plan=${encodeURIComponent(form.plan)}&price=${price}&rep=${encodeURIComponent(rep?.rep_id || '')}&rep_name=${encodeURIComponent(rep?.name || '')}`
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

  const verticals = ['Restaurant', 'Cafe', 'Bar', 'Smoke Shop', 'Boutique', 'Salon', 'Food Truck', 'Convenience Store', 'Other']
  const stepLabels = ['Business Details', 'Select Plan', 'Customize & Price', 'Generate Proposal']
  const steps: Step[] = ['details', 'plan', 'customize', 'preview']
  const currentIdx = steps.indexOf(step)

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => {
            if (step === 'details') navigate('/canada/portal/leads')
            else setStep(steps[currentIdx - 1])
          }}
          className="p-2 rounded-lg text-[#6b7a74] hover:text-white hover:bg-[#1a2420] transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-xl font-bold text-white">Generate Proposal</h1>
          <p className="text-[12px] text-[#6b7a74]">Create a branded proposal and checkout link for your customer</p>
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
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-semibold transition-all duration-300 ${
                    isDone
                      ? 'bg-[#00d4aa] text-[#0a0f0d]'
                      : isActive
                      ? 'border-2 border-[#00d4aa] text-[#00d4aa]'
                      : 'bg-[#1a2420] text-[#4a5550]'
                  }`}
                >
                  {isDone ? <Check size={14} /> : i + 1}
                </div>
                <span className={`text-[9px] mt-1.5 font-medium ${
                  isActive ? 'text-white' : isDone ? 'text-[#00d4aa]' : 'text-[#4a5550]'
                }`}>
                  {label}
                </span>
              </div>
              {i < stepLabels.length - 1 && (
                <div className={`w-8 sm:w-12 h-[2px] mx-1 mt-[-14px] ${isDone ? 'bg-[#00d4aa]' : 'bg-[#1a2420]'}`} />
              )}
            </div>
          )
        })}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[13px]">
          {error}
        </div>
      )}

      {/* ═══ STEP 1: Details ═══ */}
      {step === 'details' && (
        <div className="space-y-4">
          <div className="bg-[#0f1512] rounded-xl p-6 border border-[#1a2420] space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Store size={16} className="text-[#00d4aa]" />
              <h2 className="text-[14px] font-semibold text-white">Business Information</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-medium text-[#6b7a74] mb-1.5">Business Name *</label>
                <input type="text" value={form.businessName} onChange={e => update('businessName', e.target.value)}
                  placeholder="e.g. Lucky Dragon Kitchen"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-white placeholder-[#4a5550] focus:border-[#00d4aa]/50 focus:outline-none transition-colors" />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#6b7a74] mb-1.5">Business Type</label>
                <select value={form.vertical} onChange={e => update('vertical', e.target.value)}
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-white focus:border-[#00d4aa]/50 focus:outline-none transition-colors">
                  <option value="">Select type...</option>
                  {verticals.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>

            {/* POS Selector */}
            <div>
              <label className="block text-[11px] font-medium text-[#6b7a74] mb-2">Current POS System</label>
              <POSSystemPicker
                value={form.pos || null}
                onChange={(key) => update('pos', key)}
                mode="new-customer"
                portalContext="canada"
              />
            </div>

            <div className="flex items-center gap-2 mt-6 mb-2">
              <User size={16} className="text-[#00d4aa]" />
              <h2 className="text-[14px] font-semibold text-white">Owner Contact</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-medium text-[#6b7a74] mb-1.5">Owner Name *</label>
                <input type="text" value={form.ownerName} onChange={e => update('ownerName', e.target.value)}
                  placeholder="e.g. James Chen"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-white placeholder-[#4a5550] focus:border-[#00d4aa]/50 focus:outline-none transition-colors" />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#6b7a74] mb-1.5">Email</label>
                <input type="email" value={form.email} onChange={e => update('email', e.target.value)}
                  placeholder="james@luckydragon.com"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-white placeholder-[#4a5550] focus:border-[#00d4aa]/50 focus:outline-none transition-colors" />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#6b7a74] mb-1.5">Phone</label>
                <input type="tel" value={form.phone} onChange={e => update('phone', e.target.value)}
                  placeholder="(555) 234-5678"
                  className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-white placeholder-[#4a5550] focus:border-[#00d4aa]/50 focus:outline-none transition-colors" />
              </div>
            </div>
            <div className="mt-2">
              <label className="block text-[11px] font-medium text-[#6b7a74] mb-1.5">Notes (optional)</label>
              <textarea value={form.notes} onChange={e => update('notes', e.target.value)}
                placeholder="Any notes about this business..."
                rows={2}
                className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-white placeholder-[#4a5550] focus:border-[#00d4aa]/50 focus:outline-none transition-colors resize-none" />
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={() => validateDetails() && setStep('plan')}
              className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-[#0a0f0d] bg-[#00d4aa] rounded-lg hover:bg-[#00c49e] transition-colors">
              Next: Select Plan <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ STEP 2: Plan ═══ */}
      {step === 'plan' && (
        <div className="space-y-4">
          <div className="bg-[#0f1512] rounded-xl p-6 border border-[#1a2420]">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles size={16} className="text-[#00d4aa]" />
              <h2 className="text-[14px] font-semibold text-white">Select Plan for {form.businessName}</h2>
            </div>
            <div className="grid gap-3">
              {PLAN_TIERS.map(plan => (
                <button key={plan.id} onClick={() => update('plan', plan.id)}
                  className={`p-4 rounded-xl border text-left transition-all duration-200 ${
                    form.plan === plan.id
                      ? 'border-[#00d4aa]/50 bg-[#00d4aa]/5'
                      : 'border-[#1a2420] hover:border-[#4a5550] bg-[#0a0f0d]'
                  }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-[14px] font-semibold text-white">{plan.label}</p>
                        {plan.tag && (
                          <span className="text-[10px] px-2 py-0.5 bg-[#00d4aa] text-[#0a0f0d] font-semibold rounded">
                            {plan.tag}
                          </span>
                        )}
                      </div>
                      <p className="text-[12px] text-[#6b7a74] mt-0.5">{plan.features.slice(0, 3).join(' · ')}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-white">CA${plan.price}</p>
                      <p className="text-[10px] text-[#6b7a74]">{plan.interval === 'week' ? '/week' : '/month'}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep('details')}
              className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#6b7a74] hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('customize')}
              className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-[#0a0f0d] bg-[#00d4aa] rounded-lg hover:bg-[#00c49e] transition-colors">
              Next: Customize <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ STEP 3: Customize ═══ */}
      {step === 'customize' && (
        <div className="space-y-4">
          <div className="bg-[#0f1512] rounded-xl p-6 border border-[#1a2420]">
            <div className="flex items-center gap-2 mb-4">
              <DollarSign size={16} className="text-[#00d4aa]" />
              <h2 className="text-[14px] font-semibold text-white">Customize Pricing</h2>
            </div>

            <div className="p-4 rounded-xl border border-[#00d4aa]/20 bg-[#00d4aa]/5 mb-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-[13px] font-semibold text-white">{selectedPlan.label} Plan</p>
                  <p className="text-[11px] text-[#6b7a74]">{selectedPlan.features.length} features included</p>
                </div>
                <p className="text-lg font-bold text-[#00d4aa]">CA${selectedPlan.price}{interval}</p>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-[11px] font-medium text-[#6b7a74] mb-1.5">Custom Monthly Price (optional override)</label>
              <div className="relative">
                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#4a5550]" />
                <input type="number" value={form.customPrice}
                  onChange={e => update('customPrice', e.target.value)}
                  placeholder={selectedPlan.price.toString()}
                  className="w-full pl-8 pr-3 py-2.5 text-[13px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-white placeholder-[#4a5550] focus:border-[#00d4aa]/50 focus:outline-none transition-colors" />
              </div>
              <p className="text-[10px] text-[#4a5550] mt-1">All amounts in CAD</p>
            </div>

            <div className="mb-4">
              <label className="block text-[11px] font-medium text-[#6b7a74] mb-1.5">
                Setup Fee <span className="text-[#00d4aa]">(you keep 100%)</span>
              </label>
              <div className="relative">
                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#4a5550]" />
                <input type="number" value={form.setupFee}
                  onChange={e => update('setupFee', e.target.value)}
                  placeholder="0"
                  className="w-full pl-8 pr-3 py-2.5 text-[13px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-white placeholder-[#4a5550] focus:border-[#00d4aa]/50 focus:outline-none transition-colors" />
              </div>
              <p className="text-[10px] text-[#00d4aa]/60 mt-1">Custom amount — goes directly to you</p>
            </div>

            <div className="flex items-center justify-between p-4 rounded-xl border border-[#1a2420] bg-[#0a0f0d]">
              <div className="flex items-center gap-3">
                <Gift size={18} className={form.firstMonthFree ? 'text-[#00d4aa]' : 'text-[#4a5550]'} />
                <div>
                  <p className="text-[13px] font-semibold text-white">First Month Free</p>
                  <p className="text-[11px] text-[#6b7a74]">Waive month 1 subscription — great for closing hesitant prospects</p>
                </div>
              </div>
              <button
                onClick={() => update('firstMonthFree', !form.firstMonthFree)}
                className={`relative w-12 h-6 rounded-full transition-colors duration-200 ${
                  form.firstMonthFree ? 'bg-[#00d4aa]' : 'bg-[#1a2420]'
                }`}
              >
                <div className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform duration-200 ${
                  form.firstMonthFree ? 'translate-x-6' : ''
                }`} />
              </button>
            </div>
          </div>

          {/* Summary */}
          <div className="bg-[#0f1512] rounded-xl p-6 border border-[#00d4aa]/20">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 size={16} className="text-[#00d4aa]" />
              <h2 className="text-[14px] font-semibold text-white">Proposal Summary</h2>
            </div>
            <div className="space-y-2 text-[13px]">
              <div className="flex justify-between py-2 border-b border-[#1a2420]">
                <span className="text-[#6b7a74]">Business</span>
                <span className="text-white font-medium">{form.businessName}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1a2420]">
                <span className="text-[#6b7a74]">Plan</span>
                <span className="text-white font-medium">{selectedPlan.label} — CA${price}{interval}</span>
              </div>
              {setupFee > 0 && (
                <div className="flex justify-between py-2 border-b border-[#1a2420]">
                  <span className="text-[#6b7a74]">Setup Fee <span className="text-[#00d4aa]">(yours)</span></span>
                  <span className="text-[#00d4aa] font-medium">CA${setupFee}</span>
                </div>
              )}
              {form.firstMonthFree && (
                <div className="flex justify-between py-2 border-b border-[#1a2420]">
                  <span className="text-[#6b7a74]">First Month</span>
                  <span className="text-[#7c3aed] font-medium">FREE</span>
                </div>
              )}
              <div className="flex justify-between py-3">
                <span className="text-[#6b7a74] font-medium">Due Today</span>
                <span className="text-lg font-bold text-[#00d4aa]">CA${dueToday.toLocaleString()}</span>
              </div>
            </div>
            {rep && (
              <div className="mt-3 pt-3 border-t border-[#1a2420]">
                <p className="text-[11px] text-[#6b7a74]">
                  Rep: <span className="text-white font-medium">{rep.name}</span> ·
                  Commission: <span className="text-[#00d4aa] font-medium">{rep.commission_rate}%</span> =
                  <span className="text-[#00d4aa] font-medium"> CA${Math.round(price * (rep.commission_rate / 100))}{interval}</span>
                  {setupFee > 0 && <span className="text-[#7c3aed]"> + CA${setupFee} setup</span>}
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep('plan')}
              className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#6b7a74] hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('preview')}
              className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-[#0a0f0d] bg-[#00d4aa] rounded-lg hover:bg-[#00c49e] transition-colors">
              Next: Generate <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ STEP 4: Preview & Generate ═══ */}
      {step === 'preview' && (
        <div className="space-y-4">
          <div className="bg-[#0f1512] rounded-xl p-6 border border-[#1a2420]">
            <div className="flex items-center gap-2 mb-4">
              <Eye size={16} className="text-[#00d4aa]" />
              <h2 className="text-[14px] font-semibold text-white">Proposal Ready</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 text-[13px]">
              <div className="p-3 rounded-lg bg-[#0a0f0d] border border-[#1a2420]">
                <div className="text-[10px] text-[#4a5550] uppercase tracking-wider mb-1">Business</div>
                <div className="text-white font-medium">{form.businessName}</div>
              </div>
              <div className="p-3 rounded-lg bg-[#0a0f0d] border border-[#1a2420]">
                <div className="text-[10px] text-[#4a5550] uppercase tracking-wider mb-1">Owner</div>
                <div className="text-white font-medium">{form.ownerName}</div>
              </div>
              <div className="p-3 rounded-lg bg-[#0a0f0d] border border-[#1a2420]">
                <div className="text-[10px] text-[#4a5550] uppercase tracking-wider mb-1">Plan</div>
                <div className="text-[#00d4aa] font-medium">{selectedPlan.label} — CA${price}{interval}</div>
              </div>
              <div className="p-3 rounded-lg bg-[#0a0f0d] border border-[#1a2420]">
                <div className="text-[10px] text-[#4a5550] uppercase tracking-wider mb-1">Due Today</div>
                <div className="text-[#00d4aa] font-medium">CA${dueToday.toLocaleString()}</div>
              </div>
            </div>
          </div>

          {/* Checkout Link section */}
          <div className="bg-[#0f1512] rounded-xl p-6 border border-[#1a2420]">
            <div className="flex items-center gap-2 mb-4">
              <QrCode size={16} className="text-[#7c3aed]" />
              <h2 className="text-[14px] font-semibold text-white">Payment Checkout Link</h2>
            </div>

            {!checkoutUrl ? (
              <div>
                <p className="text-[12px] text-[#6b7a74] mb-3">
                  Generate a unique Square checkout link for this customer. Includes the {selectedPlan.label} subscription
                  {setupFee > 0 ? ` + CA$${setupFee} setup fee` : ''}
                  {form.firstMonthFree ? ' with first month free' : ''}. All amounts in CAD.
                </p>
                <button
                  onClick={handleCreateCheckout}
                  disabled={creatingCheckout}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 text-[13px] font-medium text-white bg-[#7c3aed] rounded-lg hover:bg-[#6b2fd4] disabled:opacity-50 transition-colors"
                >
                  {creatingCheckout ? (
                    <><Loader2 size={14} className="animate-spin" /> Creating Checkout Session...</>
                  ) : (
                    <><QrCode size={14} /> Generate Checkout Link & QR Code</>
                  )}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-[13px] text-[#00d4aa]">
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
                <p className="text-center text-[11px] text-[#6b7a74]">
                  Customer scans to pay — {selectedPlan.label} CA${price}{interval}
                  {setupFee > 0 ? ` + CA$${setupFee} setup` : ''}
                  {form.firstMonthFree ? ' · 30-day free trial' : ''}
                </p>
                <div className="flex gap-2">
                  <input type="text" value={checkoutUrl} readOnly
                    className="flex-1 px-3 py-2.5 text-[11px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-[#6b7a74] font-mono truncate" />
                  <button onClick={copyCheckoutUrl}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-[12px] font-medium rounded-lg border transition-all duration-200 ${
                      copiedCheckout ? 'bg-[#00d4aa]/10 border-[#00d4aa]/30 text-[#00d4aa]' : 'bg-[#1a2420] border-[#1a2420] text-white hover:bg-[#0f1512]'
                    }`}>
                    {copiedCheckout ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                    {copiedCheckout ? 'Copied!' : 'Copy'}
                  </button>
                  <a href={checkoutUrl} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-4 py-2.5 text-[12px] font-medium rounded-lg border border-[#1a2420] bg-[#1a2420] text-white hover:bg-[#0f1512] transition-colors">
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
              className="flex items-center justify-center gap-2 px-6 py-4 text-[14px] font-semibold text-[#0a0f0d] bg-gradient-to-r from-[#00d4aa] to-[#7c3aed] rounded-xl hover:opacity-90 transition-all"
            >
              <Eye size={18} /> View Proposal (8 Slides)
            </button>

            {proposalGenerated && (
              <button
                onClick={handleDownloadPdf}
                disabled={generating}
                className="flex items-center justify-center gap-2 px-6 py-3 text-[13px] font-medium text-white border border-[#1a2420] rounded-xl hover:bg-[#0f1512] transition-all disabled:opacity-50"
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
          <div className="bg-[#0f1512] rounded-xl p-6 border border-[#1a2420]">
            <div className="flex items-center gap-2 mb-4">
              <Send size={16} className="text-[#00d4aa]" />
              <h2 className="text-[14px] font-semibold text-white">Create Account & Send Onboarding Link</h2>
            </div>

            {!onboardingLink ? (
              <button
                onClick={handleCreateCustomer}
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 text-[13px] font-medium bg-[#00d4aa] text-[#0a0f0d] rounded-lg hover:bg-[#00c49e] disabled:opacity-50 transition-colors"
              >
                {saving ? <><Loader2 size={14} className="animate-spin" /> Creating...</> : <><CheckCircle2 size={14} /> Create Customer & Generate Link</>}
              </button>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-[13px] text-[#00d4aa]">
                  <CheckCircle2 size={14} /> Customer created!
                </div>
                <div className="flex gap-2">
                  <input type="text" value={onboardingLink} readOnly
                    className="flex-1 px-3 py-2.5 text-[12px] rounded-lg bg-[#0a0f0d] border border-[#1a2420] text-[#6b7a74] font-mono truncate" />
                  <button onClick={copyLink}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-[12px] font-medium rounded-lg border transition-all duration-200 ${
                      copied ? 'bg-[#00d4aa]/10 border-[#00d4aa]/30 text-[#00d4aa]' : 'bg-[#1a2420] border-[#1a2420] text-white hover:bg-[#0f1512]'
                    }`}>
                    {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <button onClick={sendViaSms}
                    className="flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-[#0a0f0d] bg-[#00d4aa] rounded-lg hover:bg-[#00c49e] transition-colors">
                    <Phone size={14} /> Text to Customer
                  </button>
                  <button onClick={() => {
                    const subject = `Your Meridian Account is Ready!`
                    const body = `Hi ${form.ownerName.split(' ')[0]},\n\nYour Meridian analytics account is set up! Click the link below to complete your onboarding — it only takes about 3 minutes:\n\n${onboardingLink}\n\n${checkoutUrl ? `To activate your subscription, complete your payment here:\n${checkoutUrl}\n\n` : ''}You'll connect your POS and your dashboard will start lighting up with insights.\n\nAll amounts in CAD.\n\nLet me know if you have any questions!\n\n${rep?.name || 'Your Meridian Rep'}${rep?.phone ? '\n' + rep.phone : ''}`
                    window.open(`mailto:${form.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, '_blank')
                  }}
                    className="flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-white bg-[#1a2420] rounded-lg hover:bg-[#0f1512] border border-[#1a2420] transition-colors">
                    <Mail size={14} /> Email to Customer
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep('customize')}
              className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-[#6b7a74] hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => {
              setForm({ businessName: '', ownerName: '', email: '', phone: '', vertical: '', pos: '', plan: 'premium', customPrice: '', setupFee: '', firstMonthFree: false, notes: '' })
              setStep('details')
              setOnboardingLink('')
              setProposalGenerated(false)
              setShowProposal(false)
              setCheckoutUrl('')
              setCheckoutSessionId('')
            }}
              className="text-[12px] text-[#00d4aa] hover:text-white transition-colors">
              + Create Another Proposal
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
      />
    </div>
  )
}
