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
import { useState } from 'react'
import {
  ArrowLeft, ArrowRight, Armchair, Building2, Car, Check, Loader2,
  MessageSquare, Phone, Scissors, UtensilsCrossed,
} from 'lucide-react'
import { Select } from '@/components/ui/Select'
import { bookingsApi, type HoursRow, type ResourceKind } from '@/lib/bookings-api'

type Mode = 'native' | 'provider' | 'external_link'
type Step = 'vertical' | 'mode' | 'link' | 'resources' | 'services' | 'hours' | 'review'

interface Preset {
  key: string
  label: string
  blurb: string
  Icon: typeof UtensilsCrossed
  noun: string
  kind: ResourceKind
  /** What one unit of capacity is called, singular, for review copy. */
  unitLabel: string
  /**
   * The count question, written out per vertical rather than assembled from
   * the unit label. "How many people take appointments?" is not a template of
   * "How many <unit>s do you have?", and an earlier version that tried to
   * generate it produced "How many tables can be booked at once?" — which
   * reads as a limit on the guest rather than a count of what the shop owns.
   */
  countTitle: string
  /** Field label above the number box. */
  countLabel: string
  defaultCount: number
  defaultSeats: number
  /** Restaurants band by party size; everyone else books a named service. */
  partyBanded: boolean
  services: { name: string; duration: number; buffer: number; min: number; max: number }[]
  days: number[]
  opens: string
  closes: string
}

/**
 * Per-vertical defaults. These are guesses, and every one is editable on the
 * next screen — the point is that a merchant who agrees with all of them can
 * press Next four times, which is the difference between finishing in the
 * meeting and "I'll do it later".
 */
const PRESETS: Preset[] = [
  {
    key: 'restaurant',
    label: 'Restaurant or bar',
    blurb: 'Tables, party sizes, turn times',
    Icon: UtensilsCrossed,
    noun: 'table', kind: 'table', unitLabel: 'table',
    countTitle: 'How many tables do you have?', countLabel: 'Tables',
    defaultCount: 8, defaultSeats: 4, partyBanded: true,
    services: [
      { name: 'Table for 1–4', duration: 90, buffer: 15, min: 1, max: 4 },
      { name: 'Table for 5–8', duration: 120, buffer: 15, min: 5, max: 8 },
    ],
    days: [0, 2, 3, 4, 5, 6], opens: '17:00', closes: '22:00',
  },
  {
    key: 'barbershop',
    label: 'Barbershop or salon',
    blurb: 'Chairs, named services, back to back',
    Icon: Scissors,
    noun: 'appointment', kind: 'chair', unitLabel: 'chair',
    countTitle: 'How many chairs do you have?', countLabel: 'Chairs',
    defaultCount: 3, defaultSeats: 1, partyBanded: false,
    services: [
      { name: 'Haircut', duration: 30, buffer: 5, min: 1, max: 1 },
      { name: 'Cut and beard', duration: 45, buffer: 5, min: 1, max: 1 },
    ],
    days: [2, 3, 4, 5, 6], opens: '09:00', closes: '18:00',
  },
  {
    key: 'detailing',
    label: 'Auto detailing',
    blurb: 'Bays, long jobs, one car at a time',
    Icon: Car,
    noun: 'appointment', kind: 'bay', unitLabel: 'bay',
    countTitle: 'How many bays do you have?', countLabel: 'Bays',
    defaultCount: 2, defaultSeats: 1, partyBanded: false,
    services: [
      { name: 'Interior and exterior', duration: 120, buffer: 15, min: 1, max: 1 },
      { name: 'Full detail', duration: 240, buffer: 30, min: 1, max: 1 },
    ],
    days: [1, 2, 3, 4, 5, 6], opens: '08:00', closes: '17:00',
  },
  {
    key: 'other',
    label: 'Something else',
    blurb: 'People and appointments',
    Icon: Building2,
    noun: 'appointment', kind: 'staff', unitLabel: 'person',
    countTitle: 'How many people take appointments?', countLabel: 'People',
    defaultCount: 2, defaultSeats: 1, partyBanded: false,
    services: [{ name: 'Appointment', duration: 60, buffer: 0, min: 1, max: 1 }],
    days: [1, 2, 3, 4, 5], opens: '09:00', closes: '17:00',
  },
]

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export default function BookingsWizard({ merchantId, onDone, onSkip }: {
  merchantId: string
  onDone: () => void
  onSkip: () => void
}) {
  const [step, setStep] = useState<Step>('vertical')
  const [preset, setPreset] = useState<Preset>(PRESETS[0])
  const [mode, setMode] = useState<Mode>('native')
  const [linkUrl, setLinkUrl] = useState('')
  const [count, setCount] = useState(PRESETS[0].defaultCount)
  const [seats, setSeats] = useState(PRESETS[0].defaultSeats)
  const [services, setServices] = useState(PRESETS[0].services)
  const [days, setDays] = useState<number[]>(PRESETS[0].days)
  const [opens, setOpens] = useState(PRESETS[0].opens)
  const [closes, setCloses] = useState(PRESETS[0].closes)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const choosePreset = (p: Preset) => {
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

  const resourceNames = Array.from({ length: count }, (_, i) => {
    const base = preset.kind === 'table' ? 'Table'
      : preset.kind === 'chair' ? 'Chair'
      : preset.kind === 'bay' ? 'Bay' : 'Staff'
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
        noun: preset.noun,
        linkUrl: mode === 'external_link' ? linkUrl.trim() : '',
        resources: mode === 'native'
          ? resourceNames.map((name, i) => ({
              name, kind: preset.kind,
              seats: preset.kind === 'table' ? seats : 1,
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

  const canAdvance =
    step !== 'link' || /^(https?:\/\/)?[\w.-]+\.[a-z]{2,}/i.test(linkUrl.trim())

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
              {PRESETS.map((p) => (
                <button
                  key={p.key}
                  onClick={() => choosePreset(p)}
                  className={`flex items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                    preset.key === p.key
                      ? 'border-[#1A8FD6]/60 bg-[#1A8FD6]/10'
                      : 'border-[#1F1F23] hover:border-[#2A2A30]'
                  }`}
                >
                  <p.Icon className={`mt-0.5 h-4 w-4 shrink-0 ${
                    preset.key === p.key ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'
                  }`} />
                  <span className="min-w-0">
                    <span className="block text-sm text-[#F5F5F7]">{p.label}</span>
                    <span className="block text-xs text-[#A1A1A8]">{p.blurb}</span>
                  </span>
                </button>
              ))}
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
              {preset.kind === 'table' && (
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
            {preset.kind === 'table' && (
              <p className="mt-3 text-xs text-[#6B6B73]">
                Got a two-top and a big booth? Set the common size now and
                change the odd ones on the next screen.
              </p>
            )}
          </Question>
        )}

        {step === 'services' && (
          <Question
            title={preset.partyBanded ? 'How long does a table turn?' : 'What do you book, and for how long?'}
            hint={preset.partyBanded
              ? 'The agent picks the right one from the party size. Turnaround is held after they leave, and never quoted to the guest.'
              : 'Turnaround is the gap you need afterwards. It blocks the chair without being part of their appointment.'}
          >
            <div className="space-y-2">
              {services.map((s, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2 rounded-lg border border-[#1F1F23] p-2.5">
                  <input
                    value={s.name}
                    onChange={(e) => setServices(services.map((x, j) =>
                      j === i ? { ...x, name: e.target.value } : x))}
                    className="min-w-[8rem] flex-1 rounded-md border border-[#1F1F23] bg-[#0A0A0B] px-2.5 py-1.5 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                  />
                  <Select
                    className="w-32"
                    ariaLabel={`How long ${s.name} takes`}
                    value={String(s.duration)}
                    onChange={(v) => setServices(services.map((x, j) =>
                      j === i ? { ...x, duration: Number(v) } : x))}
                    options={[15, 30, 45, 60, 90, 120, 180, 240].map((m) => ({
                      value: String(m),
                      label: m >= 60 ? `${m / 60} hr${m > 60 ? 's' : ''}` : `${m} min`,
                    }))}
                  />
                  <Select
                    className="w-36"
                    ariaLabel={`Turnaround after ${s.name}`}
                    value={String(s.buffer)}
                    onChange={(v) => setServices(services.map((x, j) =>
                      j === i ? { ...x, buffer: Number(v) } : x))}
                    options={[0, 5, 10, 15, 30].map((m) => ({
                      value: String(m),
                      label: m === 0 ? 'No turnaround' : `+${m} min after`,
                    }))}
                  />
                </div>
              ))}
            </div>
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
                    {count}{preset.kind === 'table' ? ` · mostly ${seats} seats` : ''}
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
              <Row label="The agent will say">“{preset.noun}”</Row>
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
