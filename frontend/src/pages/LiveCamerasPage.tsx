import { useEffect, useRef, useState, useCallback } from 'react'
import { Video, VideoOff, Loader2, Wifi } from 'lucide-react'
import { useIsDemo, useOrgId } from '@/hooks/useOrg'
import { getAuthHeaders } from '@/lib/supabase'
import CameraDemo from '@/components/camera/CameraDemo'

/**
 * Camera → Live tab.
 *  - Canada demo: the replayed YOLO+ByteTrack camera-intelligence clip.
 *  - Real merchant: live WHEP grid. Clicking a camera asks the backend to start
 *    on-demand streaming (edge → Cloudflare), then plays the WHEP feed via
 *    WebRTC. We re-ping while watching so the edge keeps publishing; stopping
 *    lets it go idle (no Cloudflare cost when nobody's looking).
 */

const API = (import.meta.env.VITE_API_URL || '') as string

interface Cam { id: string; name: string; status?: string; features?: Record<string, boolean> | string }

function feats(c: Cam): Record<string, boolean> {
  if (typeof c.features === 'string') { try { return JSON.parse(c.features) } catch { return {} } }
  return c.features || {}
}

function LiveTile({ cam, orgId }: { cam: Cam; orgId: string }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const pcRef = useRef<RTCPeerConnection | null>(null)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [state, setState] = useState<'idle' | 'connecting' | 'live' | 'error'>('idle')
  const liveView = feats(cam).live_view

  const stop = useCallback(() => {
    if (pingRef.current) { clearInterval(pingRef.current); pingRef.current = null }
    if (pcRef.current) { pcRef.current.close(); pcRef.current = null }
    if (videoRef.current) videoRef.current.srcObject = null
    setState('idle')
  }, [])

  const requestLive = useCallback(async (): Promise<string | null> => {
    const res = await fetch(`${API}/api/vision/cameras/${cam.id}/live?org_id=${encodeURIComponent(orgId)}`,
      { method: 'POST', headers: await getAuthHeaders() })
    if (!res.ok) return null
    return (await res.json()).whep_url || null
  }, [cam.id, orgId])

  const start = useCallback(async () => {
    setState('connecting')
    try {
      const whep = await requestLive()
      if (!whep) { setState('error'); return }
      const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.cloudflare.com:3478' }] })
      pcRef.current = pc
      pc.addTransceiver('video', { direction: 'recvonly' })
      pc.addTransceiver('audio', { direction: 'recvonly' })
      pc.ontrack = (e) => { if (videoRef.current) videoRef.current.srcObject = e.streams[0] }
      pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'connected') setState('live')
        if (['failed', 'disconnected', 'closed'].includes(pc.connectionState)) setState('error')
      }
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      const ans = await fetch(whep, { method: 'POST', headers: { 'Content-Type': 'application/sdp' }, body: offer.sdp || '' })
      if (!ans.ok) { setState('error'); return }
      await pc.setRemoteDescription({ type: 'answer', sdp: await ans.text() })
      // keep-alive: re-stamp the request every 15s so the edge keeps publishing
      pingRef.current = setInterval(() => { requestLive().catch(() => {}) }, 15000)
    } catch { setState('error') }
  }, [requestLive])

  useEffect(() => stop, [stop])

  return (
    <div className="rounded-2xl border border-[#1F1F23] bg-black overflow-hidden">
      <div className="relative aspect-video bg-[#0B0B0D]">
        <video ref={videoRef} autoPlay muted playsInline className="absolute inset-0 w-full h-full object-cover" />
        {state !== 'live' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
            {state === 'connecting' ? <Loader2 className="animate-spin text-[#1A8FD6]" size={22} />
              : state === 'error' ? <VideoOff className="text-[#A1A1A8]" size={22} />
              : <Video className="text-[#1A8FD6]" size={22} />}
            <p className="text-[12px] text-[#A1A1A8]">
              {state === 'connecting' ? 'Connecting…' : state === 'error' ? 'Could not connect' : 'Tap to view live'}
            </p>
            {liveView && state !== 'connecting' && (
              <button onClick={start}
                className="mt-1 text-[12px] font-medium px-3 py-1.5 rounded-full bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 transition-colors">
                {state === 'error' ? 'Retry' : 'Go live'}
              </button>
            )}
            {!liveView && <p className="text-[11px] text-[#A1A1A8]/60">Live view is off — enable it in camera settings</p>}
          </div>
        )}
        {state === 'live' && (
          <span className="absolute top-2 left-2 inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-red-500/90 text-white">
            <Wifi size={10} /> LIVE
          </span>
        )}
      </div>
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-[13px] text-[#F5F5F7] truncate">{cam.name}</span>
        {state === 'live' && (
          <button onClick={stop} className="text-[11px] text-[#A1A1A8] hover:text-[#F5F5F7]">Stop</button>
        )}
      </div>
    </div>
  )
}

export default function LiveCamerasPage() {
  const isDemo = useIsDemo()
  const orgId = useOrgId()
  const [cams, setCams] = useState<Cam[] | null>(null)

  useEffect(() => {
    if (isDemo || !orgId || orgId === 'demo') return
    let alive = true
    ;(async () => {
      try {
        const res = await fetch(`${API}/api/vision/cameras/${orgId}`, { headers: await getAuthHeaders() })
        const data = res.ok ? await res.json() : { cameras: [] }
        if (alive) setCams(data.cameras || [])
      } catch { if (alive) setCams([]) }
    })()
    return () => { alive = false }
  }, [isDemo, orgId])

  if (isDemo) return <CameraDemo />

  if (cams === null) {
    return <div className="py-12 text-center"><Loader2 className="animate-spin mx-auto text-[#1A8FD6]" size={22} /></div>
  }
  if (cams.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-[#1F1F23] py-12 text-center">
        <Video className="mx-auto text-[#A1A1A8] mb-2" size={24} />
        <p className="text-[13px] text-[#A1A1A8]">No cameras connected yet.</p>
        <p className="text-[12px] text-[#A1A1A8]/60 mt-1">Add a camera in settings to view it live from anywhere.</p>
      </div>
    )
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
      {cams.map(c => <LiveTile key={c.id} cam={c} orgId={orgId} />)}
    </div>
  )
}
