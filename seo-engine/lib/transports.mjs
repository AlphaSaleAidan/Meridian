// Message transports for the SEO daily report.
// No secrets in code — everything reads from environment variables.
// Supported: Telegram (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID), Email via Resend
// (RESEND_API_KEY + REPORT_EMAIL_TO + REPORT_EMAIL_FROM). If neither is configured,
// the caller should fall back to dry-run (print to stdout).

export function configuredTransports(env = process.env) {
  const out = []
  if (env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_CHAT_ID) out.push('telegram')
  if (env.RESEND_API_KEY && env.REPORT_EMAIL_TO && env.REPORT_EMAIL_FROM) out.push('email')
  return out
}

export async function sendTelegram(text, env = process.env) {
  const token = env.TELEGRAM_BOT_TOKEN
  const chatId = env.TELEGRAM_CHAT_ID
  if (!token || !chatId) throw new Error('Telegram not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)')
  const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'Markdown',
      disable_web_page_preview: true,
    }),
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`Telegram send failed: ${res.status} ${body}`)
  }
  return res.json()
}

export async function sendEmail(subject, textBody, htmlBody, env = process.env) {
  const key = env.RESEND_API_KEY
  const to = env.REPORT_EMAIL_TO
  const from = env.REPORT_EMAIL_FROM
  if (!key || !to || !from) throw new Error('Email not configured (RESEND_API_KEY / REPORT_EMAIL_TO / REPORT_EMAIL_FROM)')
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from,
      to: to.split(',').map(s => s.trim()),
      subject,
      text: textBody,
      html: htmlBody || `<pre style="font:14px/1.5 ui-monospace,monospace">${escapeHtml(textBody)}</pre>`,
    }),
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`Email send failed: ${res.status} ${body}`)
  }
  return res.json()
}

function escapeHtml(s) {
  return s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]))
}

// Deliver to all configured transports. Returns {sent:[], errors:[]}.
export async function deliver({ subject, text, html }, env = process.env) {
  const transports = configuredTransports(env)
  const sent = []
  const errors = []
  for (const t of transports) {
    try {
      if (t === 'telegram') { await sendTelegram(text, env); sent.push('telegram') }
      if (t === 'email') { await sendEmail(subject, text, html, env); sent.push('email') }
    } catch (e) {
      errors.push(`${t}: ${e.message}`)
    }
  }
  return { sent, errors, transports }
}
