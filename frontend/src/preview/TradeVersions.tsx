/**
 * Trade version browser — what each trade's Meridian actually becomes.
 *
 * NOT A MOCKUP. Everything on this screen is computed by the same functions
 * the real portal calls: flagsForMerchant() decides what a trade keeps,
 * orderPillars() decides what order they meet it in, and the pack supplies the
 * vocabulary and the headline number. If a pack changes, this changes with it —
 * which is the point, because a slide deck of per-trade screenshots would be
 * out of date by Friday.
 *
 * Preview harness only; not imported by the app.
 */
import { useState } from 'react'
import { AlertTriangle, Check, Minus } from 'lucide-react'
import { merchantPillars, orderPillars } from '@/config/merchantPillars'
import { flagsForMerchant, flagsForPath } from '@/config/moduleFlags'
import { ALL_PACKS, type NichePack } from '@/config/niches'

/** Capabilities a trade needs that do not exist yet. Kept here rather than in
 *  the pack because it is a roadmap fact, not a product setting. */
const MISSING: Record<string, string[]> = {
  barbershop: ['Deposits'],
  nails: ['Deposits', 'Recurring appointments'],
  medspa: ['Intake forms', 'Deposits'],
  detailing: ['Routing (mobile only)'],
  restaurant: [],
  quickservice: [],
  other: [],
}

const BASE_PATH = '/us/merchant'

export default function TradeVersions() {
  const [pack, setPack] = useState<NichePack>(ALL_PACKS[0])

  const flags = flagsForMerchant(BASE_PATH, pack.modules)
  const base = flagsForPath(BASE_PATH)

  const kept = orderPillars(
    merchantPillars.filter((p) => !p.flag || flags[p.flag]),
    pack.pillarOrder,
  )
  // What this trade loses that another trade keeps — the "optimized" half of
  // the story, and the half a feature list never shows.
  const removed = merchantPillars.filter(
    (p) => p.flag && base[p.flag] && !flags[p.flag],
  )
  const missing = MISSING[pack.key] || []

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-[#F5F5F7]">
          One engine, every trade
        </h1>
        <p className="mt-0.5 max-w-2xl text-sm text-[#A1A1A8]">
          Pick a trade to see the Meridian a merchant of that trade actually gets.
          Every panel below is computed from the live pack config, not drawn — the
          same functions the portal calls.
        </p>
      </header>

      <div className="flex flex-wrap gap-1.5">
        {ALL_PACKS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPack(p)}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
              pack.key === p.key
                ? 'border-[#1A8FD6]/60 bg-[#1A8FD6]/10 text-[#1A8FD6]'
                : 'border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7]'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <p className="max-w-2xl border-l-2 border-[#1A8FD6]/40 pl-3 text-sm italic text-[#D4D4D8]">
        “{pack.pitch}”
      </p>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {/* ── The portal this trade gets ───────────────────────────── */}
        <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Their navigation</h2>
          <p className="mt-0.5 text-xs text-[#A1A1A8]">
            In this order, top to bottom. The first one is what they open on.
          </p>

          <ol className="mt-4 space-y-1">
            {kept.map((p, i) => (
              <li
                key={p.path || 'home'}
                className={`flex items-center gap-3 rounded-lg border px-3 py-2 ${
                  i === 0
                    ? 'border-[#1A8FD6]/40 bg-[#1A8FD6]/10'
                    : 'border-[#1F1F23]'
                }`}
              >
                <span className="w-4 shrink-0 text-center font-mono text-[10px] text-[#6B6B73]">
                  {i + 1}
                </span>
                <p.icon className={`h-4 w-4 shrink-0 ${
                  i === 0 ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'
                }`} />
                <span className={`text-sm ${i === 0 ? 'text-[#F5F5F7]' : 'text-[#D4D4D8]'}`}>
                  {p.label}
                </span>
                {i === 0 && (
                  <span className="ml-auto text-[10px] uppercase tracking-wide text-[#1A8FD6]">
                    lands here
                  </span>
                )}
              </li>
            ))}
          </ol>

          {removed.length > 0 && (
            <>
              <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-[#6B6B73]">
                Removed for this trade
              </h3>
              <ul className="mt-2 space-y-1">
                {removed.map((p) => (
                  <li
                    key={p.path}
                    className="flex items-center gap-3 rounded-lg border border-dashed border-[#1F1F23] px-3 py-1.5"
                  >
                    <Minus className="h-3.5 w-3.5 shrink-0 text-[#6B6B73]" />
                    <span className="text-sm text-[#6B6B73] line-through">{p.label}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-[#6B6B73]">
                Not hidden behind a setting — never rendered, never in the nav.
              </p>
            </>
          )}
        </section>

        {/* ── What it says and does ────────────────────────────────── */}
        <div className="space-y-4">
          <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
            <h2 className="text-sm font-semibold text-[#F5F5F7]">
              The number they open on
            </h2>
            <div className="mt-3 rounded-lg border border-[#1F1F23] bg-[#0E0E11] p-4">
              <div className="text-[11px] uppercase tracking-wide text-[#A1A1A8]">
                {pack.homeMetric.label}
              </div>
              <div className="mt-1 font-mono text-3xl font-semibold text-[#F5F5F7]">
                ——
              </div>
              <p className="mt-2 text-xs text-[#6B6B73]">{pack.homeMetric.help}</p>
            </div>
            <p className="mt-3 text-xs text-[#A1A1A8]">
              If two trades opened on the same figure, one of them would be a
              colour scheme rather than a version of the product.
            </p>
          </section>

          <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
            <h2 className="text-sm font-semibold text-[#F5F5F7]">What the agent says</h2>
            <dl className="mt-3 divide-y divide-[#1F1F23] rounded-lg border border-[#1F1F23]">
              <Row label="Calls a booking">“{pack.bookingNoun}”</Row>
              <Row label="Calls the person">“{pack.customerNoun}”</Row>
              <Row label="Books against">
                {pack.booksAtAll ? `${pack.countLabel} · ${pack.defaultCount} by default` : 'Nothing — takes orders'}
              </Row>
              <Row label="Open">
                {DAYS.filter((_, i) => pack.days.includes(i)).join(', ')} · {pack.opens}–{pack.closes}
              </Row>
            </dl>
          </section>
        </div>
      </div>

      {pack.booksAtAll ? (
        <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
          <h2 className="text-sm font-semibold text-[#F5F5F7]">
            What the wizard creates before they type anything
          </h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {pack.services.map((s) => (
              <span
                key={s.name}
                className="rounded-lg border border-[#1F1F23] px-3 py-1.5 text-xs text-[#D4D4D8]"
              >
                {s.name}
                <span className="ml-2 text-[#6B6B73]">
                  {s.duration >= 60 ? `${s.duration / 60} hr` : `${s.duration} min`}
                  {s.buffer > 0 && ` +${s.buffer}`}
                </span>
              </span>
            ))}
          </div>
        </section>
      ) : (
        <section className="rounded-xl border border-dashed border-[#1F1F23] bg-[#111113] p-5">
          <h2 className="text-sm font-semibold text-[#F5F5F7]">No booking module</h2>
          <p className="mt-1 max-w-2xl text-sm text-[#A1A1A8]">
            This trade's phone is order volume, not a calendar. Handing a takeout
            shop a table plan is how you lose a merchant in week one — they decide
            the product wasn't built for them, and they're right.
          </p>
        </section>
      )}

      {missing.length > 0 && (
        <section className="rounded-xl border border-[#F5A524]/30 bg-[#F5A524]/5 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-[#F5A524]">
            <AlertTriangle className="h-4 w-4" />
            Not built yet for this trade
          </h2>
          <ul className="mt-2 space-y-1">
            {missing.map((m) => (
              <li key={m} className="text-sm text-[#D4D4D8]">{m}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-[#A1A1A8]">
            Sellable without these — but expect to be asked.
          </p>
        </section>
      )}

      {missing.length === 0 && (
        <section className="flex items-center gap-2 rounded-xl border border-[#17C5B0]/30 bg-[#17C5B0]/5 p-4">
          <Check className="h-4 w-4 shrink-0 text-[#17C5B0]" />
          <p className="text-sm text-[#D4D4D8]">
            Fully served by what is built today. Nothing to wait for.
          </p>
        </section>
      )}
    </div>
  )
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 px-3 py-2.5">
      <dt className="shrink-0 text-xs uppercase tracking-wide text-[#A1A1A8]">{label}</dt>
      <dd className="min-w-0 text-right text-sm text-[#F5F5F7]">{children}</dd>
    </div>
  )
}
