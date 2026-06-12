/**
 * Canonical catalog of CAD-priced Meridian proposal decks (43 verticals).
 *
 * Used by:
 *  - CanadaPortalProposalsPage (browse / share decks)
 *  - CanadaPortalCreateCustomerPage ("Business type" selector on lead creation)
 *  - CanadaPortalLeadDetailPage ("Proposal for this lead" card)
 *
 * Source of truth — do not duplicate this data elsewhere.
 */

export type CadGroupKey =
  | 'food'
  | 'retail'
  | 'personal'
  | 'fitness'
  | 'health'
  | 'auto'
  | 'hospitality'
  | 'specialty'
  | 'culture'

export interface CadGroupMeta {
  key: CadGroupKey
  label: string
  color: string
}

export interface CadVerticalDeck {
  slug: string
  title: string
  group: CadGroupKey
  blurb: string
  avgTicket: string
  payback: string
}

export const DECK_BASE_URL = 'https://meridian-decks.vercel.app'

export const CAD_GROUPS: Record<CadGroupKey, CadGroupMeta> = {
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

export const CAD_GROUP_ORDER: CadGroupKey[] = [
  'food', 'retail', 'personal', 'fitness', 'health', 'auto', 'hospitality', 'specialty', 'culture',
]

export const CAD_VERTICALS: CadVerticalDeck[] = [
  // Food & Beverage (8)
  { slug: 'ca-bar',          title: 'Bars & Pubs',                   group: 'food', blurb: 'Event-night reservations, mis-staffed Thursdays, tap-data analysis.',           avgTicket: 'C$48',  payback: 'Week 1' },
  { slug: 'ca-bakery',       title: 'Bakeries',                      group: 'food', blurb: 'Catering pre-order calls, production planning, Saturday rush conversion.',      avgTicket: 'C$15',  payback: 'First catering order' },
  { slug: 'ca-brewery',      title: 'Craft Breweries & Tap Rooms',   group: 'food', blurb: 'Private-event bookings, keg rotation forecast, brewery tours.',                  avgTicket: 'C$26',  payback: 'First event booking' },
  { slug: 'ca-coffee',       title: 'Coffee Shops',                  group: 'food', blurb: 'Open-rush staffing, drive-thru pacing, loyalty data.',                          avgTicket: 'C$8.50',payback: 'Open-rush staffed' },
  { slug: 'ca-foodtruck',    title: 'Food Trucks',                   group: 'food', blurb: 'Move to demand, forecast event spikes, capture catering calls.',                avgTicket: 'C$15',  payback: 'First well-routed event' },
  { slug: 'ca-grocery',      title: 'Independent Grocers',           group: 'food', blurb: 'Saturday demand, perishables waste, phone/curbside orders.',                    avgTicket: 'C$68',  payback: 'First waste cycle' },
  { slug: 'ca-icecream',     title: 'Ice Cream & Dessert Shops',     group: 'food', blurb: 'Weather-driven demand, summer peak staffing, catering pre-orders.',             avgTicket: 'C$11',  payback: 'Weekend staffed' },
  { slug: 'ca-qsr',          title: 'Quick-Service Restaurants',     group: 'food', blurb: 'Drive-thru pacing, lunch-rush forecast, direct-order capture.',                 avgTicket: 'C$13',  payback: 'Lunch rush' },
  // Retail (12)
  { slug: 'ca-bookstore',    title: 'Independent Bookstores',        group: 'retail', blurb: 'Special-orders, event/reading forecasting, genre-section conversion.',       avgTicket: 'C$28',  payback: 'First special-order capture' },
  { slug: 'ca-clothing',     title: 'Clothing Boutiques',            group: 'retail', blurb: 'Fitting-room conversion, size mismatch, return-rate analysis.',              avgTicket: 'C$95',  payback: 'Conversion lift' },
  { slug: 'ca-dispensary',   title: 'Cannabis Dispensaries',         group: 'retail', blurb: 'Provincial reporting automation, product-velocity intelligence, 4/20 staffing. Bio-data HARD-DISABLED.', avgTicket: 'C$55',  payback: 'Reporting week 1' },
  { slug: 'ca-electronics',  title: 'Electronics & Appliance',       group: 'retail', blurb: 'High-ticket inquiry capture, attach-rate uplift, delivery scheduling.',      avgTicket: 'C$580', payback: 'Inquiry-to-sale lift' },
  { slug: 'ca-florist',      title: 'Florists',                      group: 'retail', blurb: 'Holiday/event surge, wedding quotes, perishable inventory.',                 avgTicket: 'C$85',  payback: "Valentine's surge" },
  { slug: 'ca-furniture',    title: 'Furniture & Home',              group: 'retail', blurb: 'Delivery quote calls, showroom dwell vs close, financing window.',           avgTicket: 'C$1,400',payback: 'Showroom-to-delivery' },
  { slug: 'ca-gardencentre', title: 'Garden Centres & Nurseries',    group: 'retail', blurb: 'Spring rush (May/June = 60% revenue), consultations, plant inventory waste.',avgTicket: 'C$85',  payback: 'Spring rush' },
  { slug: 'ca-giftshop',     title: 'Gift & Card Shops',             group: 'retail', blurb: 'Seasonal peaks (Mother\'s Day, Valentine\'s), impulse aisle, personalization.', avgTicket: 'C$42', payback: 'Seasonal rush' },
  { slug: 'ca-jewelry',      title: 'Jewelry Stores',                group: 'retail', blurb: 'High-value consultation calls, showcase dwell vs conversion, custom orders.', avgTicket: 'C$650', payback: 'First consultation' },
  { slug: 'ca-liquor',       title: 'Liquor & Convenience',          group: 'retail', blurb: 'Curbside/phone capture (province-aware), hot-runner SKUs, impulse aisle.',    avgTicket: 'C$52',  payback: 'Week 1' },
  { slug: 'ca-pharmacy',     title: 'Independent Pharmacies',        group: 'retail', blurb: 'Pickup peak staffing, OTC upsell timing, lapsed refill recall. NO PHI.',     avgTicket: 'C$45',  payback: 'First refill recall' },
  { slug: 'ca-smokeshop',    title: 'Smoke Shops & Vape Stores',     group: 'retail', blurb: 'Basket-builder conversion, vape coil/pod reorder, province-aware flavour rules.', avgTicket: 'C$24',  payback: 'Week 1' },
  { slug: 'ca-sportinggoods',title: 'Sporting Goods',                group: 'retail', blurb: 'Seasonal sport switches, equipment-fitting bookings, attach-rate.',          avgTicket: 'C$120', payback: 'First season switch' },
  { slug: 'ca-toystore',     title: 'Toy & Hobby Stores',            group: 'retail', blurb: 'Holiday rush (Nov-Dec = 35% revenue), age-aisle conversion, special-orders.',avgTicket: 'C$48',  payback: 'Holiday forecast' },
  // Personal Services (5)
  { slug: 'ca-nailsalon',    title: 'Nail Salons',                   group: 'personal', blurb: 'No-show prediction, booking-call capture, add-on timing.',                 avgTicket: 'C$55',  payback: 'First no-show recovered' },
  { slug: 'ca-salon',        title: 'Salons & Barbershops',          group: 'personal', blurb: 'No-show rate, booking calls, upsell timing.',                              avgTicket: 'C$95',  payback: 'First no-show' },
  { slug: 'ca-spa',          title: 'Day Spas (incl. massage)',      group: 'personal', blurb: 'Package upsell timing, membership churn, multi-service add-on.',           avgTicket: 'C$140', payback: 'First package' },
  { slug: 'ca-tanning',      title: 'Tanning Salons',                group: 'personal', blurb: 'Membership conversion, bed utilization, spring-rush forecast.',            avgTicket: 'C$45',  payback: 'First membership lift' },
  { slug: 'ca-tattoo',       title: 'Tattoo & Piercing Studios',     group: 'personal', blurb: 'Quote-inquiry calls (C$200-1.5K sessions), artist scheduling.',            avgTicket: 'C$280', payback: 'First quote captured' },
  // Fitness & Studios (4)
  { slug: 'ca-gym',          title: 'Gyms & Fitness Studios',        group: 'fitness', blurb: 'Peak-hour forecast, tour-to-member conversion, churn signal.',              avgTicket: 'C$75',  payback: 'First tour conversion' },
  { slug: 'ca-yoga',         title: 'Yoga & Pilates Studios',        group: 'fitness', blurb: 'Class-fill optimization, membership-to-drop-in, churn signal.',             avgTicket: 'C$22',  payback: 'Class-fill lift' },
  { slug: 'ca-dancestudio',  title: 'Dance Studios',                 group: 'fitness', blurb: 'Sep/Jan registration rush, recital upsell, parent communication.',          avgTicket: 'C$120', payback: 'Registration spike' },
  { slug: 'ca-martialarts',  title: 'Martial Arts Dojos',            group: 'fitness', blurb: 'Registration windows, trial-to-member, belt-test upsell.',                  avgTicket: 'C$140', payback: 'Registration spike' },
  // Healthcare (7)
  { slug: 'ca-chiropractic', title: 'Chiropractic Clinics',          group: 'health', blurb: 'New-patient inquiry, no-show rate, lapsed care plan. NO PHI.',               avgTicket: 'C$95',  payback: 'First recall' },
  { slug: 'ca-dental',       title: 'Dental Clinics',                group: 'health', blurb: 'Chair utilization, new-patient inquiry, lapsed recall. NO PHI.',             avgTicket: 'C$180', payback: 'First lapsed recall' },
  { slug: 'ca-mentalhealth', title: 'Mental Health Practices',       group: 'health', blurb: 'Intake calls, cancel chain, wait-list. NO PHI · cameras OFF by default.',   avgTicket: 'C$170', payback: 'First intake captured' },
  { slug: 'ca-optometry',    title: 'Optometry Practices',           group: 'health', blurb: '24-month recall window, eyewear upsell timing. NO PHI · NO Rx.',             avgTicket: 'C$200', payback: 'First recall' },
  { slug: 'ca-physio',       title: 'Physiotherapy Clinics',         group: 'health', blurb: 'New-patient calls, cancellation chain, treatment-plan completion. NO PHI.',  avgTicket: 'C$95',  payback: 'First plan completed' },
  { slug: 'ca-vetclinic',    title: 'Veterinary Clinics',            group: 'health', blurb: 'New-patient inquiry, lapsed annual recall, exam-room utilization. NO PHI.',  avgTicket: 'C$240', payback: 'First new-patient call' },
  { slug: 'ca-walkinclinic', title: 'Walk-In & Family Medicine',     group: 'health', blurb: 'Waiting-room throughput, peak-hour staffing, private-pay vs OHIP mix. NO PHI.', avgTicket: 'C$50', payback: 'Wait-time fix' },
  // Auto Services (2)
  { slug: 'ca-carwash',      title: 'Car Washes',                    group: 'auto', blurb: 'Post-storm surge staffing, membership conversion, loyalty value.',              avgTicket: 'C$22',  payback: 'First weekend rush' },
  { slug: 'ca-detailing',    title: 'Auto Detailing Shops',          group: 'auto', blurb: 'Quote calls, bay utilization, mobile vs in-shop mix.',                          avgTicket: 'C$260', payback: 'First bay scheduled' },
  // Hospitality (2)
  { slug: 'ca-hotel',        title: 'Hotels, Motels & B&Bs',         group: 'hospitality', blurb: 'Direct booking capture (skip OTA fees), occupancy forecast, ancillary.', avgTicket: 'C$185', payback: 'First direct booking' },
  { slug: 'ca-vacationrental', title: 'Vacation Rentals (STR)',      group: 'hospitality', blurb: 'OTA commission burn, cleaning turnover, dynamic pricing.',               avgTicket: 'C$180', payback: 'First direct booking' },
  // Specialty (2)
  { slug: 'ca-drycleaner',   title: 'Dry Cleaners & Alterations',    group: 'specialty', blurb: 'Pickup/drop-off scheduling, abandoned garments, corporate accounts.',     avgTicket: 'C$28',  payback: 'First recall' },
  { slug: 'ca-printshop',    title: 'Print Shops',                   group: 'specialty', blurb: 'Rush-quote calls, repeat-corporate workflow, press utilization.',          avgTicket: 'C$220', payback: 'First rush job' },
  // Culture (1)
  { slug: 'ca-artgallery',   title: 'Art Galleries',                 group: 'culture', blurb: 'High-value collector inquiry, exhibition conversion, consignment workflow.', avgTicket: 'C$1,800',payback: 'First collector inquiry' },
]

/** Lookup by slug — used by lead detail to find the deck for `lead.vertical`. */
export function findVerticalBySlug(slug: string | null | undefined): CadVerticalDeck | undefined {
  if (!slug) return undefined
  return CAD_VERTICALS.find(v => v.slug === slug)
}

/**
 * Lookup that also tolerates legacy free-text vertical labels stored on older leads
 * (e.g. "Restaurant", "Bar", "Salon", "Smoke Shop", "Convenience Store", "Café").
 * Returns undefined if no reasonable match is found — caller should prompt the rep
 * to tag the lead with a canonical business_type.
 */
export function findVerticalByValue(value: string | null | undefined): CadVerticalDeck | undefined {
  if (!value) return undefined
  const exact = findVerticalBySlug(value)
  if (exact) return exact
  const v = value.trim().toLowerCase()
  const legacy: Record<string, string> = {
    'restaurant':         'ca-qsr',
    'cafe':               'ca-coffee',
    'café':               'ca-coffee',
    'bar':                'ca-bar',
    'smoke shop':         'ca-smokeshop',
    'vape':               'ca-smokeshop',
    'vape store':         'ca-smokeshop',
    'tobacconist':        'ca-smokeshop',
    'dispensary':         'ca-dispensary',
    'cannabis':           'ca-dispensary',
    'cannabis retail':    'ca-dispensary',
    'boutique':           'ca-clothing',
    'salon':              'ca-salon',
    'food truck':         'ca-foodtruck',
    'convenience store':  'ca-liquor',
  }
  const mapped = legacy[v]
  return mapped ? findVerticalBySlug(mapped) : undefined
}

/** Group verticals into [groupMeta, verticals[]] tuples in canonical order. */
export function verticalsByGroup(): Array<{ group: CadGroupMeta; items: CadVerticalDeck[] }> {
  return CAD_GROUP_ORDER.map(key => ({
    group: CAD_GROUPS[key],
    items: CAD_VERTICALS.filter(v => v.group === key),
  }))
}

/**
 * Build a personalized deck URL for sharing with a prospect.
 * Includes the rep's name/email/phone and the prospect's business name.
 *
 * When `pricing` is supplied, the deck overrides its hardcoded headline price
 * (and ROI-calculator monthly rate) with the figure the rep quoted on this
 * lead — so the proposal the prospect opens matches the number in the portal.
 */
export function buildPersonalizedDeckUrl(
  slug: string,
  rep?: { name?: string | null; email?: string | null; phone?: string | null } | null,
  businessName?: string | null,
  pricing?: { monthly?: number | null; setup?: number | null; currency?: 'CAD' | 'USD'; firstMonthFree?: boolean | null } | null,
): string {
  const params = new URLSearchParams()
  if (rep?.name) params.set('rep', rep.name)
  if (rep?.email) params.set('email', rep.email)
  if (rep?.phone) params.set('phone', rep.phone)
  if (businessName) params.set('business', businessName)
  if (pricing?.monthly && pricing.monthly > 0) params.set('price', String(Math.round(pricing.monthly)))
  if (pricing?.setup && pricing.setup > 0) params.set('setup', String(Math.round(pricing.setup)))
  if (pricing?.currency) params.set('currency', pricing.currency)
  if (pricing?.firstMonthFree) params.set('freemonth', '1')
  const q = params.toString()
  return `${DECK_BASE_URL}/${slug}${q ? `?${q}` : ''}`
}
