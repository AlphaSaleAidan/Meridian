/**
 * SLA generator — opens a polished HTML legal document in a new browser tab.
 * Crisp vector text, print-ready, responsive. Renders Canada or US flavors.
 */

export type SlaCountry = 'CA' | 'US'

/** Usage-based billing terms for the AI phone agent — mirrors the live
 *  backend dials (fixed per-order tier rate, included minutes, overage,
 *  hard call cap). Amounts in minor units of the local currency. */
export interface SlaPhoneAgentTerms {
  orderFeeCents: number
  includedMinutes: number
  overageCentsPerMin: number
  maxCallMinutes: number
}

export interface SlaInput {
  country: SlaCountry
  clientCompanyName: string
  /** Province (Canada) or state (US). */
  region: string
  posSystem: string
  repName: string
  planName?: string
  /** Monthly fee in minor units (cents) of the local currency. */
  monthlyPriceCents: number
  /** One-time setup fee in minor units (cents) of the local currency. */
  setupFeeCents: number
  /** When true, inserts a first-month complimentary clause in section 3. */
  firstMonthFree?: boolean
  /** Present only when the selected plan includes the AI phone agent —
   *  renders the usage-fee clause and the phone-agent service bullet. */
  phoneAgent?: SlaPhoneAgentTerms
  /** Website Buildout recurring (maintenance + hosting) actually billed, in
   *  minor units. Pass together with websiteMonthlyIncluded when a website
   *  was sold; omit both when no website is part of the deal. */
  websiteMonthlyCents?: number
  /** True when maintenance + hosting come free with the selected plan tier. */
  websiteMonthlyIncluded?: boolean
  startDate: string
  clientSignature?: string
}

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function formatMoney(country: SlaCountry, cents: number): string {
  if (country === 'US') {
    return `US$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
  return `CA$${(cents / 100).toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function isQuebec(region: string): boolean {
  const p = region.toLowerCase().trim()
  return p === 'qc' || p === 'quebec' || p === 'québec'
}

function buildSlaHtml(input: SlaInput): string {
  const locale = input.country === 'US' ? 'en-US' : 'en-CA'
  const today = new Date().toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' })
  const effectiveDate = input.startDate
    ? new Date(input.startDate).toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' })
    : today

  // Country-specific labels and clauses
  const isUS = input.country === 'US'
  const regionLabel = isUS ? 'State' : 'Province'
  const countryName = isUS ? 'United States' : 'Canada'
  const currencyName = isUS ? 'United States Dollars (USD)' : 'Canadian Dollars (CAD)'
  const taxNote = isUS
    ? 'All fees are exclusive of applicable federal, state, and local taxes (sales tax where applicable).'
    : 'All fees are exclusive of applicable federal and provincial taxes (GST/HST/QST).'
  const privacyLawText = isUS
    ? '<strong>US Privacy Compliance.</strong> The Provider shall comply with applicable United States federal and state privacy laws, including the California Consumer Privacy Act (CCPA/CPRA) and the Virginia, Colorado, Connecticut, and Utah consumer privacy statutes where applicable to the Client.'
    : '<strong>PIPEDA Compliance.</strong> The Provider shall comply with the Personal Information Protection and Electronic Documents Act (PIPEDA) and all applicable provincial privacy legislation.'
  const breachAuthority = isUS
    ? 'In the event of a breach of security safeguards, the Provider shall notify the Client without unreasonable delay and shall cooperate with the Client in making any required notifications to affected individuals or regulators (including state Attorneys General) under applicable US breach-notification statutes.'
    : 'In the event of a breach of security safeguards, the Provider shall notify the Client and the Office of the Privacy Commissioner of Canada.'
  const governingLaw = isUS
    ? `This Agreement shall be governed by the laws of the State of ${esc(input.region)} and the federal laws of the United States.`
    : `This Agreement shall be governed by the laws of the Province of ${esc(input.region)} and the federal laws of Canada.`
  const subtitle = isUS ? 'Meridian AI Business Solutions &mdash; United States' : 'Meridian AI Business Solutions &mdash; Canada'

  // Quebec Law 25 — only renders when applicable
  const quebecSection = !isUS && isQuebec(input.region) ? `
      <h3>8A. Quebec Law 25 — Additional Obligations</h3>
      <p>8A.1 The Provider designates a person responsible for the protection of personal information in accordance with Quebec&rsquo;s Act respecting the protection of personal information in the private sector (Quebec Law 25).</p>
      <p>8A.2 Before implementing any new system involving personal information of Quebec residents, the Provider shall conduct a Privacy Impact Assessment (PIA).</p>
      <p>8A.3 The Provider shall publish a clear privacy policy describing collection, purposes, rights, and retention periods.</p>
      <p>8A.4 The Provider shall, upon request, cease disseminating personal information and de-index any hyperlink attached to that individual&rsquo;s name, in accordance with Law 25.</p>
      <p>8A.5 Transfers of personal information outside Quebec shall require a privacy impact assessment ensuring adequate protection in the receiving jurisdiction.</p>
      <p>8A.6 Confidentiality incidents involving Quebec residents shall be reported to the Commission d&rsquo;acc&egrave;s &agrave; l&rsquo;information du Qu&eacute;bec (CAI) and to affected individuals.</p>
  ` : ''

  const websiteSold = input.websiteMonthlyCents !== undefined || input.websiteMonthlyIncluded !== undefined

  // Section 3 fee clauses — assembled then numbered sequentially so the
  // conditional clauses (first month, phone agent, website) never leave gaps.
  const feeClauses: string[] = []
  feeClauses.push(`<strong>Monthly Service Fee.</strong> The Client shall pay a monthly service fee of <strong>${formatMoney(input.country, input.monthlyPriceCents)}</strong> (plus applicable taxes) for the ${input.planName ? `Meridian <strong>${esc(input.planName)}</strong> plan` : 'Services described herein'}.`)
  feeClauses.push(input.setupFeeCents > 0
    ? `<strong>Setup Fee.</strong> A one-time setup fee of <strong>${formatMoney(input.country, input.setupFeeCents)}</strong> (plus applicable taxes) is payable upon execution of this Agreement.`
    : `<strong>Setup Fee.</strong> No setup fee is applicable under this Agreement.`)
  if (input.firstMonthFree) {
    feeClauses.push(`<strong>First Month Complimentary.</strong> As an introductory offer, the first calendar month of the Monthly Service Fee is waived. The one-time setup fee (where applicable) remains payable upon execution of this Agreement; recurring monthly billing commences at the start of the second calendar month.`)
  }
  if (input.phoneAgent) {
    const pa = input.phoneAgent
    feeClauses.push(`<strong>Phone Agent Usage Fees.</strong> In addition to the Monthly Service Fee, each order placed through the AI phone agent incurs a fixed per-order transaction fee of <strong>${formatMoney(input.country, pa.orderFeeCents)}</strong>. Every call includes the first ${pa.includedMinutes} minutes of call time at no additional charge; call time beyond the included minutes is billed at <strong>${formatMoney(input.country, pa.overageCentsPerMin)}</strong> per additional minute. Calls are automatically concluded at ${pa.maxCallMinutes} minutes, which caps the maximum per-call overage. Usage fees are calculated per order and per call and are billed to the Client&rsquo;s Meridian account.`)
  }
  if (websiteSold && input.websiteMonthlyIncluded) {
    feeClauses.push(`<strong>Website Maintenance &amp; Hosting.</strong> Ongoing website maintenance and managed hosting are included in the Client&rsquo;s plan at no additional recurring charge. The one-time website buildout is billed as part of the Setup Fee above.`)
  } else if (websiteSold && (input.websiteMonthlyCents ?? 0) > 0) {
    feeClauses.push(`<strong>Website Maintenance &amp; Hosting.</strong> Ongoing website maintenance and managed hosting are provided for a recurring fee of <strong>${formatMoney(input.country, input.websiteMonthlyCents ?? 0)}</strong> per month (plus applicable taxes), billed alongside the Monthly Service Fee. The one-time website buildout is billed as part of the Setup Fee above.`)
  }
  feeClauses.push(`<strong>Payment Terms.</strong> All invoices are due and payable within thirty (30) days. Payments shall be made in ${currencyName}.`)
  feeClauses.push(`<strong>Taxes.</strong> ${taxNote}`)
  feeClauses.push(`<strong>Late Payment.</strong> Overdue invoices shall bear interest at 1.5% per month (18% per annum) or the maximum rate permitted by law.`)
  const feesHtml = feeClauses.map((c, i) => `<p>3.${i + 1} ${c}</p>`).join('\n    ')

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SLA — Meridian &amp; ${esc(input.clientCompanyName)}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#08080A;--surface:#0E0E12;--border:rgba(255,255,255,0.07);
  --accent:#00d4aa;--violet:#7C5CFF;--white:#F5F5F7;--muted:#A1A1A8;--dim:#6B6B73;
}
body{background:var(--bg);color:var(--white);font-family:'Inter',system-ui,sans-serif;-webkit-font-smoothing:antialiased;line-height:1.7}

/* Print bar */
.print-bar{position:fixed;top:0;left:0;right:0;z-index:200;background:rgba(8,8,10,0.95);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:12px 32px;display:flex;align-items:center;justify-content:space-between}
.print-bar .logo{font-family:'DM Serif Display',Georgia,serif;font-style:italic;font-size:20px;color:var(--white)}
.print-btn{padding:8px 24px;background:var(--accent);color:#08080A;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;font-family:'Inter',sans-serif}
.print-btn:hover{opacity:0.9}

/* Document container */
.doc{max-width:820px;margin:80px auto 60px;padding:0 24px}

/* Title block */
.title-block{text-align:center;padding:48px 0 40px;border-bottom:1px solid var(--border)}
.title-block h1{font-family:'DM Serif Display',Georgia,serif;font-style:italic;font-size:clamp(28px,4vw,42px);color:var(--accent);margin-bottom:8px}
.title-block .subtitle{font-size:14px;color:var(--muted);letter-spacing:0.08em;text-transform:uppercase}

/* Parties card */
.parties{margin:32px 0;padding:28px 32px;background:var(--surface);border:1px solid var(--border);border-radius:12px}
.parties-grid{display:grid;grid-template-columns:140px 1fr;gap:8px 16px;font-size:14px}
.parties-grid .label{color:var(--muted);font-weight:600;font-size:12px;letter-spacing:0.06em;text-transform:uppercase}
.parties-grid .value{color:var(--white)}

/* Sections */
.section{margin-top:36px}
.section h2{font-size:15px;font-weight:700;color:var(--accent);letter-spacing:0.04em;text-transform:uppercase;padding-bottom:8px;border-bottom:1px solid rgba(0,212,170,0.2);margin-bottom:16px}
.section h3{font-size:13px;font-weight:700;color:#b0d4c8;margin:20px 0 12px}
.section p{font-size:13.5px;color:var(--white);margin-bottom:10px;line-height:1.75}
.section ul{list-style:none;padding:0;margin-bottom:12px}
.section ul li{font-size:13.5px;color:var(--white);padding:4px 0 4px 20px;position:relative;line-height:1.6}
.section ul li::before{content:'\\2713';position:absolute;left:0;color:var(--accent);font-weight:700;font-size:12px}

/* Table */
.sla-table{width:100%;border-collapse:collapse;margin:12px 0 16px;font-size:13px}
.sla-table th{background:rgba(0,212,170,0.08);color:var(--accent);font-weight:600;text-align:left;padding:10px 14px;border:1px solid var(--border);font-size:12px;letter-spacing:0.04em;text-transform:uppercase}
.sla-table td{padding:10px 14px;border:1px solid var(--border);color:var(--white);background:var(--surface)}

/* Signature blocks */
.signatures{margin-top:48px;padding-top:32px;border-top:2px solid var(--border)}
.signatures h2{font-size:16px;font-weight:700;color:var(--accent);text-align:center;margin-bottom:8px}
.signatures .witness{font-size:13px;color:var(--muted);text-align:center;margin-bottom:32px}
.sig-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
@media(max-width:640px){.sig-grid{grid-template-columns:1fr}}
.sig-box{padding:24px;background:var(--surface);border:1px solid var(--border);border-radius:12px}
.sig-box.signed{border-color:rgba(0,212,170,0.3)}
.sig-box .role{font-size:11px;font-weight:700;color:var(--muted);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:16px}
.sig-name{font-family:'DM Serif Display',Georgia,serif;font-style:italic;font-size:24px;color:var(--accent);margin-bottom:4px}
.sig-title{font-size:12px;color:var(--muted)}
.sig-date{font-size:12px;color:var(--muted);margin-top:4px}
.sig-line{border:none;border-top:1px solid var(--muted);margin:20px 0 8px;opacity:0.4}
.sig-placeholder{font-size:13px;font-style:italic;color:var(--dim)}
.sig-labels{display:flex;justify-content:space-between;font-size:11px;color:var(--dim)}

/* Footer */
.doc-footer{margin-top:40px;padding-top:20px;border-top:1px solid var(--border);text-align:center;font-size:12px;color:var(--dim)}

/* Print styles */
@media print{
  .print-bar{display:none!important}
  body{background:white;color:#111}
  .doc{margin:0 auto;padding:0 20px}
  .title-block{border-bottom:1px solid #ccc}
  .title-block h1{color:#006B55}
  .parties,.sig-box{border:1px solid #ddd;background:#f9f9f9}
  .section h2{color:#006B55;border-bottom:1px solid #ddd}
  .section h3{color:#333}
  .section p,.section ul li{color:#222}
  .section ul li::before{color:#006B55}
  .sla-table th{background:#eee;color:#006B55;border-color:#ccc}
  .sla-table td{background:white;border-color:#ccc;color:#222}
  .signatures{border-top:2px solid #ccc}
  .signatures h2{color:#006B55}
  .sig-name{color:#006B55}
  .doc-footer{border-top:1px solid #ccc;color:#888}
}
</style>
</head>
<body>

<!-- Print / Share Bar -->
<div class="print-bar">
  <div class="logo">Meridian</div>
  <div style="display:flex;gap:12px;align-items:center">
    <span style="font-size:12px;color:var(--muted)">SLA &mdash; ${esc(input.clientCompanyName)}</span>
    <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
  </div>
</div>

<div class="doc">

  <!-- Title -->
  <div class="title-block">
    <h1>Service Level Agreement</h1>
    <div class="subtitle">${subtitle}</div>
  </div>

  <!-- Parties -->
  <div class="parties">
    <div class="parties-grid">
      <div class="label">Provider</div><div class="value">Meridian AI Business Solutions</div>
      <div class="label">Client</div><div class="value">${esc(input.clientCompanyName)}</div>
      <div class="label">${regionLabel}</div><div class="value">${esc(input.region)}</div>
      <div class="label">Effective Date</div><div class="value">${effectiveDate}</div>
      <div class="label">Agreement Date</div><div class="value">${today}</div>
    </div>
  </div>

  <!-- 1. Services -->
  <div class="section">
    <h2>1. Services Provided</h2>
    <p>1.1 Meridian AI Business Solutions (&ldquo;Provider&rdquo;) agrees to provide the following services to the Client:</p>
    <ul>
      <li>AI-powered business intelligence and analytics dashboard</li>
      <li>Point-of-sale (POS) data integration and real-time monitoring</li>
      <li>Revenue forecasting and predictive analytics</li>
      <li>Customer behavior analysis and insights</li>
      <li>Inventory optimization recommendations</li>
      <li>AI camera analytics and foot traffic analysis (where applicable)</li>
      <li>3D space mapping and visualization</li>
      ${input.phoneAgent ? '<li>AI phone agent &mdash; automated call answering and order capture</li>' : ''}
      ${websiteSold ? '<li>Website buildout, maintenance, and managed hosting</li>' : ''}
    </ul>
    <p>1.2 <strong>POS System Integration.</strong> The Provider shall integrate with the Client&rsquo;s existing POS system (${esc(input.posSystem)}) to enable data collection and analytics.</p>
  </div>

  <!-- 2. Service Levels -->
  <div class="section">
    <h2>2. Service Level Commitments</h2>
    <p>2.1 <strong>Availability.</strong> The Provider commits to a service availability target of 99.5% measured on a monthly basis, excluding scheduled maintenance windows.</p>
    <p>2.2 <strong>Scheduled Maintenance.</strong> Maintenance windows shall occur between 2:00 AM and 6:00 AM ET and shall not exceed four (4) hours per month. At least 48 hours&rsquo; advance notice will be provided.</p>
    <p>2.3 <strong>Data Processing.</strong> POS transaction data shall be processed and reflected in the dashboard within sixty (60) minutes of receipt.</p>
    <p>2.4 <strong>Incident Response Times:</strong></p>
    <table class="sla-table">
      <thead><tr><th>Severity</th><th>Description</th><th>Response Time</th></tr></thead>
      <tbody>
        <tr><td>Critical (P1)</td><td>Complete service outage or data loss</td><td>1 hour</td></tr>
        <tr><td>High (P2)</td><td>Major feature unavailable</td><td>4 hours</td></tr>
        <tr><td>Medium (P3)</td><td>Minor feature degradation</td><td>1 business day</td></tr>
        <tr><td>Low (P4)</td><td>Cosmetic or informational</td><td>3 business days</td></tr>
      </tbody>
    </table>
  </div>

  <!-- 3. Fees -->
  <div class="section">
    <h2>3. Fees and Payment</h2>
    ${feesHtml}
  </div>

  <!-- 4. Term -->
  <div class="section">
    <h2>4. Term and Termination</h2>
    <p>4.1 <strong>Term.</strong> This Agreement shall commence on ${effectiveDate} and continue on a month-to-month basis until terminated in accordance with this Section. There is no minimum commitment or long-term lock-in.</p>
    <p>4.2 <strong>Termination for Convenience.</strong> Either party may terminate this Agreement at any time, for any reason, by providing thirty (30) days&rsquo; written notice to the other party. Fees accrued through the effective date of termination remain payable; no early-termination fee applies.</p>
    <p>4.3 <strong>Termination for Cause.</strong> Either party may terminate immediately upon written notice if the other party commits a material breach and fails to cure within thirty (30) days.</p>
    <p>4.4 <strong>Effect of Termination.</strong> Upon termination, the Provider shall cease all Services, provide Client data in electronic format within thirty (30) days, and securely delete all Client data within sixty (60) days.</p>
  </div>

  <!-- 5. IP -->
  <div class="section">
    <h2>5. Intellectual Property</h2>
    <p>5.1 <strong>Client Data.</strong> The Client retains all right, title, and interest in and to all data provided by the Client or generated through the Client&rsquo;s use of the Services.</p>
    <p>5.2 <strong>Provider IP.</strong> The Provider retains all right, title, and interest in and to the Services, including all AI models, algorithms, software, and analytics methodologies.</p>
    <p>5.3 <strong>Aggregated Data.</strong> The Provider may use anonymized and aggregated Client Data for improving the Services, provided it cannot identify the Client or any individual.</p>
  </div>

  <!-- 6. Confidentiality -->
  <div class="section">
    <h2>6. Confidentiality</h2>
    <p>6.1 Each party agrees to maintain the confidentiality of all information received from the other party that is identified as confidential or that a reasonable person would understand to be confidential.</p>
    <p>6.2 Confidential information shall not be disclosed to any third party without prior written consent, except as required by law.</p>
    <p>6.3 The obligations of confidentiality shall survive termination for three (3) years.</p>
  </div>

  <!-- 7. Liability -->
  <div class="section">
    <h2>7. Limitation of Liability</h2>
    <p>7.1 NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF THIS AGREEMENT.</p>
    <p>7.2 THE TOTAL AGGREGATE LIABILITY OF EITHER PARTY SHALL NOT EXCEED THE TOTAL FEES PAID OR PAYABLE DURING THE TWELVE (12) MONTH PERIOD PRECEDING THE CLAIM.</p>
    <p>7.3 This limitation does not apply to breaches of confidentiality, data protection obligations, or willful misconduct.</p>
  </div>

  <!-- 8. Privacy -->
  <div class="section">
    <h2>8. Data Protection &amp; Privacy Compliance</h2>
    <p>8.1 ${privacyLawText}</p>
    <p>8.2 <strong>Data Collection.</strong> The Provider shall collect only such personal information as is reasonably necessary for the Services.</p>
    <p>8.3 <strong>Data Security.</strong> The Provider shall implement reasonable administrative, technical, and physical safeguards to protect personal information.</p>
    <p>8.4 <strong>Breach Notification.</strong> ${breachAuthority}</p>
    <p>8.5 <strong>Data Retention.</strong> Personal information shall be retained only for so long as reasonably necessary or as required by applicable law.</p>
    ${quebecSection}
  </div>

  <!-- 9. General -->
  <div class="section">
    <h2>9. General Provisions</h2>
    <p>9.1 <strong>Governing Law.</strong> ${governingLaw}</p>
    <p>9.2 <strong>Entire Agreement.</strong> This Agreement constitutes the entire agreement between the parties and supersedes all prior agreements.</p>
    <p>9.3 <strong>Amendment.</strong> This Agreement may be amended only by written instrument signed by both parties.</p>
    <p>9.4 <strong>Assignment.</strong> Neither party may assign without prior written consent, except in connection with a merger or acquisition.</p>
    <p>9.5 <strong>Force Majeure.</strong> Neither party shall be liable for failures due to circumstances beyond reasonable control.</p>
    <p>9.6 <strong>Severability.</strong> If any provision is held invalid, the remaining provisions continue in full force.</p>
  </div>

  <!-- Signatures -->
  <div class="signatures">
    <h2>Signatures</h2>
    <p class="witness">IN WITNESS WHEREOF, the parties have executed this Service Level Agreement as of the date first written above.</p>

    <div class="sig-grid">
      <!-- Provider -->
      <div class="sig-box signed">
        <div class="role">Provider &mdash; Meridian AI Business Solutions</div>
        <div class="sig-name">Aidan Pierce</div>
        <div class="sig-title">Founder &amp; CEO</div>
        <div class="sig-date">Date: ${today}</div>
        <hr class="sig-line"/>
      </div>

      <!-- Client -->
      <div class="sig-box${input.clientSignature ? ' signed' : ''}">
        <div class="role">Client &mdash; ${esc(input.clientCompanyName)}</div>
        ${input.clientSignature
          ? `<div class="sig-name" style="color:var(--white)">${esc(input.clientSignature)}</div>
             <div class="sig-title">Authorized Signatory</div>
             <div class="sig-date">Date: ${today}</div>
             <hr class="sig-line"/>`
          : `<div class="sig-placeholder">Awaiting client signature...</div>
             <hr class="sig-line"/>
             <div class="sig-labels"><span>Authorized Signatory</span><span>Date</span></div>`
        }
      </div>
    </div>
  </div>

  <!-- Footer -->
  <div class="doc-footer">
    <p>Sales Representative: ${esc(input.repName)} &middot; Meridian AI Business Solutions &middot; meridian.tips</p>
  </div>

</div>
</body>
</html>`
}

export async function generateSlaDocument(input: SlaInput): Promise<Blob> {
  const html = buildSlaHtml(input)
  return new Blob([html], { type: 'text/html' })
}
