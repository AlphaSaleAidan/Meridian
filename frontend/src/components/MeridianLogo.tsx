import React from 'react';

/* ------------------------------------------------------------------ */
/*  Meridian Radar Logo                                                */
/*  A sweeping radar with teal-green afterglow — hunting for profit    */
/* ------------------------------------------------------------------ */

/* Shared gradient defs used by both emblem and wordmark */
const RadarDefs: React.FC<{ id: string }> = ({ id }) => (
  <defs>
    {/* Teal glow gradient for the sweep trail */}
    <linearGradient id={`${id}-sweep`} x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stopColor="#17C5B0" stopOpacity="0" />
      <stop offset="60%" stopColor="#17C5B0" stopOpacity="0.25" />
      <stop offset="100%" stopColor="#17C5B0" stopOpacity="0.7" />
    </linearGradient>
    {/* Radial glow behind the sweep */}
    <radialGradient id={`${id}-glow`} cx="50%" cy="50%" r="50%">
      <stop offset="0%" stopColor="#17C5B0" stopOpacity="0.15" />
      <stop offset="70%" stopColor="#17C5B0" stopOpacity="0.05" />
      <stop offset="100%" stopColor="#17C5B0" stopOpacity="0" />
    </radialGradient>
    {/* Text gradient */}
    <linearGradient id={`${id}-text`} x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stopColor="#1A8FD6" />
      <stop offset="100%" stopColor="#17C5B0" />
    </linearGradient>
    {/* Sweep cone gradient */}
    <linearGradient id={`${id}-cone`} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor="#17C5B0" stopOpacity="0.6" />
      <stop offset="100%" stopColor="#17C5B0" stopOpacity="0" />
    </linearGradient>
  </defs>
);

/* ------------------------------------------------------------------ */
/*  Radar Emblem — the circular sweep icon                             */
/* ------------------------------------------------------------------ */
interface EmblemProps {
  size?: number;
  animate?: boolean;
  className?: string;
}

export const MeridianEmblem: React.FC<EmblemProps> = ({
  size = 40,
  animate = true,
  className = '',
}) => {
  const id = React.useId().replace(/:/g, '');
  const cx = 50;
  const cy = 50;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Meridian radar emblem"
    >
      <RadarDefs id={id} />

      {/* Background circle — dark */}
      <circle cx={cx} cy={cy} r="48" fill="#0A0A0B" stroke="#1A8FD6" strokeWidth="1" strokeOpacity="0.3" />

      {/* Ambient glow */}
      <circle cx={cx} cy={cy} r="46" fill={`url(#${id}-glow)`} />

      {/* Range rings */}
      {[16, 30, 43].map((r) => (
        <circle
          key={r}
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#17C5B0"
          strokeWidth="0.5"
          strokeOpacity="0.15"
        />
      ))}

      {/* Crosshairs */}
      <line x1={cx} y1="8" x2={cx} y2="92" stroke="#17C5B0" strokeWidth="0.4" strokeOpacity="0.12" />
      <line x1="8" y1={cy} x2="92" y2={cy} stroke="#17C5B0" strokeWidth="0.4" strokeOpacity="0.12" />

      {/* Sweep cone — the rotating radar arm with teal trail */}
      <g style={animate ? { animation: 'meridian-sweep 3s linear infinite', transformOrigin: '50px 50px' } : { transform: 'rotate(-30deg)', transformOrigin: '50px 50px' }}>
        {/* Trailing glow cone (60 degree wedge) */}
        <path
          d={`M ${cx} ${cy} L ${cx} ${cy - 44} A 44 44 0 0 0 ${cx - 44 * Math.sin(Math.PI / 3)} ${cy - 44 * Math.cos(Math.PI / 3)} Z`}
          fill={`url(#${id}-sweep)`}
          opacity="0.5"
        />
        {/* Main sweep line */}
        <line
          x1={cx}
          y1={cy}
          x2={cx}
          y2={cy - 44}
          stroke="#17C5B0"
          strokeWidth="1.5"
          strokeLinecap="round"
          filter="drop-shadow(0 0 4px rgba(23, 197, 176, 0.8))"
        />
        {/* Bright tip */}
        <circle cx={cx} cy={cy - 42} r="2" fill="#17C5B0" opacity="0.9">
          {animate && <animate attributeName="opacity" values="0.9;0.5;0.9" dur="1s" repeatCount="indefinite" />}
        </circle>
      </g>

      {/* Detected "blips" — profit signals */}
      <circle cx="62" cy="34" r="2.5" fill="#17C5B0" opacity="0.7">
        {animate && <animate attributeName="opacity" values="0.7;0.2;0.7" dur="2s" repeatCount="indefinite" />}
      </circle>
      <circle cx="38" cy="62" r="2" fill="#17C5B0" opacity="0.5">
        {animate && <animate attributeName="opacity" values="0.5;0.15;0.5" dur="2.5s" repeatCount="indefinite" />}
      </circle>
      <circle cx="68" cy="58" r="1.8" fill="#1A8FD6" opacity="0.6">
        {animate && <animate attributeName="opacity" values="0.6;0.2;0.6" dur="1.8s" repeatCount="indefinite" />}
      </circle>
      <circle cx="35" cy="38" r="1.5" fill="#17C5B0" opacity="0.4">
        {animate && <animate attributeName="opacity" values="0.4;0.1;0.4" dur="3s" repeatCount="indefinite" />}
      </circle>

      {/* Center dot — command center */}
      <circle cx={cx} cy={cy} r="3" fill="#17C5B0" />
      <circle cx={cx} cy={cy} r="5" fill="none" stroke="#17C5B0" strokeWidth="0.8" strokeOpacity="0.5" />

      {/* Stylized M at center — subtle */}
      <text
        x={cx}
        y={cy + 1.5}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#0A0A0B"
        fontSize="5"
        fontWeight="800"
        fontFamily="system-ui, -apple-system, sans-serif"
      >
        M
      </text>

      {/* Outer rim accent */}
      <circle cx={cx} cy={cy} r="47" fill="none" stroke="#17C5B0" strokeWidth="0.8" strokeOpacity="0.25" />
      <circle cx={cx} cy={cy} r="48.5" fill="none" stroke="#1A8FD6" strokeWidth="0.3" strokeOpacity="0.15" />

      {/* CSS keyframe injected via style tag */}
      {animate && (
        <style>{`
          @keyframes meridian-sweep {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      )}
    </svg>
  );
};

/* ------------------------------------------------------------------ */
/*  Wordmark                                                           */
/* ------------------------------------------------------------------ */
interface WordmarkProps {
  height?: number;
  className?: string;
}

export const MeridianWordmark: React.FC<WordmarkProps> = ({
  height = 24,
  className = '',
}) => (
  <span
    className={`font-bold tracking-[0.18em] uppercase bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent select-none ${className}`}
    style={{ fontSize: height, lineHeight: 1 }}
    aria-label="Meridian"
  >
    MERIDIAN
  </span>
);

/* ------------------------------------------------------------------ */
/*  Combined Logo (emblem + wordmark + optional tagline)               */
/* ------------------------------------------------------------------ */
interface LogoProps {
  size?: number;
  showWordmark?: boolean;
  showTagline?: boolean;
  animate?: boolean;
  layout?: 'horizontal' | 'vertical';
  className?: string;
}

export const MeridianLogo: React.FC<LogoProps> = ({
  size = 40,
  showWordmark = true,
  showTagline = false,
  animate = true,
  layout = 'horizontal',
  className = '',
}) => {
  const isVertical = layout === 'vertical';

  return (
    <div
      className={`flex ${isVertical ? 'flex-col items-center gap-3' : 'items-center gap-3'} ${className}`}
    >
      <MeridianEmblem size={size} animate={animate} />
      {showWordmark && (
        <div className={`flex flex-col ${isVertical ? 'items-center' : 'items-start'}`}>
          <MeridianWordmark height={size * 0.5} />
          {showTagline && (
            <span
              className="text-white/40 tracking-[0.12em] uppercase mt-1"
              style={{ fontSize: Math.max(9, size * 0.22) }}
            >
              AI POS Analytics · Profit Growth
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default MeridianLogo;
