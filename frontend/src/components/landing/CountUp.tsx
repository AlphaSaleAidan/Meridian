import { useEffect, useRef, useState } from 'react'
import { useInView, useReducedMotion } from 'framer-motion'

interface Props {
  end: number
  prefix?: string
  suffix?: string
  duration?: number
  className?: string
}

/**
 * Animated count-up that triggers when entering viewport.
 *
 * Static-render value is the FINAL number (not 0) so non-scrolling renderers —
 * Googlebot, LinkedIn link unfurler, Twitter cards, OG screenshot tools — see
 * the real social-proof number in our marketing copy instead of $0/0%/0s.
 * When the viewport actually scrolls past, we snap back and animate up.
 * Honors prefers-reduced-motion by skipping animation entirely.
 */
export default function CountUp({
  end,
  prefix = '',
  suffix = '',
  duration = 2000,
  className = '',
}: Props) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px' })
  const reduceMotion = useReducedMotion()
  const [value, setValue] = useState(end)
  const animatedRef = useRef(false)

  useEffect(() => {
    if (!isInView || animatedRef.current || reduceMotion) return
    animatedRef.current = true
    setValue(0)
    const startTime = performance.now()

    const tick = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(end * eased))
      if (progress < 1) requestAnimationFrame(tick)
    }

    requestAnimationFrame(tick)
  }, [isInView, end, duration, reduceMotion])

  return (
    <span ref={ref} className={`font-mono ${className}`}>
      {prefix}{value.toLocaleString()}{suffix}
    </span>
  )
}
