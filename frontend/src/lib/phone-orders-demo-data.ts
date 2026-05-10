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
  orderType: 'pickup' | 'delivery' | 'dine_in'
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
  orderTypes: ('pickup' | 'delivery' | 'dine_in')[]
  menu: PhoneMenuItem[]
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

function h(s: string): number {
  let v = 0
  for (let i = 0; i < s.length; i++) v = ((v << 5) - v + s.charCodeAt(i)) | 0
  return v
}

function rng(seed: number): [number, number] {
  const n = (seed * 1664525 + 1013904223) | 0
  return [(n >>> 0) / 4294967296, n]
}

function rngInt(seed: number, min: number, max: number): [number, number] {
  const [r, n] = rng(seed)
  return [Math.floor(min + r * (max - min + 1)), n]
}

function rngPick<T>(arr: T[], seed: number): [T, number] {
  const [i, n] = rngInt(seed, 0, arr.length - 1)
  return [arr[i], n]
}

const FN = ['Sarah','Mike','David','Lisa','James','Emma','Chris','Jessica','Ryan','Amy','Tom','Nicole','Alex','Maria','Kevin','Sophia','Brian','Rachel','Daniel','Olivia']
const LN = ['Chen','Johnson','Smith','Park','Wang','Kim','Lee','Brown','Davis','Wilson','Garcia','Martinez','Anderson','Taylor','Thomas','Moore','Jackson','White','Harris','Clark']
const US_AC = ['212','917','646','713','832','310','323','512','312','773']
const CA_AC = ['514','438','416','647','613','604','778']

const BUSINESSES: PhoneBizConfig[] = [
  {
    id: 'tony-pizza', name: "Tony's Pizza Palace", vertical: 'Pizza Shop', country: 'US',
    currency: '$', taxRate: 0.08875, phone: '+1 (212) 555-0101',
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
    currency: 'CA$', taxRate: 0.14975, phone: '+1 (514) 555-0601',
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

function fmtT(sec: number): string {
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
}

function buildTranscript(
  biz: PhoneBizConfig, status: CallStatus, items: PhoneOrderItem[], name: string, ot: string,
): TranscriptLine[] {
  const lines: TranscriptLine[] = [{ speaker: 'agent', text: biz.greeting, time: '0:00' }]

  if (status === 'order_placed') {
    const otLabel = ot.replace('_', ' ')
    lines.push({ speaker: 'caller', text: `Hi, I'd like to place an order for ${otLabel}.`, time: '0:03' })
    lines.push({ speaker: 'agent', text: 'Of course! What would you like?', time: '0:05' })
    let t = 8
    for (const item of items) {
      const desc = item.qty > 1 ? `${item.qty} of the ${item.name}` : `the ${item.name}`
      lines.push({ speaker: 'caller', text: `I'll have ${desc}, please.`, time: fmtT(t) })
      t += 5
      lines.push({ speaker: 'agent', text: `Got it, ${item.name}. Anything else?`, time: fmtT(t) })
      t += 4
    }
    lines.push({ speaker: 'caller', text: "That's everything.", time: fmtT(t) })
    t += 3
    const sub = Math.round(items.reduce((s, i) => s + i.price * i.qty, 0) * 100) / 100
    const tot = Math.round((sub + sub * biz.taxRate) * 100) / 100
    lines.push({ speaker: 'agent', text: `Your total comes to ${biz.currency}${tot.toFixed(2)} with tax. Name for the order?`, time: fmtT(t) })
    t += 5
    lines.push({ speaker: 'caller', text: name, time: fmtT(t) })
    t += 2
    const eta = ot === 'delivery' ? '35-45 minutes' : '15-20 minutes'
    lines.push({ speaker: 'agent', text: `Perfect, ${name.split(' ')[0]}! Your order will be ready in about ${eta}.`, time: fmtT(t) })
    t += 4
    lines.push({ speaker: 'caller', text: 'Sounds great, thank you!', time: fmtT(t) })
    lines.push({ speaker: 'agent', text: `Thank you for your order! Have a great day!`, time: fmtT(t + 2) })
  } else if (status === 'no_order') {
    lines.push({ speaker: 'caller', text: 'Hi, what are your hours today?', time: '0:03' })
    lines.push({ speaker: 'agent', text: "We're open today from 11 AM to 10 PM. Would you like to place an order?", time: '0:06' })
    lines.push({ speaker: 'caller', text: 'Not right now, just checking. Thanks!', time: '0:10' })
    lines.push({ speaker: 'agent', text: 'No problem! Call back anytime.', time: '0:12' })
  } else if (status === 'transferred') {
    lines.push({ speaker: 'caller', text: 'Hi, I have a question about a catering order.', time: '0:03' })
    lines.push({ speaker: 'agent', text: "For catering orders, let me connect you with our manager. One moment please.", time: '0:07' })
    lines.push({ speaker: 'caller', text: 'Sure, thanks.', time: '0:10' })
    lines.push({ speaker: 'agent', text: `Transferring you now. Thank you for calling ${biz.name}!`, time: '0:13' })
  } else {
    lines.push({ speaker: 'caller', text: "Hi, I'd like to place an order.", time: '0:03' })
    lines.push({ speaker: 'agent', text: 'Absolutely! What can I get for you today?', time: '0:05' })
  }

  return lines
}

export function generateCalls(biz: PhoneBizConfig, days: number): PhoneCallEntry[] {
  const calls: PhoneCallEntry[] = []
  const now = new Date()
  let seed = h(biz.id + 'calls')
  const areaCodes = biz.country === 'CA' ? CA_AC : US_AC

  for (let d = days - 1; d >= 0; d--) {
    const date = new Date(now)
    date.setDate(date.getDate() - d)
    date.setHours(0, 0, 0, 0)
    const dow = date.getDay()
    const weekend = dow === 0 || dow === 6

    const [count, s1] = rngInt(seed, weekend ? 3 : 1, weekend ? 7 : 5)
    seed = s1

    for (let c = 0; c < count; c++) {
      const [statusR, s2] = rng(seed)
      seed = s2
      let status: CallStatus
      if (d === 0 && c === count - 1) status = 'in_progress'
      else if (statusR < 0.58) status = 'order_placed'
      else if (statusR < 0.75) status = 'no_order'
      else if (statusR < 0.90) status = 'transferred'
      else status = 'no_order'

      const [fn, s3] = rngPick(FN, seed); seed = s3
      const [ln, s4] = rngPick(LN, seed); seed = s4
      const [ac, s5] = rngPick(areaCodes, seed); seed = s5
      const [pn, s6] = rngInt(seed, 1000000, 9999999); seed = s6

      const [hourR, s7] = rng(seed); seed = s7
      const hour = hourR < 0.45 ? 11 + Math.floor(hourR / 0.45 * 3) : 17 + Math.floor((hourR - 0.45) / 0.55 * 4)
      const [minute, s8] = rngInt(seed, 0, 59); seed = s8
      const callDate = new Date(date)
      callDate.setHours(hour, minute, 0, 0)

      let items: PhoneOrderItem[] = []
      let subtotal = 0
      if (status === 'order_placed') {
        const [ic, s9] = rngInt(seed, 1, 4); seed = s9
        const used = new Set<string>()
        for (let i = 0; i < ic; i++) {
          const [mi, s10] = rngPick(biz.menu, seed); seed = s10
          if (used.has(mi.id)) continue
          used.add(mi.id)
          const [qty, s11] = rngInt(seed, 1, 2); seed = s11
          items.push({ name: mi.name, qty, price: mi.price })
          subtotal += mi.price * qty
        }
        if (items.length === 0) {
          items = [{ name: biz.menu[0].name, qty: 1, price: biz.menu[0].price }]
          subtotal = biz.menu[0].price
        }
      }

      subtotal = Math.round(subtotal * 100) / 100
      const tax = Math.round(subtotal * biz.taxRate * 100) / 100
      const total = Math.round((subtotal + tax) * 100) / 100

      const [durR, s12] = rng(seed); seed = s12
      const durationSec = status === 'order_placed'
        ? Math.floor(90 + durR * 150)
        : status === 'transferred'
          ? Math.floor(30 + durR * 60)
          : status === 'in_progress'
            ? Math.floor(10 + durR * 30)
            : Math.floor(15 + durR * 45)

      const [ot, s13] = rngPick(biz.orderTypes, seed); seed = s13
      const callerName = status === 'no_order' && durR < 0.3 ? '' : `${fn} ${ln}`

      let paymentStatus: PaymentStatus = 'none'
      let smsSent = false
      const paymentLink = status === 'order_placed' ? `https://pay.meridian.ai/checkout/${biz.id}-${d}-${c}` : ''
      if (status === 'order_placed') {
        smsSent = true
        const [payR, s14] = rng(seed); seed = s14
        if (d === 0 && c === count - 1) paymentStatus = 'pending'
        else if (payR < 0.78) paymentStatus = 'paid'
        else if (payR < 0.92) paymentStatus = 'pending'
        else paymentStatus = 'expired'
      }

      calls.push({
        id: `${biz.id}-${d}-${c}`,
        phone: `+1 (${ac}) ${String(pn).slice(0, 3)}-${String(pn).slice(3)}`,
        name: callerName,
        status,
        duration: fmtT(durationSec),
        durationSec,
        items,
        subtotal,
        tax,
        total,
        orderType: ot,
        transcript: buildTranscript(biz, status, items, callerName || 'Caller', ot),
        createdAt: callDate.toISOString(),
        paymentStatus,
        paymentLink,
        smsSent,
      })
    }
  }

  return calls.reverse()
}

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

export const VOICE_OPTIONS = [
  { id: 'af_bella', label: 'Bella', desc: 'Warm, professional (female)' },
  { id: 'af_sarah', label: 'Sarah', desc: 'Friendly, casual (female)' },
  { id: 'am_adam', label: 'Adam', desc: 'Authoritative (male)' },
  { id: 'am_michael', label: 'Michael', desc: 'Conversational (male)' },
]
