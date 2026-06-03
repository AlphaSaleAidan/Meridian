import { z } from 'zod'
import { supabase } from './supabase'
import type { RealtimeChannel } from '@supabase/supabase-js'
import type { Deal, DealStage } from './canada-sales-demo-data'

export class LeadsServiceError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'LeadsServiceError'
  }
}

function normalizeRate(v: number): number {
  return v <= 1 ? Math.round(v * 100) : v
}

const DEAL_STAGES = [
  'proposal_shown',
  'customer_checkout',
  'pos_connected',
  'customer_walkthrough',
  'closed_won',
  'closed_lost',
  'appointment_set',
  'prospecting',
  'contacted',
  'demo_scheduled',
  'proposal_sent',
  'negotiation',
] as const

// Schema for a row coming back from Supabase `canada_leads`. Required fields
// throw clearly if the backend renames or drops them; optional/nullable fields
// fall back to safe defaults instead of silently becoming `undefined`.
const CanadaLeadRowSchema = z.object({
  id: z.string(),
  business_name: z.string(),
  contact_name: z.string(),
  contact_email: z.string(),
  contact_phone: z.string().nullish(),
  vertical: z.string().nullish(),
  stage: z.enum(DEAL_STAGES).or(z.string()),
  monthly_value: z.union([z.number(), z.string()]).nullish(),
  commission_rate: z.union([z.number(), z.string()]).nullish(),
  expected_close_date: z.string().nullish(),
  notes: z.string().nullish(),
  source: z.string().nullish(),
  city: z.string().nullish(),
  province: z.string().nullish(),
  created_at: z.string(),
  updated_at: z.string(),
}).passthrough()

export type CanadaLeadRow = z.infer<typeof CanadaLeadRowSchema>

function rowToDeal(row: unknown): Deal {
  const parsed = CanadaLeadRowSchema.safeParse(row)
  if (!parsed.success) {
    const issues = parsed.error.issues.map(i => `${i.path.join('.')}: ${i.message}`).join('; ')
    throw new LeadsServiceError(`Invalid canada_leads row: ${issues}`)
  }
  const r = parsed.data
  return {
    id: r.id,
    business_name: r.business_name,
    contact_name: r.contact_name,
    contact_email: r.contact_email,
    contact_phone: r.contact_phone || '',
    vertical: r.vertical || '',
    stage: r.stage as DealStage,
    monthly_value: Number(r.monthly_value) || 0,
    commission_rate: normalizeRate(Number(r.commission_rate) || 0.7),
    expected_close_date: r.expected_close_date || '',
    notes: r.notes || '',
    source: r.source || '',
    city: r.city || '',
    province: r.province || '',
    created_at: r.created_at,
    updated_at: r.updated_at,
  }
}

// Module-level cache keyed by rep_id (empty string = "no rep filter"). Lets
// tab switches inside the portal show the last-known list immediately while
// `list()` revalidates in the background. The realtime subscription also
// writes through this cache.
const _listCache = new Map<string, Deal[]>()
const _listInflight = new Map<string, Promise<Deal[]>>()
const _cacheKey = (repId?: string) => repId || '__all__'

function _invalidateCaches() {
  _listCache.clear()
}

export const canadaLeadsService = {
  /** Synchronous read of the last-known list. Returns null if never fetched. */
  cached(repId?: string): Deal[] | null {
    const key = _cacheKey(repId)
    return _listCache.has(key) ? _listCache.get(key)! : null
  },

  async list(repId?: string): Promise<Deal[]> {
    if (!supabase) return []
    const key = _cacheKey(repId)
    // De-dupe concurrent calls so rapid tab navigation doesn't spam the API.
    const inflight = _listInflight.get(key)
    if (inflight) return inflight
    const promise = (async () => {
      try {
        let query = supabase!
          .from('canada_leads')
          .select('*')
          .order('created_at', { ascending: false })
        if (repId) query = query.eq('rep_id', repId)
        const { data, error } = await query
        if (error) throw new LeadsServiceError(error.message)
        const deals = (data || []).map(rowToDeal)
        _listCache.set(key, deals)
        return deals
      } finally {
        _listInflight.delete(key)
      }
    })()
    _listInflight.set(key, promise)
    return promise
  },

  async getById(id: string): Promise<Deal | null> {
    if (!supabase) return null
    const { data, error } = await supabase
      .from('canada_leads')
      .select('*')
      .eq('id', id)
      .single()
    if (error) throw new LeadsServiceError(error.message)
    if (!data) return null
    return rowToDeal(data)
  },

  async create(deal: Deal, repId?: string): Promise<Deal> {
    if (!supabase) return deal
    const { data, error } = await supabase
      .from('canada_leads')
      .insert({
        id: deal.id,
        business_name: deal.business_name,
        contact_name: deal.contact_name,
        contact_email: deal.contact_email,
        contact_phone: deal.contact_phone,
        vertical: deal.vertical,
        stage: deal.stage,
        monthly_value: deal.monthly_value,
        commission_rate: deal.commission_rate,
        expected_close_date: deal.expected_close_date,
        notes: deal.notes,
        source: deal.source || '',
        city: deal.city || '',
        province: deal.province || '',
        rep_id: repId || null,
      })
      .select()
      .single()
    if (error) throw new Error(error.message)
    _invalidateCaches()
    if (data) return rowToDeal(data)
    return deal
  },

  async updateStage(id: string, stage: DealStage): Promise<void> {
    if (!supabase) return
    const now = new Date().toISOString().slice(0, 10)
    const { error } = await supabase
      .from('canada_leads')
      .update({ stage, updated_at: now })
      .eq('id', id)
    if (error) throw new LeadsServiceError(error.message)
    _invalidateCaches()
  },

  async update(id: string, updates: Partial<Deal>): Promise<void> {
    if (!supabase) return
    const now = new Date().toISOString().slice(0, 10)
    const { error } = await supabase
      .from('canada_leads')
      .update({ ...updates, updated_at: now })
      .eq('id', id)
    if (error) throw new LeadsServiceError(error.message)
    _invalidateCaches()
  },

  async delete(id: string): Promise<void> {
    if (!supabase) return
    const { error } = await supabase.from('canada_leads').delete().eq('id', id)
    if (error) throw new LeadsServiceError(error.message)
    _invalidateCaches()
  },

  subscribe(
    repId: string | undefined,
    onChanged: (deals: Deal[]) => void,
  ): RealtimeChannel | null {
    if (!supabase) return null
    // Unique channel name per subscription so concurrent subscribers
    // (e.g. StrictMode double-mount + a tab navigation in flight)
    // don't share a single Supabase singleton channel by name.
    // Without this, the unmounting page's `removeChannel(...)` cleanup
    // killed the just-mounted page's binding — the "can't open the
    // next tab without a full refresh" symptom.
    const name = `canada_leads_realtime_${repId || 'all'}_${
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) + Date.now().toString(36)
    }`
    const channel = supabase
      .channel(name)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'canada_leads' },
        () => {
          canadaLeadsService.list(repId).then(onChanged).catch(() => {})
        },
      )
      .subscribe()
    return channel
  },

  unsubscribe(channel: RealtimeChannel | null): void {
    if (channel && supabase) {
      supabase.removeChannel(channel)
    }
  },
}
