import { useState, useEffect, useCallback, useRef } from 'react'
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

interface SpotlightRect {
  top: number
  left: number
  width: number
  height: number
}

function SpotlightOverlay({ rect, transitioning }: { rect: SpotlightRect | null; transitioning: boolean }) {
  if (!rect) return null
  const maskId = 'tour-spotlight-mask'

  return createPortal(
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9998,
        pointerEvents: 'none',
        opacity: transitioning ? 0 : 1,
        transition: 'opacity 0.2s ease',
      }}
    >
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
        <defs>
          <mask id={maskId}>
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            <rect
              x={rect.left}
              y={rect.top}
              width={rect.width}
              height={rect.height}
              rx={12}
              fill="black"
            >
              <animate attributeName="x" to={rect.left} dur="0.01s" fill="freeze" />
            </rect>
          </mask>
        </defs>
        <rect
          x="0" y="0" width="100%" height="100%"
          fill="rgba(0, 0, 0, 0.65)"
          mask={`url(#${maskId})`}
        />
        <rect
          x={rect.left - 2}
          y={rect.top - 2}
          width={rect.width + 4}
          height={rect.height + 4}
          rx={14}
          fill="none"
          stroke="#17C5B0"
          strokeWidth="2"
          opacity="0.6"
        >
          <animate
            attributeName="opacity"
            values="0.6;0.25;0.6"
            dur="2s"
            repeatCount="indefinite"
          />
        </rect>
      </svg>
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
}: {
  content: TourContent
  currentIndex: number
  totalSteps: number
  onNext: () => void
  onPrev: () => void
  onSkip: () => void
  visible: boolean
}) {
  const isLast = currentIndex === totalSteps - 1

  return createPortal(
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 9999,
        width: 420,
        maxHeight: '75vh',
        overflowY: 'auto',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(8px)',
        transition: 'opacity 0.25s ease, transform 0.25s ease',
        pointerEvents: visible ? 'auto' : 'none',
      }}
    >
      <div
        style={{
          background: '#111113',
          border: '1px solid #2a2a30',
          borderRadius: 14,
          boxShadow: '0 16px 48px rgba(0,0,0,0.6), 0 0 0 1px rgba(23,197,176,0.08)',
          padding: '24px 24px 20px',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
      >
        {/* Step dots */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 5 }}>
            {Array.from({ length: totalSteps }).map((_, i) => (
              <div
                key={i}
                style={{
                  width: i === currentIndex ? 18 : 6,
                  height: 6,
                  borderRadius: 3,
                  background: i === currentIndex ? '#17C5B0' : i < currentIndex ? 'rgba(23,197,176,0.35)' : '#2a2a30',
                  transition: 'all 0.3s ease',
                }}
              />
            ))}
          </div>
          <button
            onClick={onSkip}
            style={{
              background: 'none',
              border: 'none',
              color: '#6b7280',
              cursor: 'pointer',
              fontSize: 11,
              padding: '2px 6px',
            }}
          >
            Skip
          </button>
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
              background: 'rgba(23, 197, 176, 0.06)',
              border: '1px solid rgba(23, 197, 176, 0.12)',
              borderRadius: 8,
              padding: '10px 12px',
              marginBottom: 16,
            }}
          >
            <p style={{ color: '#4FE3C1', fontSize: 13, lineHeight: 1.6, margin: 0 }}>
              {content.tip}
            </p>
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
              }}
            >
              Back
            </button>
          )}
          <button
            onClick={onNext}
            style={{
              flex: 2,
              padding: '12px 0',
              background: '#17C5B0',
              border: 'none',
              borderRadius: 10,
              color: '#000',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 700,
            }}
          >
            {isLast ? 'Get Started' : 'Next'}
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

  const [active, setActive] = useState(false)
  const [step, setStep] = useState(0)
  const [spotlightRect, setSpotlightRect] = useState<SpotlightRect | null>(null)
  const [transitioning, setTransitioning] = useState(false)
  const [cardVisible, setCardVisible] = useState(false)
  const recalcRef = useRef<number>(0)
  const prevBusinessType = useRef<BusinessType | null>(businessType)

  const currentStep = WALKTHROUGH_STEPS[step]
  const bt = businessType || 'restaurant'
  const content = getTourContent(currentStep.id, bt, portalContext)

  useEffect(() => {
    if (prevBusinessType.current !== businessType && active) {
      setStep(0)
    }
    prevBusinessType.current = businessType
  }, [businessType, active])

  const calculateSpotlight = useCallback(() => {
    const s = WALKTHROUGH_STEPS[step]
    let el = document.querySelector(s.elementSelector)
    if (!el) el = document.querySelector(s.fallbackSelector)
    if (!el) {
      setSpotlightRect(null)
      setTransitioning(false)
      setCardVisible(true)
      return
    }
    const bounds = el.getBoundingClientRect()
    const pad = s.spotlightPadding
    setSpotlightRect({
      top: bounds.top - pad,
      left: bounds.left - pad,
      width: bounds.width + pad * 2,
      height: bounds.height + pad * 2,
    })
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setTransitioning(false)
    requestAnimationFrame(() => setCardVisible(true))
  }, [step])

  useEffect(() => {
    if (!active) return
    const s = WALKTHROUGH_STEPS[step]
    const targetPath = s.tabPath ? `${basePath}/${s.tabPath}` : basePath
    const needsNav = location.pathname !== targetPath

    setCardVisible(false)
    setTransitioning(true)

    if (needsNav) {
      navigate(targetPath)
    }

    // Retry finding the element a few times for lazy-loaded pages
    let attempts = 0
    const tryFind = () => {
      const el = document.querySelector(s.elementSelector) || document.querySelector(s.fallbackSelector)
      if (el || attempts >= 6) {
        calculateSpotlight()
      } else {
        attempts++
        recalcRef.current = window.setTimeout(tryFind, 120)
      }
    }

    recalcRef.current = window.setTimeout(tryFind, needsNav ? 150 : 50)
    return () => clearTimeout(recalcRef.current)
  }, [active, step, basePath, navigate, location.pathname, calculateSpotlight])

  useEffect(() => {
    if (!active) return
    const handler = () => calculateSpotlight()
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [active, calculateSpotlight])

  useEffect(() => {
    if (!active) return
    const handler = (e: KeyboardEvent) => {
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
  })

  function handleStart() {
    setStep(0)
    setActive(true)
  }

  function handleNext() {
    if (step < WALKTHROUGH_STEPS.length - 1) {
      setStep(s => s + 1)
    } else {
      handleSkip()
      localStorage.setItem(LS_KEY, 'completed')
    }
  }

  function handlePrev() {
    if (step > 0) setStep(s => s - 1)
  }

  function handleSkip() {
    setActive(false)
    setSpotlightRect(null)
    setCardVisible(false)
    setTransitioning(false)
    localStorage.setItem(LS_KEY, 'true')
  }

  return (
    <>
      {createPortal(
        <div style={{ position: 'fixed', bottom: 24, left: 24, zIndex: 9997 }}>
          {active ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: '#111113',
                border: '1px solid #2a2a30',
                borderRadius: 8,
                padding: '7px 12px',
              }}
            >
              <div
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: '#17C5B0',
                  animation: 'tour-pulse 1.5s ease-in-out infinite',
                }}
              />
              <span style={{ color: '#A1A1A8', fontSize: 12, fontWeight: 500 }}>
                {step + 1} / {WALKTHROUGH_STEPS.length}
              </span>
              <button
                onClick={handleSkip}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#6b7280',
                  cursor: 'pointer',
                  fontSize: 14,
                  padding: '0 2px',
                  lineHeight: 1,
                }}
              >
                &times;
              </button>
            </div>
          ) : (
            <button
              onClick={handleStart}
              style={{
                background: '#111113',
                border: '1px solid rgba(23, 197, 176, 0.3)',
                borderRadius: 8,
                padding: '8px 14px',
                color: '#17C5B0',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transition: 'border-color 0.2s',
              }}
            >
              Take a Tour
            </button>
          )}
        </div>,
        document.body,
      )}

      {active && (
        <>
          <SpotlightOverlay rect={spotlightRect} transitioning={transitioning} />
          <TourCard
            content={content}
            currentIndex={step}
            totalSteps={WALKTHROUGH_STEPS.length}
            onNext={handleNext}
            onPrev={handlePrev}
            onSkip={handleSkip}
            visible={cardVisible}
          />
        </>
      )}

      <style>{`
        @keyframes tour-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </>
  )
}
