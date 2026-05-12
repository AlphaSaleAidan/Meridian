import jsPDF from 'jspdf'
import QRCode from 'qrcode'

export interface InvoiceInput {
  invoiceNumber: string
  businessName: string
  contactName: string
  contactEmail: string
  contactPhone?: string
  monthlyPrice: number
  setupFee?: number
  firstMonthFree?: boolean
  planName: string
  billingDate: string
  dueDate: string
  repName: string
  repEmail: string
  recurring: boolean
  invoiceUrl?: string
}

function formatCAD(cents: number): string {
  return `CA$${(cents / 100).toLocaleString('en-CA', { minimumFractionDigits: 2 })}`
}

function uid8(): string {
  return Math.random().toString(36).slice(2, 10).toUpperCase()
}

export function generateInvoiceNumber(): string {
  const now = new Date()
  const yy = String(now.getFullYear()).slice(2)
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  return `MCA-${yy}${mm}-${uid8()}`
}

export function generateInvoiceUrl(invoiceNumber: string): string {
  return `${window.location.origin}/canada/invoice/${encodeURIComponent(invoiceNumber)}`
}

export async function generateInvoicePdf(input: InvoiceInput): Promise<Blob> {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  const W = 210
  const margin = 20
  const contentW = W - margin * 2
  let y = margin

  const monthlyPriceCents = Math.round(input.monthlyPrice * 100)
  const setupFeeCents = Math.round((input.setupFee || 0) * 100)
  const invoiceUrl = input.invoiceUrl || generateInvoiceUrl(input.invoiceNumber)

  // Background
  doc.setFillColor(10, 15, 13)
  doc.rect(0, 0, 210, 297, 'F')

  // Header bar
  doc.setFillColor(15, 21, 18)
  doc.rect(0, 0, W, 45, 'F')

  // Logo text
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(22)
  doc.setTextColor(0, 212, 170)
  doc.text('MERIDIAN', margin, 18)

  doc.setFontSize(9)
  doc.setTextColor(107, 122, 116)
  doc.text('Canada', margin, 25)

  // Invoice title
  doc.setFontSize(14)
  doc.setTextColor(245, 245, 247)
  doc.text('INVOICE', W - margin, 18, { align: 'right' })

  doc.setFontSize(9)
  doc.setTextColor(107, 122, 116)
  doc.text(`#${input.invoiceNumber}`, W - margin, 25, { align: 'right' })

  if (input.recurring) {
    doc.setFontSize(7)
    doc.setTextColor(0, 212, 170)
    doc.text('RECURRING MONTHLY', W - margin, 32, { align: 'right' })
  }

  y = 55

  // Bill to / Invoice details
  doc.setFontSize(8)
  doc.setTextColor(0, 212, 170)
  doc.text('BILL TO', margin, y)
  doc.text('INVOICE DETAILS', W / 2 + 10, y)

  y += 6
  doc.setFontSize(10)
  doc.setTextColor(245, 245, 247)
  doc.text(input.businessName, margin, y)
  doc.text(`Date: ${input.billingDate}`, W / 2 + 10, y)

  y += 5
  doc.setFontSize(9)
  doc.setTextColor(170, 180, 175)
  doc.text(input.contactName, margin, y)
  doc.text(`Due: ${input.dueDate}`, W / 2 + 10, y)

  y += 5
  doc.text(input.contactEmail, margin, y)
  doc.text(`Rep: ${input.repName}`, W / 2 + 10, y)

  if (input.contactPhone) {
    y += 5
    doc.text(input.contactPhone, margin, y)
  }

  y += 12

  // Line items table header
  doc.setFillColor(26, 36, 32)
  doc.rect(margin, y, contentW, 8, 'F')
  doc.setFontSize(8)
  doc.setTextColor(107, 122, 116)
  doc.text('DESCRIPTION', margin + 3, y + 5.5)
  doc.text('QTY', margin + contentW - 55, y + 5.5, { align: 'right' })
  doc.text('RATE', margin + contentW - 30, y + 5.5, { align: 'right' })
  doc.text('AMOUNT', margin + contentW - 3, y + 5.5, { align: 'right' })

  y += 12

  // Monthly subscription line
  doc.setFontSize(9)
  doc.setTextColor(245, 245, 247)
  doc.text(`Meridian ${input.planName} — Monthly Subscription`, margin + 3, y)
  doc.setTextColor(170, 180, 175)
  doc.text('1', margin + contentW - 55, y, { align: 'right' })
  doc.text(formatCAD(monthlyPriceCents), margin + contentW - 30, y, { align: 'right' })

  if (input.firstMonthFree) {
    doc.setTextColor(0, 212, 170)
    doc.text('CA$0.00 (FREE)', margin + contentW - 3, y, { align: 'right' })
  } else {
    doc.setTextColor(245, 245, 247)
    doc.text(formatCAD(monthlyPriceCents), margin + contentW - 3, y, { align: 'right' })
  }

  y += 4
  doc.setFontSize(7)
  doc.setTextColor(107, 122, 116)
  doc.text(input.recurring ? 'Recurring monthly charge' : 'One-time charge', margin + 3, y)

  y += 8

  // Setup fee line (if applicable)
  if (setupFeeCents > 0) {
    doc.setFontSize(9)
    doc.setTextColor(245, 245, 247)
    doc.text('Setup & Onboarding Fee', margin + 3, y)
    doc.setTextColor(170, 180, 175)
    doc.text('1', margin + contentW - 55, y, { align: 'right' })
    doc.text(formatCAD(setupFeeCents), margin + contentW - 30, y, { align: 'right' })
    doc.setTextColor(245, 245, 247)
    doc.text(formatCAD(setupFeeCents), margin + contentW - 3, y, { align: 'right' })

    y += 4
    doc.setFontSize(7)
    doc.setTextColor(107, 122, 116)
    doc.text('One-time setup fee', margin + 3, y)

    y += 8
  }

  // Divider
  doc.setDrawColor(26, 36, 32)
  doc.line(margin, y, W - margin, y)
  y += 6

  // Totals
  const lineTotal = input.firstMonthFree ? 0 : monthlyPriceCents
  const subtotal = lineTotal + setupFeeCents
  const tax = Math.round(subtotal * 0.13)
  const total = subtotal + tax

  doc.setFontSize(9)
  doc.setTextColor(170, 180, 175)
  doc.text('Subtotal', margin + contentW - 45, y, { align: 'right' })
  doc.setTextColor(245, 245, 247)
  doc.text(formatCAD(subtotal), margin + contentW - 3, y, { align: 'right' })

  y += 6
  doc.setTextColor(170, 180, 175)
  doc.text('HST/GST (13%)', margin + contentW - 45, y, { align: 'right' })
  doc.setTextColor(245, 245, 247)
  doc.text(formatCAD(tax), margin + contentW - 3, y, { align: 'right' })

  y += 8
  doc.setFillColor(0, 212, 170)
  doc.rect(margin + contentW - 70, y - 4, 73, 10, 'F')
  doc.setFontSize(11)
  doc.setTextColor(10, 15, 13)
  doc.setFont('helvetica', 'bold')
  doc.text('Total Due', margin + contentW - 45, y + 2, { align: 'right' })
  doc.text(formatCAD(total), margin + contentW - 3, y + 2, { align: 'right' })

  y += 18

  // Recurring notice
  if (input.recurring) {
    doc.setFillColor(15, 21, 18)
    doc.roundedRect(margin, y, contentW, 14, 3, 3, 'F')
    doc.setFontSize(8)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(0, 212, 170)
    doc.text('RECURRING BILLING', margin + 5, y + 5)
    doc.setTextColor(170, 180, 175)
    doc.text(
      `This invoice will automatically recur on the ${ordinal(new Date(input.billingDate).getDate())} of each month. ` +
      `Next charge: ${formatCAD(monthlyPriceCents)} on ${nextMonth(input.billingDate)}.`,
      margin + 5, y + 10
    )
    y += 20
  }

  // QR Code
  try {
    const qrDataUrl = await QRCode.toDataURL(invoiceUrl, {
      width: 200,
      margin: 1,
      color: { dark: '#00d4aa', light: '#0a0f0d' },
    })
    const qrSize = 30
    const qrX = margin
    const qrY = y + 2
    doc.addImage(qrDataUrl, 'PNG', qrX, qrY, qrSize, qrSize)

    doc.setFontSize(8)
    doc.setTextColor(107, 122, 116)
    doc.text('Scan to view invoice online', margin + qrSize + 5, qrY + 10)
    doc.setFontSize(7)
    doc.setTextColor(74, 85, 80)
    doc.text(invoiceUrl, margin + qrSize + 5, qrY + 15, { maxWidth: contentW - qrSize - 10 })
  } catch {
    // QR generation failed — skip silently
  }

  // Footer
  const footerY = 280
  doc.setDrawColor(26, 36, 32)
  doc.line(margin, footerY - 5, W - margin, footerY - 5)
  doc.setFontSize(7)
  doc.setTextColor(74, 85, 80)
  doc.text('Meridian Intelligence Inc. — Canada', margin, footerY)
  doc.text(`Questions? Contact ${input.repName} at ${input.repEmail}`, margin, footerY + 4)
  doc.text('All prices in Canadian Dollars (CAD)', W - margin, footerY, { align: 'right' })

  return doc.output('blob')
}

function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

function nextMonth(dateStr: string): string {
  const d = new Date(dateStr)
  d.setMonth(d.getMonth() + 1)
  return d.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
}
