import { BookOpen, ExternalLink, ShieldCheck } from 'lucide-react'

const GUIDES = [
  {
    label: 'Why We Built Meridian Compliance-First for Canada',
    blurb: 'The positioning story — use this to explain our edge to privacy-conscious owners.',
    path: '/guides/meridian-compliance-first-canada',
  },
  {
    label: 'PIPEDA Compliance for Small Businesses',
    blurb: 'What Canada\'s federal privacy law requires. Great for objection handling on data concerns.',
    path: '/guides/pipeda-compliance-small-business',
  },
  {
    label: 'Quebec Law 25 Explained',
    blurb: 'The strictest privacy law in Canada. Essential for any Quebec prospect.',
    path: '/guides/quebec-law-25-small-business',
  },
  {
    label: 'Where Does Your POS Data Live?',
    blurb: 'Data residency talking points — "your data stays in Canada" closes deals.',
    path: '/guides/pos-data-residency-canada',
  },
]

/**
 * Compliance guide library for sales reps. Links open the public marketing guides
 * in a new tab so reps stay inside the portal. `accent` lets each portal theme it.
 */
export default function ComplianceGuidesCard({ accent = '#1A8FD6' }: { accent?: string }) {
  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
      <header className="flex items-center gap-2.5 mb-1">
        <ShieldCheck size={16} style={{ color: accent }} />
        <h2 className="text-sm font-bold text-white">Compliance Guides for Reps</h2>
      </header>
      <p className="text-[11px] text-white/40 mb-4">
        Public guides you can share with prospects or use for objection handling. Our compliance-first
        story is one of our strongest differentiators in Canada — know these cold.
      </p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {GUIDES.map(g => (
          <a
            key={g.path}
            href={g.path}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-start gap-2.5 rounded-lg border border-white/5 bg-white/[0.01] p-3 hover:border-white/15 hover:bg-white/[0.03] transition-colors"
          >
            <BookOpen size={14} className="mt-0.5 shrink-0 text-white/30 group-hover:text-white/60 transition-colors" />
            <span className="min-w-0">
              <span className="flex items-center gap-1 text-[12px] font-medium text-white/90">
                {g.label}
                <ExternalLink size={10} className="shrink-0 text-white/25 group-hover:text-white/50 transition-colors" />
              </span>
              <span className="block text-[10.5px] text-white/40 leading-snug mt-0.5">{g.blurb}</span>
            </span>
          </a>
        ))}
      </div>
    </section>
  )
}
