import { useEffect, useRef } from 'react'

/**
 * Full-screen iframe wrapper for the Meridian Sales Portal.
 * Lives at /portal on meridian.tips — feels native, no redirect.
 */
export default function PortalPage() {
  const iframeRef = useRef<HTMLIFrameElement>(null)

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
      <iframe
        ref={iframeRef}
        src="https://meridian-sales-f7df5b93.viktor.space/login"
        className="w-full h-full border-0"
        title="Meridian Sales Portal"
        allow="clipboard-write"
      />
    </div>
  )
}
