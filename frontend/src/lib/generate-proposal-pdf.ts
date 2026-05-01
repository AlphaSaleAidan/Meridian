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
  // Generate deterministic pseudo-random values
  const r = (i: number) => {
    const x = Math.sin(s + i * 9.1) * 43758.5453
    return x - Math.floor(x)
  }

  const cracks: string[] = []
  const numCracks = 3 + Math.floor(r(0) * 3) // 3-5 cracks
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
  .card { background: rgba(14,14,16,0.88); border: 1px solid rgba(255,255,255,0.08); padding: 44px; }
  .card-glow { background: linear-gradient(180deg, rgba(124,92,255,0.12) 0%, rgba(14,14,16,0.88) 60%); border: 1px solid rgba(124,92,255,0.25); padding: 44px; }
  .violet { color: #7C5CFF; }
  .cyan { color: #4FE3C1; }
  .white { color: #FFFFFF; }
  .muted { color: #A1A1A8; }
  .dim { color: #6B6B73; }
  .mono { font-family: monospace; }
  .bold { font-weight: 600; }
  .flex { display: flex; }
  .gap-24 { gap: 24px; }
  .gap-32 { gap: 32px; }
  .flex-1 { flex: 1; }
  .text-center { text-align: center; }
  .mt-12 { margin-top: 12px; }
  .mt-16 { margin-top: 16px; }
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
  .btn-violet { display: inline-block; padding: 16px 48px; background: #7C5CFF; color: white; font-weight: 600; font-size: 18px; }
  .qr-container { margin-top: 32px; display: flex; justify-content: center; }
  .qr-container canvas, .qr-container img { width: 200px; height: 200px; }
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

  // Slide 1: Title
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
  `, '01 / 07'))

  // Slide 2: The Problem
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
  `, '02 / 07'))

  // Slide 3: What You Get
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
  `, '03 / 07'))

  // Slide 4: POS + Camera Intelligence
  slides.push(slideWrapper(4, `
    <div class="mb-16"><span class="eyebrow">DUAL INTELLIGENCE</span></div>
    <div class="title">POS Data + Camera Vision</div>
    <div class="mt-12"><div class="accent-bar"></div></div>
    <div class="flex gap-32 mt-40">
      <div class="card-glow flex-1" style="padding:40px;">
        <div style="font-size:15px;font-weight:600;color:#7C5CFF;margin-bottom:20px;letter-spacing:0.08em;">⚡ POS ANALYTICS ENGINE</div>
        <div style="font-size:17px;color:#A1A1A8;line-height:2.0;">
          ✓ Revenue tracking & trend analysis<br>
          ✓ Menu engineering (Stars, Dogs, Puzzles)<br>
          ✓ Predictive demand forecasting<br>
          ✓ Anomaly detection & email alerts<br>
          ✓ Inventory optimization
        </div>
      </div>
      <div class="card flex-1" style="padding:40px;border-color:rgba(79,227,193,0.15);background:linear-gradient(180deg,rgba(79,227,193,0.08) 0%,rgba(14,14,16,0.88) 60%);">
        <div style="font-size:15px;font-weight:600;color:#4FE3C1;margin-bottom:20px;letter-spacing:0.08em;">📡 CAMERA INTELLIGENCE</div>
        <div style="font-size:17px;color:#A1A1A8;line-height:2.0;">
          ✓ AI foot traffic counting<br>
          ✓ Dwell time analysis<br>
          ✓ Queue monitoring & alerts<br>
          ✓ Anonymous demographic insights<br>
          ✓ Conversion rate (traffic ÷ purchases)
        </div>
      </div>
    </div>
    <div class="mt-40">
      <div class="card" style="padding:28px;text-align:center;">
        <p style="font-size:20px;color:#A1A1A8;">When combined: know your <strong style="color:#FFFFFF;">conversion rate</strong>, <strong style="color:#FFFFFF;">revenue per visitor</strong>, and <strong style="color:#FFFFFF;">optimal staffing</strong> — all automated.</p>
      </div>
    </div>
  `, '04 / 07'))

  // Slide 5: ROI
  slides.push(slideWrapper(5, `
    <div class="mb-16"><span class="eyebrow-cyan">RETURN ON INVESTMENT</span></div>
    <div class="title">Why ${businessName} Needs This</div>
    <div class="mt-12"><div class="accent-bar"></div></div>
    <div class="flex gap-32 mt-48">
      <div class="card flex-1" style="text-align:center;padding:48px;">
        <div style="font-family:monospace;font-size:72px;font-weight:600;color:#7C5CFF;">15%</div>
        <div style="font-family:monospace;font-size:12px;font-weight:500;letter-spacing:0.14em;text-transform:uppercase;color:#A1A1A8;margin-top:14px;">avg revenue increase in 90 days</div>
      </div>
      <div class="card flex-1" style="text-align:center;padding:48px;">
        <div style="font-family:monospace;font-size:72px;font-weight:600;color:#4FE3C1;">30%</div>
        <div style="font-family:monospace;font-size:12px;font-weight:500;letter-spacing:0.14em;text-transform:uppercase;color:#A1A1A8;margin-top:14px;">reduction in waste</div>
      </div>
      <div class="card flex-1" style="text-align:center;padding:48px;">
        <div style="font-family:monospace;font-size:72px;font-weight:600;color:#9B7FFF;">10x</div>
        <div style="font-family:monospace;font-size:12px;font-weight:500;letter-spacing:0.14em;text-transform:uppercase;color:#A1A1A8;margin-top:14px;">ROI within 6 months</div>
      </div>
    </div>
    <div class="mt-40">
      <div class="card-glow" style="padding:28px;">
        <p style="font-size:20px;color:#A1A1A8;text-align:center;">At <strong style="color:#FFFFFF;">$${price}/mo</strong>, Meridian pays for itself if it helps you make just <strong style="color:#4FE3C1;">${Math.ceil(price / 30)} more sales per month</strong>.</p>
      </div>
    </div>
  `, '05 / 07'))

  // Slide 6: Pricing
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

  slides.push(slideWrapper(6, `
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
      </div>
    </div>
  `, '06 / 07'))

  // Slide 7: CTA + QR Code
  const qrSection = checkoutUrl
    ? `<div class="mt-32 text-center">
        <p style="font-size:16px;color:#A1A1A8;margin-bottom:16px;">Scan to get started instantly:</p>
        <div class="qr-container"><img id="proposal-qr" src="" alt="Checkout QR" style="width:200px;height:200px;border-radius:12px;border:2px solid rgba(124,92,255,0.3);padding:8px;background:white;" /></div>
        <p style="font-size:13px;color:#6B6B73;margin-top:12px;">${checkoutUrl}</p>
      </div>`
    : `<div class="mt-32 text-center">
        <div class="btn-violet">GET STARTED</div>
      </div>`

  slides.push(slideWrapper(7, `
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
  `, '07 / 07'))

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
