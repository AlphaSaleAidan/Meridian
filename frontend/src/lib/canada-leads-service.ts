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

/** Reject a pending Supabase request after `ms` so the UI can't spin forever
 *  on a stalled connection or a wedged auth refresh. */
async function withTimeout<T>(p: PromiseLike<T>, ms: number, message: string): Promise<T> {
  let timer: ReturnType<typeof setTimeout>
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new LeadsServiceError(message)), ms)
  })
  try {
    return await Promise.race([p, timeout])
  } finally {
    clearTimeout(timer!)
  }
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
  // Locked fee terms (fee-parity) — optional: absent pre-migration.
  plan_tier: z.string().nullish(),
  monthly_fee_cents: z.union([z.number(), z.string()]).nullish(),
  order_fee_cents: z.union([z.number(), z.string()]).nullish(),
  call_overage_cents_per_min: z.union([z.number(), z.string()]).nullish(),
  included_call_min: z.union([z.number(), z.string()]).nullish(),
  fee_terms_locked_at: z.string().nullish(),
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
    plan_tier: r.plan_tier ?? null,
    monthly_fee_cents: r.monthly_fee_cents == null ? null : Number(r.monthly_fee_cents),
    order_fee_cents: r.order_fee_cents == null ? null : Number(r.order_fee_cents),
    call_overage_cents_per_min: r.call_overage_cents_per_min == null ? null : Number(r.call_overage_cents_per_min),
    included_call_min: r.included_call_min == null ? null : Number(r.included_call_min),
    fee_terms_locked_at: r.fee_terms_locked_at ?? null,
  }
}

// Module-level cache keyed by rep_id (empty string = "no rep filter"). Lets
// tab switches inside the portal show the last-known list immediately while
// `list()` revalidates in the background. The realtime subscription also
// writes through this cache.
const _listCache = new Map<string, Deal[]>()

// Fix #2: track inflight with a timestamp so stuck promises don't get
// re-attached to every new mount. If an inflight call is older than
// `_INFLIGHT_REUSE_MS`, the next caller starts a fresh request instead
// of awaiting the (likely dead) one. A 15s timeout on the underlying
// query also rejects the inflight promise so its `finally` clears the
// map entry.
type Inflight = { promise: Promise<Deal[]>; startedAt: number }
const _listInflight = new Map<string, Inflight>()
const _INFLIGHT_REUSE_MS = 1_000
const _LIST_TIMEOUT_MS = 15_000
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

  /** Drops the module-level list cache. Call on logout / rep switch so a
   * second rep on the same browser doesn't see the previous rep's deals
   * via `initialData` until staleTime expires. */
  invalidateCaches(): void {
    _invalidateCaches()
  },

  async list(repId?: string): Promise<Deal[]> {
    if (!supabase) return []
    const key = _cacheKey(repId)
    // De-dupe concurrent calls so rapid tab navigation doesn't spam the
    // API — but only reuse an inflight promise that's <1s old. A stuck
    // request (dropped TCP, slow network, paused JS context after a
    // background tab) used to attach every subsequent mount to a dead
    // promise, leaving every tab on the "loading" skeleton until the
    // user did a full page refresh.
    const existing = _listInflight.get(key)
    const now = Date.now()
    if (existing && now - existing.startedAt < _INFLIGHT_REUSE_MS) {
      return existing.promise
    }
    // Either no inflight, or the inflight is old enough to be suspect —
    // start fresh. The old promise (if any) continues running in the
    // background; its `finally` will only clear the map entry if its
    // key still points at it, so it can't evict our new entry.
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), _LIST_TIMEOUT_MS)
    const startedAt = Date.now()
    // Hoist the holder so the inner finally can compare against `holder.promise`
    // after it's assigned — the previous shape tripped TS2454 because the
    // closure referenced `promise` before it was bound.
    const holder: { promise: Promise<Deal[]> } = { promise: undefined as unknown as Promise<Deal[]> }
    holder.promise = (async () => {
      try {
        let query = supabase!
          .from('canada_leads')
          .select('*')
          .order('created_at', { ascending: false })
          .abortSignal(controller.signal)
        if (repId) query = query.eq('rep_id', repId)
        const { data, error } = await query
        if (error) throw new LeadsServiceError(error.message)
        const deals = (data || []).map(rowToDeal)
        _listCache.set(key, deals)
        return deals
      } finally {
        clearTimeout(timeoutId)
        const current = _listInflight.get(key)
        // Only clear if we're still the current entry — a fresher
        // request may have replaced us in the meantime, in which case
        // we must not evict it.
        if (current && current.promise === holder.promise) {
          _listInflight.delete(key)
        }
      }
    })()
    _listInflight.set(key, { promise: holder.promise, startedAt })
    return holder.promise
  },

  async getById(id: string, repId?: string): Promise<Deal | null> {
    if (!supabase) return null
    // Client-side defence: scope to the owning rep so a rep cannot fetch a
    // lead that belongs to a different rep even if RLS is misconfigured.
    let query = supabase
      .from('canada_leads')
      .select('*')
      .eq('id', id)
    if (repId) query = query.eq('rep_id', repId)
    const { data, error } = await query.single()
    if (error) throw new LeadsServiceError(error.message)
    if (!data) return null
    return rowToDeal(data)
  },

  async create(deal: Deal, repId?: string): Promise<Deal> {
    if (!supabase) return deal
    const { data, error } = await withTimeout(
      supabase
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
        .single(),
      15_000,
      'Saving the lead timed out — check your connection and try again.',
    )
    if (error) throw new Error(error.message)
    _invalidateCaches()
    if (data) return rowToDeal(data)
    return deal
  },

  async updateStage(id: string, stage: DealStage): Promise<void> {
    if (!supabase) return
    const now = new Date().toISOString().slice(0, 10)
    const { error } = await withTimeout(
      supabase
        .from('canada_leads')
        .update({ stage, updated_at: now })
        .eq('id', id),
      15_000,
      'Updating the stage timed out — check your connection and try again.',
    )
    if (error) throw new LeadsServiceError(error.message)
    _invalidateCaches()
  },

  async update(id: string, updates: Partial<Deal>): Promise<void> {
    if (!supabase) return
    const now = new Date().toISOString().slice(0, 10)
    const { error } = await withTimeout(
      supabase
        .from('canada_leads')
        .update({ ...updates, updated_at: now })
        .eq('id', id),
      15_000,
      'Saving the changes timed out — check your connection and try again.',
    )
    if (error) throw new LeadsServiceError(error.message)
    _invalidateCaches()
  },

  async delete(id: string): Promise<void> {
    if (!supabase) return
    // `.select()` returns the rows actually removed. PostgREST returns success
    // with zero rows when an RLS DELETE policy filters the row out, so without
    // this we'd report success on a silent no-op. Treat 0 rows as a hard
    // failure so the UI never claims a lead was deleted when it wasn't.
    const { data, error } = await withTimeout(
      supabase.from('canada_leads').delete().eq('id', id).select('id'),
      15_000,
      'Deleting the lead timed out — check your connection and try again.',
    )
    if (error) throw new LeadsServiceError(error.message)
    if (!data || data.length === 0) {
      throw new LeadsServiceError(
        'Lead could not be deleted — you may not have permission to remove it.',
      )
    }
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
        // Scope the realtime subscription to this rep's rows so the
        // callback does not fire for changes belonging to other reps.
        {
          event: '*',
          schema: 'public',
          table: 'canada_leads',
          ...(repId ? { filter: `rep_id=eq.${repId}` } : {}),
        },
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
