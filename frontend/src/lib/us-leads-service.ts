import { supabase } from './supabase'
import type { RealtimeChannel } from '@supabase/supabase-js'
import type { Deal, DealStage } from './canada-sales-demo-data'

function normalizeRate(v: number): number {
  return v <= 1 ? Math.round(v * 100) : v
}

function rowToDeal(row: Record<string, unknown>): Deal {
  return {
    id: row.id as string,
    business_name: row.business_name as string,
    contact_name: row.contact_name as string,
    contact_email: row.contact_email as string,
    contact_phone: (row.contact_phone as string) || '',
    vertical: (row.vertical as string) || '',
    stage: row.stage as DealStage,
    monthly_value: Number(row.monthly_value) || 0,
    commission_rate: normalizeRate(Number(row.commission_rate) || 0.7),
    expected_close_date: (row.expected_close_date as string) || '',
    notes: (row.notes as string) || '',
    source: (row.source as string) || '',
    city: (row.city as string) || '',
    province: (row.province as string) || '',
    created_at: row.created_at as string,
    updated_at: row.updated_at as string,
    // Locked fee terms (fee-parity) — optional: absent pre-migration.
    plan_tier: (row.plan_tier as string) ?? null,
    monthly_fee_cents: row.monthly_fee_cents == null ? null : Number(row.monthly_fee_cents),
    order_fee_cents: row.order_fee_cents == null ? null : Number(row.order_fee_cents),
    call_overage_cents_per_min: row.call_overage_cents_per_min == null ? null : Number(row.call_overage_cents_per_min),
    included_call_min: row.included_call_min == null ? null : Number(row.included_call_min),
    fee_terms_locked_at: (row.fee_terms_locked_at as string) ?? null,
  }
}

/**
 * Postgres speaks to the database owner; this portal speaks to a rep. RLS
 * denials arrive as raw policy text — 'new row violates row-level security
 * policy "Training required to insert US leads"' — which lands in the add-lead
 * form verbatim and tells the rep nothing they can act on. Translate the
 * denials we know into the action they name, and keep everything else as-is:
 * an unexpected message is worth seeing unedited.
 */
export function humanise(message: string): string {
  if (/training required/i.test(message)) {
    return 'Finish your training first — leads unlock as soon as the course is done.'
  }
  if (/row-level security/i.test(message)) {
    return "Your account isn't allowed to do that. If it should be, ask your team lead."
  }
  return message
}

export class LeadsServiceError extends Error {
  constructor(message: string) {
    super(humanise(message))
    this.name = 'LeadsServiceError'
  }
}

// Cap every query so a stalled Supabase connection can't hang the UI forever
// (parity with canada-leads-service, which the US copy had dropped).
const QUERY_TIMEOUT_MS = 15000
function withTimeout<T>(p: PromiseLike<T>, label: string): Promise<T> {
  return Promise.race([
    Promise.resolve(p),
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new LeadsServiceError(`${label} timed out`)), QUERY_TIMEOUT_MS),
    ),
  ])
}

export const usLeadsService = {
  async list(repId?: string): Promise<Deal[]> {
    if (!supabase) return []
    let query = supabase
      .from('us_leads')
      .select('*')
      .order('created_at', { ascending: false })
    if (repId) query = query.eq('rep_id', repId)
    const { data, error } = await withTimeout(query, 'list')
    if (error) throw new LeadsServiceError(error.message)
    if (!data) return []
    return data.map(rowToDeal)
  },

  async getById(id: string): Promise<Deal | null> {
    if (!supabase) return null
    const { data, error } = await withTimeout(
      supabase.from('us_leads').select('*').eq('id', id).single(),
      'getById',
    )
    if (error) throw new LeadsServiceError(error.message)
    if (!data) return null
    return rowToDeal(data)
  },

  async create(deal: Deal, repId?: string): Promise<Deal> {
    if (!supabase) return deal
    const builder = supabase
      .from('us_leads')
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
    const { data, error } = await withTimeout(Promise.resolve(builder), 'create')
    if (error) throw new LeadsServiceError(error.message)
    if (data) return rowToDeal(data)
    return deal
  },

  async updateStage(id: string, stage: DealStage): Promise<void> {
    if (!supabase) return
    const now = new Date().toISOString().slice(0, 10)
    const { error } = await withTimeout(
      supabase.from('us_leads').update({ stage, updated_at: now }).eq('id', id),
      'updateStage',
    )
    if (error) throw new LeadsServiceError(error.message)
  },

  async update(id: string, updates: Partial<Deal>): Promise<void> {
    if (!supabase) return
    const now = new Date().toISOString().slice(0, 10)
    const { error } = await withTimeout(
      supabase.from('us_leads').update({ ...updates, updated_at: now }).eq('id', id),
      'update',
    )
    if (error) throw new LeadsServiceError(error.message)
  },

  async delete(id: string): Promise<void> {
    if (!supabase) return
    // `.select()` returns the rows actually removed. PostgREST returns 200/204
    // with zero rows when an RLS DELETE policy filters the row out, so without
    // this we'd report success on a silent no-op. Treat 0 rows as a hard
    // failure so the UI never claims a lead was deleted when it wasn't.
    const { data, error } = await withTimeout(
      supabase.from('us_leads').delete().eq('id', id).select('id'),
      'delete',
    )
    if (error) throw new LeadsServiceError(error.message)
    if (!data || data.length === 0) {
      throw new LeadsServiceError(
        'Lead could not be deleted — you may not have permission to remove it.',
      )
    }
  },

  subscribe(
    repId: string | undefined,
    onChanged: (deals: Deal[]) => void,
  ): RealtimeChannel | null {
    if (!supabase) return null
    // Channel name must be unique per subscription — otherwise mounting a second
    // page that subscribes (e.g. Leads + LeadDetail at the same time) collides
    // with the first and removeChannel from one unmount kills the other's stream.
    const channelName = `us_leads_realtime_${repId ?? 'all'}_${Math.random().toString(36).slice(2, 10)}`
    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        // When scoped to a rep, only react to that rep's rows server-side
        // instead of refetching all reps' leads on every global change.
        { event: '*', schema: 'public', table: 'us_leads', ...(repId ? { filter: `rep_id=eq.${repId}` } : {}) },
        () => {
          usLeadsService.list(repId).then(onChanged).catch(() => {})
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
