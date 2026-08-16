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
  /** US list price in cents. Money is the first thing an owner looks at, so a
   *  pack that cannot price its own services cannot show them revenue. */
  price?: number
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
   * Segment views this trade never sees, as "pillar/view".
   *
   * Pillar-level on/off was too blunt and cost real features. A barbershop
   * absolutely tracks margin — it sells pomade and burns through blades — so
   * switching Inventory off to "simplify" removed the tool that tells them
   * whether the retail shelf pays for itself. What it does NOT need is Menu
   * Matrix, which is a restaurant instrument.
   *
   * So the rule is: keep the pillar, drop the segments that belong to another
   * trade. Removing a whole capability should be rare and deliberate.
   */
  hiddenViews?: string[]
  /**
   * The number that leads the home screen. This is the test of whether a pack
   * is real: if a trade's Meridian opens on the same figure as every other
   * trade's, it is a theme, not a version.
   */
  homeMetric: { label: string; help: string }
  /**
   * The four figures a COUNTER trade opens on.
   *
   * A trade with no book has no bookings to derive a day from, so its
   * headline figures cannot be computed the way a barbershop's are. They live
   * here, beside everything else that is true about the trade, rather than as
   * literals inside the overview component — which is where the takeaway
   * shop's numbers used to sit, invisible to anyone reading the pack.
   *
   * Only set on packs where booksAtAll is false.
   */
  counterStats?: {
    label: string
    /** Money, in US cents. The Canadian demo converts it, exactly as it does
     *  every service price — a pre-formatted "$28.00" string cannot be. */
    cents?: number
    /** Anything that is not money: a count, a percentage, a time. */
    value?: string
    sub?: string
    tone?: 'good' | 'warn'
  }[]
  /**
   * What a COUNTER trade took today, in US cents.
   *
   * The headline is booked revenue, which a trade with no book has none of —
   * so a takeaway shop, a cafe and a smoke shop all opened the demo on a
   * "$0" headline. They take money all day; they just do not take bookings.
   */
  counterTakingsCents?: number
  /**
   * Average spend per cover, for trades where the booking is a table rather
   * than a priced service. A restaurant's revenue is covers x spend; pricing
   * a "Table for 1-4" would be nonsense.
   */
  avgCoverCents?: number

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
      { name: 'Haircut', duration: 30, buffer: 5, min: 1, max: 1, price: 3500 },
      { name: 'Cut and beard', duration: 45, buffer: 5, min: 1, max: 1, price: 5500 },
      { name: 'Skin fade', duration: 45, buffer: 5, min: 1, max: 1, price: 4500 },
    ],
    days: [2, 3, 4, 5, 6],
    opens: '09:00',
    closes: '18:00',
    // Inventory stays ON: a barbershop sells pomade and burns through blades,
    // and margin on the retail shelf is a real number to them. Menu Matrix is
    // a restaurant instrument and goes.
    modules: { camera: false, taxExpenses: false, topActions: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['bookings', 'phone', '', 'inventory', 'schedule'],
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
      { name: 'Gel manicure', duration: 45, buffer: 10, min: 1, max: 1, price: 5500 },
      { name: 'Full set', duration: 90, buffer: 15, min: 1, max: 1, price: 9500 },
      { name: 'Fill', duration: 60, buffer: 10, min: 1, max: 1, price: 6500 },
      { name: 'Lash extensions', duration: 120, buffer: 15, min: 1, max: 1, price: 15000 },
    ],
    days: [1, 2, 3, 4, 5, 6],
    opens: '09:00',
    closes: '19:00',
    // Gel, tips, lash trays — consumable cost per service is the whole margin
    // question in this trade.
    modules: { camera: false, taxExpenses: false, topActions: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['bookings', 'phone', '', 'inventory', 'schedule'],
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
      { name: 'Wash and wax', duration: 90, buffer: 15, min: 1, max: 1, price: 12000 },
      { name: 'Interior and exterior', duration: 120, buffer: 15, min: 1, max: 1, price: 22000 },
      { name: 'Full detail', duration: 240, buffer: 30, min: 1, max: 1, price: 40000 },
      { name: 'Ceramic coating', duration: 480, buffer: 60, min: 1, max: 1, price: 90000 },
    ],
    days: [1, 2, 3, 4, 5, 6],
    opens: '08:00',
    closes: '17:00',
    // Ceramic coating is hundreds of dollars a bottle. A detailer who cannot
    // see product cost against job price is guessing at their own margin.
    modules: { schedule: false, taxExpenses: false, topActions: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['bookings', 'phone', '', 'inventory'],
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
      { name: 'Exterior wash', duration: 60, buffer: 15, min: 1, max: 1, price: 9000 },
      { name: 'Interior and exterior', duration: 120, buffer: 20, min: 1, max: 1, price: 20000 },
      { name: 'Full detail', duration: 240, buffer: 30, min: 1, max: 1, price: 40000 },
    ],
    days: [1, 2, 3, 4, 5, 6],
    opens: '08:00',
    closes: '18:00',
    // Same chemicals as the shop, carried in a van. Margin per job still
    // depends on what went into it.
    modules: { camera: false, schedule: false, taxExpenses: false, topActions: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['', 'bookings', 'phone', 'inventory'],
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
    // Camera earns its place here — front of house, queue length, covers
    // actually seated against covers booked. This is the trade it was built
    // for, and switching it off was the wrong call.
    modules: {},
    pillarOrder: ['bookings', 'phone', '', 'inventory', 'schedule', 'camera'],
    avgCoverCents: 4800,
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
    // Menu Matrix stays: this is exactly the trade it was written for. Camera
    // stays too — counter queue at 7pm is the constraint on the whole evening.
    modules: { bookings: false },
    pillarOrder: ['phone', '', 'inventory', 'camera', 'schedule'],
    homeMetric: { label: 'Orders taken by phone',
                  help: 'Orders the agent took while the line was busy — the ones you would have lost.' },
    counterStats: [
      { label: 'Orders by phone', value: '86', sub: 'taken by the agent' },
      { label: 'Avg ticket', cents: 2800 },
      { label: 'Busiest hour', value: '7pm', sub: '22 orders' },
      { label: 'Missed calls', value: '0', sub: 'nobody hung up', tone: 'good' },
    ],
    counterTakingsCents: 428_000,
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
      { name: 'Consultation', duration: 30, buffer: 10, min: 1, max: 1, price: 0 },
      { name: 'Facial', duration: 60, buffer: 15, min: 1, max: 1, price: 18000 },
      { name: 'Injectables', duration: 45, buffer: 15, min: 1, max: 1, price: 65000 },
      { name: 'Laser session', duration: 90, buffer: 20, min: 1, max: 1, price: 30000 },
    ],
    days: [1, 2, 3, 4, 5],
    opens: '09:00',
    closes: '18:00',
    // Injectables and skincare are the most expensive stock in any of these
    // trades, with expiry dates attached. Inventory is not optional here.
    modules: { camera: false, taxExpenses: false, topActions: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['bookings', 'phone', '', 'inventory', 'schedule'],
    homeMetric: { label: 'Consultations booked this week',
                  help: 'A consultation is the start of a treatment plan, not a single sale.' },
  },
  {
    key: 'coffeeshop',
    label: 'Coffee shop & cafe',
    pitch: 'The morning rush is ninety minutes long and decides the whole day.',
    bookingNoun: 'order',
    customerNoun: 'regular',
    resourceKind: 'table',
    countTitle: '',
    countLabel: '',
    // A cafe does not book a table and never has. Handing it a calendar is
    // the same mistake as handing one to a pizza shop.
    booksAtAll: false,
    defaultCount: 0,
    defaultSeats: 0,
    partyBanded: false,
    services: [],
    days: [0, 1, 2, 3, 4, 5, 6],
    opens: '06:00',
    closes: '16:00',
    // Menu Matrix is the point here — a cafe lives or dies on which drinks
    // carry the margin. Camera stays for the queue at 8am.
    modules: { bookings: false },
    pillarOrder: ['inventory', '', 'schedule', 'phone', 'camera'],
    homeMetric: { label: 'Morning rush takings',
                  help: 'The first four hours are most of the day. Everything else is a tail.' },
    counterStats: [
      { label: 'Drinks sold', value: '412', sub: 'before 11am: 268' },
      { label: 'Avg ticket', cents: 940 },
      { label: 'Morning rush', value: '8am', sub: '96 drinks in the hour' },
      { label: 'Regulars back', value: '38%', sub: 'seen in the last week', tone: 'good' },
    ],
    counterTakingsCents: 387_000,
  },
  {
    key: 'autoshop',
    label: 'Auto repair shop',
    pitch: 'A bay standing empty at 10am is a day you cannot get back.',
    bookingNoun: 'appointment',
    customerNoun: 'customer',
    resourceKind: 'bay',
    countTitle: 'How many bays can take a vehicle at once?',
    countLabel: 'Bays',
    booksAtAll: true,
    defaultCount: 4,
    defaultSeats: 1,
    partyBanded: false,
    // Repair, not detailing: the jobs are diagnostic and mechanical, and the
    // spread from a 30-minute oil change to a 4-hour brake job is the whole
    // scheduling problem.
    services: [
      { name: 'Oil change', duration: 30, buffer: 10, min: 1, max: 1, price: 8900 },
      { name: 'Diagnostic', duration: 60, buffer: 15, min: 1, max: 1, price: 12500 },
      { name: 'Brake service', duration: 150, buffer: 20, min: 1, max: 1, price: 42000 },
      { name: 'Tyre fitting', duration: 45, buffer: 10, min: 1, max: 1, price: 16000 },
    ],
    days: [1, 2, 3, 4, 5, 6],
    opens: '08:00',
    closes: '17:00',
    // Parts are inventory with real margin, so Inventory stays. Menu Matrix
    // is a food screen and goes.
    modules: { taxExpenses: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['bookings', '', 'inventory', 'phone', 'schedule'],
    // Not "bay hours" — that is the DETAILER's headline, and two trades
    // opening on the same figure is the definition of a theme rather than a
    // version. A repair shop counts vehicles through the door; the hours are
    // a tile underneath.
    homeMetric: { label: 'Vehicles through the bays today',
                  help: 'A repair shop is paid per vehicle, and a bay standing empty at 10am is a job that never arrives.' },
  },
  {
    key: 'smokeshop',
    label: 'Smoke & vape shop',
    pitch: 'Margin lives in the case, not at the till.',
    bookingNoun: 'order',
    customerNoun: 'customer',
    resourceKind: 'table',
    countTitle: '',
    countLabel: '',
    // Pure retail. There is nothing to book, and pretending otherwise put an
    // "Appointments" figure on a shop that has never taken one.
    booksAtAll: false,
    defaultCount: 0,
    defaultSeats: 0,
    partyBanded: false,
    services: [],
    days: [0, 1, 2, 3, 4, 5, 6],
    opens: '10:00',
    closes: '21:00',
    // Everything here is an inventory business: stock, margin, dead lines.
    // Menu Matrix is a food screen; the rest of Inventory is the product.
    modules: { bookings: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['inventory', '', 'camera', 'phone', 'schedule'],
    homeMetric: { label: 'Margin taken today',
                  help: 'Two shops can take the same money and keep very different amounts of it.' },
    counterStats: [
      { label: 'Transactions', value: '134' },
      { label: 'Avg basket', cents: 3120 },
      { label: 'Gross margin', value: '46%', sub: 'on today\u2019s mix', tone: 'good' },
      { label: 'Dead stock', value: '7 lines', sub: 'no sale in 30 days', tone: 'warn' },
    ],
    counterTakingsCents: 418_000,
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
  services: [{ name: 'Appointment', duration: 60, buffer: 0, min: 1, max: 1, price: 8000 }],
  days: [1, 2, 3, 4, 5],
  opens: '09:00',
  closes: '17:00',
  // Deliberately empty. Every merchant in production today has no trade set,
  // and they must keep exactly the portal they had this morning.
  modules: {},
  homeMetric: { label: 'Bookings today', help: 'What is on the book for today.' },
}

export const ALL_PACKS = [...NICHE_PACKS, GENERIC_PACK]

/**
 * Names for the same trade that are NOT the pack key.
 *
 * Two vocabularies grew up separately: the demo's BusinessType values
 * ('fast_food', 'mobile_detailing') and these pack keys ('quickservice',
 * 'mobiledetailing'). Rather than rename either — the demo values are already
 * in visitors' localStorage and in saved merchant records — the two are
 * reconciled here.
 *
 * DELIBERATELY AN EXPLICIT TABLE, not fuzzy matching. Unknown text must still
 * fall through to the generic pack, because that fallback is what guarantees
 * every existing merchant sees the portal they saw yesterday.
 */
const PACK_ALIASES: Record<string, string> = {
  fast_food: 'quickservice',
  coffee_shop: 'coffeeshop',
  auto_shop: 'autoshop',
  smoke_shop: 'smokeshop',
  mobile_detailing: 'mobiledetailing',
  auto_detailing: 'detailing',
  med_spa: 'medspa',
  nail_salon: 'nails',
  barber_shop: 'barbershop',
}

export function packFor(key: string | null | undefined): NichePack {
  if (!key) return GENERIC_PACK
  const resolved = PACK_ALIASES[key] || key
  return ALL_PACKS.find((p) => p.key === resolved) || GENERIC_PACK
}
