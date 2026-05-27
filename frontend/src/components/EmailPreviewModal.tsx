import { useState, useCallback, useEffect, useRef } from 'react'
import { X, Send, Loader2 } from 'lucide-react'

interface EmailPreviewModalProps {
  template: string
  firstName: string
  portal: 'us' | 'canada'
  onClose: () => void
  onSend: () => Promise<void>
}

const TEMPLATES: Record<string, { subject: string; body: (name: string, portal: string) => string }> = {
  welcome: {
    subject: 'Welcome to Meridian!',
    body: (name, portal) => `
      <h2 style="margin:0 0 16px;font-size:22px;color:#111">Welcome aboard, ${name}!</h2>
      <p style="margin:0 0 12px;color:#444;line-height:1.6">
        You've been added to the Meridian ${portal === 'canada' ? 'Canada' : 'US'} sales team.
        Your portal is ready and waiting for you.
      </p>
      <p style="margin:0 0 24px;color:#444;line-height:1.6">
        To start processing payments for your merchants, connect your Square account
        through the dashboard. This takes about 2 minutes.
      </p>
      <a style="display:inline-block;padding:12px 28px;background:#1A8FD6;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
        Connect Square Account
      </a>
      <p style="margin:24px 0 0;color:#888;font-size:13px;line-height:1.5">
        Need help? Reply to this email or reach out to your manager directly.
      </p>`,
  },
  onboarding_reminder: {
    subject: 'Finish setting up your Meridian account',
    body: (name) => `
      <h2 style="margin:0 0 16px;font-size:22px;color:#111">Hey ${name}, just a quick reminder</h2>
      <p style="margin:0 0 12px;color:#444;line-height:1.6">
        You started your Meridian onboarding but haven't connected your POS system yet.
        Completing this step unlocks your full dashboard and commission tracking.
      </p>
      <p style="margin:0 0 24px;color:#444;line-height:1.6">
        It only takes a couple of minutes to finish setup.
      </p>
      <a style="display:inline-block;padding:12px 28px;background:#1A8FD6;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
        Complete Setup
      </a>
      <p style="margin:24px 0 0;color:#888;font-size:13px;line-height:1.5">
        If you're having trouble, your manager can walk you through it.
      </p>`,
  },
  onboarding_complete: {
    subject: 'You\'re all set!',
    body: (name) => `
      <h2 style="margin:0 0 16px;font-size:22px;color:#111">Congratulations, ${name}!</h2>
      <p style="margin:0 0 12px;color:#444;line-height:1.6">
        Your onboarding is complete and your Meridian dashboard is fully active.
        You can now view leads, track commissions, and manage your pipeline.
      </p>
      <p style="margin:0 0 24px;color:#444;line-height:1.6">
        Start by reviewing your training materials and submitting your first lead.
        Every merchant you close earns you recurring monthly income.
      </p>
      <a style="display:inline-block;padding:12px 28px;background:#17C5B0;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
        Go to Dashboard
      </a>
      <p style="margin:24px 0 0;color:#888;font-size:13px;line-height:1.5">
        Welcome to the team. Let's close some deals.
      </p>`,
  },
}

export default function EmailPreviewModal({ template, firstName, portal, onClose, onSend }: EmailPreviewModalProps) {
  const [sending, setSending] = useState(false)
  const backdropRef = useRef<HTMLDivElement>(null)

  const handleSend = useCallback(async () => {
    setSending(true)
    try {
      await onSend()
    } finally {
      setSending(false)
    }
  }, [onSend])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const tpl = TEMPLATES[template] ?? TEMPLATES.welcome
  const subjectLine = tpl.subject
  const bodyHtml = tpl.body(firstName || 'there', portal)

  return (
    <div
      ref={backdropRef}
      onClick={e => { if (e.target === backdropRef.current) onClose() }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(6px)' }}
    >
      <div className="w-full max-w-lg rounded-xl overflow-hidden" style={{ background: '#111113', border: '1px solid #1F1F23' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: '1px solid #1F1F23' }}>
          <div>
            <p className="text-sm font-semibold" style={{ color: '#F5F5F7' }}>Email Preview</p>
            <p className="text-xs mt-0.5" style={{ color: '#A1A1A8' }}>
              Template: <span style={{ color: '#1A8FD6' }}>{template}</span>
            </p>
          </div>
          <button aria-label="Close email preview" onClick={onClose} className="p-1 rounded-md hover:bg-white/5 transition-colors" style={{ color: '#A1A1A8' }}>
            <X size={18} />
          </button>
        </div>

        {/* Subject line */}
        <div className="px-5 py-2.5" style={{ background: '#0A0A0B', borderBottom: '1px solid #1F1F23' }}>
          <p className="text-xs" style={{ color: '#A1A1A8' }}>
            Subject: <span className="font-medium" style={{ color: '#F5F5F7' }}>{subjectLine}</span>
          </p>
        </div>

        {/* Email body preview — white bg to look like a real email */}
        <div className="mx-5 my-4 rounded-lg overflow-hidden" style={{ border: '1px solid #ddd' }}>
          <div style={{ background: '#fff', padding: '28px 24px' }}>
            {/* Meridian logo header */}
            <div style={{ borderBottom: '2px solid #1A8FD6', paddingBottom: 16, marginBottom: 20, textAlign: 'center' as const }}>
              <span style={{ fontSize: 20, fontWeight: 700, color: '#111', letterSpacing: 1 }}>MERIDIAN</span>
              <span style={{ display: 'block', fontSize: 10, color: '#1A8FD6', fontWeight: 600, letterSpacing: 2, marginTop: 2 }}>
                AI BUSINESS SOLUTIONS
              </span>
            </div>
            {/* Template body */}
            <div dangerouslySetInnerHTML={{ __html: bodyHtml }} />
            {/* Footer */}
            <div style={{ borderTop: '1px solid #eee', marginTop: 28, paddingTop: 16, textAlign: 'center' as const }}>
              <p style={{ margin: 0, fontSize: 11, color: '#aaa' }}>
                Meridian AI Business Solutions
              </p>
              <p style={{ margin: '4px 0 0', fontSize: 11, color: '#ccc' }}>
                {portal === 'canada' ? 'Toronto, ON' : 'Miami, FL'}
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 px-5 py-3" style={{ borderTop: '1px solid #1F1F23' }}>
          <button
            onClick={onClose}
            disabled={sending}
            className="px-4 py-2 text-sm rounded-lg transition-colors"
            style={{ color: '#A1A1A8', border: '1px solid #1F1F23' }}
          >
            Cancel
          </button>
          <button
            onClick={handleSend}
            disabled={sending}
            className="flex items-center gap-1.5 px-5 py-2 text-sm font-semibold rounded-lg transition-all"
            style={{
              background: sending ? '#17C5B0aa' : '#17C5B0',
              color: '#0A0A0B',
              cursor: sending ? 'wait' : 'pointer',
            }}
          >
            {sending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            {sending ? 'Sending...' : 'Send Email'}
          </button>
        </div>
      </div>
    </div>
  )
}
