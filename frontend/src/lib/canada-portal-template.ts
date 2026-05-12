/**
 * Canada Portal Template — canonical configuration for all Canadian sales accounts.
 *
 * Every new Canada rep account inherits these defaults. To change behavior
 * portal-wide, update this file. Individual overrides are not supported —
 * consistency across reps is the goal.
 */

export const CANADA_PORTAL_TEMPLATE = {
  id: 'canada-v1',
  name: 'Canada Sales Portal',
  currency: 'CAD',
  currencySymbol: 'CA$',
  locale: 'en-CA',
  taxLabel: 'HST/GST',
  taxRate: 0.13,

  signingAuthority: {
    name: 'Aidan Pierce',
    title: 'Founder & CEO',
    company: 'Meridian AI Business Solutions',
  },

  pipeline: {
    stages: [
      { key: 'proposal_shown', label: 'Proposal Shown', step: 1 },
      { key: 'customer_checkout', label: 'Customer Checkout', step: 2 },
      { key: 'pos_connected', label: 'POS Connected', step: 3 },
      { key: 'customer_walkthrough', label: 'Customer Walkthrough', step: 4 },
    ] as const,
    lostStage: 'closed_lost' as const,
    totalSteps: 4,
  },

  pricing: {
    minMonthly: 350,
    maxMonthly: 1400,
    step: 50,
    defaultMonthly: 500,
    defaultCommissionRate: 70,
    plans: [
      { name: 'Standard', minPrice: 0 },
      { name: 'Premium', minPrice: 500 },
      { name: 'Command', minPrice: 1000 },
    ] as const,
  },

  sla: {
    enabled: true,
    pipedaRequired: true,
    quebecLaw25Provinces: ['qc', 'quebec', 'québec'],
    initialTermMonths: 12,
    renewalTermMonths: 12,
    noticePeriodDays: 30,
    availabilityTarget: 99.5,
    dataProcessingMinutes: 60,
  },

  invoice: {
    enabled: true,
    prefix: 'MCA',
    recurring: true,
    squareCheckout: true,
    qrCodeEnabled: true,
  },

  customerAccount: {
    enabled: true,
    walkthroughEnabled: true,
    loginPath: '/canada/login',
    dashboardPath: '/canada/dashboard',
    portalPath: '/canada/portal',
  },

  posIntegration: {
    verificationRequired: true,
    supportedSystems: [
      'Square', 'Clover', 'Toast', 'Moneris', 'Lightspeed',
      'Shopify POS', 'TouchBistro', 'Revel', 'Heartland', 'Aloha',
      'NCR Silver', 'SpotOn', 'Helcim', 'Dejavoo', 'Poynt',
      'Payanywhere', 'SumUp', 'iZettle', 'Vend', 'Hike POS',
      'Epos Now', 'Lavu', 'Upserve', 'Talech', 'PayPal Zettle',
      'Stripe Terminal',
    ],
  },

  provinces: [
    'Alberta', 'British Columbia', 'Manitoba', 'New Brunswick',
    'Newfoundland and Labrador', 'Northwest Territories', 'Nova Scotia',
    'Nunavut', 'Ontario', 'Prince Edward Island', 'Quebec',
    'Saskatchewan', 'Yukon',
  ],

  verticals: [
    'Restaurant', 'Smoke Shop', 'Cafe', 'Bar', 'Food Truck',
    'Salon', 'Boutique', 'Convenience Store', 'Other',
  ],

  leadSources: [
    'Referral', 'Cold Call', 'Walk-in', 'Social Media',
    'Website', 'Trade Show', 'Partner', 'Other',
  ],

  branding: {
    primaryColor: '#00d4aa',
    backgroundColor: '#0a0f0d',
    cardColor: '#0f1512',
    borderColor: '#1a2420',
    textColor: '#e8ede8',
    mutedColor: '#6b7a74',
  },
} as const

export type CanadaPortalTemplate = typeof CANADA_PORTAL_TEMPLATE

export function getPlanName(monthlyPrice: number): string {
  const plans = CANADA_PORTAL_TEMPLATE.pricing.plans
  for (let i = plans.length - 1; i >= 0; i--) {
    if (monthlyPrice >= plans[i].minPrice) return plans[i].name
  }
  return plans[0].name
}

export function isQuebecProvince(province: string): boolean {
  const p = province.toLowerCase().trim()
  return (CANADA_PORTAL_TEMPLATE.sla.quebecLaw25Provinces as readonly string[]).includes(p)
}

export function formatCadPrice(dollars: number): string {
  return `${CANADA_PORTAL_TEMPLATE.currencySymbol}${dollars.toLocaleString(CANADA_PORTAL_TEMPLATE.locale)}`
}

export function getStageStep(stage: string): number {
  const found = CANADA_PORTAL_TEMPLATE.pipeline.stages.find(s => s.key === stage)
  if (found) return found.step
  if (stage === CANADA_PORTAL_TEMPLATE.pipeline.lostStage) return 0
  return 1
}

export function getStageLabel(stage: string): string {
  const found = CANADA_PORTAL_TEMPLATE.pipeline.stages.find(s => s.key === stage)
  return found?.label ?? stage
}

export function getNextStage(currentStage: string): string | null {
  const stages = CANADA_PORTAL_TEMPLATE.pipeline.stages
  const idx = stages.findIndex(s => s.key === currentStage)
  if (idx >= 0 && idx < stages.length - 1) return stages[idx + 1].key
  return null
}
