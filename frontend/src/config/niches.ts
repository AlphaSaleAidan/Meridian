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
import type { ModuleFlags } from '@/config/moduleFlags'
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

  // ── What this trade's Meridian actually contains ──────────────────────
  /**
   * Modules this trade never sees. TURNING OFF ONLY — flagsForMerchant applies
   * these with AND, so a pack can never resurrect a module its market cut.
   *
   * Camera is off for every trade below and that is not an oversight: it is
   * core to none of them. A module nobody's trade needs is a module in the way.
   */
  modules?: Partial<ModuleFlags>
  /**
   * Pillar paths in the order this trade should meet them, most valuable
   * first. Anything unlisted keeps its natural position after these.
   * '' is Overview.
   */
  pillarOrder?: string[]
  /**
   * The number that leads the home screen. This is the test of whether a pack
   * is real: if a trade's Meridian opens on the same figure as every other
   * trade's, it is a theme, not a version.
   */
  homeMetric: { label: string; help: string }

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
    modules: { inventory: false, camera: false, taxExpenses: false, topActions: false },
    pillarOrder: ['bookings', 'phone', '', 'schedule'],
    homeMetric: { label: 'Chair hours filled today',
                  help: 'Booked minutes against the hours your chairs are open.' },
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
    modules: { inventory: false, camera: false, taxExpenses: false, topActions: false },
    pillarOrder: ['bookings', 'phone', '', 'schedule'],
    homeMetric: { label: 'Clients rebooked before they left',
                  help: 'The cheapest appointment you will ever sell is the next one.' },
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
    modules: { inventory: false, camera: false, schedule: false, taxExpenses: false, topActions: false },
    pillarOrder: ['bookings', 'phone', ''],
    homeMetric: { label: 'Bay hours sold today',
                  help: 'A bay standing empty is the only thing that costs you money.' },
  },
  {
    // Split from shop detailing on purpose. They look like one trade and are
    // not: a shop runs jobs in PARALLEL across bays, a mobile operator runs
    // them in SERIES down a road. Modelling mobile as "a shop with bays"
    // produced a route with two stops at the same time, which is not a
    // scheduling edge case — it is physically impossible.
    key: 'mobiledetailing',
    label: 'Mobile detailing',
    pitch: 'Your day is a route, and it either fits or it does not.',
    bookingNoun: 'appointment',
    customerNoun: 'customer',
    resourceKind: 'staff',
    countTitle: 'How many vans are on the road?',
    countLabel: 'Vans',
    booksAtAll: true,
    defaultCount: 1,
    defaultSeats: 1,
    partyBanded: false,
    services: [
      { name: 'Exterior wash', duration: 60, buffer: 15, min: 1, max: 1 },
      { name: 'Interior and exterior', duration: 120, buffer: 20, min: 1, max: 1 },
      { name: 'Full detail', duration: 240, buffer: 30, min: 1, max: 1 },
    ],
    days: [1, 2, 3, 4, 5, 6],
    opens: '08:00',
    closes: '18:00',
    modules: { inventory: false, camera: false, schedule: false, taxExpenses: false, topActions: false },
    pillarOrder: ['', 'bookings', 'phone'],
    homeMetric: { label: 'Stops on today\'s route',
                  help: 'Not how many you booked — how many you can actually reach.' },
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
    modules: { camera: false },
    pillarOrder: ['bookings', 'phone', '', 'inventory', 'schedule'],
    homeMetric: { label: 'Covers booked tonight',
                  help: 'Guests expected, not tables — a four-top and a two-top are not the same night.' },
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
    modules: { bookings: false, camera: false, schedule: false },
    pillarOrder: ['phone', '', 'inventory'],
    homeMetric: { label: 'Orders taken by phone',
                  help: 'Orders the agent took while the line was busy — the ones you would have lost.' },
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
    modules: { inventory: false, camera: false, taxExpenses: false, topActions: false },
    pillarOrder: ['bookings', 'phone', '', 'schedule'],
    homeMetric: { label: 'Consultations booked this week',
                  help: 'A consultation is the start of a treatment plan, not a single sale.' },
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
  // Deliberately empty. Every merchant in production today has no trade set,
  // and they must keep exactly the portal they had this morning.
  modules: {},
  homeMetric: { label: 'Bookings today', help: 'What is on the book for today.' },
}

export const ALL_PACKS = [...NICHE_PACKS, GENERIC_PACK]

export function packFor(key: string | null | undefined): NichePack {
  return ALL_PACKS.find((p) => p.key === key) || GENERIC_PACK
}
