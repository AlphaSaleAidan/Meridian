import { Phone, ShieldCheck, MessageSquare, VenetianMask } from 'lucide-react'
import { CHARACTER_OPTIONS } from '@/lib/phone-orders-demo-data'

// Public demo lines. Both ring the real phone agent and currently answer as
// Vinny (services/phone_agent/merchant_config.py seeds the demo pool with him).
const DEMO_LINES = [
  { label: 'Call the Canada demo line', display: '+1 506 801 7904', e164: '+15068017904' },
  { label: 'Call the US demo line — meet Vinny', display: '+1 380 240 9535', e164: '+13802409535' },
]

// The two surfaces this lands on don't share a container idiom: the merchant
// demo runs on `.card` (#111113/#1F1F23), the rep portal on the translucent
// white/10 sections its siblings use. Only the outer shell differs.
const SURFACE = {
  demo: 'card p-4 sm:p-5',
  portal: 'rounded-xl border border-white/10 bg-white/[0.02] p-5',
}

interface Props {
  /** Themes the icons per surface (merchant #1A8FD6, Canada #17C5B0, US #00d4aa). */
  accent?: string
  variant?: keyof typeof SURFACE
}

/**
 * Live demo lines a prospect can call on the spot. They order out loud, then
 * watch the ticket land and the pay-by-text arrive for real — nothing is ever
 * charged. Demo surfaces only; never rendered against a live merchant's data.
 */
export default function DemoCallCard({ accent = '#1A8FD6', variant = 'demo' }: Props) {
  return (
    <section className={SURFACE[variant]}>
      <header className="flex items-center gap-2.5 mb-1">
        <Phone size={16} style={{ color: accent }} />
        <h2 className="text-sm font-bold text-white">Call a Demo Agent</h2>
      </header>
      <p className="text-[11px] text-white/40 mb-4">
        These are live AI order-taking agents, not recordings. Hand the owner your phone, let them
        order a pizza, and they will watch the order land and the pay-by-text arrive for real.
        Nothing is ever charged.
      </p>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {DEMO_LINES.map(line => (
          <a
            key={line.e164}
            href={`tel:${line.e164}`}
            className="group flex min-h-[64px] items-center gap-3 rounded-lg border border-white/5 bg-white/[0.01] p-3.5 transition-colors hover:border-white/15 hover:bg-white/[0.03]"
          >
            <span
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border"
              style={{ color: accent, borderColor: `${accent}33`, backgroundColor: `${accent}14` }}
            >
              <Phone size={16} />
            </span>
            <span className="min-w-0">
              <span className="block text-[12px] font-medium text-white/90">{line.label}</span>
              <span className="block font-mono text-sm text-white tabular-nums">{line.display}</span>
            </span>
          </a>
        ))}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[10.5px] text-white/40">
        <span className="flex items-center gap-1.5">
          <ShieldCheck size={12} className="shrink-0 text-white/30" />
          No card taken, no charge
        </span>
        <span className="flex items-center gap-1.5">
          <MessageSquare size={12} className="shrink-0 text-white/30" />
          Pay-by-text fires for real
        </span>
      </div>

      <div className="mt-5 border-t border-white/5 pt-4">
        <header className="flex items-center gap-2.5 mb-1">
          <VenetianMask size={14} style={{ color: accent }} />
          <h3 className="text-[12px] font-bold text-white">The cast</h3>
        </header>
        <p className="text-[11px] text-white/40 mb-3">
          The agent comes as a character the merchant picks in Settings — same ordering brain,
          different personality on the line. Both demo numbers answer as Vinny today.
        </p>
        <div className="-mx-1 flex snap-x snap-mandatory gap-2 overflow-x-auto px-1 pb-2 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 sm:pb-0 lg:grid-cols-4">
          {CHARACTER_OPTIONS.map(c => (
            <div
              key={c.id}
              className="w-[224px] shrink-0 snap-start rounded-lg border border-white/5 bg-white/[0.01] p-3 sm:w-auto"
            >
              <span className="block text-[12px] font-medium text-white/90">{c.label}</span>
              <span className="mt-0.5 block text-[10.5px] leading-snug text-white/40">{c.tagline}</span>
              <span className="mt-1.5 block text-[10.5px] italic leading-snug text-white/55">
                &ldquo;{c.catchphrase}&rdquo;
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
