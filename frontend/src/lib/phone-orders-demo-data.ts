export interface PhoneMenuItem {
  id: string
  name: string
  price: number
  category: string
}

export interface PhoneOrderItem {
  name: string
  qty: number
  price: number
  mods?: string
}

export interface TranscriptLine {
  speaker: 'agent' | 'caller'
  text: string
  time: string
}

export type CallStatus = 'order_placed' | 'no_order' | 'transferred' | 'in_progress'
export type PaymentStatus = 'paid' | 'pending' | 'expired' | 'none'

export interface PhoneCallEntry {
  id: string
  phone: string
  name: string
  status: CallStatus
  duration: string
  durationSec: number
  items: PhoneOrderItem[]
  subtotal: number
  tax: number
  total: number
  orderType: 'pickup' | 'delivery' | 'dine_in' | 'reservation'
  transcript: TranscriptLine[]
  createdAt: string
  paymentStatus: PaymentStatus
  paymentLink: string
  smsSent: boolean
}

export interface PhoneBizConfig {
  id: string
  name: string
  vertical: string
  country: 'US' | 'CA'
  currency: string
  taxRate: number
  phone: string
  greeting: string
  voice: string
  orderTypes: ('pickup' | 'delivery' | 'dine_in' | 'reservation')[]
  menu: PhoneMenuItem[]
}

export interface VoicePersonality {
  formality: number
  upsell: 'none' | 'gentle' | 'active'
  humor: boolean
  customGreeting: string
  customHold: string
  customClosing: string
  brandKeywords: string[]
  // Selected character type ('' = none — classic voice applies). Ids must stay
  // in lockstep with services/phone_agent/personas.py PERSONAS.
  character?: string
}

export interface PhoneStats {
  totalCalls: number
  orders: number
  conversion: number
  revenue: number
  avgOrder: number
  avgDurationSec: number
  paid: number
  pending: number
  paidRevenue: number
}

import { generateCalls } from './phone-transcript-builder'

/* ---- businesses ---- */
const BUSINESSES: PhoneBizConfig[] = [
  {
    id: 'tony-pizza', name: "Tony's Pizza Palace", vertical: 'Pizza Shop', country: 'US',
    currency: '$', taxRate: 0.08875, phone: '+1 (380) 240-9535',  // LIVE demo line — callable
    greeting: "Thanks for calling Tony's Pizza Palace! What can I get for you?",
    voice: 'am_adam', orderTypes: ['pickup', 'delivery'],
    menu: [
      { id: 'p1', name: 'Cheese Pizza (Large)', price: 18.99, category: 'Pizza' },
      { id: 'p2', name: 'Pepperoni Pizza (Large)', price: 21.99, category: 'Pizza' },
      { id: 'p3', name: 'Margherita Pizza', price: 19.99, category: 'Pizza' },
      { id: 'p4', name: 'Meat Lovers Pizza', price: 24.99, category: 'Pizza' },
      { id: 'p5', name: 'Garlic Knots (6pc)', price: 5.99, category: 'Sides' },
      { id: 'p6', name: 'Caesar Salad', price: 9.99, category: 'Sides' },
      { id: 'p7', name: 'Chicken Wings (10pc)', price: 14.99, category: 'Sides' },
      { id: 'p8', name: 'Cannoli', price: 4.99, category: 'Dessert' },
      { id: 'p9', name: 'Soda (2L)', price: 3.49, category: 'Drinks' },
    ],
  },
  {
    id: 'smokin-joes', name: "Smokin' Joe's BBQ", vertical: 'BBQ Joint', country: 'US',
    currency: '$', taxRate: 0.0825, phone: '+1 (713) 555-0202',
    greeting: "Welcome to Smokin' Joe's BBQ! Ready to get your smoke on?",
    voice: 'am_michael', orderTypes: ['pickup', 'dine_in'],
    menu: [
      { id: 'b1', name: 'Brisket Plate (1/2 lb)', price: 18.99, category: 'Plates' },
      { id: 'b2', name: 'Pulled Pork Plate', price: 15.99, category: 'Plates' },
      { id: 'b3', name: 'Smoked Ribs (Half Rack)', price: 22.99, category: 'Plates' },
      { id: 'b4', name: 'Mac & Cheese', price: 5.99, category: 'Sides' },
      { id: 'b5', name: 'Coleslaw', price: 3.99, category: 'Sides' },
      { id: 'b6', name: 'Cornbread (2pc)', price: 3.49, category: 'Sides' },
      { id: 'b7', name: 'Banana Pudding', price: 5.99, category: 'Dessert' },
      { id: 'b8', name: 'Sweet Tea', price: 2.99, category: 'Drinks' },
    ],
  },
  {
    id: 'sakura-sushi', name: 'Sakura Sushi Bar', vertical: 'Sushi Bar', country: 'US',
    currency: '$', taxRate: 0.095, phone: '+1 (310) 555-0303',
    greeting: "Thank you for calling Sakura Sushi Bar. How may I help you today?",
    voice: 'af_bella', orderTypes: ['pickup', 'delivery', 'dine_in'],
    menu: [
      { id: 's1', name: 'California Roll (8pc)', price: 12.99, category: 'Rolls' },
      { id: 's2', name: 'Spicy Tuna Roll', price: 14.99, category: 'Rolls' },
      { id: 's3', name: 'Dragon Roll', price: 17.99, category: 'Rolls' },
      { id: 's4', name: 'Salmon Nigiri (2pc)', price: 8.99, category: 'Nigiri' },
      { id: 's5', name: 'Edamame', price: 5.99, category: 'Appetizers' },
      { id: 's6', name: 'Miso Soup', price: 3.99, category: 'Soup' },
      { id: 's7', name: 'Tempura Shrimp (5pc)', price: 11.99, category: 'Appetizers' },
      { id: 's8', name: 'Green Tea Ice Cream', price: 5.99, category: 'Dessert' },
    ],
  },
  {
    id: 'el-fuego', name: 'El Fuego Taco Truck', vertical: 'Taco Truck', country: 'US',
    currency: '$', taxRate: 0.0825, phone: '+1 (512) 555-0404',
    greeting: "Hola! Thanks for calling El Fuego. What can we make for you?",
    voice: 'am_michael', orderTypes: ['pickup'],
    menu: [
      { id: 't1', name: 'Street Tacos (3pc)', price: 9.99, category: 'Tacos' },
      { id: 't2', name: 'Al Pastor Tacos (3pc)', price: 11.99, category: 'Tacos' },
      { id: 't3', name: 'Carne Asada Tacos (3pc)', price: 12.99, category: 'Tacos' },
      { id: 't4', name: 'Burrito Bowl', price: 13.99, category: 'Bowls' },
      { id: 't5', name: 'Chips & Guac', price: 6.99, category: 'Sides' },
      { id: 't6', name: 'Elote (Street Corn)', price: 4.99, category: 'Sides' },
      { id: 't7', name: 'Horchata', price: 3.99, category: 'Drinks' },
      { id: 't8', name: 'Jarritos', price: 2.99, category: 'Drinks' },
    ],
  },
  {
    id: 'rosies-diner', name: "Rosie's Diner", vertical: 'Diner', country: 'US',
    currency: '$', taxRate: 0.1025, phone: '+1 (312) 555-0505',
    greeting: "Hi there! Welcome to Rosie's Diner. What'll it be today?",
    voice: 'af_sarah', orderTypes: ['pickup', 'dine_in'],
    menu: [
      { id: 'd1', name: 'Classic Burger', price: 12.99, category: 'Burgers' },
      { id: 'd2', name: 'Cheeseburger Deluxe', price: 14.99, category: 'Burgers' },
      { id: 'd3', name: 'Club Sandwich', price: 11.99, category: 'Sandwiches' },
      { id: 'd4', name: 'French Fries', price: 4.99, category: 'Sides' },
      { id: 'd5', name: 'Milkshake', price: 6.99, category: 'Drinks' },
      { id: 'd6', name: 'Apple Pie', price: 5.99, category: 'Dessert' },
      { id: 'd7', name: 'Pancake Stack', price: 9.99, category: 'Breakfast' },
      { id: 'd8', name: 'Coffee', price: 2.49, category: 'Drinks' },
    ],
  },
  {
    id: 'la-belle', name: 'La Belle Poutine', vertical: 'Poutinerie', country: 'CA',
    currency: 'CA$', taxRate: 0.14975, phone: '+1 (380) 240-9535',  // LIVE demo line — callable (answers as Tony's Pizza)
    greeting: "Bonjour! Thanks for calling La Belle Poutine. What can I get for you?",
    voice: 'af_bella', orderTypes: ['pickup', 'delivery'],
    menu: [
      { id: 'lp1', name: 'Classic Poutine', price: 10.99, category: 'Poutine' },
      { id: 'lp2', name: 'Smoked Meat Poutine', price: 15.99, category: 'Poutine' },
      { id: 'lp3', name: 'Veggie Poutine', price: 12.99, category: 'Poutine' },
      { id: 'lp4', name: 'Pulled Pork Poutine', price: 16.99, category: 'Poutine' },
      { id: 'lp5', name: 'Pea Soup', price: 6.99, category: 'Soup' },
      { id: 'lp6', name: 'Sugar Pie', price: 5.99, category: 'Dessert' },
      { id: 'lp7', name: 'Iced Tea', price: 2.99, category: 'Drinks' },
    ],
  },
  {
    id: 'tora-ramen', name: 'Tora Ramen House', vertical: 'Ramen House', country: 'CA',
    currency: 'CA$', taxRate: 0.13, phone: '+1 (416) 555-0702',
    greeting: "Thank you for calling Tora Ramen House! How can I help you?",
    voice: 'af_sarah', orderTypes: ['pickup', 'dine_in'],
    menu: [
      { id: 'tr1', name: 'Tonkotsu Ramen', price: 16.99, category: 'Ramen' },
      { id: 'tr2', name: 'Miso Ramen', price: 15.99, category: 'Ramen' },
      { id: 'tr3', name: 'Shoyu Ramen', price: 15.99, category: 'Ramen' },
      { id: 'tr4', name: 'Spicy Tan Tan Men', price: 17.99, category: 'Ramen' },
      { id: 'tr5', name: 'Gyoza (6pc)', price: 8.99, category: 'Appetizers' },
      { id: 'tr6', name: 'Karaage Chicken', price: 9.99, category: 'Appetizers' },
      { id: 'tr7', name: 'Matcha Latte', price: 5.49, category: 'Drinks' },
      { id: 'tr8', name: 'Ramune Soda', price: 3.99, category: 'Drinks' },
    ],
  },
  {
    id: 'byblos', name: 'Byblos Shawarma', vertical: 'Shawarma Spot', country: 'CA',
    currency: 'CA$', taxRate: 0.13, phone: '+1 (613) 555-0803',
    greeting: "Welcome to Byblos Shawarma! What can I prepare for you?",
    voice: 'am_adam', orderTypes: ['pickup', 'delivery'],
    menu: [
      { id: 'bs1', name: 'Chicken Shawarma Wrap', price: 12.99, category: 'Wraps' },
      { id: 'bs2', name: 'Beef Shawarma Plate', price: 16.99, category: 'Plates' },
      { id: 'bs3', name: 'Falafel Wrap', price: 10.99, category: 'Wraps' },
      { id: 'bs4', name: 'Mixed Grill Plate', price: 19.99, category: 'Plates' },
      { id: 'bs5', name: 'Hummus & Pita', price: 7.99, category: 'Appetizers' },
      { id: 'bs6', name: 'Fattoush Salad', price: 8.99, category: 'Salads' },
      { id: 'bs7', name: 'Baklava (3pc)', price: 5.49, category: 'Dessert' },
      { id: 'bs8', name: 'Mint Lemonade', price: 3.99, category: 'Drinks' },
    ],
  },
  {
    id: 'schwartz-bagels', name: "Schwartz's Bagel Cafe", vertical: 'Bagel Cafe', country: 'CA',
    currency: 'CA$', taxRate: 0.14975, phone: '+1 (514) 555-0904',
    greeting: "Good morning! Schwartz's Bagel Cafe, how can I help?",
    voice: 'af_bella', orderTypes: ['pickup'],
    menu: [
      { id: 'sb1', name: 'Montreal Bagel', price: 1.99, category: 'Bagels' },
      { id: 'sb2', name: 'Everything Bagel w/ Cream Cheese', price: 4.99, category: 'Bagels' },
      { id: 'sb3', name: 'Lox & Cream Cheese Bagel', price: 9.99, category: 'Bagels' },
      { id: 'sb4', name: 'Egg & Cheese Bagel', price: 6.99, category: 'Bagels' },
      { id: 'sb5', name: 'Smoked Meat Bagel', price: 8.99, category: 'Bagels' },
      { id: 'sb6', name: "Baker's Dozen (13)", price: 16.99, category: 'Bulk' },
      { id: 'sb7', name: 'Matzo Ball Soup', price: 7.99, category: 'Soup' },
      { id: 'sb8', name: 'Coffee (Large)', price: 3.49, category: 'Drinks' },
    ],
  },
  {
    id: 'golden-dragon', name: 'Golden Dragon Dim Sum', vertical: 'Dim Sum', country: 'CA',
    currency: 'CA$', taxRate: 0.12, phone: '+1 (604) 555-1005',
    greeting: "Golden Dragon Dim Sum, how may I help you?",
    voice: 'af_sarah', orderTypes: ['pickup', 'dine_in'],
    menu: [
      { id: 'gd1', name: 'Har Gow (Shrimp Dumpling, 4pc)', price: 6.99, category: 'Dim Sum' },
      { id: 'gd2', name: 'Siu Mai (Pork Dumpling, 4pc)', price: 5.99, category: 'Dim Sum' },
      { id: 'gd3', name: 'Char Siu Bao (BBQ Pork Bun, 3pc)', price: 5.99, category: 'Dim Sum' },
      { id: 'gd4', name: 'Cheung Fun (Rice Roll)', price: 7.99, category: 'Dim Sum' },
      { id: 'gd5', name: 'Congee (Large)', price: 8.99, category: 'Rice' },
      { id: 'gd6', name: 'Fried Rice', price: 12.99, category: 'Rice' },
      { id: 'gd7', name: 'Egg Tart (3pc)', price: 4.99, category: 'Dessert' },
      { id: 'gd8', name: 'Chrysanthemum Tea', price: 3.49, category: 'Drinks' },
      { id: 'gd9', name: 'Wonton Soup', price: 9.99, category: 'Soup' },
    ],
  },
]

export const MIDTOWN_KITCHEN: PhoneBizConfig = {
  id: 'midtown-kitchen', name: 'The Midtown Kitchen', vertical: 'American Bistro', country: 'US',
  currency: '$', taxRate: 0.08875, phone: '+1 (212) 555-2024',
  greeting: "Thank you for calling The Midtown Kitchen! How can I help you today?",
  voice: 'af_bella', orderTypes: ['pickup', 'delivery', 'dine_in'],
  menu: [
    { id: 'mk1', name: 'Grilled Salmon', price: 24.99, category: 'Mains' },
    { id: 'mk2', name: 'Filet Mignon', price: 34.99, category: 'Mains' },
    { id: 'mk3', name: 'Chicken Parm', price: 19.99, category: 'Mains' },
    { id: 'mk4', name: 'Truffle Burger', price: 18.99, category: 'Mains' },
    { id: 'mk5', name: 'Caesar Salad', price: 12.99, category: 'Starters' },
    { id: 'mk6', name: 'French Onion Soup', price: 9.99, category: 'Starters' },
    { id: 'mk7', name: 'Calamari', price: 13.99, category: 'Starters' },
    { id: 'mk8', name: 'Truffle Fries', price: 8.99, category: 'Sides' },
    { id: 'mk9', name: 'Roasted Vegetables', price: 7.99, category: 'Sides' },
    { id: 'mk10', name: 'Mac & Cheese', price: 9.99, category: 'Sides' },
    { id: 'mk11', name: 'Creme Brulee', price: 10.99, category: 'Dessert' },
    { id: 'mk12', name: 'Chocolate Lava Cake', price: 11.99, category: 'Dessert' },
    { id: 'mk13', name: 'Craft Beer', price: 8.99, category: 'Drinks' },
    { id: 'mk14', name: 'House Wine', price: 12.99, category: 'Drinks' },
    { id: 'mk15', name: 'Espresso', price: 3.99, category: 'Drinks' },
  ],
}

/**
 * Synthetic menu-build target for the demo. The MenuBuildStatus component
 * animates the item count climbing up to this set, then settles on "ready".
 * Demo never calls the backend — this is the whole catalog it "discovers".
 */
export function getMenuBuildDemo(bizId?: string): { item_count: number; sample: string[] } {
  const menu = getPhoneDemoData(bizId).business.menu
  return {
    item_count: menu.length,
    sample: menu.slice(0, 5).map(m => m.name),
  }
}

export { generateCalls } from './phone-transcript-builder'

export function getPhoneStats(calls: PhoneCallEntry[], period: 'today' | '7d' | '30d' | '90d'): PhoneStats {
  const now = new Date()
  const cutoff = new Date(now)
  if (period === 'today') cutoff.setHours(0, 0, 0, 0)
  else if (period === '7d') cutoff.setDate(cutoff.getDate() - 7)
  else if (period === '30d') cutoff.setDate(cutoff.getDate() - 30)
  else cutoff.setDate(cutoff.getDate() - 90)

  const filtered = calls.filter(c => new Date(c.createdAt) >= cutoff)
  const orders = filtered.filter(c => c.status === 'order_placed')
  const rev = orders.reduce((s, c) => s + c.total, 0)
  const paidOrders = orders.filter(c => c.paymentStatus === 'paid')
  const pendingOrders = orders.filter(c => c.paymentStatus === 'pending')
  const paidRev = paidOrders.reduce((s, c) => s + c.total, 0)

  return {
    totalCalls: filtered.length,
    orders: orders.length,
    conversion: filtered.length > 0 ? Math.round(orders.length / filtered.length * 100) : 0,
    revenue: Math.round(rev * 100) / 100,
    avgOrder: orders.length > 0 ? Math.round(rev / orders.length * 100) / 100 : 0,
    paid: paidOrders.length,
    pending: pendingOrders.length,
    paidRevenue: Math.round(paidRev * 100) / 100,
    avgDurationSec: filtered.length > 0 ? Math.round(filtered.reduce((s, c) => s + c.durationSec, 0) / filtered.length) : 0,
  }
}

export function getPhoneDemoData(bizId?: string) {
  const allBiz = [...BUSINESSES, MIDTOWN_KITCHEN]
  const biz = bizId ? allBiz.find(b => b.id === bizId) || MIDTOWN_KITCHEN : MIDTOWN_KITCHEN
  const calls = generateCalls(biz, 90)
  return { business: biz, calls, businesses: allBiz }
}

// Labels/descriptions = the Vapi native voice actually used on live calls
// (see KOKORO_TO_VAPI in src/api/routes/vapi_webhook.py). The stored `id`
// stays the legacy kokoro-style value so existing merchant configs remain valid.
// Accent groups follow the roster's documented accents
// (docs.vapi.ai/providers/voice/vapi-voices): Savannah/Layla/Sid/Kai American,
// Elliot Canadian, Naina + Neil Indian, Emma Asian American.
export type VoiceAccent = 'north_american' | 'indian' | 'east_asian'

export const ACCENT_OPTIONS: { id: 'all' | VoiceAccent; label: string; desc: string }[] = [
  { id: 'all', label: 'All voices', desc: 'Browse the full roster' },
  { id: 'north_american', label: 'North American', desc: 'US & Canadian accents' },
  { id: 'indian', label: 'Indian', desc: 'Indian accents — can also understand Hindi & Punjabi callers' },
  { id: 'east_asian', label: 'East Asian', desc: 'Asian-American accent' },
]

export const VOICE_OPTIONS: { id: string; label: string; desc: string; accent: VoiceAccent; sampleText: string }[] = [
  { id: 'af_bella', label: 'Savannah', desc: 'American — realistic, straightforward (female)', accent: 'north_american', sampleText: "Thank you for calling! I'd be happy to help you place an order today." },
  { id: 'af_sarah', label: 'Layla', desc: 'American — warm, bright, cheerful (female)', accent: 'north_american', sampleText: "Hey there! Welcome in -- what can I get started for you?" },
  { id: 'af_nicole', label: 'Naina', desc: 'Indian — calm, collected, professional (female)', accent: 'indian', sampleText: "Hi, you've reached us -- take your time, I'm here whenever you're ready." },
  { id: 'bf_emma', label: 'Emma', desc: 'Asian American — warm, conversational (female)', accent: 'east_asian', sampleText: "Good day, thank you for ringing -- how may I help with your order?" },
  { id: 'am_adam', label: 'Sid', desc: 'American — smooth, deep-toned, laid-back (male)', accent: 'north_american', sampleText: "Good evening. I'll take your order whenever you're ready." },
  { id: 'am_michael', label: 'Elliot', desc: 'Canadian — friendly, professional (male) -- default', accent: 'north_american', sampleText: "Hi! Thanks for calling -- let me know what sounds good to you." },
  { id: 'am_echo', label: 'Kai', desc: 'American — friendly, relaxed, approachable (male)', accent: 'north_american', sampleText: "Hey, great to hear from you -- what can I grab for you tonight?" },
  { id: 'bm_george', label: 'Neil', desc: 'Indian — clear, professional (male)', accent: 'indian', sampleText: "Hello there, lovely to hear from you -- what shall I put together?" },
]

// Character types — each pairs a premium ElevenLabs voice with a charming,
// family-friendly persona. Ids/labels/taglines/catchphrases mirror the backend
// registry (services/phone_agent/personas.py) — keep in lockstep.
export const CHARACTER_OPTIONS: { id: string; label: string; tagline: string; catchphrase: string }[] = [
  { id: 'vinny', label: 'Vinny', tagline: 'Fun Italian guy — big New York pizzeria energy', catchphrase: "Whaddya havin' today, my friend?" },
  { id: 'mel', label: 'Mel', tagline: 'Aussie mate — sunny, easygoing, zero fuss', catchphrase: "G'day! What are we gettin' ya today, mate?" },
  { id: 'rosie', label: 'Rosie', tagline: 'Southern sweetheart — warm as fresh biscuits', catchphrase: 'What can I get ya, sugar?' },
  { id: 'priya', label: 'Priya', tagline: 'Warm Indian host — everything first-class and fresh', catchphrase: 'Haan ji, what would you like today?' },
  { id: 'jacques', label: 'Jacques', tagline: 'French bistro charmer — every order is magnifique', catchphrase: 'Bonjour! What may I prepare for you?' },
  { id: 'carlos', label: 'Carlos', tagline: 'Taqueria amigo — lively, generous, muy fresh', catchphrase: '¡Órale! What are we making for you today, amigo?' },
  { id: 'sam', label: 'Sam', tagline: 'Classic diner pro — smooth, fast, friendly', catchphrase: 'You got it, boss.' },
  { id: 'mei', label: 'Mei', tagline: 'Bubbly and upbeat — makes ordering feel fun', catchphrase: 'Ooh, good choice! What else?' },
]

export const DEFAULT_PERSONALITY: VoicePersonality = {
  formality: 0.5,
  upsell: 'gentle',
  humor: false,
  customGreeting: '',
  customHold: '',
  customClosing: '',
  character: '',
  brandKeywords: [],
}
