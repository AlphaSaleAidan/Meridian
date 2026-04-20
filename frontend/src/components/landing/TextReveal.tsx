import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1]

interface Props {
  children: ReactNode
  delay?: number
  className?: string
}

/**
 * Staggered text-mask reveal: each line slides up with opacity fade.
 * Wrap each line in a TextReveal for the effect.
 */
export function TextRevealLine({ children, delay = 0, className = '' }: Props) {
  return (
    <span className="block overflow-hidden">
      <motion.span
        className={`block ${className}`}
        initial={{ y: '100%', opacity: 0 }}
        animate={{ y: '0%', opacity: 1 }}
        transition={{ duration: 0.8, ease: EASE, delay }}
      >
        {children}
      </motion.span>
    </span>
  )
}

/**
 * Stagger container for hero text — delays each child.
 */
export function TextRevealStagger({
  children,
  staggerDelay = 0.06,
  baseDelay = 0.2,
  className = '',
}: {
  children: ReactNode[]
  staggerDelay?: number
  baseDelay?: number
  className?: string
}) {
  return (
    <div className={className}>
      {(children as ReactNode[]).map((child, i) => (
        <TextRevealLine key={i} delay={baseDelay + i * staggerDelay}>
          {child}
        </TextRevealLine>
      ))}
    </div>
  )
}
