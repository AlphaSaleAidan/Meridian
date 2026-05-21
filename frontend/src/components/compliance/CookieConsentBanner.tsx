import { useState, useEffect } from 'react'

const STORAGE_KEY = 'meridian_cookie_consent'

type ConsentLevel = 'all' | 'essential' | null

function getStoredConsent(): ConsentLevel {
  try {
    const val = localStorage.getItem(STORAGE_KEY)
    if (val === 'all' || val === 'essential') return val
  } catch { /* SSR or private browsing */ }
  return null
}

function isQuebecLocale(): boolean {
  try {
    const lang = navigator.language || ''
    // fr-CA is the most common Quebec browser locale
    if (lang.toLowerCase().startsWith('fr-ca')) return true
    // Also check if the app context has province = QC
    const org = localStorage.getItem('meridian_org')
    if (org) {
      const parsed = JSON.parse(org)
      if (parsed?.province?.toUpperCase() === 'QC') return true
    }
  } catch { /* ignore */ }
  return false
}

export default function CookieConsentBanner() {
  const [consent, setConsent] = useState<ConsentLevel>(getStoredConsent)
  const [isQuebec] = useState(isQuebecLocale)

  useEffect(() => {
    // Re-check on mount in case localStorage was updated
    setConsent(getStoredConsent())
  }, [])

  if (consent !== null) return null

  const handleAcceptAll = () => {
    localStorage.setItem(STORAGE_KEY, 'all')
    setConsent('all')
  }

  const handleEssentialOnly = () => {
    localStorage.setItem(STORAGE_KEY, 'essential')
    setConsent('essential')
  }

  return (
    <div className="fixed bottom-0 inset-x-0 z-50 p-4">
      <div className="mx-auto max-w-3xl rounded-xl border border-zinc-700 bg-zinc-900 p-5 shadow-2xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-zinc-300 leading-relaxed">
            <p className="font-medium text-white mb-1">Cookie Preferences</p>
            <p>
              We use essential cookies for authentication.
              {isQuebec ? (
                ' We would also like to use analytics cookies to improve our service. Your explicit consent is required.'
              ) : (
                ' We also use analytics cookies to improve our service.'
              )}
            </p>
          </div>
          <div className="flex shrink-0 gap-3">
            <button
              onClick={handleEssentialOnly}
              className="rounded-lg border border-zinc-600 px-4 py-2 text-sm font-medium text-zinc-300 transition-colors hover:border-zinc-500 hover:text-white"
            >
              Essential Only
            </button>
            <button
              onClick={handleAcceptAll}
              className="rounded-lg bg-[#1A8FD6] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#1A8FD6]/90"
            >
              Accept All
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/** Check if analytics cookies are allowed */
export function hasAnalyticsConsent(): boolean {
  return getStoredConsent() === 'all'
}
