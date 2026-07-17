import { getAuthHeaders } from '@/lib/supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

/**
 * Client for the normalized menu store (/api/menu/*).
 *
 * The store is the single source of truth; the backend keeps the legacy
 * phone_agent_config.menu_items JSONB in sync (write-through mirror), so the
 * live agent updates the moment anything here succeeds. All ingestion lands
 * in a review queue (needs_review) — nothing scraped/uploaded goes live until
 * confirmed. POS import is the exception (trusted; flagged only when a price
 * is missing).
 */

export interface MenuStoreItem {
  id: string
  name: string
  price?: number
  category?: string
  description?: string
  sizes?: string[]
  size_prices?: Record<string, number>
  topping_price?: number
  modifications?: string[]
  sold_out: boolean
  source: 'manual' | 'pos' | 'scrape' | 'csv' | 'photo'
  confidence?: number | null
  needs_review: boolean
  published: boolean
  position?: number | null
  updated_at?: string
}

export interface MenuItemsResponse {
  merchant_id: string
  items: MenuStoreItem[]
  pending_review: number
}

export interface MenuIngestResult {
  ok: boolean
  found: number
  pending_review: number
  skipped_existing: number
  row_errors?: { row: number; error: string }[]
  flags?: string[]
  engine?: string
  sample?: { name: string; price?: number; category?: string }[]
}

export interface MenuItemEdit {
  name?: string
  price?: number
  category?: string
  description?: string
  sold_out?: boolean
}

export interface PublicMenuInfo {
  published: boolean
  slug: string | null
  url: string | null
}

async function jsonOrThrow<T>(res: Response, fallback: string): Promise<T> {
  if (res.ok) return res.json()
  let detail = fallback
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') detail = body.detail
  } catch { /* non-JSON error body */ }
  throw new Error(detail)
}

async function uploadForm(path: string, field: string, file: File): Promise<MenuIngestResult> {
  const form = new FormData()
  form.append(field, file)
  // Strip Content-Type so the browser sets the multipart boundary itself.
  const { 'Content-Type': _ct, ...headers } = await getAuthHeaders()
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', headers, body: form })
  return jsonOrThrow(res, `upload failed: ${res.status}`)
}

export const menuService = {
  csvTemplateUrl: `${API_BASE}/api/menu/csv-template`,

  async getItems(merchantId: string): Promise<MenuItemsResponse> {
    const res = await fetch(`${API_BASE}/api/menu/${merchantId}/items`, {
      headers: await getAuthHeaders(),
    })
    return jsonOrThrow(res, `could not load menu: ${res.status}`)
  },

  async getReview(merchantId: string): Promise<MenuStoreItem[]> {
    const res = await fetch(`${API_BASE}/api/menu/${merchantId}/review`, {
      headers: await getAuthHeaders(),
    })
    const data = await jsonOrThrow<{ items: MenuStoreItem[] }>(res, `could not load review queue: ${res.status}`)
    return data.items || []
  },

  async confirm(merchantId: string, items: ({ id: string } & MenuItemEdit)[]): Promise<{ ok: boolean; published: number }> {
    const res = await fetch(`${API_BASE}/api/menu/${merchantId}/confirm`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
    })
    return jsonOrThrow(res, `confirm failed: ${res.status}`)
  },

  async patchItem(merchantId: string, itemId: string, edit: MenuItemEdit): Promise<void> {
    const res = await fetch(`${API_BASE}/api/menu/${merchantId}/items/${itemId}`, {
      method: 'PATCH',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify(edit),
    })
    await jsonOrThrow(res, `update failed: ${res.status}`)
  },

  async deleteItem(merchantId: string, itemId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/menu/${merchantId}/items/${itemId}`, {
      method: 'DELETE',
      headers: await getAuthHeaders(),
    })
    await jsonOrThrow(res, `delete failed: ${res.status}`)
  },

  async scrape(merchantId: string, url: string): Promise<MenuIngestResult> {
    const res = await fetch(`${API_BASE}/api/menu/${merchantId}/scrape`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    return jsonOrThrow(res, `scrape failed: ${res.status}`)
  },

  async uploadCsv(merchantId: string, file: File): Promise<MenuIngestResult> {
    return uploadForm(`/api/menu/${merchantId}/csv`, 'file', file)
  },

  async uploadPhoto(merchantId: string, file: File): Promise<MenuIngestResult> {
    return uploadForm(`/api/menu/${merchantId}/photo`, 'photo', file)
  },

  /** POS import — the trusted fourth path (POST /api/phone/menu/sync). */
  async syncPos(merchantId: string): Promise<{ synced: boolean; item_count: number; needs_review?: number; reason?: string }> {
    const res = await fetch(`${API_BASE}/api/phone/menu/sync/${merchantId}`, {
      method: 'POST',
      headers: await getAuthHeaders(),
    })
    return jsonOrThrow(res, `POS sync failed: ${res.status}`)
  },

  async getPublicInfo(merchantId: string): Promise<PublicMenuInfo> {
    const res = await fetch(`${API_BASE}/api/menu/${merchantId}/public-info`, {
      headers: await getAuthHeaders(),
    })
    return jsonOrThrow(res, `could not load public menu info: ${res.status}`)
  },

  async publish(merchantId: string): Promise<{ ok: boolean; slug: string; url: string; published: boolean }> {
    const res = await fetch(`${API_BASE}/api/menu/${merchantId}/publish`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ published: true }),
    })
    return jsonOrThrow(res, `publish failed: ${res.status}`)
  },

  async unpublish(merchantId: string): Promise<{ ok: boolean; slug: string | null; url: string | null; published: boolean }> {
    const res = await fetch(`${API_BASE}/api/menu/${merchantId}/publish`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ published: false }),
    })
    return jsonOrThrow(res, `unpublish failed: ${res.status}`)
  },
}
