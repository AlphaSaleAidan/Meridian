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
  source?: string
  city?: string
  province?: string
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
  const d = new Date(); d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

function daysFromNow(n: number): string {
  const d = new Date(); d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

const DEMO_DEALS: Deal[] = [
  {
    id: uuid(), business_name: 'Golden Dragon Dim Sum', contact_name: 'Kevin Lau', contact_email: 'kevin@goldendragon.ca', contact_phone: '(604) 555-2345',
    vertical: 'Restaurant', stage: 'prospecting', monthly_value: 685, commission_rate: 70, expected_close_date: daysFromNow(21), notes: 'High-volume dim sum spot in Richmond. 4 POS terminals, wants inventory tracking.', source: 'Referral', city: 'Richmond', province: 'BC', created_at: daysAgo(2), updated_at: daysAgo(1),
  },
  {
    id: uuid(), business_name: 'Cloud Nine Vape YVR', contact_name: 'Marcus Gill', contact_email: 'marcus@cloudninevape.ca', contact_phone: '(604) 555-3456',
    vertical: 'Smoke Shop', stage: 'contacted', monthly_value: 500, commission_rate: 70, expected_close_date: daysFromNow(14), notes: 'Currently on Clover. Wants anomaly detection for theft. 2 Vancouver locations.', source: 'Cold Call', city: 'Vancouver', province: 'BC', created_at: daysAgo(5), updated_at: daysAgo(3),
  },
  {
    id: uuid(), business_name: 'Kensington Coffee House', contact_name: 'Sarah Olsen', contact_email: 'sarah@kensingtoncoffee.ca', contact_phone: '(403) 555-4567',
    vertical: 'Café', stage: 'demo_scheduled', monthly_value: 343, commission_rate: 70, expected_close_date: daysFromNow(7), notes: 'Demo set for Thursday 2pm MST. Interested in predictive ordering for pastry inventory.', source: 'Website', city: 'Calgary', province: 'AB', created_at: daysAgo(8), updated_at: daysAgo(1),
  },
  {
    id: uuid(), business_name: 'Queen West Threads', contact_name: 'Priya Patel', contact_email: 'priya@queenwestthreads.ca', contact_phone: '(416) 555-5678',
    vertical: 'Boutique', stage: 'proposal_sent', monthly_value: 500, commission_rate: 70, expected_close_date: daysFromNow(5), notes: 'Sent Premium tier proposal. Owner reviewing with business partner.', source: 'Referral', city: 'Toronto', province: 'ON', created_at: daysAgo(12), updated_at: daysAgo(2),
  },
  {
    id: uuid(), business_name: 'The Pilot Taphouse', contact_name: 'David Fong', contact_email: 'david@pilottaphouse.ca', contact_phone: '(416) 555-6789',
    vertical: 'Bar', stage: 'negotiation', monthly_value: 1000, commission_rate: 70, expected_close_date: daysFromNow(3), notes: 'Wants camera intelligence. 3 patios. Very close to signing.', source: 'Event', city: 'Toronto', province: 'ON', created_at: daysAgo(15), updated_at: daysAgo(0),
  },
  {
    id: uuid(), business_name: 'Chez Benny Poutine', contact_name: 'Benoît Tremblay', contact_email: 'benoit@chezbenny.ca', contact_phone: '(514) 555-7890',
    vertical: 'Restaurant', stage: 'closed_won', monthly_value: 343, commission_rate: 70, expected_close_date: daysAgo(2), notes: 'Signed! Onboarding started. Moneris integration in progress.', source: 'Referral', city: 'Montreal', province: 'QC', created_at: daysAgo(20), updated_at: daysAgo(2),
  },
  {
    id: uuid(), business_name: 'Lux Hair Studio', contact_name: 'Tanya Chen', contact_email: 'tanya@luxhair.ca', contact_phone: '(604) 555-8901',
    vertical: 'Salon', stage: 'closed_won', monthly_value: 500, commission_rate: 70, expected_close_date: daysAgo(10), notes: 'Active client. POS connected via Square Canada. First commission earned.', source: 'Website', city: 'Vancouver', province: 'BC', created_at: daysAgo(30), updated_at: daysAgo(10),
  },
  {
    id: uuid(), business_name: 'Maple Quick Mart', contact_name: 'Ali Farah', contact_email: 'ali@maplequickmart.ca', contact_phone: '(905) 555-9012',
    vertical: 'Convenience Store', stage: 'closed_lost', monthly_value: 685, commission_rate: 70, expected_close_date: daysAgo(5), notes: 'Went with competitor. Price was the deciding factor — revisit in 6 months.', source: 'Cold Call', city: 'Mississauga', province: 'ON', created_at: daysAgo(25), updated_at: daysAgo(5),
  },
  {
    id: uuid(), business_name: 'Taco Madre', contact_name: 'Maria Santos', contact_email: 'maria@tacomadre.ca', contact_phone: '(403) 555-0123',
    vertical: 'Restaurant', stage: 'prospecting', monthly_value: 500, commission_rate: 70, expected_close_date: daysFromNow(28), notes: 'Referral from Chez Benny. First call scheduled for next week.', source: 'Referral', city: 'Calgary', province: 'AB', created_at: daysAgo(1), updated_at: daysAgo(0),
  },
  {
    id: uuid(), business_name: 'Byward Smoke Co.', contact_name: 'Kyle Bennett', contact_email: 'kyle@bywardsmoke.ca', contact_phone: '(613) 555-1122',
    vertical: 'Smoke Shop', stage: 'demo_scheduled', monthly_value: 343, commission_rate: 70, expected_close_date: daysFromNow(10), notes: 'Demo next Tuesday. Interested in anomaly detection for high-value inventory.', source: 'Website', city: 'Ottawa', province: 'ON', created_at: daysAgo(6), updated_at: daysAgo(1),
  },
]

const DEMO_COMMISSIONS: Commission[] = [
  { id: uuid(), client_name: 'Lux Hair Studio', gross_amount: 1536, commission_rate: 70, commission_amount: 1075, status: 'paid', source_type: 'square_payment', created_at: daysAgo(30) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Lux Hair Studio', gross_amount: 1343, commission_rate: 70, commission_amount: 940, status: 'paid', source_type: 'square_payment', created_at: daysAgo(23) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Chez Benny Poutine', gross_amount: 877, commission_rate: 70, commission_amount: 614, status: 'earned', source_type: 'moneris_payment', created_at: daysAgo(5) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Lux Hair Studio', gross_amount: 1440, commission_rate: 70, commission_amount: 1008, status: 'earned', source_type: 'square_payment', created_at: daysAgo(16) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Chez Benny Poutine', gross_amount: 987, commission_rate: 70, commission_amount: 691, status: 'earned', source_type: 'moneris_payment', created_at: daysAgo(2) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Lux Hair Studio', gross_amount: 1220, commission_rate: 70, commission_amount: 854, status: 'pending', source_type: 'square_payment', created_at: daysAgo(1) + 'T10:00:00Z' },
]

const DEMO_CLIENTS: SalesClient[] = [
  { id: uuid(), business_name: 'Lux Hair Studio', contact_name: 'Tanya Chen', contact_email: 'tanya@luxhair.ca', vertical: 'Salon', plan: 'premium', monthly_revenue: 500, commission_rate: 70, assigned_at: daysAgo(30), is_active: true, pos_provider: 'square', pos_connected: true },
  { id: uuid(), business_name: 'Chez Benny Poutine', contact_name: 'Benoît Tremblay', contact_email: 'benoit@chezbenny.ca', vertical: 'Restaurant', plan: 'standard', monthly_revenue: 343, commission_rate: 70, assigned_at: daysAgo(2), is_active: true, pos_provider: 'moneris', pos_connected: true },
]

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
      conversion_rate: allDeals.length > 0 ? Math.round((closedWon.length / allDeals.length) * 100) : 0,
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
