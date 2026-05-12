import jsPDF from 'jspdf'

export interface SlaInput {
  clientCompanyName: string
  province: string
  posSystem: string
  repName: string
  monthlyPriceCad: number
  setupFeeCad: number
  startDate: string
  clientSignature?: string
}

function formatCad(cents: number): string {
  return `CA$${(cents / 100).toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function isQuebec(province: string): boolean {
  const p = province.toLowerCase().trim()
  return p === 'qc' || p === 'quebec' || p === 'québec'
}

const BG = '#0a0f0d'
const CARD = '#0f1512'
const BORDER = '#1a2420'
const ACCENT = '#00d4aa'
const TEXT = '#e8ede8'
const MUTED = '#6b7a74'
const MARGIN = 20
const PAGE_W = 210
const CONTENT_W = PAGE_W - MARGIN * 2

export async function generateSlaDocument(input: SlaInput): Promise<Blob> {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const today = new Date().toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' })
  const effectiveDate = input.startDate
    ? new Date(input.startDate).toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' })
    : today

  let y = 0

  function setColor(hex: string) {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    doc.setTextColor(r, g, b)
  }

  function setFillColor(hex: string) {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    doc.setFillColor(r, g, b)
  }

  function setDrawColor(hex: string) {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    doc.setDrawColor(r, g, b)
  }

  function newPage() {
    doc.addPage()
    setFillColor(BG)
    doc.rect(0, 0, 210, 297, 'F')
    y = MARGIN
  }

  function checkPage(needed: number) {
    if (y + needed > 277) newPage()
  }

  function heading(text: string) {
    checkPage(14)
    y += 6
    doc.setFontSize(11)
    doc.setFont('helvetica', 'bold')
    setColor(ACCENT)
    doc.text(text, MARGIN, y)
    y += 2
    setDrawColor(ACCENT)
    doc.setLineWidth(0.3)
    doc.line(MARGIN, y, MARGIN + CONTENT_W, y)
    y += 5
  }

  function subheading(text: string) {
    checkPage(10)
    y += 3
    doc.setFontSize(9.5)
    doc.setFont('helvetica', 'bold')
    setColor('#b0d4c8')
    doc.text(text, MARGIN, y)
    y += 5
  }

  function para(text: string) {
    checkPage(8)
    doc.setFontSize(8.5)
    doc.setFont('helvetica', 'normal')
    setColor(TEXT)
    const lines = doc.splitTextToSize(text, CONTENT_W)
    for (const line of lines) {
      checkPage(4.5)
      doc.text(line, MARGIN, y)
      y += 4
    }
    y += 2
  }

  function bullet(text: string) {
    checkPage(5)
    doc.setFontSize(8.5)
    doc.setFont('helvetica', 'normal')
    setColor(TEXT)
    const lines = doc.splitTextToSize(text, CONTENT_W - 6)
    setColor(ACCENT)
    doc.text('•', MARGIN + 2, y)
    setColor(TEXT)
    for (let i = 0; i < lines.length; i++) {
      checkPage(4.5)
      doc.text(lines[i], MARGIN + 6, y)
      y += 4
    }
    y += 1
  }

  function tableRow(cells: string[], widths: number[], isHeader = false) {
    checkPage(8)
    const rowH = 7
    let x = MARGIN
    for (let i = 0; i < cells.length; i++) {
      setFillColor(isHeader ? '#142018' : CARD)
      setDrawColor(BORDER)
      doc.rect(x, y - 4.5, widths[i], rowH, 'FD')
      doc.setFontSize(7.5)
      doc.setFont('helvetica', isHeader ? 'bold' : 'normal')
      setColor(isHeader ? ACCENT : TEXT)
      doc.text(cells[i], x + 2, y)
      x += widths[i]
    }
    y += rowH - 4.5 + 1
  }

  // Background
  setFillColor(BG)
  doc.rect(0, 0, 210, 297, 'F')

  // Title
  y = 30
  doc.setFontSize(18)
  doc.setFont('helvetica', 'bold')
  setColor(ACCENT)
  doc.text('SERVICE LEVEL AGREEMENT', PAGE_W / 2, y, { align: 'center' })
  y += 8
  doc.setFontSize(10)
  setColor(MUTED)
  doc.text('MERIDIAN AI BUSINESS SOLUTIONS — CANADA', PAGE_W / 2, y, { align: 'center' })
  y += 12

  // Parties card
  setFillColor(CARD)
  setDrawColor(BORDER)
  doc.roundedRect(MARGIN, y, CONTENT_W, 42, 2, 2, 'FD')
  y += 7
  const pairs: [string, string][] = [
    ['Provider:', 'Meridian AI Business Solutions'],
    ['Client:', input.clientCompanyName],
    ['Province:', input.province],
    ['Effective Date:', effectiveDate],
    ['Agreement Date:', today],
  ]
  for (const [label, val] of pairs) {
    doc.setFontSize(8)
    doc.setFont('helvetica', 'bold')
    setColor(MUTED)
    doc.text(label, MARGIN + 5, y)
    doc.setFont('helvetica', 'normal')
    setColor(TEXT)
    doc.text(val, MARGIN + 40, y)
    y += 7
  }
  y += 5

  // 1. Services
  heading('1. SERVICES PROVIDED')
  para('1.1 Meridian AI Business Solutions ("Provider") agrees to provide the following services to the Client:')
  bullet('AI-powered business intelligence and analytics dashboard')
  bullet('Point-of-sale (POS) data integration and real-time monitoring')
  bullet('Revenue forecasting and predictive analytics')
  bullet('Customer behavior analysis and insights')
  bullet('Inventory optimization recommendations')
  bullet('AI camera analytics and foot traffic analysis (where applicable)')
  bullet('3D space mapping and visualization')
  para(`1.2 POS System Integration. The Provider shall integrate with the Client's existing POS system (${input.posSystem}) to enable data collection and analytics.`)

  // 2. Service Levels
  heading('2. SERVICE LEVEL COMMITMENTS')
  para('2.1 Availability. The Provider commits to a service availability target of 99.5% measured on a monthly basis, excluding scheduled maintenance windows.')
  para("2.2 Scheduled Maintenance. Maintenance windows shall occur between 2:00 AM and 6:00 AM ET and shall not exceed four (4) hours per month. At least 48 hours' advance notice will be provided.")
  para('2.3 Data Processing. POS transaction data shall be processed and reflected in the dashboard within sixty (60) minutes of receipt.')
  para('2.4 Incident Response Times:')
  const tw = [40, 70, 60]
  tableRow(['Severity', 'Description', 'Response Time'], tw, true)
  tableRow(['Critical (P1)', 'Complete service outage or data loss', '1 hour'], tw)
  tableRow(['High (P2)', 'Major feature unavailable', '4 hours'], tw)
  tableRow(['Medium (P3)', 'Minor feature degradation', '1 business day'], tw)
  tableRow(['Low (P4)', 'Cosmetic or informational', '3 business days'], tw)
  y += 3

  // 3. Fees
  heading('3. FEES AND PAYMENT')
  para(`3.1 Monthly Service Fee. The Client shall pay a monthly service fee of ${formatCad(input.monthlyPriceCad)} (plus applicable taxes) for the Services described herein.`)
  para(input.setupFeeCad > 0
    ? `3.2 Setup Fee. A one-time setup fee of ${formatCad(input.setupFeeCad)} (plus applicable taxes) is payable upon execution of this Agreement.`
    : '3.2 Setup Fee. No setup fee is applicable under this Agreement.')
  para('3.3 Payment Terms. All invoices are due and payable within thirty (30) days. Payments shall be made in Canadian Dollars (CAD).')
  para('3.4 Taxes. All fees are exclusive of applicable federal and provincial taxes (GST/HST/QST).')
  para('3.5 Late Payment. Overdue invoices shall bear interest at 1.5% per month (18% per annum) or the maximum rate permitted by law.')

  // 4. Term
  heading('4. TERM AND TERMINATION')
  para(`4.1 Initial Term. This Agreement shall commence on ${effectiveDate} and continue for twelve (12) months.`)
  para('4.2 Renewal. Following the Initial Term, this Agreement auto-renews for successive twelve (12) month periods unless either party provides thirty (30) days written notice of non-renewal.')
  para('4.3 Termination for Cause. Either party may terminate immediately upon written notice if the other party commits a material breach and fails to cure within thirty (30) days.')
  para('4.4 Effect of Termination. Upon termination, the Provider shall cease all Services, provide Client data in electronic format within thirty (30) days, and securely delete all Client data within sixty (60) days.')

  // 5. IP
  heading('5. INTELLECTUAL PROPERTY')
  para("5.1 Client Data. The Client retains all right, title, and interest in and to all data provided by the Client or generated through the Client's use of the Services.")
  para('5.2 Provider IP. The Provider retains all right, title, and interest in and to the Services, including all AI models, algorithms, software, and analytics methodologies.')
  para('5.3 Aggregated Data. The Provider may use anonymized and aggregated Client Data for improving the Services, provided it cannot identify the Client or any individual.')

  // 6. Confidentiality
  heading('6. CONFIDENTIALITY')
  para('6.1 Each party agrees to maintain the confidentiality of all information received from the other party that is identified as confidential or that a reasonable person would understand to be confidential.')
  para('6.2 Confidential information shall not be disclosed to any third party without prior written consent, except as required by law.')
  para('6.3 The obligations of confidentiality shall survive termination for three (3) years.')

  // 7. Liability
  heading('7. LIMITATION OF LIABILITY')
  para('7.1 NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF THIS AGREEMENT.')
  para('7.2 THE TOTAL AGGREGATE LIABILITY OF EITHER PARTY SHALL NOT EXCEED THE TOTAL FEES PAID OR PAYABLE DURING THE TWELVE (12) MONTH PERIOD PRECEDING THE CLAIM.')
  para('7.3 This limitation does not apply to breaches of confidentiality, data protection obligations, or willful misconduct.')

  // 8. Privacy
  heading('8. DATA PROTECTION & PRIVACY COMPLIANCE')
  para('8.1 PIPEDA Compliance. The Provider shall comply with the Personal Information Protection and Electronic Documents Act (PIPEDA) and all applicable provincial privacy legislation.')
  para('8.2 Data Collection. The Provider shall collect only such personal information as is reasonably necessary for the Services.')
  para('8.3 Data Security. The Provider shall implement reasonable administrative, technical, and physical safeguards to protect personal information.')
  para('8.4 Breach Notification. In the event of a breach of security safeguards, the Provider shall notify the Client and the Office of the Privacy Commissioner of Canada.')
  para('8.5 Data Retention. Personal information shall be retained only for so long as reasonably necessary or as required by applicable law.')

  if (isQuebec(input.province)) {
    subheading('8A. QUEBEC LAW 25 — ADDITIONAL OBLIGATIONS')
    para("8A.1 The Provider designates a person responsible for the protection of personal information in accordance with Quebec's Act respecting the protection of personal information in the private sector (Quebec Law 25).")
    para('8A.2 Before implementing any new system involving personal information of Quebec residents, the Provider shall conduct a Privacy Impact Assessment (PIA).')
    para('8A.3 The Provider shall publish a clear privacy policy describing collection, purposes, rights, and retention periods.')
    para("8A.4 The Provider shall, upon request, cease disseminating personal information and de-index any hyperlink attached to that individual's name, in accordance with Law 25.")
    para('8A.5 Transfers of personal information outside Quebec shall require a privacy impact assessment ensuring adequate protection in the receiving jurisdiction.')
    para("8A.6 Confidentiality incidents involving Quebec residents shall be reported to the Commission d'accès à l'information du Québec (CAI) and to affected individuals.")
  }

  // 9. General
  heading('9. GENERAL PROVISIONS')
  para('9.1 Governing Law. This Agreement shall be governed by the laws of the Province of ' + input.province + ' and the federal laws of Canada.')
  para('9.2 Entire Agreement. This Agreement constitutes the entire agreement between the parties and supersedes all prior agreements.')
  para('9.3 Amendment. This Agreement may be amended only by written instrument signed by both parties.')
  para('9.4 Assignment. Neither party may assign without prior written consent, except in connection with a merger or acquisition.')
  para('9.5 Force Majeure. Neither party shall be liable for failures due to circumstances beyond reasonable control.')
  para('9.6 Severability. If any provision is held invalid, the remaining provisions continue in full force.')

  // Signature page
  newPage()
  y = 35
  doc.setFontSize(14)
  doc.setFont('helvetica', 'bold')
  setColor(ACCENT)
  doc.text('SIGNATURES', PAGE_W / 2, y, { align: 'center' })
  y += 8
  para('IN WITNESS WHEREOF, the parties have executed this Service Level Agreement as of the date first written above.')

  // Provider signature box
  y += 8
  setFillColor(CARD)
  setDrawColor(BORDER)
  doc.roundedRect(MARGIN, y, CONTENT_W, 48, 2, 2, 'FD')
  y += 8
  doc.setFontSize(8)
  doc.setFont('helvetica', 'bold')
  setColor(MUTED)
  doc.text('PROVIDER — MERIDIAN AI BUSINESS SOLUTIONS', MARGIN + 5, y)
  y += 12
  doc.setFontSize(16)
  doc.setFont('times', 'italic')
  setColor(ACCENT)
  doc.text('Aidan Pierce', MARGIN + 5, y)
  y += 6
  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  setColor(MUTED)
  doc.text('Founder & CEO', MARGIN + 5, y)
  y += 5
  doc.text(`Date: ${today}`, MARGIN + 5, y)
  y += 10
  setDrawColor(ACCENT)
  doc.setLineWidth(0.2)
  doc.line(MARGIN + 5, y, MARGIN + CONTENT_W - 5, y)
  y += 10

  // Client signature box
  y += 5
  setFillColor(CARD)
  setDrawColor(input.clientSignature ? ACCENT : BORDER)
  doc.roundedRect(MARGIN, y, CONTENT_W, 48, 2, 2, 'FD')
  y += 8
  doc.setFontSize(8)
  doc.setFont('helvetica', 'bold')
  setColor(MUTED)
  doc.text(`CLIENT — ${input.clientCompanyName.toUpperCase()}`, MARGIN + 5, y)
  y += 12
  if (input.clientSignature) {
    doc.setFontSize(16)
    doc.setFont('times', 'italic')
    setColor(TEXT)
    doc.text(input.clientSignature, MARGIN + 5, y)
    y += 6
    doc.setFontSize(8)
    doc.setFont('helvetica', 'normal')
    setColor(MUTED)
    doc.text('Authorized Signatory', MARGIN + 5, y)
    y += 5
    doc.text(`Date: ${today}`, MARGIN + 5, y)
  } else {
    doc.setFontSize(9)
    doc.setFont('helvetica', 'italic')
    setColor(MUTED)
    doc.text('Awaiting client signature...', MARGIN + 5, y)
    y += 10
    setDrawColor(MUTED)
    doc.setLineWidth(0.2)
    doc.line(MARGIN + 5, y, MARGIN + CONTENT_W - 5, y)
    y += 5
    doc.setFontSize(7)
    doc.text('Authorized Signatory                                                        Date', MARGIN + 5, y)
  }
  y += 14

  // Footer
  doc.setFontSize(7)
  doc.setFont('helvetica', 'italic')
  setColor(MUTED)
  doc.text(`Sales Representative: ${input.repName}`, MARGIN, y)

  return doc.output('blob')
}
