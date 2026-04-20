import { useRef, useState, type ReactNode, type MouseEvent } from 'react'

interface Props {
  children: ReactNode
  className?: string
  onClick?: () => void
  strength?: number
}

/**
 * Button with magnetic cursor pull effect (2-4px).
 * On hover, the button content subtly shifts toward the cursor.
 */
export default function MagneticButton({
  children,
  className = '',
  onClick,
  strength = 0.3,
}: Props) {
  const ref = useRef<HTMLButtonElement>(null)
  const [transform, setTransform] = useState('')

  const handleMove = (e: MouseEvent) => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const x = (e.clientX - rect.left - rect.width / 2) * strength
    const y = (e.clientY - rect.top - rect.height / 2) * strength
    setTransform(`translate(${x}px, ${y}px)`)
  }

  const handleLeave = () => setTransform('')

  return (
    <button
      ref={ref}
      className={className}
      onClick={onClick}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      style={{
        transform,
        transition: transform ? 'transform 0.15s ease-out' : 'transform 0.4s ease-out',
      }}
    >
      {children}
    </button>
  )
}
