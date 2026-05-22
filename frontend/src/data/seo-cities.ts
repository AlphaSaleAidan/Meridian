export interface CityData {
  city: string
  region: string
  slug: string
  country: 'CA' | 'US'
  currency: string
  currencySymbol: string
  nearby: string[]
}

export interface IndustryData {
  slug: string
  label: string
  plural: string
  icon: string
  painPoints: string[]
  features: string[]
}

export const INDUSTRIES: IndustryData[] = [
  {
    slug: 'restaurants',
    label: 'Restaurant',
    plural: 'Restaurants',
    icon: 'UtensilsCrossed',
    painPoints: [
      'Thin margins with no visibility into what drives profit',
      'Manual spreadsheet tracking that misses trends',
      'Staffing decisions based on gut feeling, not data',
    ],
    features: [
      'Revenue forecasting (7/30/90-day)',
      'Menu engineering and product mix analysis',
      'Peak hours and staffing optimization',
      'Anomaly detection for voids and refunds',
      'Customer segmentation and retention',
      'AI insights in plain English',
    ],
  },
  {
    slug: 'coffee-shops',
    label: 'Coffee Shop',
    plural: 'Coffee Shops',
    icon: 'Coffee',
    painPoints: [
      'No visibility into drink-level margins',
      'Inconsistent rush hour staffing',
      'Loyalty spend with no measurable return',
    ],
    features: [
      'Revenue per hour tracking',
      'Product mix and margin analysis',
      'Peak rush period optimization',
      'Barista performance metrics',
      'Customer frequency tracking',
      'Inventory demand forecasting',
    ],
  },
  {
    slug: 'auto-shops',
    label: 'Auto Shop',
    plural: 'Auto Shops',
    icon: 'Wrench',
    painPoints: [
      'No visibility into which services are most profitable',
      'Scheduling inefficiency and technician idle time',
      'Customer retention is a mystery',
    ],
    features: [
      'Service profitability analysis',
      'Technician productivity tracking',
      'Appointment demand forecasting',
      'Customer retention analytics',
      'Parts inventory optimization',
      'Revenue trend analysis',
    ],
  },
  {
    slug: 'fast-food',
    label: 'Fast Food',
    plural: 'Fast Food Restaurants',
    icon: 'Zap',
    painPoints: [
      'Drive-through bottlenecks are invisible',
      'Food waste from inaccurate demand forecasting',
      'Labor scheduling based on guesswork',
    ],
    features: [
      'Order volume forecasting',
      'Peak period analytics',
      'Speed of service optimization',
      'Waste reduction insights',
      'Labor cost optimization',
      'Menu performance analysis',
    ],
  },
]

export const CANADIAN_CITIES: CityData[] = [
  { city: 'Toronto', region: 'ON', slug: 'toronto-on', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['mississauga-on', 'brampton-on', 'markham-on', 'hamilton-on'] },
  { city: 'Vancouver', region: 'BC', slug: 'vancouver-bc', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['surrey-bc', 'victoria-bc', 'calgary-ab'] },
  { city: 'Montreal', region: 'QC', slug: 'montreal-qc', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['laval-qc', 'quebec-city-qc', 'ottawa-on'] },
  { city: 'Calgary', region: 'AB', slug: 'calgary-ab', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['edmonton-ab', 'vancouver-bc', 'saskatoon-sk'] },
  { city: 'Ottawa', region: 'ON', slug: 'ottawa-on', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['montreal-qc', 'toronto-on', 'kingston-on'] },
  { city: 'Edmonton', region: 'AB', slug: 'edmonton-ab', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['calgary-ab', 'saskatoon-sk', 'winnipeg-mb'] },
  { city: 'Winnipeg', region: 'MB', slug: 'winnipeg-mb', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['saskatoon-sk', 'regina-sk', 'edmonton-ab'] },
  { city: 'Quebec City', region: 'QC', slug: 'quebec-city-qc', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['montreal-qc', 'ottawa-on', 'halifax-ns'] },
  { city: 'Hamilton', region: 'ON', slug: 'hamilton-on', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['toronto-on', 'kitchener-on', 'london-on'] },
  { city: 'Kitchener', region: 'ON', slug: 'kitchener-on', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['hamilton-on', 'london-on', 'toronto-on'] },
  { city: 'Halifax', region: 'NS', slug: 'halifax-ns', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['quebec-city-qc', 'montreal-qc'] },
  { city: 'London', region: 'ON', slug: 'london-on', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['kitchener-on', 'hamilton-on', 'toronto-on'] },
  { city: 'Victoria', region: 'BC', slug: 'victoria-bc', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['vancouver-bc', 'surrey-bc'] },
  { city: 'Saskatoon', region: 'SK', slug: 'saskatoon-sk', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['regina-sk', 'winnipeg-mb', 'edmonton-ab'] },
  { city: 'Regina', region: 'SK', slug: 'regina-sk', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['saskatoon-sk', 'winnipeg-mb', 'calgary-ab'] },
  { city: 'Mississauga', region: 'ON', slug: 'mississauga-on', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['toronto-on', 'brampton-on', 'hamilton-on'] },
  { city: 'Brampton', region: 'ON', slug: 'brampton-on', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['toronto-on', 'mississauga-on', 'markham-on'] },
  { city: 'Markham', region: 'ON', slug: 'markham-on', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['toronto-on', 'brampton-on', 'mississauga-on'] },
  { city: 'Surrey', region: 'BC', slug: 'surrey-bc', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['vancouver-bc', 'victoria-bc'] },
  { city: 'Laval', region: 'QC', slug: 'laval-qc', country: 'CA', currency: 'CAD', currencySymbol: 'CA$', nearby: ['montreal-qc', 'quebec-city-qc', 'ottawa-on'] },
]

export const US_CITIES: CityData[] = [
  { city: 'New York', region: 'NY', slug: 'new-york-ny', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['philadelphia-pa', 'newark-nj'] },
  { city: 'Los Angeles', region: 'CA', slug: 'los-angeles-ca', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['san-diego-ca', 'phoenix-az', 'las-vegas-nv'] },
  { city: 'Chicago', region: 'IL', slug: 'chicago-il', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['minneapolis-mn', 'detroit-mi'] },
  { city: 'Houston', region: 'TX', slug: 'houston-tx', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['dallas-tx', 'san-antonio-tx', 'austin-tx'] },
  { city: 'Phoenix', region: 'AZ', slug: 'phoenix-az', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['los-angeles-ca', 'las-vegas-nv', 'denver-co'] },
  { city: 'Philadelphia', region: 'PA', slug: 'philadelphia-pa', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['new-york-ny', 'baltimore-md'] },
  { city: 'San Antonio', region: 'TX', slug: 'san-antonio-tx', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['austin-tx', 'houston-tx', 'dallas-tx'] },
  { city: 'Dallas', region: 'TX', slug: 'dallas-tx', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['houston-tx', 'austin-tx', 'san-antonio-tx'] },
  { city: 'Austin', region: 'TX', slug: 'austin-tx', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['san-antonio-tx', 'houston-tx', 'dallas-tx'] },
  { city: 'Seattle', region: 'WA', slug: 'seattle-wa', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['portland-or', 'denver-co'] },
  { city: 'Denver', region: 'CO', slug: 'denver-co', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['phoenix-az', 'salt-lake-city-ut', 'minneapolis-mn'] },
  { city: 'Nashville', region: 'TN', slug: 'nashville-tn', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['atlanta-ga', 'raleigh-nc'] },
  { city: 'Miami', region: 'FL', slug: 'miami-fl', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['atlanta-ga', 'nashville-tn'] },
  { city: 'Atlanta', region: 'GA', slug: 'atlanta-ga', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['nashville-tn', 'raleigh-nc', 'miami-fl'] },
  { city: 'Portland', region: 'OR', slug: 'portland-or', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['seattle-wa', 'denver-co'] },
  { city: 'Las Vegas', region: 'NV', slug: 'las-vegas-nv', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['los-angeles-ca', 'phoenix-az', 'denver-co'] },
  { city: 'Minneapolis', region: 'MN', slug: 'minneapolis-mn', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['chicago-il', 'denver-co'] },
  { city: 'San Diego', region: 'CA', slug: 'san-diego-ca', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['los-angeles-ca', 'phoenix-az'] },
  { city: 'Salt Lake City', region: 'UT', slug: 'salt-lake-city-ut', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['denver-co', 'phoenix-az', 'las-vegas-nv'] },
  { city: 'Raleigh', region: 'NC', slug: 'raleigh-nc', country: 'US', currency: 'USD', currencySymbol: '$', nearby: ['atlanta-ga', 'nashville-tn', 'philadelphia-pa'] },
]

export const ALL_CITIES = [...CANADIAN_CITIES, ...US_CITIES]

export function findCity(slug: string): CityData | undefined {
  return ALL_CITIES.find(c => c.slug === slug)
}

export function findIndustry(slug: string): IndustryData | undefined {
  return INDUSTRIES.find(i => i.slug === slug)
}
