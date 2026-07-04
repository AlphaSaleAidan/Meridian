import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Camera, CheckCircle2, Loader2, Users, AlertTriangle } from 'lucide-react'

/**
 * /cam — Zero-hardware camera connect, Path A (phone/tablet as camera).
 *
 * The merchant opens this on ANY phone/tablet they already own (via a QR code on
 * their dashboard). Flow: open link → allow camera → prop it at the space → live.
 * No app store, no install. The page captures a JPEG every ~700ms and POSTs it to
 * /api/vision/camera/frame, which feeds the same detector/analytics pipeline the
 * RTSP cameras use. Anonymous counts only — no biometric/identity data.
 *
 * Transport = 1–2 fps JPEG POST (MVP). Sufficient for foot-traffic / dwell /
 * occupancy (5-min buckets). WebRTC/WHIP is the next increment for live view.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''
const CAPTURE_INTERVAL_MS = 700 // ~1.4 fps
const JPEG_QUALITY = 0.6
const CAPTURE_MAX_WIDTH = 960 // downscale before upload to keep frames small

type Phase = 'intro' | 'requesting' | 'preview' | 'live' | 'error'

export default function CamConnectPage() {
  const [params] = useSearchParams()
  const cameraId = params.get('camera_id') || ''
  const orgId = params.get('org_id') || ''
  const token = params.get('token') || ''

  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const loopRef = useRef<number | null>(null)
  const inflightRef = useRef(false)

  const [phase, setPhase] = useState<Phase>('intro')
  const [error, setError] = useState<string>('')
  const [placement, setPlacement] = useState('')
  const [personCount, setPersonCount] = useState<number | null>(null)
  const [density, setDensity] = useState<string>('')
  const [sentCount, setSentCount] = useState(0)

  const missingParams = !cameraId || !orgId || !token

  const stopEverything = useCallback(() => {
    if (loopRef.current !== null) {
      window.clearInterval(loopRef.current)
      loopRef.current = null
    }
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  useEffect(() => () => stopEverything(), [stopEverything])

  const startCamera = useCallback(async () => {
    setPhase('requesting')
    setError('')
    try {
      // Rear camera preferred for a propped phone; falls back to any camera.
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setPhase('preview')
    } catch (err: any) {
      setError(
        err?.name === 'NotAllowedError'
          ? 'Camera permission denied. Allow camera access and try again.'
          : `Could not start camera: ${err?.message || 'unknown error'}`,
      )
      setPhase('error')
    }
  }, [])

  const captureFrame = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const video = videoRef.current
      const canvas = canvasRef.current
      if (!video || !canvas || video.videoWidth === 0) return resolve(null)
      const scale = Math.min(1, CAPTURE_MAX_WIDTH / video.videoWidth)
      canvas.width = Math.round(video.videoWidth * scale)
      canvas.height = Math.round(video.videoHeight * scale)
      const ctx = canvas.getContext('2d')
      if (!ctx) return resolve(null)
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      canvas.toBlob((blob) => resolve(blob), 'image/jpeg', JPEG_QUALITY)
    })
  }, [])

  const sendFrame = useCallback(async () => {
    if (inflightRef.current) return // never queue up if the network is slow
    const blob = await captureFrame()
    if (!blob) return
    inflightRef.current = true
    try {
      const form = new FormData()
      form.append('camera_id', cameraId)
      form.append('org_id', orgId)
      form.append('token', token)
      form.append('frame', blob, 'frame.jpg')
      const res = await fetch(`${API_BASE}/api/vision/camera/frame`, {
        method: 'POST',
        body: form,
      })
      if (res.ok) {
        const data = await res.json()
        setPersonCount(typeof data.persons === 'number' ? data.persons : null)
        setDensity(data.density || '')
        setSentCount((c) => c + 1)
      } else if (res.status === 401) {
        setError('This camera link has expired. Re-open it from your dashboard.')
        setPhase('error')
        stopEverything()
      }
    } catch {
      // transient network error — keep looping, the next frame will retry
    } finally {
      inflightRef.current = false
    }
  }, [cameraId, orgId, token, captureFrame, stopEverything])

  const goLive = useCallback(async () => {
    // Best-effort: name the placement on the camera row (ignore failure).
    if (placement.trim()) {
      fetch(`${API_BASE}/api/vision/cameras/${cameraId}?org_id=${orgId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: placement.trim() }),
      }).catch(() => {})
    }
    setPhase('live')
    void sendFrame()
    loopRef.current = window.setInterval(() => void sendFrame(), CAPTURE_INTERVAL_MS)
  }, [placement, cameraId, orgId, sendFrame])

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
      <header className="px-5 py-4 border-b border-zinc-800 flex items-center gap-2">
        <Camera className="w-5 h-5 text-emerald-400" />
        <span className="font-semibold">Meridian · Camera</span>
        {phase === 'live' && (
          <span className="ml-auto flex items-center gap-1.5 text-emerald-400 text-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Live
          </span>
        )}
      </header>

      <main className="flex-1 flex flex-col items-center px-5 py-6 gap-5 max-w-md mx-auto w-full">
        {missingParams ? (
          <Notice icon={<AlertTriangle className="w-6 h-6 text-amber-400" />}>
            This link is incomplete. Open the camera QR code from your Meridian
            dashboard.
          </Notice>
        ) : (
          <>
            {phase === 'intro' && (
              <div className="text-center space-y-5 pt-8">
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto">
                  <Camera className="w-8 h-8 text-emerald-400" />
                </div>
                <h1 className="text-xl font-semibold">Turn this phone into a camera</h1>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  Prop this phone or tablet where you want to measure foot traffic.
                  It counts people anonymously — no faces, no recordings stored, just
                  live counts. Nothing to install.
                </p>
                <button
                  onClick={startCamera}
                  className="w-full py-3 rounded-xl bg-emerald-500 text-zinc-950 font-semibold hover:bg-emerald-400 transition"
                >
                  Allow camera
                </button>
              </div>
            )}

            {phase === 'requesting' && (
              <Notice icon={<Loader2 className="w-6 h-6 text-emerald-400 animate-spin" />}>
                Waiting for camera permission…
              </Notice>
            )}

            {phase === 'error' && (
              <div className="text-center space-y-4 pt-8">
                <Notice icon={<AlertTriangle className="w-6 h-6 text-amber-400" />}>
                  {error}
                </Notice>
                <button
                  onClick={startCamera}
                  className="px-5 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-sm"
                >
                  Try again
                </button>
              </div>
            )}

            {(phase === 'preview' || phase === 'live') && (
              <div className="w-full space-y-4">
                <div className="relative rounded-xl overflow-hidden bg-black aspect-video">
                  <video
                    ref={videoRef}
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                  {phase === 'live' && personCount !== null && (
                    <div className="absolute bottom-3 left-3 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/70 backdrop-blur">
                      <Users className="w-4 h-4 text-emerald-400" />
                      <span className="text-sm font-medium">
                        {personCount} {personCount === 1 ? 'person' : 'people'}
                      </span>
                      {density && density !== 'empty' && (
                        <span className="text-xs text-zinc-400">· {density}</span>
                      )}
                    </div>
                  )}
                </div>

                {phase === 'preview' && (
                  <>
                    <div>
                      <label className="text-sm text-zinc-400 block mb-1.5">
                        Where is this pointed? (optional)
                      </label>
                      <input
                        value={placement}
                        onChange={(e) => setPlacement(e.target.value)}
                        placeholder="e.g. Front entrance"
                        className="w-full px-3 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 focus:border-emerald-500 outline-none text-sm"
                      />
                    </div>
                    <button
                      onClick={goLive}
                      className="w-full py-3 rounded-xl bg-emerald-500 text-zinc-950 font-semibold hover:bg-emerald-400 transition"
                    >
                      Go live
                    </button>
                    <p className="text-xs text-zinc-500 text-center">
                      Keep this page open and the screen on. Plug the phone in so it
                      doesn't sleep.
                    </p>
                  </>
                )}

                {phase === 'live' && (
                  <div className="flex items-center gap-2 text-emerald-400 text-sm justify-center">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Streaming to your dashboard · {sentCount} frames sent</span>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>

      <canvas ref={canvasRef} className="hidden" />
    </div>
  )
}

function Notice({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 p-4 rounded-xl bg-zinc-900 border border-zinc-800 mt-6">
      <div className="shrink-0">{icon}</div>
      <p className="text-sm text-zinc-300 leading-relaxed">{children}</p>
    </div>
  )
}
