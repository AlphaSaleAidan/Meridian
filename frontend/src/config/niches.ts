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

  /**
   * True for trades where the operator sends the customer the bill — a
   * "Send payment link" action on each booking, riding the same rail phone
   * orders settle through. A trade with a till does not need it; a trade
   * standing in a driveway with wet hands does. Data, not a screen: turning
   * it on for another trade is one line here.
   */
  paymentLinks?: boolean
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
    // Camera stays ON now that it records EVENTS rather than only counting
    // heads. A spill by the basin, product leaving the retail shelf without
    // a sale, a front desk empty while somebody waits to pay — all three
    // happen here, and none of them were worth a camera when the pillar
    // could only report footfall.
    modules: { taxExpenses: false, topActions: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['bookings', 'phone', '', 'inventory', 'schedule'],
    homeMetric: { label: 'Chair hours filled today',
                  help: 'Booked minutes against the hours your chairs are open.' },
    // Card-on-file culture without the card machine contract: the cut ends,
    // the client gets the bill by text while they check the mirror.
    paymentLinks: true,
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
    // Camera stays ON now that it records EVENTS rather than only counting
    // heads. A spill by the basin, product leaving the retail shelf without
    // a sale, a front desk empty while somebody waits to pay — all three
    // happen here, and none of them were worth a camera when the pillar
    // could only report footfall.
    modules: { taxExpenses: false, topActions: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['bookings', 'phone', '', 'inventory', 'schedule'],
    homeMetric: { label: 'Clients rebooked before they left',
                  help: 'The cheapest appointment you will ever sell is the next one.' },
    // Wet nails cannot open a purse. Pay-by-text is the trade's native rail.
    paymentLinks: true,
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
    // Big tickets, and the customer is rarely standing there when the job
    // finishes — the bill goes to wherever they are.
    paymentLinks: true,
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
    // The whole trade is paid in a driveway. "I'll Venmo you?" is the
    // competitor this button removes.
    paymentLinks: true,
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
    label: 'Quick service & takeaway',
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
    key: 'pizzeria',
    label: 'Pizza shop',
    pitch: 'Every delivery on one screen, and nobody waits on hold at 6pm on a Friday.',
    bookingNoun: 'delivery',
    customerNoun: 'customer',
    resourceKind: 'staff',
    countTitle: 'How many drivers are out at once?',
    countLabel: 'Drivers',
    // A DELIVERY IS A BOOKING. Not a reservation — nobody rings a pizza shop
    // for a table — but a drop has a time, an address and a driver, which is
    // the same record with the same double-booking guarantee behind it. That
    // is what makes the map work on real data rather than only in the demo:
    // without it a live shop has no stops to draw.
    booksAtAll: true,
    travels: true,
    defaultCount: 3,
    defaultSeats: 1,
    partyBanded: false,
    services: [
      { name: 'Delivery', duration: 30, buffer: 5, min: 1, max: 1, price: 3200 },
      { name: 'Large pizza', duration: 20, buffer: 5, min: 1, max: 1, price: 2400 },
      { name: 'Family deal', duration: 25, buffer: 5, min: 1, max: 1, price: 4500 },
    ],
    days: [0, 1, 2, 3, 4, 5, 6],
    opens: '11:00',
    closes: '23:00',
    // Menu Matrix is exactly the screen this trade was written for, and the
    // camera watches the counter queue at 7pm — the constraint on the whole
    // evening. Bookings stays ON: it is the delivery board.
    modules: {},
    pillarOrder: ['', 'bookings', 'phone', 'inventory', 'camera', 'schedule'],
    homeMetric: { label: 'Deliveries on the road',
                  help: 'Where every driver is, and which drop is about to be late.' },
    avgCoverCents: 2600,
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
    // Camera stays ON now that it records EVENTS rather than only counting
    // heads. A spill by the basin, product leaving the retail shelf without
    // a sale, a front desk empty while somebody waits to pay — all three
    // happen here, and none of them were worth a camera when the pillar
    // could only report footfall.
    modules: { taxExpenses: false, topActions: false },
    hiddenViews: ['inventory/menu'],
    pillarOrder: ['bookings', 'phone', '', 'inventory', 'schedule'],
    homeMetric: { label: 'Consultations booked this week',
                  help: 'A consultation is the start of a treatment plan, not a single sale.' },
    // The highest tickets of any trade here, already sold on a deposits
    // culture — the balance goes by text the moment the treatment ends.
    paymentLinks: true,
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
    // "Your car is ready" and the bill travel in the same text — the customer
    // pays before they drive over, and pickup is keys, not a queue.
    paymentLinks: true,
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
/**
 * The deck slug a rep sells each pack under, per market.
 *
 * THIS IS THE JOIN THAT WAS MISSING. Three different vocabularies write
 * `business_type` on an organization and none of them agreed:
 *
 *   1. The rep portals write a DECK SLUG — `ca-salon`, `us-detailing` —
 *      because the field doubles as which proposal deck to render.
 *   2. Square POS detection writes a BusinessType — `coffee_shop`,
 *      `auto_shop` — from the merchant's MCC or its name.
 *   3. Both fall back to the literal string "restaurant" when unset.
 *
 * packFor() matched pack keys and none of the above, so every account a rep
 * created resolved to the generic pack: the merchant paid for a trade version
 * and got the untailored portal. Silently, because the fallback is by design
 * a working portal rather than an error.
 *
 * One table, read by packFor, closes it. Both markets map to the same pack —
 * a Canadian barbershop and an American one are the same product.
 */
export const PACK_DECK_SLUGS: Record<string, string[]> = {
  barbershop: ['ca-salon', 'us-salon'],
  nails: ['ca-nailsalon', 'us-nailsalon'],
  medspa: ['ca-spa', 'us-spa'],
  detailing: ['ca-detailing', 'us-detailing', 'ca-carwash', 'us-carwash'],
  quickservice: ['ca-qsr', 'us-qsr'],
  coffeeshop: ['ca-coffee', 'us-coffee'],
  smokeshop: ['ca-smokeshop', 'us-smokeshop'],
  // No deck exists for these yet: the catalogues have no restaurant, auto
  // repair or mobile-detailing entry in either market. They are sellable
  // products with no proposal behind them, which is a gap to close rather
  // than a mapping to invent.
  restaurant: [],
  autoshop: [],
  mobiledetailing: [],
}

/**
 * What a rep can actually sell, in the order the picker shows it.
 *
 * THE PICKER NOW SELECTS A PACK, not a deck. `business_type` stores the pack
 * key directly, so the thing the rep chose and the thing the portal renders
 * are literally the same string — no round trip through a slug that only
 * existed because the field doubled as "which proposal to open".
 *
 * The deck is a property OF the trade rather than its identity, which is what
 * lets mobile detailing be its own product while sharing the detailing deck —
 * that deck's audience line already reads "detailing shop owner or MOBILE
 * detailer". Legacy accounts that stored a slug still resolve through
 * PACK_DECK_SLUGS below, so nothing already sold changes shape.
 *
 * Anything not in this list is not sellable. Thirty-five verticals in each
 * catalogue have a deck and no product version behind them; a rep closing one
 * of those sells a tailored portal that does not exist.
 */
export interface SellableTrade {
  /** Pack key. Stored verbatim as organizations.business_type. */
  key: string
  label: string
  group: 'Food and drink' | 'Appointments' | 'Vehicles' | 'Retail'
  /** Deck slug per market. Some decks are market-neutral and share one. */
  deck: { ca: string; us: string }
}

export const SELLABLE_TRADES: SellableTrade[] = [
  { key: 'restaurant', label: 'Restaurants', group: 'Food and drink',
    // Market-neutral slug: this deck predates the ca-/us- split and is live
    // under the bare name in both markets.
    deck: { ca: 'restaurant', us: 'restaurant' } },
  { key: 'quickservice', label: 'Quick Service & Takeaway', group: 'Food and drink',
    deck: { ca: 'ca-qsr', us: 'us-qsr' } },
  { key: 'pizzeria', label: 'Pizza Shops', group: 'Food and drink',
    // Shares the quick-service deck, which is written for exactly this shop.
    deck: { ca: 'ca-qsr', us: 'us-qsr' } },
  { key: 'coffeeshop', label: 'Coffee Shops & Cafes', group: 'Food and drink',
    deck: { ca: 'ca-coffee', us: 'us-coffee' } },

  { key: 'barbershop', label: 'Barbershops & Salons', group: 'Appointments',
    deck: { ca: 'ca-salon', us: 'us-salon' } },
  { key: 'nails', label: 'Nail & Lash Studios', group: 'Appointments',
    deck: { ca: 'ca-nailsalon', us: 'us-nailsalon' } },
  { key: 'medspa', label: 'Med Spas & Day Spas', group: 'Appointments',
    deck: { ca: 'ca-spa', us: 'us-spa' } },

  { key: 'detailing', label: 'Auto Detailing (shop)', group: 'Vehicles',
    deck: { ca: 'ca-detailing', us: 'us-detailing' } },
  { key: 'mobiledetailing', label: 'Mobile Detailing (van)', group: 'Vehicles',
    // Shares the detailing deck, which is written for both — its audience
    // line names mobile detailers explicitly. A separate product, not a
    // separate proposal.
    deck: { ca: 'ca-detailing', us: 'us-detailing' } },
  { key: 'autoshop', label: 'Auto Repair Shops', group: 'Vehicles',
    deck: { ca: 'autoshop', us: 'autoshop' } },

  { key: 'smokeshop', label: 'Smoke & Vape Shops', group: 'Retail',
    deck: { ca: 'ca-smokeshop', us: 'us-smokeshop' } },
]

export const SELLABLE_GROUPS = [
  'Food and drink', 'Appointments', 'Vehicles', 'Retail',
] as const

/** The deck a rep should link for this trade in this market. */
export function deckSlugFor(tradeKey: string, market: 'ca' | 'us'): string | null {
  return SELLABLE_TRADES.find((t) => t.key === tradeKey)?.deck[market] ?? null
}

/** Deck slug → pack key, derived so the two can never drift apart. */
const SLUG_TO_PACK: Record<string, string> = Object.fromEntries(
  Object.entries(PACK_DECK_SLUGS).flatMap(([pack, slugs]) => slugs.map((s) => [s, pack])),
)

const PACK_ALIASES: Record<string, string> = {
  fast_food: 'quickservice',
  pizza: 'pizzeria',
  pizza_shop: 'pizzeria',
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
  // CASE-INSENSITIVE, because live data is not consistent: organizations hold
  // both "restaurant" and "Restaurant" today, written by different paths over
  // two years. Matching exactly gave two identical businesses two different
  // portals, which is a worse outcome than either portal.
  const norm = key.trim().toLowerCase()
  const resolved = SLUG_TO_PACK[norm] || PACK_ALIASES[norm] || norm
  return ALL_PACKS.find((p) => p.key === resolved) || GENERIC_PACK
}
