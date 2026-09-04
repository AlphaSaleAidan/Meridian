/**
 * The vertical switcher's data spine. One brain, many trades: picking a card
 * swaps the ENTIRE page's transcript, vocabulary, artifact, and demo line in
 * place — segmentation as an interactive device, never separate pages.
 * (Competitors ship restaurants-only or gesture at verticals with generic
 * copy; this is the page proving the niche packs are real.)
 *
 * Every transcript here is the product's actual behavior — no capability is
 * scripted that the agent cannot do (order → POS, booking → Square
 * Appointments, waitlist text offers).
 */

export interface TranscriptLine {
  speaker: 'caller' | 'agent'
  text: string
}

export interface VerticalArtifact {
  /** The panel title, e.g. "Square Dashboard" */
  panel: string
  /** The row that appears when the call ends — the proof. */
  headline: string
  detail: string
  amount?: string
}

export interface Vertical {
  key: string
  label: string
  /** short noun the trade thinks in — chair, table, bay */
  seat: string
  headline: string
  sub: string
  transcript: TranscriptLine[]
  artifact: VerticalArtifact
  /** Live line when one exists; empty string = demo-booking CTA instead. */
  demoNumber: string
  demoNumberE164: string
  demoLabel: string
}

export const DEMO_LINE = {
  display: '+1 380 240 9535',
  e164: '+13802409535',
} as const

export const VERTICALS: Vertical[] = [
  {
    key: 'restaurant',
    label: 'Restaurants',
    seat: 'table',
    headline: 'Answer every call. Fill every table.',
    sub: 'Meridian answers 24/7, takes orders and reservations straight into your POS, and texts your waitlist the moment a table opens.',
    transcript: [
      { speaker: 'caller', text: 'Hey, can I get a large pepperoni and a Caesar salad for pickup?' },
      { speaker: 'agent', text: 'Absolutely — one large pepperoni, one Caesar. That’s $31.40. I’ll text you a payment link and it’ll be ready in 20 minutes.' },
      { speaker: 'caller', text: 'Perfect.' },
      { speaker: 'agent', text: 'Order’s in. See you at 7:15.' },
    ],
    artifact: {
      panel: 'Your POS — live',
      headline: 'Order #1042 · PAID',
      detail: 'Lg pepperoni · Caesar salad · pickup 7:15',
      amount: '$31.40',
    },
    demoNumber: DEMO_LINE.display,
    demoNumberE164: DEMO_LINE.e164,
    demoLabel: 'Call our live demo restaurant',
  },
  {
    key: 'barbershop',
    label: 'Barbershops & salons',
    seat: 'chair',
    headline: 'Your chair is never empty because nobody answered.',
    sub: 'Meridian books appointments straight into Square Appointments, texts deposits and reminders, and texts your waitlist when a slot frees up.',
    transcript: [
      { speaker: 'caller', text: 'Can I get a fade with Marcus on Saturday?' },
      { speaker: 'agent', text: 'Marcus has 11:30 or 2:00 on Saturday — which works?' },
      { speaker: 'caller', text: '2 o’clock.' },
      { speaker: 'agent', text: 'Booked — Saturday 2 PM with Marcus. There’s a $10 deposit to hold the chair; I just texted you the link.' },
    ],
    artifact: {
      panel: 'Square Appointments — live',
      headline: 'Sat 2:00 PM · Marcus',
      detail: 'Skin fade · deposit requested',
      amount: '$10 deposit',
    },
    demoNumber: '',
    demoNumberE164: '',
    demoLabel: 'Book a 15-minute demo',
  },
  {
    key: 'trades',
    label: 'Golf & service trades',
    seat: 'tee time',
    headline: 'The pro shop phone, answered on the first ring.',
    sub: 'Tee sheets, detailing bays, med spa chairs — Meridian books them all, takes payment links, and never puts a customer on hold.',
    transcript: [
      { speaker: 'caller', text: 'Do you have anything for four players tomorrow morning?' },
      { speaker: 'agent', text: 'Tomorrow I’ve got 8:40 or 10:10 for a foursome. Carts included?' },
      { speaker: 'caller', text: '8:40 with carts.' },
      { speaker: 'agent', text: 'You’re on the tee sheet — 8:40, four players, two carts. Confirmation’s on its way by text.' },
    ],
    artifact: {
      panel: 'Tee sheet — live',
      headline: '8:40 AM · 4 players',
      detail: '2 carts · confirmation texted',
      amount: '$260',
    },
    demoNumber: '+1 240 525 9305',
    demoNumberE164: '+12405259305',
    demoLabel: 'Call our live demo golf course',
  },
]

/** Cost table — every number here is real and checkable. */
export const COST_ROWS = [
  { who: 'Meridian', price: 'from US$250/mo', perMin: 'flat monthly', note: 'phone agent + POS analytics + cameras, month to month' },
  { who: 'Slang.ai', price: '$399–599/mo', perMin: 'unlimited minutes', note: 'answering + reservations only' },
  { who: 'Popmenu AI', price: '~$349/mo', perMin: '—', note: 'part of marketing bundle' },
  { who: 'Loman.ai', price: '$399/mo', perMin: '+ $0.50/min', note: 'per-minute overage' },
  { who: 'Fresha AI', price: '$99.95/loc', perMin: '$0.60/min over 200', note: 'salons; overage-priced' },
] as const
