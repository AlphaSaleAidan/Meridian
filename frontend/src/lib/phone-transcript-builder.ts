/**
 * Transcript builder & call generator for phone orders demo data.
 * Produces natural-sounding conversations with varied patterns:
 * standard, regular customer, indecisive, large group, complaint.
 */
import type {
  PhoneBizConfig, PhoneMenuItem, PhoneOrderItem, PhoneCallEntry,
  TranscriptLine, CallStatus, PaymentStatus,
} from './phone-orders-demo-data'

/* ---- seeded RNG helpers ---- */
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

function fmtT(sec: number): string {
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
}

/* ---- Conversation patterns ---- */
type ConvoPattern = 'standard' | 'regular' | 'indecisive' | 'large_group' | 'complaint'

function pickConvoPattern(seed: number): [ConvoPattern, number] {
  const [r, next] = rng(seed)
  if (r < 0.40) return ['standard', next]
  if (r < 0.55) return ['regular', next]
  if (r < 0.70) return ['indecisive', next]
  if (r < 0.85) return ['large_group', next]
  return ['complaint', next]
}

function nextTime(base: number, minGap: number, maxGap: number, seed: number): [number, number] {
  const [r, next] = rng(seed)
  return [base + minGap + Math.floor(r * (maxGap - minGap)), next]
}

function getUpsell(biz: PhoneBizConfig, seed: number): [string | null, PhoneMenuItem | null, number] {
  const pool = biz.menu.filter(m => m.category === 'Drinks' || m.category === 'Dessert')
  if (pool.length === 0) return [null, null, seed]
  const [item, next] = rngPick(pool, seed)
  const prefixes = [
    `Would you like to add a ${item.name} for just ${biz.currency}${item.price.toFixed(2)}?`,
    `Can I tempt you with a ${item.name}? It's only ${biz.currency}${item.price.toFixed(2)}.`,
    `A lot of folks love our ${item.name} with that. Want one?`,
  ]
  const [line, next2] = rngPick(prefixes, next)
  return [line, item, next2]
}

function getPopularComment(item: { name: string }, seed: number): [string, number] {
  const comments = [
    `Great choice! The ${item.name} is one of our most popular items.`,
    `Oh you'll love that, the ${item.name} is fantastic.`,
    `Excellent pick! That ${item.name} is a customer favorite.`,
    `Nice! The ${item.name} has been flying off the menu lately.`,
  ]
  return rngPick(comments, seed)
}

/* ---- Build transcript ---- */
function buildTranscript(
  biz: PhoneBizConfig, status: CallStatus, items: PhoneOrderItem[],
  name: string, ot: string, seed: number,
): TranscriptLine[] {
  const lines: TranscriptLine[] = []
  let t = 0
  let s = seed
  const push = (speaker: 'agent' | 'caller', text: string) => {
    lines.push({ speaker, text, time: fmtT(t) })
  }

  push('agent', biz.greeting)

  if (status === 'order_placed') {
    const [pattern, s1] = pickConvoPattern(s); s = s1
    const otLabel = ot.replace('_', ' ')
    const firstName = name.split(' ')[0] || 'there'

    if (pattern === 'regular') {
      ;[t, s] = nextTime(t, 2, 4, s)
      const [r, s2] = rng(s); s = s2
      if (r < 0.5) {
        push('caller', `Hey, it's ${firstName}. I'll have my usual.`)
        ;[t, s] = nextTime(t, 2, 4, s)
        const itemList = items.length > 0 ? items.map(i => `${i.qty > 1 ? i.qty + 'x ' : ''}${i.name}`).join(' and ') : 'your favorites'
        push('agent', `Hey ${firstName}! Good to hear from you. So that's the ${itemList}, right?`)
        ;[t, s] = nextTime(t, 2, 3, s)
        push('caller', 'Yep, exactly.')
        ;[t, s] = nextTime(t, 1, 3, s)
        push('agent', `Perfect. For ${otLabel} like last time?`)
        ;[t, s] = nextTime(t, 1, 2, s)
        push('caller', 'Yeah, same as always.')
      } else {
        push('caller', `Hi, it's ${firstName} again. Can I get the same thing I had last week?`)
        ;[t, s] = nextTime(t, 2, 4, s)
        const itemDesc = items.length > 0 ? items.map(i => i.name).join(', ') : 'your favorites'
        push('agent', `Of course, ${firstName}! I've got you down for ${itemDesc}. ${otLabel === 'delivery' ? 'Delivery to the same address?' : `For ${otLabel}?`}`)
        ;[t, s] = nextTime(t, 2, 3, s)
        push('caller', 'That works, thanks!')
      }
    } else if (pattern === 'indecisive') {
      ;[t, s] = nextTime(t, 3, 5, s)
      push('caller', `Hi, I'd like to order for ${otLabel}. Um, what do you recommend?`)
      ;[t, s] = nextTime(t, 3, 5, s)
      if (items.length > 0) {
        const [comment, s3] = getPopularComment(items[0], s); s = s3
        push('agent', `${comment} And if you're looking for something on the side, the ${biz.menu.find(m => m.category === 'Sides')?.name || 'sides'} are really good too.`)
      } else {
        push('agent', `Everything on our menu is great, but I'd especially recommend the ${biz.menu[0]?.name}. It's been a customer favorite!`)
      }
      ;[t, s] = nextTime(t, 4, 7, s)
      push('caller', 'Hmm, let me think... okay, yeah, I\'ll try that.')
      ;[t, s] = nextTime(t, 2, 4, s)
      push('agent', 'Awesome! Anything else catch your eye?')
      if (items.length > 1) {
        ;[t, s] = nextTime(t, 5, 8, s)
        push('caller', `Actually, what about the ${items[1].name}? Is that any good?`)
        ;[t, s] = nextTime(t, 2, 4, s)
        push('agent', `Oh absolutely, that's another great one. Want me to add it?`)
        ;[t, s] = nextTime(t, 2, 3, s)
        push('caller', 'Sure, why not. Let\'s do it.')
        ;[t, s] = nextTime(t, 1, 3, s)
        push('agent', 'You got it!')
        for (let i = 2; i < items.length; i++) {
          ;[t, s] = nextTime(t, 3, 5, s)
          push('caller', `Oh, and can you also throw in ${items[i].qty > 1 ? items[i].qty + ' of the' : 'the'} ${items[i].name}?`)
          ;[t, s] = nextTime(t, 1, 3, s)
          push('agent', 'Of course, adding that now.')
        }
      }
      ;[t, s] = nextTime(t, 3, 5, s)
      push('caller', 'Okay, I think that\'s it.')
    } else if (pattern === 'large_group') {
      ;[t, s] = nextTime(t, 3, 5, s)
      push('caller', `Hi! I need to place a bigger order for a group, for ${otLabel}.`)
      ;[t, s] = nextTime(t, 2, 4, s)
      push('agent', 'Of course, I\'d be happy to help with that! How many people are we feeding?')
      ;[t, s] = nextTime(t, 2, 4, s)
      const [groupSize, s4] = rngInt(s, 4, 8); s = s4
      push('caller', `About ${groupSize} of us. Let me go through the list...`)
      ;[t, s] = nextTime(t, 2, 3, s)
      push('agent', 'Take your time, I\'m ready when you are!')
      for (let i = 0; i < items.length; i++) {
        ;[t, s] = nextTime(t, 3, 6, s)
        const item = items[i]
        const [modR, s5] = rng(s); s = s5
        if (modR < 0.3 && i > 0) {
          const mods = ['without onions', 'extra spicy', 'on the side', 'no cheese', 'gluten free if possible']
          const [mod, s6] = rngPick(mods, s); s = s6
          push('caller', `${item.qty > 1 ? item.qty + ' of the' : 'One'} ${item.name}, but ${mod}.`)
          ;[t, s] = nextTime(t, 2, 4, s)
          push('agent', `Got it, ${item.name} ${mod}. No problem at all!`)
        } else {
          push('caller', `${item.qty > 1 ? item.qty + ' of the' : 'And the'} ${item.name}.`)
          ;[t, s] = nextTime(t, 2, 3, s)
          const acks = ['Got it!', 'Added.', 'Okay!', 'Sure thing.']
          const [ack, s7] = rngPick(acks, s); s = s7
          push('agent', `${ack} ${i < items.length - 1 ? 'What else?' : 'Anything else for the group?'}`)
        }
      }
      ;[t, s] = nextTime(t, 3, 5, s)
      push('caller', 'I think that covers everyone.')
    } else if (pattern === 'complaint') {
      ;[t, s] = nextTime(t, 3, 5, s)
      push('caller', 'Hi, so last time I ordered, my food was kind of cold when it arrived. Just wanted to mention that.')
      ;[t, s] = nextTime(t, 2, 4, s)
      push('agent', `Oh no, I'm really sorry to hear that, ${firstName}. That's definitely not up to our standards. I'll make a note for the kitchen to double-check everything this time. Can I offer you a free side or drink with your order today?`)
      ;[t, s] = nextTime(t, 3, 5, s)
      push('caller', 'Oh, that\'s nice of you. Sure, I appreciate that. Let me go ahead and order then.')
      ;[t, s] = nextTime(t, 2, 3, s)
      push('agent', 'Absolutely! What would you like?')
      for (let i = 0; i < items.length; i++) {
        ;[t, s] = nextTime(t, 3, 6, s)
        const desc = items[i].qty > 1 ? `${items[i].qty} of the ${items[i].name}` : `the ${items[i].name}`
        push('caller', `I'll have ${desc}.`)
        ;[t, s] = nextTime(t, 2, 4, s)
        if (i === 0) { const [c, s8] = getPopularComment(items[i], s); s = s8; push('agent', c) }
        else push('agent', `Added! ${i === items.length - 1 ? 'Anything else?' : 'What\'s next?'}`)
      }
      ;[t, s] = nextTime(t, 2, 4, s)
      push('caller', `That's all. For ${otLabel}, please.`)
    } else {
      // Standard flow
      ;[t, s] = nextTime(t, 3, 5, s)
      const [openR, s9] = rng(s); s = s9
      const openers = [`Hi, I'd like to place an order for ${otLabel} please.`, `Yeah, hi. Can I get an order for ${otLabel}?`, `Hey! I'd like to order something for ${otLabel}.`]
      push('caller', openers[Math.floor(openR * openers.length)])
      ;[t, s] = nextTime(t, 2, 4, s)
      const [agentOpen, s10] = rngPick(['Of course! What would you like?', 'Absolutely! What can I get for you?', 'Sure thing! What sounds good today?'], s); s = s10
      push('agent', agentOpen)
      for (let i = 0; i < items.length; i++) {
        ;[t, s] = nextTime(t, 4, 8, s)
        const desc = items[i].qty > 1 ? `${items[i].qty} of the ${items[i].name}` : `the ${items[i].name}`
        const callerLines = [`I'll have ${desc}, please.`, `Can I get ${desc}?`, `Let me do ${desc}.`, `And ${desc}.`]
        push('caller', i === 0 ? callerLines[0] : callerLines[Math.min(i, callerLines.length - 1)])
        ;[t, s] = nextTime(t, 2, 5, s)
        if (i === 0) {
          const [popR, s11] = rng(s); s = s11
          if (popR < 0.5) { const [c, s12] = getPopularComment(items[i], s); s = s12; push('agent', `${c} Anything else?`) }
          else push('agent', `Got it, ${items[i].name}! What else?`)
        } else if (i < items.length - 1) { const [ack, s13] = rngPick(['Sure thing! Anything else?', 'Added! Keep going.', 'Got it! What else?'], s); s = s13; push('agent', ack) }
        else push('agent', 'Got it! Is that everything?')
      }
      const [upsellR, s14] = rng(s); s = s14
      if (upsellR < 0.5) {
        ;[t, s] = nextTime(t, 1, 3, s)
        const [upsellLine, upsellItem, s15] = getUpsell(biz, s); s = s15
        if (upsellLine) {
          push('agent', upsellLine)
          ;[t, s] = nextTime(t, 3, 5, s)
          const [acceptR, s16] = rng(s); s = s16
          if (acceptR < 0.35 && upsellItem) { push('caller', 'Actually yeah, that sounds good. Add it on.'); ;[t, s] = nextTime(t, 1, 3, s); push('agent', 'You got it!') }
          else { push('caller', "No thanks, I'm good."); ;[t, s] = nextTime(t, 1, 2, s); push('agent', 'No worries!') }
        }
      }
      ;[t, s] = nextTime(t, 2, 4, s)
      push('caller', "That's everything.")
    }

    // Common closing
    ;[t, s] = nextTime(t, 2, 5, s)
    const sub = Math.round(items.reduce((a, i) => a + i.price * i.qty, 0) * 100) / 100
    const tot = Math.round((sub + sub * biz.taxRate) * 100) / 100
    push('agent', `Alright, your total comes to ${biz.currency}${tot.toFixed(2)} including tax. Can I get a name for the order?`)
    ;[t, s] = nextTime(t, 3, 5, s)
    push('caller', name)
    ;[t, s] = nextTime(t, 2, 4, s)
    const eta = ot === 'delivery' ? '35 to 45 minutes' : '15 to 20 minutes'
    const [closing, s17] = rngPick([
      `Perfect, ${firstName}! Your order will be ready in about ${eta}. I'm sending you a text with the details and a payment link now.`,
      `Great, ${firstName}! We'll have that ready in roughly ${eta}. You'll get an SMS with your order confirmation shortly.`,
      `You're all set, ${firstName}! Expect about ${eta}. Check your phone for the payment link.`,
    ], s); s = s17
    push('agent', closing)
    ;[t, s] = nextTime(t, 2, 4, s)
    const [ty, s18] = rngPick(['Sounds great, thanks!', 'Awesome, thank you!', 'Perfect, appreciate it!', 'Thanks so much!'], s); s = s18
    push('caller', ty)
    ;[t, s] = nextTime(t, 1, 3, s)
    push('agent', `Thank you for your order! Have a great ${new Date().getHours() >= 17 ? 'evening' : 'day'}!`)

  } else if (status === 'no_order') {
    const [noOrderR, s1] = rng(s); s = s1
    if (noOrderR < 0.4) {
      ;[t, s] = nextTime(t, 2, 4, s); push('caller', 'Hi, what are your hours today?')
      ;[t, s] = nextTime(t, 2, 4, s); push('agent', "We're open today from 11 AM to 10 PM. Would you like to place an order?")
      ;[t, s] = nextTime(t, 3, 5, s); push('caller', 'Not right now, just checking. Thanks!')
      ;[t, s] = nextTime(t, 1, 3, s); push('agent', 'No problem at all! Call us back anytime.')
    } else if (noOrderR < 0.7) {
      ;[t, s] = nextTime(t, 2, 4, s); push('caller', 'Hey, do you guys do catering for events?')
      ;[t, s] = nextTime(t, 3, 5, s); push('agent', "We do! For catering inquiries I'd recommend emailing us or calling during business hours. Is there anything else?")
      ;[t, s] = nextTime(t, 2, 4, s); push('caller', "No, that's fine. I'll send an email. Thanks.")
      ;[t, s] = nextTime(t, 1, 3, s); push('agent', 'Sounds good! Have a great day.')
    } else {
      ;[t, s] = nextTime(t, 2, 4, s); push('caller', 'Hi, I was wondering if you have any vegan options?')
      ;[t, s] = nextTime(t, 3, 5, s)
      const veggieItem = biz.menu.find(m => /veg|salad|falafel|edamame/i.test(m.name))
      push('agent', veggieItem ? `Absolutely! We have the ${veggieItem.name} which is a great option. Would you like to order?` : 'Let me check on that... we can accommodate most dietary preferences. Would you like to place an order?')
      ;[t, s] = nextTime(t, 3, 5, s); push('caller', "I'll think about it and call back. Thank you!")
      ;[t, s] = nextTime(t, 1, 3, s); push('agent', 'Of course! We look forward to your call.')
    }
  } else if (status === 'transferred') {
    const [txR, s1] = rng(s); s = s1
    if (txR < 0.5) {
      ;[t, s] = nextTime(t, 2, 4, s); push('caller', 'Hi, I have a question about a catering order for next weekend.')
      ;[t, s] = nextTime(t, 3, 5, s); push('agent', "For catering orders, let me connect you with our manager. One moment please!")
      ;[t, s] = nextTime(t, 2, 3, s); push('caller', 'Sure, thanks.')
      ;[t, s] = nextTime(t, 2, 4, s); push('agent', `Transferring you now. Thank you for calling ${biz.name}!`)
    } else {
      ;[t, s] = nextTime(t, 2, 4, s); push('caller', "Hi, I need to talk to someone about a problem with my order from yesterday.")
      ;[t, s] = nextTime(t, 3, 5, s); push('agent', "I'm sorry to hear there was an issue. Let me transfer you to our manager right away.")
      ;[t, s] = nextTime(t, 2, 3, s); push('caller', 'Okay, appreciate it.')
      ;[t, s] = nextTime(t, 2, 4, s); push('agent', 'Connecting you now. Thank you for your patience.')
    }
  } else {
    ;[t, s] = nextTime(t, 2, 4, s); push('caller', "Hi, I'd like to place an order.")
    ;[t, s] = nextTime(t, 2, 4, s); push('agent', 'Absolutely! What can I get for you today?')
  }

  return lines
}

/* ---- Generate call log for a business ---- */
export function generateCalls(biz: PhoneBizConfig, days: number): PhoneCallEntry[] {
  const calls: PhoneCallEntry[] = []
  const now = new Date()
  let seed = h(biz.id + 'calls')
  const areaCodes = biz.country === 'CA' ? CA_AC : US_AC

  for (let d = days - 1; d >= 0; d--) {
    const date = new Date(now); date.setDate(date.getDate() - d); date.setHours(0, 0, 0, 0)
    const weekend = date.getDay() === 0 || date.getDay() === 6
    const [count, s1] = rngInt(seed, weekend ? 3 : 1, weekend ? 7 : 5); seed = s1

    for (let c = 0; c < count; c++) {
      const [statusR, s2] = rng(seed); seed = s2
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
      const callDate = new Date(date); callDate.setHours(hour, minute, 0, 0)

      let items: PhoneOrderItem[] = []
      let subtotal = 0
      if (status === 'order_placed') {
        const [ic, s9] = rngInt(seed, 1, 4); seed = s9
        const used = new Set<string>()
        for (let i = 0; i < ic; i++) {
          const [mi, s10] = rngPick(biz.menu, seed); seed = s10
          if (used.has(mi.id)) continue; used.add(mi.id)
          const [qty, s11] = rngInt(seed, 1, 2); seed = s11
          items.push({ name: mi.name, qty, price: mi.price }); subtotal += mi.price * qty
        }
        if (items.length === 0) { items = [{ name: biz.menu[0].name, qty: 1, price: biz.menu[0].price }]; subtotal = biz.menu[0].price }
      }

      subtotal = Math.round(subtotal * 100) / 100
      const tax = Math.round(subtotal * biz.taxRate * 100) / 100
      const total = Math.round((subtotal + tax) * 100) / 100
      const [durR, s12] = rng(seed); seed = s12
      const durationSec = status === 'order_placed' ? Math.floor(90 + durR * 150)
        : status === 'transferred' ? Math.floor(30 + durR * 60)
        : status === 'in_progress' ? Math.floor(10 + durR * 30) : Math.floor(15 + durR * 45)
      const [ot, s13] = rngPick(biz.orderTypes, seed); seed = s13
      const callerName = status === 'no_order' && durR < 0.3 ? '' : `${fn} ${ln}`

      let paymentStatus: PaymentStatus = 'none'; let smsSent = false
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
        id: `${biz.id}-${d}-${c}`, phone: `+1 (${ac}) ${String(pn).slice(0, 3)}-${String(pn).slice(3)}`,
        name: callerName, status, duration: fmtT(durationSec), durationSec,
        items, subtotal, tax, total, orderType: ot,
        transcript: buildTranscript(biz, status, items, callerName || 'Caller', ot, seed),
        createdAt: callDate.toISOString(), paymentStatus, paymentLink, smsSent,
      })
    }
  }
  return calls.reverse()
}
