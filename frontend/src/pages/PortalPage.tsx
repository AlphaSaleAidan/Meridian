import { useEffect, useRef, useState } from 'react'

/**
 * Full-screen iframe wrapper for the Meridian Sales Portal.
 * Lives at /portal on meridian.tips — feels native, no redirect.
 */
export default function PortalPage() {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    // Ensure the iframe fills the viewport
    const resize = () => {
      if (iframeRef.current) {
        iframeRef.current.style.height = `${window.innerHeight}px`
      }
    }
    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  return (
    <div className="w-full h-screen overflow-hidden bg-[#0A0A0B]">
      {/* Loading state while iframe loads */}
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0A0A0B] z-10">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/15 border border-[#1A8FD6]/30 flex items-center justify-center animate-pulse">
              <span className="text-[#1A8FD6] font-bold text-lg">M</span>
            </div>
            <p className="text-sm text-[#A1A1A8]">Loading Sales Portal…</p>
          </div>
        </div>
      )}
      <iframe
        ref={iframeRef}
        src="https://meridian-sales-f7df5b93.viktor.space/login"
        className="w-full h-full border-0"
        title="Meridian Sales Portal"
        allow="clipboard-write"
        onLoad={() => setLoaded(true)}
      />
    </div>
  )
}
