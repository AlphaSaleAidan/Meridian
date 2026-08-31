/**
 * Booking setup wizard — zero to taking bookings inside a sales call.
 *
 * The manual setup page is four cards of forms. That is the right tool for a
 * merchant changing their Friday hours and the wrong one for a merchant who
 * has just said yes and is watching you over the counter. This asks the
 * questions in the order an owner already thinks about them and fills in
 * everything it can guess.
 *
 * THE SHAPE OF THE WIZARD IS THE SHAPE OF THE ARCHITECTURE. There are three
 * ways a business can be set up and they need wildly different amounts of
 * information:
 *
 *   we take the booking   → we own the calendar, so we need tables, turn
 *                           times and opening hours. Six steps.
 *   book into Square      → Square owns availability; asking for our own
 *                           tables and hours would be asking twice and would
 *                           let the two disagree. Three steps and an OAuth.
 *   text them your link   → we hold nothing at all. Three steps, one of which
 *                           is pasting a URL.
 *
 * NOTHING IS LIVE UNTIL THE LAST STEP. booking_mode is written last by
 * POST /api/bookings/setup, after the things it depends on exist — so a
 * merchant who abandons this half way is exactly as they were, rather than
 * live with an empty calendar and a phone agent offering times against it.
 */
import { useTradePack } from '@/config/moduleFlags'
import { useState } from 'react'
import {
  ArrowLeft, ArrowRight, Armchair, Building2, Car, Check, HeartPulse, Loader2,
  MessageSquare, Phone, Plus, Scissors, Sparkles, Trash2, UtensilsCrossed,
} from 'lucide-react'
import { Select } from '@/components/ui/Select'
import { ALL_PACKS, type NichePack } from '@/config/niches'
import { bookingsApi, type HoursRow, type ResourceKind } from '@/lib/bookings-api'

type Mode = 'native' | 'provider' | 'external_link'
type Step = 'vertical' | 'mode' | 'link' | 'resources' | 'services' | 'hours' | 'review'

/**
 * The vertical choices come from the shared niche packs (config/niches.ts) so
 * the wizard, the sales pitch and anything built on top of a trade cannot
 * drift apart. Trades that do not book at all are filtered out here rather
 * than offered a table plan they will never use.
 */
const PRESETS = ALL_PACKS.filter((p) => p.booksAtAll)

const ICONS: Record<string, typeof UtensilsCrossed> = {
  restaurant: UtensilsCrossed,
  barbershop: Scissors,
  nails: Sparkles,
  detailing: Car,
  medspa: HeartPulse,
  other: Building2,
}

const BLURBS: Record<string, string> = {
  restaurant: 'Tables, party sizes, turn times',
  barbershop: 'Chairs, named services, back to back',
  nails: 'Technicians, longer sittings, rebooking',
  detailing: 'Bays, long jobs, one car at a time',
  medspa: 'Treatment rooms, consultations, follow-ups',
  other: 'People and appointments',
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/** Up to a full day: a full detail is a 4-hour job and a wedding party books
 *  a room for the evening. */
const DURATIONS = [15, 30, 45, 60, 90, 120, 180, 240, 300, 360, 480]

export default function BookingsWizard({ merchantId, onDone, onSkip }: {
  merchantId: string
  onDone: () => void
  onSkip: () => void
}) {
  /**
   * Start on the trade the account was SOLD as.
   *
   * The rep already chose it, it is on the organization, and it is what the
   * rest of the portal is already rendering. Opening this wizard on
   * "Barbershop & salon" for a med spa asked the merchant a question we had
   * the answer to, and invited them to give a different one — after which
   * their book and their portal would disagree about what business they run.
   *
   * Still changeable: the rep can pick wrong, and the merchant is the
   * authority on their own shop.
   */
  const soldAs = useTradePack()
  const initial = PRESETS.find((p) => p.key === soldAs.key) || PRESETS[0]

  const [step, setStep] = useState<Step>('vertical')
  const [preset, setPreset] = useState<NichePack>(initial)
  const [mode, setMode] = useState<Mode>('native')
  const [linkUrl, setLinkUrl] = useState('')
  const [count, setCount] = useState(initial.defaultCount)
  const [seats, setSeats] = useState(initial.defaultSeats)
  const [services, setServices] = useState(initial.services)
  const [days, setDays] = useState<number[]>(initial.days)
  const [opens, setOpens] = useState(initial.opens)
  const [closes, setCloses] = useState(initial.closes)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const choosePreset = (p: NichePack) => {
    setPreset(p)
    setCount(p.defaultCount)
    setSeats(p.defaultSeats)
    setServices(p.services)
    setDays(p.days)
    setOpens(p.opens)
    setCloses(p.closes)
  }

  // Only the "we take the booking" path needs to know about capacity — the
  // other two are asking Square or the merchant's own site instead.
  const FLOW: Record<Mode, Step[]> = {
    native: ['vertical', 'mode', 'resources', 'services', 'hours', 'review'],
    provider: ['vertical', 'mode', 'review'],
    external_link: ['vertical', 'mode', 'link', 'review'],
  }
  const flow = FLOW[mode]
  const index = Math.max(0, flow.indexOf(step))

  const go = (delta: number) => {
    const next = flow[index + delta]
    if (next) setStep(next)
  }

  /**
   * Name resources after what the TRADE calls them.
   *
   * This mapped the resource KIND, which only covered table/chair/bay and
   * dropped everything else onto "Staff". So a med spa was asked "how many
   * treatment rooms do you have?" and told "we'll add them as Staff 1", and a
   * mobile detailer was asked about vans and told the same. Both questions
   * already knew the right word — countLabel — and were not using it.
   *
   * The kind map stays as the fallback for a pack with no label of its own.
   */
  const resourceNames = Array.from({ length: count }, (_, i) => {
    const labelled = (preset.countLabel || '').trim().replace(/s$/i, '')
    const base = labelled || (
      preset.resourceKind === 'table' ? 'Table'
        : preset.resourceKind === 'chair' ? 'Chair'
        : preset.resourceKind === 'bay' ? 'Bay'
        : preset.resourceKind === 'room' ? 'Room' : 'Staff'
    )
    return `${base} ${i + 1}`
  })

  const hours: HoursRow[] = days.map((weekday) => ({
    weekday, opensAt: opens, closesAt: closes, slotMinutes: 15,
  }))

  const finish = async () => {
    setBusy(true)
    setError('')
    try {
      await bookingsApi.applySetup({
        merchantId,
        mode,
        noun: preset.bookingNoun,
        linkUrl: mode === 'external_link' ? linkUrl.trim() : '',
        resources: mode === 'native'
          ? resourceNames.map((name, i) => ({
              name, kind: preset.resourceKind,
              // A tee holds a group of up to four players; that is the band,
              // not a question to ask the operator.
              seats: preset.resourceKind === 'table' ? seats
                : preset.resourceKind === 'tee' ? 4 : 1,
              sortOrder: i,
            }))
          : [],
        services: mode === 'native'
          ? services.map((s) => ({
              name: s.name, durationMinutes: s.duration, bufferMinutes: s.buffer,
              minParty: s.min, maxParty: s.max,
            }))
          : [],
        hours: mode === 'native' ? hours : [],
      })
      onDone()
    } catch {
      setError('That did not save. Check the details and try again.')
      setBusy(false)
    }
  }

  const servicesValid = services.length > 0
    && services.every((s) => s.name.trim() && s.max >= s.min)

  const canAdvance =
    step === 'link'
      ? /^(https?:\/\/)?[\w.-]+\.[a-z]{2,}/i.test(linkUrl.trim())
      : step === 'services'
        ? servicesValid
        : true

  return (
    <div className="mx-auto max-w-2xl">
      <header className="mb-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold tracking-tight text-[#F5F5F7]">
            Set up bookings
          </h1>
          <button
            onClick={onSkip}
            className="text-xs text-[#6B6B73] transition-colors hover:text-[#A1A1A8]"
          >
            Set it up manually instead
          </button>
        </div>
        <div className="mt-3 flex gap-1.5" aria-hidden="true">
          {flow.map((s, i) => (
            <span
              key={s}
              className={`h-1 flex-1 rounded-full transition-colors duration-200 ${
                i <= index ? 'bg-[#1A8FD6]' : 'bg-[#1F1F23]'
              }`}
            />
          ))}
        </div>
        <p className="mt-2 text-xs text-[#6B6B73]">
          Step {index + 1} of {flow.length} · nothing goes live until the last one
        </p>
      </header>

      <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-6">
        {step === 'vertical' && (
          <Question
            title="What kind of business is this?"
            hint="It only sets the starting point — you can change everything after."
          >
            <div className="grid gap-2 sm:grid-cols-2">
              {PRESETS.map((p) => {
                const Icon = ICONS[p.key] || Building2
                const chosen = preset.key === p.key
                return (
                  <button
                    key={p.key}
                    // The chosen trade was signalled by colour alone, so a
                    // screen reader announced ten identical buttons and no
                    // state. It is also what makes the selection assertable.
                    aria-pressed={chosen}
                    onClick={() => choosePreset(p)}
                    className={`flex items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                      chosen
                        ? 'border-[#1A8FD6]/60 bg-[#1A8FD6]/10'
                        : 'border-[#1F1F23] hover:border-[#2A2A30]'
                    }`}
                  >
                    <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${
                      chosen ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'
                    }`} />
                    <span className="min-w-0">
                      <span className="block text-sm text-[#F5F5F7]">{p.label}</span>
                      <span className="block text-xs text-[#A1A1A8]">
                        {BLURBS[p.key] || ''}
                      </span>
                    </span>
                  </button>
                )
              })}
            </div>
          </Question>
        )}

        {step === 'mode' && (
          <Question
            title="Who should hold the calendar?"
            hint="This is the only answer that is hard to change later, so it is worth a moment."
          >
            <div className="space-y-2">
              <ModeCard
                selected={mode === 'native'}
                onSelect={() => setMode('native')}
                Icon={Phone}
                title="We take the booking"
                body="The phone agent checks what's free and books it. Best if you don't already run booking software."
              />
              <ModeCard
                selected={mode === 'provider'}
                onSelect={() => setMode('provider')}
                Icon={Armchair}
                title="Book into my Square Appointments"
                body="Square stays the source of truth and we book into it. Works on every Square plan, including the free one."
              />
              <ModeCard
                selected={mode === 'external_link'}
                onSelect={() => setMode('external_link')}
                Icon={MessageSquare}
                title="Text callers my own booking link"
                body="We never hold a calendar — the caller gets your booking page as a text, and you see who opened it."
              />
            </div>
          </Question>
        )}

        {step === 'link' && (
          <Question
            title="Where should callers be sent?"
            hint="We text this to them rather than reading it out — nobody writes down a web address while driving."
          >
            <input
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              placeholder="yourshop.ca/reservations"
              autoFocus
              className="w-full rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2.5 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
            />
          </Question>
        )}

        {step === 'resources' && (
          <Question
            title={preset.countTitle}
            hint={count > 1
              ? `We'll add them as ${resourceNames[0]} through to ${resourceNames[count - 1]}. Rename or resize any of them straight after.`
              : `We'll add it as ${resourceNames[0]}. You can rename it straight after.`}
          >
            <div className="flex flex-wrap items-end gap-4">
              <label className="space-y-1">
                <span className="block text-xs uppercase tracking-wide text-[#A1A1A8]">
                  {preset.countLabel}
                </span>
                <input
                  type="number" min={1} max={200} value={count}
                  onChange={(e) => setCount(Math.min(200, Math.max(1, Number(e.target.value) || 1)))}
                  className="w-24 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                />
              </label>
              {preset.resourceKind === 'table' && (
                <label className="space-y-1">
                  {/* "Most tables seat" rather than "Seats each": no restaurant
                      has identical tables, and a label that claims they do
                      makes an owner stop and correct us instead of moving on. */}
                  <span className="block text-xs uppercase tracking-wide text-[#A1A1A8]">
                    Most tables seat
                  </span>
                  <div className="flex items-center gap-2">
                    <input
                      type="number" min={1} max={100} value={seats}
                      onChange={(e) => setSeats(Math.min(100, Math.max(1, Number(e.target.value) || 1)))}
                      className="w-20 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                    />
                    <span className="text-sm text-[#A1A1A8]">people</span>
                  </div>
                </label>
              )}
            </div>
            {preset.resourceKind === 'table' && (
              <p className="mt-3 text-xs text-[#6B6B73]">
                Got a two-top and a big booth? Set the common size now and
                change the odd ones on the next screen.
              </p>
            )}
          </Question>
        )}

        {step === 'services' && (
          <Question
            title={preset.partyBanded
              ? preset.resourceKind === 'tee'
                ? 'How far apart are your tee times?'
                : 'How long does a table turn?'
              : 'What do you book, and for how long?'}
            hint={preset.partyBanded
              ? preset.resourceKind === 'tee'
                ? 'The agent books groups of one to four into each start. The length here is the gap between groups off the tee, not the round.'
                : 'The agent picks the right one from the party size. Turnaround is held after they leave, and never quoted to the guest.'
              : `Turnaround is the gap you need afterwards. It holds the ${preset.countLabel.toLowerCase().replace(/s$/, '')} without being part of what the customer is quoted.`}
          >
            <div className="space-y-2">
              {services.map((s, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2 rounded-lg border border-[#1F1F23] p-2.5">
                  <input
                    value={s.name}
                    placeholder={preset.partyBanded ? 'Table for 9–12' : 'What is it called?'}
                    onChange={(e) => setServices(services.map((x, j) =>
                      j === i ? { ...x, name: e.target.value } : x))}
                    className="min-w-[7rem] flex-1 rounded-md border border-[#1F1F23] bg-[#0A0A0B] px-2.5 py-1.5 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                  />
                  {/* A restaurant's "services" ARE party bands, so a new row
                      has to carry its range — a band added without one would
                      silently match nothing and the agent would say a party of
                      nine cannot be seated at all. */}
                  {preset.partyBanded && (
                    <span className="flex items-center gap-1 text-xs text-[#A1A1A8]">
                      parties
                      <input
                        type="number" min={1} max={100} value={s.min}
                        aria-label={`Smallest party for ${s.name || 'this option'}`}
                        onChange={(e) => setServices(services.map((x, j) =>
                          j === i ? { ...x, min: Math.max(1, Number(e.target.value) || 1) } : x))}
                        className="w-12 rounded-md border border-[#1F1F23] bg-[#0A0A0B] px-1.5 py-1.5 text-center text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                      />
                      to
                      <input
                        type="number" min={1} max={100} value={s.max}
                        aria-label={`Largest party for ${s.name || 'this option'}`}
                        onChange={(e) => setServices(services.map((x, j) =>
                          j === i ? { ...x, max: Math.max(1, Number(e.target.value) || 1) } : x))}
                        className="w-12 rounded-md border border-[#1F1F23] bg-[#0A0A0B] px-1.5 py-1.5 text-center text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                      />
                    </span>
                  )}
                  <Select
                    className="w-28"
                    ariaLabel={`How long ${s.name || 'this option'} takes`}
                    value={String(s.duration)}
                    onChange={(v) => setServices(services.map((x, j) =>
                      j === i ? { ...x, duration: Number(v) } : x))}
                    options={DURATIONS.map((m) => ({
                      value: String(m),
                      label: m >= 60 ? `${m / 60} hr${m > 60 ? 's' : ''}` : `${m} min`,
                    }))}
                  />
                  <Select
                    className={preset.partyBanded ? 'w-32' : 'w-40'}
                    ariaLabel={`Turnaround after ${s.name || 'this option'}`}
                    value={String(s.buffer)}
                    onChange={(v) => setServices(services.map((x, j) =>
                      j === i ? { ...x, buffer: Number(v) } : x))}
                    options={[0, 5, 10, 15, 30, 60].map((m) => ({
                      value: String(m),
                      label: m === 0
                        ? (preset.partyBanded ? 'No gap' : 'No turnaround')
                        : `+${m} min${preset.partyBanded ? '' : ' after'}`,
                    }))}
                  />
                  <button
                    onClick={() => setServices(services.filter((_, j) => j !== i))}
                    disabled={services.length === 1}
                    // The last one cannot go: a merchant with no services has
                    // nothing for the agent to work out a duration from.
                    title={services.length === 1
                      ? 'Keep at least one — it is what sets how long a booking lasts.'
                      : `Remove ${s.name || 'this one'}`}
                    aria-label={`Remove ${s.name || 'this one'}`}
                    className="rounded-md p-1.5 text-[#6B6B73] transition-colors hover:text-[#E5484D] disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:text-[#6B6B73]"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={() => setServices([...services, {
                name: '',
                // Longest of what they already have, since a merchant adding
                // a row is usually adding a bigger package rather than a
                // shorter one.
                duration: Math.max(...services.map((s) => s.duration), 30),
                buffer: services[services.length - 1]?.buffer ?? 0,
                min: preset.partyBanded
                  ? Math.max(...services.map((s) => s.max)) + 1 : 1,
                max: preset.partyBanded
                  ? Math.max(...services.map((s) => s.max)) + 4 : 1,
              }])}
              disabled={services.length >= 20}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-[#1F1F23] px-3 py-2 text-xs text-[#A1A1A8] transition-colors hover:border-[#1A8FD6]/40 hover:text-[#F5F5F7] disabled:opacity-40"
            >
              <Plus className="h-3.5 w-3.5" />
              {preset.partyBanded ? 'Add another party size' : 'Add another'}
            </button>

            {services.some((s) => !s.name.trim()) && (
              <p className="mt-2 text-xs text-[#6B6B73]">
                Give every line a name — it is what the agent says out loud.
              </p>
            )}
          </Question>
        )}

        {step === 'hours' && (
          <Question
            title="When can people book?"
            hint="A booking has to finish before you close, so we never offer a slot that runs past it."
          >
            <div className="mb-4 flex flex-wrap gap-1.5">
              {DAYS.map((label, d) => {
                const on = days.includes(d)
                return (
                  <button
                    key={d}
                    onClick={() => setDays(on ? days.filter((x) => x !== d) : [...days, d].sort())}
                    aria-pressed={on}
                    className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                      on
                        ? 'border-[#1A8FD6]/50 bg-[#1A8FD6]/10 text-[#1A8FD6]'
                        : 'border-[#1F1F23] text-[#6B6B73] hover:text-[#A1A1A8]'
                    }`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <label className="space-y-1">
                <span className="block text-xs uppercase tracking-wide text-[#A1A1A8]">Opens</span>
                <input
                  type="time" value={opens} onChange={(e) => setOpens(e.target.value)}
                  className="rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                />
              </label>
              <label className="space-y-1">
                <span className="block text-xs uppercase tracking-wide text-[#A1A1A8]">Closes</span>
                <input
                  type="time" value={closes} onChange={(e) => setCloses(e.target.value)}
                  className="rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                />
              </label>
            </div>
            <p className="mt-3 text-xs text-[#6B6B73]">
              Open past midnight? Set the late hours on the following day — a
              1am booking belongs to that day. You can do it on the setup page.
            </p>
          </Question>
        )}

        {step === 'review' && (
          <Question
            title="Ready to turn on"
            hint="Nothing has changed yet. This is the moment the phone agent starts offering bookings."
          >
            <dl className="divide-y divide-[#1F1F23] rounded-lg border border-[#1F1F23]">
              <Row label="Business">{preset.label}</Row>
              <Row label="Calendar">
                {mode === 'native' ? 'We take the booking'
                  : mode === 'provider' ? 'Books into Square Appointments'
                  : 'Callers get texted your link'}
              </Row>
              {mode === 'external_link' && <Row label="Link">{linkUrl}</Row>}
              {mode === 'native' && (
                <>
                  <Row label={preset.countLabel}>
                    {count}{preset.resourceKind === 'table' ? ` · mostly ${seats} seats` : ''}
                  </Row>
                  <Row label="Bookable">
                    {services.map((s) => `${s.name} (${s.duration} min)`).join(', ')}
                  </Row>
                  <Row label="Open">
                    {days.length === 0 ? 'No days selected'
                      : `${days.map((d) => DAYS[d]).join(', ')} · ${opens}–${closes}`}
                  </Row>
                </>
              )}
              <Row label="The agent will say">“{preset.bookingNoun}”</Row>
            </dl>

            {mode === 'provider' && (
              <p className="mt-3 text-xs text-[#A1A1A8]">
                One more step after this: you'll be sent to Square to approve
                booking access. Until you do, nothing is booked.
              </p>
            )}
            {error && <p className="mt-3 text-xs text-[#E5484D]">{error}</p>}
          </Question>
        )}

        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={() => go(-1)}
            disabled={index === 0 || busy}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-[#A1A1A8] transition-colors hover:text-[#F5F5F7] disabled:invisible"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>

          {step === 'review' ? (
            <button
              onClick={finish}
              disabled={busy || (mode === 'native' && days.length === 0)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#1A8FD6]/50 bg-[#1A8FD6]/15 px-4 py-2 text-sm font-medium text-[#1A8FD6] transition-colors hover:bg-[#1A8FD6]/25 disabled:opacity-40"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Turn bookings on
            </button>
          ) : (
            <button
              onClick={() => go(1)}
              disabled={!canAdvance}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#1F1F23] px-4 py-2 text-sm text-[#F5F5F7] transition-colors hover:border-[#1A8FD6]/40 disabled:opacity-40"
            >
              Next
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </section>
    </div>
  )
}

function Question({ title, hint, children }: {
  title: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div>
      <h2 className="text-base font-medium text-[#F5F5F7]">{title}</h2>
      {hint && <p className="mb-4 mt-1 text-sm text-[#A1A1A8]">{hint}</p>}
      {children}
    </div>
  )
}

function ModeCard({ selected, onSelect, Icon, title, body }: {
  selected: boolean
  onSelect: () => void
  Icon: typeof Phone
  title: string
  body: string
}) {
  return (
    <button
      onClick={onSelect}
      className={`flex w-full items-start gap-3 rounded-lg border p-3.5 text-left transition-colors ${
        selected ? 'border-[#1A8FD6]/60 bg-[#1A8FD6]/10' : 'border-[#1F1F23] hover:border-[#2A2A30]'
      }`}
    >
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${selected ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'}`} />
      <span className="min-w-0">
        <span className="block text-sm text-[#F5F5F7]">{title}</span>
        <span className="mt-0.5 block text-xs text-[#A1A1A8]">{body}</span>
      </span>
    </button>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 px-3 py-2.5">
      <dt className="shrink-0 text-xs uppercase tracking-wide text-[#A1A1A8]">{label}</dt>
      <dd className="min-w-0 text-right text-sm text-[#F5F5F7]">{children}</dd>
    </div>
  )
}
