export type DealStage = 'prospecting' | 'contacted' | 'demo_scheduled' | 'proposal_sent' | 'negotiation' | 'closed_won' | 'closed_lost'

export interface Deal {
  id: string
  business_name: string
  contact_name: string
  contact_email: string
  contact_phone: string
  vertical: string
  stage: DealStage
  monthly_value: number
  commission_rate: number
  expected_close_date: string
  notes: string
  created_at: string
  updated_at: string
}

export interface Commission {
  id: string
  client_name: string
  gross_amount: number
  commission_rate: number
  commission_amount: number
  status: 'pending' | 'earned' | 'paid' | 'disputed'
  source_type: string
  created_at: string
}

export interface SalesClient {
  id: string
  business_name: string
  contact_name: string
  contact_email: string
  vertical: string
  plan: string
  monthly_revenue: number
  commission_rate: number
  assigned_at: string
  is_active: boolean
  pos_provider: string | null
  pos_connected: boolean
}

export interface SalesOverview {
  total_deals: number
  pipeline_value: number
  closed_this_month: number
  monthly_commission_earned: number
  total_earned: number
  total_paid: number
  pending_payout: number
  active_clients: number
  conversion_rate: number
}

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

function daysFromNow(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

const DEMO_DEALS: Deal[] = []

const DEMO_COMMISSIONS: Commission[] = []

const DEMO_CLIENTS: SalesClient[] = []

function delay<T>(data: T, ms = 300): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(data), ms + Math.random() * 200))
}

export const canadaSalesDemoData = {
  overview: (): Promise<SalesOverview> => {
    const activePipeline = DEMO_DEALS.filter(d => !['closed_won', 'closed_lost'].includes(d.stage))
    const closedWon = DEMO_DEALS.filter(d => d.stage === 'closed_won')
    const allDeals = DEMO_DEALS.filter(d => d.stage !== 'closed_lost')
    const totalEarned = DEMO_COMMISSIONS.reduce((s, c) => s + c.commission_amount, 0)
    const totalPaid = DEMO_COMMISSIONS.filter(c => c.status === 'paid').reduce((s, c) => s + c.commission_amount, 0)

    return delay({
      total_deals: activePipeline.length,
      pipeline_value: activePipeline.reduce((s, d) => s + d.monthly_value, 0),
      closed_this_month: closedWon.length,
      monthly_commission_earned: DEMO_COMMISSIONS.filter(c => c.status === 'earned').reduce((s, c) => s + c.commission_amount, 0),
      total_earned: totalEarned,
      total_paid: totalPaid,
      pending_payout: totalEarned - totalPaid,
      active_clients: DEMO_CLIENTS.filter(c => c.is_active).length,
      conversion_rate: Math.round((closedWon.length / allDeals.length) * 100),
    })
  },

  deals: (): Promise<Deal[]> => delay([...DEMO_DEALS]),

  commissions: (): Promise<Commission[]> => delay([...DEMO_COMMISSIONS].sort((a, b) => b.created_at.localeCompare(a.created_at))),

  clients: (): Promise<SalesClient[]> => delay([...DEMO_CLIENTS]),
}

export const STAGE_CONFIG: Record<DealStage, { label: string; color: string; bg: string; border: string }> = {
  prospecting:    { label: 'Prospecting',     color: '#A1A1A8', bg: '#A1A1A8/10', border: '#A1A1A8/20' },
  contacted:      { label: 'Contacted',       color: '#1A8FD6', bg: '#1A8FD6/10', border: '#1A8FD6/20' },
  demo_scheduled: { label: 'Demo Scheduled',  color: '#7C5CFF', bg: '#7C5CFF/10', border: '#7C5CFF/20' },
  proposal_sent:  { label: 'Proposal Sent',   color: '#F59E0B', bg: '#F59E0B/10', border: '#F59E0B/20' },
  negotiation:    { label: 'Negotiation',     color: '#F97316', bg: '#F97316/10', border: '#F97316/20' },
  closed_won:     { label: 'Closed Won',      color: '#17C5B0', bg: '#17C5B0/10', border: '#17C5B0/20' },
  closed_lost:    { label: 'Closed Lost',     color: '#EF4444', bg: '#EF4444/10', border: '#EF4444/20' },
}

export const STAGE_ORDER: DealStage[] = ['prospecting', 'contacted', 'demo_scheduled', 'proposal_sent', 'negotiation', 'closed_won', 'closed_lost']
