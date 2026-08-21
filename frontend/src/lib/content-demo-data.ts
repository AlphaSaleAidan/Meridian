/**
 * Content System Demo Data — per business type
 *
 * Each demo business gets 1 example social media photo ad
 * plus a few other posts and rankings to fill out the dashboard.
 * No generation allowed in demo mode — these are static showcases.
 */

import { getActiveBusinessType, type BusinessType } from './demo-context'

export interface ContentCredits {
  balance: number
  lifetime_used: number
  free_granted: number
}

// Mirror of backend src/credits/costs.py — keep these in lockstep.
// If you change a number here, change it there too (and vice versa).
export const CREDIT_COSTS = {
  // Content
  social_post: 100,
  seo_article: 250,
  caption_only: 50,
  hashtags_only: 0,
  image_regen: 75,
  // Phone agent — billed per minute, rounded up to next 30s.
  phone_call_per_min: 50,
  // SMS responder — billed per direction. One exchange = 50 credits.
  sms_inbound: 20,
  sms_outbound: 30,
} as const

// Free credits granted on signup. Sized so a new merchant can run a
// meaningful demo (~20 min of calls or ~30 SMS exchanges) and close
// real orders before paying — see backend STARTER_GRANT.
export const STARTER_CREDIT_GRANT = 1000

// Dashboard surfaces a top-up nudge when balance falls below this.
export const LOW_BALANCE_THRESHOLD = 200

// pack_id keys must match backend src/credits/purchase.py PACKS dict.
export const CREDIT_PACKS = [
  { pack_id: 'starter', credits: 2000, priceUsd: 2, priceCad: 2.75, label: 'Starter' },
  { pack_id: 'popular', credits: 5000, priceUsd: 4.50, priceCad: 6.20, label: 'Popular', recommended: true },
  { pack_id: 'pro', credits: 15000, priceUsd: 12, priceCad: 16.50, label: 'Pro' },
  { pack_id: 'agency', credits: 50000, priceUsd: 35, priceCad: 48, label: 'Agency' },
] as const

export interface ContentDashboardData {
  brand: {
    business_name: string
    business_type: string
    content_tier: string
    ayrshare_connected_platforms: string[]
    voice_profile: {
      tone: string
      emoji_usage: string
      top_products: string[]
      keywords: string[]
    }
  } | null
  posts: ContentPost[]
  rankings: ContentRanking[]
  activeJobs: ContentJob[]
  credits: ContentCredits
}

export interface ContentPost {
  id: string
  post_type: 'social' | 'article' | 'video_brief' | 'gmb_post' | 'ad_creative'
  platform: string
  status: string
  title?: string
  hook?: string
  body?: string
  hashtags?: string[]
  call_to_action?: string
  image_url?: string
  video_url?: string
  target_keyword?: string
  secondary_keywords?: string[]
  meta_description?: string
  word_count?: number
  slug?: string
  scheduled_at?: string
  published_at?: string
  publish_url?: string
  pos_data_reference?: Record<string, unknown>
  created_at: string
}

export interface ContentRanking {
  keyword: string
  rank_position: number
  rank_change: number
  checked_at: string
  ai_citation_count: number
  ai_platforms_cited: string[]
}

export interface ContentJob {
  id: string
  job_type: string
  status: string
}

const now = new Date()
function daysAgo(n: number): string {
  const d = new Date(now)
  d.setDate(d.getDate() - n)
  return d.toISOString()
}

interface DemoBusiness {
  brand: ContentDashboardData['brand']
  post: ContentPost
  rankings: ContentRanking[]
}

const DEMO_BUSINESSES: Record<BusinessType, DemoBusiness> = {
  pizzeria: {
    brand: {
      business_name: "Tony's Pizzeria",
      business_type: 'pizzeria',
      content_tier: 'growth',
      ayrshare_connected_platforms: ['instagram', 'facebook', 'google_business'],
      voice_profile: {
        tone: 'friendly',
        emoji_usage: 'minimal',
        top_products: ['Large Pepperoni', 'Family Deal', 'Garlic Knots'],
        keywords: ['pizza delivery near me', 'best pizza', 'family deal'],
      },
    },
    post: {
      id: 'demo-pizzeria-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'Friday night: 41 deliveries, none of them late.',
      body: "Three drivers, one route, and the kitchen knows what is going out before it comes off the peel.\n\nFamily Deal is still the fastest thing to order and the easiest thing to feed four people with.",
      hashtags: ['#PizzaDelivery', '#FamilyDeal', '#TonysPizzeria', '#FridayNight'],
      call_to_action: 'Order for delivery — link in bio',
      pos_data_reference: { item: 'Family Deal', peak: '7:00 PM', deliveries: 41 },
      published_at: daysAgo(2),
      publish_url: 'https://instagram.com/p/demo',
      created_at: daysAgo(3),
    },
    rankings: [
      { keyword: 'pizza delivery near me', rank_position: 3, rank_change: 5, checked_at: daysAgo(0), ai_citation_count: 3, ai_platforms_cited: ['chatgpt', 'claude', 'perplexity'] },
      { keyword: 'best pizza', rank_position: 7, rank_change: 2, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
      { keyword: 'family deal pizza', rank_position: 5, rank_change: 4, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'claude'] },
      { keyword: 'late night pizza', rank_position: 11, rank_change: -1, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
    ],
  },

  barbershop: {
    brand: {
      business_name: 'The Fade Room',
      business_type: 'barbershop',
      content_tier: 'growth',
      ayrshare_connected_platforms: ['instagram', 'facebook', 'google_business'],
      voice_profile: {
        tone: 'confident',
        emoji_usage: 'minimal',
        top_products: ['Skin Fade', 'Cut & Beard', 'Matte Pomade'],
        keywords: ['barber near me', 'skin fade', 'walk in barber'],
      },
    },
    post: {
      id: 'demo-barbershop-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'Thursday evenings book out first. Here is why.',
      body: 'Four chairs, and the 5pm slot is the first one gone every week. If you want it, Thursday opens for booking on Sunday night.\n\nCut and beard, thirty-five minutes, out the door.',
      hashtags: ['#SkinFade', '#BarberLife', '#TheFadeRoom', '#FreshCut'],
      call_to_action: 'Book Thursday — link in bio',
      // No image_url: inventing an Unsplash photo id gives a broken tile, which
      // reads worse on a demo than a text post does.
      pos_data_reference: { item: 'Cut & Beard', peak_slot: '5:00 PM', day: 'Thursday' },
      published_at: daysAgo(2),
      publish_url: 'https://instagram.com/p/demo',
      created_at: daysAgo(3),
    },
    rankings: [
      { keyword: 'barber near me', rank_position: 3, rank_change: 4, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'perplexity'] },
      { keyword: 'skin fade', rank_position: 6, rank_change: 2, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
      { keyword: 'walk in barber', rank_position: 11, rank_change: -1, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
      { keyword: 'beard trim', rank_position: 8, rank_change: 3, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['chatgpt'] },
    ],
  },

  nails: {
    brand: {
      business_name: 'Lacquer Lash Bar',
      business_type: 'nails',
      content_tier: 'growth',
      ayrshare_connected_platforms: ['instagram', 'facebook', 'google_business'],
      voice_profile: {
        tone: 'polished',
        emoji_usage: 'moderate',
        top_products: ['Gel Manicure', 'Full Set', 'Lash Extensions'],
        keywords: ['nail salon near me', 'gel manicure', 'lash extensions'],
      },
    },
    post: {
      id: 'demo-nails-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'Fills booked back-to-back last week. Three slots left.',
      body: 'Two technicians, one lash bed, and a book that filled by Wednesday. If you are due for a fill, this week still has room on Friday afternoon.',
      hashtags: ['#GelManicure', '#LashExtensions', '#NailSalon', '#LacquerLash'],
      call_to_action: 'Book a fill — link in bio',
      // No image_url: inventing an Unsplash photo id gives a broken tile, which
      // reads worse on a demo than a text post does.
      pos_data_reference: { item: 'Fill', repeat_rate: '68%', day: 'Friday' },
      published_at: daysAgo(2),
      publish_url: 'https://instagram.com/p/demo',
      created_at: daysAgo(3),
    },
    rankings: [
      { keyword: 'nail salon near me', rank_position: 5, rank_change: 3, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'perplexity'] },
      { keyword: 'gel manicure', rank_position: 4, rank_change: 6, checked_at: daysAgo(0), ai_citation_count: 3, ai_platforms_cited: ['chatgpt', 'claude', 'perplexity'] },
      { keyword: 'lash extensions', rank_position: 9, rank_change: 1, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
      { keyword: 'acrylic full set', rank_position: 13, rank_change: -2, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
    ],
  },

  medspa: {
    brand: {
      business_name: 'Northline Aesthetics',
      business_type: 'medspa',
      content_tier: 'growth',
      ayrshare_connected_platforms: ['instagram', 'facebook', 'google_business'],
      voice_profile: {
        tone: 'clinical',
        emoji_usage: 'none',
        top_products: ['Facial', 'Injectables', 'Laser Session'],
        keywords: ['med spa near me', 'botox consultation', 'hydrafacial'],
      },
    },
    post: {
      id: 'demo-medspa-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'Consultations are free. Most of ours turn into a plan, not a sale.',
      body: 'Twenty minutes with our nurse injector, a look at what you actually want changed, and a written plan you can take away and think about.\n\nNo pressure to book anything on the day.',
      hashtags: ['#MedSpa', '#Aesthetics', '#SkinHealth', '#Northline'],
      call_to_action: 'Book a consultation — link in bio',
      // No image_url: inventing an Unsplash photo id gives a broken tile, which
      // reads worse on a demo than a text post does.
      pos_data_reference: { item: 'Consultation', conversion: '54%', window: '14 days' },
      published_at: daysAgo(2),
      publish_url: 'https://instagram.com/p/demo',
      created_at: daysAgo(3),
    },
    rankings: [
      { keyword: 'med spa near me', rank_position: 6, rank_change: 4, checked_at: daysAgo(0), ai_citation_count: 3, ai_platforms_cited: ['chatgpt', 'claude', 'perplexity'] },
      { keyword: 'botox consultation', rank_position: 8, rank_change: 2, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'perplexity'] },
      { keyword: 'hydrafacial', rank_position: 5, rank_change: 5, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['claude'] },
      { keyword: 'laser hair removal', rank_position: 14, rank_change: -3, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
    ],
  },

  detailing: {
    brand: {
      business_name: 'Apex Auto Detail',
      business_type: 'detailing',
      content_tier: 'growth',
      ayrshare_connected_platforms: ['instagram', 'facebook', 'google_business'],
      voice_profile: {
        tone: 'straightforward',
        emoji_usage: 'none',
        top_products: ['Full Detail', 'Ceramic Coating', 'Wash and Wax'],
        keywords: ['car detailing near me', 'ceramic coating', 'interior detail'],
      },
    },
    post: {
      id: 'demo-detailing-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'A ceramic coating is a two-day job. Here is what those two days buy you.',
      body: 'Decontamination, a paint correction pass, then the coating itself with a cure overnight. Three to five years of a finish that rinses clean instead of scrubbing clean.',
      hashtags: ['#CeramicCoating', '#AutoDetailing', '#PaintCorrection', '#ApexDetail'],
      call_to_action: 'Get a quote — link in bio',
      // No image_url: inventing an Unsplash photo id gives a broken tile, which
      // reads worse on a demo than a text post does.
      pos_data_reference: { item: 'Ceramic Coating', ticket: 'highest', share: '31%' },
      published_at: daysAgo(2),
      publish_url: 'https://instagram.com/p/demo',
      created_at: daysAgo(3),
    },
    rankings: [
      { keyword: 'car detailing near me', rank_position: 4, rank_change: 5, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'perplexity'] },
      { keyword: 'ceramic coating', rank_position: 7, rank_change: 3, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'claude'] },
      { keyword: 'interior detail', rank_position: 10, rank_change: 1, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
      { keyword: 'paint correction', rank_position: 12, rank_change: 2, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
    ],
  },

  mobile_detailing: {
    brand: {
      business_name: 'Roadside Shine Mobile',
      business_type: 'mobile_detailing',
      content_tier: 'growth',
      ayrshare_connected_platforms: ['instagram', 'facebook', 'google_business'],
      voice_profile: {
        tone: 'straightforward',
        emoji_usage: 'none',
        top_products: ['Interior and Exterior', 'Wash and Wax', 'Full Detail'],
        keywords: ['mobile detailing near me', 'car detailing at home', 'mobile car wash'],
      },
    },
    post: {
      id: 'demo-mobile_detailing-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'We come to your driveway. You do not move the car.',
      body: 'Water, power and everything else travels with the van. Book a window, leave the keys, and the car is done where it sits.\n\nWe cover the north side of the city six days a week.',
      hashtags: ['#MobileDetailing', '#CarCare', '#RoadsideShine', '#DetailingAtHome'],
      call_to_action: 'Book a window — link in bio',
      // No image_url: inventing an Unsplash photo id gives a broken tile, which
      // reads worse on a demo than a text post does.
      pos_data_reference: { item: 'Interior and Exterior', radius_km: 25, jobs_per_day: 4 },
      published_at: daysAgo(2),
      publish_url: 'https://instagram.com/p/demo',
      created_at: daysAgo(3),
    },
    rankings: [
      { keyword: 'mobile detailing near me', rank_position: 3, rank_change: 6, checked_at: daysAgo(0), ai_citation_count: 3, ai_platforms_cited: ['chatgpt', 'claude', 'perplexity'] },
      { keyword: 'car detailing at home', rank_position: 5, rank_change: 4, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
      { keyword: 'mobile car wash', rank_position: 9, rank_change: 2, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['chatgpt'] },
      { keyword: 'detailing prices', rank_position: 15, rank_change: -1, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
    ],
  },

  restaurant: {
    brand: {
      business_name: 'The Corner Bistro',
      business_type: 'restaurant',
      content_tier: 'growth',
      ayrshare_connected_platforms: ['instagram', 'facebook', 'google_business'],
      voice_profile: {
        tone: 'warm',
        emoji_usage: 'minimal',
        top_products: ['House Burger', 'Truffle Fries', 'Seasonal Cocktails'],
        keywords: ['best bistro downtown', 'farm to table restaurant', 'brunch near me'],
      },
    },
    post: {
      id: 'demo-restaurant-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'Your #1 seller drove 23% of Tuesday revenue.',
      body: 'The House Burger isn\'t just popular — it\'s carrying the week. Half-pound patty, aged cheddar, house-made aioli on a brioche bun. Our POS data shows it outsells everything else 3-to-1 on Tuesdays.\n\nCome taste why.',
      hashtags: ['#HouseBurger', '#BestBurger', '#CornerBistro', '#LocalEats', '#DowntownDining'],
      call_to_action: 'Reserve your table — link in bio',
      image_url: 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=400&h=400&fit=crop&q=80',
      pos_data_reference: { item: 'House Burger', revenue_share: '23%', day: 'Tuesday' },
      published_at: daysAgo(2),
      publish_url: 'https://instagram.com/p/demo',
      created_at: daysAgo(3),
    },
    rankings: [
      { keyword: 'best bistro downtown', rank_position: 4, rank_change: 3, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'perplexity'] },
      { keyword: 'farm to table restaurant', rank_position: 7, rank_change: 5, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
      { keyword: 'brunch near me', rank_position: 12, rank_change: -2, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
      { keyword: 'happy hour deals', rank_position: 9, rank_change: 6, checked_at: daysAgo(0), ai_citation_count: 3, ai_platforms_cited: ['chatgpt', 'claude', 'perplexity'] },
      { keyword: 'seasonal menu restaurant', rank_position: 6, rank_change: 4, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'claude'] },
    ],
  },

  coffee_shop: {
    brand: {
      business_name: 'Ember & Bloom Coffee',
      business_type: 'coffee_shop',
      content_tier: 'growth',
      ayrshare_connected_platforms: ['instagram', 'facebook'],
      voice_profile: {
        tone: 'cozy',
        emoji_usage: 'moderate',
        top_products: ['Oat Milk Latte', 'Almond Croissant', 'Cold Brew Flight'],
        keywords: ['best coffee shop', 'oat milk latte', 'local roaster'],
      },
    },
    post: {
      id: 'demo-coffee-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'Your morning ritual, perfected.',
      body: 'The Oat Milk Latte accounts for 34% of all morning orders — and we get it. Single-origin Ethiopian beans, house-made oat milk, a hint of vanilla. It\'s the reason 200+ regulars come back every single week.\n\nPaired with our fresh-baked Almond Croissant? That\'s the combo.',
      hashtags: ['#OatMilkLatte', '#CoffeeLovers', '#EmberAndBloom', '#LocalCoffee', '#MorningRitual'],
      call_to_action: 'Order ahead — skip the line',
      image_url: 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&h=400&fit=crop&q=80',
      pos_data_reference: { item: 'Oat Milk Latte', revenue_share: '34%', period: 'morning' },
      published_at: daysAgo(1),
      publish_url: 'https://instagram.com/p/demo-coffee',
      created_at: daysAgo(2),
    },
    rankings: [
      { keyword: 'best coffee shop near me', rank_position: 3, rank_change: 2, checked_at: daysAgo(0), ai_citation_count: 3, ai_platforms_cited: ['chatgpt', 'claude', 'perplexity'] },
      { keyword: 'oat milk latte', rank_position: 8, rank_change: 4, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
      { keyword: 'local coffee roaster', rank_position: 11, rank_change: 0, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
      { keyword: 'cold brew near me', rank_position: 6, rank_change: 3, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'claude'] },
      { keyword: 'best croissant downtown', rank_position: 5, rank_change: 7, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
    ],
  },

  fast_food: {
    brand: {
      business_name: 'Blaze Burrito Co.',
      business_type: 'fast_food',
      content_tier: 'starter',
      ayrshare_connected_platforms: ['instagram', 'tiktok'],
      voice_profile: {
        tone: 'bold',
        emoji_usage: 'moderate',
        top_products: ['Loaded Steak Burrito', 'Queso Fries', 'Mango Habanero Bowl'],
        keywords: ['best burrito', 'fast casual near me', 'lunch deal'],
      },
    },
    post: {
      id: 'demo-fastfood-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'The lunch rush doesn\'t lie.',
      body: 'Between 11:30 and 1PM, the Loaded Steak Burrito outsells everything 4-to-1. Hand-cut steak, house queso, fresh pico, and enough heat to wake you up from that morning meeting.\n\n$9.99 combo with Queso Fries. That\'s the move.',
      hashtags: ['#SteakBurrito', '#LunchDeal', '#BlazeBurritoCo', '#FastCasual', '#BurritoLovers'],
      call_to_action: 'Order for pickup — link in bio',
      image_url: 'https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?w=400&h=400&fit=crop&q=80',
      pos_data_reference: { item: 'Loaded Steak Burrito', revenue_share: '41%', period: 'lunch rush' },
      published_at: daysAgo(1),
      publish_url: 'https://instagram.com/p/demo-burrito',
      created_at: daysAgo(2),
    },
    rankings: [
      { keyword: 'best burrito near me', rank_position: 5, rank_change: 4, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'perplexity'] },
      { keyword: 'fast casual lunch', rank_position: 9, rank_change: 2, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
      { keyword: 'lunch deals under $10', rank_position: 7, rank_change: 6, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['chatgpt'] },
      { keyword: 'steak burrito', rank_position: 3, rank_change: 1, checked_at: daysAgo(0), ai_citation_count: 3, ai_platforms_cited: ['chatgpt', 'claude', 'perplexity'] },
      { keyword: 'queso fries', rank_position: 14, rank_change: -1, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
    ],
  },

  auto_shop: {
    brand: {
      business_name: 'Apex Auto Care',
      business_type: 'auto_shop',
      content_tier: 'growth',
      ayrshare_connected_platforms: ['facebook', 'google_business'],
      voice_profile: {
        tone: 'professional',
        emoji_usage: 'none',
        top_products: ['Full Synthetic Oil Change', 'Brake Inspection', 'Tire Rotation & Balance'],
        keywords: ['trusted mechanic', 'oil change near me', 'auto repair'],
      },
    },
    post: {
      id: 'demo-auto-ad',
      post_type: 'social',
      platform: 'facebook',
      status: 'published',
      hook: 'Your engine runs on data — so do we.',
      body: 'Full Synthetic Oil Changes are our most booked service — 47% of all appointments this month. We use premium Mobil 1 synthetic, a 21-point inspection, and get you back on the road in under 30 minutes.\n\nBook online, skip the wait.',
      hashtags: ['#OilChange', '#ApexAutoCare', '#TrustedMechanic', '#AutoRepair'],
      call_to_action: 'Book your appointment at apexautocare.com',
      image_url: 'https://images.unsplash.com/photo-1487754180451-c456f719a1fc?w=400&h=400&fit=crop&q=80',
      pos_data_reference: { item: 'Full Synthetic Oil Change', revenue_share: '47%', period: 'this month' },
      published_at: daysAgo(3),
      publish_url: 'https://facebook.com/apexauto/posts/demo',
      created_at: daysAgo(4),
    },
    rankings: [
      { keyword: 'oil change near me', rank_position: 3, rank_change: 5, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'perplexity'] },
      { keyword: 'trusted mechanic', rank_position: 6, rank_change: 2, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['claude'] },
      { keyword: 'auto repair shop', rank_position: 8, rank_change: 0, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
      { keyword: 'brake inspection', rank_position: 10, rank_change: 3, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
      { keyword: 'tire rotation near me', rank_position: 4, rank_change: 7, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'claude'] },
    ],
  },

  smoke_shop: {
    brand: {
      business_name: 'Haze Collective',
      business_type: 'smoke_shop',
      content_tier: 'starter',
      ayrshare_connected_platforms: ['instagram'],
      voice_profile: {
        tone: 'bold',
        emoji_usage: 'minimal',
        top_products: ['Premium Glass Collection', 'Artisan Rolling Papers', 'CBD Wellness Line'],
        keywords: ['smoke shop', 'premium glass', 'CBD wellness'],
      },
    },
    post: {
      id: 'demo-smoke-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'New glass just dropped.',
      body: 'Our Premium Glass Collection drives 38% of weekend revenue — and we just restocked with 12 new pieces from local artists. Hand-blown, one-of-a-kind, priced from $45.\n\nThese don\'t last. First come, first served.',
      hashtags: ['#PremiumGlass', '#HazeCollective', '#GlassArt', '#SmokeShop', '#HandBlown'],
      call_to_action: 'Visit us this weekend — 2847 Main St',
      image_url: 'https://images.unsplash.com/photo-1563203369-26f2e4a5ccf7?w=400&h=400&fit=crop&q=80',
      pos_data_reference: { item: 'Premium Glass Collection', revenue_share: '38%', period: 'weekends' },
      published_at: daysAgo(1),
      publish_url: 'https://instagram.com/p/demo-haze',
      created_at: daysAgo(2),
    },
    rankings: [
      { keyword: 'smoke shop near me', rank_position: 5, rank_change: 3, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['chatgpt'] },
      { keyword: 'premium glass pipes', rank_position: 7, rank_change: 4, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
      { keyword: 'CBD wellness products', rank_position: 11, rank_change: -1, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'perplexity'] },
      { keyword: 'artisan rolling papers', rank_position: 4, rank_change: 6, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['claude'] },
      { keyword: 'hand blown glass', rank_position: 9, rank_change: 2, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
    ],
  },

  peptide_shop: {
    brand: {
      business_name: 'Apex Peptide Supply',
      business_type: 'peptide_shop',
      content_tier: 'starter',
      ayrshare_connected_platforms: ['instagram'],
      voice_profile: {
        // Deliberately plain: this trade's content NEVER makes a health
        // claim. Stock, lots, and availability are the whole vocabulary.
        tone: 'precise',
        emoji_usage: 'none',
        top_products: ['BPC-157 5mg', 'Bacteriostatic Water 30ml', 'NAD+ 500mg'],
        keywords: ['peptide shop', 'BPC-157', 'bacteriostatic water'],
      },
    },
    post: {
      id: 'demo-peptide-ad',
      post_type: 'social',
      platform: 'instagram',
      status: 'published',
      hook: 'Fresh lots landed this morning.',
      body: 'New BPC-157 and NAD+ lots are live on the site, third-party tested with certificates linked on every product page.\n\nStanding reorder customers: your usual is reserved until Saturday — order online or call and the agent has your history.',
      hashtags: ['#ApexPeptideSupply', '#Restock', '#ThirdPartyTested'],
      call_to_action: 'Order online — in-stock lots ship same day',
      pos_data_reference: { item: 'BPC-157 5mg', repeat_share: '64%', period: 'this month' },
      published_at: daysAgo(1),
      publish_url: 'https://instagram.com/p/demo-apex',
      created_at: daysAgo(2),
    },
    rankings: [
      { keyword: 'peptide shop near me', rank_position: 4, rank_change: 5, checked_at: daysAgo(0), ai_citation_count: 1, ai_platforms_cited: ['perplexity'] },
      { keyword: 'bpc-157 in stock', rank_position: 6, rank_change: 3, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
      { keyword: 'bacteriostatic water', rank_position: 9, rank_change: 1, checked_at: daysAgo(0), ai_citation_count: 0, ai_platforms_cited: [] },
      { keyword: 'third party tested peptides', rank_position: 7, rank_change: 4, checked_at: daysAgo(0), ai_citation_count: 2, ai_platforms_cited: ['chatgpt', 'claude'] },
    ],
  },
}

export function fetchDemoContentData(): ContentDashboardData {
  const businessType = getActiveBusinessType()
  const demo = DEMO_BUSINESSES[businessType] ?? DEMO_BUSINESSES.restaurant

  return {
    brand: demo.brand,
    posts: [demo.post],
    rankings: demo.rankings,
    activeJobs: [],
    credits: { balance: 1000, lifetime_used: 0, free_granted: 1000 },
  }
}
