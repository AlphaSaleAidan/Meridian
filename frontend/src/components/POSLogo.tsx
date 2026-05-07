import { clsx } from 'clsx'
import { posSystemsByKey, type POSSystemKey } from '@/data/pos-systems'

const svgModules = import.meta.glob<{ default: string }>('@/assets/pos-logos/*.svg', { eager: true })

const logoMap: Record<string, string> = {}
for (const [path, mod] of Object.entries(svgModules)) {
  const key = path.split('/').pop()!.replace('.svg', '')
  logoMap[key] = mod.default
}

const sizes = { sm: 20, md: 32, lg: 48 } as const

interface POSLogoProps {
  system: POSSystemKey
  size?: 'sm' | 'md' | 'lg'
  variant?: 'color' | 'mono' | 'white'
  className?: string
}

export default function POSLogo({ system, size = 'md', variant = 'color', className }: POSLogoProps) {
  const px = sizes[size]
  const src = logoMap[system]
  const info = posSystemsByKey[system]
  const brandColor = info?.brandColor || '#A1A1A8'

  if (src) {
    return (
      <img
        src={src}
        alt={`${info?.name || system} POS`}
        width={px}
        height={px}
        className={clsx(
          'rounded-lg object-contain flex-shrink-0',
          variant === 'mono' && 'grayscale',
          variant === 'white' && 'brightness-0 invert',
          className,
        )}
      />
    )
  }

  return (
    <div
      className={clsx(
        'rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-white',
        className,
      )}
      style={{
        width: px,
        height: px,
        backgroundColor: variant === 'mono' ? '#1F1F23' : brandColor,
        fontSize: px * 0.35,
      }}
    >
      {info?.logoInitials || (info?.name || system).slice(0, 2).toUpperCase()}
    </div>
  )
}

export function POSStatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; color: string; bg: string }> = {
    integrated: { label: 'Supported', color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10 border-[#17C5B0]/20' },
    coming_soon: { label: 'Coming Soon', color: 'text-amber-400', bg: 'bg-amber-400/10 border-amber-400/20' },
    contingency: { label: 'Manual Import', color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10 border-[#1A8FD6]/20' },
    unsupported: { label: 'Contact Us', color: 'text-[#A1A1A8]', bg: 'bg-[#A1A1A8]/10 border-[#A1A1A8]/20' },
  }
  const c = config[status] || config.unsupported
  return (
    <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded-full border', c.color, c.bg)}>
      {c.label}
    </span>
  )
}
