// Rich HTML email for the Meridian SEO daily report.
// Table-based layout + inline styles for broad email-client compatibility (Gmail, Outlook,
// Apple Mail). Takes the same derived model the text report uses.

const BLUE = '#0066FF'
const TEAL = '#17C5B0'
const INK = '#0A0A0B'
const SLATE = '#5b6470'

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]))
}

function metricCard(value, label, accent) {
  return `
    <td width="25%" style="padding:6px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #ECEEF1;border-radius:12px;">
        <tr><td style="padding:16px 14px;text-align:center;">
          <div style="font:700 28px/1.1 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:${accent};">${esc(value)}</div>
          <div style="font:500 11px/1.3 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:${SLATE};margin-top:6px;text-transform:uppercase;letter-spacing:.04em;">${esc(label)}</div>
        </td></tr>
      </table>
    </td>`
}

function listBlock(title, items, opts = {}) {
  if (!items || !items.length) return ''
  const rows = items.map(it => `
    <tr><td style="padding:9px 0;border-bottom:1px solid #F1F3F5;">
      <span style="font:500 14px/1.4 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1A1D21;">${esc(it.title || it)}</span>
      ${it.pill ? `<span style="display:inline-block;margin-left:8px;font:600 10px/1 -apple-system,Arial,sans-serif;color:${opts.pillColor || TEAL};background:${(opts.pillColor || TEAL)}14;padding:4px 8px;border-radius:20px;text-transform:uppercase;letter-spacing:.04em;">${esc(it.pill)}</span>` : ''}
    </td></tr>`).join('')
  return `
    <tr><td style="padding:22px 28px 0;">
      <div style="font:700 13px/1.3 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:${INK};text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;">${esc(title)}</div>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">${rows}</table>
    </td></tr>`
}

function gscBlock(gsc) {
  if (!gsc) {
    return `<tr><td style="padding:22px 28px 0;">
      <div style="font:500 12px/1.5 -apple-system,Arial,sans-serif;color:${SLATE};background:#F7F8FA;border-radius:10px;padding:14px;">
        🔍 Search Console not wired yet — add the service-account key to start seeing impressions, clicks, and ranking positions here.</div></td></tr>`
  }
  if (gsc.error) {
    return `<tr><td style="padding:22px 28px 0;"><div style="font:500 12px/1.5 -apple-system,Arial,sans-serif;color:#B4541A;background:#FFF4EC;border-radius:10px;padding:14px;">⚠ Search Console: ${esc(gsc.error)}</div></td></tr>`
  }
  const queries = (gsc.topQueries || []).map(q => `
    <tr>
      <td style="padding:7px 0;border-bottom:1px solid #F1F3F5;font:500 13px/1.3 -apple-system,Arial,sans-serif;color:#1A1D21;">${esc(q.q)}</td>
      <td align="right" style="padding:7px 0;border-bottom:1px solid #F1F3F5;font:600 13px/1.3 -apple-system,Arial,sans-serif;color:${BLUE};white-space:nowrap;">pos ${esc(q.pos)}</td>
      <td align="right" style="padding:7px 0 7px 14px;border-bottom:1px solid #F1F3F5;font:500 13px/1.3 -apple-system,Arial,sans-serif;color:${SLATE};white-space:nowrap;">${esc(q.clicks)} clk</td>
    </tr>`).join('')
  return `
    <tr><td style="padding:22px 28px 0;">
      <div style="font:700 13px/1.3 -apple-system,Arial,sans-serif;color:${INK};text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;">Search Console · ${esc(gsc.window || '')}</div>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
        <tr>
          <td width="50%" style="padding:6px;"><table role="presentation" width="100%" style="background:${BLUE}0D;border-radius:10px;"><tr><td style="padding:14px;text-align:center;"><div style="font:700 22px -apple-system,Arial,sans-serif;color:${BLUE};">${esc(gsc.impressions)}</div><div style="font:500 11px -apple-system,Arial,sans-serif;color:${SLATE};margin-top:4px;">IMPRESSIONS</div></td></tr></table></td>
          <td width="50%" style="padding:6px;"><table role="presentation" width="100%" style="background:${TEAL}14;border-radius:10px;"><tr><td style="padding:14px;text-align:center;"><div style="font:700 22px -apple-system,Arial,sans-serif;color:${TEAL};">${esc(gsc.clicks)}</div><div style="font:500 11px -apple-system,Arial,sans-serif;color:${SLATE};margin-top:4px;">CLICKS</div></td></tr></table></td>
        </tr>
      </table>
      ${queries ? `<table role="presentation" width="100%" cellpadding="0" cellspacing="0">${queries}</table>` : ''}
    </td></tr>`
}

export function buildHtml(m) {
  const progress = m.queuedCount + m.publishedCount > 0
    ? Math.round((m.publishedCount / (m.queuedCount + m.publishedCount + m.awaitingReview.length)) * 100)
    : 0
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#EEF1F4;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#EEF1F4;padding:24px 12px;">
<tr><td align="center">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FBFCFD;border-radius:18px;overflow:hidden;box-shadow:0 1px 3px rgba(10,11,12,.08);">
    <!-- header -->
    <tr><td style="background:linear-gradient(120deg,${BLUE},${TEAL});padding:28px 28px 24px;">
      <div style="font:700 18px/1.2 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#ffffff;letter-spacing:-.01em;">Meridian — SEO Daily Report</div>
      <div style="font:500 13px -apple-system,Arial,sans-serif;color:#ffffffcc;margin-top:4px;">${esc(m.todayISO)}</div>
    </td></tr>
    <!-- metric cards -->
    <tr><td style="padding:16px 16px 0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
        ${metricCard(m.pages.total, 'Live Pages', INK)}
        ${metricCard(m.draftedToday.length, 'Drafted Today', BLUE)}
        ${metricCard(m.awaitingReview.length, 'Awaiting Review', '#B4541A')}
        ${metricCard(m.queuedCount, 'Backlog', TEAL)}
      </tr></table>
    </td></tr>
    <!-- progress bar -->
    <tr><td style="padding:14px 28px 0;">
      <div style="font:600 11px -apple-system,Arial,sans-serif;color:${SLATE};margin-bottom:6px;">PIPELINE PROGRESS · ${progress}% published</div>
      <div style="background:#E6E9ED;border-radius:99px;height:8px;overflow:hidden;"><div style="width:${progress}%;height:8px;background:linear-gradient(90deg,${BLUE},${TEAL});"></div></div>
    </td></tr>
    ${listBlock('New Drafts Today', m.draftedToday.map(i => ({ title: i.title, pill: i.status })), { pillColor: BLUE })}
    ${listBlock('Published Today', m.shippedToday.map(i => ({ title: i.title, pill: 'live' })), { pillColor: TEAL })}
    ${listBlock('Awaiting Your Review', m.awaitingReview.map(i => ({ title: i.title })))}
    ${listBlock('Scheduled Next', m.nextUp.map(i => ({ title: i.title })))}
    ${gscBlock(m.gsc)}
    <!-- footer -->
    <tr><td style="padding:26px 28px 28px;">
      <div style="border-top:1px solid #ECEEF1;padding-top:16px;font:500 12px/1.5 -apple-system,Arial,sans-serif;color:${SLATE};">
        Drafts await approval on branch <span style="font-family:monospace;color:#1A1D21;">feat/canada-compliance-seo</span> — nothing publishes to meridian.tips without your sign-off.
      </div>
    </td></tr>
  </table>
  <div style="font:500 11px -apple-system,Arial,sans-serif;color:#9AA2AC;margin-top:14px;">Meridian SEO Engine · automated daily</div>
</td></tr>
</table>
</body></html>`
}
