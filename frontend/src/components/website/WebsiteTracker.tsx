import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface WebsiteTrackerProps {
  websiteId: string
  merchantId: string
}

function getDeviceType(): 'mobile' | 'tablet' | 'desktop' {
  const w = window.innerWidth
  if (w < 768) return 'mobile'
  if (w < 1024) return 'tablet'
  return 'desktop'
}

export default function WebsiteTracker({ websiteId, merchantId }: WebsiteTrackerProps) {
  const [searchParams] = useSearchParams()
  const startTime = useRef(Date.now())
  const sentPageview = useRef(false)

  useEffect(() => {
    if (sentPageview.current) return
    sentPageview.current = true

    const utmSource = searchParams.get('utm_source') || undefined
    const utmMedium = searchParams.get('utm_medium') || undefined
    const utmCampaign = searchParams.get('utm_campaign') || undefined
    const utmTerm = searchParams.get('utm_term') || undefined
    const utmContent = searchParams.get('utm_content') || undefined

    const payload = {
      website_id: websiteId,
      merchant_id: merchantId,
      event: 'pageview',
      url: window.location.href,
      referrer: document.referrer || undefined,
      device_type: getDeviceType(),
      user_agent: navigator.userAgent,
      screen_width: window.screen.width,
      screen_height: window.screen.height,
      timestamp: new Date().toISOString(),
      utm_source: utmSource,
      utm_medium: utmMedium,
      utm_campaign: utmCampaign,
      utm_term: utmTerm,
      utm_content: utmContent,
    }

    fetch(`${API_BASE}/api/website/analytics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).catch(() => {
      /* Analytics failures are silent — never block the page */
    })
  }, [websiteId, merchantId, searchParams])

  useEffect(() => {
    const start = startTime.current

    const sendDuration = () => {
      const duration = Math.round((Date.now() - start) / 1000)
      const payload = JSON.stringify({
        website_id: websiteId,
        merchant_id: merchantId,
        event: 'duration',
        duration_seconds: duration,
        timestamp: new Date().toISOString(),
      })

      if (navigator.sendBeacon) {
        navigator.sendBeacon(
          `${API_BASE}/api/website/analytics`,
          new Blob([payload], { type: 'application/json' }),
        )
      } else {
        fetch(`${API_BASE}/api/website/analytics`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
          keepalive: true,
        }).catch(() => {})
      }
    }

    window.addEventListener('beforeunload', sendDuration)
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') sendDuration()
    })

    return () => {
      window.removeEventListener('beforeunload', sendDuration)
      sendDuration()
    }
  }, [websiteId, merchantId])

  return null
}
