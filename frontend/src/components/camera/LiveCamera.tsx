import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Layers, X } from 'lucide-react'
import WhepPlayer from './WhepPlayer'
import OverlayCanvas from './OverlayCanvas'
import LayerManager from './LayerManager'
import { MOBILE_DEFAULT, PRESETS, type LayerKey, type LayerState, type OverlayFrame } from './overlay-layers'

interface LiveTokenResp { token: string; whep_url: string; hls_url?: string }
interface FeedResp { channel: string; allowed_layers: LayerKey[] }

/**
 * One live camera tile: fetches a short-lived view token + overlay descriptor, plays the
 * WHEP stream, renders the toggleable overlays, and persists layer prefs (localStorage —
 * swap to user_overlay_prefs API when wired). ponytail: self-contained; the page passes
 * apiBase / orgId / getAuthToken / subscribeOverlay so we don't hard-couple auth + realtime.
 */
export default function LiveCamera({
  cameraId, name, apiBase, orgId, getAuthToken, subscribeOverlay,
}: {
  cameraId: string
  name: string
  apiBase: string
  orgId: string
  getAuthToken: () => string | null
  // returns an unsubscribe fn; calls cb with each overlay frame for this camera
  subscribeOverlay: (channel: string, cb: (f: OverlayFrame) => void) => () => void
}) {
  const [tok, setTok] = useState<LiveTokenResp | null>(null)
  const [allowed, setAllowed] = useState<Set<LayerKey>>(new Set())
  const [channel, setChannel] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [showPanel, setShowPanel] = useState(false)
  const frameRef = useRef<OverlayFrame | null>(null)
  const [, force] = useState(0)

  const prefKey = `overlay:${cameraId}`
  const [layers, setLayers] = useState<LayerState>(() => {
    try { const s = localStorage.getItem(prefKey); if (s) return JSON.parse(s) } catch { /* ignore */ }
    return window.innerWidth < 768 ? MOBILE_DEFAULT : PRESETS.Operations
  })
  const saveLayers = useCallback((next: LayerState) => {
    setLayers(next); try { localStorage.setItem(prefKey, JSON.stringify(next)) } catch { /* ignore */ }
  }, [prefKey])

  // fetch token + overlay descriptor
  useEffect(() => {
    let cancelled = false
    const auth = getAuthToken()
    const h = { Authorization: `Bearer ${auth ?? ''}` }
    const q = `?org_id=${encodeURIComponent(orgId)}`
    Promise.all([
      fetch(`${apiBase}/api/cameras/${cameraId}/live-token${q}`, { method: 'POST', headers: h }).then(r => r.ok ? r.json() : Promise.reject(r.status)),
      fetch(`${apiBase}/api/overlays/${cameraId}/feed${q}`, { headers: h }).then(r => r.ok ? r.json() : Promise.reject(r.status)),
    ]).then(([t, f]: [LiveTokenResp, FeedResp]) => {
      if (cancelled) return
      setTok(t); setAllowed(new Set(f.allowed_layers || [])); setChannel(f.channel)
    }).catch(() => { if (!cancelled) setErr('Could not start stream') })
    return () => { cancelled = true }
  }, [cameraId, apiBase, orgId, getAuthToken])

  // subscribe to overlay frames
  useEffect(() => {
    if (!channel) return
    const unsub = subscribeOverlay(channel, (f) => { frameRef.current = f })
    return unsub
  }, [channel, subscribeOverlay])

  const getVideoTime = useMemo(() => () => Date.now(), [])  // live ≈ now; tolerance handles drift

  return (
    <div className="relative rounded-2xl overflow-hidden border border-[#1F1F23] bg-black aspect-video">
      {tok && !err ? (
        <>
          <WhepPlayer whepUrl={tok.whep_url} hlsUrl={tok.hls_url} token={tok.token} />
          <OverlayCanvas frame={frameRef.current} layers={layers} getVideoTime={getVideoTime} />
        </>
      ) : (
        <div className="absolute inset-0 flex items-center justify-center text-[13px] text-[#A1A1A8]/60">
          {err || 'Connecting…'}
        </div>
      )}

      {/* name + layer toggle */}
      <div className="absolute top-2 left-2 right-2 flex items-center justify-between">
        <span className="px-2 py-1 rounded-lg bg-black/50 text-[12px] font-semibold text-white">{name}</span>
        <button onClick={() => { setShowPanel(v => !v); force(n => n + 1) }}
          className="p-1.5 rounded-lg bg-black/50 text-white hover:bg-black/70 active:scale-95 transition-all">
          {showPanel ? <X size={16} /> : <Layers size={16} />}
        </button>
      </div>

      {showPanel && (
        <div className="absolute bottom-2 left-2 right-2 max-w-xs">
          <LayerManager state={layers} allowed={allowed} onChange={saveLayers} />
        </div>
      )}
    </div>
  )
}
