/**
 * Site Care — change requests for merchants whose website Meridian built.
 *
 * PRICING HERE IS PROVISIONAL. The amounts are placeholders, anchored to the
 * existing Website Buildout scale in canada-proposal-plans.ts (core CA$350,
 * anim3d CA$175, scroll CA$105, forms CA$70, maint CA$55) so the surface has a
 * coherent shape to show. They are NOT an approved rate card. Set the real
 * numbers here — this file is the single source, and every amount reaches the
 * customer labelled as an estimate confirmed before any work starts.
 */

export type SiteRequestKind =
  | 'content'
  | 'media'
  | 'menu'
  | 'page'
  | 'design'
  | 'seo'
  | 'fix'

export interface SiteRequestType {
  kind: SiteRequestKind
  label: string
  /** What the merchant gets — written for them, not for us. */
  description: string
  /** Provisional estimate in CAD. `null` renders as "Quoted on request". */
  estimateCad: number | null
  /** Business days, quoted as a range. */
  turnaround: string
}

export const SITE_REQUEST_TYPES: SiteRequestType[] = [
  {
    kind: 'content',
    label: 'Content update',
    description: 'Change wording, hours, contact details or prices already on the site.',
    estimateCad: 55,
    turnaround: '1–2 business days',
  },
  {
    kind: 'media',
    label: 'Photos & media',
    description: 'Swap in new photography, logos or video, resized and optimised for you.',
    estimateCad: 70,
    turnaround: '1–2 business days',
  },
  {
    kind: 'menu',
    label: 'Menu or product update',
    description: 'Add, remove or re-price items, including anything wired to online ordering.',
    estimateCad: 85,
    turnaround: '2–3 business days',
  },
  {
    kind: 'page',
    label: 'New page',
    description: 'A new section built to match the rest of the site — about, careers, location.',
    estimateCad: 175,
    turnaround: '3–5 business days',
  },
  {
    kind: 'design',
    label: 'Design change',
    description: 'Layout, colour or typography work across one or more existing pages.',
    estimateCad: 105,
    turnaround: '3–5 business days',
  },
  {
    kind: 'seo',
    label: 'SEO update',
    description: 'Titles, descriptions and structured data so you show up properly in search.',
    estimateCad: 70,
    turnaround: '2–3 business days',
  },
  {
    kind: 'fix',
    label: 'Something is broken',
    description: 'A link, form or page that is not working. No charge if we caused it.',
    estimateCad: null,
    turnaround: 'Same business day',
  },
]

/** Surcharge for jumping the queue. Provisional — see the file header. */
export const RUSH_SURCHARGE_CAD = 60
export const RUSH_TURNAROUND = 'Next business day'

export function requestType(kind: SiteRequestKind): SiteRequestType {
  return SITE_REQUEST_TYPES.find(t => t.kind === kind) ?? SITE_REQUEST_TYPES[0]
}

export type SiteRequestStatus = 'submitted' | 'in_review' | 'in_progress' | 'complete'

export const STATUS_LABELS: Record<SiteRequestStatus, string> = {
  submitted: 'Submitted',
  in_review: 'In review',
  in_progress: 'In progress',
  complete: 'Complete',
}

export interface SiteChangeRequest {
  id: string
  kind: SiteRequestKind
  details: string
  rush: boolean
  /** Estimate at submission time, in CAD. `null` = quoted on request. */
  estimateCad: number | null
  status: SiteRequestStatus
  submittedAt: string
}
