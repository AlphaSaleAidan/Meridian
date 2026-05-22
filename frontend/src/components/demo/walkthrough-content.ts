import type { BusinessType } from '@/lib/demo-context'

export type PortalContext = 'us' | 'canada'
export type StepId = 'hook' | 'anomaly' | 'forecast' | 'customers' | 'staff' | 'insights' | 'close'

export interface WalkthroughStep {
  id: StepId
  name: string
  tabPath: string
  elementSelector: string
  fallbackSelector: string
  spotlightPadding: number
}

export interface CoachingContent {
  title: string
  sayThis: string
  whyItWorks: string
  likelyResponse: string
  likelyAnswer: string
  whatToDo: string
}

export const WALKTHROUGH_STEPS: WalkthroughStep[] = [
  {
    id: 'hook',
    name: 'The Hook',
    tabPath: '',
    elementSelector: '[data-walkthrough="money-left-score"]',
    fallbackSelector: '.glow-violet',
    spotlightPadding: 24,
  },
  {
    id: 'anomaly',
    name: 'The Anomaly',
    tabPath: 'anomalies',
    elementSelector: '[data-walkthrough="top-anomaly"]',
    fallbackSelector: '.card-hover',
    spotlightPadding: 16,
  },
  {
    id: 'forecast',
    name: 'The Forecast',
    tabPath: 'forecasts',
    elementSelector: '[data-walkthrough="revenue-forecast-chart"]',
    fallbackSelector: '.recharts-responsive-container',
    spotlightPadding: 20,
  },
  {
    id: 'customers',
    name: 'The Customers',
    tabPath: 'customers',
    elementSelector: '[data-walkthrough="at-risk-segment"]',
    fallbackSelector: '.card p',
    spotlightPadding: 16,
  },
  {
    id: 'staff',
    name: 'The Staff Problem',
    tabPath: 'peak-hours',
    elementSelector: '[data-walkthrough="peak-heatmap"]',
    fallbackSelector: '.card',
    spotlightPadding: 20,
  },
  {
    id: 'insights',
    name: 'The AI Insights',
    tabPath: 'insights',
    elementSelector: '[data-walkthrough="first-insight"]',
    fallbackSelector: '.card-hover',
    spotlightPadding: 16,
  },
  {
    id: 'close',
    name: 'The Close',
    tabPath: '',
    elementSelector: '[data-walkthrough="connect-pos-cta"]',
    fallbackSelector: '.glow-violet',
    spotlightPadding: 24,
  },
]

// ─── Per-type step names shown in the coaching card header ───

const STEP_NAMES: Record<string, Record<StepId, string>> = {
  restaurant: {
    hook: 'The Money Left',
    anomaly: 'The Void Spike',
    forecast: 'The Empty Tables',
    customers: 'The Regulars Leaving',
    staff: 'The Friday Night Problem',
    insights: 'The Server Insight',
    close: 'The Close',
  },
  fast_food: {
    hook: 'The Drive-Thru Gap',
    anomaly: 'The Comp Pattern',
    forecast: 'The Saturday Surge',
    customers: 'The Lunch Crowd',
    staff: 'The Rush Window',
    insights: 'The Speed Insight',
    close: 'The Close',
  },
  coffee_shop: {
    hook: 'The Morning Rush',
    anomaly: 'The Free Drink Flag',
    forecast: 'The Monday Spike',
    customers: 'The Loyal Lapsers',
    staff: 'The Barista Gap',
    insights: 'The Upsell Insight',
    close: 'The Close',
  },
  auto_shop: {
    hook: 'The Bay Revenue',
    anomaly: 'The Write-Off Alert',
    forecast: 'The Slow Week',
    customers: 'The One-Visit Customer',
    staff: 'The Idle Bay',
    insights: 'The Service Advisor Insight',
    close: 'The Close',
  },
  smoke_shop: {
    hook: 'The Shelf Blind Spot',
    anomaly: 'The Shrinkage Flag',
    forecast: 'The Weekend Pattern',
    customers: 'The Vape Regulars',
    staff: 'The Afternoon Surge',
    insights: 'The Product Mix Insight',
    close: 'The Close',
  },
}

export function getStepName(stepId: StepId, businessType: BusinessType): string {
  return STEP_NAMES[businessType]?.[stepId] || WALKTHROUGH_STEPS.find(s => s.id === stepId)!.name
}

// ─── Fully unique coaching content per business type ───

function restaurantContent(portalContext: PortalContext): Record<StepId, CoachingContent> {
  const currency = portalContext === 'canada' ? 'CA$' : '$'
  const opp = portalContext === 'canada' ? '65,580' : '47,230'
  const price = portalContext === 'canada' ? '339' : '250'
  return {
    hook: {
      title: 'The Money Left on the Table',
      sayThis: `See this number? ${currency}${opp} per month.\n\n[pause 3 seconds]\n\nThat's what our AI says your restaurant is leaving on the table right now. It's broken down into five buckets — underpriced entrées, dead menu items nobody orders, server upsell gaps, peak-hour understaffing, and discount leakage.\n\nLet me show you exactly where each dollar is coming from.`,
      whyItWorks: 'Restaurant owners think in terms of food cost and covers. Showing them a single number that bundles five different leaks is new — and the specificity of "underpriced entrées" and "dead menu items" tells them this isn\'t generic.',
      likelyResponse: 'How do you know my menu is underpriced?',
      likelyAnswer: `We compare your average ticket against similar restaurants in your area — same cuisine type, similar seating capacity. When your Ribeye is $34.95 and comparable places charge $38–42, that gap compounds across hundreds of covers. We're not guessing — we're pulling real pricing data.`,
      whatToDo: 'Don\'t click anything yet. Let them absorb the total. Then slowly scroll to show the five component bars below. Point at "Underpriced Products" — that one always gets a reaction from restaurant owners.',
    },
    anomaly: {
      title: 'The Void Spike That Tells a Story',
      sayThis: `See this alert? Friday night — your busiest night — there was a spike in voids and comps on one register between 8pm and 10pm.\n\n[pause]\n\nThe AI flagged it because the pattern doesn't match normal operations. Could be a training issue, could be something else. But without this, you'd never see it in the noise of a busy dinner service.\n\nWould you want to know if this was happening every Friday?`,
      whyItWorks: 'Every restaurant owner has had a bartender or server they suspected but couldn\'t prove anything. Friday dinner service is the exact moment they can\'t watch everything — and they know it.',
      likelyResponse: 'We already watch the cameras',
      likelyAnswer: 'Cameras tell you what happened after you already know something\'s wrong. This tells you something IS wrong before you know to look. You\'re not going to rewatch 4 hours of Friday footage on a hunch — but the AI just told you exactly which register, which 2-hour window, and how much the deviation was. Now you know where to point the camera.',
      whatToDo: 'Click into the anomaly detail if available. Point out the specific time window, the register ID, and the deviation percentage. Let them sit with it.',
    },
    forecast: {
      title: 'Know Your Slow Nights Before They Happen',
      sayThis: `This is your next 7 days of revenue.\n\nSee Tuesday? The AI predicts it's going to be 18% below your average. And Thursday is looking strong — possibly your second-best night this week.\n\n[pause]\n\nIf you knew Tuesday was going to be slow, would you still schedule a full kitchen line? And if you knew Thursday was going to pop, would you have enough servers on?`,
      whyItWorks: 'Restaurants over-staff slow nights and under-staff busy ones because they schedule based on last week, not next week. The forecast makes them realize they\'ve been flying blind on labor.',
      likelyResponse: 'We just go by what last week looked like',
      likelyAnswer: 'That\'s what everyone does — and it\'s why restaurants over-spend on labor 15-20%. Last Tuesday isn\'t next Tuesday. The AI factors in weather, local events, holidays, seasonal patterns, and your own historical trends. After 90 days, the 7-day forecast is within 8-12% of actual.',
      whatToDo: 'Toggle to the 30-day view. Point out the weekend peaks vs weekday valleys. Ask: "If you could see this every Monday morning, how would that change your prep orders for the week?"',
    },
    customers: {
      title: 'Your Regulars Are Leaving and You Don\'t Know It',
      sayThis: `Look at this — "Needs Action." These are customers who used to dine with you at least twice a month. They haven't been back in 45+ days.\n\n[point to the total spend number]\n\nThat's how much revenue is walking out the door. Not to a competitor necessarily — maybe they moved, maybe they got bored of the menu, maybe a bad experience. But you don't know because nobody's tracking it.\n\nWhen's the last time you personally called a regular who stopped showing up?`,
      whyItWorks: 'Every restaurant owner has a "where did so-and-so go?" moment. This turns that anecdote into data. The spend number makes the loss tangible.',
      likelyResponse: 'I know my regulars — I\'d notice',
      likelyAnswer: 'You know your top 10. But what about the couple that came every other Thursday for 6 months and quietly stopped? You\'d never notice them individually. The AI tracks all of them and tells you when the pattern breaks — before they become a lost customer.',
      whatToDo: 'Click into the At Risk segment. Show the individual customer rows if visible. Point out the "days since last visit" column — the 60+ day ones are probably gone. The 30-45 day ones are still recoverable.',
    },
    staff: {
      title: 'Your Friday Night Is Under-Resourced',
      sayThis: `This heatmap — see this dark cell? Friday, 7:00–8:30pm. That's your single highest-revenue hour of the entire week.\n\n[pause]\n\nAre you 100% sure you have your strongest server team on the floor at that exact moment every Friday?\n\n[wait for answer]\n\nMost restaurants we talk to find they're running one server short during their peak dinner window. One server short for 3 hours means slower turns, lower tips, and tables that don't order dessert or that second bottle of wine.`,
      whyItWorks: 'They know Friday dinner is busy. They don\'t know the EXACT revenue impact of being one server short. The dessert/wine detail is specific enough to feel real.',
      likelyResponse: 'We can\'t always get people to work Fridays',
      likelyAnswer: 'Right — and that\'s exactly why this matters. If you know Friday 7-9pm is worth 3x what Tuesday lunch is, you can pay a premium for that shift and still come out ahead. The AI quantifies the gap so you can make the case to your team: "This shift is worth $X more to the house — here\'s the bonus to match."',
      whatToDo: 'After the heatmap, mention that the Insights tab calculates the exact dollar cost of understaffing during peak hours. That\'s the bridge to the next step.',
    },
    insights: {
      title: 'Your AI Tells You to Raise the Salmon by $2',
      sayThis: `Read this insight.\n\n[let them read for 10 seconds]\n\nThe AI didn't just notice your Grilled Salmon is underpriced — it calculated exactly how much raising it by $2 would add per month, based on your current order volume. And it checked that the new price still falls within the competitive range for your area.\n\n[point to the dollar amount]\n\nThat's one menu change. One number on the menu. This dashboard finds 10 of these every week.`,
      whyItWorks: 'Menu pricing is the single highest-leverage thing a restaurant owner can change. It costs nothing to implement and the impact is immediate. "$2 on the salmon" is so specific it feels like advice from a consultant, not a dashboard.',
      likelyResponse: 'I don\'t want to raise prices and lose customers',
      likelyAnswer: 'That\'s the instinct everyone has. But the AI checks your price elasticity — it knows which items customers buy regardless of small price changes. Your Salmon has a 0.80 popularity score — demand is strong. A $2 increase won\'t move the needle on orders, but it moves the margin significantly. The insight shows you the math.',
      whatToDo: 'Click through 2-3 insights. Find one about staffing and one about menu engineering. Show that each insight has a recommended action AND a dollar impact. This isn\'t a dashboard you stare at — it tells you what to do.',
    },
    close: {
      title: 'The Bridge to Their Real Numbers',
      sayThis: portalContext === 'canada'
        ? `Everything I just showed you — the void alerts, the forecast, the menu pricing — that's sample data for a Canadian restaurant.\n\nWith your actual Square or Moneris data? The AI rewrites every insight for YOUR menu, YOUR staff, YOUR customers. CA$${price}/month. First month free.\n\n[pause]\n\nWhat POS are you running?`
        : `Everything I just showed you — the void alerts, the forecast, the menu pricing — that's based on typical restaurant data.\n\nWith your actual POS connected? Every insight rewrites itself for YOUR menu, YOUR staff patterns, YOUR customer base. $${price}/month. First month free, no credit card.\n\n[pause]\n\nAre you on Square, Toast, or something else?`,
      whyItWorks: 'By now they\'ve seen 6 features framed around their specific pain points. The close doesn\'t ask for a decision — it asks about their POS, which assumes the decision is already made.',
      likelyResponse: 'Let me think about it',
      likelyAnswer: portalContext === 'canada'
        ? 'Totally fair. The first month is free — no contract, cancel anytime. The only question is: would you rather see your real numbers or keep guessing on menu pricing and staffing? Most of our Canadian restaurant owners tell us the anomaly alerts alone pay for the subscription.'
        : 'Of course. The first month is free and there\'s nothing to sign. Most restaurant owners tell us the first insight that pays for itself is a menu pricing change — usually within the first week. You\'ve got nothing to lose.',
      whatToDo: 'When they name their POS, show how the connection works. Square is a single OAuth button. Toast takes about 5 minutes. Emphasize: "By tomorrow morning, you\'re looking at your real data."',
    },
  }
}

function fastFoodContent(portalContext: PortalContext): Record<StepId, CoachingContent> {
  const currency = portalContext === 'canada' ? 'CA$' : '$'
  const opp = portalContext === 'canada' ? '43,670' : '31,440'
  const price = portalContext === 'canada' ? '339' : '250'
  return {
    hook: {
      title: 'The Drive-Thru Revenue Gap',
      sayThis: `See this number? ${currency}${opp} a month.\n\n[pause]\n\nThat's what you're losing between combo upsells that aren't happening, drive-thru bottlenecks at peak lunch, dead menu items taking up board space, and scheduling gaps during your Saturday rush.\n\nThe biggest chunk? Missed upsell opportunities at the order window. Let me show you.`,
      whyItWorks: 'QSR owners think in terms of speed and throughput. Framing the loss as "drive-thru bottlenecks" and "order window upsells" speaks their exact language — not generic "revenue opportunity."',
      likelyResponse: 'We already push combos',
      likelyAnswer: `Your crew pushes combos — but how consistently? The AI tracks upsell rate per shift, per register, per employee. If your lunch crew upsells 34% of the time but your evening crew only hits 18%, that's the gap. It's not about the script — it's about who's actually doing it and when.`,
      whatToDo: 'Scroll to the upsell component in the Money Left breakdown. Point out the difference between what the best shift does and what the worst shift does. That gap IS the opportunity.',
    },
    anomaly: {
      title: 'The Comp Pattern Nobody Catches',
      sayThis: `See this flag? Saturday lunch — your peak — there's a spike in comps and cancelled orders on one register.\n\n[pause]\n\nIn a fast food operation, comps at lunch are almost always one of two things: a training problem or a pattern. The AI can't tell you which — but it can tell you it's happening every Saturday, same register, same 2-hour window.\n\nWith 200 transactions flying through during lunch rush, would you have caught that yourself?`,
      whyItWorks: 'Fast food managers can\'t watch every register during a 200-ticket lunch rush. They know it. This acknowledges the reality of their workload while showing the AI catches what they physically can\'t.',
      likelyResponse: 'My managers should be catching that',
      likelyAnswer: 'Your managers are working the line during rush. They\'re expediting, not auditing. That\'s the right call — you need them on the floor. But who\'s watching the register patterns while they\'re making food? The AI does that job 24/7 without pulling anyone off the line.',
      whatToDo: 'Click into the anomaly. Show the time pattern — same register, same shift. Ask: "Who\'s on that register during Saturday lunch?" Let them connect the dots.',
    },
    forecast: {
      title: 'Your Saturday Is 40% of Your Week',
      sayThis: `Look at this forecast — Saturday alone accounts for nearly 40% of your weekly revenue.\n\n[pause]\n\nNow look at Tuesday. It's your weakest day — less than half of Saturday.\n\nIf you're prepping the same amount of food for Tuesday as Saturday, you're either throwing away food or running short. The AI gives you this breakdown for every day of the coming week.\n\nHow do you currently decide how much to prep each morning?`,
      whyItWorks: 'Fast food waste is a massive margin killer. Framing the forecast around PREP instead of revenue is the angle that makes QSR operators lean in — they live and die by food waste.',
      likelyResponse: 'We go by yesterday\'s numbers',
      likelyAnswer: 'Yesterday\'s numbers don\'t account for weather, school schedules, local events, or seasonal patterns. The AI does. After 90 days, it tells you not just how much revenue to expect — but which items will move fastest. That means you prep the right amount of beef vs chicken, the right number of buns, the right amount of fries. Less waste, fewer stockouts.',
      whatToDo: 'Point out the day-by-day variance. Ask: "What\'s your food waste percentage?" — whatever they say, the forecast cuts it. That\'s real money.',
    },
    customers: {
      title: 'Your Lunch Crowd Is Thinning',
      sayThis: `This "Needs Action" segment — these are regulars who used to come in at least weekly. They haven't been back in over a month.\n\n[point to the count]\n\nIn fast food, a regular is worth $15-25 a week. Multiply that by 52 weeks. Now multiply by this number of customers you're losing.\n\nThat's not a rounding error. That's a second location's worth of revenue walking to your competitor.`,
      whyItWorks: 'Fast food margins are thin — every regular matters. Framing the loss as "a second location\'s worth of revenue" is dramatic but mathematically defensible for high-volume QSR.',
      likelyResponse: 'Fast food customers aren\'t loyal — they go wherever',
      likelyAnswer: 'That\'s the old model. The data says otherwise — about 35% of fast food revenue comes from customers who visit 2+ times per week. Those are habitual customers, and when they break the habit, they rarely come back on their own. The AI identifies them at the 3-week mark — early enough to win them back with a targeted offer.',
      whatToDo: 'Point out the frequency data. Show that the "Champions" segment has a much higher visit rate. Ask: "Do you know how many of your customers come in more than once a week?" The answer will surprise them.',
    },
    staff: {
      title: 'Your 12pm Rush Is a Bottleneck',
      sayThis: `This heatmap — see this dark block? Saturday, 12:00–1:00pm. That's your highest-revenue hour.\n\n[pause]\n\nHow many people are on the line right now during that hour?\n\n[wait]\n\nEvery minute your drive-thru wait time goes above 3 minutes during peak, you lose cars. The AI measured that this window generates 2.5x the revenue of your average hour — but your staffing doesn't match. You're running the same crew size at noon as you are at 3pm.`,
      whyItWorks: 'Drive-thru wait time is the metric that keeps QSR operators up at night. Connecting the heatmap to "you lose cars" makes the data feel like lost revenue, not just a pretty chart.',
      likelyResponse: 'We can\'t get enough people to work lunch',
      likelyAnswer: 'If Saturday noon is worth 2.5x what a regular hour is worth, can you afford to pay $2/hour more for that specific shift? The AI doesn\'t just show you the problem — the Insights tab calculates what solving it is worth. Usually the premium pay pays for itself 3-4x over in throughput.',
      whatToDo: 'Compare the noon block to the 3pm block visually. The difference is stark. Then say: "Let me show you what the AI recommends" and move to insights.',
    },
    insights: {
      title: 'Your AI Says: Add One Person at Noon',
      sayThis: `Read this.\n\n[10 seconds]\n\nThe AI calculated that adding one crew member to your Saturday lunch window would increase throughput by 15-20% — because the bottleneck is the second prep station, not the register.\n\n[point to the dollar figure]\n\nThat's the revenue increase per month from solving this one problem. The cost of the extra shifts is about a third of that number. Net positive from week one.`,
      whyItWorks: 'The specificity of "second prep station, not the register" shows this isn\'t generic advice. It sounds like something an operations consultant would say after watching your kitchen for a week.',
      likelyResponse: 'How does it know it\'s the prep station?',
      likelyAnswer: 'It analyzes order-to-completion time patterns. When the bottleneck is the register, average ticket time is consistent but fewer tickets get started. When it\'s prep, tickets start fast but completion time spikes. Your data shows completion time spiking during rush — that\'s a prep constraint. The AI explains its reasoning right here.',
      whatToDo: 'Click through another insight — ideally one about combo attach rates or dead menu items. Show breadth: "It\'s not just staffing — it finds revenue in every part of your operation."',
    },
    close: {
      title: 'The Bridge to Real Throughput Data',
      sayThis: portalContext === 'canada'
        ? `Everything I just showed you — the drive-thru gaps, the prep forecasts, the crew bottlenecks — that's sample data.\n\nWith your actual POS? The AI rewrites everything for YOUR location, YOUR menu, YOUR crew patterns. CA$${price}/month, first month free.\n\n[pause]\n\nAre you on Square, Moneris, or a custom POS?`
        : `Everything I just showed you — the drive-thru gaps, the prep forecasts, the crew bottlenecks — that's modeled from typical QSR data.\n\nConnect your POS and by tomorrow morning you'll see YOUR lunch rush, YOUR throughput gaps, YOUR upsell rates by employee. $${price}/month. First month free, cancel anytime.\n\n[pause]\n\nWhat system are you running — Square, Toast, Clover?`,
      whyItWorks: 'QSR operators are action-oriented. They don\'t "think about it" — they either see the ROI or they don\'t. By this point, the throughput and crew insights have made the ROI obvious.',
      likelyResponse: 'I need to talk to my franchise group',
      likelyAnswer: portalContext === 'canada'
        ? 'Totally fair. Want me to send you a one-pager you can forward? Shows the ROI calculation for a single-location QSR. The free month means there\'s no risk for a trial — and the data you collect during the trial becomes the business case for rollout.'
        : 'Understood. Do you want me to send a summary you can forward? The free month means zero risk — and the data you collect during the trial becomes the pitch to the franchise group. Most operators we work with start with one location and expand from the data.',
      whatToDo: 'If they need to check with someone, offer to email a summary. If they\'re the decision-maker, walk them through the POS connection right now — "Takes 4 minutes, let\'s just do it while we\'re here."',
    },
  }
}

function coffeeShopContent(portalContext: PortalContext): Record<StepId, CoachingContent> {
  const currency = portalContext === 'canada' ? 'CA$' : '$'
  const opp = portalContext === 'canada' ? '26,340' : '18,920'
  const price = portalContext === 'canada' ? '339' : '250'
  return {
    hook: {
      title: 'Your Morning Rush Is Leaving Money Behind',
      sayThis: `See this number? ${currency}${opp} a month.\n\n[pause]\n\nFor a coffee shop, the biggest piece of that is the gap between drinks-only orders and drinks-plus-food orders. Your average ticket on a latte alone is $5.25. A latte plus a croissant is $9.50. The AI says you're converting drink-to-food only 28% of the time during morning rush.\n\nThat pastry attach rate is where most of this money is hiding.`,
      whyItWorks: 'Coffee shop owners live and die by average ticket. The croissant/pastry attach rate is something they think about but never measure precisely. Giving them the exact percentage makes them want to see their real number.',
      likelyResponse: 'We display pastries right at the counter',
      likelyAnswer: `Display helps, but the data shows attach rates vary 2x between baristas. Some ask "would you like a pastry with that?" and some don't. The AI breaks it down by employee — you'll see which baristas naturally upsell and which ones need coaching. It's not about the display case — it's about the ask.`,
      whatToDo: 'Scroll through the Money Left components. Point out "Upsell Potential" — that\'s the pastry attach gap. Then point at "Peak Hour Gaps" — that\'s the 7:15am crush where you\'re one barista short.',
    },
    anomaly: {
      title: 'The Free Drink Flag',
      sayThis: `This alert — see this? Monday morning, there's a pattern of voided drink orders between 7 and 8am.\n\n[pause]\n\nIn a coffee shop, voided drinks during peak usually means one of two things: either the barista is remaking drinks that were made wrong, which is a training issue — or drinks are being made and voided after the fact. The AI doesn't know which, but it knows it's happening consistently.\n\nDo you track your void rate per barista right now?`,
      whyItWorks: 'Coffee shop margins on drinks are high, but "free drinks" culture is real. Every café owner has wondered if their baristas are making drinks for friends. This gives them a way to check without accusing anyone.',
      likelyResponse: 'My baristas wouldn\'t do that',
      likelyAnswer: 'And they probably aren\'t. Could be remakes — which is still money. If your barista lead is remaking 8 lattes a shift because of order confusion, that\'s $30/day in milk and labor. The AI shows you the pattern so you can have a data-driven conversation instead of a suspicion-driven one. Usually it\'s a workflow issue, not a trust issue.',
      whatToDo: 'Click into the anomaly. Show the specific time window and the void count. Ask: "How many remakes do you think happen during morning rush?" Whatever they guess, the data will be higher.',
    },
    forecast: {
      title: 'Monday Is Your Real Peak — Not Saturday',
      sayThis: `Most people assume weekends are busiest. Look at this — your Monday morning between 7:30 and 9:00 generates more revenue than any other window of the week.\n\n[pause]\n\nSaturday has higher foot traffic, but Monday morning has the highest average ticket — commuters want their coffee fast and they add food because they skipped breakfast. The forecast shows you this pattern week after week.\n\nAre you staffing Monday morning like it's your biggest day?`,
      whyItWorks: 'This is genuinely counterintuitive for most café owners. They over-staff weekends and under-staff Monday AM. The data proves it and makes them realize their scheduling is backwards.',
      likelyResponse: 'Really? Monday is bigger than Saturday?',
      likelyAnswer: 'In revenue per hour, yes — and by a significant margin. Saturday has more foot traffic but lower tickets — people browse, they\'re not rushed. Monday commuters order quickly, add food, and leave. The AI breaks this down by day so you can optimize both staffing and prep.',
      whatToDo: 'Toggle the forecast view to show daily patterns. Point out Monday vs Saturday revenue. Ask: "How many baristas do you have Monday at 7:30am vs Saturday at 10am?" The answer will reveal the misallocation.',
    },
    customers: {
      title: 'Your Loyal Lapsers Are Slipping Away',
      sayThis: `This segment — these are people who came in 3-4 times a week and stopped. Not tourists, not one-timers — your regulars.\n\n[pause]\n\nFor a coffee shop, losing a regular is losing $20/week, 52 weeks a year. That's over $1,000 per customer per year.\n\n[point to the count]\n\nMultiply that. When's the last time you noticed a regular stop coming in and actually did something about it?`,
      whyItWorks: 'Coffee shop regulars are the most habitual customers in any retail category. When they leave, the per-customer loss is enormous relative to ticket size. The $1,000/year math hits hard.',
      likelyResponse: 'We see the same faces every day — we\'d notice',
      likelyAnswer: 'You\'d notice your top 5. But what about the woman who always came at 7:45 on Tuesdays and Thursdays? If she stops coming, would you notice at 7:45 on a busy Tuesday? The AI catches every single pattern break — not just the faces you recognize.',
      whatToDo: 'Show the At Risk customer count. Ask: "If I told you there was a way to send each of these customers a \'we miss you — free pastry with your next latte\' message, would you do it?" — that sets up the retention conversation.',
    },
    staff: {
      title: 'Your 7:30am Barista Gap',
      sayThis: `Look at this — Monday, 7:30–9:00am. Darkest cell on the heatmap. That's not just your busiest window — it's your highest-margin window because commuters don't price-compare their morning latte.\n\n[pause]\n\nHow fast is your line moving at 7:45 on a Monday?\n\n[wait]\n\nEvery person who looks through the window, sees a 6-person line, and keeps walking is $5-10 you never get back. And they might not come back tomorrow either — they'll find another shop with a shorter line.`,
      whyItWorks: 'The "walk-away" scenario is visceral for café owners. They\'ve seen people look at the line and leave. Connecting that to the heatmap makes it quantifiable instead of anecdotal.',
      likelyResponse: 'We open with two baristas — that\'s all we can afford',
      likelyAnswer: 'If adding a third barista from 7 to 9am costs you $30/day, and each walk-away is a $6 sale you lost — how many walk-aways per day before the third barista pays for herself? The AI calculates that in the Insights section. Usually it\'s 5-6 walk-aways. Are you losing more than 6 people a morning? Most cafés are.',
      whatToDo: 'Let them sit with the heatmap. Then say: "The Insights tab has the exact math on this — let me show you the ROI of one extra barista during peak." Move to insights.',
    },
    insights: {
      title: 'Your AI Says: Push Croissants Before 9am',
      sayThis: `Read this insight.\n\n[10 seconds]\n\nThe AI noticed that your croissant sales drop 60% after 9am — but your baristas aren't mentioning pastries during morning rush because they're focused on speed. It calculated that if your team asked "pastry with that?" on just 30% of morning drink orders, it would add this much per month.\n\n[point to the dollar figure]\n\nOne sentence. Thirty percent of the time. That's the entire insight. No workflow change, no new product, no cost.`,
      whyItWorks: 'The simplicity is the sell. "One sentence, 30% of the time" is so achievable it removes all friction. The AI just told them exactly what to do and exactly what it\'s worth.',
      likelyResponse: 'My baristas are already slammed during morning rush',
      likelyAnswer: 'That\'s why it says 30%, not 100%. Not every customer, not every drink. Just the ones where there\'s a natural pause — while the espresso is pulling. "Croissant with that?" takes 2 seconds. The insight isn\'t asking them to slow down — it\'s asking them to fill a 15-second gap they already have.',
      whatToDo: 'Show another insight — ideally one about dead stock (Hot Chocolate in summer, for example) or a pricing recommendation. The variety shows this isn\'t one trick — it\'s an analyst working for you every week.',
    },
    close: {
      title: 'See Your Real Morning Rush',
      sayThis: portalContext === 'canada'
        ? `Everything I just showed you — the morning rush patterns, the pastry attach rates, the barista gaps — that's sample data for a Canadian café.\n\nWith your actual data? The AI rewrites every insight for YOUR menu, YOUR peak hours, YOUR team. CA$${price}/month, first month free.\n\n[pause]\n\nWhat are you running — Square, Moneris, Clover?`
        : `Everything I just showed you — the morning rush patterns, the pastry attach rates, the walk-away math — that's sample café data.\n\nConnect your POS and the AI recalculates everything for YOUR shop. Your real morning rush. Your real attach rates. Your real staff gaps. $${price}/month, first month free.\n\n[pause]\n\nWhat POS are you on?`,
      whyItWorks: 'By now they\'ve heard three insights specific to café operations. The close ties back to "your morning rush" — the thing they think about every single day.',
      likelyResponse: 'Can I try it on a quieter week first?',
      likelyAnswer: portalContext === 'canada'
        ? 'Absolutely — and the first month is free so there\'s no cost to a trial. But honestly, the more data it has, the better the insights get. Starting during a busy month means the AI learns your peak patterns faster. Most café owners tell us they see the first useful insight within 3-4 days.'
        : 'Sure — but the AI actually gets better during busy weeks because there\'s more data to learn from. The first month is free regardless, so there\'s no cost to starting now. Most shops see the first actionable insight within a few days.',
      whatToDo: 'Walk them through the POS connection. Emphasize speed: "Square connects in 60 seconds — one OAuth button." If they use a less common system, show the full integration list.',
    },
  }
}

function autoShopContent(portalContext: PortalContext): Record<StepId, CoachingContent> {
  const currency = portalContext === 'canada' ? 'CA$' : '$'
  const opp = portalContext === 'canada' ? '72,410' : '52,180'
  const price = portalContext === 'canada' ? '339' : '250'
  return {
    hook: {
      title: 'The Revenue Sitting in Empty Bays',
      sayThis: `See this number? ${currency}${opp} a month.\n\n[pause]\n\nFor an auto shop, that breaks down differently than food service. The biggest piece is service advisor upsell gaps — the difference between writing up an oil change and writing up an oil change plus the air filter and tire rotation the vehicle actually needs. Next is bay utilization — dead time between jobs where a technician is waiting.\n\nThat's real bay hours turning into zero revenue.`,
      whyItWorks: 'Auto shop owners think in bay hours and labor rate. "Empty bays" and "upsell gaps" are the two metrics they track mentally but never precisely. Showing both in one number is powerful.',
      likelyResponse: 'My service advisors push the multi-point inspection',
      likelyAnswer: `Do they push it consistently? The AI tracks recommendation-to-close rate per advisor. If Nina closes 60% of her upsell recommendations and Greg closes 25%, that's not a process problem — that's a coaching problem. You can't fix what you can't measure per person.`,
      whatToDo: 'Scroll to the Money Left components. Point at "Upsell Potential" first — that\'s the service advisor gap. Then "Staffing & Scheduling" — that\'s the bay utilization gap. These are the two biggest levers for an auto shop.',
    },
    anomaly: {
      title: 'The Write-Off That Doesn\'t Add Up',
      sayThis: `See this flag? There's a pattern of warranty write-offs and parts returns that spike on specific days.\n\n[pause]\n\nIn an auto shop, warranty claims that cluster on the same day of the week usually mean one of two things: a technician who's consistently misdiagnosing, or parts being returned that were never installed. The AI can't tell you which — but it can tell you the pattern exists.\n\nAre you tracking warranty claim rates per technician right now?`,
      whyItWorks: 'Parts shrinkage and warranty fraud are real problems in auto repair — and every shop owner suspects it happens more than they can prove. This gives them data without making an accusation.',
      likelyResponse: 'We track warranty through our shop management system',
      likelyAnswer: 'Your SMS tracks the claim — but does it flag the pattern? If Technician B has 3x the warranty rate of Technician A on brake jobs, your SMS just records each claim individually. The AI connects them and says "this is a pattern, not random." That\'s the difference between bookkeeping and intelligence.',
      whatToDo: 'Click into the anomaly. Show the day-of-week pattern. Ask: "Who\'s working on that day?" — often it narrows to one tech. Let them connect the dots.',
    },
    forecast: {
      title: 'Your Slow Week Is Predictable',
      sayThis: `Look at this — the AI predicts next week will be 22% below your average. The week after that? Back to normal.\n\n[pause]\n\nIf you knew a slow week was coming, what would you do differently? Would you schedule that big training session you've been putting off? Would you run a "free inspection" campaign to fill bays?\n\nMost auto shops react to slow weeks. This lets you plan for them.`,
      whyItWorks: 'Auto shops have dramatic revenue swings — one week every bay is full, the next week tumbleweeds. Framing the forecast around "plan for it instead of react to it" turns a problem into a strategy.',
      likelyResponse: 'How does it predict slow weeks in auto?',
      likelyAnswer: 'Seasonal patterns are huge in automotive — post-holiday dips, pre-summer A/C season, back-to-school tire rush, winter prep. The AI layers in weather forecasts too — a cold snap drives battery and starter work. After 90 days of your data, it learns YOUR shop\'s specific patterns on top of the industry baseline.',
      whatToDo: 'Show the 30-day forecast. Point out the peaks and valleys. Ask: "When was the last time you ran a proactive marketing campaign during a predicted slow week?" The answer is usually never.',
    },
    customers: {
      title: 'Your One-Visit Customers Never Come Back',
      sayThis: `Look at this — "Needs Action." These are customers who came in once for a service and never returned.\n\n[point to the spend figure]\n\nThe average lifetime value of a retained auto customer is $3,000-5,000 over 3 years. Every one of these one-visit customers represents that much in lost future revenue.\n\nIn auto, the first oil change is the hardest to win. The second one should be automatic. Why aren't these customers coming back?`,
      whyItWorks: 'Auto shop LTV is enormous compared to food service. A single retained oil change customer becomes brake jobs, tire replacements, and major service. The math on lost LTV is genuinely shocking.',
      likelyResponse: 'People just go wherever is cheapest for an oil change',
      likelyAnswer: 'Some do. But the data shows that customers who have a good first experience AND get a follow-up reminder have a 60%+ return rate. The problem isn\'t price — it\'s that nobody follows up. The AI identifies the customers who came once and didn\'t return — that\'s your follow-up list. A simple "your next oil change is due" text message converts 15-20% of them.',
      whatToDo: 'Point to the At Risk count. Multiply by $3,000 LTV. Ask: "If you could get even 20% of these customers back for a second visit, what would that be worth?" Let them do the math.',
    },
    staff: {
      title: 'Your Bays Are Empty When They Shouldn\'t Be',
      sayThis: `This heatmap — see Monday morning? 7:30–10:00am. That's your highest-demand window. Customers want to drop off before work.\n\n[pause]\n\nBut look at 2:00–4:00pm. Much lighter. Are your techs sitting idle during that window?\n\n[wait]\n\nThe gap between your peak and your valley is bigger than most shop owners realize. If you could shift even 20% of morning appointments to afternoon, you'd smooth out your labor costs AND reduce morning wait times.`,
      whyItWorks: 'Bay utilization is THE metric for auto shop profitability. Every hour a tech is idle is pure cost. Showing the morning/afternoon gap makes the waste visible.',
      likelyResponse: 'Customers want morning appointments — I can\'t force them to come at 2pm',
      likelyAnswer: 'You can incentivize it. "Afternoon oil change special — $10 off" costs you $10 but fills an otherwise empty bay hour. The AI calculates the exact revenue of each bay hour so you know what the discount is worth vs the idle time cost. Usually the discount pays for itself 4x over.',
      whatToDo: 'Show the contrast between AM and PM blocks. Then say: "The Insights tab has specific recommendations for smoothing your demand curve — let me show you the math."',
    },
    insights: {
      title: 'Your AI Says: Bundle the Tire Rotation',
      sayThis: `Read this.\n\n[10 seconds]\n\nThe AI noticed that customers who get a synthetic oil change rarely add a tire rotation — even though it's the most logical bundle. Your advisors recommend it 40% of the time, but only close it 15% of the time.\n\n[point to the dollar figure]\n\nThat's the revenue from closing tire rotations on just 30% of synthetic oil changes instead of 15%. The fix? A printed checklist that the advisor reviews with the customer. Not a harder sell — a more systematic one.`,
      whyItWorks: 'The "checklist" solution is so simple that shop owners can implement it tomorrow. The AI didn\'t just find the problem — it gave them a $0-cost fix.',
      likelyResponse: 'We already do multi-point inspections',
      likelyAnswer: 'The multi-point finds what\'s WRONG. This is different — it\'s about what\'s DUE. "Your tires have 4/32" tread — they\'re fine" versus "your last tire rotation was 8 months ago — it\'s due." The inspection finds problems. The bundled recommendation prevents them. The AI tracks both and tells you which advisor does each best.',
      whatToDo: 'Show another insight — ideally one about bay scheduling or parts inventory. Demonstrate breadth: "This isn\'t just about upsells — it optimizes every part of your shop."',
    },
    close: {
      title: 'See Your Real Bay Utilization',
      sayThis: portalContext === 'canada'
        ? `Everything I just showed you — the bay gaps, the advisor close rates, the one-visit drop-offs — that's sample data for a Canadian auto shop.\n\nWith your actual shop management data? Every insight rewrites for YOUR bays, YOUR techs, YOUR service mix. CA$${price}/month, first month free.\n\n[pause]\n\nWhat shop management system are you running?`
        : `Everything I just showed you — the bay gaps, the advisor close rates, the customer retention — that's modeled from typical auto shop data.\n\nConnect your POS or shop management system and the AI calculates YOUR real bay utilization, YOUR real upsell gaps, YOUR real customer retention rates. $${price}/month, first month free.\n\n[pause]\n\nAre you on Tekmetric, ShopBoss, or something else?`,
      whyItWorks: 'Auto shop owners are technical people — they respond to specificity. Mentioning Tekmetric and ShopBoss by name signals that this tool was built for their world, not adapted from a restaurant product.',
      likelyResponse: 'My shop management system already tracks a lot of this',
      likelyAnswer: portalContext === 'canada'
        ? 'Your SMS tracks transactions. This analyzes patterns across those transactions and tells you what to do about them. Your SMS is the data source — Meridian is the analyst. They work together. And the first month is free, so you can see for yourself what it finds that your current reports miss.'
        : 'Your SMS records the data. Meridian reads the patterns IN that data and tells you what to do about them. Think of it this way: your SMS is the scoreboard. Meridian is the coach. The first month is free — see what it finds that your current reports don\'t surface.',
      whatToDo: 'Ask about their specific system. If it\'s a major SMS (Tekmetric, ShopBoss, Mitchell), show the integration page. If it\'s Square or Clover, show the OAuth flow — "60 seconds, one button."',
    },
  }
}

function smokeShopContent(portalContext: PortalContext): Record<StepId, CoachingContent> {
  const currency = portalContext === 'canada' ? 'CA$' : '$'
  const opp = portalContext === 'canada' ? '32,870' : '23,650'
  const price = portalContext === 'canada' ? '339' : '250'
  return {
    hook: {
      title: 'The Shelf Space That\'s Costing You',
      sayThis: `See this number? ${currency}${opp} a month.\n\n[pause]\n\nFor a smoke shop, the biggest piece of that is dead inventory — products sitting on your shelf that turn once every 90 days instead of every 2 weeks. You're paying rent on that shelf space, and the AI identified specific SKUs that are tying up cash and producing almost zero margin.\n\nThe second piece is missed accessory bundles — customers buying a vape device without the coils, liquid, or case.`,
      whyItWorks: 'Smoke shop owners think in terms of inventory turns and cash flow. "Dead shelf space" is the exact pain point — they know they have too many slow-moving SKUs but don\'t know which ones to cut.',
      likelyResponse: 'I know which products don\'t sell — I just can\'t return them',
      likelyAnswer: `You know the obvious ones. But what about the product that sells 3 units a month — enough to seem active, but not enough to justify the shelf space? The AI calculates revenue-per-square-foot by product category. Sometimes your best move isn't cutting a product — it's shrinking its shelf allocation and giving that space to something with 4x the turn rate.`,
      whatToDo: 'Point at "Dead Stock" in the Money Left breakdown. Then point at "Upsell Potential" — that\'s the accessory bundle gap. Smoke shops have the highest potential upsell rates of any retail category.',
    },
    anomaly: {
      title: 'The Shrinkage You Can\'t See',
      sayThis: `This alert — see this? There's a pattern of inventory adjustments and register discrepancies during afternoon shifts on Fridays.\n\n[pause]\n\nIn a smoke shop, shrinkage is one of the highest costs — vape products and accessories are small, high-value, and easy to pocket. The AI doesn't accuse anyone — it flags statistical anomalies in your register patterns.\n\nDo you currently know your shrinkage rate by shift?`,
      whyItWorks: 'Shrinkage is the #1 unspoken problem in smoke shops. Products are small, valuable, and easy to steal. Every shop owner knows this but most don\'t have per-shift data to narrow it down.',
      likelyResponse: 'We do inventory counts every month',
      likelyAnswer: 'Monthly counts tell you WHAT\'s missing. The AI tells you WHEN it went missing — which narrows it to a shift, a register, and a time window. That\'s the difference between knowing you lost $500 in product and knowing it happened between 4-6pm on Fridays on register 2. One is a number. The other is actionable.',
      whatToDo: 'Click into the anomaly. Show the time pattern — same day, same hours. Ask: "Who works the Friday afternoon shift?" Let them think about it. Don\'t push — the data speaks for itself.',
    },
    forecast: {
      title: 'Your Weekend Pattern Drives Everything',
      sayThis: `Look at your weekly forecast — Friday and Saturday are 45% of your total revenue. But the interesting part is what happens BETWEEN those peaks.\n\n[pause]\n\nSee Wednesday? It's your weakest day — less than half of Friday. If you're staffing and stocking the same way every day, you're overspending four days a week to cover two.\n\nWhat if you could shift some of that Friday/Saturday demand to midweek with targeted promotions?`,
      whyItWorks: 'Smoke shop revenue is extremely day-of-week dependent. Showing the Friday/Saturday concentration makes owners realize their midweek is a liability — and the forecast gives them data to act on.',
      likelyResponse: 'People come when they come — I can\'t control that',
      likelyAnswer: 'You can influence it. "Midweek coil refill deal — 20% off Wednesday only" drives traffic to your slow day from your regulars who would have come Friday anyway. You\'re not creating new demand — you\'re smoothing it. The AI identifies which products and promotions would be most effective for demand shifting based on your actual purchase patterns.',
      whatToDo: 'Show the 30-day forecast. Point out the consistent Friday/Saturday peaks. Ask: "What\'s your rent cost per day?" — then show them they\'re paying the same rent for a Wednesday that generates half the revenue. The forecast helps them fix that.',
    },
    customers: {
      title: 'Your Vape Regulars Are Buying Elsewhere',
      sayThis: `Look at this segment — these are customers who used to buy vape supplies every 2-3 weeks like clockwork. They haven't been back in 45+ days.\n\n[pause]\n\nVape customers are the most predictable segment in your store — they run out of coils and liquid on a fixed schedule. When they stop coming, they didn't quit — they found another shop. Or worse, they started ordering online.\n\nHow many of these customers did you know you lost?`,
      whyItWorks: 'Vape customers are the highest-LTV, most predictable segment in a smoke shop. Losing them to online or a competitor is devastating because the purchase cycle is so regular — and recoverable if you catch it early.',
      likelyResponse: 'Online is killing us — we can\'t compete on price',
      likelyAnswer: 'You can\'t compete on price, but you compete on immediacy and trust. When a coil burns out at 9pm, nobody waits 2 days for Amazon. The AI identifies customers at the 3-week mark — just when they\'re about to run out — so you can send a "your coils are probably due — we\'ve got your brand in stock" text. That level of personalization is something online can\'t match.',
      whatToDo: 'Point to the At Risk count. Ask: "If each of these customers spends $30 every 2 weeks, what\'s the annual loss?" Let them calculate: $30 x 26 visits x [count]. The number will be alarming.',
    },
    staff: {
      title: 'Your Afternoon Surge Needs Another Person',
      sayThis: `See this dark block — Friday, 4:30–6:30pm. That's your peak — people stopping in after work.\n\n[pause]\n\nDuring that window, you probably have one person behind the counter managing the register, answering product questions, AND checking IDs. If there are 3 people in the store and one has a question about a new vape mod, the other two are waiting.\n\nHow many walk-outs do you think you get during Friday rush?`,
      whyItWorks: 'Smoke shops are typically understaffed — one person behind the counter is common. The "3 customers, one has a question" scenario is instantly recognizable to any shop owner.',
      likelyResponse: 'I can\'t afford another person just for Fridays',
      likelyAnswer: 'What if that second person only works 4-7pm Friday and Saturday? That\'s 6 hours a week. If they prevent 5 walk-outs per shift at an average $25 ticket, that\'s $250/week in recovered revenue for maybe $100 in labor. The AI calculates the exact break-even in the Insights section — let me show you.',
      whatToDo: 'Compare the Friday 4-6pm block to a Tuesday afternoon visually. The contrast is dramatic. Then bridge: "The Insights tab has the exact math on adding a part-time closer."',
    },
    insights: {
      title: 'Your AI Says: Move the Disposable Vapes to Eye Level',
      sayThis: `Read this insight.\n\n[10 seconds]\n\nThe AI analyzed your product velocity and found that disposable vapes sell 2.4x faster than your second-best category — but they're not in your highest-traffic display position. The recommendation: swap disposable vapes with the cigar display at the front counter.\n\n[point to the dollar figure]\n\nThat's the projected monthly increase from one shelf rearrangement. Zero cost. Zero new inventory.`,
      whyItWorks: 'Smoke shop owners are visual merchandisers — they understand shelf position. Giving them a specific swap recommendation (not just "optimize your layout") is immediately actionable.',
      likelyResponse: 'Cigars are a higher margin item though',
      likelyAnswer: 'Higher margin per unit, but much lower velocity. The AI calculated margin-times-velocity — total margin per shelf-foot per month. Disposable vapes in that position generate 2.4x the total margin because they turn so much faster. The cigar display doesn\'t disappear — it moves to a secondary position where cigar buyers will still find it. They\'re intentional buyers. Vape buyers are impulse buyers — they need to see it.',
      whatToDo: 'Show another insight — ideally one about dead stock clearance or an accessory bundle suggestion. Show that the AI understands smoke shop merchandising, not just generic retail.',
    },
    close: {
      title: 'See Your Real Product Velocity',
      sayThis: portalContext === 'canada'
        ? `Everything I just showed you — the shrinkage patterns, the vape customer retention, the shelf optimization — that's sample data.\n\nWith your actual POS data? The AI rewrites every insight for YOUR inventory, YOUR customers, YOUR peak patterns. CA$${price}/month, first month free.\n\n[pause]\n\nWhat POS are you running — Square, Moneris?`
        : `Everything I just showed you — the shrinkage alerts, the vape customer churn, the shelf placement math — that's modeled data.\n\nConnect your POS and by tomorrow you'll see YOUR real product velocity, YOUR real shrinkage patterns, YOUR real customer retention. $${price}/month, first month free.\n\n[pause]\n\nAre you on Square, Clover, or a specialty system?`,
      whyItWorks: 'Smoke shop owners are often independent operators who make fast decisions. The insights have been specific enough to their world that the close feels natural, not pushy.',
      likelyResponse: 'I need to see if it works with my POS',
      likelyAnswer: portalContext === 'canada'
        ? 'Totally fair — we integrate with Square, Moneris, Clover, Toast, and 75+ other systems. Most smoke shops are on Square and it connects in 60 seconds. First month is free, so the question is just whether you want to see your data or not. Want to try the connection right now?'
        : 'We integrate with Square, Clover, Toast, and 75+ systems. Most smoke shops use Square — it connects in 60 seconds, single button. The first month is free with no credit card. Want to try it right now? Takes less time than this conversation did.',
      whatToDo: 'If they\'re on Square (most smoke shops are), show the OAuth flow. Emphasize: "60 seconds, one button, you\'ll have data by morning." If they\'re hesitant, offer to email them the link so they can connect on their own time.',
    },
  }
}

const CONTENT_BY_TYPE: Record<string, (ctx: PortalContext) => Record<StepId, CoachingContent>> = {
  restaurant: restaurantContent,
  fast_food: fastFoodContent,
  coffee_shop: coffeeShopContent,
  auto_shop: autoShopContent,
  smoke_shop: smokeShopContent,
}

export function getWalkthroughContent(
  stepId: StepId,
  businessType: BusinessType,
  portalContext: PortalContext,
): CoachingContent {
  const factory = CONTENT_BY_TYPE[businessType] || restaurantContent
  return factory(portalContext)[stepId]
}
