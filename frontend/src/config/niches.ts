/**
 * US niche packs — one product, configured per trade.
 *
 * The bet: a barbershop and a pizza place do not want the same software, but
 * they do not want DIFFERENT software either. They want the same engine with
 * the right words on it, the right defaults in it, and the parts they will
 * never use out of the way.
 *
 * A PACK IS DATA. Nothing here forks a component, and nothing here is allowed
 * to. The moment a pack needs its own screen, the pack model has failed and
 * the answer is a better shared screen, not a second codebase — because two
 * codebases means every fix lands in one of them.
 *
 * What a pack is allowed to change:
 *   vocabulary  — what the product and the phone agent call things
 *   defaults    — what the setup wizard fills in before anyone types
 *   emphasis    — which module a trade is sold on
 *
 * What a pack must never change: the booking engine, the exclusion
 * constraint, the auth model, or anything a merchant could be harmed by
 * getting wrong.
 *
 * Selection order: the rep picks the trade at signup, and the merchant can
 * change it later. It is a starting point, not a cage — a detailer who also
 * rents a bay by the hour must not be locked out of doing that.
 */
import type { ResourceKind } from '@/lib/bookings-api'

export interface PackService {
  name: string
  duration: number
  buffer: number
  min: number
  max: number
}

export interface NichePack {
  key: string
  label: string
  /** What the rep says in one line. Written to be said out loud, not read. */
  pitch: string

  // ── Vocabulary ────────────────────────────────────────────────────────
  /** What the phone agent calls a booking: "table", "appointment", "slot". */
  bookingNoun: string
  /** What the shop calls the person: "guest", "client", "customer". */
  customerNoun: string
  /** The unit of capacity, and what the portal labels it. */
  resourceKind: ResourceKind
  /** Written per trade, not templated — "How many people take appointments?"
   *  is not a rendering of "How many <unit>s do you have?". */
  countTitle: string
  countLabel: string

  // ── Booking defaults ──────────────────────────────────────────────────
  /**
   * false means this trade does not book at all. A pizza shop's phone is
   * ordering volume, not a calendar, and offering it a table plan is how a
   * product loses a merchant in the first week. The pack says so out loud
   * rather than leaving them to discover the feature is irrelevant.
   */
  booksAtAll: boolean
  defaultCount: number
  defaultSeats: number
  /** Restaurants band by party size; every other trade books a named thing. */
  partyBanded: boolean
  services: PackService[]
  /** 0 = Sunday. */
  days: number[]
  opens: string
  closes: string

  /** True when the work happens at the customer's address, which changes what
   *  a booking needs to carry (where, and how long to get there). Not yet
   *  implemented — see docs; declared here because the packs that need it are
   *  exactly the packs worth building next. */
  travels?: boolean
}

/**
 * The six US trades worth targeting first, chosen on three things: the phone
 * still rings, Square is already in the building, and one person can sell to
 * them without an enterprise motion.
 */
export const NICHE_PACKS: NichePack[] = [
  {
    key: 'barbershop',
    label: 'Barbershop & salon',
    pitch: 'Your chair is never empty because nobody answered the phone.',
    bookingNoun: 'appointment',
    customerNoun: 'client',
    resourceKind: 'chair',
    countTitle: 'How many chairs do you have?',
    countLabel: 'Chairs',
    booksAtAll: true,
    defaultCount: 3,
    defaultSeats: 1,
    partyBanded: false,
    services: [
      { name: 'Haircut', duration: 30, buffer: 5, min: 1, max: 1 },
      { name: 'Cut and beard', duration: 45, buffer: 5, min: 1, max: 1 },
      { name: 'Skin fade', duration: 45, buffer: 5, min: 1, max: 1 },
    ],
    days: [2, 3, 4, 5, 6],
    opens: '09:00',
    closes: '18:00',
  },
  {
    key: 'nails',
    label: 'Nail & lash studio',
    pitch: 'Rebook the client while she is still in the chair, and fill the gap when she cancels.',
    bookingNoun: 'appointment',
    customerNoun: 'client',
    resourceKind: 'staff',
    countTitle: 'How many technicians work at once?',
    countLabel: 'Technicians',
    booksAtAll: true,
    defaultCount: 4,
    defaultSeats: 1,
    partyBanded: false,
    services: [
      { name: 'Gel manicure', duration: 45, buffer: 10, min: 1, max: 1 },
      { name: 'Full set', duration: 90, buffer: 15, min: 1, max: 1 },
      { name: 'Fill', duration: 60, buffer: 10, min: 1, max: 1 },
      { name: 'Lash extensions', duration: 120, buffer: 15, min: 1, max: 1 },
    ],
    days: [1, 2, 3, 4, 5, 6],
    opens: '09:00',
    closes: '19:00',
  },
  {
    key: 'detailing',
    label: 'Auto detailing',
    pitch: 'Every quote call becomes a booked bay instead of a voicemail.',
    bookingNoun: 'appointment',
    customerNoun: 'customer',
    resourceKind: 'bay',
    countTitle: 'How many bays do you have?',
    countLabel: 'Bays',
    booksAtAll: true,
    defaultCount: 2,
    defaultSeats: 1,
    partyBanded: false,
    services: [
      { name: 'Wash and wax', duration: 90, buffer: 15, min: 1, max: 1 },
      { name: 'Interior and exterior', duration: 120, buffer: 15, min: 1, max: 1 },
      { name: 'Full detail', duration: 240, buffer: 30, min: 1, max: 1 },
      { name: 'Ceramic coating', duration: 480, buffer: 60, min: 1, max: 1 },
    ],
    days: [1, 2, 3, 4, 5, 6],
    opens: '08:00',
    closes: '17:00',
    travels: true,
  },
  {
    key: 'restaurant',
    label: 'Full-service restaurant',
    pitch: 'The 7pm that cancels at 4 gets refilled before you notice it went.',
    bookingNoun: 'table',
    customerNoun: 'guest',
    resourceKind: 'table',
    countTitle: 'How many tables do you have?',
    countLabel: 'Tables',
    booksAtAll: true,
    defaultCount: 8,
    defaultSeats: 4,
    partyBanded: true,
    services: [
      { name: 'Table for 1–4', duration: 90, buffer: 15, min: 1, max: 4 },
      { name: 'Table for 5–8', duration: 120, buffer: 15, min: 5, max: 8 },
    ],
    days: [0, 2, 3, 4, 5, 6],
    opens: '17:00',
    closes: '22:00',
  },
  {
    key: 'quickservice',
    label: 'Pizza & takeout',
    pitch: 'Nobody waits on hold at 6pm on a Friday.',
    bookingNoun: 'order',
    customerNoun: 'customer',
    resourceKind: 'table',
    countTitle: '',
    countLabel: '',
    // Deliberately false. A takeout shop's phone is ORDER volume, and handing
    // it a table plan is how you lose a merchant in week one — they conclude
    // the product was not built for them, and they are right.
    booksAtAll: false,
    defaultCount: 0,
    defaultSeats: 0,
    partyBanded: false,
    services: [],
    days: [0, 1, 2, 3, 4, 5, 6],
    opens: '11:00',
    closes: '22:00',
  },
  {
    key: 'medspa',
    label: 'Med spa & wellness',
    pitch: 'A missed call is a $400 appointment that went to the place down the road.',
    bookingNoun: 'appointment',
    customerNoun: 'client',
    resourceKind: 'room',
    countTitle: 'How many treatment rooms do you have?',
    countLabel: 'Rooms',
    booksAtAll: true,
    defaultCount: 3,
    defaultSeats: 1,
    partyBanded: false,
    services: [
      { name: 'Consultation', duration: 30, buffer: 10, min: 1, max: 1 },
      { name: 'Facial', duration: 60, buffer: 15, min: 1, max: 1 },
      { name: 'Injectables', duration: 45, buffer: 15, min: 1, max: 1 },
      { name: 'Laser session', duration: 90, buffer: 20, min: 1, max: 1 },
    ],
    days: [1, 2, 3, 4, 5],
    opens: '09:00',
    closes: '18:00',
  },
]

/** The pack a merchant with nothing chosen falls back to. Generic on purpose:
 *  a wrong-but-confident guess is worse than an obviously neutral one. */
export const GENERIC_PACK: NichePack = {
  key: 'other',
  label: 'Something else',
  pitch: 'The phone gets answered, and what it produces lands somewhere you can see it.',
  bookingNoun: 'appointment',
  customerNoun: 'customer',
  resourceKind: 'staff',
  countTitle: 'How many people take appointments?',
  countLabel: 'People',
  booksAtAll: true,
  defaultCount: 2,
  defaultSeats: 1,
  partyBanded: false,
  services: [{ name: 'Appointment', duration: 60, buffer: 0, min: 1, max: 1 }],
  days: [1, 2, 3, 4, 5],
  opens: '09:00',
  closes: '17:00',
}

export const ALL_PACKS = [...NICHE_PACKS, GENERIC_PACK]

export function packFor(key: string | null | undefined): NichePack {
  return ALL_PACKS.find((p) => p.key === key) || GENERIC_PACK
}
