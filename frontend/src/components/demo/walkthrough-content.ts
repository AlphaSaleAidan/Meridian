import type { BusinessType } from '@/lib/demo-context'

export type PortalContext = 'us' | 'canada'
export type StepId =
  | 'overview'
  | 'actions'
  | 'margins'
  | 'staff'
  | 'camera'
  | 'phone'
  | 'content'
  | 'anomaly'
  | 'forecast'
  | 'customers'
  | 'connect'
  | 'checkout'

export interface WalkthroughStep {
  id: StepId
  tabPath: string
  elementSelector: string
  fallbackSelector: string
  spotlightPadding: number
}

export interface TourContent {
  title: string
  description: string
  tip?: string
}

export const WALKTHROUGH_STEPS: WalkthroughStep[] = [
  {
    id: 'overview',
    tabPath: '',
    elementSelector: '[data-walkthrough="overview-stats"]',
    fallbackSelector: '.card',
    spotlightPadding: 16,
  },
  {
    id: 'actions',
    tabPath: 'actions',
    elementSelector: '[data-walkthrough="top-actions-list"]',
    fallbackSelector: '.card',
    spotlightPadding: 16,
  },
  {
    id: 'margins',
    tabPath: 'margins',
    elementSelector: '[data-walkthrough="margin-stats"]',
    fallbackSelector: '[data-walkthrough="margin-calculator"]',
    spotlightPadding: 12,
  },
  {
    id: 'staff',
    tabPath: 'staff',
    elementSelector: '[data-walkthrough="staff-stats"]',
    fallbackSelector: '.card',
    spotlightPadding: 16,
  },
  {
    id: 'camera',
    // Route is registered as `camera-analytics` in App.tsx (CustomerDashboardRoutes
    // + Canada demo block). Earlier `camera-intelligence` value didn't match,
    // so the tour navigated to a non-existent path and the catch-all `*` route
    // bounced the user to the US landing page mid-tour.
    tabPath: 'camera-analytics',
    elementSelector: '[data-walkthrough="camera-stats"]',
    fallbackSelector: '.card',
    spotlightPadding: 16,
  },
  {
    id: 'phone',
    tabPath: 'phone-orders',
    elementSelector: '[data-walkthrough="phone-stats"]',
    fallbackSelector: '.card',
    spotlightPadding: 16,
  },
  {
    id: 'content',
    tabPath: 'content',
    elementSelector: '[data-walkthrough="content-stats"]',
    fallbackSelector: '.card',
    spotlightPadding: 16,
  },
  {
    id: 'anomaly',
    tabPath: 'anomalies',
    elementSelector: '[data-walkthrough="top-anomaly"]',
    fallbackSelector: '.card',
    spotlightPadding: 16,
  },
  {
    id: 'forecast',
    tabPath: 'forecasts',
    elementSelector: '[data-walkthrough="revenue-forecast-chart"]',
    fallbackSelector: '.recharts-responsive-container',
    spotlightPadding: 20,
  },
  {
    id: 'customers',
    tabPath: '',
    elementSelector: '[data-walkthrough="sidebar-nav"]',
    fallbackSelector: '[data-walkthrough="connect-pos-cta"]',
    spotlightPadding: 8,
  },
  {
    id: 'connect',
    tabPath: '',
    elementSelector: '[data-walkthrough="connect-pos-cta"]',
    fallbackSelector: '.glow-violet',
    spotlightPadding: 24,
  },
  {
    id: 'checkout',
    tabPath: '',
    elementSelector: '[data-walkthrough="connect-pos-cta"]',
    fallbackSelector: '.glow-violet',
    spotlightPadding: 0,
  },
]

// ─── Restaurant ─────────────────────────────────────────────

function restaurant(id: StepId): TourContent {
  switch (id) {
    case 'overview': return {
      title: 'Your revenue at a glance',
      description: 'Total revenue, covers, and average check for the last 30 days. The Money Left score shows how much untapped revenue our AI found in your data.',
      tip: 'Restaurants with a Money Left score above 70 typically have the biggest quick wins.',
    }
    case 'actions': return {
      title: 'Today\'s top priorities',
      description: 'Three AI-ranked actions based on ROI potential, effort required, and time sensitivity. Each one tells you exactly what to do, why it matters, and how much it could be worth.',
    }
    case 'margins': return {
      title: 'Margin calculator',
      description: 'See real margins on every menu item after waste, batch costs, and leakage are factored in. Most restaurants are surprised by which items are actually making money.',
      tip: 'Pour cost and waste-adjusted cost often tell a very different story than the raw food cost percentage.',
    }
    case 'staff': return {
      title: 'Staff performance ratings',
      description: 'Every team member ranked by revenue per hour, with AI-generated coaching notes. See who\'s driving sales and where training gaps might be costing you.',
    }
    case 'camera': return {
      title: 'Camera intelligence',
      description: 'Connect your security cameras and turn them into foot traffic counters. See entries, exits, occupancy, and conversion rate — no new hardware needed.',
      tip: 'Pair traffic data with POS data to understand your true conversion rate: how many people walk in vs. how many actually order.',
    }
    case 'phone': return {
      title: 'AI phone ordering',
      description: 'An AI voice agent answers calls, takes orders, and routes them to your POS. It handles after-hours calls, busy periods, and sends text-to-pay links automatically.',
    }
    case 'content': return {
      title: 'Content marketing engine',
      description: 'Generate social posts, SEO-optimized articles, and video content — all tailored to your brand. AI writes the copy, you approve and publish across every platform.',
      tip: 'Restaurants posting 3+ times per week on Google Business Profile see 2x more direction requests than those posting monthly.',
    }
    case 'anomaly': return {
      title: 'Unusual activity detected',
      description: 'Automatic alerts for void spikes, unexpected revenue dips, or sudden drops in a top-selling dish. You get flagged before it becomes a problem.',
    }
    case 'forecast': return {
      title: 'Revenue forecasts',
      description: 'Predict next week\'s and next month\'s revenue based on your history and seasonality. Plan prep, ordering, and staffing ahead of time instead of guessing.',
    }
    case 'customers': return {
      title: 'And there\'s a lot more',
      description: 'Customer segmentation, inventory tracking, marketing tools, and new features shipping every month. Check the Features tab for the full list — we\'re always adding more.',
    }
    case 'connect': return {
      title: 'Ready to see your real data?',
      description: 'Connect your POS and everything you just saw fills in with your actual numbers. Takes about 4 minutes. First month free, no credit card.',
    }
    case 'checkout': return {
      title: 'Let\'s get you set up',
      description: 'Answer a couple of quick questions so we can tailor your onboarding. Takes 30 seconds.',
    }
  }
}

// ─── Fast Food ──────────────────────────────────────────────

function fastFood(id: StepId): TourContent {
  switch (id) {
    case 'overview': return {
      title: 'Daily throughput and ticket size',
      description: 'Transaction volume, average ticket, and revenue at a glance. The Money Left score highlights revenue sitting in your existing traffic.',
      tip: 'A $0.30 average ticket increase across hundreds of daily transactions adds up to thousands per month.',
    }
    case 'actions': return {
      title: 'Today\'s highest-impact moves',
      description: 'Three AI-prioritized actions ranked by ROI. Things like combo optimization, upsell timing, or menu board adjustments — with projected dollar impact for each.',
    }
    case 'margins': return {
      title: 'Margin breakdown by item',
      description: 'See true margins after waste, batch cost, and leakage. Find out which combos and add-ons actually drive profit vs. which ones just move volume.',
    }
    case 'staff': return {
      title: 'Crew performance',
      description: 'Staff ranked by revenue per hour and speed. Identify your strongest crew members and spot where training could improve throughput during peak rushes.',
    }
    case 'camera': return {
      title: 'Traffic and conversion',
      description: 'Use your existing cameras to count foot traffic, measure drive-thru line length, and calculate walk-in conversion rates throughout the day.',
    }
    case 'phone': return {
      title: 'AI phone orders',
      description: 'An AI agent handles phone orders 24/7 — takes the order, sends a payment link, and pushes it to your POS. Frees up the counter during rush.',
      tip: 'Stores using AI phone ordering see 15-20% of their phone calls convert to orders that would have been missed.',
    }
    case 'content': return {
      title: 'Content marketing',
      description: 'Auto-generate social posts, SEO articles, and promo videos from your menu and sales data. Schedule across Instagram, Facebook, Google, and TikTok from one dashboard.',
    }
    case 'anomaly': return {
      title: 'Anomaly detection',
      description: 'Get alerted when drive-thru volume drops unexpectedly, an item sells way below forecast, or order cancellations spike. Catch issues same-day.',
    }
    case 'forecast': return {
      title: 'Volume forecasts',
      description: 'Predicted transaction counts and revenue for the week ahead. Dial in food prep quantities to reduce waste without running out during peak.',
    }
    case 'customers': return {
      title: 'And there\'s a lot more',
      description: 'Customer segmentation, inventory tracking, marketing tools, and new features shipping every month. Check the Features tab for the full list — we\'re always adding more.',
    }
    case 'connect': return {
      title: 'See this with your numbers',
      description: 'Connect your POS and all of this fills in with your real sales data. About 4 minutes to set up. First month free.',
    }
    case 'checkout': return {
      title: 'Let\'s get you set up',
      description: 'Answer a couple of quick questions so we can tailor your onboarding. Takes 30 seconds.',
    }
  }
}

// ─── Coffee Shop ────────────────────────────────────────────

function coffeeShop(id: StepId): TourContent {
  switch (id) {
    case 'overview': return {
      title: 'Your daily sales snapshot',
      description: 'Revenue, transactions, and average drink ticket at a glance. The Money Left score estimates additional revenue sitting in your existing traffic.',
      tip: 'Coffee shops often score highest on Money Left because small upsells (size upgrades, add-ons) compound across hundreds of daily orders.',
    }
    case 'actions': return {
      title: 'What to focus on today',
      description: 'Three AI-ranked actions specific to your data — like pushing a size upgrade during morning rush, promoting a high-margin seasonal drink, or adjusting a price that\'s leaving money behind.',
    }
    case 'margins': return {
      title: 'Drink and food margins',
      description: 'True margins on every menu item with waste and batch cost factored in. See which drinks are actually your profit drivers vs. which ones just look popular.',
      tip: 'Specialty drinks often have 3-4x the margin of drip coffee. Knowing exactly which ones lets you train baristas to suggestive sell the right items.',
    }
    case 'staff': return {
      title: 'Barista performance',
      description: 'Each team member\'s revenue per hour and average ticket. See who\'s naturally upselling and who might benefit from coaching on add-ons and size upgrades.',
    }
    case 'camera': return {
      title: 'Foot traffic analytics',
      description: 'Turn your existing cameras into traffic counters. See how many people walk in, peak entry times, and what percentage actually buy. No new hardware required.',
    }
    case 'phone': return {
      title: 'Phone order agent',
      description: 'An AI answers calls, takes orders (including customizations), and sends a text-to-pay link. Keeps your baristas focused on making drinks instead of answering the phone.',
    }
    case 'content': return {
      title: 'Social & content engine',
      description: 'Generate Instagram-ready posts featuring your seasonal specials, SEO articles to drive local search traffic, and short-form video content — all on-brand and scheduled automatically.',
      tip: 'Coffee shops that post daily specials on Instagram see 25-35% higher engagement than those posting generic brand content.',
    }
    case 'anomaly': return {
      title: 'When something\'s off',
      description: 'Automatic alerts when your morning rush doesn\'t show up, a seasonal drink underperforms, or your food-to-beverage ratio shifts unexpectedly.',
    }
    case 'forecast': return {
      title: 'Sales forecasts',
      description: 'Daily predictions to help you dial in milk orders, pastry pars, and cold brew batches. Stop dumping product or running out mid-shift.',
    }
    case 'customers': return {
      title: 'And there\'s a lot more',
      description: 'Customer segmentation, inventory tracking, marketing tools, and new features shipping every month. Check the Features tab for the full list — we\'re always adding more.',
    }
    case 'connect': return {
      title: 'Get your real data in here',
      description: 'Connect your POS — Square, Toast, Clover — and this entire dashboard fills with your numbers. About 4 minutes. Free first month.',
    }
    case 'checkout': return {
      title: 'Let\'s get you set up',
      description: 'Answer a couple of quick questions so we can tailor your onboarding. Takes 30 seconds.',
    }
  }
}

// ─── Auto Shop ──────────────────────────────────────────────

function autoShop(id: StepId): TourContent {
  switch (id) {
    case 'overview': return {
      title: 'Revenue and ticket trends',
      description: 'Monthly revenue, repair order count, and average ticket value. The Money Left score estimates revenue available from services you\'re not currently capturing.',
    }
    case 'actions': return {
      title: 'Today\'s top opportunities',
      description: 'Three AI-ranked actions specific to your shop — like a service to start upselling, a maintenance interval to market, or a pricing adjustment on a high-demand repair.',
    }
    case 'margins': return {
      title: 'Service margins',
      description: 'True margins on each service type after parts cost, labor, and waste are factored in. See which repairs are your real profit centers.',
      tip: 'Shops that know their true margin per service type can steer their marketing toward the work that actually makes money.',
    }
    case 'staff': return {
      title: 'Tech performance',
      description: 'Each technician ranked by revenue per hour and job completion rate. See who\'s your most efficient tech and where scheduling adjustments could help.',
    }
    case 'camera': return {
      title: 'Bay and lot monitoring',
      description: 'Use your cameras to track customer arrivals, bay occupancy, and wait times. Understand flow through your shop without adding any new hardware.',
    }
    case 'phone': return {
      title: 'AI appointment agent',
      description: 'An AI answers calls, books appointments, provides estimates, and sends text-to-pay links. Handles after-hours calls so you never miss a job.',
      tip: 'Auto shops miss 30-40% of inbound calls during busy hours. An AI phone agent captures those leads automatically.',
    }
    case 'content': return {
      title: 'Marketing content',
      description: 'Generate service-focused content — seasonal maintenance reminders, Google Business posts, and video walkthroughs of common repairs. Build trust and drive repeat visits.',
    }
    case 'anomaly': return {
      title: 'Anomaly alerts',
      description: 'Flagged when oil change volume drops (competitor?), declined repairs spike (pricing issue?), or a high-value service type disappears from the mix.',
    }
    case 'forecast': return {
      title: 'Revenue predictions',
      description: 'Forecast slow weeks so you can run promos, and busy weeks so you can schedule enough techs. Based on your historical patterns and seasonal trends.',
    }
    case 'customers': return {
      title: 'And there\'s a lot more',
      description: 'Customer segmentation, inventory tracking, marketing tools, and new features shipping every month. Check the Features tab for the full list — we\'re always adding more.',
    }
    case 'connect': return {
      title: 'See your shop\'s real data',
      description: 'Connect your POS or shop management system and this dashboard fills with your actual numbers. About 4 minutes. First month free.',
    }
    case 'checkout': return {
      title: 'Let\'s get you set up',
      description: 'Answer a couple of quick questions so we can tailor your onboarding. Takes 30 seconds.',
    }
  }
}

// ─── Smoke Shop ─────────────────────────────────────────────

function smokeShop(id: StepId): TourContent {
  switch (id) {
    case 'overview': return {
      title: 'Sales and basket overview',
      description: 'Daily revenue, transaction count, and average basket size. The Money Left score highlights revenue hiding in your product mix and pricing.',
    }
    case 'actions': return {
      title: 'Highest-value actions today',
      description: 'Three AI-prioritized moves — like a product to display at the counter, a pricing adjustment on a high-velocity item, or a bundle idea that could lift basket size.',
    }
    case 'margins': return {
      title: 'Product margin analysis',
      description: 'True margins across your product categories after cost and shrinkage. Find out which items are your real profit drivers vs. which just move volume.',
      tip: 'Small margin adjustments across hundreds of SKUs add up fast. This view helps you find the ones worth adjusting.',
    }
    case 'staff': return {
      title: 'Staff performance',
      description: 'Each employee ranked by revenue per hour and average basket. See who\'s naturally cross-selling and who could benefit from product knowledge training.',
    }
    case 'camera': return {
      title: 'Foot traffic and conversion',
      description: 'Use your existing cameras to measure foot traffic, dwell time, and conversion rate. See how many browsers actually buy.',
    }
    case 'phone': return {
      title: 'AI phone agent',
      description: 'An AI handles incoming calls — answers product availability questions, takes phone orders, and sends text-to-pay links. Keeps your counter staff focused.',
    }
    case 'content': return {
      title: 'Content & promotions',
      description: 'Generate product spotlight posts, new arrival announcements, and local SEO content. Schedule across your social platforms to drive foot traffic and repeat visits.',
    }
    case 'anomaly': return {
      title: 'Sales anomalies',
      description: 'Alerts when a top-seller suddenly drops, a product category spikes unexpectedly, or average basket shrinks. React before small trends become big problems.',
    }
    case 'forecast': return {
      title: 'Inventory forecasts',
      description: 'Revenue and volume forecasts help you time reorders and avoid tying up cash in slow-moving stock. Especially useful for seasonal products.',
    }
    case 'customers': return {
      title: 'And there\'s a lot more',
      description: 'Customer segmentation, inventory tracking, marketing tools, and new features shipping every month. Check the Features tab for the full list — we\'re always adding more.',
    }
    case 'connect': return {
      title: 'Put your real numbers here',
      description: 'Connect your POS and see all of this with your actual sales data. Takes about 4 minutes. First month free, no credit card.',
    }
    case 'checkout': return {
      title: 'Let\'s get you set up',
      description: 'Answer a couple of quick questions so we can tailor your onboarding. Takes 30 seconds.',
    }
  }
}

const contentFns: Record<string, (id: StepId) => TourContent> = {
  restaurant,
  fast_food: fastFood,
  coffee_shop: coffeeShop,
  auto_shop: autoShop,
  smoke_shop: smokeShop,
}

export function getTourContent(
  stepId: StepId,
  businessType: BusinessType,
  _ctx: PortalContext,
): TourContent {
  const fn = contentFns[businessType] || restaurant
  return fn(stepId)
}
