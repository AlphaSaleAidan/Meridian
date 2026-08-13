/**
 * Meridian plan tiers — single source of truth for pricing and features.
 *
 * Three tiers (USD). Every tier includes all Meridian features; the axis is
 * the AI phone agent and the per-order service fee:
 *   Standard $250 — everything except the phone agent, no per-order fee
 *   Premium  $350 — phone agent included, $0.65 service fee per order
 *   Command  $500 — phone agent included, $0.45 service fee per order
 *
 * 2026-08-06 (Aidan): per-order fees adjusted DOWN to the former redlines and
 * FIXED — the rep fee slider is retired, so orderFee === orderFeeFloor.
 *
 * Reps may add up to REP_PRICE_HEADROOM on top of any tier via the price
 * slider — the base prices above are floors, never discounted.
 */

export interface PlanTier {
  id: 'standard' | 'premium' | 'command'
  label: string
  price: number
  interval?: 'month' | 'week'
  tag?: string
  features: string[]
  /** AI phone agent included in this tier. */
  phoneAgent: boolean
  /** Per-order service fee in the plan's currency (0 = no per-order fee). */
  orderFee: number
  /** Server-side floor for the per-order fee. The fee slider is retired
   *  (Aidan 2026-08-06) — the tier rate IS the floor; the backend still
   *  clamps any client-sent fee to it. */
  orderFeeFloor: number
}

/** Max amount (in the plan's currency) a rep can add on top of a tier's base price. */
export const REP_PRICE_HEADROOM = 100

/** Voice-call terms. Call time is NOT billed — the overage was retired
 *  2026-08-07 (Aidan) in favour of the hard cap below: a call simply ends at
 *  VOICE_MAX_CALL_MINUTES rather than running up a per-minute charge. Mirrors
 *  the live backend dials (GET /api/phone/fees); shown wherever pricing is. */
export const VOICE_INCLUDED_MINUTES = 3
/** 0 = call time is not billed. Kept so the SLA/proposal surfaces can render a
 *  rate if a bespoke per-merchant deal ever reinstates one. */
export const VOICE_OVERAGE_PER_MIN = 0
/** Hard cap — Vapi force-ends every call at this length. */
export const VOICE_MAX_CALL_MINUTES = 5

/** "$0 per order" minutes plan — the alternative fee model a rep can pick at
 *  close (Aidan 2026-08-09/10). THE MONTHLY DOES NOT CHANGE: the merchant
 *  pays the same tier retail as a per-order deal; the deal simply swaps the
 *  per-order fee for a monthly bucket of AI-call minutes (overage per minute
 *  past it). Wholesale numbers (what a partner org is charged on the backend)
 *  never appear here. Overage is a flat $0.20/min in BOTH markets (Aidan
 *  2026-08-10, not FX-derived); the wholesale card's overage matches since
 *  the same date.
 *  Mirrors backend fee_terms.ZERO_PER_ORDER_TERMS — keep in sync. Standard
 *  has no phone agent, so it has no card (the option simply doesn't render). */
export interface ZeroPerOrderCard {
  includedMinutes: number
  overagePerMin: number
}

export const ZERO_PER_ORDER_CARDS: Partial<Record<PlanTier['id'], ZeroPerOrderCard>> = {
  premium: { includedMinutes: 600, overagePerMin: 0.2 },
  command: { includedMinutes: 1000, overagePerMin: 0.2 },
}

export const PLAN_TIERS: PlanTier[] = [
  {
    id: 'standard',
    label: 'Standard',
    price: 250,
    interval: 'month',
    phoneAgent: false,
    orderFee: 0,
    orderFeeFloor: 0,
    features: [
      'POS analytics dashboard',
      'Revenue + product insights',
      'Predictive engine (churn, demand)',
      'Menu engineering AI',
      'Camera intelligence',
      'Email alerts + priority support',
    ],
  },
  {
    id: 'premium',
    label: 'Premium',
    price: 350,
    interval: 'month',
    tag: 'MOST POPULAR',
    phoneAgent: true,
    orderFee: 0.65,
    orderFeeFloor: 0.65,
    features: [
      'Everything in Standard',
      'AI phone agent — answers calls + takes orders',
      'Pay-by-text checkout',
      '$0.65 per-order transaction fee',
      'Calls: no per-minute charge (calls are capped at 5 min)',
    ],
  },
  {
    id: 'command',
    label: 'Command',
    price: 500,
    interval: 'month',
    phoneAgent: true,
    orderFee: 0.45,
    orderFeeFloor: 0.45,
    features: [
      'Everything in Premium',
      'Lowest per-order rate — $0.45 service fee per order',
      'Calls: no per-minute charge (calls are capped at 5 min)',
      'Multi-location support',
      'Dedicated account manager',
    ],
  },
]

/**
 * Website Buildout modules (Aidan 2026-08-06): the buildout is sold as
 * modular line items the rep toggles with the owner — each priced, summing
 * to the package total, so the merchant sees exactly what they're buying.
 * One-time modules bill into the setup fee; monthly ones are recurring and
 * listed separately. All one-time modules together = $500 (the package).
 */
export interface WebsiteModule {
  id: string
  label: string
  blurb: string
  price: number
  /** recurring — shown as /mo, never summed into the one-time setup fee */
  monthly?: boolean
  /** the core build — always included, can't be unchecked */
  core?: boolean
}

export const WEBSITE_MODULES: WebsiteModule[] = [
  { id: 'core', label: 'Custom build & launch', blurb: 'Full site designed, built, and launched in 48 hours', price: 250, core: true },
  { id: 'scroll', label: 'Scrolling animation', blurb: 'Scroll-driven motion and reveal effects', price: 75 },
  { id: 'anim3d', label: '3D product animation', blurb: 'Interactive 3D showcase of their product or space', price: 125 },
  { id: 'forms', label: 'Booking & quote form wiring', blurb: 'Forms wired to their email and phone', price: 50 },
  { id: 'maint', label: 'Meridian Maintenance', blurb: 'Content edits, updates, and fixes handled by us', price: 40, monthly: true },
  { id: 'host', label: 'Server hosting', blurb: 'Fast managed hosting with SSL', price: 35, monthly: true },
]

/**
 * 30-Second AI Advertisement (Aidan 2026-08-14) — a Setup Service alongside
 * Website Buildout: FIXED price, billed into the same one-time setup fee.
 *
 * What the merchant buys is a finished 30-second commercial, not a credit
 * balance: the rep's intake below becomes the creative brief, and closing the
 * deal posts it to POST /api/content/ad-spot/order, where the Commercial
 * Director boards it into SHOT_COUNT shots and submits each to the generation
 * pipeline. Assembly (cut, voiceover, music, captions) is a finishing step on
 * top of the generated shots — see docs and the route's module docstring.
 */
export interface AdSpotService {
  id: string
  label: string
  blurb: string
  price: number
  /** Finished runtime of the delivered spot, in seconds. */
  durationSeconds: number
  /** Shots the spot is cut from — the pipeline generates one clip per shot. */
  shotCount: number
  /** What the merchant receives — quoted on the proposal, so keep it true. */
  deliverables: string[]
}

export const AD_SPOT_SERVICE: AdSpotService = {
  id: 'adspot',
  label: '30-Second AI Advertisement',
  blurb: 'A finished 30-second commercial for their business — scripted, generated, and cut for their channels',
  price: 1000,
  durationSeconds: 30,
  shotCount: 6,
  deliverables: [
    'Scripted 30-second spot built from their offer',
    'Six AI-generated shots, cut to the read',
    'Voiceover and music bed',
    'Delivered in their placement\'s aspect ratio, no watermark',
    'One revision round on the cut',
  ],
}

/** Where the spot runs — this picks the aspect ratio the shots generate at.
 *  Ids match the backend PLATFORM_CONFIG keys; do not invent new ones here
 *  without adding them there too (an unknown id silently falls back to 9:16). */
export const AD_SPOT_PLACEMENTS: { id: string; label: string; aspect: string }[] = [
  { id: 'instagram_reel', label: 'Reels / TikTok / Shorts', aspect: '9:16' },
  { id: 'instagram_feed', label: 'Instagram + Facebook feed', aspect: '1:1' },
  { id: 'youtube_video', label: 'YouTube / website / in-store screen', aspect: '16:9' },
]

/** How the spot is scored. Drives the finishing step, not the shot prompts. */
export const AD_SPOT_AUDIO: { id: string; label: string }[] = [
  { id: 'voiceover_music', label: 'Voiceover + music bed' },
  { id: 'music_only', label: 'Music bed only' },
  { id: 'captions_only', label: 'On-screen captions only (silent autoplay)' },
]

/**
 * Custom CRM build — a Setup Service alongside Website Buildout, billed into
 * the same one-time setup fee. Unlike the website modules its price is NOT
 * fixed: the build is scoped per deal, so the rep enters the amount they
 * quoted. Same currency as the page it renders on (no FX — nothing to
 * convert on a rep-entered figure).
 */
export const CUSTOM_CRM_SERVICE = {
  id: 'crm',
  label: 'Custom CRM build',
  blurb: 'Pipeline, contacts and follow-ups built around how they actually sell',
} as const

/**
 * Parse a rep-typed setup-service amount into whole currency units. Blank and
 * unparseable input is 0, never NaN — the result is summed into the setup fee
 * that reaches the onboarding link, the invoice, the SLA and Stripe.
 */
export function parseSetupServiceAmount(raw: string | null | undefined): number {
  if (raw == null) return 0
  const parsed = parseInt(String(raw).trim(), 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0
}

/** The monthly buildout modules (Meridian Maintenance + Server hosting) come
 *  FREE with the second tier and up (Aidan 2026-08-06) — only Standard pays
 *  the monthly. Index-based so future tiers above Premium stay included. */
export function websiteMonthlyFree(planId: string): boolean {
  return PLAN_TIERS.findIndex(p => p.id === planId) >= 1
}

export function getPlan(id: string): PlanTier {
  return PLAN_TIERS.find(p => p.id === id) || PLAN_TIERS[1] // default to Premium
}

/**
 * Closest monthly tier for a custom monthly price. Reps can slide above a
 * tier's base price, so plan labels shown on SLAs/emails/checkout links are
 * derived from the canonical tier prices above rather than hardcoded
 * thresholds.
 */
export function closestMonthlyPlan(monthly: number, tiers: PlanTier[] = PLAN_TIERS): PlanTier {
  const monthlyTiers = tiers.filter(p => (p.interval ?? 'month') === 'month')
  return monthlyTiers.reduce((best, p) =>
    Math.abs(p.price - monthly) < Math.abs(best.price - monthly) ? p : best
  )
}
