import type { SalesRegion } from '@/lib/regions'

/**
 * Region orientation — how selling inside an isolated territory differs from
 * the core team. Informational only: it deliberately does NOT join the gated
 * course flow (video + quiz unlock lead creation; this card must never block
 * that or be blocked by it).
 */

function Icon({ d, accent }: { d: string; accent: string }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4 flex-shrink-0 mt-0.5" fill="none" stroke={accent} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  )
}

// Inline stroke paths (lucide-style): wall/fence, globe, trophy-off, compass.
const ICONS = {
  fence: 'M4 4v16 M10 4v16 M16 4v16 M22 4v16 M2 9h22 M2 15h22',
  globe: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M3 12h18 M12 3c2.5 2.6 3.8 5.7 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.7-3.8-9s1.3-6.4 3.8-9',
  quiet: 'M8 21h8 M12 17v4 M17 4v5a5 5 0 0 1-10 0V4h10z M3 8l18 10',
  compass: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20 M15.5 8.5l-2 5-5 2 2-5 5-2',
}

export function RegionOrientationCard({ region }: { region: SalesRegion }) {
  const { accent, deep, mid } = region.theme
  const points: Array<{ icon: keyof typeof ICONS; title: string; body: string }> = [
    {
      icon: 'fence',
      title: 'Your territory is walled off',
      body: 'Only Odyssey members appear in your roster, and your leads are visible inside the region only. Core Meridian reps can’t see your pipeline, and you won’t see theirs.',
    },
    {
      icon: 'globe',
      title: 'One login, both portals',
      body: 'The same credentials work on the US portal and the Canada portal. Your leads stay with whichever portal you created them in.',
    },
    {
      icon: 'quiet',
      title: 'No leaderboard',
      body: 'Odyssey runs without a public board — your numbers are between you and your region lead. Rankings and incentive contests in the core portal don’t apply here.',
    },
    {
      icon: 'compass',
      title: 'Same rules of the sea',
      body: 'The training course, code of conduct, and published pricing apply exactly as in the core portal. Questions go to your region lead first.',
    },
  ]

  return (
    <section
      className="relative overflow-hidden rounded-xl border p-5"
      style={{
        borderColor: accent + '33',
        background: `linear-gradient(120deg, ${deep} 0%, ${mid} 70%, ${deep} 100%)`,
      }}
    >
      <p className="text-[10px] font-semibold uppercase tracking-[0.28em]" style={{ color: accent }}>
        {region.name} · Orientation
      </p>
      <h2 className="mt-1 text-base font-bold text-white">Selling inside the Odyssey Region</h2>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {points.map(p => (
          <div key={p.title} className="flex gap-2.5">
            <Icon d={ICONS[p.icon]} accent={accent} />
            <div>
              <p className="text-[12.5px] font-semibold text-white">{p.title}</p>
              <p className="mt-0.5 text-[11.5px] leading-relaxed text-white/60">{p.body}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
