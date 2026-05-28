import { useRef, useCallback, type ReactNode, type MouseEvent } from 'react'

interface Props {
  children: ReactNode
  className?: string
  onClick?: () => void
  strength?: number
  style?: React.CSSProperties
}

/**
 * Button with magnetic cursor pull effect (2-4px).
 * On hover, the button content subtly shifts toward the cursor.
 * Uses direct DOM manipulation via ref to avoid re-renders on every mousemove.
 */
export default function MagneticButton({
  children,
  className = '',
  onClick,
  strength = 0.3,
  style: externalStyle,
}: Props) {
  const ref = useRef<HTMLButtonElement>(null)

  const handleMove = useCallback((e: MouseEvent) => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const x = (e.clientX - rect.left - rect.width / 2) * strength
    const y = (e.clientY - rect.top - rect.height / 2) * strength
    ref.current.style.transform = `translate(${x}px, ${y}px)`
    ref.current.style.transition = 'transform 0.15s ease-out'
  }, [strength])

  const handleLeave = useCallback(() => {
    if (!ref.current) return
    ref.current.style.transform = ''
    ref.current.style.transition = 'transform 0.4s ease-out'
  }, [])

  return (
    <button
      ref={ref}
      className={className}
      onClick={onClick}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      style={externalStyle}
    >
      {children}
    </button>
  )
}
