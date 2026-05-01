/**
 * Proposal PDF generator — Glowing Obsidian style.
 *
 * Renders slides into a hidden container, captures them with html2canvas,
 * and assembles the final PDF with jsPDF.
 */

import type { PlanTier } from './proposal-plans'
import type { SalesRepProfile } from './sales-auth'

export interface ProposalInput {
  businessName: string
  ownerName: string
  email: string
  phone: string
  plan: PlanTier
  customPrice?: number
  setupFee: number
  firstMonthFree: boolean
  rep: SalesRepProfile
  checkoutUrl?: string
}

/* ------------------------------------------------------------------ */
/*  Marble background SVG generator (procedural, no external images)  */
/* ------------------------------------------------------------------ */

function marbleSvgBackground(seed: number): string {
  const s = seed * 137.5
  const r = (i: number) => {
    const x = Math.sin(s + i * 9.1) * 43758.5453
    return x - Math.floor(x)
  }

  const cracks: string[] = []
  const numCracks = 3 + Math.floor(r(0) * 3)
  for (let i = 0; i < numCracks; i++) {
    const x1 = r(i * 4 + 1) * 1920
    const y1 = r(i * 4 + 2) * 1080
    const x2 = r(i * 4 + 3) * 1920
    const y2 = r(i * 4 + 4) * 1080
    const cx = (x1 + x2) / 2 + (r(i * 4 + 5) - 0.5) * 400
    const cy = (y1 + y2) / 2 + (r(i * 4 + 6) - 0.5) * 400

    cracks.push(`
      <path d="M${x1},${y1} Q${cx},${cy} ${x2},${y2}"
        stroke="url(#glow${i})" stroke-width="${2 + r(i * 4 + 7) * 4}" fill="none"
        filter="url(#blur)" opacity="${0.6 + r(i * 4 + 8) * 0.4}" />
      <path d="M${x1},${y1} Q${cx},${cy} ${x2},${y2}"
        stroke="#c8b0ff" stroke-width="1" fill="none" opacity="0.5" />
    `)
  }

  const gradients = Array.from({ length: numCracks }, (_, i) => `
    <radialGradient id="glow${i}" cx="50%" cy="50%" r="80%">
      <stop offset="0%" stop-color="#9B7FFF" stop-opacity="0.9"/>
      <stop offset="50%" stop-color="#7C5CFF" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#4a2e99" stop-opacity="0"/>
    </radialGradient>
  `).join('')

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">
      <defs>
        ${gradients}
        <filter id="blur"><feGaussianBlur stdDeviation="6"/></filter>
        <radialGradient id="stone" cx="50%" cy="50%" r="70%">
          <stop offset="0%" stop-color="#111118"/>
          <stop offset="100%" stop-color="#06060a"/>
        </radialGradient>
      </defs>
      <rect width="1920" height="1080" fill="url(#stone)"/>
      ${cracks.join('')}
    </svg>
  `)}`
}


/* ------------------------------------------------------------------ */
/*  Slide HTML builders                                                */
/* ------------------------------------------------------------------ */

const SLIDE_CSS = `
  * { margin: 0; padding: 0; box-sizing: border-box; }
  .slide {
    width: 1920px; height: 1080px; position: relative; overflow: hidden;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    color: #F5F5F7; -webkit-font-smoothing: antialiased;
  }
  .slide-bg {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-size: cover; background-position: center; z-index: 0;
  }
  .slide-overlay {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(8,8,10,0.55); z-index: 1;
  }
  .slide-content { position: relative; z-index: 2; padding: 80px 120px; height: 100%; }
  .eyebrow {
    font-family: monospace; font-size: 13px; font-weight: 500;
    letter-spacing: 0.18em; text-transform: uppercase; color: #7C5CFF;
  }
  .eyebrow-cyan { font-family: monospace; font-size: 13px; font-weight: 500; letter-spacing: 0.18em; text-transform: uppercase; color: #4FE3C1; }
  .title { font-family: 'Georgia', serif; font-style: italic; font-size: 88px; font-weight: 400; line-height: 1.05; color: #FFFFFF; }
  .title-hero { font-family: 'Georgia', serif; font-style: italic; font-size: 110px; font-weight: 400; line-height: 1.0; color: #FFFFFF; }
  .subtitle { font-size: 26px; font-weight: 300; line-height: 1.55; color: #A1A1A8; }
  .body { font-size: 22px; font-weight: 400; line-height: 1.6; color: #A1A1A8; }
  .accent-bar { width: 64px; height: 3px; background: linear-gradient(135deg, #7C5CFF, #4FE3C1); }
  .card { background: rgba(14,14,16,0.88); border: 1px solid rgba(255,255,255,0.08); padding: 44px; border-radius: 8px; }
  .card-glow { background: linear-gradient(180deg, rgba(124,92,255,0.12) 0%, rgba(14,14,16,0.88) 60%); border: 1px solid rgba(124,92,255,0.25); padding: 44px; border-radius: 8px; }
  .card-cyan { background: linear-gradient(180deg, rgba(79,227,193,0.10) 0%, rgba(14,14,16,0.88) 60%); border: 1px solid rgba(79,227,193,0.20); padding: 44px; border-radius: 8px; }
  .violet { color: #7C5CFF; }
  .cyan { color: #4FE3C1; }
  .white { color: #FFFFFF; }
  .muted { color: #A1A1A8; }
  .dim { color: #6B6B73; }
  .mono { font-family: monospace; }
  .bold { font-weight: 600; }
  .flex { display: flex; }
  .gap-16 { gap: 16px; }
  .gap-24 { gap: 24px; }
  .gap-32 { gap: 32px; }
  .flex-1 { flex: 1; }
  .text-center { text-align: center; }
  .mt-12 { margin-top: 12px; }
  .mt-16 { margin-top: 16px; }
  .mt-24 { margin-top: 24px; }
  .mt-32 { margin-top: 32px; }
  .mt-40 { margin-top: 40px; }
  .mt-48 { margin-top: 48px; }
  .mb-8 { margin-bottom: 8px; }
  .mb-16 { margin-bottom: 16px; }
  .mb-24 { margin-bottom: 24px; }
  .page-num {
    position: absolute; bottom: 36px; right: 120px;
    font-family: monospace; font-size: 11px; color: #6B6B73;
    letter-spacing: 0.1em; z-index: 2;
  }
  .check { color: #A1A1A8; font-size: 16px; line-height: 1.8; }
  .check::before { content: '✓ '; color: #4FE3C1; }
  .price-big { font-family: monospace; font-size: 56px; font-weight: 600; color: #FFFFFF; }
  .price-tag { font-size: 18px; color: #6B6B73; }
  .btn-violet { display: inline-block; padding: 16px 48px; background: #7C5CFF; color: white; font-weight: 600; font-size: 18px; border-radius: 8px; }
  .qr-container { margin-top: 32px; display: flex; justify-content: center; }
  .qr-container canvas, .qr-container img { width: 200px; height: 200px; }
  .fusion-row {
    display: flex; gap: 24px; align-items: stretch; margin-bottom: 20px;
  }
  .fusion-signal {
    flex: 1; padding: 20px 24px; border-radius: 8px;
    background: rgba(14,14,16,0.88); border: 1px solid rgba(255,255,255,0.06);
  }
  .fusion-plus {
    display: flex; align-items: center; font-size: 28px; font-weight: 700; color: #7C5CFF; padding: 0 4px;
  }
  .fusion-equals {
    display: flex; align-items: center; font-size: 28px; font-weight: 700; color: #4FE3C1; padding: 0 4px;
  }
  .fusion-insight {
    flex: 1.3; padding: 20px 24px; border-radius: 8px;
    background: linear-gradient(135deg, rgba(124,92,255,0.12), rgba(79,227,193,0.08));
    border: 1px solid rgba(124,92,255,0.20);
  }
  .signal-icon { font-size: 20px; margin-bottom: 6px; }
  .signal-label { font-family: monospace; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: #6B6B73; margin-bottom: 4px; }
  .signal-data { font-size: 15px; color: #F5F5F7; font-weight: 500; line-height: 1.4; }
  .insight-label { font-family: monospace; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: #4FE3C1; margin-bottom: 4px; }
  .insight-data { font-size: 15px; color: #F5F5F7; font-weight: 600; line-height: 1.4; }
  .insight-action { font-size: 13px; color: #A1A1A8; margin-top: 4px; }
`

function slideWrapper(bgSeed: number, content: string, pageNum: string): string {
  return `
    <div class="slide">
      <div class="slide-bg" style="background-image:url('${marbleSvgBackground(bgSeed)}')"></div>
      <div class="slide-overlay"></div>
      <div class="slide-content">${content}</div>
      <div class="page-num">${pageNum}</div>
    </div>
  `
}

function buildSlides(input: ProposalInput): string[] {
  const { businessName, ownerName, plan, customPrice, setupFee, firstMonthFree, rep, checkoutUrl } = input
  const price = customPrice || plan.price
  const slides: string[] = []
  const total = 9 // Total slide count
  const pad = (n: number) => `${String(n).padStart(2, '0')} / ${String(total).padStart(2, '0')}`

  // ═══════════════════════════════════════════════════════════════
  // Slide 1: Title
  // ═══════════════════════════════════════════════════════════════
  slides.push(slideWrapper(1, `
    <div style="display:flex;flex-direction:column;justify-content:center;height:100%;">
      <div class="mb-24"><span class="eyebrow">MERIDIAN INTELLIGENCE · PROPOSAL</span></div>
      <div class="title-hero">Prepared for</div>
      <div class="title-hero" style="color:#7C5CFF;margin-top:-10px;">${businessName}</div>
      <div class="mt-40" style="max-width:700px;">
        <p class="subtitle">AI-powered analytics that turns your POS data + camera feeds into revenue growth.</p>
      </div>
      <div class="mt-48" style="font-size:15px;color:#6B6B73;">Prepared by ${rep.name} · ${rep.email}${rep.phone ? ' · ' + rep.phone : ''}</div>
    </div>
  `, pad(1)))

  // ═══════════════════════════════════════════════════════════════
  // Slide 2: The Problem / Opportunity
  // ═══════════════════════════════════════════════════════════════
  slides.push(slideWrapper(2, `
    <div class="mb-16"><span class="eyebrow">THE OPPORTUNITY</span></div>
    <div class="title" style="max-width:1100px;">What you're missing without analytics</div>
    <div class="mt-12"><div class="accent-bar"></div></div>
    <div class="flex gap-32 mt-48">
      <div class="card flex-1">
        <div style="font-family:monospace;font-size:72px;font-weight:600;color:#7C5CFF;">62%</div>
        <div style="font-family:monospace;font-size:12px;font-weight:500;letter-spacing:0.14em;text-transform:uppercase;color:#A1A1A8;margin-top:14px;">of restaurants fail in Year 1</div>
        <p class="body" style="margin-top:20px;font-size:17px;">Most never see the data patterns that could have saved them.</p>
      </div>
      <div class="card flex-1">
        <div style="font-family:monospace;font-size:72px;font-weight:600;color:#4FE3C1;">24/7</div>
        <div style="font-family:monospace;font-size:12px;font-weight:500;letter-spacing:0.14em;text-transform:uppercase;color:#A1A1A8;margin-top:14px;">AI monitoring your data</div>
        <p class="body" style="margin-top:20px;font-size:17px;">Meridian watches your sales patterns and alerts you before problems become losses.</p>
      </div>
      <div class="card flex-1">
        <div style="font-family:monospace;font-size:72px;font-weight:600;color:#9B7FFF;">5 min</div>
        <div style="font-family:monospace;font-size:12px;font-weight:500;letter-spacing:0.14em;text-transform:uppercase;color:#A1A1A8;margin-top:14px;">to get started</div>
        <p class="body" style="margin-top:20px;font-size:17px;">Connect your POS — insights start flowing immediately. No hardware needed.</p>
      </div>
    </div>
  `, pad(2)))

  // ═══════════════════════════════════════════════════════════════
  // Slide 3: Plan Features
  // ═══════════════════════════════════════════════════════════════
  const featureHtml = plan.features.map(f => `<div class="check">${f}</div>`).join('')
  slides.push(slideWrapper(3, `
    <div class="mb-16"><span class="eyebrow">YOUR PLAN</span></div>
    <div class="title">Meridian ${plan.label}</div>
    <div class="mt-12"><div class="accent-bar"></div></div>
    <div class="flex gap-32 mt-48">
      <div class="card-glow flex-1" style="padding:48px;">
        <div style="font-family:monospace;font-size:14px;color:#7C5CFF;margin-bottom:24px;letter-spacing:0.1em;">WHAT'S INCLUDED</div>
        ${featureHtml}
      </div>
      <div class="card flex-1" style="padding:48px;">
        <div style="font-family:monospace;font-size:14px;color:#4FE3C1;margin-bottom:24px;letter-spacing:0.1em;">PLATFORM HIGHLIGHTS</div>
        <div class="check">5-minute onboarding</div>
        <div class="check">Square + Clover integration</div>
        <div class="check">AI-powered insights engine</div>
        <div class="check">Self-healing data pipelines</div>
        <div class="check">Real-time anomaly detection</div>
        <div class="check">Mobile-friendly dashboard</div>
        ${plan.id !== 'standard' ? '<div class="check">Camera intelligence AI agents</div>' : ''}
        ${plan.id === 'command' ? '<div class="check">Dedicated account manager</div>' : ''}
      </div>
    </div>
  `, pad(3)))

  // ═══════════════════════════════════════════════════════════════
  // Slide 4: POS Analytics Deep Dive
  // ═══════════════════════════════════════════════════════════════
  slides.push(slideWrapper(4, `
    <div class="mb-16"><span class="eyebrow">POS ANALYTICS ENGINE</span></div>
    <div class="title" style="font-size:76px;">Your Sales Data, Decoded</div>
    <div class="mt-12"><div class="accent-bar"></div></div>
    <div class="flex gap-24 mt-40">
      <div class="card flex-1" style="padding:36px;">
        <div style="font-size:32px;margin-bottom:8px;">📊</div>
        <div style="font-size:17px;font-weight:600;color:#7C5CFF;margin-bottom:12px;">Revenue Intelligence</div>
        <div style="font-size:14px;color:#A1A1A8;line-height:1.7;">
          Track hourly, daily, weekly revenue trends. Spot slow days before they drain cash. Get AI alerts when revenue dips below normal.
        </div>
        <div style="margin-top:16px;padding:12px;background:rgba(124,92,255,0.08);border-radius:6px;border:1px solid rgba(124,92,255,0.15);">
          <div style="font-family:monospace;font-size:11px;color:#7C5CFF;margin-bottom:4px;">EXAMPLE INSIGHT</div>
          <div style="font-size:13px;color:#F5F5F7;">"Tuesday lunch revenue dropped 18% vs 4-week avg. Your chicken sandwich combo was 86'd at 11:30am."</div>
        </div>
      </div>
      <div class="card flex-1" style="padding:36px;">
        <div style="font-size:32px;margin-bottom:8px;">🧮</div>
        <div style="font-size:17px;font-weight:600;color:#4FE3C1;margin-bottom:12px;">Menu Engineering</div>
        <div style="font-size:14px;color:#A1A1A8;line-height:1.7;">
          Every item classified as a Star, Plow Horse, Puzzle, or Dog. Know exactly which items to push, which to raise prices on, and which to cut.
        </div>
        <div style="margin-top:16px;padding:12px;background:rgba(79,227,193,0.08);border-radius:6px;border:1px solid rgba(79,227,193,0.15);">
          <div style="font-family:monospace;font-size:11px;color:#4FE3C1;margin-bottom:4px;">EXAMPLE INSIGHT</div>
          <div style="font-size:13px;color:#F5F5F7;">"Your açaí bowl has 62% margin but only 3% of orders. Moving it to position #2 on the menu could increase orders 40%."</div>
        </div>
      </div>
      <div class="card flex-1" style="padding:36px;">
        <div style="font-size:32px;margin-bottom:8px;">🔮</div>
        <div style="font-size:17px;font-weight:600;color:#9B7FFF;margin-bottom:12px;">Predictive Forecasting</div>
        <div style="font-size:14px;color:#A1A1A8;line-height:1.7;">
          AI predicts tomorrow's sales with 90%+ accuracy. Auto-suggested prep lists. Never over-order or under-staff again.
        </div>
        <div style="margin-top:16px;padding:12px;background:rgba(155,127,255,0.08);border-radius:6px;border:1px solid rgba(155,127,255,0.15);">
          <div style="font-family:monospace;font-size:11px;color:#9B7FFF;margin-bottom:4px;">EXAMPLE INSIGHT</div>
          <div style="font-size:13px;color:#F5F5F7;">"Friday's predicted revenue: $4,280 (+12% vs last week). Recommend 2 extra staff for 11am–2pm rush."</div>
        </div>
      </div>
    </div>
  `, pad(4)))

  // ═══════════════════════════════════════════════════════════════
  // Slide 5: Camera Intelligence Deep Dive
  // ═══════════════════════════════════════════════════════════════
  slides.push(slideWrapper(5, `
    <div class="mb-16"><span class="eyebrow-cyan">CAMERA INTELLIGENCE</span></div>
    <div class="title" style="font-size:76px;">Eyes That Never Blink</div>
    <div class="mt-12"><div class="accent-bar"></div></div>
    <div class="flex gap-24 mt-40">
      <div class="card-cyan flex-1" style="padding:36px;">
        <div style="font-size:32px;margin-bottom:8px;">👥</div>
        <div style="font-size:17px;font-weight:600;color:#4FE3C1;margin-bottom:12px;">Foot Traffic Counting</div>
        <div style="font-size:14px;color:#A1A1A8;line-height:1.7;">
          Know exactly how many people walk in every hour. Compare traffic to revenue to find your true conversion rate.
        </div>
        <div style="margin-top:16px;padding:12px;background:rgba(79,227,193,0.08);border-radius:6px;border:1px solid rgba(79,227,193,0.15);">
          <div style="font-family:monospace;font-size:11px;color:#4FE3C1;margin-bottom:4px;">EXAMPLE</div>
          <div style="font-size:13px;color:#F5F5F7;">"312 people entered today. 187 made a purchase. Your conversion rate is 60% — up from 52% last month."</div>
        </div>
      </div>
      <div class="card-cyan flex-1" style="padding:36px;">
        <div style="font-size:32px;margin-bottom:8px;">⏱️</div>
        <div style="font-size:17px;font-weight:600;color:#4FE3C1;margin-bottom:12px;">Queue & Wait Time</div>
        <div style="font-size:14px;color:#A1A1A8;line-height:1.7;">
          Real-time line length monitoring. Get alerts when wait time exceeds your target. Reduce walkways automatically.
        </div>
        <div style="margin-top:16px;padding:12px;background:rgba(79,227,193,0.08);border-radius:6px;border:1px solid rgba(79,227,193,0.15);">
          <div style="font-family:monospace;font-size:11px;color:#4FE3C1;margin-bottom:4px;">EXAMPLE</div>
          <div style="font-size:13px;color:#F5F5F7;">"⚠️ 12:15pm — line hit 8 people, avg wait 6.5 min. You lost an estimated 4 customers who walked out."</div>
        </div>
      </div>
      <div class="card-cyan flex-1" style="padding:36px;">
        <div style="font-size:32px;margin-bottom:8px;">🗺️</div>
        <div style="font-size:17px;font-weight:600;color:#4FE3C1;margin-bottom:12px;">Dwell & Heatmaps</div>
        <div style="font-size:14px;color:#A1A1A8;line-height:1.7;">
          See where people linger, which displays they stop at, and how long they stay before buying — or leaving.
        </div>
        <div style="margin-top:16px;padding:12px;background:rgba(79,227,193,0.08);border-radius:6px;border:1px solid rgba(79,227,193,0.15);">
          <div style="font-family:monospace;font-size:11px;color:#4FE3C1;margin-bottom:4px;">EXAMPLE</div>
          <div style="font-size:13px;color:#F5F5F7;">"Customers spend 3.2 min at the pastry case but only 8% buy. Try a tasting sample or price drop test."</div>
        </div>
      </div>
    </div>
  `, pad(5)))

  // ═══════════════════════════════════════════════════════════════
  // Slide 6: FUSION DATA — POS + Camera Combined Intelligence
  // ═══════════════════════════════════════════════════════════════
  slides.push(slideWrapper(6, `
    <div class="mb-16"><span class="eyebrow">FUSION INTELLIGENCE</span></div>
    <div class="title" style="font-size:72px;">POS + Camera = Superpowers</div>
    <div class="mt-12"><div class="accent-bar"></div></div>
    <p style="font-size:18px;color:#A1A1A8;margin-top:16px;max-width:900px;">When we combine what your register knows with what the camera sees, you get insights no one else in your market has.</p>

    <div style="margin-top:36px;">
      <!-- Fusion Example 1 -->
      <div class="fusion-row">
        <div class="fusion-signal">
          <div class="signal-label">📡 CAMERA</div>
          <div class="signal-data">Foot traffic up 23% on Saturday</div>
        </div>
        <div class="fusion-plus">+</div>
        <div class="fusion-signal">
          <div class="signal-label">💳 POS</div>
          <div class="signal-data">Revenue flat — same as last Saturday</div>
        </div>
        <div class="fusion-equals">=</div>
        <div class="fusion-insight">
          <div class="insight-label">🧠 MERIDIAN INSIGHT</div>
          <div class="insight-data">Conversion rate dropped from 58% to 44%</div>
          <div class="insight-action">→ "Your traffic is growing but staff isn't converting. Add a greeter or upsell training."</div>
        </div>
      </div>

      <!-- Fusion Example 2 -->
      <div class="fusion-row">
        <div class="fusion-signal">
          <div class="signal-label">📡 CAMERA</div>
          <div class="signal-data">14 people in line at 12:10pm, avg wait 7 min</div>
        </div>
        <div class="fusion-plus">+</div>
        <div class="fusion-signal">
          <div class="signal-label">💳 POS</div>
          <div class="signal-data">Only 6 transactions in that window</div>
        </div>
        <div class="fusion-equals">=</div>
        <div class="fusion-insight">
          <div class="insight-label">🧠 MERIDIAN INSIGHT</div>
          <div class="insight-data">$340 estimated lost revenue from walkouts</div>
          <div class="insight-action">→ "Open register 2 from 11:45am–1:15pm. Projected to recover $2,380/week."</div>
        </div>
      </div>

      <!-- Fusion Example 3 -->
      <div class="fusion-row">
        <div class="fusion-signal">
          <div class="signal-label">📡 CAMERA</div>
          <div class="signal-data">Peak foot traffic at 2–3pm daily</div>
        </div>
        <div class="fusion-plus">+</div>
        <div class="fusion-signal">
          <div class="signal-label">💳 POS</div>
          <div class="signal-data">Avg ticket $8.20 (vs $14.50 at lunch)</div>
        </div>
        <div class="fusion-equals">=</div>
        <div class="fusion-insight">
          <div class="insight-label">🧠 MERIDIAN INSIGHT</div>
          <div class="insight-data">Afternoon crowd is coffee/snack only</div>
          <div class="insight-action">→ "Launch a 2–4pm combo deal. Similar businesses saw 35% afternoon ticket increase."</div>
        </div>
      </div>

      <!-- Fusion Example 4 -->
      <div class="fusion-row">
        <div class="fusion-signal">
          <div class="signal-label">📡 CAMERA</div>
          <div class="signal-data">40% of visitors linger at display case 3+ min</div>
        </div>
        <div class="fusion-plus">+</div>
        <div class="fusion-signal">
          <div class="signal-label">💳 POS</div>
          <div class="signal-data">Display case items: 5% attach rate</div>
        </div>
        <div class="fusion-equals">=</div>
        <div class="fusion-insight">
          <div class="insight-label">🧠 MERIDIAN INSIGHT</div>
          <div class="insight-data">High interest, low conversion — price or access barrier</div>
          <div class="insight-action">→ "Try sample trays or a 'Pick 2 for $6' deal. Interest is already there."</div>
        </div>
      </div>
    </div>
  `, pad(6)))

  // ═══════════════════════════════════════════════════════════════
  // Slide 7: More Fusion Examples + Revenue Per Visitor
  // ═══════════════════════════════════════════════════════════════
  slides.push(slideWrapper(7, `
    <div class="mb-16"><span class="eyebrow-cyan">FUSION INTELLIGENCE · CONTINUED</span></div>
    <div class="title" style="font-size:72px;">Every Data Point Tells a Story</div>
    <div class="mt-12"><div class="accent-bar"></div></div>

    <div style="margin-top:36px;">
      <!-- Fusion Example 5 -->
      <div class="fusion-row">
        <div class="fusion-signal">
          <div class="signal-label">📡 CAMERA</div>
          <div class="signal-data">Groups of 3+ make up 60% of evening traffic</div>
        </div>
        <div class="fusion-plus">+</div>
        <div class="fusion-signal">
          <div class="signal-label">💳 POS</div>
          <div class="signal-data">Avg group order: $42 (single: $16)</div>
        </div>
        <div class="fusion-equals">=</div>
        <div class="fusion-insight">
          <div class="insight-label">🧠 MERIDIAN INSIGHT</div>
          <div class="insight-data">Group dining drives 78% of evening revenue</div>
          <div class="insight-action">→ "Push family platters and shareable items. Add a 'group deal' to the evening menu."</div>
        </div>
      </div>

      <!-- Fusion Example 6 -->
      <div class="fusion-row">
        <div class="fusion-signal">
          <div class="signal-label">📡 CAMERA</div>
          <div class="signal-data">Rain days: 40% less foot traffic</div>
        </div>
        <div class="fusion-plus">+</div>
        <div class="fusion-signal">
          <div class="signal-label">💳 POS</div>
          <div class="signal-data">But avg ticket jumps to $19.80 (normal: $13.50)</div>
        </div>
        <div class="fusion-equals">=</div>
        <div class="fusion-insight">
          <div class="insight-label">🧠 MERIDIAN INSIGHT</div>
          <div class="insight-data">Rain customers are high-intent. They spend 47% more.</div>
          <div class="insight-action">→ "Run a rainy-day promo to attract more of them. Every extra rain visitor = ~$20."</div>
        </div>
      </div>

      <!-- Fusion Example 7 -->
      <div class="fusion-row">
        <div class="fusion-signal">
          <div class="signal-label">📡 CAMERA</div>
          <div class="signal-data">Staff member A: 45 sec avg greeting time</div>
        </div>
        <div class="fusion-plus">+</div>
        <div class="fusion-signal">
          <div class="signal-label">💳 POS</div>
          <div class="signal-data">Staff A avg ticket: $22 vs team avg $15</div>
        </div>
        <div class="fusion-equals">=</div>
        <div class="fusion-insight">
          <div class="insight-label">🧠 MERIDIAN INSIGHT</div>
          <div class="insight-data">Faster greeting = 47% higher ticket value</div>
          <div class="insight-action">→ "Train all staff on A's greeting flow. Projected +$1,200/week revenue impact."</div>
        </div>
      </div>
    </div>

    <!-- Key Metric Callout -->
    <div style="margin-top:32px;display:flex;gap:24px;">
      <div class="card-glow" style="flex:1;padding:28px;text-align:center;">
        <div style="font-family:monospace;font-size:11px;color:#7C5CFF;letter-spacing:0.12em;margin-bottom:8px;">YOUR NEW KEY METRIC</div>
        <div style="font-family:monospace;font-size:48px;font-weight:700;color:#FFFFFF;">Revenue Per Visitor</div>
        <div style="font-size:16px;color:#A1A1A8;margin-top:12px;">Only possible when POS data meets camera data. This is the number that separates thriving businesses from guessing ones.</div>
      </div>
    </div>
  `, pad(7)))

  // ═══════════════════════════════════════════════════════════════
  // Slide 8: Pricing
  // ═══════════════════════════════════════════════════════════════
  const setupFeeHtml = setupFee > 0 ? `
    <div style="display:flex;justify-content:space-between;padding:16px 0;border-bottom:1px solid rgba(255,255,255,0.08);">
      <span class="muted" style="font-size:18px;">One-Time Setup Fee</span>
      <span class="white bold" style="font-size:22px;">$${setupFee.toLocaleString()}</span>
    </div>
  ` : ''
  const firstMonthHtml = firstMonthFree ? `
    <div style="display:flex;justify-content:space-between;padding:16px 0;border-bottom:1px solid rgba(255,255,255,0.08);">
      <span class="muted" style="font-size:18px;">First Month</span>
      <span class="cyan bold" style="font-size:22px;">FREE</span>
    </div>
  ` : ''
  const dueToday = (firstMonthFree ? 0 : price) + setupFee

  slides.push(slideWrapper(8, `
    <div class="mb-16"><span class="eyebrow">YOUR INVESTMENT</span></div>
    <div class="title">Simple, Transparent Pricing</div>
    <div class="mt-12"><div class="accent-bar"></div></div>
    <div class="flex gap-32 mt-48">
      <div class="card-glow flex-1" style="padding:48px;">
        <div style="font-family:monospace;font-size:14px;color:#7C5CFF;margin-bottom:24px;letter-spacing:0.1em;">MERIDIAN ${plan.label.toUpperCase()}</div>
        <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:32px;">
          <span class="price-big">$${price.toLocaleString()}</span>
          <span class="price-tag">/month</span>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.08);padding-top:20px;">
          ${featureHtml}
        </div>
      </div>
      <div class="card flex-1" style="padding:48px;">
        <div style="font-family:monospace;font-size:14px;color:#4FE3C1;margin-bottom:24px;letter-spacing:0.1em;">ORDER SUMMARY</div>
        <div style="display:flex;justify-content:space-between;padding:16px 0;border-bottom:1px solid rgba(255,255,255,0.08);">
          <span class="muted" style="font-size:18px;">${plan.label} Plan (monthly)</span>
          <span class="white bold" style="font-size:22px;">$${price.toLocaleString()}/mo</span>
        </div>
        ${setupFeeHtml}
        ${firstMonthHtml}
        <div style="display:flex;justify-content:space-between;padding:24px 0;margin-top:8px;">
          <span class="white bold" style="font-size:22px;">Due Today</span>
          <span style="font-family:monospace;font-size:36px;font-weight:700;color:#4FE3C1;">$${dueToday.toLocaleString()}</span>
        </div>
        ${firstMonthFree ? '<div style="font-size:14px;color:#7C5CFF;margin-top:8px;">🎉 Your first month is on us. Billing starts month 2.</div>' : ''}
        ${checkoutUrl ? `
          <div style="margin-top:24px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.08);text-align:center;">
            <div style="font-family:monospace;font-size:11px;color:#6B6B73;letter-spacing:0.12em;margin-bottom:12px;">SCAN TO PAY</div>
            <div class="qr-container"><img id="proposal-qr" src="" alt="Checkout QR" style="width:160px;height:160px;border-radius:8px;padding:6px;background:white;" /></div>
          </div>
        ` : ''}
      </div>
    </div>
  `, pad(8)))

  // ═══════════════════════════════════════════════════════════════
  // Slide 9: CTA
  // ═══════════════════════════════════════════════════════════════
  const qrSection = checkoutUrl
    ? `<div class="mt-32 text-center">
        <p style="font-size:16px;color:#A1A1A8;margin-bottom:16px;">Scan to get started instantly:</p>
        <div class="qr-container"><img id="proposal-qr-cta" src="" alt="Checkout QR" style="width:200px;height:200px;border-radius:12px;border:2px solid rgba(124,92,255,0.3);padding:8px;background:white;" /></div>
        <p style="font-size:13px;color:#6B6B73;margin-top:12px;">${checkoutUrl}</p>
      </div>`
    : `<div class="mt-32 text-center">
        <div class="btn-violet">GET STARTED</div>
      </div>`

  slides.push(slideWrapper(9, `
    <div style="display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;height:100%;">
      <div class="mb-24"><span class="eyebrow">READY TO GROW YOUR BUSINESS?</span></div>
      <div class="title-hero">Let's Go,</div>
      <div class="title-hero" style="color:#7C5CFF;margin-top:-10px;">${ownerName.split(' ')[0]}</div>
      <div class="mt-32" style="max-width:700px;">
        <p class="subtitle" style="font-size:24px;">Connect your POS in 5 minutes. See your first insights today. No risk${firstMonthFree ? ' — first month free' : ''}.</p>
      </div>
      ${qrSection}
      <div style="margin-top:48px;display:flex;gap:48px;">
        <div style="text-align:center;">
          <div style="font-family:monospace;font-size:11px;color:#6B6B73;letter-spacing:0.12em;margin-bottom:6px;">YOUR REP</div>
          <div style="font-size:18px;color:#A1A1A8;">${rep.name}</div>
        </div>
        <div style="text-align:center;">
          <div style="font-family:monospace;font-size:11px;color:#6B6B73;letter-spacing:0.12em;margin-bottom:6px;">EMAIL</div>
          <div style="font-size:18px;color:#A1A1A8;">${rep.email}</div>
        </div>
        ${rep.phone ? `<div style="text-align:center;">
          <div style="font-family:monospace;font-size:11px;color:#6B6B73;letter-spacing:0.12em;margin-bottom:6px;">PHONE</div>
          <div style="font-size:18px;color:#A1A1A8;">${rep.phone}</div>
        </div>` : ''}
        <div style="text-align:center;">
          <div style="font-family:monospace;font-size:11px;color:#6B6B73;letter-spacing:0.12em;margin-bottom:6px;">PLATFORM</div>
          <div style="font-size:18px;color:#A1A1A8;">meridian.tips</div>
        </div>
      </div>
    </div>
  `, pad(9)))

  return slides
}


/* ------------------------------------------------------------------ */
/*  PDF assembly                                                       */
/* ------------------------------------------------------------------ */

export async function generateProposalPdf(input: ProposalInput): Promise<Blob> {
  const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
    import('jspdf'),
    import('html2canvas'),
  ])

  const slides = buildSlides(input)

  // Create hidden container
  const container = document.createElement('div')
  container.style.cssText = 'position:fixed;top:-9999px;left:-9999px;width:1920px;z-index:-1;'
  document.body.appendChild(container)

  const pdf = new jsPDF({ orientation: 'landscape', unit: 'px', format: [1920, 1080] })

  try {
    for (let i = 0; i < slides.length; i++) {
      container.innerHTML = `<style>${SLIDE_CSS}</style>${slides[i]}`
      const slideEl = container.querySelector('.slide') as HTMLElement
      if (!slideEl) continue

      // eslint-disable-next-line no-await-in-loop
      const canvas = await html2canvas(slideEl, {
        width: 1920,
        height: 1080,
        scale: 1,
        useCORS: true,
        backgroundColor: '#0A0A0B',
      })

      if (i > 0) pdf.addPage([1920, 1080], 'landscape')
      pdf.addImage(canvas.toDataURL('image/jpeg', 0.92), 'JPEG', 0, 0, 1920, 1080)
    }
  } finally {
    document.body.removeChild(container)
  }

  return pdf.output('blob')
}

/**
 * Trigger a browser download of the proposal PDF.
 */
export async function downloadProposalPdf(input: ProposalInput): Promise<void> {
  const blob = await generateProposalPdf(input)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Meridian_Proposal_${input.businessName.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
