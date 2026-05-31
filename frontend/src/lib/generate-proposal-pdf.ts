/**
 * Proposal generator — opens a polished HTML presentation in a new browser tab.
 * No jsPDF/html2canvas needed. Crisp vector text, instant load, print-ready.
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

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function buildProposalHtml(input: ProposalInput): string {
  const { businessName, ownerName, plan, customPrice, setupFee, firstMonthFree, rep, checkoutUrl } = input
  const price = customPrice || plan.price
  const dueToday = (firstMonthFree ? 0 : price) + setupFee
  const firstName = ownerName.split(' ')[0]
  const date = new Date().toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' })
  const features = plan.features.map((f: string) => `<li>${esc(f)}</li>`).join('')

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Meridian Proposal — ${esc(businessName)}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#08080A;--surface:#0E0E12;--border:rgba(255,255,255,0.07);
  --violet:#7C5CFF;--cyan:#4FE3C1;--white:#F5F5F7;--muted:#A1A1A8;--dim:#6B6B73;
}
html{scroll-behavior:smooth;scroll-snap-type:y mandatory}
body{background:var(--bg);color:var(--white);font-family:'Inter',system-ui,sans-serif;-webkit-font-smoothing:antialiased;overflow-x:hidden}

/* Slide system */
.slide{min-height:100vh;scroll-snap-align:start;position:relative;overflow:hidden;display:flex;align-items:center;padding:80px clamp(40px,8vw,120px)}
.slide-inner{width:100%;max-width:1400px;margin:0 auto;position:relative;z-index:2}

/* Backgrounds */
.slide::before{content:'';position:absolute;inset:0;z-index:0}
.bg-radial::before{background:radial-gradient(ellipse 80% 60% at 20% 40%,rgba(124,92,255,0.08),transparent 70%),radial-gradient(ellipse 60% 50% at 80% 70%,rgba(79,227,193,0.05),transparent 60%),var(--bg)}
.bg-cyan::before{background:radial-gradient(ellipse 70% 60% at 70% 40%,rgba(79,227,193,0.08),transparent 70%),var(--bg)}
.bg-violet::before{background:radial-gradient(ellipse 70% 60% at 30% 50%,rgba(124,92,255,0.10),transparent 70%),var(--bg)}
.bg-center::before{background:radial-gradient(ellipse 60% 50% at 50% 50%,rgba(124,92,255,0.07),transparent 60%),var(--bg)}

/* Lines decoration */
.slide::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:var(--border);z-index:1}

/* Typography */
.eyebrow{font-family:'Inter',monospace;font-size:12px;font-weight:600;letter-spacing:0.2em;text-transform:uppercase;color:var(--violet)}
.eyebrow-cyan{font-family:'Inter',monospace;font-size:12px;font-weight:600;letter-spacing:0.2em;text-transform:uppercase;color:var(--cyan)}
.hero-title{font-family:'DM Serif Display',Georgia,serif;font-style:italic;font-size:clamp(48px,7vw,96px);line-height:1.05;color:var(--white)}
.section-title{font-family:'DM Serif Display',Georgia,serif;font-style:italic;font-size:clamp(36px,5vw,72px);line-height:1.1;color:var(--white)}
.subtitle{font-size:clamp(16px,1.8vw,24px);font-weight:300;line-height:1.6;color:var(--muted);max-width:700px}
.accent-bar{width:64px;height:3px;background:linear-gradient(135deg,var(--violet),var(--cyan));border-radius:2px;margin:20px 0 0}

/* Cards */
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:36px}
.card-glow{background:linear-gradient(180deg,rgba(124,92,255,0.08) 0%,var(--surface) 60%);border:1px solid rgba(124,92,255,0.18);border-radius:12px;padding:36px}
.card-cyan{background:linear-gradient(180deg,rgba(79,227,193,0.06) 0%,var(--surface) 60%);border:1px solid rgba(79,227,193,0.15);border-radius:12px;padding:36px}

/* Grid */
.grid-3{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;margin-top:48px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:32px;margin-top:48px}
@media(max-width:768px){.grid-2,.grid-3{grid-template-columns:1fr}}

/* Feature checks */
.checks{list-style:none;padding:0}
.checks li{font-size:15px;color:var(--muted);line-height:2;padding-left:28px;position:relative}
.checks li::before{content:'\\2713';position:absolute;left:0;color:var(--cyan);font-weight:700}

/* Insight boxes */
.insight-box{margin-top:16px;padding:14px 16px;border-radius:8px;border:1px solid}
.insight-box.violet{background:rgba(124,92,255,0.06);border-color:rgba(124,92,255,0.15)}
.insight-box.cyan{background:rgba(79,227,193,0.06);border-color:rgba(79,227,193,0.15)}
.insight-label{font-family:'Inter',monospace;font-size:10px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;margin-bottom:6px}
.insight-text{font-size:14px;color:var(--white);line-height:1.5}

/* Fusion rows */
.fusion{display:flex;align-items:stretch;gap:12px;margin-bottom:16px}
.fusion-sig{flex:1;padding:16px 20px;border-radius:8px;background:var(--surface);border:1px solid var(--border)}
.fusion-op{display:flex;align-items:center;font-size:24px;font-weight:700;color:var(--violet);padding:0 6px;flex-shrink:0}
.fusion-op.eq{color:var(--cyan)}
.fusion-out{flex:1.4;padding:16px 20px;border-radius:8px;background:linear-gradient(135deg,rgba(124,92,255,0.08),rgba(79,227,193,0.05));border:1px solid rgba(124,92,255,0.15)}
.sig-label{font-size:10px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:var(--dim);margin-bottom:4px}
.sig-data{font-size:14px;color:var(--white);font-weight:500;line-height:1.4}
.out-label{font-size:10px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:var(--cyan);margin-bottom:4px}
.out-action{font-size:12px;color:var(--muted);margin-top:4px}
@media(max-width:900px){.fusion{flex-direction:column}.fusion-op{padding:4px 0;justify-content:center}}

/* Stats */
.stat-big{font-family:'Inter',monospace;font-size:clamp(48px,6vw,72px);font-weight:700}
.stat-label{font-family:'Inter',monospace;font-size:11px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:var(--muted);margin-top:12px}

/* Price */
.price-hero{font-family:'Inter',monospace;font-size:56px;font-weight:700;color:var(--white)}
.price-per{font-size:18px;color:var(--dim);margin-left:4px}
.summary-row{display:flex;justify-content:space-between;padding:16px 0;border-bottom:1px solid var(--border);font-size:16px}
.summary-row .label{color:var(--muted)}
.summary-row .value{color:var(--white);font-weight:600}
.summary-total{display:flex;justify-content:space-between;padding:24px 0;font-size:20px}
.summary-total .value{font-family:'Inter',monospace;font-size:36px;font-weight:700;color:var(--cyan)}

/* CTA */
.btn-primary{display:inline-flex;align-items:center;gap:8px;padding:16px 48px;background:var(--violet);color:white;font-weight:600;font-size:18px;border-radius:10px;text-decoration:none;transition:transform 0.2s}
.btn-primary:hover{transform:translateY(-2px)}

/* Navigation dots */
.nav-dots{position:fixed;right:24px;top:50%;transform:translateY(-50%);z-index:100;display:flex;flex-direction:column;gap:12px}
.nav-dot{width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,0.15);transition:all 0.3s;cursor:pointer;border:none;padding:0}
.nav-dot.active{background:var(--violet);box-shadow:0 0 12px rgba(124,92,255,0.4)}

/* Print bar */
.print-bar{position:fixed;top:0;left:0;right:0;z-index:200;background:rgba(8,8,10,0.95);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:12px 32px;display:flex;align-items:center;justify-content:space-between}
.print-bar .logo{font-family:'DM Serif Display',Georgia,serif;font-style:italic;font-size:20px;color:var(--white)}
.print-btn{padding:8px 24px;background:var(--violet);color:white;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;font-family:'Inter',sans-serif}
.print-btn:hover{opacity:0.9}

/* Slide counter */
.page-num{position:absolute;bottom:32px;right:clamp(40px,8vw,120px);font-family:'Inter',monospace;font-size:11px;color:var(--dim);letter-spacing:0.1em;z-index:2}

/* Animations */
@keyframes fadeUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}
.slide-inner>*{animation:fadeUp 0.6s ease-out both}
.slide-inner>:nth-child(2){animation-delay:0.1s}
.slide-inner>:nth-child(3){animation-delay:0.2s}
.slide-inner>:nth-child(4){animation-delay:0.3s}

/* Print styles */
@media print{
  .print-bar,.nav-dots{display:none!important}
  html{scroll-snap-type:none}
  .slide{min-height:auto;page-break-after:always;break-after:page;padding:60px 80px}
  .slide::before,.slide::after{display:none}
  body{background:white;color:#111}
  .card,.card-glow,.card-cyan{border:1px solid #ddd;background:#f9f9f9}
  .hero-title,.section-title{color:#111}
  .subtitle,.checks li,.sig-data,.insight-text{color:#333}
}
</style>
</head>
<body>

<!-- Print / Share Bar -->
<div class="print-bar">
  <div class="logo">Meridian</div>
  <div style="display:flex;gap:12px;align-items:center">
    <span style="font-size:12px;color:var(--muted)">Proposal for ${esc(businessName)}</span>
    <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
  </div>
</div>

<!-- Navigation Dots -->
<div class="nav-dots" id="dots"></div>

<!-- ═══════ SLIDE 1: Title ═══════ -->
<section class="slide bg-radial" id="s1" style="padding-top:120px">
  <div class="slide-inner" style="display:flex;flex-direction:column;justify-content:center;min-height:70vh">
    <div class="eyebrow" style="margin-bottom:32px">Meridian Intelligence &middot; Proposal &middot; ${date}</div>
    <div class="hero-title">Prepared for</div>
    <div class="hero-title" style="color:var(--violet)">${esc(businessName)}</div>
    <div class="accent-bar"></div>
    <p class="subtitle" style="margin-top:32px">
      AI-powered analytics that turns your POS data, camera feeds, and weather patterns into revenue growth. Insights no spreadsheet can give you.
    </p>
    <div style="margin-top:64px;font-size:14px;color:var(--dim)">
      Prepared by ${esc(rep.name)} &middot; ${esc(rep.email)}${rep.phone ? ' &middot; ' + esc(rep.phone) : ''}
    </div>
  </div>
  <div class="page-num">01 / 09</div>
</section>

<!-- ═══════ SLIDE 2: The Problem ═══════ -->
<section class="slide bg-violet" id="s2">
  <div class="slide-inner">
    <div class="eyebrow">The Opportunity</div>
    <div class="section-title" style="margin-top:16px;max-width:900px">What you're leaving on the table without analytics</div>
    <div class="accent-bar"></div>
    <div class="grid-3">
      <div class="card" style="text-align:center">
        <div class="stat-big" style="color:var(--violet)">62%</div>
        <div class="stat-label">of restaurants fail in year 1</div>
        <p style="font-size:14px;color:var(--muted);margin-top:16px">Most never see the data patterns that could have saved them.</p>
      </div>
      <div class="card" style="text-align:center">
        <div class="stat-big" style="color:var(--cyan)">$840</div>
        <div class="stat-label">avg monthly revenue left on table</div>
        <p style="font-size:14px;color:var(--muted);margin-top:16px">From mispriced items, missed peak hours, and unoptimized menus.</p>
      </div>
      <div class="card" style="text-align:center">
        <div class="stat-big" style="color:var(--white)">5 min</div>
        <div class="stat-label">to connect &amp; start seeing insights</div>
        <p style="font-size:14px;color:var(--muted);margin-top:16px">Plug in your POS. Meridian does the rest — no hardware, no training.</p>
      </div>
    </div>
  </div>
  <div class="page-num">02 / 09</div>
</section>

<!-- ═══════ SLIDE 3: What Meridian Does ═══════ -->
<section class="slide bg-cyan" id="s3">
  <div class="slide-inner">
    <div class="eyebrow-cyan">What Meridian Does</div>
    <div class="section-title" style="margin-top:16px">Seven AI agents working 24/7 for your business</div>
    <div class="accent-bar"></div>
    <div class="grid-3" style="margin-top:40px">
      <div class="card">
        <div style="font-size:28px;margin-bottom:12px">📊</div>
        <div style="font-size:16px;font-weight:600;color:var(--violet);margin-bottom:8px">Revenue Intelligence</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.7">Track hourly, daily, weekly trends. AI alerts when revenue dips below your normal pattern. Spot slow days before they drain cash.</p>
        <div class="insight-box violet">
          <div class="insight-label" style="color:var(--violet)">Example Alert</div>
          <div class="insight-text">"Tuesday lunch dropped 18% vs 4-week avg. Your chicken combo was 86'd at 11:30am."</div>
        </div>
      </div>
      <div class="card">
        <div style="font-size:28px;margin-bottom:12px">🍽️</div>
        <div style="font-size:16px;font-weight:600;color:var(--cyan);margin-bottom:8px">Menu Engineering</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.7">Every item classified as Star, Plow Horse, Puzzle, or Dog. Know exactly what to push, what to reprice, and what to cut.</p>
        <div class="insight-box cyan">
          <div class="insight-label" style="color:var(--cyan)">Example Insight</div>
          <div class="insight-text">"Your aca&iacute; bowl has 62% margin but only 3% of orders. Move it to menu position #2 for a projected 40% lift."</div>
        </div>
      </div>
      <div class="card">
        <div style="font-size:28px;margin-bottom:12px">🔮</div>
        <div style="font-size:16px;font-weight:600;color:#9B7FFF;margin-bottom:8px">Predictive Forecasting</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.7">AI predicts tomorrow's sales with 90%+ accuracy. Auto-suggested prep lists and staffing recommendations. Never over-order again.</p>
        <div class="insight-box violet">
          <div class="insight-label" style="color:#9B7FFF">Example Forecast</div>
          <div class="insight-text">"Friday predicted: $4,280 (+12% vs last week). Add 2 extra staff for 11am&ndash;2pm rush."</div>
        </div>
      </div>
      <div class="card">
        <div style="font-size:28px;margin-bottom:12px">💰</div>
        <div style="font-size:16px;font-weight:600;color:var(--cyan);margin-bottom:8px">Pricing Optimizer</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.7">Data-backed pricing suggestions based on elasticity, competition, and margin analysis. Find hidden revenue in every menu item.</p>
        <div class="insight-box cyan">
          <div class="insight-label" style="color:var(--cyan)">Example</div>
          <div class="insight-text">"Raise flat white from $5.25 to $5.75 (+9.5%). Demand is inelastic — projected $0 lost orders, +$310/mo."</div>
        </div>
      </div>
      <div class="card">
        <div style="font-size:28px;margin-bottom:12px">⚡</div>
        <div style="font-size:16px;font-weight:600;color:var(--violet);margin-bottom:8px">Anomaly Detector</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.7">Catches unusual patterns in real-time: unexpected drops, refund spikes, discount abuse. Alerts you before small problems become big losses.</p>
        <div class="insight-box violet">
          <div class="insight-label" style="color:var(--violet)">Example Alert</div>
          <div class="insight-text">"Refund rate spiked to 8.2% today (normal: 1.4%). 6 of 9 refunds were on the new seasonal item."</div>
        </div>
      </div>
      <div class="card">
        <div style="font-size:28px;margin-bottom:12px">🌤️</div>
        <div style="font-size:16px;font-weight:600;color:var(--cyan);margin-bottom:8px">Weather Intelligence</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.7">Cross-references weather forecasts with your historical sales. Adjusts prep, staffing, and promo recommendations automatically.</p>
        <div class="insight-box cyan">
          <div class="insight-label" style="color:var(--cyan)">Example</div>
          <div class="insight-text">"Rain forecast Thursday. Your revenue drops 22% on rain days. Reduce perishable prep 20%, push delivery promos."</div>
        </div>
      </div>
    </div>
  </div>
  <div class="page-num">03 / 09</div>
</section>

<!-- ═══════ SLIDE 4: Camera Intelligence ═══════ -->
<section class="slide bg-cyan" id="s4">
  <div class="slide-inner">
    <div class="eyebrow-cyan">Camera Intelligence</div>
    <div class="section-title" style="margin-top:16px">Eyes that never blink</div>
    <div class="accent-bar"></div>
    <p class="subtitle" style="margin-top:16px">Optional camera add-on that turns any IP camera into an analytics powerhouse. No new hardware required.</p>
    <div class="grid-3" style="margin-top:36px">
      <div class="card-cyan">
        <div style="font-size:28px;margin-bottom:12px">👥</div>
        <div style="font-size:16px;font-weight:600;color:var(--cyan);margin-bottom:8px">Foot Traffic Counting</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.7">Know exactly how many people walk in every hour. Compare traffic to transactions to find your true conversion rate.</p>
        <div class="insight-box cyan">
          <div class="insight-label" style="color:var(--cyan)">Example</div>
          <div class="insight-text">"312 visitors today, 187 transactions. 60% conversion — up from 52% last month."</div>
        </div>
      </div>
      <div class="card-cyan">
        <div style="font-size:28px;margin-bottom:12px">⏱️</div>
        <div style="font-size:16px;font-weight:600;color:var(--cyan);margin-bottom:8px">Queue &amp; Wait Time</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.7">Real-time line monitoring. Alerts when wait time exceeds your target. Estimates lost revenue from walkouts.</p>
        <div class="insight-box cyan">
          <div class="insight-label" style="color:var(--cyan)">Example</div>
          <div class="insight-text">"12:15pm — 8 in line, 6.5 min wait. ~4 walkouts, ~$48 lost. Open register 2."</div>
        </div>
      </div>
      <div class="card-cyan">
        <div style="font-size:28px;margin-bottom:12px">🗺️</div>
        <div style="font-size:16px;font-weight:600;color:var(--cyan);margin-bottom:8px">Zone Heatmaps &amp; Dwell</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.7">See where people linger, which displays they stop at, and how long they browse before buying — or leaving.</p>
        <div class="insight-box cyan">
          <div class="insight-label" style="color:var(--cyan)">Example</div>
          <div class="insight-text">"Customers spend 3.2 min at pastry case but only 8% buy. Try samples or a 'pick 2 for $6' deal."</div>
        </div>
      </div>
    </div>
  </div>
  <div class="page-num">04 / 09</div>
</section>

<!-- ═══════ SLIDE 5: Fusion Intelligence ═══════ -->
<section class="slide bg-radial" id="s5">
  <div class="slide-inner">
    <div class="eyebrow">Fusion Intelligence</div>
    <div class="section-title" style="margin-top:16px">POS + Camera = Superpowers</div>
    <div class="accent-bar"></div>
    <p class="subtitle" style="margin-top:16px">When we combine what your register knows with what the camera sees, you get insights no competitor has.</p>
    <div style="margin-top:36px">
      <div class="fusion">
        <div class="fusion-sig"><div class="sig-label">📡 Camera</div><div class="sig-data">Foot traffic up 23% on Saturday</div></div>
        <div class="fusion-op">+</div>
        <div class="fusion-sig"><div class="sig-label">💳 POS</div><div class="sig-data">Revenue flat — same as last Saturday</div></div>
        <div class="fusion-op eq">=</div>
        <div class="fusion-out"><div class="out-label">🧠 Meridian Insight</div><div class="sig-data">Conversion dropped from 58% to 44%</div><div class="out-action">→ "Traffic is growing but staff isn't converting. Add a greeter or upsell training."</div></div>
      </div>
      <div class="fusion">
        <div class="fusion-sig"><div class="sig-label">📡 Camera</div><div class="sig-data">14 people in line at 12:10pm, 7 min wait</div></div>
        <div class="fusion-op">+</div>
        <div class="fusion-sig"><div class="sig-label">💳 POS</div><div class="sig-data">Only 6 transactions in that window</div></div>
        <div class="fusion-op eq">=</div>
        <div class="fusion-out"><div class="out-label">🧠 Meridian Insight</div><div class="sig-data">$340 estimated lost revenue from walkouts</div><div class="out-action">→ "Open register 2 from 11:45am–1:15pm. Projected to recover $2,380/week."</div></div>
      </div>
      <div class="fusion">
        <div class="fusion-sig"><div class="sig-label">📡 Camera</div><div class="sig-data">Rain days: 40% less foot traffic</div></div>
        <div class="fusion-op">+</div>
        <div class="fusion-sig"><div class="sig-label">💳 POS</div><div class="sig-data">But avg ticket jumps to $19.80 (normal: $13.50)</div></div>
        <div class="fusion-op eq">=</div>
        <div class="fusion-out"><div class="out-label">🧠 Meridian Insight</div><div class="sig-data">Rain customers spend 47% more — they're high-intent</div><div class="out-action">→ "Run a rainy-day promo. Every extra rain visitor ≈ $20 in revenue."</div></div>
      </div>
      <div class="fusion">
        <div class="fusion-sig"><div class="sig-label">📡 Camera</div><div class="sig-data">Staff A greets in 45 sec avg</div></div>
        <div class="fusion-op">+</div>
        <div class="fusion-sig"><div class="sig-label">💳 POS</div><div class="sig-data">Staff A avg ticket: $22 vs team avg $15</div></div>
        <div class="fusion-op eq">=</div>
        <div class="fusion-out"><div class="out-label">🧠 Meridian Insight</div><div class="sig-data">Faster greeting = 47% higher ticket value</div><div class="out-action">→ "Train all staff on A's flow. Projected +$1,200/week revenue impact."</div></div>
      </div>
    </div>
  </div>
  <div class="page-num">05 / 09</div>
</section>

<!-- ═══════ SLIDE 6: Revenue Per Visitor ═══════ -->
<section class="slide bg-center" id="s6">
  <div class="slide-inner" style="text-align:center;display:flex;flex-direction:column;align-items:center">
    <div class="eyebrow">Your New Key Metric</div>
    <div class="section-title" style="margin-top:16px">Revenue Per Visitor</div>
    <div class="accent-bar" style="margin:20px auto 0"></div>
    <p class="subtitle" style="margin-top:24px;text-align:center;max-width:800px;margin-left:auto;margin-right:auto">
      Only possible when POS data meets camera data. This is the number that separates thriving businesses from guessing ones. Track it daily, optimize it weekly, watch your revenue grow.
    </p>
    <div style="margin-top:48px;display:grid;grid-template-columns:repeat(3,1fr);gap:32px;width:100%;max-width:900px">
      <div class="card-glow" style="text-align:center;padding:32px">
        <div style="font-family:monospace;font-size:11px;color:var(--violet);letter-spacing:0.12em;margin-bottom:12px">BEFORE MERIDIAN</div>
        <div style="font-family:monospace;font-size:40px;font-weight:700;color:var(--dim)">???</div>
        <div style="font-size:13px;color:var(--muted);margin-top:8px">No visibility into traffic vs. sales</div>
      </div>
      <div class="card-glow" style="text-align:center;padding:32px;border-color:rgba(124,92,255,0.35)">
        <div style="font-family:monospace;font-size:11px;color:var(--violet);letter-spacing:0.12em;margin-bottom:12px">INDUSTRY AVERAGE</div>
        <div style="font-family:monospace;font-size:40px;font-weight:700;color:var(--white)">$4.20</div>
        <div style="font-size:13px;color:var(--muted);margin-top:8px">Per visitor (quick-service)</div>
      </div>
      <div class="card-glow" style="text-align:center;padding:32px;border-color:rgba(79,227,193,0.35)">
        <div style="font-family:monospace;font-size:11px;color:var(--cyan);letter-spacing:0.12em;margin-bottom:12px">WITH MERIDIAN (90 DAYS)</div>
        <div style="font-family:monospace;font-size:40px;font-weight:700;color:var(--cyan)">$5.85</div>
        <div style="font-size:13px;color:var(--muted);margin-top:8px">+39% through optimization</div>
      </div>
    </div>
  </div>
  <div class="page-num">06 / 09</div>
</section>

<!-- ═══════ SLIDE 7: Your Plan ═══════ -->
<section class="slide bg-violet" id="s7">
  <div class="slide-inner">
    <div class="eyebrow">Your Plan</div>
    <div class="section-title" style="margin-top:16px">Meridian ${esc(plan.label)}</div>
    <div class="accent-bar"></div>
    <div class="grid-2">
      <div class="card-glow">
        <div style="font-family:monospace;font-size:12px;color:var(--violet);letter-spacing:0.12em;margin-bottom:24px">WHAT'S INCLUDED</div>
        <ul class="checks">${features}</ul>
      </div>
      <div class="card">
        <div style="font-family:monospace;font-size:12px;color:var(--cyan);letter-spacing:0.12em;margin-bottom:24px">PLATFORM HIGHLIGHTS</div>
        <ul class="checks">
          <li>5-minute POS onboarding</li>
          <li>Square, Clover &amp; Toast integration</li>
          <li>7 AI agents analyzing your data 24/7</li>
          <li>Weather-correlated revenue insights</li>
          <li>Real-time anomaly detection &amp; alerts</li>
          <li>Mobile-friendly dashboard</li>
          <li>Predictive staffing recommendations</li>
          ${plan.id !== 'standard' ? '<li>Camera intelligence &amp; foot traffic</li>' : ''}
          ${plan.id === 'command' ? '<li>Dedicated account manager</li>' : ''}
        </ul>
      </div>
    </div>
  </div>
  <div class="page-num">07 / 09</div>
</section>

<!-- ═══════ SLIDE 8: Pricing ═══════ -->
<section class="slide bg-radial" id="s8">
  <div class="slide-inner">
    <div class="eyebrow">Your Investment</div>
    <div class="section-title" style="margin-top:16px">Simple, Transparent Pricing</div>
    <div class="accent-bar"></div>
    <div class="grid-2">
      <div class="card-glow" style="display:flex;flex-direction:column;justify-content:center">
        <div style="font-family:monospace;font-size:12px;color:var(--violet);letter-spacing:0.12em;margin-bottom:20px">MERIDIAN ${esc(plan.label.toUpperCase())}</div>
        <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:32px">
          <span class="price-hero">$${price.toLocaleString()}</span>
          <span class="price-per">/month</span>
        </div>
        <ul class="checks" style="border-top:1px solid var(--border);padding-top:24px">${features}</ul>
      </div>
      <div class="card">
        <div style="font-family:monospace;font-size:12px;color:var(--cyan);letter-spacing:0.12em;margin-bottom:20px">ORDER SUMMARY</div>
        <div class="summary-row"><span class="label">${esc(plan.label)} Plan (monthly)</span><span class="value">$${price.toLocaleString()}/mo</span></div>
        ${setupFee > 0 ? `<div class="summary-row"><span class="label">One-Time Setup Fee</span><span class="value">$${setupFee.toLocaleString()}</span></div>` : ''}
        ${firstMonthFree ? `<div class="summary-row"><span class="label">First Month</span><span class="value" style="color:var(--cyan)">FREE</span></div>` : ''}
        <div class="summary-total"><span class="label" style="color:var(--white);font-weight:600">Due Today</span><span class="value">$${dueToday.toLocaleString()}</span></div>
        ${firstMonthFree ? '<p style="font-size:13px;color:var(--violet);margin-top:8px">🎉 Your first month is on us. Billing starts month 2.</p>' : ''}
        ${checkoutUrl ? `<div style="margin-top:24px;padding-top:20px;border-top:1px solid var(--border);text-align:center">
          <p style="font-size:12px;color:var(--dim);margin-bottom:16px">Scan to pay or click below</p>
          <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(checkoutUrl)}&color=7C5CFF&bgcolor=111113&format=png" width="180" height="180" style="border-radius:12px;border:1px solid var(--border);margin-bottom:12px" alt="Checkout QR Code"/>
          <br><a href="${esc(checkoutUrl)}" target="_blank" style="color:var(--cyan);font-size:13px;word-break:break-all">${esc(checkoutUrl)}</a>
        </div>` : ''}
      </div>
    </div>
  </div>
  <div class="page-num">08 / 09</div>
</section>

<!-- ═══════ SLIDE 9: CTA ═══════ -->
<section class="slide bg-center" id="s9">
  <div class="slide-inner" style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;min-height:70vh">
    <div class="eyebrow" style="margin-bottom:32px">Ready to grow your business?</div>
    <div class="hero-title">Let's go,</div>
    <div class="hero-title" style="color:var(--violet)">${esc(firstName)}</div>
    <div class="accent-bar" style="margin:24px auto 0"></div>
    <p class="subtitle" style="margin-top:32px;text-align:center;margin-left:auto;margin-right:auto">
      Connect your POS in 5 minutes. See your first insights today.${firstMonthFree ? ' First month free — no risk.' : ''}
    </p>
    ${checkoutUrl
      ? `<a href="${esc(checkoutUrl)}" target="_blank" class="btn-primary" style="margin-top:48px">Get Started Now →</a>
         <div style="margin-top:40px;display:flex;flex-direction:column;align-items:center;gap:12px">
           <img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(checkoutUrl)}&color=F5F5F7&bgcolor=111113&format=png" width="220" height="220" style="border-radius:16px;border:2px solid var(--border);padding:8px;background:var(--surface)" alt="Checkout QR Code"/>
           <p style="font-size:12px;color:var(--dim)">Scan to checkout</p>
         </div>
         <p style="font-size:13px;color:var(--dim);margin-top:12px">${esc(checkoutUrl)}</p>`
      : `<div class="btn-primary" style="margin-top:48px">GET STARTED</div>`
    }
    <div style="margin-top:64px;display:flex;gap:48px;flex-wrap:wrap;justify-content:center">
      <div style="text-align:center"><div style="font-family:monospace;font-size:10px;color:var(--dim);letter-spacing:0.12em;margin-bottom:6px">YOUR REP</div><div style="font-size:16px;color:var(--muted)">${esc(rep.name)}</div></div>
      <div style="text-align:center"><div style="font-family:monospace;font-size:10px;color:var(--dim);letter-spacing:0.12em;margin-bottom:6px">EMAIL</div><div style="font-size:16px;color:var(--muted)">${esc(rep.email)}</div></div>
      ${rep.phone ? `<div style="text-align:center"><div style="font-family:monospace;font-size:10px;color:var(--dim);letter-spacing:0.12em;margin-bottom:6px">PHONE</div><div style="font-size:16px;color:var(--muted)">${esc(rep.phone)}</div></div>` : ''}
      <div style="text-align:center"><div style="font-family:monospace;font-size:10px;color:var(--dim);letter-spacing:0.12em;margin-bottom:6px">PLATFORM</div><div style="font-size:16px;color:var(--muted)">meridian.tips</div></div>
    </div>
  </div>
  <div class="page-num">09 / 09</div>
</section>

<script>
// Navigation dots
const slides = document.querySelectorAll('.slide');
const dotsContainer = document.getElementById('dots');
slides.forEach((s, i) => {
  const dot = document.createElement('button');
  dot.className = 'nav-dot' + (i === 0 ? ' active' : '');
  dot.onclick = () => s.scrollIntoView({ behavior: 'smooth' });
  dotsContainer.appendChild(dot);
});
const dots = dotsContainer.querySelectorAll('.nav-dot');
const observer = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      const idx = Array.from(slides).indexOf(e.target);
      dots.forEach((d, i) => d.classList.toggle('active', i === idx));
    }
  });
}, { threshold: 0.5 });
slides.forEach(s => observer.observe(s));
</script>
</body>
</html>`
}

/**
 * Generate the proposal and return it as a Blob (for compatibility with email flow).
 */
export async function generateProposalPdf(input: ProposalInput): Promise<Blob> {
  const html = buildProposalHtml(input)
  return new Blob([html], { type: 'text/html' })
}

/**
 * Open the proposal in a new browser tab as a live HTML page.
 */
export async function downloadProposalPdf(input: ProposalInput): Promise<void> {
  const html = buildProposalHtml(input)
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
