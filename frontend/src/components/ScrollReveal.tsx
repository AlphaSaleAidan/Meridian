import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { useEffect, useState, type ReactNode } from 'react'

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1]

const variants: Record<string, Variants> = {
  fadeUp: {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
  },
  fadeIn: {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.5, ease: EASE } },
  },
  slideRight: {
    hidden: { opacity: 0, x: -16 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.5, ease: EASE } },
  },
  scaleIn: {
    hidden: { opacity: 0, scale: 0.95 },
    visible: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: EASE } },
  },
}

interface Props {
  children: ReactNode
  variant?: keyof typeof variants
  delay?: number
  className?: string
  once?: boolean
}

/**
 * Scroll-triggered reveal.
 *
 * Bots, link unfurlers (LinkedIn/Twitter cards), and prefers-reduced-motion
 * users skip the animation entirely so content is always present in the
 * static render. We also force-reveal after 1.2s as a safety net for any
 * IntersectionObserver edge case (PDF renderers, headless screenshotters).
 */
export default function ScrollReveal({
  children,
  variant = 'fadeUp',
  delay = 0,
  className = '',
  once = true,
}: Props) {
  const reducedMotion = useReducedMotion()
  const [forceVisible, setForceVisible] = useState(false)

  useEffect(() => {
    if (reducedMotion) return
    const t = setTimeout(() => setForceVisible(true), 1200)
    return () => clearTimeout(t)
  }, [reducedMotion])

  if (reducedMotion) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      initial="hidden"
      animate={forceVisible ? 'visible' : undefined}
      whileInView="visible"
      viewport={{ once, amount: 'some' }}
      variants={variants[variant]}
      transition={{ delay }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

/** Staggered container for child animations */
export function StaggerContainer({
  children,
  className = '',
  staggerDelay = 0.06,
  ...rest
}: {
  children: ReactNode
  className?: string
  staggerDelay?: number
  [key: string]: unknown
}) {
  const reducedMotion = useReducedMotion()
  const [forceVisible, setForceVisible] = useState(false)

  useEffect(() => {
    if (reducedMotion) return
    const t = setTimeout(() => setForceVisible(true), 1200)
    return () => clearTimeout(t)
  }, [reducedMotion])

  if (reducedMotion) {
    return <div className={className} {...rest}>{children}</div>
  }

  return (
    <motion.div
      initial="hidden"
      animate={forceVisible ? 'visible' : undefined}
      whileInView="visible"
      viewport={{ once: true, amount: 'some' }}
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: staggerDelay } },
      }}
      {...rest}
      className={className}
    >
      {children}
    </motion.div>
  )
}

export function StaggerItem({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  const reducedMotion = useReducedMotion()
  if (reducedMotion) {
    return <div className={className}>{children}</div>
  }
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 16 },
        visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } },
      }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
