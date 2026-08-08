/**
 * Site Care — change requests for merchants whose website Meridian built.
 *
 * There is deliberately NO published rate card. Change requests vary too much
 * in scope to price up front, so every request is quoted before work starts
 * and the UI never shows a number it cannot stand behind. Turnaround is the
 * only commitment made here.
 *
 * If fixed pricing is introduced later, it belongs in this file and nowhere
 * else — the page reads everything below and formats nothing of its own.
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
  /** Business days, quoted as a range. The only figure we commit to. */
  turnaround: string
}

export const SITE_REQUEST_TYPES: SiteRequestType[] = [
  {
    kind: 'content',
    label: 'Content update',
    description: 'Change wording, hours, contact details or prices already on the site.',
    turnaround: '1–2 business days',
  },
  {
    kind: 'media',
    label: 'Photos & media',
    description: 'Swap in new photography, logos or video, resized and optimised for you.',
    turnaround: '1–2 business days',
  },
  {
    kind: 'menu',
    label: 'Menu or product update',
    description: 'Add, remove or re-price items, including anything wired to online ordering.',
    turnaround: '2–3 business days',
  },
  {
    kind: 'page',
    label: 'New page',
    description: 'A new section built to match the rest of the site — about, careers, location.',
    turnaround: '3–5 business days',
  },
  {
    kind: 'design',
    label: 'Design change',
    description: 'Layout, colour or typography work across one or more existing pages.',
    turnaround: '3–5 business days',
  },
  {
    kind: 'seo',
    label: 'SEO update',
    description: 'Titles, descriptions and structured data so you show up properly in search.',
    turnaround: '2–3 business days',
  },
  {
    kind: 'fix',
    label: 'Something is broken',
    description: 'A link, form or page that is not working. No charge if we caused it.',
    turnaround: 'Same business day',
  },
]

/** Priority handling. Priced in the quote like everything else. */
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
  status: SiteRequestStatus
  submittedAt: string
}
