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

const VERTICALS = ['Restaurant', 'Smoke Shop', 'Café', 'Bar', 'Food Truck', 'Salon', 'Boutique', 'Convenience Store']
const PLANS = ['trial', 'insights', 'optimize', 'command']

const DEMO_DEALS: Deal[] = [
  {
    id: uuid(), business_name: 'Lucky Dragon Kitchen', contact_name: 'James Chen', contact_email: 'james@luckydragon.com', contact_phone: '(555) 234-5678',
    vertical: 'Restaurant', stage: 'prospecting', monthly_value: 28000, commission_rate: 70, expected_close_date: daysFromNow(21), notes: 'High-volume Chinese restaurant, 3 POS terminals. Interested in inventory tracking.', created_at: daysAgo(2), updated_at: daysAgo(1),
  },
  {
    id: uuid(), business_name: 'Velvet Smoke Lounge', contact_name: 'Marcus Reed', contact_email: 'marcus@velvetsmoke.com', contact_phone: '(555) 345-6789',
    vertical: 'Smoke Shop', stage: 'contacted', monthly_value: 15000, commission_rate: 70, expected_close_date: daysFromNow(14), notes: 'Wants to replace old POS. Currently on Clover. 2 locations.', created_at: daysAgo(5), updated_at: daysAgo(3),
  },
  {
    id: uuid(), business_name: 'Sunrise Coffee Co.', contact_name: 'Amy Torres', contact_email: 'amy@sunrisecoffee.com', contact_phone: '(555) 456-7890',
    vertical: 'Café', stage: 'demo_scheduled', monthly_value: 12000, commission_rate: 70, expected_close_date: daysFromNow(7), notes: 'Demo set for Thursday 2pm. They want to see the forecasting feature.', created_at: daysAgo(8), updated_at: daysAgo(1),
  },
  {
    id: uuid(), business_name: 'Urban Threads Boutique', contact_name: 'Priya Sharma', contact_email: 'priya@urbanthreads.com', contact_phone: '(555) 567-8901',
    vertical: 'Boutique', stage: 'proposal_sent', monthly_value: 9500, commission_rate: 70, expected_close_date: daysFromNow(5), notes: 'Sent Optimize tier proposal. Waiting for owner sign-off.', created_at: daysAgo(12), updated_at: daysAgo(2),
  },
  {
    id: uuid(), business_name: 'The Rusty Nail Bar', contact_name: 'David Park', contact_email: 'david@rustynail.com', contact_phone: '(555) 678-9012',
    vertical: 'Bar', stage: 'negotiation', monthly_value: 22000, commission_rate: 70, expected_close_date: daysFromNow(3), notes: 'Very close to closing. 3 locations, high volume.', created_at: daysAgo(15), updated_at: daysAgo(0),
  },
  {
    id: uuid(), business_name: 'Fresh Bites Food Truck', contact_name: 'Carlos Ruiz', contact_email: 'carlos@freshbites.com', contact_phone: '(555) 789-0123',
    vertical: 'Food Truck', stage: 'closed_won', monthly_value: 8000, commission_rate: 70, expected_close_date: daysAgo(2), notes: 'Signed! Onboarding started. Square integration in progress.', created_at: daysAgo(20), updated_at: daysAgo(2),
  },
  {
    id: uuid(), business_name: 'Glamour Cuts Salon', contact_name: 'Tanya Williams', contact_email: 'tanya@glamourcuts.com', contact_phone: '(555) 890-1234',
    vertical: 'Salon', stage: 'closed_won', monthly_value: 11000, commission_rate: 70, expected_close_date: daysAgo(10), notes: 'Active client. POS connected. First commission earned.', created_at: daysAgo(30), updated_at: daysAgo(10),
  },
  {
    id: uuid(), business_name: 'Corner Mart Express', contact_name: 'Ali Hassan', contact_email: 'ali@cornermart.com', contact_phone: '(555) 901-2345',
    vertical: 'Convenience Store', stage: 'closed_lost', monthly_value: 18000, commission_rate: 70, expected_close_date: daysAgo(5), notes: 'Went with competitor. Price was the deciding factor.', created_at: daysAgo(25), updated_at: daysAgo(5),
  },
  {
    id: uuid(), business_name: 'Taco Loco', contact_name: 'Maria Gonzalez', contact_email: 'maria@tacoloco.com', contact_phone: '(555) 012-3456',
    vertical: 'Restaurant', stage: 'prospecting', monthly_value: 16000, commission_rate: 70, expected_close_date: daysFromNow(28), notes: 'Referral from Fresh Bites. First call scheduled for next week.', created_at: daysAgo(1), updated_at: daysAgo(0),
  },
  {
    id: uuid(), business_name: 'Cloud Nine Vape', contact_name: 'Kyle Bennett', contact_email: 'kyle@cloudnine.com', contact_phone: '(555) 111-2222',
    vertical: 'Smoke Shop', stage: 'demo_scheduled', monthly_value: 10000, commission_rate: 70, expected_close_date: daysFromNow(10), notes: 'Demo next Tuesday. Interested in anomaly detection for theft prevention.', created_at: daysAgo(6), updated_at: daysAgo(1),
  },
]

const DEMO_COMMISSIONS: Commission[] = [
  { id: uuid(), client_name: 'Glamour Cuts Salon', gross_amount: 1120000, commission_rate: 70, commission_amount: 784000, status: 'paid', source_type: 'square_payment', created_at: daysAgo(30) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Glamour Cuts Salon', gross_amount: 980000, commission_rate: 70, commission_amount: 686000, status: 'paid', source_type: 'square_payment', created_at: daysAgo(23) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Fresh Bites Food Truck', gross_amount: 640000, commission_rate: 70, commission_amount: 448000, status: 'earned', source_type: 'square_payment', created_at: daysAgo(5) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Glamour Cuts Salon', gross_amount: 1050000, commission_rate: 70, commission_amount: 735000, status: 'earned', source_type: 'square_payment', created_at: daysAgo(16) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Fresh Bites Food Truck', gross_amount: 720000, commission_rate: 70, commission_amount: 504000, status: 'earned', source_type: 'square_payment', created_at: daysAgo(2) + 'T10:00:00Z' },
  { id: uuid(), client_name: 'Glamour Cuts Salon', gross_amount: 890000, commission_rate: 70, commission_amount: 623000, status: 'pending', source_type: 'square_payment', created_at: daysAgo(1) + 'T10:00:00Z' },
]

const DEMO_CLIENTS: SalesClient[] = [
  { id: uuid(), business_name: 'Glamour Cuts Salon', contact_name: 'Tanya Williams', contact_email: 'tanya@glamourcuts.com', vertical: 'Salon', plan: 'optimize', monthly_revenue: 1050000, commission_rate: 70, assigned_at: daysAgo(30), is_active: true, pos_provider: 'square', pos_connected: true },
  { id: uuid(), business_name: 'Fresh Bites Food Truck', contact_name: 'Carlos Ruiz', contact_email: 'carlos@freshbites.com', vertical: 'Food Truck', plan: 'insights', monthly_revenue: 680000, commission_rate: 70, assigned_at: daysAgo(2), is_active: true, pos_provider: 'square', pos_connected: true },
]

function delay<T>(data: T, ms = 300): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(data), ms + Math.random() * 200))
}

export const salesDemoData = {
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
