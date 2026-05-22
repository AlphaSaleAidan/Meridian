import { useState, useEffect } from 'react'
import { WifiOff } from 'lucide-react'

export default function OfflineBanner() {
  const [offline, setOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const goOffline = () => setOffline(true)
    const goOnline = () => setOffline(false)
    window.addEventListener('offline', goOffline)
    window.addEventListener('online', goOnline)
    return () => {
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online', goOnline)
    }
  }, [])

  if (!offline) return null

  return (
    <div className="flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium text-amber-400 bg-amber-500/10 border-b border-amber-500/20">
      <WifiOff size={14} />
      You're offline — some features may be limited
    </div>
  )
}
