import type { SalesRegion } from '@/lib/regions'

/**
 * Region hero header — a silent, seamlessly-looping video band with the
 * region's blue wash over it and the region wordmark in gold. Rendered only
 * for region members, at the top of Leads / Dashboard pages.
 *
 * The video is decorative: muted, autoplay, loop, aria-hidden. When the
 * viewer prefers reduced motion (or the file 404s) the band degrades to the
 * region's two-tone gradient, so the wordmark never disappears.
 */
interface RegionHeroProps {
  region: SalesRegion
  /** Path under /public, e.g. /regions/odyssey/leads-hero.mp4 */
  videoSrc: string
  /**
   * CSS object-position for the video crop. The band is much shorter than the
   * 16:9 source, so this picks WHICH horizontal slice shows — tune it per
   * clip so the subject's face lands inside the band (e.g. '50% 12%' when the
   * head sits near the top of the frame). Defaults to center.
   */
  focus?: string
}

export function RegionHero({ region, videoSrc, focus = '50% 50%' }: RegionHeroProps) {
  const { accent, deep, mid } = region.theme
  const wordmark = region.name.split(' ')[0].toUpperCase()
  const reducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

  return (
    <div
      className="relative h-44 sm:h-56 overflow-hidden rounded-xl border"
      style={{
        borderColor: accent + '33',
        background: `linear-gradient(120deg, ${deep} 0%, ${mid} 62%, ${deep} 100%)`,
      }}
    >
      {!reducedMotion && (
        <video
          aria-hidden
          className="absolute inset-0 h-full w-full object-cover"
          style={{ objectPosition: focus }}
          src={videoSrc}
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
        />
      )}
      {/* Blue wash — keeps the gold wordmark legible over any frame. */}
      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          background: `linear-gradient(180deg, ${deep}66 0%, ${deep}8c 55%, ${deep}c9 100%)`,
        }}
      />
      <div className="relative flex h-full flex-col items-center justify-center gap-2">
        <div className="flex items-center gap-4">
          <span aria-hidden className="h-px w-10 sm:w-16" style={{ backgroundColor: accent + '80' }} />
          <h2
            className="text-2xl sm:text-3xl font-bold uppercase tracking-[0.42em] pl-[0.42em] text-center"
            style={{ color: accent, textShadow: `0 2px 14px ${deep}` }}
          >
            {wordmark}
          </h2>
          <span aria-hidden className="h-px w-10 sm:w-16" style={{ backgroundColor: accent + '80' }} />
        </div>
        <p className="text-[10px] font-medium uppercase tracking-[0.28em] text-white/60">
          {region.name}
        </p>
      </div>
    </div>
  )
}
