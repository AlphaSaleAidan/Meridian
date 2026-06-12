import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDemoContext, type BusinessType } from '@/lib/demo-context'
import { getTourContent, type StepId, type TourContent } from './walkthrough-content'

// Canada-only guided tour for the new /canada/demo portal. Purpose-built for
// the flat-nav CanadaLayout (see CanadaDemoLayout.tsx); the US /demo keeps the
// shared WalkthroughEngine. Independent dismissal key so the two never collide.
const LS_KEY = 'meridian_canada_tour_dismissed'
const BASE_PATH = '/canada/demo'

interface SpotlightRect {
  top: number
  left: number
  width: number
  height: number
}

interface CanadaStep {
  id: StepId
  tabPath: string
  selector: string
  fallback: string
  pad: number
}

// Order mirrors the new portal's value story over the CanadaLayout nav.
const CANADA_TOUR_STEPS: CanadaStep[] = [
  { id: 'overview', tabPath: '', selector: '[data-walkthrough="money-left-score"]', fallback: '[data-walkthrough="overview-stats"]', pad: 16 },
  { id: 'actions', tabPath: 'actions', selector: '[data-walkthrough="top-actions-list"]', fallback: '.card', pad: 16 },
  { id: 'margins', tabPath: 'margins', selector: '[data-walkthrough="margin-stats"]', fallback: '[data-walkthrough="margin-calculator"]', pad: 12 },
  { id: 'forecast', tabPath: 'forecasts', selector: '[data-walkthrough="revenue-forecast-chart"]', fallback: '.recharts-responsive-container', pad: 20 },
  { id: 'camera', tabPath: 'camera-analytics', selector: '[data-walkthrough="camera-stats"]', fallback: '.card', pad: 16 },
  { id: 'phone', tabPath: 'phone-orders', selector: '[data-walkthrough="phone-stats"]', fallback: '.card', pad: 16 },
  { id: 'anomaly', tabPath: 'anomalies', selector: '[data-walkthrough="top-anomaly"]', fallback: '.card', pad: 16 },
  { id: 'customers', tabPath: '', selector: '[data-walkthrough="sidebar-nav"]', fallback: '.card', pad: 8 },
  { id: 'connect', tabPath: '', selector: '[data-walkthrough="connect-pos-cta"]', fallback: '.glow-violet', pad: 24 },
]

// Canada framing layered onto the shared per-vertical copy.
function canadaContent(id: StepId, bt: BusinessType): TourContent {
  const base = getTourContent(id, bt, 'canada')
  if (id === 'overview') {
    return {
      ...base,
      description: `${base.description} Every figure here is in Canadian dollars, tuned to how Canadian ${bt === 'auto_shop' ? 'shops' : 'businesses'} actually trade.`,
    }
  }
  if (id === 'connect') {
    return {
      title: 'Ready to see your real numbers?',
      description: 'Connect your POS — Square, Moneris, TouchBistro, Clover and more — and this whole dashboard fills with your actual Canadian sales data. Setup takes about 4 minutes. First month free, no credit card.',
      tip: base.tip,
    }
  }
  return base
}

function SpotlightOverlay({ rect }: { rect: SpotlightRect | null }) {
  const ringRef = useRef<HTMLDivElement>(null)
  const animRef = useRef<SpotlightRect | null>(null)
  const rafRef = useRef(0)

  useEffect(() => {
    if (!rect) { animRef.current = null; return }
    const el = ringRef.current
    if (!el) return
    if (!animRef.current) {
      animRef.current = rect
      apply(el, rect)
      return
    }
    const start = { ...animRef.current }
    const startTime = performance.now()
    const tick = (now: number) => {
      const raw = Math.min((now - startTime) / 400, 1)
      const t = 1 - Math.pow(1 - raw, 3)
      apply(el, {
        top: start.top + (rect.top - start.top) * t,
        left: start.left + (rect.left - start.left) * t,
        width: start.width + (rect.width - start.width) * t,
        height: start.height + (rect.height - start.height) * t,
      })
      if (raw < 1) rafRef.current = requestAnimationFrame(tick)
      else animRef.current = rect
    }
    cancelAnimationFrame(rafRef.current)
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [rect])

  function apply(el: HTMLDivElement, r: SpotlightRect) {
    el.style.top = `${r.top - 4}px`
    el.style.left = `${r.left - 4}px`
    el.style.width = `${r.width + 8}px`
    el.style.height = `${r.height + 8}px`
  }

  if (!rect) return null
  return createPortal(
    <div
      ref={ringRef}
      style={{
        position: 'fixed',
        top: rect.top - 4,
        left: rect.left - 4,
        width: rect.width + 8,
        height: rect.height + 8,
        zIndex: 9998,
        pointerEvents: 'none',
        borderRadius: 14,
        border: '2px solid rgba(23, 197, 176, 0.5)',
        boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.55), 0 0 20px rgba(23, 197, 176, 0.15)',
        animation: 'cdt-ring-pulse 2s ease-in-out infinite',
      }}
    />,
    document.body,
  )
}

function TourCard({
  content, currentIndex, totalSteps, onNext, onPrev, onSkip, visible, isMobile,
}: {
  content: TourContent
  currentIndex: number
  totalSteps: number
  onNext: () => void
  onPrev: () => void
  onSkip: () => void
  visible: boolean
  isMobile: boolean
}) {
  const isLast = currentIndex === totalSteps - 1
  return createPortal(
    <div
      style={{
        position: 'fixed',
        bottom: isMobile ? 0 : 24,
        right: isMobile ? 0 : 24,
        left: isMobile ? 0 : 'auto',
        zIndex: 9999,
        width: isMobile ? '100%' : 420,
        maxHeight: isMobile ? '55vh' : '75vh',
        overflowY: 'auto',
        opacity: visible ? 1 : 0,
        pointerEvents: visible ? 'auto' : 'none',
        transform: visible ? 'translateY(0)' : `translateY(${isMobile ? 20 : 6}px)`,
        transition: 'opacity 0.3s cubic-bezier(0.16,1,0.3,1), transform 0.3s cubic-bezier(0.16,1,0.3,1)',
      }}
    >
      <div style={{
        background: 'linear-gradient(180deg, #131315 0%, #111113 100%)',
        border: isMobile ? 'none' : '1px solid #2a2a30',
        borderTop: '1px solid #2a2a30',
        borderRadius: isMobile ? '16px 16px 0 0' : 16,
        boxShadow: isMobile ? '0 -10px 40px rgba(0,0,0,0.8)' : '0 20px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(23,197,176,0.06)',
        padding: isMobile ? '20px 16px 28px' : '24px 24px 20px',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}>
        {/* progress */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 4, flex: 1, marginRight: 12 }}>
            {Array.from({ length: totalSteps }).map((_, i) => (
              <div key={i} style={{
                flex: i === currentIndex ? 2.5 : 1,
                height: 3,
                borderRadius: 2,
                background: i === currentIndex ? '#17C5B0' : i < currentIndex ? 'rgba(23,197,176,0.4)' : '#2a2a30',
                transition: 'all 0.4s cubic-bezier(0.16,1,0.3,1)',
              }} />
            ))}
          </div>
          <button
            onClick={onSkip}
            style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', fontSize: 11, padding: '2px 6px' }}
            onMouseEnter={e => (e.currentTarget.style.color = '#A1A1A8')}
            onMouseLeave={e => (e.currentTarget.style.color = '#6b7280')}
          >
            Skip
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, fontWeight: 600, color: '#17C5B0', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8, opacity: 0.8 }}>
          <span>🇨🇦</span>
          <span>Step {currentIndex + 1} of {totalSteps}</span>
        </div>

        <h3 style={{ color: '#F5F5F7', fontSize: 18, fontWeight: 700, lineHeight: 1.3, margin: '0 0 8px' }}>{content.title}</h3>
        <p style={{ color: '#A1A1A8', fontSize: 14, lineHeight: 1.7, margin: '0 0 12px' }}>{content.description}</p>
        {content.tip && (
          <p style={{ color: '#17C5B0', fontSize: 12.5, lineHeight: 1.6, margin: '0 0 4px', padding: '10px 12px', background: 'rgba(23,197,176,0.06)', border: '1px solid rgba(23,197,176,0.12)', borderRadius: 10 }}>
            <strong>Tip:</strong> {content.tip}
          </p>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 18 }}>
          <button
            onClick={onPrev}
            disabled={currentIndex === 0}
            style={{ background: 'none', border: 'none', color: currentIndex === 0 ? '#3a3a40' : '#A1A1A8', cursor: currentIndex === 0 ? 'default' : 'pointer', fontSize: 13, fontWeight: 500, padding: '8px 4px' }}
          >
            Back
          </button>
          <button
            onClick={onNext}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: '#17C5B0', color: '#0a0f0d', border: 'none',
              borderRadius: 10, padding: '10px 18px', fontSize: 13, fontWeight: 700, cursor: 'pointer',
              boxShadow: '0 4px 16px rgba(23,197,176,0.25)',
            }}
          >
            {isLast ? 'Get started' : 'Next'}
            <span aria-hidden>→</span>
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

function CtaScreen({ onClose, isMobile }: { onClose: () => void; isMobile: boolean }) {
  const navigate = useNavigate()
  return createPortal(
    <div style={{
      position: 'fixed', inset: 0, zIndex: 10000, display: 'flex',
      alignItems: isMobile ? 'flex-end' : 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)', animation: 'cdt-fade-in 0.3s ease',
    }}>
      <div style={{
        width: '100%', maxWidth: isMobile ? '100%' : 460, margin: isMobile ? 0 : '0 16px',
        background: 'linear-gradient(180deg, #131315 0%, #0f0f11 100%)',
        border: isMobile ? 'none' : '1px solid #2a2a30',
        borderRadius: isMobile ? '16px 16px 0 0' : 20,
        boxShadow: '0 40px 100px rgba(0,0,0,0.8), 0 0 0 1px rgba(23,197,176,0.08)',
        padding: isMobile ? '24px 16px 32px' : '32px 28px', textAlign: 'center',
      }}>
        <div style={{
          width: 48, height: 48, margin: '0 auto 16px', borderRadius: '50%',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'linear-gradient(135deg, rgba(23,197,176,0.15), rgba(26,143,214,0.15))',
          border: '1px solid rgba(23,197,176,0.2)', fontSize: 22,
        }}>🇨🇦</div>
        <h2 style={{ color: '#F5F5F7', fontSize: 22, fontWeight: 700, margin: '0 0 8px' }}>That’s Meridian for Canada</h2>
        <p style={{ color: '#A1A1A8', fontSize: 14, lineHeight: 1.6, margin: '0 0 24px' }}>
          Everything you just saw runs on your own Canadian sales data the moment you connect your POS. Get set up in minutes — first month is on us.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <button
            onClick={() => { onClose(); navigate('/canada/portal/signup') }}
            style={{ background: '#17C5B0', color: '#0a0f0d', border: 'none', borderRadius: 12, padding: '13px', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}
          >
            Start your Canada setup
          </button>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#6b7280', fontSize: 13, fontWeight: 500, cursor: 'pointer', padding: '6px' }}
          >
            Keep exploring the demo
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

export default function CanadaDemoTour() {
  const { businessType } = useDemoContext()
  const location = useLocation()
  const navigate = useNavigate()
  const bt = businessType || 'restaurant'

  const isOverview = location.pathname === BASE_PATH || location.pathname === BASE_PATH + '/'

  const [active, setActive] = useState(false)
  const [step, setStep] = useState(0)
  const [spotlightRect, setSpotlightRect] = useState<SpotlightRect | null>(null)
  const [cardVisible, setCardVisible] = useState(false)
  const [showCta, setShowCta] = useState(false)
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 1024)
  const [dismissed, setDismissed] = useState(() => {
    try { return localStorage.getItem(LS_KEY) === 'true' } catch { return false }
  })

  const recalcRef = useRef(0)
  const navPendingForStep = useRef(-1)
  const steps = CANADA_TOUR_STEPS
  const current = steps[step] ?? steps[0]
  const content = useMemo(() => canadaContent(current.id, bt), [current.id, bt])

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 1024)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const calculateSpotlight = useCallback((retry = 0) => {
    const s = steps[step]
    if (!s) return
    const findEl = () => document.querySelector(s.selector) || document.querySelector(s.fallback)
    const el = findEl()
    if (!el) {
      if (retry < 4) { setTimeout(() => calculateSpotlight(retry + 1), 150); return }
      setSpotlightRect(null)
      setCardVisible(true)
      return
    }
    const bounds = el.getBoundingClientRect()
    if ((bounds.width < 10 || bounds.height < 10) && retry < 6) {
      setTimeout(() => calculateSpotlight(retry + 1), 120)
      return
    }
    const main = document.querySelector('main')
    if (main) {
      const mainRect = main.getBoundingClientRect()
      const scrollDelta = (bounds.top + bounds.height / 2) - (mainRect.top + mainRect.height / 2)
      if (Math.abs(scrollDelta) > mainRect.height * 0.35) {
        main.scrollTo({ top: main.scrollTop + scrollDelta, behavior: 'smooth' })
        setTimeout(() => {
          const fresh = findEl()?.getBoundingClientRect()
          if (!fresh) return
          setSpotlightRect({ top: fresh.top - s.pad, left: fresh.left - s.pad, width: fresh.width + s.pad * 2, height: fresh.height + s.pad * 2 })
          requestAnimationFrame(() => setCardVisible(true))
        }, 300)
        return
      }
    }
    setSpotlightRect({ top: bounds.top - s.pad, left: bounds.left - s.pad, width: bounds.width + s.pad * 2, height: bounds.height + s.pad * 2 })
    requestAnimationFrame(() => setCardVisible(true))
  }, [step, steps])

  useEffect(() => {
    if (!active || showCta) return
    const s = steps[step]
    if (!s) return
    const targetPath = s.tabPath ? `${BASE_PATH}/${s.tabPath}` : BASE_PATH
    if (location.pathname !== targetPath) {
      navPendingForStep.current = step
      setSpotlightRect(null)
      setCardVisible(true)
      const main = document.querySelector('main')
      if (main) main.scrollTop = 0
      navigate(targetPath)
      return
    }
    const justNavigated = navPendingForStep.current === step
    navPendingForStep.current = -1
    recalcRef.current = window.setTimeout(calculateSpotlight, justNavigated ? 500 : 80)
    return () => clearTimeout(recalcRef.current)
  }, [active, step, showCta, location.pathname, navigate, calculateSpotlight, steps])

  useEffect(() => {
    if (!active) return
    const handler = () => calculateSpotlight()
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [active, calculateSpotlight])

  useEffect(() => {
    if (!active) return
    const handler = (e: KeyboardEvent) => {
      if (showCta) { if (e.key === 'Escape') handleSkip(); return }
      if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); handleNext() }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); handlePrev() }
      else if (e.key === 'Escape') handleSkip()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, step, showCta])

  function handleStart() {
    setStep(0)
    setActive(true)
    setShowCta(false)
    setDismissed(true)
  }
  function handleNext() {
    if (step < steps.length - 1) setStep(s => s + 1)
    else { setShowCta(true); setSpotlightRect(null); setCardVisible(false) }
  }
  function handlePrev() {
    if (step > 0) setStep(s => s - 1)
  }
  function handleSkip() {
    setActive(false)
    setSpotlightRect(null)
    setCardVisible(false)
    setShowCta(false)
    try { localStorage.setItem(LS_KEY, 'true') } catch { /* private mode */ }
    setDismissed(true)
  }

  return (
    <>
      {/* Launcher — floating, always available on the demo until the tour runs */}
      {!active && (
        <button onClick={handleStart} className="cdt-launcher" aria-label="Take a tour of Meridian Canada">
          <span className="cdt-launcher-bg" />
          <span className="cdt-launcher-content">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="cdt-launcher-icon">
              <path d="M12 3l1.912 5.813a2 2 0 001.275 1.275L21 12l-5.813 1.912a2 2 0 00-1.275 1.275L12 21l-1.912-5.813a2 2 0 00-1.275-1.275L3 12l5.813-1.912a2 2 0 001.275-1.275L12 3z" />
            </svg>
            <span className="cdt-launcher-text">Take a Tour</span>
            {isOverview && !dismissed && <span className="cdt-launcher-hint">See what Meridian does for Canada</span>}
          </span>
        </button>
      )}

      {active && !showCta && (
        <>
          <SpotlightOverlay rect={spotlightRect} />
          <TourCard
            content={content}
            currentIndex={step}
            totalSteps={steps.length}
            onNext={handleNext}
            onPrev={handlePrev}
            onSkip={handleSkip}
            visible={cardVisible}
            isMobile={isMobile}
          />
        </>
      )}

      {showCta && <CtaScreen onClose={handleSkip} isMobile={isMobile} />}

      <style>{`
        @keyframes cdt-ring-pulse {
          0%, 100% { border-color: rgba(23, 197, 176, 0.5); }
          50% { border-color: rgba(23, 197, 176, 0.2); }
        }
        @keyframes cdt-fade-in { 0% { opacity: 0; } 100% { opacity: 1; } }
        @keyframes cdt-glow-breathe { 0%, 100% { opacity: 0.4; } 50% { opacity: 0.75; } }

        .cdt-launcher {
          position: fixed;
          bottom: 24px;
          right: 24px;
          z-index: 9990;
          display: inline-flex;
          align-items: center;
          padding: 12px 18px;
          border: none;
          border-radius: 14px;
          cursor: pointer;
          background: transparent;
          overflow: hidden;
          font-family: Inter, system-ui, sans-serif;
        }
        .cdt-launcher-bg {
          position: absolute;
          inset: 0;
          border-radius: 14px;
          background: linear-gradient(135deg, rgba(23,197,176,0.14) 0%, rgba(26,143,214,0.12) 50%, rgba(23,197,176,0.14) 100%);
          border: 1px solid rgba(23,197,176,0.3);
          box-shadow: 0 8px 28px rgba(0,0,0,0.45), 0 0 18px rgba(23,197,176,0.12);
          animation: cdt-glow-breathe 6s ease-in-out infinite;
          transition: all 0.4s ease;
        }
        .cdt-launcher:hover .cdt-launcher-bg {
          border-color: rgba(23,197,176,0.5);
          box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 28px rgba(23,197,176,0.22);
        }
        .cdt-launcher-content {
          position: relative;
          z-index: 1;
          display: inline-flex;
          align-items: center;
          gap: 9px;
        }
        .cdt-launcher-icon { color: #17C5B0; filter: drop-shadow(0 0 4px rgba(23,197,176,0.4)); flex-shrink: 0; }
        .cdt-launcher-text { color: #F5F5F7; font-size: 14px; font-weight: 700; letter-spacing: -0.01em; }
        .cdt-launcher-hint { color: #8a8a92; font-size: 12px; font-weight: 400; margin-left: 4px; }
        @media (max-width: 640px) {
          .cdt-launcher { bottom: 80px; right: 16px; padding: 11px 15px; }
          .cdt-launcher-hint { display: none; }
        }
      `}</style>
    </>
  )
}
