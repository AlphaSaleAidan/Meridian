/**
 * Ad Spot API client — the 30-Second AI Advertisement sold as a Setup Service.
 *
 * Mirrors src/api/routes/ad_spot.py. Every call carries the rep's Supabase
 * session (getAuthHeaders), same as content-api.ts.
 *
 * The status ladder is deliberately explicit, because "the ad is done" is a
 * claim about a merchant's paid deliverable:
 *
 *   boarding → generating → shots_ready → assembling → assembled → delivered
 *
 * `shots_ready` = footage in hand. `assembled` = a master exists and a human
 * should watch it. Only `delivered` means the merchant has it.
 */

import { getAuthHeaders } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

export type AdSpotStatus =
  | 'boarding'
  | 'generating'
  | 'shots_ready'
  | 'assembling'
  | 'assembled'
  | 'delivered'
  | 'failed'

export type AdSpotShotStatus = 'queued' | 'generating' | 'completed' | 'failed'

export interface AdSpotOrder {
  id: string
  created_at: string
  market: 'us' | 'ca'
  business_name: string
  business_type?: string | null
  contact_email?: string | null
  rep_id?: string | null
  rep_name?: string | null
  price_cents: number
  currency: 'USD' | 'CAD'
  goal: string
  highlights?: string | null
  brand_notes?: string | null
  placement: string
  aspect_ratio?: string | null
  audio: string
  status: AdSpotStatus
  status_detail?: string | null
  storyboard?: { aspect_ratio?: string; shots?: { shot: number; beat: string; voiceover?: string }[] } | null
  master_url?: string | null
  assembled_at?: string | null
  assembly_notes?: {
    notes?: string[]
    hasVoiceover?: boolean
    hasMusic?: boolean
    hasCaptions?: boolean
    width?: number
    height?: number
    shotsUsed?: number
  } | null
  delivered_url?: string | null
  delivered_at?: string | null
}

export interface AdSpotShot {
  id: string
  shot_number: number
  beat?: string | null
  prompt?: string | null
  model?: string | null
  duration_seconds?: number | null
  status: AdSpotShotStatus
  video_url?: string | null
  error?: string | null
}

export interface AdSpotDetail {
  ok: boolean
  order: AdSpotOrder
  shots: AdSpotShot[]
  shotsCompleted: number
  shotsTotal: number
}

export interface AdSpotAssembleResult {
  ok: boolean
  orderId: string
  /** Accepted, not finished — encoding runs detached and the order moves to
   *  `assembled` (or back to `shots_ready` with a reason) when it lands. Poll
   *  the order; whatever the cut left out arrives in `assembly_notes`. */
  status: 'assembling'
  shotsUsed: number
  durationSeconds: number
}

async function apiFetch<T>(path: string, method: 'GET' | 'POST' = 'GET', body?: unknown): Promise<T> {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { ...headers, Accept: 'application/json' },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(
      typeof detail?.detail === 'string' ? detail.detail : `Request failed (${res.status})`,
    )
  }
  return res.json()
}

export const adSpotApi = {
  list: (repId?: string) =>
    apiFetch<{ ok: boolean; orders: AdSpotOrder[] }>(
      `/api/content/ad-spot${repId ? `?repId=${encodeURIComponent(repId)}` : ''}`,
    ),

  get: (orderId: string) => apiFetch<AdSpotDetail>(`/api/content/ad-spot/${orderId}`),

  /** Re-generate one shot without touching (or re-paying for) the others. */
  retryShot: (orderId: string, shotNumber: number) =>
    apiFetch<{ ok: boolean; shotNumber: number; status: string }>(
      `/api/content/ad-spot/${orderId}/shots/${shotNumber}/retry`,
      'POST',
    ),

  /** Start cutting the completed shots into a master. Returns as soon as the
   *  job is accepted — ffmpeg runs server-side for minutes, so watch the
   *  order's status rather than this promise. */
  assemble: (orderId: string) =>
    apiFetch<AdSpotAssembleResult>(`/api/content/ad-spot/${orderId}/assemble`, 'POST'),

  /** Hand it over. Omit the url to deliver the assembled master as-is. */
  deliver: (orderId: string, deliveredUrl?: string) =>
    apiFetch<{ ok: boolean; status: string; deliveredUrl: string }>(
      `/api/content/ad-spot/${orderId}/deliver`,
      'POST',
      { deliveredUrl: deliveredUrl || null },
    ),
}

/** Currency-correct price label for an order, in the market it was sold in. */
export function adSpotPriceLabel(order: Pick<AdSpotOrder, 'price_cents' | 'currency'>): string {
  const amount = (order.price_cents / 100).toLocaleString()
  return order.currency === 'CAD' ? `CA$${amount}` : `$${amount}`
}

/** How the status ladder reads to a rep — never overstate where a spot is. */
export const AD_SPOT_STATUS_LABEL: Record<AdSpotStatus, string> = {
  boarding: 'Writing the shot list',
  generating: 'Generating shots',
  shots_ready: 'Footage ready — needs the cut',
  assembling: 'Cutting the master',
  assembled: 'Master ready — review it',
  delivered: 'Delivered',
  failed: 'Needs a human',
}
