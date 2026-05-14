import { supabase } from './supabase'
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
  }
}

export class LeadsServiceError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'LeadsServiceError'
  }
}

export const canadaLeadsService = {
  async list(): Promise<Deal[]> {
    if (!supabase) return []
    const { data, error } = await supabase
      .from('canada_leads')
      .select('*')
      .order('created_at', { ascending: false })
    if (error) throw new LeadsServiceError(error.message)
    if (!data) return []
    return data.map(rowToDeal)
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

  async create(deal: Deal): Promise<Deal> {
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
      })
      .select()
      .single()
    if (error) throw new Error(error.message)
    if (data) return rowToDeal(data)
    return deal
  },

  async updateStage(id: string, stage: DealStage): Promise<void> {
    if (!supabase) return
    const now = new Date().toISOString().slice(0, 10)
    await supabase
      .from('canada_leads')
      .update({ stage, updated_at: now })
      .eq('id', id)
  },

  async update(id: string, updates: Partial<Deal>): Promise<void> {
    if (!supabase) return
    const now = new Date().toISOString().slice(0, 10)
    const { error } = await supabase
      .from('canada_leads')
      .update({ ...updates, updated_at: now })
      .eq('id', id)
    if (error) throw new LeadsServiceError(error.message)
  },

  async delete(id: string): Promise<void> {
    if (!supabase) return
    await supabase.from('canada_leads').delete().eq('id', id)
  },
}
