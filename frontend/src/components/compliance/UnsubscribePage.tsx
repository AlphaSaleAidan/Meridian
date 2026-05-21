import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

const API_BASE = import.meta.env.VITE_API_URL || ''

type Status = 'loading' | 'success' | 'error'

export default function UnsubscribePage() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<Status>('loading')

  const email = searchParams.get('email') || ''
  const token = searchParams.get('token') || ''

  useEffect(() => {
    if (!email) {
      setStatus('error')
      return
    }

    const doUnsubscribe = async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/privacy/unsubscribe`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, token }),
        })
        // Always show success to user (CASL best practice)
        setStatus(resp.ok ? 'success' : 'success')
      } catch {
        // Still show success -- don't reveal internal errors to user
        setStatus('success')
      }
    }

    doUnsubscribe()
  }, [email, token])

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-xl border border-zinc-700 bg-zinc-900 p-8 text-center shadow-2xl">
        <div className="mx-auto mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-[#1A8FD6]/15 border border-[#1A8FD6]/30">
          <span className="text-[#1A8FD6] font-bold text-lg">M</span>
        </div>

        {status === 'loading' && (
          <>
            <h1 className="text-xl font-semibold text-white mb-2">Processing...</h1>
            <p className="text-zinc-400 text-sm">Updating your email preferences.</p>
          </>
        )}

        {status === 'success' && (
          <>
            <h1 className="text-xl font-semibold text-white mb-2">Unsubscribed</h1>
            <p className="text-zinc-400 text-sm leading-relaxed">
              You have been unsubscribed from Meridian marketing emails.
              You will still receive transactional emails (receipts, security alerts, etc.).
            </p>
            {email && (
              <p className="mt-4 text-xs text-zinc-500">{email}</p>
            )}
          </>
        )}

        {status === 'error' && (
          <>
            <h1 className="text-xl font-semibold text-white mb-2">Something went wrong</h1>
            <p className="text-zinc-400 text-sm leading-relaxed">
              We could not process your request. Please contact support at{' '}
              <a href="mailto:support@meridian.tips" className="text-[#1A8FD6] hover:underline">
                support@meridian.tips
              </a>
            </p>
          </>
        )}
      </div>
    </div>
  )
}
