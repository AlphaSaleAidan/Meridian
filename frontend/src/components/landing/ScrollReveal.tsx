import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { useEffect, useState, type ReactNode } from 'react'

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1]

const variants: Record<string, Variants> = {
  fadeUp: {
    hidden: { opacity: 0, y: 24 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: EASE } },
  },
  fadeIn: {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.6, ease: EASE } },
  },
  clipReveal: {
    hidden: { clipPath: 'inset(50% 50% 50% 50%)', opacity: 0 },
    visible: {
      clipPath: 'inset(0% 0% 0% 0%)',
      opacity: 1,
      transition: { duration: 0.8, ease: EASE },
    },
  },
}

interface Props {
  children: ReactNode
  variant?: 'fadeUp' | 'fadeIn' | 'clipReveal'
  delay?: number
  className?: string
  once?: boolean
}

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
