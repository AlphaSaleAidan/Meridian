import { useCallback, useEffect, useRef, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useOrgId } from '@/hooks/useOrg'
import LiveCamera from '@/components/camera/LiveCamera'
import type { OverlayFrame } from '@/components/camera/overlay-layers'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface Cam { id: string; name: string }

/**
 * Live camera grid: lists the org's cameras and renders a LiveCamera tile (WHEP + overlays)
 * for each. Auth token + Supabase realtime are injected into the tiles.
 * ponytail: thin page; all the streaming/overlay logic lives in the components.
 *
 * Surface it via a route or the Camera pillar (1-line wiring follow-up).
 */
export default function LiveCamerasPage() {
  const orgId = useOrgId()
  const [cams, setCams] = useState<Cam[]>([])
  const tokenRef = useRef<string | null>(null)

  // keep a fresh session token for the tiles to read synchronously
  useEffect(() => {
    let alive = true
    const load = async () => {
      const { data } = await supabase!.auth.getSession()
      if (alive) tokenRef.current = data?.session?.access_token ?? null
    }
    load()
    const { data: sub } = supabase!.auth.onAuthStateChange((_e, s) => { tokenRef.current = s?.access_token ?? null })
    return () => { alive = false; sub?.subscription?.unsubscribe?.() }
  }, [])

  // fetch the org's cameras
  useEffect(() => {
    if (!orgId) return
    fetch(`${API_BASE}/api/vision/cameras/${orgId}`)
      .then(r => r.ok ? r.json() : { cameras: [] })
      .then(d => setCams(d.cameras || d || []))
      .catch(() => setCams([]))
  }, [orgId])

  const getAuthToken = useCallback(() => tokenRef.current, [])
  const subscribeOverlay = useCallback((channel: string, cb: (f: OverlayFrame) => void) => {
    const ch = supabase!.channel(channel)
      .on('broadcast', { event: 'frame' }, (m) => cb(m.payload as OverlayFrame))
      .subscribe()
    return () => { supabase!.removeChannel(ch) }
  }, [])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-[#F5F5F7]">Live cameras</h1>
        <p className="text-[12px] text-[#A1A1A8] mt-0.5">Sub-second WebRTC · tap the layers icon to toggle overlays</p>
      </div>
      {cams.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#1F1F23] py-12 text-center text-[13px] text-[#A1A1A8]/60">
          No cameras yet — connect one from the “Connect cameras” wizard.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {cams.map(c => (
            <LiveCamera key={c.id} cameraId={c.id} name={c.name}
              apiBase={API_BASE} orgId={orgId}
              getAuthToken={getAuthToken} subscribeOverlay={subscribeOverlay} />
          ))}
        </div>
      )}
    </div>
  )
}
