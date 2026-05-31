// Minimal RFC 4180–ish CSV parser. Handles:
//   - Quoted fields containing commas and embedded newlines
//   - Doubled-quote escape inside quoted fields ("He said ""hi""")
//   - LF and CRLF line endings
// Does NOT handle: custom delimiters, BOM, header inference. Callers do that.
export function parseCsv(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let inQuotes = false
  let i = 0
  const len = text.length

  while (i < len) {
    const ch = text[i]

    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"'
          i += 2
          continue
        }
        inQuotes = false
        i++
        continue
      }
      field += ch
      i++
      continue
    }

    if (ch === '"') {
      inQuotes = true
      i++
      continue
    }
    if (ch === ',') {
      row.push(field)
      field = ''
      i++
      continue
    }
    if (ch === '\r') {
      // Swallow a following \n so CRLF is one line break, not two.
      if (text[i + 1] === '\n') i++
      row.push(field)
      rows.push(row)
      row = []
      field = ''
      i++
      continue
    }
    if (ch === '\n') {
      row.push(field)
      rows.push(row)
      row = []
      field = ''
      i++
      continue
    }
    field += ch
    i++
  }

  // Flush trailing field/row (no terminating newline).
  if (field.length > 0 || row.length > 0) {
    row.push(field)
    rows.push(row)
  }

  // Drop trailing fully-empty rows from a trailing newline.
  while (rows.length > 0 && rows[rows.length - 1].every(c => c === '')) rows.pop()

  return rows
}
