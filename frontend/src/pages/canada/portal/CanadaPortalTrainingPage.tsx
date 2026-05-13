import { useState } from 'react'
import {
  GraduationCap, CheckCircle2, ChevronRight, ChevronDown,
  BookOpen, Target, Users, Zap, Shield, BarChart3,
  Camera, Lightbulb, Plug, Monitor, Bot, Layout,
  TrendingUp, Wrench,
} from 'lucide-react'
import { clsx } from 'clsx'

interface Lesson {
  id: string
  title: string
  completed: boolean
  content: string[]
}

interface Module {
  id: string
  title: string
  description: string
  icon: typeof GraduationCap
  duration: string
  lessons: Lesson[]
  category: string
}

const MODULES: Module[] = [
  {
    id: 'onboarding',
    title: 'New Rep Onboarding',
    description: 'Everything you need to know to start selling Meridian POS Intelligence.',
    icon: BookOpen,
    duration: '45 min',
    category: 'Getting Started',
    lessons: [
      { id: '1', title: 'Welcome to Meridian Sales', completed: false, content: [
        'Meridian is an AI-powered POS analytics platform for independent business owners — restaurants, smoke shops, cafes, salons, and retail. We connect to their existing POS system (Square, Clover, Toast, Moneris, Lightspeed) and surface actionable insights they can\'t get on their own.',
        'Your role: find businesses using a POS system, show them what they\'re missing, and close them on a CA$343–CA$1,370/mo subscription. You earn 70% commission on every deal for the lifetime of the account.',
        'The Canadian market is wide open. Most small businesses have no analytics beyond what their POS dashboard shows. Meridian fills that gap with AI agents that run 24/7 — revenue forecasting, peak hour optimization, customer churn warnings, and inventory intelligence.',
        'Key stat to remember: the average Meridian merchant discovers CA$2,800/mo in "money left on the table" within the first week. That\'s your opening hook.',
      ]},
      { id: '2', title: 'Understanding the Product', completed: false, content: [
        'Meridian connects to a merchant\'s POS via OAuth (Square, Clover) or API key (Toast, Moneris). Once connected, we backfill 18 months of transaction history and run 24 AI agents across their data.',
        'Core features to demo: (1) Money Left on Table score — the single dollar amount a business is losing monthly. (2) Revenue Forecasting — 7/14/30 day predictions using AutoARIMA + LightGBM ensemble. (3) Peak Hour Optimizer — tells them exactly when to staff up or run promos. (4) Customer Churn Warnings — flags regulars who stopped coming before it\'s too late.',
        'Premium features (higher plans): Camera Intelligence (foot traffic, queue length, dwell time), 3D Store Scanning (zone-level revenue attribution), and Multi-Location rollups.',
        'What makes us different from competitors: we don\'t just show charts — we tell the owner exactly what to do and how much money it\'s worth. Every insight comes with a dollar amount and a specific action.',
      ]},
      { id: '3', title: 'Pricing & Plans Overview', completed: false, content: [
        'Three plans — all prices in CAD: Standard (CA$343/mo), Premium (CA$685/mo), Command (CA$1,370/mo). No setup fees. Month-to-month, no contracts.',
        'Standard: POS integration, daily AI insights, revenue analytics, email digest, 1 location. Best for: single-location cafes, smoke shops, small restaurants.',
        'Premium: Everything in Standard + Camera Intelligence, foot traffic analytics, customer segmentation, priority support. Best for: restaurants with 50+ seats, multi-register shops.',
        'Command: Everything in Premium + multi-location rollups, custom AI models, dedicated account manager, API access. Best for: franchise operators, multi-unit owners.',
        'Your commission: 70% of monthly subscription value, paid every month the account stays active. A single Standard deal = CA$240/mo recurring. Close 10 deals = CA$2,400/mo passive income.',
      ]},
      { id: '4', title: 'Setting Up Your Pipeline', completed: false, content: [
        'Your pipeline lives in this portal under the Leads tab. Every prospect goes through these stages: Proposal Shown → Customer Checkout → POS Connected → Customer Walkthrough.',
        'Lead sources that work best in Canada: (1) Walk-ins — visit the business, ask what POS they use, mention "I noticed you\'re on Square, most Square merchants are leaving money on the table." (2) Referrals — ask every closed client for 3 introductions. (3) Local business associations — BIAs, chambers of commerce, restaurant associations.',
        'Aim for 20 new leads per week. Of those, 5 will book demos, 2–3 will receive proposals, and 1 will close. That\'s 4 deals/month = CA$960+/mo in recurring commissions within 60 days.',
        'Log every interaction in the Leads tab. Update the stage as conversations progress. Notes are critical — write down their POS system, pain points, and any objections they raised.',
      ]},
      { id: '5', title: 'First Week Checklist', completed: false, content: [
        'Day 1: Complete all training modules in this portal. Read the pitch scripts. Familiarize yourself with the demo dashboard at meridian-dun-nu.vercel.app/demo.',
        'Day 2: Identify 30 target businesses in your city. Focus on restaurants, cafes, and smoke shops first — they have the highest close rates. Add them as leads in the portal.',
        'Day 3–4: Start outreach. Visit 10 businesses in person. Call or email the other 20. Use the 60-second pitch from Module 2.',
        'Day 5: Follow up on all conversations. Book at least 2 demos for the following week. Report your pipeline status to your team lead.',
        'Weekly rhythm going forward: Monday = outreach + new leads, Tuesday–Thursday = demos + follow-ups, Friday = pipeline review + admin.',
      ]},
    ],
  },
  {
    id: 'pitch',
    title: 'Perfecting Your Pitch',
    description: 'Master the Meridian value proposition and overcome common objections.',
    icon: Target,
    duration: '30 min',
    category: 'Sales Skills',
    lessons: [
      { id: '6', title: 'The 60-Second Elevator Pitch', completed: false, content: [
        'The pitch structure: Problem → Solution → Proof → Ask. Keep it under 60 seconds. Practice until it sounds natural, not scripted.',
        '"Hey [name], I work with [restaurant/cafe/shop] owners who use [their POS system]. Most of them are leaving thousands of dollars on the table every month and don\'t know it. We connect to your POS and our AI finds exactly where you\'re losing money — hidden revenue gaps, staffing inefficiencies, inventory waste. The average owner we work with discovers CA$2,800/month in opportunities within the first week. Can I show you a 15-minute demo?"',
        'Variations by context: If they\'re busy: "I\'ll be quick — we help [POS] users find money they\'re leaving on the table. Can I come back Thursday at 2 for 15 minutes?" If they ask what it costs: "Plans start at CA$343/month, but most owners find 10x that in their first week. Let me show you on your own data."',
        'Never lead with features. Lead with the dollar amount they\'re losing. Features are for the demo.',
      ]},
      { id: '7', title: 'Pain Points by Vertical', completed: false, content: [
        'Restaurants: "Do you know which menu items are actually making you money vs. just selling well? Most restaurant owners can\'t tell the difference between high-revenue and high-margin items." Also: food waste, peak hour understaffing, no-show reservations.',
        'Smoke Shops: "Theft and shrinkage are the #1 margin killer in smoke shops. Our anomaly detection catches unusual transaction patterns in real-time." Also: product velocity tracking (which SKUs move fastest), supplier reorder timing.',
        'Cafes: "Your morning rush is your money maker, but most cafe owners don\'t know exactly when to schedule their second barista. We predict demand down to the hour." Also: seasonal menu optimization, customer retention.',
        'Salons/Spas: "Your regulars are your business. We flag when a loyal customer hasn\'t rebooked in their usual timeframe so you can reach out before they switch." Also: staff performance comparison, service pricing optimization.',
        'Retail/Boutiques: "Inventory sitting on shelves is cash tied up. We forecast demand by SKU so you order the right quantities at the right time." Also: basket analysis (what sells together), markdown timing.',
      ]},
      { id: '8', title: 'Handling Price Objections', completed: false, content: [
        '"CA$343/month is too expensive." → "I understand. Let me ask — if I could show you CA$3,000/month in revenue you\'re currently missing, would CA$343 to capture that be worth it? That\'s what our AI typically finds in the first week."',
        '"I already have analytics in my POS." → "Square/Clover gives you what happened. We tell you what to do about it — and exactly how much each action is worth. That\'s the difference between a dashboard and intelligence."',
        '"I need to think about it." → "Totally fair. What specifically would you want to think through? I want to make sure I\'ve answered everything." (Then address the real objection they reveal.)',
        '"Can I try it for free?" → "We don\'t offer free trials because the onboarding takes real work — we connect your POS, backfill 18 months of data, and run 24 AI agents. But it\'s month-to-month, no contract. If you don\'t see value in month one, you cancel with one click."',
        '"I\'m locked into a contract with [competitor]." → "When does it end? Let me show you the demo now so you know exactly what you\'re switching to when it\'s up. I\'ll follow up 30 days before your renewal."',
      ]},
      { id: '9', title: 'Competitive Positioning', completed: false, content: [
        'MarketMan/BlueCart (inventory-only): "They only cover inventory. We cover revenue, customers, staff, forecasting, and inventory — all from one POS connection. They\'re a feature; we\'re the whole picture."',
        'Lightspeed Analytics: "Lightspeed only works with Lightspeed POS. We work with Square, Clover, Toast, Moneris, and Lightspeed. And we don\'t just report — we prescribe actions with dollar amounts."',
        'Generic BI tools (Power BI, Tableau): "Those require a data team to set up and maintain. We\'re plug-and-play — connect your POS, get insights in 24 hours. No SQL, no dashboards to build."',
        'Key differentiator: Meridian is the only platform that (1) works across all major POS systems, (2) uses AI agents that proactively surface insights with dollar amounts, and (3) requires zero technical setup from the merchant.',
      ]},
    ],
  },
  {
    id: 'demo',
    title: 'Running a Great Demo',
    description: 'How to conduct product demos that convert prospects into clients.',
    icon: Monitor,
    duration: '25 min',
    category: 'Sales Skills',
    lessons: [
      { id: '10', title: 'Demo Environment Setup', completed: false, content: [
        'Always demo from meridian-dun-nu.vercel.app/demo — this is the live demo environment with realistic data for a restaurant vertical. It mirrors exactly what the merchant will see.',
        'Before every demo: (1) Test the URL loads correctly on your device. (2) Know the prospect\'s vertical — the demo data is restaurant-focused, so frame it as "here\'s what it looks like for a restaurant, yours will show [their vertical]-specific insights." (3) Have the pricing page ready to share.',
        'Screen share settings: use a clean browser with no other tabs. Increase font size to 125% so they can read on their phone/laptop. Dark mode is default — it looks professional, don\'t change it.',
        'If doing an in-person demo at their business, use your phone or tablet. The dashboard is fully responsive.',
      ]},
      { id: '11', title: 'The Discovery Call Framework', completed: false, content: [
        'Before showing anything, ask 5 questions (2–3 minutes): (1) "What POS system are you on?" (2) "How many locations?" (3) "What\'s your biggest operational headache right now?" (4) "Do you currently track any analytics beyond what your POS shows?" (5) "If you could know one thing about your business that you don\'t today, what would it be?"',
        'Their answers tell you which features to emphasize in the demo. If they say "staffing" → show Peak Hours. If they say "inventory" → show Inventory Intelligence. If they say "I don\'t know what I don\'t know" → show Money Left on Table.',
        'Write down their answers. You\'ll reference them during the demo: "You mentioned staffing was your biggest headache — look at this..."',
      ]},
      { id: '12', title: 'Feature Walkthrough Script', completed: false, content: [
        'Open with the Overview dashboard (30 seconds): "This is your command center. One glance and you see your revenue trend, top insights, and the money left on the table score — that\'s the single most important number."',
        'Money Left on Table (2 minutes): "This CA$2,800 number? That\'s real money this business is losing every month. Click into it — here\'s exactly where it\'s coming from: pricing gaps, peak hour understaffing, customer churn. Each one has a dollar amount and a specific action."',
        'Pick 2–3 features based on discovery (5 minutes total): Show the ones that match their pain points. Don\'t show everything — it overwhelms them. "Based on what you told me about [their issue], let me show you this..."',
        'AI Agents page (1 minute): "These 24 agents run on your data 24/7. They\'re finding patterns a human would take weeks to spot. When something changes — a revenue dip, an inventory anomaly, a churning customer — you get an alert with what to do about it."',
        'Close the demo (1 minute): "So based on what you\'ve seen, the Standard plan at CA$343/mo would give you [relevant features]. Want to get started today? I can have your POS connected and insights running by tomorrow."',
      ]},
      { id: '13', title: 'Closing After the Demo', completed: false, content: [
        'The assumptive close: "Which plan makes the most sense for your setup — Standard or Premium?" Don\'t ask "Would you like to sign up?" — that invites a no.',
        'If they\'re excited but hesitant: "Let\'s do this — I\'ll get you set up on Standard today. You\'ll have insights by tomorrow morning. If after 30 days you don\'t see the value, you cancel with one click. Fair?"',
        'If they need to "talk to a partner/spouse": "Totally understand. Can we schedule a 10-minute call with both of you this Thursday? I want to make sure they see what you saw today."',
        'If they say yes: Walk them through the onboarding wizard in the portal immediately. Don\'t leave without their POS connected or a follow-up call scheduled to finish setup.',
        'After every demo (whether they close or not): Update the lead stage in the portal. Add detailed notes about what they liked, what concerned them, and the next step.',
      ]},
    ],
  },
  {
    id: 'verticals',
    title: 'Selling by Vertical',
    description: 'Tailored strategies for restaurants, smoke shops, salons, and retail.',
    icon: Users,
    duration: '40 min',
    category: 'Industry Knowledge',
    lessons: [
      { id: '14', title: 'Restaurants & Cafes', completed: false, content: [
        'Best opening: "Do you know your real food cost percentage, or are you guessing?" Most restaurant owners track revenue but not true margins by dish.',
        'Key Meridian features for restaurants: Menu Engineering Matrix (stars, plowhorses, puzzles, dogs), Peak Hour staffing recommendations, Revenue Forecasting for prep planning, Customer Churn detection for regulars.',
        'Average deal size: CA$343–CA$685/mo. Restaurants love the Premium tier because Camera Intelligence shows foot traffic patterns and queue wait times.',
        'Decision maker: Usually the owner or GM. In franchises, it\'s the franchisee (not corporate). Best time to visit: 2–4 PM (after lunch rush, before dinner prep).',
        'Seasonal angle: "Summer patio season is coming — our Peak Hour Optimizer will tell you exactly when to open the patio and how many staff to schedule."',
      ]},
      { id: '15', title: 'Smoke Shops & Vape', completed: false, content: [
        'Best opening: "How much are you losing to shrinkage every month? Most smoke shop owners don\'t know until inventory day — and by then it\'s too late."',
        'Key features: Anomaly Detection (catches suspicious void/refund patterns in real-time), Product Velocity (which SKUs move fastest, which are dead stock), Inventory Intelligence (reorder point predictions).',
        'Average deal size: CA$343–CA$500/mo. Smoke shops are price-sensitive but close fast when you show the shrinkage angle.',
        'Decision maker: Usually owner-operated. Best time to visit: late morning (11 AM–1 PM) when it\'s slow. Evening shifts are too busy.',
        'Tip: Many smoke shops use Clover. Ask "Are you on Clover?" as your opening — it immediately shows you know their world.',
      ]},
      { id: '16', title: 'Salons & Spas', completed: false, content: [
        'Best opening: "How do you know when a regular client is about to switch to another salon? Our AI flags it before their next appointment would have been."',
        'Key features: Customer LTV & Churn Warning (flag lapsed regulars), Staff Performance Comparison (revenue per stylist/therapist), Basket Analysis (which services are booked together — upsell opportunities).',
        'Average deal size: CA$343/mo. Salons are relationship-driven — the churn warning feature is your strongest closer.',
        'Decision maker: Salon owner, sometimes a manager with buying authority. Best time to visit: Tuesday or Wednesday mid-morning (slowest days for most salons).',
        'Tip: Bring a one-page "Salon Intelligence Report" showing what insights look like for a typical salon. Visual proof converts this vertical.',
      ]},
      { id: '17', title: 'Retail & Boutiques', completed: false, content: [
        'Best opening: "How much dead stock are you sitting on right now? Our AI predicts demand by SKU so you stop over-ordering."',
        'Key features: Inventory Intelligence (demand forecasting, reorder points), Basket Analysis (what sells together — merchandising insights), Seasonality patterns, Pricing Power analysis.',
        'Average deal size: CA$343–CA$685/mo. Multi-SKU retailers get more value from Premium because the data volume justifies deeper analytics.',
        'Decision maker: Store owner or buyer. Best time to visit: weekday mornings before the rush. Avoid weekends entirely.',
        'Canadian angle: "With supply chain unpredictability and currency fluctuations, knowing exactly what to order and when saves you thousands in tied-up inventory."',
      ]},
      { id: '18', title: 'Food Trucks & QSR', completed: false, content: [
        'Best opening: "Your busiest hour makes or breaks your day. Do you know exactly when your peak is — down to the 15-minute window?"',
        'Key features: Peak Hour Optimizer (critical for food trucks with limited service windows), Revenue Forecasting (predict slow days to skip or change locations), Menu Engineering (which items to push during rush vs. slow periods).',
        'Average deal size: CA$343/mo. Food trucks are budget-conscious but appreciate mobile-friendly dashboards they can check between rushes.',
        'Decision maker: Almost always the owner (often a solo operator). Best approach: visit them at their truck during a slow period, or DM on Instagram.',
        'Unique sell: "You probably track sales in your head. What if your phone showed you tomorrow\'s predicted revenue, your best-selling items by location, and exactly when your rush starts — automatically?"',
      ]},
    ],
  },
  {
    id: 'advanced',
    title: 'Advanced Closing Techniques',
    description: 'Negotiation tactics, urgency creation, and multi-location selling.',
    icon: Zap,
    duration: '35 min',
    category: 'Advanced',
    lessons: [
      { id: '19', title: 'Creating Urgency Without Pressure', completed: false, content: [
        'Time-based urgency: "The sooner we connect your POS, the sooner the AI starts learning your patterns. It takes 2–3 weeks to build accurate forecasts, so starting today means you\'ll have predictions by [date]."',
        'Loss-based urgency: "Every month without Meridian is another month of leaving CA$2,800+ on the table. That\'s CA$8,400 in the next quarter alone."',
        'Social proof: "Three other [vertical] owners in [city] signed up this month. [Business name] down the street is already seeing results." (Only use if true.)',
        'Never use fake scarcity ("this price is only available today"). It destroys trust. Real urgency comes from the cost of waiting, not artificial deadlines.',
      ]},
      { id: '20', title: 'Multi-Location Upsell', completed: false, content: [
        'Trigger: Any merchant with 2+ locations is a Command tier candidate (CA$1,370/mo). That\'s CA$959/mo commission for you.',
        'Opening: "You mentioned you have 3 locations. Right now, are you comparing performance across all three? Most multi-location owners fly blind on which location is actually most profitable."',
        'Key feature: Multi-Location Rollups — unified dashboard showing all locations side by side. Which one has the best margins? Which is understaffed? Where\'s revenue trending down?',
        'Close: "With Command, you see all 3 locations on one screen. The CA$1,370/mo pays for itself when you catch a single staffing inefficiency across locations."',
      ]},
      { id: '21', title: 'Referral Programs', completed: false, content: [
        'Ask for referrals within 48 hours of closing a deal — that\'s when satisfaction is highest. Script: "You\'re going to love this. Quick question — do you know 2–3 other business owners who\'d benefit from seeing their POS data like this?"',
        'Make it easy: "Can you text them right now and intro me? I\'ll handle the rest." People are more likely to refer if the action is immediate and simple.',
        'Follow up on every referral within 24 hours. Mention the referrer by name: "Hey, [name] from [business] thought you\'d find this interesting..."',
        'Track referral sources in the Leads tab. Over time, your best clients will become your best lead generators. Nurture those relationships.',
      ]},
      { id: '22', title: 'Commission Optimization', completed: false, content: [
        'Focus on retention, not just acquisition. Your 70% commission is recurring — every month the client stays, you earn. One client on Standard = CA$240/mo. Keep 10 clients for 12 months = CA$28,800/year from those 10 alone.',
        'Check in with clients monthly (a 2-minute text or call). Ask: "Are you using the insights? Anything confusing?" Clients who engage with the product don\'t churn.',
        'Upsell path: Standard → Premium is a natural upgrade after 2–3 months when they\'ve seen the value. "You\'ve been loving the revenue insights. Want to add Camera Intelligence to see foot traffic too? It\'s an extra CA$342/mo."',
        'Track your numbers: Pipeline value, close rate, average deal size, and monthly recurring commission. Review weekly. The reps who track their numbers outperform the ones who don\'t, every time.',
      ]},
    ],
  },
  {
    id: 'compliance',
    title: 'Compliance & Ethics',
    description: 'Guidelines for responsible selling and regulatory compliance.',
    icon: Shield,
    duration: '20 min',
    category: 'Required',
    lessons: [
      { id: '23', title: 'Sales Ethics Policy', completed: false, content: [
        'Never make promises Meridian can\'t keep. "Guaranteed to increase your revenue by X%" is not acceptable. Instead: "Our average merchant discovers CA$2,800/mo in opportunities" — that\'s a verifiable average, not a guarantee.',
        'Never disparage competitors by name. Compare features, not brands. "Unlike some solutions that only cover inventory, we provide full business intelligence" — not "Unlike MarketMan, which is garbage..."',
        'Never pressure a merchant into signing before they\'re ready. Pushy sales tactics damage the Meridian brand and lead to early cancellations (which costs you recurring commission).',
        'If a merchant asks about a feature we don\'t have yet, be honest: "That\'s on our roadmap but not available today. Here\'s what we do have that addresses a similar need."',
      ]},
      { id: '24', title: 'Data Privacy & Security', completed: false, content: [
        'Meridian processes merchant transaction data — this is sensitive business information. Key commitments to convey to prospects:',
        '(1) We never sell merchant data to third parties. (2) All data is encrypted in transit (TLS 1.3) and at rest (AES-256). (3) Data is stored in Canada-region infrastructure for Canadian merchants. (4) Merchants can delete their data and disconnect at any time.',
        'PIPEDA compliance: Canada\'s Personal Information Protection and Electronic Documents Act governs how we handle data. For Camera Intelligence specifically, merchants must display signage notifying customers of camera presence. We provide signage templates.',
        'If a merchant asks "who sees my data?" — answer: "Only you and the Meridian AI. No human at Meridian reviews individual merchant data unless you specifically request support."',
      ]},
      { id: '25', title: 'Accurate Representations', completed: false, content: [
        'Pricing: Always quote in CAD for Canadian merchants. Standard = CA$343/mo, Premium = CA$685/mo, Command = CA$1,370/mo. No hidden fees. Month-to-month.',
        'Capabilities: Only demo features that are live in production. If something is "coming soon," label it clearly. Never demo a prototype as if it\'s a shipped feature.',
        'Results: Use ranges and averages, not guarantees. "Merchants typically discover CA$1,500–CA$4,000/month in opportunities" is accurate. "You will make CA$4,000 more per month" is not.',
        'Support: Response time is best-effort for Standard, priority for Premium/Command. Don\'t promise 24/7 phone support unless it\'s part of the plan they\'re purchasing.',
      ]},
    ],
  },
  {
    id: 'camera',
    title: 'Camera Intelligence Setup',
    description: 'How to sell and configure Meridian Vision for foot traffic and queue analytics.',
    icon: Camera,
    duration: '30 min',
    category: 'Product Knowledge',
    lessons: [
      { id: '26', title: 'What is Camera Intelligence?', completed: false, content: [
        'Camera Intelligence is Meridian\'s computer vision system that turns existing security cameras into business analytics sensors. It tracks: foot traffic counts (hourly/daily/weekly), dwell time per zone, queue length and wait time, path analysis (how customers move through the store).',
        'It does NOT do facial recognition or store personal images. All processing produces anonymous counts and heatmaps — no individual customer data is stored.',
        'This is a Premium/Command tier feature. It\'s the primary upsell from Standard. Monthly uplift: CA$342/mo (Standard → Premium upgrade).',
        'Best verticals for Camera Intelligence: restaurants with seating areas, retail stores with multiple product zones, any business with a checkout queue.',
      ]},
      { id: '27', title: 'Hardware Requirements & Placement', completed: false, content: [
        'Minimum: 1 IP camera with RTSP stream output, positioned at the entrance for foot traffic counting. Most merchants already have security cameras that work.',
        'Compatible cameras: Any IP camera with RTSP (Hikvision, Dahua, Axis, Reolink, Amcrest). Ring and Nest do NOT support RTSP natively — check before promising compatibility.',
        'Optimal placement: (1) Entrance/exit — overhead, pointing down at 45° angle for accurate person counting. (2) Key zones — aisles, display areas, checkout. (3) Avoid: direct sunlight, mirrors, glass reflections.',
        'Network: Camera needs to be on the same network as the Meridian edge device (or accessible via the merchant\'s public IP with port forwarding). Bandwidth: 2–4 Mbps per camera.',
      ]},
      { id: '28', title: 'PIPEDA Compliance & Privacy Signage', completed: false, content: [
        'Canadian privacy law (PIPEDA) requires: (1) Visible signage at entrances notifying visitors that video analytics are in use. (2) A posted privacy policy explaining what data is collected and how it\'s used. (3) Data retention limits — we auto-delete raw footage after 30 days.',
        'Meridian provides: printable signage templates (bilingual English/French for Quebec), a privacy policy template merchants can customize, and automatic data retention enforcement.',
        'Key talking point: "This is anonymous analytics, not surveillance. We count people and track movement patterns — we don\'t identify individuals. It\'s the same technology major retailers use, made affordable for independent businesses."',
        'Quebec-specific: signage MUST be bilingual. We provide French translations in the signage templates.',
      ]},
      { id: '29', title: 'Configuring Zones & Alerts', completed: false, content: [
        'After camera installation, the merchant (or you during onboarding) defines zones in the Meridian dashboard: entrance, checkout, product displays, seating areas, etc.',
        'Zone configuration: draw polygons on the camera feed to mark each zone. Name them descriptively ("Front Display", "Checkout Counter", "Window Seats"). The AI then tracks time spent in each zone and correlates with POS transactions.',
        'Alerts to set up: (1) Queue length > 5 people — staff up immediately. (2) Zone dwell time anomaly — something changed in customer behavior. (3) Traffic drop-off — fewer visitors than predicted, investigate.',
        'The real value is the cross-reference: "Customers who spend more than 3 minutes in the display zone have a 40% higher average ticket." That\'s actionable merchandising intelligence.',
      ]},
      { id: '30', title: 'Selling the ROI to Prospects', completed: false, content: [
        'Frame it as "your security cameras are already there — we\'re just making them smart." No new hardware cost in most cases.',
        'ROI calculation: "If Camera Intelligence helps you reduce queue wait time by 30 seconds and you serve 200 customers/day, that\'s 100 minutes saved daily. At your average ticket of CA$15, serving even 5 more customers/day = CA$2,250/month in additional revenue."',
        'For restaurants specifically: "Knowing that 60% of your foot traffic passes your specials board but only 15% orders from it tells you the board placement isn\'t working. Move it, increase orders, measure the impact."',
        'Close with: "You\'re already paying for security cameras. For CA$342/mo more, those cameras become your most valuable employee — one that watches your business 24/7 and tells you exactly how to make more money."',
      ]},
    ],
  },
  {
    id: 'quicktips',
    title: 'Quick Tips',
    description: 'Bite-sized tips for everyday selling in the Canadian market.',
    icon: Lightbulb,
    duration: '15 min',
    category: 'Quick Reference',
    lessons: [
      { id: '31', title: 'Pricing in CAD — Handling Currency Questions', completed: false, content: [
        'All Meridian prices for Canadian merchants are quoted and billed in CAD. Standard: CA$343/mo, Premium: CA$685/mo, Command: CA$1,370/mo.',
        'If a merchant asks "why is it more expensive than the US version?" — "Pricing is set at parity value for the Canadian market. The product, features, and support are identical."',
        'Never quote USD prices to a Canadian merchant. Always use the CA$ prefix when stating amounts verbally and in writing.',
        'Invoices and billing are processed in CAD through Stripe. No currency conversion surprises for the merchant.',
      ]},
      { id: '32', title: 'Canadian Payment Processing Landscape', completed: false, content: [
        'Top POS systems in Canada (by market share): (1) Moneris — the biggest, especially in established restaurants. (2) Square — growing fast in small businesses and food trucks. (3) Clover — popular in smoke shops and retail. (4) Lightspeed — strong in retail and hospitality. (5) Toast — expanding into Canada, mostly in restaurants.',
        'Meridian currently connects to: Square, Clover, Toast. Moneris and Lightspeed integrations are on the roadmap.',
        'If a prospect is on Moneris or Lightspeed: "We\'re building that integration right now. I can put you on the early access list — you\'ll be one of the first connected. In the meantime, we can do a CSV import of your transaction data to show you the insights immediately."',
      ]},
      { id: '33', title: 'Provincial Tax Differences (GST/HST/PST)', completed: false, content: [
        'Meridian\'s subscription is a digital service — it\'s subject to GST/HST. Know your province: BC = GST 5% + PST 7%, Alberta = GST 5% only, Ontario = HST 13%, Quebec = GST 5% + QST 9.975%, Manitoba = GST 5% + PST 7%.',
        'Don\'t get into tax discussions during the sale. If asked: "Sales tax is applied automatically based on your province at billing. It\'s on top of the quoted price, same as any software subscription."',
        'For the merchant\'s own data: Meridian handles tax-inclusive vs. tax-exclusive transactions based on how their POS reports them. All revenue figures in the dashboard match their POS configuration.',
      ]},
      { id: '34', title: 'Seasonal Sales Patterns in Canada', completed: false, content: [
        'Best months to sell: September (back to business after summer), January (new year resolutions to "run a better business"), and March–April (pre-patio season for restaurants).',
        'Hardest months: July–August (owners are busy/on vacation), December (holiday distraction). Focus on pipeline building during hard months, closing during peak months.',
        'Seasonal hooks: Spring — "Patio season is 6 weeks away. Get your forecasting set up now so you know exactly how to staff." Fall — "Q4 is your make-or-break quarter. Start tracking now so you can optimize holiday pricing." Winter — "Slow season? That\'s when smart owners analyze what worked last year and plan for spring."',
      ]},
    ],
  },
  {
    id: 'pos-guides',
    title: 'POS Connection Guides',
    description: 'Step-by-step guides for connecting major Canadian POS systems.',
    icon: Plug,
    duration: '25 min',
    category: 'Technical',
    lessons: [
      { id: '35', title: 'Moneris Integration Walkthrough', completed: false, content: [
        'Note: Moneris integration is currently in development. For now, use the CSV import method to get Moneris merchants started.',
        'CSV Import process: (1) The merchant exports their transaction report from Moneris Go portal → Reports → Transaction Report → Export CSV. (2) In the Meridian onboarding wizard, select "Manual CSV Import" and upload the file. (3) Our system maps Moneris fields automatically.',
        'What to tell the merchant: "We\'re building a direct Moneris connection that will sync automatically. For now, we can import your data via CSV — it takes 5 minutes and gives you full access to all AI insights. Once the direct integration is live, we\'ll switch you over automatically."',
        'Export tip: Tell the merchant to export at least 6 months of data for the AI to detect meaningful patterns. 12–18 months is ideal.',
      ]},
      { id: '36', title: 'Square Canada Setup', completed: false, content: [
        'Square OAuth flow: (1) In the onboarding wizard, click "Connect Square." (2) Merchant logs into their Square account and authorizes Meridian. (3) We automatically backfill up to 18 months of transaction history. (4) Incremental sync runs every 15 minutes + real-time webhooks.',
        'Common issues: (1) Merchant has multiple Square locations — they need to authorize the correct one. (2) "I don\'t remember my Square login" — direct them to squareup.com/login to reset. (3) Sandbox vs. Production — make sure they\'re connecting their real account, not a test account.',
        'Data we pull from Square: transactions, items, categories, customers, inventory counts, refunds, discounts, employees (for staff analytics).',
        'Timeline: After connection, initial backfill takes 5–30 minutes depending on data volume. AI insights begin appearing within 24 hours.',
      ]},
      { id: '37', title: 'Clover Canada Configuration', completed: false, content: [
        'Clover OAuth flow: Similar to Square. (1) Click "Connect Clover" in the wizard. (2) Merchant logs into their Clover account. (3) Authorize Meridian app access. (4) Backfill + incremental sync begins.',
        'Clover-specific notes: (1) Clover\'s API rate limits are tighter than Square\'s — initial backfill may take longer (up to 2 hours for merchants with high transaction volumes). (2) Some older Clover hardware runs Android 6 and may have connectivity issues — unrelated to Meridian but worth knowing.',
        'Data we pull from Clover: orders, line items, payments, refunds, employees, inventory (if the merchant uses Clover\'s inventory features — many don\'t).',
        'Tip for the sale: "Clover gives you a green screen of sales totals. Meridian turns that into intelligence — what to sell more of, when to staff up, which customers are about to leave."',
      ]},
      { id: '38', title: 'Troubleshooting POS Connections', completed: false, content: [
        '"Connection failed" during OAuth: (1) Check if the merchant is logged into the correct POS account. (2) Try a different browser (incognito mode clears cached auth). (3) Check if the merchant\'s POS subscription is active — expired accounts can\'t authorize third-party apps.',
        '"Data isn\'t showing up" after connection: (1) Backfill takes 5–30 minutes — wait before troubleshooting. (2) Check the connection status in Settings. Green = connected, Yellow = syncing, Red = error. (3) If red, disconnect and reconnect.',
        '"Numbers don\'t match my POS reports": (1) Timezone mismatch — ensure the merchant\'s POS timezone matches what Meridian is using. (2) Refunds/voids — we include or exclude refunds depending on the metric. Revenue = net of refunds. Transaction count = gross. (3) Currency — always verify both sides are in CAD.',
        'Escalation: If you can\'t resolve a connection issue within 10 minutes, document the error in the lead notes and flag it to the team. Don\'t let a technical issue kill a warm deal — offer to follow up once it\'s resolved.',
      ]},
    ],
  },
  {
    id: 'dashboard-overview',
    title: 'The Merchant Dashboard',
    description: 'Every screen the merchant sees — know it inside out before you demo.',
    icon: Layout,
    duration: '40 min',
    category: 'Product Knowledge',
    lessons: [
      { id: '39', title: 'Overview & Command Center', completed: false, content: [
        'The Overview page is the first screen a merchant lands on after logging in. It shows four stat cards at the top: Total Revenue (last 30 days), Transaction Count, Average Ticket size, and the Money Left on Table score. Each stat includes a percentage change versus the prior period so the merchant instantly knows if things are trending up or down.',
        'Below the stats is the Revenue Chart — a 30-day line graph showing daily revenue with the trend direction. Merchants can hover over any day to see exact figures. This is the "heartbeat" of the business.',
        'The next section shows Top AI Insights — the 5 most impactful findings from all 37 agents, sorted by dollar impact. Each insight card shows the type (pricing, staffing, anomaly, etc.), the dollar amount at stake, and a one-line action the merchant should take.',
        'Finally, the Overview shows a summary of active AI agents, the customer retention score across all RFM segments, and a connection status badge (green = live POS sync, yellow = syncing, red = disconnected). This page alone gives the merchant a complete 30-second health check of their business.',
      ]},
      { id: '40', title: 'Revenue & Forecasting Pages', completed: false, content: [
        'The Revenue page breaks down income by day, week, and month. It shows daily revenue bars with a trend line overlay, the best and worst revenue days, and week-over-week and month-over-month growth percentages. Merchants can drill into any individual day to see every transaction.',
        'Transaction Drill-Down: Clicking a day opens a detailed view showing each transaction with line items, payment method, timestamps, and the employee who processed it. This is critical for spotting anomalies — a merchant can see exactly what happened at 2:47 PM on a Tuesday.',
        'The Forecasts page uses AutoARIMA and LightGBM ensemble models to predict revenue for 7, 14, and 30 days out. Each forecast shows a predicted amount, a confidence interval (upper and lower bounds), and a growth percentage. Merchants use this for staffing decisions, inventory ordering, and cash flow planning.',
        'Key demo tip: Show the forecast page and say "This is what your next 30 days look like. Your POS can\'t do this — it only tells you what already happened. Meridian tells you what\'s coming."',
      ]},
      { id: '41', title: 'Products, Margins & Menu Matrix', completed: false, content: [
        'The Products page ranks every item sold by revenue, units, and margin. Each product shows its selling price, cost, margin percentage, and monthly sales volume. Merchants can sort by any column to find their best sellers, worst sellers, or highest-margin items.',
        'The Margins page goes deeper — it breaks down true cost per serving including ingredient costs, waste adjustments, and pour cost percentages. For each product, the merchant sees revenue vs. cost, margin per unit, and total leakage (money lost to waste or underpricing). This is where the "Money Left on Table" numbers come from.',
        'Menu Engineering Matrix (Menu Matrix page) classifies every item into four quadrants: Stars (high popularity + high margin — promote these), Plowhorses (high popularity + low margin — raise price or cut cost), Puzzles (low popularity + high margin — market these harder), Dogs (low popularity + low margin — consider removing). This framework gives merchants a clear action for every item on their menu.',
        'Selling this to a restaurant owner: "Right now you know what sells the most, but do you know what makes you the most money? They\'re not always the same item. Your top seller might be your worst margin item."',
      ]},
      { id: '42', title: 'Customers & Retention Intelligence', completed: false, content: [
        'The Customers page uses RFM analysis (Recency, Frequency, Monetary value) to segment every customer into groups: Champions (best customers — high spend, frequent, recent), Loyal (consistent regulars), At Risk (used to come often but visits are declining), and Lost (haven\'t returned in 60+ days).',
        'For each customer, the dashboard shows: average order value, total lifetime spend, visits per month, days since last visit, their top item, retention risk level (low/medium/high), predicted lifetime value (LTV), churn probability percentage, and probability of being "alive" (still an active customer).',
        'The retention score is a weighted average across all segments — it tells the merchant what percentage of their customer base is healthy vs. at risk. A score below 60% means they\'re losing customers faster than they\'re gaining them.',
        'Demo this by saying: "See these 23 customers flagged as At Risk? They used to spend CA$200/month each. That\'s CA$4,600/month walking out the door. Our AI caught it — your POS didn\'t."',
      ]},
      { id: '43', title: 'Peak Hours, Staff & Inventory', completed: false, content: [
        'Peak Hours shows a heatmap grid — days of the week on one axis, hours of the day on the other. Each cell is color-coded by revenue intensity. This instantly shows the merchant their golden hours (dark green = peak revenue) and dead zones (gray = low traffic). The staffing agent overlays recommended headcount for each hour.',
        'The Staff page ranks employees by performance metrics: average ticket size, transactions per shift, upsell rate, customer rating, and revenue generated per hour. Each staff member shows a trend arrow (improving, declining, or stable). Managers use this to identify top performers for training models and underperformers who need coaching.',
        'The Inventory page tracks stock levels with AI-predicted reorder points. For each item, it shows current quantity, daily velocity (units sold per day), predicted stockout date, and a suggested reorder point. The system flags items that will run out within 3 days so the merchant can order before they lose sales.',
        'Tie these together in a demo: "Your peak hour is 7–9 AM, but you\'re one staff member short during that window. Meanwhile, your espresso beans will run out in 2 days. Meridian catches both of these before they cost you money."',
      ]},
      { id: '44', title: 'Anomalies, Insights & Actions', completed: false, content: [
        'The Anomalies page flags unusual patterns in the data: unexpected void spikes (possible theft or training issues), revenue drops on normally strong days, sudden changes in product mix, and payment method anomalies. Each anomaly shows what happened, when, the statistical deviation from normal, and a recommended investigation step.',
        'The Insights page aggregates all findings from every AI agent into a filterable list. Merchants can filter by type: Money Left, Products, Pricing, Staffing, Anomalies, Seasonal, Inventory, Benchmarks, or General. Each insight shows the dollar impact and whether it\'s been acted on or is still pending.',
        'The Top Actions page is the most important page for driving merchant value. It ranks the top recommendations by ROI — highest impact actions first. Each action shows: what to do, why (with the AI\'s full reasoning chain), expected monthly impact in dollars, effort level (low/medium/high), and which AI agent discovered it.',
        'The reasoning chain is key to merchant trust. When an action says "Raise Matcha Latte price to CA$7.00 for +CA$840/month," the merchant can click to see the full reasoning: the elasticity calculation, competitor pricing data, volume impact projection, and the statistical model used. Transparency builds confidence.',
      ]},
      { id: '45', title: 'Settings, Notifications & 3D Space', completed: false, content: [
        'The Settings page is where merchants manage their POS connection, account details, notification preferences, and subscription plan. The connection badge shows real-time sync status. Merchants can disconnect and reconnect their POS at any time.',
        'Notifications surface time-sensitive alerts: revenue milestones, anomaly detections, inventory warnings, and agent findings. Merchants can configure which notifications they receive and how (in-app, email digest, or both). The daily email digest summarizes yesterday\'s performance and top insights.',
        'Phone Orders (Premium+) enables AI-powered voice ordering via phone. The system uses speech-to-text and a conversational AI to take customer orders by phone, process them through the POS, and log the transaction. Useful for restaurants that take delivery/pickup orders.',
        '3D Space (Command tier) is the most advanced feature. It creates a 3D scan of the merchant\'s physical store and overlays revenue data by zone. The merchant can see exactly which areas of their store generate the most revenue, where customers linger, and which displays drive the most sales. This is the "wow factor" feature for Command tier demos.',
      ]},
    ],
  },
  {
    id: 'ai-agents',
    title: 'Understanding the 37 AI Agents',
    description: 'What each agent does, what it finds, and how to explain it to merchants.',
    icon: Bot,
    duration: '45 min',
    category: 'Product Knowledge',
    lessons: [
      { id: '46', title: 'How AI Agents Work', completed: false, content: [
        'Meridian runs 37 specialized AI agents on every merchant\'s POS data. Each agent focuses on one specific area — revenue trends, customer behavior, pricing optimization, inventory management, staffing, etc. They run on a schedule (every 1–6 hours depending on the agent) and produce findings with dollar amounts attached.',
        'Agents are grouped into 5 categories: Analysis (examining data patterns), Forecasting (predicting future trends), Optimization (recommending specific changes), Strategy (high-level business planning), and Coordination (synthesizing findings from other agents).',
        'Each agent has a confidence score (0–100%) that reflects how reliable its findings are. Agents with more data produce higher confidence scores. This is why we tell merchants "the AI gets smarter every week" — confidence scores genuinely improve as more transaction history accumulates.',
        'On the Agent Dashboard, merchants see every agent with its status (active, running, idle), last run time, next scheduled run, number of findings, confidence score, and latest finding. They can click any agent to see its full reasoning chain — the observation, analysis, conclusion, and recommended action.',
      ]},
      { id: '47', title: 'Analysis Agents (The Data Detectives)', completed: false, content: [
        'Transaction Analyst: Deep dives into every transaction looking for anomalies — void spikes, unusual refund patterns, register-specific issues. Example finding: "3x spike in void transactions on Tuesday evenings — possible training gap or theft."',
        'Product Intelligence: Ranks every SKU by margin, velocity, and cannibalization. Finds co-purchase patterns (items frequently bought together) and recommends bundles. Example: "Cappuccino + Croissant co-purchase rate 34%, potential CA$2.40 uplift per bundle."',
        'Customer Segmentor: Uses RFM (Recency, Frequency, Monetary) analysis to classify customers into segments — Champions, Loyal, At Risk, Lost. Example: "23 VIP customers drive 41% of revenue — 4 showing early churn signals."',
        'Revenue Trend: Tracks daily, weekly, and monthly growth rates and flags inflection points. Day of Week agent identifies the best and worst performing days. Category Mix agent analyzes revenue share by product category and flags imbalances.',
        'Additional analysis agents: Basket Analysis (co-purchase patterns), Customer LTV (lifetime value predictions), Product Velocity (rising stars vs. dead stock), Competitor Benchmarker (industry comparisons), Customer Recognizer (repeat visitor tracking without personal data), and Demographic Profiler (age/gender distribution from camera feeds — Premium tier only).',
      ]},
      { id: '48', title: 'Optimization Agents (The Money Finders)', completed: false, content: [
        'Peak Hour Optimizer: Maps transaction density by hour and day, overlays staffing data, and recommends exact headcount per hour. Example: "7–9 AM generates 47% of daily revenue but is 1 staff member short — adding 1 person recovers CA$520/month in walkout losses."',
        'Margin Optimizer: Identifies margin leakage by comparing actual margins to category averages. Flags items with unusually low margins due to ingredient costs, waste, or underpricing. Example: "Matcha Latte margin at 62% vs. 75% category average — ingredient cost review needed."',
        'Inventory Intelligence: Predicts stockout risk by tracking daily sales velocity per item and calculating when current inventory will run out. Sets optimal reorder points. Example: "Espresso beans will stockout in 2 days at current velocity — reorder now."',
        'Pricing Power: Measures price elasticity across every SKU to identify items where the merchant can safely raise prices without losing volume. Example: "4 items have inelastic demand — combined price increase potential CA$1,200/month."',
        'Additional optimization agents: Discount Analyzer (evaluates promo ROI and detects cannibalization), Staffing (calculates optimal headcount per hour based on labor efficiency), Payment Optimizer (analyzes payment method mix and fee optimization), Waste & Shrinkage (tracks shrinkage rate and void patterns), and Queue Monitor (real-time queue length and walkaway revenue loss — Premium tier with camera).',
      ]},
      { id: '49', title: 'Forecasting & Strategy Agents', completed: false, content: [
        'Revenue Forecaster: Predicts revenue for 7, 14, 30, and 90 days using AutoARIMA + LightGBM ensemble models. Includes confidence intervals and growth projections. Example: "90-day forecast projects CA$184K revenue with 12% growth trajectory."',
        'Cash Flow: Projects 14-day cash position including payment processing fees and identifies optimal payment method mix. Cashflow Forecast extends this to 30 days with danger zone detection for low-balance periods. Example: "Cash position dips to danger zone around the 18th — schedule vendor payments after the 20th."',
        'Seasonality: Decomposes historical data into seasonal patterns and calendar effects. Helps merchants plan inventory ramp-ups and promotional timing. Example: "Spring uptick begins mid-March historically — plan inventory ramp-up 2 weeks early."',
        'Strategy agents synthesize findings from all other agents into actionable plans. Retention Strategist recommends specific winback offers per customer segment. Growth Score calculates an executive 0–100 opportunity score with a monthly action plan. Money Left on Table aggregates all agent outputs into the headline dollar opportunity figure — the single most important number in the dashboard.',
        'Coordination agents: Insight Narrator translates all agent findings into plain English narratives and executive briefs. Action Prioritizer ranks every recommendation by ROI and effort so the merchant always knows what to do first. Feature Engineer identifies the highest-value product improvements based on aggregate agent data.',
      ]},
      { id: '50', title: 'Premium & Command Tier Agents', completed: false, content: [
        'These agents only activate on Premium and Command plans — they require camera data or multi-location setups to function. They\'re the primary technical reason to upsell from Standard.',
        'Foot Traffic (Premium): Counts entries and exits from camera feeds, calculates visitor-to-transaction conversion rate. Example: "Conversion rate 34% — 66% of foot traffic leaves without purchasing, signage test recommended." This metric is unavailable from POS data alone.',
        'Queue Monitor (Premium): Tracks real-time queue length and average wait times. Estimates revenue lost to walkaway customers. Example: "Average wait exceeds 3 minutes during 8–9 AM — estimated CA$320/month in walkaway losses." Combines with Peak Hour Optimizer for staffing recommendations.',
        'Dwell Time (Premium): Measures how long visitors spend in each zone of the store (requires zone configuration on camera feed). Correlates dwell time with purchase probability. Example: "Visitors spending 6+ minutes in browse zone convert at 2.1x the rate of those spending under 3 minutes."',
        'Demographic Profiler (Premium): Detects anonymized age and gender distribution from camera feeds. No facial recognition — just aggregate demographics for marketing decisions. Location Analyst (Command): Activates for multi-location merchants, comparing performance metrics across all locations side by side. Loyalty Architect (Command): Monitors loyalty program ROI and optimizes reward tiers.',
      ]},
    ],
  },
  {
    id: 'onboarding-flow',
    title: 'Customer Onboarding Mastery',
    description: 'Walk merchants from signup to first insights — the make-or-break moment.',
    icon: TrendingUp,
    duration: '30 min',
    category: 'Product Knowledge',
    lessons: [
      { id: '51', title: 'The Onboarding Wizard Step by Step', completed: false, content: [
        'After a merchant signs up, you walk them through the Onboarding Wizard. This is the most critical moment in the customer lifecycle — a smooth onboarding leads to retention, a confusing one leads to churn. Your job is to make this effortless.',
        'Step 1 — Business Profile: The merchant enters their business name, selects their industry type (restaurant, cafe, smoke shop, salon, retail, food truck, auto shop), and confirms their location. This determines which AI agents are prioritized and what industry benchmarks are used.',
        'Step 2 — POS Connection: The merchant clicks "Connect" next to their POS system (Square, Clover, or Toast). They log into their POS account and authorize Meridian. The OAuth flow takes 30 seconds. Once authorized, the system begins backfilling up to 18 months of transaction history.',
        'Step 3 — Initial Data Sync: A progress screen shows the backfill status. Depending on data volume, this takes 5–30 minutes. Tell the merchant: "Your data is syncing now. You\'ll start seeing insights within 24 hours, and the AI gets smarter every week as it learns your patterns." Do NOT leave until the connection status shows green.',
        'Step 4 — Dashboard Tour: Walk the merchant through the Overview page, point out the Money Left on Table score, show them the Insights tab, and explain that 37 agents are now running on their data. Set expectations: "Check your dashboard daily for the first week — new insights will keep appearing as the AI analyzes more of your history."',
      ]},
      { id: '52', title: 'The Customer Walkthrough', completed: false, content: [
        'The Customer Walkthrough is a guided tour built into the dashboard that highlights key features with tooltip-style popups. You can trigger it during onboarding to make the merchant comfortable navigating on their own.',
        'The walkthrough covers: (1) The stat cards and what each number means. (2) The revenue chart and how to read trends. (3) The Money Left on Table score and how to drill into its components. (4) The Insights tab and how to filter by type. (5) The Agents page and how to see reasoning chains. (6) Settings and how to check connection status.',
        'After the walkthrough, ask the merchant: "Is there anything on this dashboard that doesn\'t make sense?" Address any confusion immediately. The goal is for them to feel confident checking the dashboard independently by the time you leave.',
        'Schedule a follow-up call for 48 hours later: "I\'ll call you Thursday to walk through the insights that have come in. By then, the AI will have found specific opportunities in your data." This follow-up is where you solidify the relationship and start the upsell conversation.',
      ]},
      { id: '53', title: 'First 7 Days After Onboarding', completed: false, content: [
        'Day 1 (Onboarding day): POS connected, wizard completed, customer walkthrough done. Connection status green. Set the expectation that insights take 24 hours to generate.',
        'Day 2: Check the merchant\'s dashboard yourself (via their account or the admin panel). Verify that data is flowing, insights are generating, and no errors are showing. Text the merchant: "Your AI agents found their first insights — check your dashboard! I\'ll call tomorrow to walk through them."',
        'Day 3: Call the merchant. Walk them through the top 3 insights. Focus on the one with the highest dollar amount. Say: "This one insight alone — CA$840/month — pays for your subscription 2x over." Ask if they have questions about any of the numbers.',
        'Day 5–7: Send a follow-up text with a specific insight: "Hey [name], your Peak Hour agent just found that your Tuesday 11 AM–1 PM window is underperforming by 23%. Might be worth looking at your Tuesday specials." This proves the AI is working and keeps them engaged.',
        'If the merchant hasn\'t logged in by day 5, call them. Disengaged merchants churn within 30 days. Your recurring commission depends on them using the product.',
      ]},
      { id: '54', title: 'Handling Onboarding Problems', completed: false, content: [
        '"My POS won\'t connect." — Try a different browser, clear cache, or use incognito mode. Verify the merchant\'s POS subscription is active. If using Clover, the backfill can take up to 2 hours due to API rate limits — set expectations. If nothing works after 10 minutes, escalate to the team and schedule a follow-up.',
        '"The numbers don\'t look right." — Check three things: (1) Timezone settings — the POS and Meridian must match. (2) Refund handling — revenue is net of refunds, transaction count is gross. (3) Date range — the default view is 30 days, not all time. Walk the merchant through these settings.',
        '"I don\'t understand what this means." — This is a training problem, not a product problem. Use the Customer Walkthrough again. Focus on the Overview page and the Top Actions. Say: "Ignore everything else for now — just check these two pages every morning. That\'s all you need to do."',
        '"I\'m too busy to check the dashboard." — Enable the daily email digest in Settings. Say: "You\'ll get one email every morning with yesterday\'s numbers and the top insight. It takes 30 seconds to read. If something needs your attention, you\'ll see it in the email without logging in."',
      ]},
    ],
  },
  {
    id: 'demo-mastery',
    title: 'Demo Environment Mastery',
    description: 'Know every screen of the demo dashboard so you never get caught off guard.',
    icon: Wrench,
    duration: '25 min',
    category: 'Product Knowledge',
    lessons: [
      { id: '55', title: 'The Demo Dashboard Navigation', completed: false, content: [
        'The demo lives at meridian.tips/demo (or meridian.tips/canada/demo for the Canadian version with CAD pricing). It uses pre-built realistic data — no POS connection needed. The demo auto-detects business type and adjusts all product names, prices, and industry benchmarks accordingly.',
        'The left sidebar has 17 navigation items: Overview, Agents, Top Actions, Revenue, Forecasts, Products, Margins, Menu Matrix, Anomalies, Customers, Staff, Peak Hours, Inventory, 3D Space, Phone Orders, Insights, Notifications, and Settings. You should be able to navigate to any of these instantly during a demo.',
        'Business Type Selector: At the top of the demo, merchants can switch between business verticals — Coffee Shop, Restaurant, Fast Food, Auto Shop, Smoke Shop. The entire dashboard updates with industry-specific data: product names, pricing, benchmarks, and agent findings all change. Use this to show "here\'s what it looks like for a [their vertical]."',
        'The demo data is designed to tell a story. The Money Left on Table score is always between CA$2,500–CA$4,000. The top actions are always high-impact and easy to understand. The agent findings always include specific dollar amounts. Don\'t improvise — let the data speak.',
      ]},
      { id: '56', title: 'Key Demo Screens to Master', completed: false, content: [
        'Money Left on Table (Overview page): This is your opening. The big number at the top breaks down into specific categories — pricing gaps, staffing inefficiencies, customer churn, inventory waste. Click into each to show the math behind the number.',
        'Top Actions: This is your closer. Show the #1 ranked action with its full reasoning chain. Walk through: "Here\'s what the AI recommends, here\'s why, here\'s the expected impact, and here\'s how much effort it takes." The reasoning chain (observation → analysis → conclusion → impact) builds trust.',
        'Agents page: This is your differentiator. Scroll through the 37 agents and say: "Each of these is a specialist analyzing your business right now. A human analyst would take weeks to do what these agents do in hours." Click one agent to show its reasoning.',
        'Peak Hours heatmap: This is your most visual screen. The color-coded grid instantly shows busy vs. slow periods. Point to the darkest cells: "This is where you make your money. Are you staffed correctly during these hours?" Then point to gray cells: "And these are your dead zones — should you even be open?"',
      ]},
      { id: '57', title: 'Handling Demo Questions', completed: false, content: [
        '"Is this real data?" — "This is realistic demo data modeled after actual Canadian businesses. When you connect your POS, you\'ll see your own transactions, your own products, and your own revenue — with insights specific to your business."',
        '"How long until I see this for my business?" — "Your POS data starts syncing immediately. Basic revenue analytics appear within an hour. Full AI insights — including the Money Left on Table score — generate within 24 hours. The AI gets more accurate every week as it learns your patterns."',
        '"Can it really predict my revenue?" — "The forecasting model uses your historical transaction data to predict 7, 30, and 90 days out. It accounts for day-of-week patterns, seasonal trends, and growth trajectory. The confidence interval shows you the range — it\'s not a guarantee, it\'s an informed prediction."',
        '"What if I don\'t have 18 months of data?" — "The AI starts working with whatever data your POS has. Even 3 months gives us useful patterns. The more history, the more accurate the forecasts — but you\'ll see value from day one."',
      ]},
      { id: '58', title: 'Demo Mistakes to Avoid', completed: false, content: [
        'Don\'t show every page. The demo has 17 sections — showing all of them overwhelms the prospect and dilutes impact. Pick 3–4 based on their discovery call answers. Less is more.',
        'Don\'t read the screen out loud. The merchant can read. Instead, add context: "See this number? That\'s CA$840 per month you\'d capture just by adjusting one price. The AI did the elasticity math for you."',
        'Don\'t click around aimlessly. Have a plan: Overview → Money Left on Table → one feature that matches their pain → Top Actions → close. Practice this flow until it\'s smooth.',
        'Don\'t demo on a slow connection or a cluttered browser. Use a clean browser window, dark mode (default), and 125% zoom. Test the URL before the call. Nothing kills momentum like "sorry, it\'s loading..."',
        'Don\'t panic if they ask about a feature you don\'t know. Say: "Great question — let me get you the exact answer on that and follow up today." Then actually follow up. Honesty beats faking it every time.',
      ]},
    ],
  },
]

const SECTIONS = [
  {
    title: 'How to Sell a Deal (5-Step SOP)',
    description: 'Follow these steps from first contact to closed deal.',
    moduleIds: ['onboarding', 'pitch', 'demo'],
  },
  {
    title: 'Know the Product Inside Out',
    description: 'Every dashboard screen, AI agent, and feature — explained for reps.',
    moduleIds: ['dashboard-overview', 'ai-agents', 'onboarding-flow', 'demo-mastery'],
  },
  {
    title: 'Sales Knowledge',
    description: 'Deepen your expertise across verticals and techniques.',
    moduleIds: ['verticals', 'advanced'],
  },
  {
    title: 'Compliance & Ethics',
    description: 'Required training for all sales representatives.',
    moduleIds: ['compliance'],
  },
  {
    title: 'Technical Guides',
    description: 'Camera Intelligence setup and POS connection walkthroughs.',
    moduleIds: ['camera', 'pos-guides'],
  },
  {
    title: 'Quick Reference',
    description: 'Handy tips for the Canadian market.',
    moduleIds: ['quicktips'],
  },
]

export default function CanadaPortalTrainingPage() {
  const [expandedModuleId, setExpandedModuleId] = useState<string | null>('onboarding')
  const [expandedLessonId, setExpandedLessonId] = useState<string | null>(null)
  const [completedLessons, setCompletedLessons] = useState<Set<string>>(() => {
    const saved = localStorage.getItem('meridian_training_progress')
    if (saved) {
      try { return new Set(JSON.parse(saved) as string[]) } catch { /* fall through */ }
    }
    return new Set<string>()
  })

  const totalLessons = MODULES.reduce((s, m) => s + m.lessons.length, 0)
  const completedCount = completedLessons.size
  const progressPct = Math.round((completedCount / totalLessons) * 100)

  function toggleComplete(lessonId: string) {
    setCompletedLessons(prev => {
      const next = new Set(prev)
      if (next.has(lessonId)) next.delete(lessonId)
      else next.add(lessonId)
      localStorage.setItem('meridian_training_progress', JSON.stringify([...next]))
      return next
    })
  }

  let globalStep = 0

  return (
    <div className="min-h-screen bg-[#0a0f0d] space-y-6 p-1">
      <div>
        <h1 className="text-xl font-bold text-white">Training</h1>
        <p className="text-sm text-[#6b7a74] mt-0.5">Level up your sales skills with guided modules.</p>
      </div>

      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart3 size={16} className="text-[#00d4aa]" />
            <span className="text-sm font-semibold text-white">Your Progress</span>
          </div>
          <span className="text-sm font-bold text-[#00d4aa]">{progressPct}%</span>
        </div>
        <div className="w-full h-2 bg-[#1a2420] rounded-full overflow-hidden">
          <div className="h-full bg-[#00d4aa] rounded-full transition-all duration-500" style={{ width: `${progressPct}%` }} />
        </div>
        <p className="text-[10px] text-[#4a5550] mt-2">{completedCount} of {totalLessons} lessons completed</p>
      </div>

      {SECTIONS.map((section) => {
        const sectionModules = section.moduleIds.map(id => MODULES.find(m => m.id === id)!).filter(Boolean)
        return (
          <div key={section.title} className="space-y-3">
            <div className="mb-2">
              <h2 className="text-[14px] font-semibold text-white">{section.title}</h2>
              <p className="text-[11px] text-[#6b7a74] mt-0.5">{section.description}</p>
            </div>

            {sectionModules.map(mod => {
              globalStep++
              const stepNum = globalStep
              const modCompleted = mod.lessons.filter(l => completedLessons.has(l.id)).length
              const isExpanded = expandedModuleId === mod.id
              const Icon = mod.icon

              return (
                <div key={mod.id} className="bg-[#0f1512] border border-[#1a2420] rounded-xl overflow-hidden">
                  <button
                    onClick={() => setExpandedModuleId(isExpanded ? null : mod.id)}
                    className="w-full px-4 sm:px-5 py-4 flex items-center gap-3 text-left hover:bg-[#0f1512]/80 transition-colors"
                  >
                    <div className="w-7 h-7 rounded-full bg-[#00d4aa]/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-[11px] font-bold text-[#00d4aa]">{stepNum}</span>
                    </div>
                    <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center flex-shrink-0">
                      <Icon size={16} className="text-[#00d4aa]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] font-semibold text-white">{mod.title}</p>
                      <p className="text-[10px] text-[#6b7a74] truncate mt-0.5">{mod.description}</p>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <div className="text-right">
                        <p className="text-[10px] font-medium text-[#6b7a74]">{modCompleted}/{mod.lessons.length}</p>
                        <p className="text-[9px] text-[#4a5550]">{mod.duration}</p>
                      </div>
                      <ChevronRight size={14} className={clsx('text-[#4a5550] transition-transform', isExpanded && 'rotate-90')} />
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="border-t border-[#1a2420]">
                      {mod.lessons.map((lesson, i) => {
                        const isLessonOpen = expandedLessonId === lesson.id
                        const isComplete = completedLessons.has(lesson.id)
                        return (
                          <div key={lesson.id} className={clsx(i < mod.lessons.length - 1 && 'border-b border-[#1a2420]/50')}>
                            <button
                              onClick={() => setExpandedLessonId(isLessonOpen ? null : lesson.id)}
                              className="w-full px-5 py-3 flex items-center gap-3 text-left hover:bg-[#1a2420]/30 transition-colors"
                            >
                              <button
                                onClick={(e) => { e.stopPropagation(); toggleComplete(lesson.id) }}
                                className="flex-shrink-0"
                              >
                                {isComplete ? (
                                  <CheckCircle2 size={16} className="text-[#00d4aa]" />
                                ) : (
                                  <div className="w-4 h-4 rounded-full border border-[#2a3a34] hover:border-[#00d4aa]/50 transition-colors" />
                                )}
                              </button>
                              <span className={clsx('text-[11px] font-medium flex-1', isComplete ? 'text-[#6b7a74]' : 'text-white')}>
                                {lesson.title}
                              </span>
                              {isLessonOpen ? (
                                <ChevronDown size={12} className="text-[#00d4aa] flex-shrink-0" />
                              ) : (
                                <ChevronRight size={12} className="text-[#4a5550] flex-shrink-0" />
                              )}
                            </button>

                            {isLessonOpen && (
                              <div className="px-5 pb-4 pl-12 space-y-3">
                                {lesson.content.map((paragraph, pi) => (
                                  <p key={pi} className="text-[12px] leading-relaxed text-[#9ca3a0]">{paragraph}</p>
                                ))}
                                {!isComplete && (
                                  <button
                                    onClick={() => toggleComplete(lesson.id)}
                                    className="mt-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20 text-[#00d4aa] text-[11px] font-medium hover:bg-[#00d4aa]/20 transition-colors"
                                  >
                                    <CheckCircle2 size={12} /> Mark Complete
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}
