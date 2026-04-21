/**
 * MeridianLogo — Compass + Growth-Arrow emblem inspired by brand mark.
 *
 * Three exports:
 *   MeridianEmblem   – standalone icon (gradient compass + rising arrow)
 *   MeridianWordmark  – "Meridian" text
 *   MeridianLogo      – emblem + wordmark together (default)
 */

interface Props {
  size?: number
  showText?: boolean
  showTagline?: boolean
  textSize?: string
  className?: string
}

/* ─── SVG Emblem ──────────────────────────────────────────────── */

export function MeridianEmblem({
  size = 32,
  className = '',
}: {
  size?: number
  className?: string
}) {
  const id = `me-${Math.random().toString(36).slice(2, 8)}`
  return (
    <div
      className={`flex items-center justify-center flex-shrink-0 ${className}`}
      style={{ width: size, height: size }}
    >
      <svg
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: '100%' }}
      >
        <defs>
          {/* Main brand gradient: dark navy → ocean blue → teal */}
          <linearGradient id={`${id}-main`} x1="10" y1="110" x2="110" y2="10">
            <stop offset="0%" stopColor="#0B3D6B" />
            <stop offset="45%" stopColor="#1A8FD6" />
            <stop offset="100%" stopColor="#17C5B0" />
          </linearGradient>
          <linearGradient id={`${id}-arrow`} x1="50" y1="80" x2="100" y2="20">
            <stop offset="0%" stopColor="#1A8FD6" />
            <stop offset="100%" stopColor="#17C5B0" />
          </linearGradient>
          <linearGradient id={`${id}-sweep`} x1="20" y1="20" x2="100" y2="20">
            <stop offset="0%" stopColor="#1A8FD6" />
            <stop offset="100%" stopColor="#17C5B0" />
          </linearGradient>
        </defs>

        {/* ── Circular sweep arrow (outer ring, top arc) ── */}
        <path
          d="M 22 35 A 48 48 0 0 1 98 35"
          stroke={`url(#${id}-sweep)`}
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
          opacity="0.55"
        />
        {/* Sweep arrowhead */}
        <path
          d="M 94 28 L 100 35 L 92 38"
          stroke={`url(#${id}-sweep)`}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          opacity="0.55"
        />

        {/* ── Outer compass circle ── */}
        <circle
          cx="56"
          cy="60"
          r="42"
          stroke={`url(#${id}-main)`}
          strokeWidth="2.5"
          opacity="0.7"
        />

        {/* ── Inner compass circle ── */}
        <circle
          cx="56"
          cy="60"
          r="26"
          stroke={`url(#${id}-main)`}
          strokeWidth="1.2"
          opacity="0.25"
        />

        {/* ── Compass cardinal ticks ── */}
        {/* North */}
        <line x1="56" y1="18" x2="56" y2="28" stroke={`url(#${id}-main)`} strokeWidth="2.5" strokeLinecap="round" opacity="0.8" />
        {/* South */}
        <line x1="56" y1="92" x2="56" y2="102" stroke={`url(#${id}-main)`} strokeWidth="2" strokeLinecap="round" opacity="0.35" />
        {/* West */}
        <line x1="8" y1="60" x2="18" y2="60" stroke={`url(#${id}-main)`} strokeWidth="2" strokeLinecap="round" opacity="0.35" />
        {/* East (shorter, behind chart) */}
        <line x1="94" y1="60" x2="102" y2="60" stroke={`url(#${id}-main)`} strokeWidth="2" strokeLinecap="round" opacity="0.25" />

        {/* ── Compass cross-hairs (subtle) ── */}
        <line x1="56" y1="34" x2="56" y2="42" stroke={`url(#${id}-main)`} strokeWidth="1" opacity="0.15" />
        <line x1="56" y1="78" x2="56" y2="86" stroke={`url(#${id}-main)`} strokeWidth="1" opacity="0.15" />
        <line x1="30" y1="60" x2="38" y2="60" stroke={`url(#${id}-main)`} strokeWidth="1" opacity="0.15" />
        <line x1="74" y1="60" x2="82" y2="60" stroke={`url(#${id}-main)`} strokeWidth="1" opacity="0.15" />

        {/* ── Stylised "M" at compass center ── */}
        <path
          d="M 40 76 V 48 L 48 62 L 56 46 L 64 62 L 72 48 V 76"
          stroke={`url(#${id}-main)`}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />

        {/* ── Growth arrow breaking out of circle (upper-right) ── */}
        <path
          d="M 62 78 L 72 62 L 82 66 L 102 30"
          stroke={`url(#${id}-arrow)`}
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        {/* Arrowhead */}
        <path
          d="M 96 26 L 104 29 L 100 36"
          stroke={`url(#${id}-arrow)`}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />

        {/* ── Circuit-board nodes (tech / AI feel) ── */}
        <circle cx="72" cy="62" r="2.5" fill="#1A8FD6" />
        <circle cx="82" cy="66" r="2.5" fill="#17C5B0" />
        {/* Small circuit traces on the right */}
        <line x1="96" y1="52" x2="108" y2="52" stroke="#17C5B0" strokeWidth="1.2" strokeLinecap="round" opacity="0.35" />
        <circle cx="108" cy="52" r="1.8" fill="#17C5B0" opacity="0.35" />
        <line x1="92" y1="74" x2="104" y2="74" stroke="#1A8FD6" strokeWidth="1.2" strokeLinecap="round" opacity="0.25" />
        <circle cx="104" cy="74" r="1.8" fill="#1A8FD6" opacity="0.25" />
      </svg>
    </div>
  )
}

/* ─── Wordmark ────────────────────────────────────────────────── */

export function MeridianWordmark({
  className = '',
  size = 'text-lg',
}: {
  className?: string
  size?: string
}) {
  return (
    <span
      className={`font-sans font-bold tracking-wide uppercase bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent ${size} ${className}`}
    >
      Meridian
    </span>
  )
}

/* ─── Combined Logo (default export) ─────────────────────────── */

export default function MeridianLogo({
  size = 32,
  showText = true,
  showTagline = false,
  textSize = 'text-lg',
  className = '',
}: Props) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <MeridianEmblem size={size} />
      {showText && (
        <div className="flex flex-col">
          <MeridianWordmark size={textSize} />
          {showTagline && (
            <span className="text-[9px] text-[#A1A1A8]/60 tracking-[0.15em] uppercase font-medium -mt-0.5">
              AI POS Analytics · Profit Growth
            </span>
          )}
        </div>
      )}
    </div>
  )
}
