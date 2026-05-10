import { supabase } from './supabase'
import type { Deal, DealStage } from './canada-sales-demo-data'

const STORAGE_KEY = 'meridian_canada_leads'

function loadLocal(): Deal[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function saveLocal(deals: Deal[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(deals))
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
    commission_rate: Number(row.commission_rate) || 70,
    expected_close_date: (row.expected_close_date as string) || '',
    notes: (row.notes as string) || '',
    source: (row.source as string) || '',
    city: (row.city as string) || '',
    province: (row.province as string) || '',
    created_at: row.created_at as string,
    updated_at: row.updated_at as string,
  }
}

export const canadaLeadsService = {
  async list(): Promise<Deal[]> {
    if (supabase) {
      const { data, error } = await supabase
        .from('canada_leads')
        .select('*')
        .order('created_at', { ascending: false })
      if (!error && data) return data.map(rowToDeal)
    }
    return loadLocal()
  },

  async getById(id: string): Promise<Deal | null> {
    if (supabase) {
      const { data, error } = await supabase
        .from('canada_leads')
        .select('*')
        .eq('id', id)
        .single()
      if (!error && data) return rowToDeal(data)
    }
    return loadLocal().find(d => d.id === id) ?? null
  },

  async create(deal: Deal): Promise<Deal> {
    if (supabase) {
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
      if (!error && data) return rowToDeal(data)
    }
    const all = loadLocal()
    all.unshift(deal)
    saveLocal(all)
    return deal
  },

  async updateStage(id: string, stage: DealStage): Promise<void> {
    const now = new Date().toISOString().slice(0, 10)
    if (supabase) {
      await supabase
        .from('canada_leads')
        .update({ stage, updated_at: now })
        .eq('id', id)
    }
    const all = loadLocal()
    const idx = all.findIndex(d => d.id === id)
    if (idx >= 0) {
      all[idx].stage = stage
      all[idx].updated_at = now
      saveLocal(all)
    }
  },

  async update(id: string, updates: Partial<Deal>): Promise<void> {
    const now = new Date().toISOString().slice(0, 10)
    if (supabase) {
      await supabase
        .from('canada_leads')
        .update({ ...updates, updated_at: now })
        .eq('id', id)
    }
    const all = loadLocal()
    const idx = all.findIndex(d => d.id === id)
    if (idx >= 0) {
      all[idx] = { ...all[idx], ...updates, updated_at: now }
      saveLocal(all)
    }
  },

  async delete(id: string): Promise<void> {
    if (supabase) {
      await supabase.from('canada_leads').delete().eq('id', id)
    }
    const all = loadLocal().filter(d => d.id !== id)
    saveLocal(all)
  },
}
