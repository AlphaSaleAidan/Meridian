import { getAuthHeaders } from '@/lib/supabase'
import type {
  PhoneCallEntry, PhoneBizConfig, PhoneStats,
  CallStatus, PaymentStatus, TranscriptLine, VoicePersonality,
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

/** Normalise a raw North-American number to +1XXXXXXXXXX E.164 format. */
export function normalizeToE164(raw: string): string {
  const digits = raw.replace(/[^\d]/g, '')
  if (digits.length === 10) return `+1${digits}`
  if (digits.length === 11 && digits.startsWith('1')) return `+${digits}`
  return raw.trim() // already E.164 or unknown format — pass through as-is
}

export interface ReservationConfig {
  on_website: boolean
  website_url: string
}

export interface PhoneConfig {
  exists: boolean
  merchant_id: string
  business_name?: string
  business_type?: string
  phone_number?: string
  greeting?: string
  voice?: string
  // 'en' (default) or 'multi' — multilingual understanding (Hindi/Punjabi +
  // English code-switching) on live calls.
  language?: string
  // Accent group picked in the wizard (north_american | indian | east_asian).
  accent?: string
  // Rep-negotiated per-order Meridian fee override (cents). null/undefined =
  // plan default. Read-only here — set from the sales portal, shown in the
  // wizard's pricing disclosure.
  order_fee_cents?: number | null
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
  // Per-merchant hard call cap (minutes). null/undefined = platform default
  // (8 min); 0 = uncapped.
  max_call_minutes?: number | null
  // The merchant's real store line (the number they forward FROM) — used by
  // the forwarding verification flow.
  business_line_number?: string
  // How confirmed orders are routed, chosen in the setup wizard.
  order_routing?: 'pos' | 'webhook' | 'sms' | 'email'
  // Merchant-customized Text-to-Pay SMS body. Supports {name} {business}
  // {total} {link} placeholders; empty/unset falls back to the default copy.
  sms_pay_template?: string
  reservation_config?: ReservationConfig | null
  // Agent personality (formality/upsell/humor/custom phrases/brand keywords).
  // Persisted to phone_agent_config.personality (JSONB) and rendered into the
  // live Vapi system prompt by vapi_webhook._system_prompt.
  personality?: VoicePersonality | null
  // Call-script pack (services/phone_agent/script_packs.py). 'legacy' or
  // unset = the standard generic script (default, zero behavior change);
  // other values opt into a per-vertical time-optimized script.
  script_pack?: string
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
  // 400 = format errors; 422 = safety validation (e.g. the transfer-loop
  // guard) — both carry a merchant-readable reason in `detail`.
  if ((res.status === 400 || res.status === 422) && res.detail) return res.detail
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

/** One advisory recommendation from the call-telemetry feedback loop.
 * READ-ONLY: it names a suggested_change; nothing is auto-applied. */
export interface PhoneRecommendation {
  signal: 'RAISE_CAP' | 'AGENT_QUALITY' | 'PRICING_HEADROOM' | string
  title: string
  suggested_change: string
  impact_score: number
  advisory: boolean
  evidence: Record<string, number>
}

export interface PhoneRecommendationsResponse {
  merchant_id: string
  days: number
  total_calls: number
  recommendations: PhoneRecommendation[]
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

  /** Advisory cap/fee recommendations derived from call-ending telemetry.
   * Read-only: the server never mutates a cap or fee — a human decides. */
  async getRecommendations(merchantId: string, days = 7): Promise<PhoneRecommendationsResponse | null> {
    const res = await fetch(
      `${API_BASE}/api/phone/recommendations/${merchantId}?days=${days}`,
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
    personality?: VoicePersonality
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

  // ── Forwarding verification (setup wizard "Verify forwarding") ──

  /** Place a live test call to the merchant's store line; if their carrier
   * forward is set up, it lands on the Meridian agent and the pending
   * verification flips to `verified` (poll verifyForwardingStatus). */
  async verifyForwardingStart(merchantId: string, businessLineNumber?: string): Promise<ForwardingVerifyStart> {
    const res = await fetch(`${API_BASE}/api/phone/forwarding/verify-start`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ merchant_id: merchantId, business_line_number: businessLineNumber || undefined }),
    })
    if (!res.ok) {
      let detail = `verification failed to start (${res.status})`
      try { detail = (await res.json()).detail || detail } catch { /* noop */ }
      throw new Error(detail)
    }
    return res.json()
  },

  // Kitchen prove-out: fire a clearly-marked test order through the REAL
  // dispatch pipeline (POS + merchant SMS in parallel), honoring demo_safe.
  async sendTestOrder(merchantId: string): Promise<TestOrderResponse> {
    const res = await fetch(`${API_BASE}/api/phone/test-order/${merchantId}`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
    })
    if (!res.ok) {
      let detail = `test order failed: ${res.status}`
      try { detail = (await res.json()).detail || detail } catch { /* noop */ }
      throw new Error(detail)
    }
    return res.json()
  },

  async verifyForwardingStatus(merchantId: string): Promise<ForwardingVerifyStatus> {
    const res = await fetch(
      `${API_BASE}/api/phone/forwarding/verify-status/${merchantId}`,
      { headers: await getAuthHeaders() },
    )
    if (!res.ok) return { status: 'none' }
    return res.json()
  },

  /** Fire-and-forget activation-funnel event — never throws, never awaited
   * by callers (a telemetry failure must not disturb the wizard). */
  activationEvent(merchantId: string, step: ActivationStep, meta?: Record<string, unknown>): void {
    if (!merchantId) return
    getAuthHeaders()
      .then(headers => fetch(`${API_BASE}/api/phone/activation-event`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ merchant_id: merchantId, step, meta: meta || {} }),
      }))
      .catch(() => { /* fire-and-forget */ })
  },

  // Poll the per-channel delivery + fulfillment confirmation of a test order.
  async getTestOrderStatus(merchantId: string, orderId: string): Promise<TestOrderStatus | null> {
    const res = await fetch(
      `${API_BASE}/api/phone/test-order/${merchantId}/status/${orderId}`,
      { headers: await getAuthHeaders() },
    )
    if (!res.ok) return null
    return res.json()
  },
}

export type ActivationStep =
  | 'wizard_opened' | 'carrier_selected' | 'codes_viewed'
  | 'verify_started' | 'verified' | 'verify_failed'

export interface ForwardingVerifyStart {
  ok: boolean
  status: 'pending'
  verification_id?: string | null
  timeout_seconds: number
}

export interface ForwardingVerifyStatus {
  status: 'none' | 'pending' | 'verified' | 'failed'
  started_at?: string
  verified_at?: string | null
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

// Per-channel leg outcome from the delivery fan-out
// (sent | failed | deferred_pending_payment | skipped_* | demo_safe).
export interface TestOrderChannel {
  status?: string
  error?: string
  at?: string
  [key: string]: unknown
}

export interface TestOrderResponse {
  ok: boolean
  order_id: string | null
  pos_order_id: string
  pos_system: string
  demo_safe: boolean
  verifying: boolean
  channels: {
    pos?: TestOrderChannel | null
    customer_sms?: TestOrderChannel | null
    merchant_sms?: TestOrderChannel | null
  }
  item: string
  total: number
}

export interface TestOrderStatus {
  order_id: string
  source?: string
  status?: string
  pos_system?: string | null
  pos_order_id?: string | null
  pos_success?: boolean
  pos_delivery_status?: string | null
  sms_delivery_status?: string | null
  merchant_notify_status?: string | null
  delivery_detail?: Record<string, TestOrderChannel>
  fulfillment_state?: string | null
  fulfillment_confirmed_at?: string | null
  created_at?: string
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
