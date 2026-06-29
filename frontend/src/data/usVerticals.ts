/**
 * Canonical catalog of USD-priced Meridian proposal decks (43 verticals).
 *
 * Used by:
 *  - USPortalProposalsPage (browse / share decks)
 *
 * US source of truth — do not duplicate this data elsewhere. Kept independent of
 * the Canada catalog so US copy stays free of CAD / province / Canada-specific
 * strings.
 *
 * Deck `slug`s reference the shared, industry-specific deck pages hosted on
 * meridian-decks. Those pages are country-neutral in content (a bar is a bar)
 * and render USD pricing client-side when the share URL carries `currency=USD`
 * + `price` — see `buildUsDeckUrl` below.
 */

export type UsGroupKey =
  | 'food'
  | 'retail'
  | 'personal'
  | 'fitness'
  | 'health'
  | 'auto'
  | 'hospitality'
  | 'specialty'
  | 'culture'

export interface UsGroupMeta {
  key: UsGroupKey
  label: string
  color: string
}

export interface UsVerticalDeck {
  slug: string
  title: string
  group: UsGroupKey
  blurb: string
  avgTicket: string
  payback: string
}

export const US_DECK_BASE_URL = 'https://meridian-decks.vercel.app'

export const US_GROUPS: Record<UsGroupKey, UsGroupMeta> = {
  food:        { key: 'food',        label: 'Food & Beverage',   color: '#FBBF24' },
  retail:      { key: 'retail',      label: 'Retail',            color: '#5FE7D2' },
  personal:    { key: 'personal',    label: 'Personal Services', color: '#FB7185' },
  fitness:     { key: 'fitness',     label: 'Fitness & Studio',  color: '#A3E635' },
  health:      { key: 'health',      label: 'Healthcare',        color: '#34D399' },
  auto:        { key: 'auto',        label: 'Auto Services',     color: '#818CF8' },
  hospitality: { key: 'hospitality', label: 'Hospitality',       color: '#38BDF8' },
  specialty:   { key: 'specialty',   label: 'Specialty',         color: '#FCD34D' },
  culture:     { key: 'culture',     label: 'Culture',           color: '#D8B4FE' },
}

export const US_GROUP_ORDER: UsGroupKey[] = [
  'food', 'retail', 'personal', 'fitness', 'health', 'auto', 'hospitality', 'specialty', 'culture',
]

export const US_VERTICALS: UsVerticalDeck[] = [
  // Food & Beverage (8)
  { slug: 'us-bar',          title: 'Bars & Pubs',                   group: 'food', blurb: 'Event-night reservations, mis-staffed Thursdays, tap-data analysis.',           avgTicket: '$48',   payback: 'Week 1' },
  { slug: 'ca-bakery',       title: 'Bakeries',                      group: 'food', blurb: 'Catering pre-order calls, production planning, Saturday rush conversion.',      avgTicket: '$15',   payback: 'First catering order' },
  { slug: 'ca-brewery',      title: 'Craft Breweries & Tap Rooms',   group: 'food', blurb: 'Private-event bookings, keg rotation forecast, brewery tours.',                  avgTicket: '$26',   payback: 'First event booking' },
  { slug: 'us-coffee',       title: 'Coffee Shops',                  group: 'food', blurb: 'Open-rush staffing, drive-thru pacing, loyalty data.',                          avgTicket: '$8.50', payback: 'Open-rush staffed' },
  { slug: 'ca-foodtruck',    title: 'Food Trucks',                   group: 'food', blurb: 'Move to demand, forecast event spikes, capture catering calls.',                avgTicket: '$15',   payback: 'First well-routed event' },
  { slug: 'ca-grocery',      title: 'Independent Grocers',           group: 'food', blurb: 'Saturday demand, perishables waste, phone/curbside orders.',                    avgTicket: '$68',   payback: 'First waste cycle' },
  { slug: 'ca-icecream',     title: 'Ice Cream & Dessert Shops',     group: 'food', blurb: 'Weather-driven demand, summer peak staffing, catering pre-orders.',             avgTicket: '$11',   payback: 'Weekend staffed' },
  { slug: 'us-qsr',          title: 'Quick-Service Restaurants',     group: 'food', blurb: 'Drive-thru pacing, lunch-rush forecast, direct-order capture.',                 avgTicket: '$13',   payback: 'Lunch rush' },
  // Retail (12)
  { slug: 'ca-bookstore',    title: 'Independent Bookstores',        group: 'retail', blurb: 'Special-orders, event/reading forecasting, genre-section conversion.',       avgTicket: '$28',   payback: 'First special-order capture' },
  { slug: 'us-clothing',     title: 'Clothing Boutiques',            group: 'retail', blurb: 'Fitting-room conversion, size mismatch, return-rate analysis.',              avgTicket: '$95',   payback: 'Conversion lift' },
  { slug: 'us-dispensary',   title: 'Cannabis Dispensaries',         group: 'retail', blurb: 'State reporting automation, product-velocity intelligence, 4/20 staffing. Bio-data HARD-DISABLED.', avgTicket: '$55',   payback: 'Reporting week 1' },
  { slug: 'ca-electronics',  title: 'Electronics & Appliance',       group: 'retail', blurb: 'High-ticket inquiry capture, attach-rate uplift, delivery scheduling.',      avgTicket: '$580',  payback: 'Inquiry-to-sale lift' },
  { slug: 'ca-florist',      title: 'Florists',                      group: 'retail', blurb: 'Holiday/event surge, wedding quotes, perishable inventory.',                 avgTicket: '$85',   payback: "Valentine's surge" },
  { slug: 'ca-furniture',    title: 'Furniture & Home',              group: 'retail', blurb: 'Delivery quote calls, showroom dwell vs close, financing window.',           avgTicket: '$1,400', payback: 'Showroom-to-delivery' },
  { slug: 'ca-gardencentre', title: 'Garden Centers & Nurseries',    group: 'retail', blurb: 'Spring rush (May/June = 60% revenue), consultations, plant inventory waste.', avgTicket: '$85',   payback: 'Spring rush' },
  { slug: 'ca-giftshop',     title: 'Gift & Card Shops',             group: 'retail', blurb: "Seasonal peaks (Mother's Day, Valentine's), impulse aisle, personalization.", avgTicket: '$42',   payback: 'Seasonal rush' },
  { slug: 'ca-jewelry',      title: 'Jewelry Stores',                group: 'retail', blurb: 'High-value consultation calls, showcase dwell vs conversion, custom orders.', avgTicket: '$650',  payback: 'First consultation' },
  { slug: 'ca-liquor',       title: 'Liquor & Convenience',          group: 'retail', blurb: 'Curbside/phone capture, hot-runner SKUs, impulse aisle.',                    avgTicket: '$52',   payback: 'Week 1' },
  { slug: 'ca-pharmacy',     title: 'Independent Pharmacies',        group: 'retail', blurb: 'Pickup peak staffing, OTC upsell timing, lapsed refill recall. NO PHI.',     avgTicket: '$45',   payback: 'First refill recall' },
  { slug: 'ca-smokeshop',    title: 'Smoke Shops & Vape Stores',     group: 'retail', blurb: 'Basket-builder conversion, vape coil/pod reorder, state-aware flavor rules.', avgTicket: '$24',   payback: 'Week 1' },
  { slug: 'ca-sportinggoods',title: 'Sporting Goods',                group: 'retail', blurb: 'Seasonal sport switches, equipment-fitting bookings, attach-rate.',          avgTicket: '$120',  payback: 'First season switch' },
  { slug: 'ca-toystore',     title: 'Toy & Hobby Stores',            group: 'retail', blurb: 'Holiday rush (Nov-Dec = 35% revenue), age-aisle conversion, special-orders.', avgTicket: '$48',   payback: 'Holiday forecast' },
  // Personal Services (5)
  { slug: 'ca-nailsalon',    title: 'Nail Salons',                   group: 'personal', blurb: 'No-show prediction, booking-call capture, add-on timing.',                 avgTicket: '$55',   payback: 'First no-show recovered' },
  { slug: 'ca-salon',        title: 'Salons & Barbershops',          group: 'personal', blurb: 'No-show rate, booking calls, upsell timing.',                              avgTicket: '$95',   payback: 'First no-show' },
  { slug: 'ca-spa',          title: 'Day Spas (incl. massage)',      group: 'personal', blurb: 'Package upsell timing, membership churn, multi-service add-on.',           avgTicket: '$140',  payback: 'First package' },
  { slug: 'ca-tanning',      title: 'Tanning Salons',                group: 'personal', blurb: 'Membership conversion, bed utilization, spring-rush forecast.',            avgTicket: '$45',   payback: 'First membership lift' },
  { slug: 'ca-tattoo',       title: 'Tattoo & Piercing Studios',     group: 'personal', blurb: 'Quote-inquiry calls ($200-1.5K sessions), artist scheduling.',             avgTicket: '$280',  payback: 'First quote captured' },
  // Fitness & Studios (4)
  { slug: 'ca-gym',          title: 'Gyms & Fitness Studios',        group: 'fitness', blurb: 'Peak-hour forecast, tour-to-member conversion, churn signal.',              avgTicket: '$75',   payback: 'First tour conversion' },
  { slug: 'ca-yoga',         title: 'Yoga & Pilates Studios',        group: 'fitness', blurb: 'Class-fill optimization, membership-to-drop-in, churn signal.',             avgTicket: '$22',   payback: 'Class-fill lift' },
  { slug: 'ca-dancestudio',  title: 'Dance Studios',                 group: 'fitness', blurb: 'Sep/Jan registration rush, recital upsell, parent communication.',          avgTicket: '$120',  payback: 'Registration spike' },
  { slug: 'ca-martialarts',  title: 'Martial Arts Dojos',            group: 'fitness', blurb: 'Registration windows, trial-to-member, belt-test upsell.',                  avgTicket: '$140',  payback: 'Registration spike' },
  // Healthcare (7)
  { slug: 'ca-chiropractic', title: 'Chiropractic Clinics',          group: 'health', blurb: 'New-patient inquiry, no-show rate, lapsed care plan. NO PHI.',               avgTicket: '$95',   payback: 'First recall' },
  { slug: 'ca-dental',       title: 'Dental Clinics',                group: 'health', blurb: 'Chair utilization, new-patient inquiry, lapsed recall. NO PHI.',             avgTicket: '$180',  payback: 'First lapsed recall' },
  { slug: 'ca-mentalhealth', title: 'Mental Health Practices',       group: 'health', blurb: 'Intake calls, cancel chain, wait-list. NO PHI · cameras OFF by default.',   avgTicket: '$170',  payback: 'First intake captured' },
  { slug: 'ca-optometry',    title: 'Optometry Practices',           group: 'health', blurb: '24-month recall window, eyewear upsell timing. NO PHI · NO Rx.',             avgTicket: '$200',  payback: 'First recall' },
  { slug: 'ca-physio',       title: 'Physical Therapy Clinics',      group: 'health', blurb: 'New-patient calls, cancellation chain, treatment-plan completion. NO PHI.',  avgTicket: '$95',   payback: 'First plan completed' },
  { slug: 'ca-vetclinic',    title: 'Veterinary Clinics',            group: 'health', blurb: 'New-patient inquiry, lapsed annual recall, exam-room utilization. NO PHI.',  avgTicket: '$240',  payback: 'First new-patient call' },
  { slug: 'ca-walkinclinic', title: 'Urgent Care & Family Medicine', group: 'health', blurb: 'Waiting-room throughput, peak-hour staffing, self-pay vs insured mix. NO PHI.', avgTicket: '$50', payback: 'Wait-time fix' },
  // Auto Services (2)
  { slug: 'ca-carwash',      title: 'Car Washes',                    group: 'auto', blurb: 'Post-storm surge staffing, membership conversion, loyalty value.',              avgTicket: '$22',   payback: 'First weekend rush' },
  { slug: 'ca-detailing',    title: 'Auto Detailing Shops',          group: 'auto', blurb: 'Quote calls, bay utilization, mobile vs in-shop mix.',                          avgTicket: '$260',  payback: 'First bay scheduled' },
  // Hospitality (2)
  { slug: 'ca-hotel',        title: 'Hotels, Motels & B&Bs',         group: 'hospitality', blurb: 'Direct booking capture (skip OTA fees), occupancy forecast, ancillary.', avgTicket: '$185',  payback: 'First direct booking' },
  { slug: 'ca-vacationrental', title: 'Vacation Rentals (STR)',      group: 'hospitality', blurb: 'OTA commission burn, cleaning turnover, dynamic pricing.',               avgTicket: '$180',  payback: 'First direct booking' },
  // Specialty (2)
  { slug: 'ca-drycleaner',   title: 'Dry Cleaners & Alterations',    group: 'specialty', blurb: 'Pickup/drop-off scheduling, abandoned garments, corporate accounts.',     avgTicket: '$28',   payback: 'First recall' },
  { slug: 'ca-printshop',    title: 'Print Shops',                   group: 'specialty', blurb: 'Rush-quote calls, repeat-corporate workflow, press utilization.',          avgTicket: '$220',  payback: 'First rush job' },
  // Culture (1)
  { slug: 'ca-artgallery',   title: 'Art Galleries',                 group: 'culture', blurb: 'High-value collector inquiry, exhibition conversion, consignment workflow.', avgTicket: '$1,800', payback: 'First collector inquiry' },
]

/**
 * Build a personalized, USD-rendered deck URL for sharing with a US prospect.
 *
 * Carries the rep's name/email/phone so the deck cover reads "Prepared by …" and
 * routes CTAs back to the rep. `currency=USD` + a `price` are both required for
 * the deck to swap its native symbol/number to USD — the deck ignores currency
 * unless a positive price accompanies it.
 */
export function buildUsDeckUrl(
  slug: string,
  rep?: { name?: string | null; email?: string | null; phone?: string | null } | null,
  monthly?: number | null,
): string {
  const params = new URLSearchParams()
  if (rep?.name) params.set('rep', rep.name)
  if (rep?.email) params.set('email', rep.email)
  if (rep?.phone) params.set('phone', rep.phone)
  if (monthly && monthly > 0) {
    params.set('currency', 'USD')
    params.set('price', String(Math.round(monthly)))
  }
  const q = params.toString()
  return `${US_DECK_BASE_URL}/${slug}${q ? `?${q}` : ''}`
}
