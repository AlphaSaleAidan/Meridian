import { useEffect, useRef, useState } from 'react'
import { useInView } from 'framer-motion'

interface Props {
  end: number
  prefix?: string
  suffix?: string
  duration?: number
  className?: string
}

/**
 * Animated count-up that triggers when entering viewport.
 * Uses font-mono for numeric display.
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
  const [value, setValue] = useState(0)

  useEffect(() => {
    if (!isInView) return

    const start = 0
    const startTime = performance.now()

    const tick = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(start + (end - start) * eased))
      if (progress < 1) requestAnimationFrame(tick)
    }

    requestAnimationFrame(tick)
  }, [isInView, end, duration])

  return (
    <span ref={ref} className={`font-mono ${className}`}>
      {prefix}{value.toLocaleString()}{suffix}
    </span>
  )
}
