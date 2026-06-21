import { getAuthHeaders } from '@/lib/supabase'
import type {
  PhoneCallEntry, PhoneBizConfig, PhoneStats,
  CallStatus, PaymentStatus, TranscriptLine,
} from './phone-orders-demo-data'

const API_BASE = import.meta.env.VITE_API_URL || ''

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

  async saveConfig(config: Partial<PhoneConfig> & { merchant_id: string }): Promise<boolean> {
    const res = await fetch(`${API_BASE}/api/phone/config`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    return res.ok
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
