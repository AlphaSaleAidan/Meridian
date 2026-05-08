/**
 * Email service — sends email via the Meridian backend (Postal).
 *
 * Previously called Resend directly from the browser. Now all email
 * goes through POST /api/email/send which routes to Postal.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''

interface SendResult {
  status: string
  message_id?: string
}

async function sendEmail(
  template: string,
  to: string,
  firstName: string,
  extra: Record<string, string> = {},
  portal: string = 'us',
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/email/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template, to, first_name: firstName, portal, extra }),
    })
    if (!res.ok) {
      console.warn('[Email] API error:', res.status)
      return false
    }
    const data: SendResult = await res.json()
    return data.status === 'sent'
  } catch {
    console.error('[Email] Failed to send:', template)
    return false
  }
}

export const onboardingEmails = {
  async welcome(to: string, repName: string): Promise<boolean> {
    return sendEmail('welcome', to, repName.split(' ')[0])
  },

  async reminder48h(to: string, repName: string): Promise<boolean> {
    return sendEmail('onboarding_reminder', to, repName.split(' ')[0], {}, 'canada')
  },

  async complete(to: string, repName: string): Promise<boolean> {
    return sendEmail('onboarding_complete', to, repName.split(' ')[0], {}, 'canada')
  },
}
