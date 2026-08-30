// jsPDF (~592KB) is lazy-imported inside generateSchedulePdf so it loads only
// when someone actually exports a schedule — not eagerly in the route chunk.
// ponytail: same treatment as generate-invoice-pdf(-us).ts.
import type { jsPDF } from 'jspdf'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const MARGIN = 15
// Print-friendly palette: white paper, dark ink, light gray grid, accent header
const CARD = '#ffffff'
const HEADER_FILL = '#eaf2f8'
const BORDER = '#d4dad6'
const ACCENT = '#1A8FD6'
const TEXT = '#1f2523'
const MUTED = '#6b7a74'

function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

function formatWeekRange(start: Date): string {
  const end = addDays(start, 6)
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' }
  return `${start.toLocaleDateString('en-US', opts)} – ${end.toLocaleDateString('en-US', opts)}`
}

function setColor(doc: jsPDF, hex: string) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  doc.setTextColor(r, g, b)
}

function setFillColor(doc: jsPDF, hex: string) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  doc.setFillColor(r, g, b)
}

function setDrawColor(doc: jsPDF, hex: string) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  doc.setDrawColor(r, g, b)
}

export interface SchedulePdfInput {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  weekStartDate: Date
  businessName?: string
}

export async function generateSchedulePdf(input: SchedulePdfInput): Promise<Blob> {
  const { shifts, staff, weekStartDate, businessName } = input
  const { jsPDF } = await import('jspdf')
  const doc = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'landscape' })
  const pageW = 297
  const pageH = 210
  const contentW = pageW - MARGIN * 2

  const staffMap = new Map<string, ScheduleStaffMember>()
  staff.forEach(s => staffMap.set(s.id, s))

  // Assigned, non-recommended shifts
  const realShifts = shifts.filter(s => !s.isRecommended && s.staffMemberId)
  // Unassigned (open) shifts still belong on the printed week
  const openShifts = shifts.filter(s => !s.isRecommended && !s.staffMemberId)

  // Unique staff that have shifts
  const staffWithShifts = staff.filter(s =>
    realShifts.some(sh => sh.staffMemberId === s.id)
  )

  // Header
  let y = 14
  if (businessName) {
    doc.setFontSize(20)
    doc.setFont('helvetica', 'bold')
    setColor(doc, TEXT)
    doc.text(businessName, pageW / 2, y, { align: 'center' })
    y += 8
  }
  doc.setFontSize(14)
  doc.setFont('helvetica', 'bold')
  setColor(doc, ACCENT)
  doc.text(`Weekly Schedule — ${formatWeekRange(weekStartDate)}`, pageW / 2, y, { align: 'center' })

  y += 10

  // Table dimensions
  const nameColW = 30
  const dayColW = (contentW - nameColW) / 7
  const rowH = 9
  const headerH = 8

  // Table header — day names (redrawn at the top of every page)
  function drawDayHeader(headerY: number): number {
    let hx = MARGIN
    setFillColor(doc, HEADER_FILL)
    setDrawColor(doc, BORDER)
    doc.rect(hx, headerY, nameColW, headerH, 'FD')
    doc.setFontSize(7)
    doc.setFont('helvetica', 'bold')
    setColor(doc, MUTED)
    doc.text('Staff', hx + 2, headerY + 5.5)

    hx += nameColW
    for (let d = 0; d < 7; d++) {
      setFillColor(doc, HEADER_FILL)
      doc.rect(hx, headerY, dayColW, headerH, 'FD')
      setColor(doc, ACCENT)
      const dayDate = addDays(weekStartDate, d)
      const label = `${DAY_NAMES[d].slice(0, 3)} ${dayDate.getDate()}`
      doc.text(label, hx + dayColW / 2, headerY + 5.5, { align: 'center' })
      hx += dayColW
    }
    return headerY + headerH
  }

  y = drawDayHeader(y)

  // Page break — start a new page and repeat the day-column header
  function breakPageIfNeeded() {
    if (y + rowH > pageH - 20) {
      doc.addPage()
      y = drawDayHeader(MARGIN)
    }
  }

  // One grid row: name cell + 7 day cells
  function drawRow(name: string, shiftsForDay: (d: number) => string) {
    breakPageIfNeeded()

    let x = MARGIN
    setFillColor(doc, CARD)
    setDrawColor(doc, BORDER)
    doc.rect(x, y, nameColW, rowH, 'FD')
    doc.setFontSize(7)
    doc.setFont('helvetica', 'bold')
    setColor(doc, TEXT)
    doc.text(name, x + 2, y + 6)

    x += nameColW
    for (let d = 0; d < 7; d++) {
      setFillColor(doc, CARD)
      doc.rect(x, y, dayColW, rowH, 'FD')

      const label = shiftsForDay(d)
      if (label) {
        doc.setFontSize(6.5)
        doc.setFont('helvetica', 'normal')
        setColor(doc, TEXT)
        doc.text(label, x + dayColW / 2, y + 6, { align: 'center' })
      }

      x += dayColW
    }

    y += rowH
  }

  // Staff rows
  const staffList = staffWithShifts.length > 0 ? staffWithShifts : staff
  for (const member of staffList) {
    drawRow(member.name, d =>
      realShifts
        .filter(s => s.staffMemberId === member.id && s.dayOfWeek === d)
        .map(s => `${s.startTime}–${s.endTime}`)
        .join(', ')
    )
  }

  // Open (unassigned) shifts — skip the row when there are none
  if (openShifts.length > 0) {
    drawRow('Open shifts', d =>
      openShifts
        .filter(s => s.dayOfWeek === d)
        .map(s => `${s.startTime}–${s.endTime} (${s.role.replace(/_/g, ' ')})`)
        .join(', ')
    )
  }

  // Footer
  const footerY = pageH - 10
  const generatedDate = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  const footerText = businessName
    ? `${businessName} • Generated ${generatedDate}`
    : `Generated ${generatedDate} by Meridian`
  doc.setFontSize(7)
  doc.setFont('helvetica', 'italic')
  setColor(doc, MUTED)
  doc.text(footerText, pageW / 2, footerY, { align: 'center' })

  return doc.output('blob')
}
