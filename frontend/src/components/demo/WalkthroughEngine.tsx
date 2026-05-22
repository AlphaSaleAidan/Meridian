import { useState, useEffect, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDemoContext, type BusinessType } from '@/lib/demo-context'
import {
  WALKTHROUGH_STEPS,
  getWalkthroughContent,
  getStepName,
  type PortalContext,
  type CoachingContent,
  type WalkthroughStep,
} from './walkthrough-content'

const LS_DISMISSED = 'meridian_walkthrough_dismissed'

interface SpotlightRect {
  top: number
  left: number
  width: number
  height: number
}

function SpotlightOverlay({ rect }: { rect: SpotlightRect | null }) {
  if (!rect) return null

  const maskId = 'walkthrough-spotlight-mask'

  return createPortal(
    <div style={{ position: 'fixed', inset: 0, zIndex: 9998, pointerEvents: 'none' }}>
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
            />
          </mask>
        </defs>
        <rect
          x="0" y="0" width="100%" height="100%"
          fill="rgba(0, 0, 0, 0.72)"
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
          opacity="0.7"
        >
          <animate
            attributeName="opacity"
            values="0.7;0.3;0.7"
            dur="2s"
            repeatCount="indefinite"
          />
        </rect>
      </svg>
    </div>,
    document.body,
  )
}

function CoachingCard({
  step,
  content,
  stepName,
  currentIndex,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
}: {
  step: WalkthroughStep
  content: CoachingContent
  stepName: string
  currentIndex: number
  totalSteps: number
  onNext: () => void
  onPrev: () => void
  onSkip: () => void
}) {
  return createPortal(
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 9999,
        width: 380,
        maxHeight: '72vh',
        overflowY: 'auto',
      }}
    >
      <div
        style={{
          background: '#0d1117',
          border: '1px solid rgba(23, 197, 176, 0.4)',
          borderRadius: 12,
          boxShadow: '0 0 40px rgba(23, 197, 176, 0.12), 0 20px 60px rgba(0,0,0,0.5)',
          padding: 20,
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span
              style={{
                background: '#17C5B0',
                color: '#000',
                borderRadius: 20,
                padding: '2px 10px',
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: '0.05em',
              }}
            >
              STEP {currentIndex + 1} OF {totalSteps}
            </span>
            <span style={{ color: '#f0f6fc', fontSize: 13, fontWeight: 600 }}>
              {stepName}
            </span>
          </div>
          <button
            onClick={onSkip}
            style={{
              background: 'none',
              border: 'none',
              color: '#8b949e',
              cursor: 'pointer',
              fontSize: 12,
              padding: '4px 8px',
            }}
          >
            Skip tour
          </button>
        </div>

        {/* Progress bar */}
        <div style={{ height: 2, background: '#21262d', borderRadius: 1, marginBottom: 16 }}>
          <div
            style={{
              height: '100%',
              width: `${((currentIndex + 1) / totalSteps) * 100}%`,
              background: '#17C5B0',
              borderRadius: 1,
              transition: 'width 0.3s ease',
            }}
          />
        </div>

        {/* Say This */}
        <div
          style={{
            background: 'rgba(23, 197, 176, 0.05)',
            border: '1px solid rgba(23, 197, 176, 0.15)',
            borderRadius: 8,
            padding: '12px 14px',
            marginBottom: 12,
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: '#17C5B0',
              letterSpacing: '0.08em',
              marginBottom: 6,
            }}
          >
            SAY THIS
          </div>
          <p
            style={{
              color: '#f0f6fc',
              fontSize: 13,
              lineHeight: '1.6',
              margin: 0,
              whiteSpace: 'pre-line',
            }}
          >
            {content.sayThis}
          </p>
        </div>

        {/* Likely response */}
        <details style={{ marginBottom: 12 }}>
          <summary
            style={{
              color: '#8b949e',
              fontSize: 12,
              cursor: 'pointer',
              userSelect: 'none',
              padding: '4px 0',
            }}
          >
            If they ask: &ldquo;{content.likelyResponse}&rdquo;
          </summary>
          <div
            style={{
              background: 'rgba(240, 180, 41, 0.05)',
              border: '1px solid rgba(240, 180, 41, 0.15)',
              borderRadius: 6,
              padding: '10px 12px',
              marginTop: 8,
            }}
          >
            <p style={{ color: '#d4b86a', fontSize: 12, lineHeight: '1.5', margin: 0 }}>
              {content.likelyAnswer}
            </p>
          </div>
        </details>

        {/* Why it works */}
        <details style={{ marginBottom: 12 }}>
          <summary
            style={{
              color: '#8b949e',
              fontSize: 12,
              cursor: 'pointer',
              userSelect: 'none',
              padding: '4px 0',
            }}
          >
            Why this works
          </summary>
          <div
            style={{
              background: 'rgba(124, 92, 255, 0.05)',
              border: '1px solid rgba(124, 92, 255, 0.12)',
              borderRadius: 6,
              padding: '10px 12px',
              marginTop: 8,
            }}
          >
            <p style={{ color: '#a78bfa', fontSize: 12, lineHeight: '1.5', margin: 0 }}>
              {content.whyItWorks}
            </p>
          </div>
        </details>

        {/* What to do */}
        <div
          style={{
            background: 'rgba(63, 185, 80, 0.05)',
            border: '1px solid rgba(63, 185, 80, 0.1)',
            borderRadius: 6,
            padding: '10px 12px',
            marginBottom: 16,
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: '#3fb950',
              letterSpacing: '0.08em',
              marginBottom: 4,
            }}
          >
            WHAT TO DO
          </div>
          <p style={{ color: '#8b949e', fontSize: 12, lineHeight: '1.5', margin: 0 }}>
            {content.whatToDo}
          </p>
        </div>

        {/* Navigation */}
        <div style={{ display: 'flex', gap: 8 }}>
          {currentIndex > 0 && (
            <button
              onClick={onPrev}
              style={{
                flex: 1,
                padding: 10,
                background: 'none',
                border: '1px solid #21262d',
                borderRadius: 6,
                color: '#8b949e',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              &larr; Back
            </button>
          )}
          <button
            onClick={onNext}
            style={{
              flex: 2,
              padding: 10,
              background: currentIndex === totalSteps - 1 ? '#3fb950' : '#17C5B0',
              border: 'none',
              borderRadius: 6,
              color: '#000',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 700,
            }}
          >
            {currentIndex === totalSteps - 1 ? 'Done' : 'Next →'}
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
  const recalcRef = useRef<number>(0)
  const prevBusinessType = useRef<BusinessType | null>(businessType)

  const currentStep = WALKTHROUGH_STEPS[step]
  const bt = businessType || 'restaurant'
  const content = getWalkthroughContent(currentStep.id, bt, portalContext)

  // Reset walkthrough when business type changes
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
  }, [step])

  // Navigate to the correct tab and then spotlight
  useEffect(() => {
    if (!active) return
    const s = WALKTHROUGH_STEPS[step]
    const targetPath = s.tabPath ? `${basePath}/${s.tabPath}` : basePath

    if (location.pathname !== targetPath) {
      navigate(targetPath)
    }

    // Wait for the page to render, then calculate spotlight
    recalcRef.current = window.setTimeout(calculateSpotlight, 400)
    return () => clearTimeout(recalcRef.current)
  }, [active, step, basePath, navigate, location.pathname, calculateSpotlight])

  // Recalc on resize
  useEffect(() => {
    if (!active) return
    const handler = () => calculateSpotlight()
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [active, calculateSpotlight])

  // Keyboard nav
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
      localStorage.setItem(LS_DISMISSED, 'completed')
    }
  }

  function handlePrev() {
    if (step > 0) setStep(s => s - 1)
  }

  function handleSkip() {
    setActive(false)
    setSpotlightRect(null)
    localStorage.setItem(LS_DISMISSED, 'true')
  }

  return (
    <>
      {/* Trigger button — always visible in demo */}
      {createPortal(
        <div
          style={{
            position: 'fixed',
            top: 16,
            right: isCanada ? 16 : 16,
            zIndex: 9997,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 36,
          }}
        >
          {active ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: '#0d1117',
                border: '1px solid rgba(23, 197, 176, 0.4)',
                borderRadius: 8,
                padding: '8px 12px',
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: '#17C5B0',
                  animation: 'walkthrough-pulse 1.5s ease-in-out infinite',
                }}
              />
              <span style={{ color: '#f0f6fc', fontSize: 12, fontWeight: 600 }}>
                Step {step + 1}/{WALKTHROUGH_STEPS.length}
              </span>
              <button
                onClick={handleSkip}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#8b949e',
                  cursor: 'pointer',
                  fontSize: 14,
                  padding: '0 4px',
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
                background: '#17C5B0',
                border: 'none',
                borderRadius: 8,
                padding: '8px 16px',
                color: '#000',
                fontSize: 13,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                boxShadow: '0 4px 20px rgba(23, 197, 176, 0.3)',
              }}
            >
              &#9654; Start Walkthrough
            </button>
          )}
        </div>,
        document.body,
      )}

      {/* Spotlight + coaching card when active */}
      {active && (
        <>
          <SpotlightOverlay rect={spotlightRect} />
          <CoachingCard
            step={currentStep}
            content={content}
            stepName={getStepName(currentStep.id, bt)}
            currentIndex={step}
            totalSteps={WALKTHROUGH_STEPS.length}
            onNext={handleNext}
            onPrev={handlePrev}
            onSkip={handleSkip}
          />
        </>
      )}

      {/* Pulse animation keyframes */}
      <style>{`
        @keyframes walkthrough-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </>
  )
}
