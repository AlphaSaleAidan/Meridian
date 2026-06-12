import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDemoContext, type BusinessType } from '@/lib/demo-context'
import {
  WALKTHROUGH_STEPS,
  getTourContent,
  type PortalContext,
  type TourContent,
} from './walkthrough-content'

const LS_KEY = 'meridian_tour_dismissed'
const CONTACT_PHONE = '+18337725377'
const AUTO_ADVANCE_MS = 16000

interface SpotlightRect {
  top: number
  left: number
  width: number
  height: number
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

function lerpRect(a: SpotlightRect, b: SpotlightRect, t: number): SpotlightRect {
  return {
    top: lerp(a.top, b.top, t),
    left: lerp(a.left, b.left, t),
    width: lerp(a.width, b.width, t),
    height: lerp(a.height, b.height, t),
  }
}

function SpotlightOverlay({ rect, entering }: { rect: SpotlightRect | null; entering: boolean }) {
  const animRef = useRef<SpotlightRect | null>(null)
  const rafRef = useRef(0)
  const ringRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!rect) {
      animRef.current = null
      return
    }
    if (!animRef.current) {
      animRef.current = rect
      updateRing(rect)
      return
    }

    const start = { ...animRef.current }
    const startTime = performance.now()
    const duration = 400

    function tick(now: number) {
      const elapsed = now - startTime
      const raw = Math.min(elapsed / duration, 1)
      const t = 1 - Math.pow(1 - raw, 3)
      const current = lerpRect(start, rect!, t)
      updateRing(current)
      if (raw < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        animRef.current = rect
      }
    }

    cancelAnimationFrame(rafRef.current)
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [rect])

  function updateRing(r: SpotlightRect) {
    const el = ringRef.current
    if (!el) return
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
        opacity: entering ? 0 : 1,
        transition: 'opacity 0.35s ease',
        animation: 'tour-ring-pulse 2s ease-in-out infinite',
      }}
    />,
    document.body,
  )
}

function CheckoutScreen({
  onClose,
  isCanada,
  isMobile,
}: {
  onClose: () => void
  isCanada: boolean
  isMobile: boolean
}) {
  const [answers, setAnswers] = useState({ locations: '', pos: '', revenue: '' })
  const [submitted, setSubmitted] = useState(false)
  const navigate = useNavigate()

  const posOptions = ['Square', 'Toast', 'Clover', 'Lightspeed', 'Shopify POS', ...(isCanada ? ['Moneris', 'TouchBistro'] : []), 'Other']
  const revenueOptions = ['Under $30K/mo', '$30K–$80K/mo', '$80K–$200K/mo', '$200K+/mo']
  const locationOptions = ['1 location', '2–3 locations', '4–10 locations', '10+ locations']

  function handleSubmit() {
    setSubmitted(true)
  }

  function handleGetStarted() {
    onClose()
    navigate(isCanada ? '/canada/portal/signup' : '/customer/signup')
  }

  return createPortal(
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 10000,
      display: 'flex',
      alignItems: isMobile ? 'flex-end' : 'center',
      justifyContent: 'center',
      background: 'rgba(0,0,0,0.75)',
      backdropFilter: 'blur(8px)',
      animation: 'tour-fade-in 0.3s ease',
    }}>
      <div style={{
        width: '100%',
        maxWidth: isMobile ? '100%' : 520,
        margin: isMobile ? 0 : '0 16px',
        background: 'linear-gradient(180deg, #131315 0%, #0f0f11 100%)',
        border: isMobile ? 'none' : '1px solid #2a2a30',
        borderTop: '1px solid #2a2a30',
        borderRadius: isMobile ? '16px 16px 0 0' : 20,
        boxShadow: isMobile ? '0 -10px 40px rgba(0,0,0,0.8)' : '0 40px 100px rgba(0,0,0,0.8), 0 0 0 1px rgba(23,197,176,0.08)',
        padding: isMobile ? '24px 16px 32px' : '32px 28px',
        maxHeight: isMobile ? '85vh' : '90vh',
        overflowY: 'auto',
        alignSelf: isMobile ? 'flex-end' : 'center',
      }}>
        {!submitted ? (
          <>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{
                width: 48, height: 48, margin: '0 auto 16px',
                borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'linear-gradient(135deg, rgba(23,197,176,0.15), rgba(26,143,214,0.15))',
                border: '1px solid rgba(23,197,176,0.2)',
              }}>
                <span style={{ fontSize: 22 }}>&#10024;</span>
              </div>
              <h2 style={{ color: '#F5F5F7', fontSize: 22, fontWeight: 700, margin: '0 0 6px' }}>
                Almost there
              </h2>
              <p style={{ color: '#A1A1A8', fontSize: 14, margin: 0 }}>
                Help us personalize your setup — takes 15 seconds
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ color: '#A1A1A8', fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 6 }}>
                  Which POS system do you use?
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {posOptions.map(opt => (
                    <button
                      key={opt}
                      onClick={() => setAnswers(a => ({ ...a, pos: opt }))}
                      style={{
                        padding: '7px 12px',
                        borderRadius: 8,
                        fontSize: 12,
                        fontWeight: 500,
                        border: answers.pos === opt ? '1px solid #17C5B0' : '1px solid #2a2a30',
                        background: answers.pos === opt ? 'rgba(23,197,176,0.08)' : '#111113',
                        color: answers.pos === opt ? '#17C5B0' : '#A1A1A8',
                        cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ color: '#A1A1A8', fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 6 }}>
                  Monthly revenue range?
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {revenueOptions.map(opt => (
                    <button
                      key={opt}
                      onClick={() => setAnswers(a => ({ ...a, revenue: opt }))}
                      style={{
                        padding: '7px 12px',
                        borderRadius: 8,
                        fontSize: 12,
                        fontWeight: 500,
                        border: answers.revenue === opt ? '1px solid #17C5B0' : '1px solid #2a2a30',
                        background: answers.revenue === opt ? 'rgba(23,197,176,0.08)' : '#111113',
                        color: answers.revenue === opt ? '#17C5B0' : '#A1A1A8',
                        cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ color: '#A1A1A8', fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 6 }}>
                  How many locations?
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {locationOptions.map(opt => (
                    <button
                      key={opt}
                      onClick={() => setAnswers(a => ({ ...a, locations: opt }))}
                      style={{
                        padding: '7px 12px',
                        borderRadius: 8,
                        fontSize: 12,
                        fontWeight: 500,
                        border: answers.locations === opt ? '1px solid #17C5B0' : '1px solid #2a2a30',
                        background: answers.locations === opt ? 'rgba(23,197,176,0.08)' : '#111113',
                        color: answers.locations === opt ? '#17C5B0' : '#A1A1A8',
                        cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
              <button
                onClick={handleSubmit}
                className="tour-glow-btn"
                style={{
                  flex: 2,
                  padding: '14px 0',
                  background: 'linear-gradient(135deg, #17C5B0 0%, #1A8FD6 100%)',
                  border: 'none',
                  borderRadius: 12,
                  color: '#fff',
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: 'pointer',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <span style={{ position: 'relative', zIndex: 1 }}>Continue</span>
              </button>
              <button
                onClick={onClose}
                style={{
                  flex: 1,
                  padding: '14px 0',
                  background: 'none',
                  border: '1px solid #2a2a30',
                  borderRadius: 12,
                  color: '#A1A1A8',
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Maybe later
              </button>
            </div>
          </>
        ) : (
          <>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{
                width: 56, height: 56, margin: '0 auto 16px',
                borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'linear-gradient(135deg, rgba(23,197,176,0.2), rgba(26,143,214,0.2))',
                border: '1px solid rgba(23,197,176,0.3)',
                animation: 'tour-pulse 2s ease-in-out infinite',
              }}>
                <span style={{ fontSize: 26 }}>&#10003;</span>
              </div>
              <h2 style={{ color: '#F5F5F7', fontSize: 22, fontWeight: 700, margin: '0 0 8px' }}>
                You're a great fit
              </h2>
              <p style={{ color: '#A1A1A8', fontSize: 14, margin: 0, lineHeight: 1.6 }}>
                Based on your answers, Meridian can start generating insights for you within 24 hours of connecting your POS.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <button
                onClick={handleGetStarted}
                className="tour-glow-btn"
                style={{
                  width: '100%',
                  padding: '16px 0',
                  background: 'linear-gradient(135deg, #17C5B0 0%, #1A8FD6 100%)',
                  border: 'none',
                  borderRadius: 12,
                  color: '#fff',
                  fontSize: 15,
                  fontWeight: 700,
                  cursor: 'pointer',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <span style={{ position: 'relative', zIndex: 1 }}>Start Free Month →</span>
              </button>

              <a
                href={`tel:${CONTACT_PHONE}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  width: '100%',
                  padding: '14px 0',
                  background: 'rgba(23,197,176,0.04)',
                  border: '1px solid rgba(23,197,176,0.15)',
                  borderRadius: 12,
                  color: '#17C5B0',
                  fontSize: 14,
                  fontWeight: 600,
                  textDecoration: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
                </svg>
                Talk to a rep — call now
              </a>

              <button
                onClick={onClose}
                style={{
                  width: '100%',
                  padding: '12px 0',
                  background: 'none',
                  border: 'none',
                  color: '#6b7280',
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                I'll explore more first
              </button>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body,
  )
}

function TourCard({
  content,
  currentIndex,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
  visible,
  direction,
  autoPlaying,
  onToggleAuto,
  isMobile,
}: {
  content: TourContent
  currentIndex: number
  totalSteps: number
  onNext: () => void
  onPrev: () => void
  onSkip: () => void
  visible: boolean
  direction: 'next' | 'prev'
  autoPlaying: boolean
  onToggleAuto: () => void
  isMobile: boolean
}) {
  const isLast = currentIndex === totalSteps - 1
  const slideX = direction === 'next' ? 12 : -12

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
        transform: visible ? 'translateY(0) translateX(0)' : `translateY(${isMobile ? 20 : 4}px) translateX(${isMobile ? 0 : slideX}px)`,
        transition: 'opacity 0.3s cubic-bezier(0.16,1,0.3,1), transform 0.3s cubic-bezier(0.16,1,0.3,1)',
      }}
    >
      <div
        style={{
          background: 'linear-gradient(180deg, #131315 0%, #111113 100%)',
          border: isMobile ? 'none' : '1px solid #2a2a30',
          borderTop: '1px solid #2a2a30',
          borderRadius: isMobile ? '16px 16px 0 0' : 16,
          boxShadow: isMobile
            ? '0 -10px 40px rgba(0,0,0,0.8)'
            : '0 20px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(23,197,176,0.06), inset 0 1px 0 rgba(255,255,255,0.03)',
          padding: isMobile ? '20px 16px 28px' : '24px 24px 20px',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
      >
        {/* Step progress bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div style={{ display: 'flex', gap: 4, flex: 1, marginRight: 12 }}>
            {Array.from({ length: totalSteps }).map((_, i) => (
              <div
                key={i}
                style={{
                  flex: i === currentIndex ? 2.5 : 1,
                  height: 3,
                  borderRadius: 2,
                  background: i === currentIndex
                    ? '#17C5B0'
                    : i < currentIndex
                      ? 'rgba(23,197,176,0.4)'
                      : '#2a2a30',
                  transition: 'all 0.4s cubic-bezier(0.16,1,0.3,1)',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                {i === currentIndex && (
                  <div style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%)',
                    animation: 'tour-shimmer 2s ease-in-out infinite',
                  }} />
                )}
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <button
              onClick={onToggleAuto}
              title={autoPlaying ? 'Pause auto-play' : 'Auto-play tour'}
              style={{
                background: 'none',
                border: 'none',
                color: autoPlaying ? '#17C5B0' : '#6b7280',
                cursor: 'pointer',
                fontSize: 14,
                padding: '2px 4px',
                transition: 'color 0.15s',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              {autoPlaying ? '⏸' : '▶'}
            </button>
            <button
              onClick={onSkip}
              style={{
                background: 'none',
                border: 'none',
                color: '#6b7280',
                cursor: 'pointer',
                fontSize: 11,
                padding: '2px 6px',
                transition: 'color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = '#A1A1A8')}
              onMouseLeave={e => (e.currentTarget.style.color = '#6b7280')}
            >
              Skip
            </button>
          </div>
        </div>

        {/* Step counter */}
        <div style={{
          fontSize: 10,
          fontWeight: 600,
          color: '#17C5B0',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          marginBottom: 8,
          opacity: 0.7,
        }}>
          Step {currentIndex + 1} of {totalSteps}
        </div>

        {/* Title */}
        <h3
          style={{
            color: '#F5F5F7',
            fontSize: 18,
            fontWeight: 700,
            lineHeight: 1.3,
            margin: '0 0 8px',
          }}
        >
          {content.title}
        </h3>

        {/* Description */}
        <p
          style={{
            color: '#A1A1A8',
            fontSize: 14,
            lineHeight: 1.7,
            margin: '0 0 12px',
          }}
        >
          {content.description}
        </p>

        {/* Tip */}
        {content.tip && (
          <div
            style={{
              background: 'rgba(23, 197, 176, 0.05)',
              border: '1px solid rgba(23, 197, 176, 0.1)',
              borderRadius: 10,
              padding: '10px 12px',
              marginBottom: 16,
            }}
          >
            <p style={{ color: '#4FE3C1', fontSize: 13, lineHeight: 1.6, margin: 0 }}>
              <span style={{ marginRight: 6, opacity: 0.6 }}>&#9672;</span>
              {content.tip}
            </p>
          </div>
        )}

        {/* Auto-play progress bar */}
        {autoPlaying && (
          <div style={{
            height: 2, borderRadius: 1, background: '#2a2a30',
            marginBottom: 12, overflow: 'hidden',
          }}>
            <div style={{
              height: '100%', background: '#17C5B0', borderRadius: 1,
              animation: `tour-auto-progress ${AUTO_ADVANCE_MS}ms linear forwards`,
            }} />
          </div>
        )}

        {/* Navigation */}
        <div style={{ display: 'flex', gap: 8, marginTop: content.tip ? 0 : 4 }}>
          {currentIndex > 0 && (
            <button
              onClick={onPrev}
              style={{
                flex: 1,
                padding: '12px 0',
                background: 'none',
                border: '1px solid #2a2a30',
                borderRadius: 10,
                color: '#A1A1A8',
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: 500,
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#3a3a40'; e.currentTarget.style.color = '#F5F5F7' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2a30'; e.currentTarget.style.color = '#A1A1A8' }}
            >
              Back
            </button>
          )}
          <button
            onClick={onNext}
            style={{
              flex: 2,
              padding: '12px 0',
              background: 'linear-gradient(135deg, #17C5B0 0%, #14a899 100%)',
              border: 'none',
              borderRadius: 10,
              color: '#000',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 700,
              transition: 'all 0.15s',
              boxShadow: '0 2px 12px rgba(23,197,176,0.2)',
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 4px 16px rgba(23,197,176,0.3)' }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 2px 12px rgba(23,197,176,0.2)' }}
          >
            {isLast ? 'See My Results →' : 'Next →'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

export default function WalkthroughEngine() {
  const { businessType } = useDemoContext()
  const location = useLocation()
  const navigate = useNavigate()
  const isCanada = location.pathname.startsWith('/canada')
  const portalContext: PortalContext = isCanada ? 'canada' : 'us'
  const basePath = isCanada ? '/canada/demo' : '/demo'
  const isOverview = location.pathname === basePath || location.pathname === basePath + '/'

  const [active, setActive] = useState(false)
  const [step, setStep] = useState(0)
  const [spotlightRect, setSpotlightRect] = useState<SpotlightRect | null>(null)
  const [entering, setEntering] = useState(false)
  const [cardVisible, setCardVisible] = useState(false)
  const [direction, setDirection] = useState<'next' | 'prev'>('next')
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 1024)
  const [autoPlaying, setAutoPlaying] = useState(false)
  const [showCheckout, setShowCheckout] = useState(false)
  const bannerContainerRef = useRef<HTMLDivElement | null>(null)
  const [bannerMounted, setBannerMounted] = useState(false)
  const recalcRef = useRef<number>(0)
  const autoTimerRef = useRef<number>(0)
  const prevBusinessType = useRef<BusinessType | null>(businessType)
  const navPendingForStep = useRef<number>(-1)

  const tourSteps = useMemo(() => WALKTHROUGH_STEPS.filter(s => s.id !== 'checkout'), [])
  const currentStep = tourSteps[step] ?? tourSteps[0]
  const bt = businessType || 'restaurant'
  const content = getTourContent(currentStep.id, bt, portalContext)

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 1024)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    let attempts = 0
    const maxAttempts = 20

    function tryMount() {
      const main = document.querySelector('main')
      if (!main) {
        if (++attempts < maxAttempts) {
          setTimeout(tryMount, 100)
        }
        return
      }
      const div = document.createElement('div')
      div.id = 'tour-banner-root'
      main.prepend(div)
      bannerContainerRef.current = div
      setBannerMounted(true)
    }

    tryMount()
    return () => {
      const el = bannerContainerRef.current
      if (el) { el.remove(); bannerContainerRef.current = null }
    }
  }, [])

  useEffect(() => {
    if (prevBusinessType.current !== businessType && active) {
      setStep(0)
      setDirection('next')
    }
    prevBusinessType.current = businessType
  }, [businessType, active])

  // Auto-play timer
  useEffect(() => {
    if (!autoPlaying || !active || showCheckout) return
    autoTimerRef.current = window.setTimeout(() => {
      if (step < tourSteps.length - 1) {
        setDirection('next')
        setStep(s => s + 1)
      } else {
        setAutoPlaying(false)
        setShowCheckout(true)
      }
    }, AUTO_ADVANCE_MS)
    return () => clearTimeout(autoTimerRef.current)
  }, [autoPlaying, active, step, showCheckout, tourSteps.length])

  const calculateSpotlight = useCallback((retryCount = 0) => {
    const s = tourSteps[step]
    if (!s) return

    const findEl = () =>
      document.querySelector(s.elementSelector) || document.querySelector(s.fallbackSelector)

    const el = findEl()
    if (!el) {
      if (retryCount < 4) {
        setTimeout(() => calculateSpotlight(retryCount + 1), 150)
        return
      }
      setSpotlightRect(null)
      setEntering(false)
      setCardVisible(true)
      return
    }

    const bounds = el.getBoundingClientRect()

    // Element exists but has zero dimensions (animation hasn't started or stale ref)
    if (bounds.width < 10 || bounds.height < 10) {
      if (retryCount < 6) {
        setTimeout(() => calculateSpotlight(retryCount + 1), 120)
        return
      }
    }

    const main = document.querySelector('main')
    if (main) {
      const mainRect = main.getBoundingClientRect()
      const elCenter = bounds.top + bounds.height / 2
      const mainCenter = mainRect.top + mainRect.height / 2
      const scrollDelta = elCenter - mainCenter
      const needsScroll = Math.abs(scrollDelta) > mainRect.height * 0.35
      if (needsScroll) {
        main.scrollTo({ top: main.scrollTop + scrollDelta, behavior: 'smooth' })
        setTimeout(() => {
          const freshEl = findEl()
          if (!freshEl) return
          const fresh = freshEl.getBoundingClientRect()
          const pad = s.spotlightPadding
          setSpotlightRect({
            top: fresh.top - pad,
            left: fresh.left - pad,
            width: fresh.width + pad * 2,
            height: fresh.height + pad * 2,
          })
          setEntering(false)
          requestAnimationFrame(() => setCardVisible(true))
        }, 300)
        return
      }
    }

    const pad = s.spotlightPadding
    setSpotlightRect({
      top: bounds.top - pad,
      left: bounds.left - pad,
      width: bounds.width + pad * 2,
      height: bounds.height + pad * 2,
    })
    setEntering(false)
    requestAnimationFrame(() => setCardVisible(true))
  }, [step, tourSteps])

  useEffect(() => {
    if (!active || showCheckout) return
    const s = tourSteps[step]
    if (!s) return
    const targetPath = s.tabPath ? `${basePath}/${s.tabPath}` : basePath
    const atTarget = location.pathname === targetPath

    if (!atTarget) {
      // Need to navigate — mark this step as pending so the re-fire uses the right delay
      navPendingForStep.current = step
      setEntering(true)
      setSpotlightRect(null)
      setCardVisible(true)
      const main = document.querySelector('main')
      if (main) main.scrollTop = 0
      navigate(targetPath)
      return
    }

    // We're at the target path. Determine delay based on whether we just navigated.
    const justNavigated = navPendingForStep.current === step
    navPendingForStep.current = -1
    const delay = justNavigated ? 500 : 80

    recalcRef.current = window.setTimeout(calculateSpotlight, delay)
    return () => clearTimeout(recalcRef.current)
  }, [active, step, basePath, navigate, location.pathname, calculateSpotlight, showCheckout, tourSteps])

  useEffect(() => {
    if (!active) return
    const handler = () => calculateSpotlight()
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [active, calculateSpotlight])

  useEffect(() => {
    if (!active) return
    const handler = (e: KeyboardEvent) => {
      if (showCheckout) {
        if (e.key === 'Escape') handleSkip()
        return
      }
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault()
        handleNext()
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        handlePrev()
      } else if (e.key === 'Escape') {
        handleSkip()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [active, step, showCheckout])

  function handleStart(auto = false) {
    setStep(0)
    setDirection('next')
    setActive(true)
    setAutoPlaying(auto)
    setShowCheckout(false)
  }

  function handleNext() {
    clearTimeout(autoTimerRef.current)
    if (step < tourSteps.length - 1) {
      setDirection('next')
      setStep(s => s + 1)
    } else {
      setShowCheckout(true)
      setSpotlightRect(null)
      setCardVisible(false)
    }
  }

  function handlePrev() {
    clearTimeout(autoTimerRef.current)
    if (step > 0) {
      setDirection('prev')
      setStep(s => s - 1)
    }
  }

  function handleSkip() {
    setActive(false)
    setSpotlightRect(null)
    setCardVisible(false)
    setEntering(false)
    setAutoPlaying(false)
    setShowCheckout(false)
    localStorage.setItem(LS_KEY, 'true')
  }

  function handleToggleAuto() {
    setAutoPlaying(p => !p)
  }

  return (
    <>
      {/* Tour launcher banner removed 2026-06-11 (Aidan) — the walkthrough
          engine stays intact; nothing currently triggers it. */}

      {/* Floating step counter — only when tour is active */}
      {active && !showCheckout && createPortal(
        <div style={{
          position: 'fixed',
          top: isMobile ? 16 : 'auto',
          bottom: isMobile ? 'auto' : 24,
          left: isMobile ? '50%' : 24,
          transform: isMobile ? 'translateX(-50%)' : 'none',
          zIndex: 9997,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: '#111113',
          border: '1px solid #2a2a30',
          borderRadius: 10,
          padding: '8px 14px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
        }}>
          <div style={{
            width: 7, height: 7, borderRadius: '50%',
            background: '#17C5B0',
            boxShadow: '0 0 6px rgba(23,197,176,0.5)',
            animation: 'tour-pulse 1.5s ease-in-out infinite',
          }} />
          <span style={{ color: '#A1A1A8', fontSize: 12, fontWeight: 500 }}>
            {step + 1} / {tourSteps.length}
          </span>
          {autoPlaying && (
            <span style={{ color: '#17C5B0', fontSize: 10, fontWeight: 600, letterSpacing: '0.05em' }}>AUTO</span>
          )}
          <button
            onClick={handleSkip}
            style={{
              background: 'none', border: 'none', color: '#6b7280',
              cursor: 'pointer', fontSize: 14, padding: '0 2px',
              lineHeight: 1, transition: 'color 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#F5F5F7')}
            onMouseLeave={e => (e.currentTarget.style.color = '#6b7280')}
          >
            &times;
          </button>
        </div>,
        document.body,
      )}

      {/* Active tour overlay + card */}
      {active && !showCheckout && (
        <>
          <SpotlightOverlay rect={spotlightRect} entering={entering} />
          <TourCard
            content={content}
            currentIndex={step}
            totalSteps={tourSteps.length}
            onNext={handleNext}
            onPrev={handlePrev}
            onSkip={handleSkip}
            visible={cardVisible}
            direction={direction}
            autoPlaying={autoPlaying}
            onToggleAuto={handleToggleAuto}
            isMobile={isMobile}
          />
        </>
      )}

      {/* Checkout screen */}
      {showCheckout && (
        <CheckoutScreen onClose={handleSkip} isCanada={isCanada} isMobile={isMobile} />
      )}

      <style>{`
        @keyframes tour-ring-pulse {
          0%, 100% { border-color: rgba(23, 197, 176, 0.5); }
          50% { border-color: rgba(23, 197, 176, 0.2); }
        }
        @keyframes tour-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes tour-shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes tour-lava-drift {
          0%   { background-position: 0% 50%; }
          50%  { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        @keyframes tour-glow-breathe {
          0%, 100% { opacity: 0.4; }
          40% { opacity: 0.7; }
          70% { opacity: 0.5; }
        }
        @keyframes tour-sparkle-ping {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0; }
        }
        @keyframes tour-auto-progress {
          0% { width: 0%; }
          100% { width: 100%; }
        }
        @keyframes tour-fade-in {
          0% { opacity: 0; }
          100% { opacity: 1; }
        }

        .tour-banner {
          display: flex;
          justify-content: center;
          padding: 12px 16px 0;
          max-width: 896px;
          margin: 0 auto;
        }

        .tour-glow-btn-wrapper {
          position: relative;
          display: flex;
          align-items: center;
          width: 100%;
          max-width: 480px;
          padding: 14px 22px;
          border: none;
          border-radius: 14px;
          cursor: pointer;
          background: transparent;
          overflow: hidden;
        }

        .tour-glow-btn-bg {
          position: absolute;
          inset: 0;
          border-radius: 14px;
          background: linear-gradient(135deg, rgba(23,197,176,0.10) 0%, rgba(26,143,214,0.08) 50%, rgba(23,197,176,0.10) 100%);
          border: 1px solid rgba(23,197,176,0.18);
          transition: all 0.6s ease;
        }
        .tour-glow-btn-bg::before {
          content: '';
          position: absolute;
          inset: -1px;
          border-radius: 15px;
          background: linear-gradient(
            270deg,
            rgba(23,197,176,0.0) 0%,
            rgba(23,197,176,0.18) 20%,
            rgba(26,143,214,0.14) 40%,
            rgba(23,197,176,0.0) 55%,
            rgba(26,143,214,0.12) 75%,
            rgba(23,197,176,0.16) 90%,
            rgba(23,197,176,0.0) 100%
          );
          background-size: 300% 100%;
          animation: tour-lava-drift 8s ease-in-out infinite;
          z-index: -1;
        }
        .tour-glow-btn-bg::after {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: 14px;
          box-shadow: 0 0 15px rgba(23,197,176,0.08), inset 0 0 12px rgba(23,197,176,0.02);
          animation: tour-glow-breathe 6s ease-in-out infinite;
        }

        .tour-glow-btn-wrapper:hover .tour-glow-btn-bg {
          border-color: rgba(23,197,176,0.35);
          background: linear-gradient(135deg, rgba(23,197,176,0.15) 0%, rgba(26,143,214,0.12) 50%, rgba(23,197,176,0.15) 100%);
        }
        .tour-glow-btn-wrapper:hover .tour-glow-btn-bg::after {
          box-shadow: 0 0 25px rgba(23,197,176,0.18), 0 0 50px rgba(23,197,176,0.06), inset 0 0 20px rgba(23,197,176,0.04);
        }

        .tour-glow-btn-content {
          position: relative;
          display: flex;
          align-items: center;
          gap: 10px;
          width: 100%;
          z-index: 1;
        }

        .tour-glow-sparkle {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
          flex-shrink: 0;
        }
        .tour-glow-sparkle-ping {
          position: absolute;
          inset: -2px;
          border-radius: 50%;
          background: rgba(23,197,176,0.15);
          animation: tour-sparkle-ping 4s ease-in-out infinite;
        }
        .tour-glow-sparkle-icon {
          position: relative;
          color: #17C5B0;
          filter: drop-shadow(0 0 4px rgba(23,197,176,0.4));
        }

        .tour-glow-text {
          color: #F5F5F7;
          font-size: 15px;
          font-weight: 700;
          letter-spacing: -0.01em;
        }
        .tour-glow-hint {
          color: #6b7280;
          font-weight: 400;
          font-size: 12px;
          margin-left: auto;
        }

        @media (max-width: 480px) {
          .tour-glow-hint { display: none; }
          .tour-glow-btn-wrapper { max-width: 100%; }
        }

        .tour-glow-btn {
          position: relative;
          overflow: hidden;
        }
        .tour-glow-btn::before {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 50%, transparent 100%);
          transform: translateX(-100%);
          animation: tour-shimmer 3s ease-in-out infinite;
        }
      `}</style>
    </>
  )
}
