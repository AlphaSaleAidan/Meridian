import { getAuthHeaders } from '@/lib/supabase'
import type {
  PhoneCallEntry, PhoneBizConfig, PhoneStats,
  CallStatus, PaymentStatus, TranscriptLine,
} from './phone-orders-demo-data'

const API_BASE = import.meta.env.VITE_API_URL || ''

// E.164: a leading '+' then 8–15 digits, first digit non-zero. This is the
// format the live phone agent dials when warm-transferring a caller to a human
// (see phone.py transfer_call). Used to validate the wizard's transfer-number
// field before it's persisted as `transfer_number`.
const E164_RE = /^\+[1-9]\d{7,14}$/

/** True when `value` is a syntactically valid E.164 phone number. */
export function isValidE164(value: string): boolean {
  return E164_RE.test(value.trim())
}

export interface PhoneConfig {
  exists: boolean
  merchant_id: string
  business_name?: string
  business_type?: string
  phone_number?: string
  greeting?: string
  voice?: string
  language?: string
  active?: boolean
  menu_items?: any[]
  pos_system?: string
  pos_location_id?: string
  business_hours?: Record<string, string>
  after_hours_message?: string
  max_concurrent_calls?: number
  order_types?: string[]
  special_instructions_enabled?: boolean
  transfer_number?: string
  // How confirmed orders are routed, chosen in the setup wizard.
  order_routing?: 'pos' | 'webhook' | 'sms' | 'email'
  // Merchant-customized Text-to-Pay SMS body. Supports {name} {business}
  // {total} {link} placeholders; empty/unset falls back to the default copy.
  sms_pay_template?: string
}

/** Result of POST /api/phone/config — carries enough to explain a failure. */
export interface SaveConfigResult {
  ok: boolean
  status: number
  detail?: string
}

/**
 * Human-readable reason for a failed saveConfig, specific enough to act on:
 * auth problems say "log out and back in", validation errors surface the
 * backend's own detail text.
 */
export function saveConfigErrorMessage(res: SaveConfigResult): string {
  if (res.ok) return ''
  if (res.status === 401 || res.status === 403) {
    return 'Session issue — log out and back in, then try again.'
  }
  if (res.status === 400 && res.detail) return res.detail
  if (res.detail) return `Could not save (${res.status}): ${res.detail}`
  return `Could not save — the server responded with ${res.status}. Please try again.`
}

export interface PhoneStatsResponse {
  merchant_id: string
  days: number
  total_calls: number
  order_calls: number
  conversion_rate: number
  total_orders: number
  total_revenue: number
  avg_duration_seconds: number
}

export const phoneService = {
  async getConfig(merchantId: string): Promise<PhoneConfig> {
    const res = await fetch(
      `${API_BASE}/api/phone/config/${merchantId}`,
      { headers: await getAuthHeaders() },
    )
    if (!res.ok) return { exists: false, merchant_id: merchantId }
    return res.json()
  },

  async saveConfig(config: Partial<PhoneConfig> & { merchant_id: string }): Promise<SaveConfigResult> {
    let res: Response
    try {
      res = await fetch(`${API_BASE}/api/phone/config`, {
        method: 'POST',
        headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
    } catch {
      // Network / CORS failure — no HTTP status to report.
      return { ok: false, status: 0, detail: 'Could not reach the server' }
    }
    if (res.ok) return { ok: true, status: res.status }
    let detail: string | undefined
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
      else if (body?.detail != null) detail = JSON.stringify(body.detail)
    } catch { /* non-JSON error body */ }
    return { ok: false, status: res.status, detail }
  },

  async getCalls(merchantId: string, limit = 50): Promise<PhoneCallEntry[]> {
    const res = await fetch(
      `${API_BASE}/api/phone/calls/${merchantId}?limit=${limit}`,
      { headers: await getAuthHeaders() },
    )
    if (!res.ok) return []
    const data = await res.json()
    return (data.calls || []).map(mapCallRow)
  },

  async getStats(merchantId: string, days = 7): Promise<PhoneStatsResponse | null> {
    const res = await fetch(
      `${API_BASE}/api/phone/stats/${merchantId}?days=${days}`,
      { headers: await getAuthHeaders() },
    )
    if (!res.ok) return null
    return res.json()
  },

  async testChat(req: {
    merchant_id: string
    messages: { role: 'user' | 'assistant'; content: string }[]
    business_name?: string
    greeting?: string
    menu_items?: { name: string; price: number; category?: string }[]
    order_types?: string[]
  }): Promise<TestChatResponse> {
    const res = await fetch(`${API_BASE}/api/phone/test-chat`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    if (!res.ok) throw new Error(`test-chat failed: ${res.status}`)
    return res.json()
  },

  async getMenuStatus(merchantId: string): Promise<MenuBuildStatus> {
    const res = await fetch(
      `${API_BASE}/api/phone/menu/status/${merchantId}`,
      { headers: await getAuthHeaders() },
    )
    if (!res.ok) return { state: 'idle', item_count: 0, sample: [] }
    return res.json()
  },

  async provisionNumber(req: {
    merchant_id: string
    country?: string
    area_code?: string
    business_name?: string
    // Swap: release the current number at the provider and purchase a new one.
    force?: boolean
  }): Promise<ProvisionNumberResponse> {
    const res = await fetch(`${API_BASE}/api/phone/provision-number`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    if (!res.ok) {
      let detail = `provision failed: ${res.status}`
      try { detail = (await res.json()).detail || detail } catch { /* noop */ }
      throw new Error(detail)
    }
    return res.json()
  },

  // Supplementary menu builder: upload a photo of a paper menu; the backend
  // runs a vision model and MERGES the extracted items onto the existing menu.
  async scanMenuPhoto(merchantId: string, file: File, replace = false): Promise<MenuScanResult> {
    const form = new FormData()
    form.append('photo', file)
    // Strip Content-Type so the browser sets the multipart boundary itself.
    const { 'Content-Type': _ct, ...headers } = await getAuthHeaders()
    const res = await fetch(
      `${API_BASE}/api/phone/menu/scan-photo/${merchantId}?replace=${replace}`,
      { method: 'POST', headers, body: form },
    )
    if (!res.ok) {
      let detail = `scan failed: ${res.status}`
      try { detail = (await res.json()).detail || detail } catch { /* noop */ }
      throw new Error(detail)
    }
    return res.json()
  },

  // Supplementary menu builder: upload a CSV (name,price,category — header
  // flexible); the backend parses rows and MERGES them onto the existing menu.
  async importMenuCsv(merchantId: string, file: File, replace = false): Promise<MenuScanResult> {
    const form = new FormData()
    form.append('file', file)
    // Strip Content-Type so the browser sets the multipart boundary itself.
    const { 'Content-Type': _ct, ...headers } = await getAuthHeaders()
    const res = await fetch(
      `${API_BASE}/api/phone/menu/import-csv/${merchantId}?replace=${replace}`,
      { method: 'POST', headers, body: form },
    )
    if (!res.ok) {
      let detail = `import failed: ${res.status}`
      try { detail = (await res.json()).detail || detail } catch { /* noop */ }
      throw new Error(detail)
    }
    return res.json()
  },
}

export interface MenuScanResult {
  scanned: boolean
  added: number
  scanned_count?: number
  item_count: number
  mode?: 'merge' | 'replace'
  reason?: string
  sample?: { name: string; price?: number; category?: string }[]
}

export interface ProvisionNumberResponse {
  phone_number: string
  provisioned: boolean
  already_existed: boolean
}

export type MenuBuildState = 'idle' | 'building' | 'ready' | 'error'

export interface MenuBuildStatus {
  state: MenuBuildState
  item_count: number
  updated_at?: string | null
  sample: string[]
}

export interface TestChatResponse {
  reply: string
  ended: boolean
  order: Record<string, unknown> | null
}

function mapCallRow(row: any): PhoneCallEntry {
  const items = (row.order_data?.items || []).map((i: any) => ({
    name: i.name || '',
    qty: i.quantity || 1,
    price: i.price || 0,
  }))
  const subtotal = items.reduce((s: number, i: any) => s + i.price * i.qty, 0)

  const transcript: TranscriptLine[] = (row.transcript || []).map((t: any) => ({
    speaker: t.role === 'user' ? 'caller' : 'agent',
    text: t.content || '',
    time: '',
  }))

  const dur = row.duration_seconds || 0
  const mins = Math.floor(dur / 60)
  const secs = dur % 60

  return {
    id: row.id || row.call_sid || '',
    phone: row.caller_phone || '',
    name: row.order_data?.customer_name || row.caller_phone || 'Unknown',
    status: (row.status as CallStatus) || 'no_order',
    duration: `${mins}:${secs.toString().padStart(2, '0')}`,
    durationSec: dur,
    items,
    subtotal: Math.round(subtotal * 100) / 100,
    tax: 0,
    total: Math.round(subtotal * 100) / 100,
    orderType: row.order_data?.order_type || 'pickup',
    transcript,
    createdAt: row.created_at || new Date().toISOString(),
    paymentStatus: (row.pos_result?.payment_status as PaymentStatus) || 'none',
    paymentLink: row.pos_result?.payment_link || '',
    smsSent: row.pos_result?.sms_sent || false,
  }
}
