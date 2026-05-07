const RESEND_API_URL = 'https://api.resend.com/emails'

interface EmailPayload {
  to: string
  subject: string
  html: string
}

async function sendEmail(payload: EmailPayload): Promise<boolean> {
  const apiKey = import.meta.env.VITE_RESEND_API_KEY
  if (!apiKey) {
    console.warn('[Email] No RESEND_API_KEY configured — email not sent:', payload.subject)
    return false
  }

  try {
    const res = await fetch(RESEND_API_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'Meridian Canada <onboarding@meridian.tips>',
        to: [payload.to],
        subject: payload.subject,
        html: payload.html,
      }),
    })
    return res.ok
  } catch {
    console.error('[Email] Failed to send:', payload.subject)
    return false
  }
}

function baseTemplate(content: string): string {
  return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0A0A0B;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:560px;margin:0 auto;padding:40px 24px;">
<div style="text-align:center;margin-bottom:32px;">
<div style="display:inline-block;width:36px;height:36px;border-radius:8px;background:#00d4aa22;border:1px solid #00d4aa44;line-height:36px;text-align:center;">
<span style="color:#00d4aa;font-weight:bold;font-size:16px;">M</span>
</div>
<p style="color:#F5F5F7;font-size:18px;font-weight:700;margin:12px 0 0;">Meridian Canada</p>
</div>
<div style="background:#0f1512;border:1px solid #1a2420;border-radius:12px;padding:32px;">
${content}
</div>
<p style="text-align:center;color:#4a5550;font-size:10px;margin-top:24px;">
Meridian POS Intelligence &middot; Canada Sales Team
</p>
</div>
</body>
</html>`
}

export const onboardingEmails = {
  async welcome(to: string, repName: string): Promise<boolean> {
    const firstName = repName.split(' ')[0]
    return sendEmail({
      to,
      subject: `Welcome to Meridian, ${firstName}!`,
      html: baseTemplate(`
        <h2 style="color:#F5F5F7;font-size:20px;margin:0 0 12px;">Welcome aboard, ${firstName}!</h2>
        <p style="color:#6b7a74;font-size:14px;line-height:1.6;margin:0 0 20px;">
          You've been added to the Meridian Canada sales team. Here's what to do next:
        </p>
        <div style="background:#0a0f0d;border-radius:8px;padding:16px;margin-bottom:16px;">
          <p style="color:#F5F5F7;font-size:13px;margin:0 0 8px;"><strong>1.</strong> Complete your onboarding checklist</p>
          <p style="color:#F5F5F7;font-size:13px;margin:0 0 8px;"><strong>2.</strong> Go through the training modules</p>
          <p style="color:#F5F5F7;font-size:13px;margin:0;"><strong>3.</strong> Add your first lead</p>
        </div>
        <a href="https://meridian.tips/canada/portal/onboarding" style="display:inline-block;background:#00d4aa;color:#0a0f0d;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
          Start Onboarding
        </a>
      `),
    })
  },

  async reminder48h(to: string, repName: string): Promise<boolean> {
    const firstName = repName.split(' ')[0]
    return sendEmail({
      to,
      subject: `${firstName}, finish your Meridian setup`,
      html: baseTemplate(`
        <h2 style="color:#F5F5F7;font-size:20px;margin:0 0 12px;">Don't forget to finish setup</h2>
        <p style="color:#6b7a74;font-size:14px;line-height:1.6;margin:0 0 20px;">
          Hey ${firstName}, it looks like you haven't completed your onboarding yet.
          Finishing setup takes about 5 minutes and unlocks your full sales dashboard.
        </p>
        <a href="https://meridian.tips/canada/portal/onboarding" style="display:inline-block;background:#00d4aa;color:#0a0f0d;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
          Complete Onboarding
        </a>
        <p style="color:#4a5550;font-size:12px;margin:20px 0 0;">
          Questions? Reply to this email or ask your manager.
        </p>
      `),
    })
  },

  async complete(to: string, repName: string): Promise<boolean> {
    const firstName = repName.split(' ')[0]
    return sendEmail({
      to,
      subject: `You're all set, ${firstName}!`,
      html: baseTemplate(`
        <h2 style="color:#F5F5F7;font-size:20px;margin:0 0 12px;">Onboarding Complete!</h2>
        <p style="color:#6b7a74;font-size:14px;line-height:1.6;margin:0 0 20px;">
          Nice work, ${firstName}! You've completed your onboarding and you're ready to start selling.
        </p>
        <div style="background:#0a0f0d;border-radius:8px;padding:16px;margin-bottom:16px;">
          <p style="color:#00d4aa;font-size:13px;font-weight:600;margin:0 0 8px;">Next steps:</p>
          <p style="color:#F5F5F7;font-size:13px;margin:0 0 6px;">&bull; Review your training modules</p>
          <p style="color:#F5F5F7;font-size:13px;margin:0 0 6px;">&bull; Add prospects to your pipeline</p>
          <p style="color:#F5F5F7;font-size:13px;margin:0;">&bull; Book your first demo</p>
        </div>
        <a href="https://meridian.tips/canada/portal/dashboard" style="display:inline-block;background:#00d4aa;color:#0a0f0d;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
          Go to Dashboard
        </a>
      `),
    })
  },
}
