import type { SalesRegion } from '@/lib/regions'

/**
 * Region identity band for the Team section (region members only — core
 * portal never renders this). Two-tone theme comes from the region registry;
 * decoration is inline stroke SVG (no raster assets, no emojis, no motion).
 */

/** Greek-key meander strip — the region's signature edge ornament. */
function MeanderStrip({ accent }: { accent: string }) {
  return (
    <svg aria-hidden className="absolute inset-x-0 top-0 h-[11px] w-full" preserveAspectRatio="none" style={{ color: accent }}>
      <defs>
        <pattern id="rb-meander" width="18" height="11" patternUnits="userSpaceOnUse">
          <path
            d="M0 9 H14 V2 H5 V6 H9"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="square"
          />
        </pattern>
      </defs>
      <rect width="100%" height="11" fill="url(#rb-meander)" opacity="0.45" />
    </svg>
  )
}

/** Eight-point wind rose — navigation motif, stroke-only. */
function WindRose({ accent }: { accent: string }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke={accent} strokeWidth="1.5" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9.25" strokeWidth="1" opacity="0.45" />
      <path d="M12 2.75 L13.8 10.2 L21.25 12 L13.8 13.8 L12 21.25 L10.2 13.8 L2.75 12 L10.2 10.2 Z" />
      <circle cx="12" cy="12" r="1.4" />
    </svg>
  )
}

interface RegionBannerProps {
  region: SalesRegion
  memberCount: number
}

export function RegionBanner({ region, memberCount }: RegionBannerProps) {
  const { accent, deep, mid } = region.theme
  return (
    <div
      className="relative overflow-hidden rounded-xl border px-5 pb-4 pt-6"
      style={{
        borderColor: accent + '3a',
        background: `linear-gradient(120deg, ${deep} 0%, ${mid} 62%, ${deep} 100%)`,
      }}
    >
      <MeanderStrip accent={accent} />
      <div className="flex flex-wrap items-center gap-4">
        <div
          className="flex h-11 w-11 items-center justify-center rounded-lg border"
          style={{ borderColor: accent + '40', backgroundColor: accent + '14' }}
        >
          <WindRose accent={accent} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em]" style={{ color: accent }}>
            Isolated Territory
          </p>
          <h2 className="mt-0.5 text-lg font-bold leading-tight text-white">{region.name}</h2>
          <p className="mt-0.5 text-xs text-white/55">{region.tagline}</p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-medium"
            style={{ borderColor: accent + '33', color: accent, backgroundColor: accent + '0f' }}
          >
            {memberCount} {memberCount === 1 ? 'member' : 'members'}
          </span>
          {!region.showLeaderboard && (
            <span className="inline-flex items-center rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-[10px] font-medium text-white/60">
              Leaderboard off
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
