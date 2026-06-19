// Consent-gated Google Analytics 4 loader.
//
// Compliance-first by design: gtag.js is NEVER loaded until the visitor has explicitly
// accepted analytics cookies (consent === 'all'). This satisfies Quebec Law 25's
// "no non-essential tracking before explicit consent" requirement. Reads the Measurement
// ID from VITE_GA4_ID at build time — if unset, this is a complete no-op.

const CONSENT_KEY = 'meridian_cookie_consent'
export const CONSENT_EVENT = 'meridian-consent-changed'

let loaded = false

function hasAnalyticsConsent(): boolean {
  try {
    return localStorage.getItem(CONSENT_KEY) === 'all'
  } catch {
    return false
  }
}

/**
 * Load GA4 if (and only if) a Measurement ID is configured AND the visitor has
 * consented to analytics. Safe to call multiple times — it loads at most once.
 * Call on app mount and again whenever consent changes.
 */
export function loadGA4(): void {
  if (loaded) return
  const id = import.meta.env.VITE_GA4_ID as string | undefined
  if (!id) return
  if (!hasAnalyticsConsent()) return
  loaded = true

  const s = document.createElement('script')
  s.async = true
  s.src = `https://www.googletagmanager.com/gtag/js?id=${id}`
  document.head.appendChild(s)

  const w = window as unknown as { dataLayer: unknown[]; gtag: (...args: unknown[]) => void }
  w.dataLayer = w.dataLayer || []
  w.gtag = function gtag() { w.dataLayer.push(arguments) }
  w.gtag('js', new Date())
  // anonymize_ip + denied ad signals — analytics only, no advertising personalization.
  w.gtag('config', id, { anonymize_ip: true, allow_google_signals: false, allow_ad_personalization_signals: false })
}
