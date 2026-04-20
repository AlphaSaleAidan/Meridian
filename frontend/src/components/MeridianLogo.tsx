/**
 * MeridianLogo — Hand-drawn white "M" emblem + cursive wordmark.
 * The SVG M uses organic brush-stroke paths for a premium hand-drawn feel.
 */

interface Props {
  size?: number
  showText?: boolean
  textSize?: string
  className?: string
}

export function MeridianEmblem({ size = 32, className = '' }: { size?: number; className?: string }) {
  return (
    <div
      className={`flex items-center justify-center rounded-xl bg-gradient-to-br from-[#7C5CFF]/20 to-[#4FE3C1]/10 border border-[#7C5CFF]/20 ${className}`}
      style={{ width: size, height: size }}
    >
      <svg
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: size * 0.6, height: size * 0.6 }}
      >
        {/* Hand-drawn M — brush-stroke style with slight irregularity */}
        <path
          d="M8 38V12.5C8 11.5 8.3 10.8 9 10.5C9.5 10.3 10 10.5 10.2 11L18.5 28C19.5 30 20.5 31.5 21.5 31.5C22.5 31.5 23 30.5 24 28.5L32.5 11C32.8 10.4 33.5 10.2 34 10.5C34.7 10.8 35 11.5 35 12.5V38"
          stroke="white"
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            filter: 'url(#roughen)',
          }}
        />
        <path
          d="M40 38V12C40 11.2 39.6 10.5 39 10.5"
          stroke="white"
          strokeWidth="3.5"
          strokeLinecap="round"
          opacity="0.85"
        />
        {/* Subtle organic filter for hand-drawn feel */}
        <defs>
          <filter id="roughen" x="-2" y="-2" width="52" height="52">
            <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="4" result="noise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="0.8" />
          </filter>
        </defs>
      </svg>
    </div>
  )
}

export function MeridianWordmark({ className = '', size = 'text-lg' }: { className?: string; size?: string }) {
  return (
    <span className={`font-serif italic text-white tracking-tight ${size} ${className}`}>
      Meridian
    </span>
  )
}

export default function MeridianLogo({ size = 32, showText = true, textSize = 'text-lg', className = '' }: Props) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <MeridianEmblem size={size} />
      {showText && <MeridianWordmark size={textSize} />}
    </div>
  )
}
