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

// Inline stroke paths (lucide-style): storefront, funnel/pipeline, coins, lifebuoy.
const ICONS = {
  store: 'M3 9l1.5-5h15L21 9 M3 9h18 M5 9v11h14V9 M9 20v-6h6v6',
  funnel: 'M3 4h18l-7 8v6l-4 2v-8L3 4',
  coins: 'M12 8a7 3 0 1 0 0-6 7 3 0 0 0 0 6 M5 5v4c0 1.7 3.1 3 7 3s7-1.3 7-3V5 M5 13v4c0 1.7 3.1 3 7 3s7-1.3 7-3v-4',
  buoy: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20 M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M5 5l4 4 M19 5l-4 4 M5 19l4-4 M19 19l-4-4',
}

export function RegionOrientationCard({ region }: { region: SalesRegion }) {
  const { accent, deep, mid } = region.theme
  const points: Array<{ icon: keyof typeof ICONS; title: string; body: string }> = [
    {
      icon: 'store',
      title: 'What you sell',
      body: 'Meridian for independent merchants: the AI phone-ordering agent plus POS analytics on their existing system (one-click Square, Clover, or Stripe connect, 18-month backfill), anonymous camera counts, and real margin tracking.',
    },
    {
      icon: 'funnel',
      title: 'How a deal moves',
      body: 'Create the lead, show the proposal, walk the customer through checkout, connect their POS, then run the onboarding walkthrough. Every stage lives on your Leads page — deals only count once the POS is connected.',
    },
    {
      icon: 'coins',
      title: 'How you get paid',
      body: 'A milestone schedule per closed account: a lump sum when the merchant’s first payment clears, then retention milestones at months 4, 9, and 12 the account stays active. Full package table in Pricing & Commission — retention pays more than the close.',
    },
    {
      icon: 'buoy',
      title: 'Where to get help',
      body: 'The course below unlocks lead creation; the playbook answers POS, camera, and objection questions in seconds. Anything it doesn’t cover goes to your region lead.',
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
