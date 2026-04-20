import { useRef, type ReactNode, type MouseEvent } from 'react'

interface Props {
  children: ReactNode
  className?: string
  maxTilt?: number
  glowColor?: string
}

/**
 * Dashboard card with 3D tilt on mouse hover.
 * Adds a subtle glow and perspective transform.
 */
export default function DashboardTiltCard({
  children,
  className = '',
  maxTilt = 4,
  glowColor = 'rgba(124, 92, 255, 0.06)',
}: Props) {
  const ref = useRef<HTMLDivElement>(null)

  const handleMove = (e: MouseEvent) => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    const rotateX = -y * maxTilt
    const rotateY = x * maxTilt
    ref.current.style.transform =
      `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.005, 1.005, 1.005)`
    ref.current.style.boxShadow =
      `0 8px 32px ${glowColor}, 0 0 0 1px rgba(124, 92, 255, 0.08)`
  }

  const handleLeave = () => {
    if (!ref.current) return
    ref.current.style.transform =
      'perspective(600px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)'
    ref.current.style.boxShadow = ''
  }

  return (
    <div
      ref={ref}
      className={className}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      style={{
        transition: 'transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.35s ease',
        transformStyle: 'preserve-3d',
        willChange: 'transform',
      }}
    >
      {children}
    </div>
  )
}
