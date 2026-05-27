import { useState, useRef, useCallback, useEffect } from 'react'
import {
  X, CheckCircle2, Loader2, RotateCcw, ArrowRight,
  Move, Scan, Layers, Eye,
} from 'lucide-react'

interface WebXRScanProps {
  onFramesCaptured: (frames: Blob[], metadata: XRCaptureMetadata) => void
  onCancel: () => void
  onFallbackToStandard: () => void
  deviceModel: string | null
}

interface XRCaptureMetadata {
  frameCount: number
  durationSeconds: number
  deviceModel: string | null
  tier: 'lidar'
  resolution: { width: number; height: number }
  hasDepthData: boolean
  xrSessionUsed: boolean
}

type ScanState = 'initializing' | 'scanning' | 'reviewing' | 'error'

const FRAME_INTERVAL_MS = 500
const MIN_FRAMES = 25
const MAX_FRAMES = 250
const TARGET_FRAMES = 100

export default function WebXRScan({ onFramesCaptured, onCancel, onFallbackToStandard, deviceModel }: WebXRScanProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const xrSessionRef = useRef<any>(null)
  const framesRef = useRef<Blob[]>([])
  const startTimeRef = useRef(0)
  const lastCaptureRef = useRef(0)
  const animFrameRef = useRef(0)

  const [state, setState] = useState<ScanState>('initializing')
  const [frameCount, setFrameCount] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [hasDepthData, setHasDepthData] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [coveragePercent, setCoveragePercent] = useState(0)
  const [resolution, setResolution] = useState({ width: 0, height: 0 })

  const initXR = useCallback(async () => {
    if (!('xr' in navigator)) {
      setErrorMsg('WebXR not supported on this browser')
      setState('error')
      return
    }

    const xr = (navigator as any).xr
    const arSupported = await xr.isSessionSupported('immersive-ar').catch(() => false)

    if (!arSupported) {
      setErrorMsg('AR scanning not available — switching to enhanced camera mode')
      setState('error')
      setTimeout(onFallbackToStandard, 2000)
      return
    }

    try {
      const features: string[] = ['local-floor']
      const optionalFeatures: string[] = ['depth-sensing', 'hit-test', 'light-estimation']

      const session = await xr.requestSession('immersive-ar', {
        requiredFeatures: features,
        optionalFeatures,
        depthSensing: {
          usagePreference: ['cpu-optimized'],
          dataFormatPreference: ['luminance-alpha'],
        },
      })

      xrSessionRef.current = session
      const canvas = canvasRef.current!
      const gl = canvas.getContext('webgl2', { xrCompatible: true })
        || canvas.getContext('webgl', { xrCompatible: true })

      if (!gl) {
        throw new Error('WebGL context not available')
      }

      await session.updateRenderState({ baseLayer: new (window as any).XRWebGLLayer(session, gl) })
      const refSpace = await session.requestReferenceSpace('local-floor')

      startTimeRef.current = Date.now()
      setState('scanning')

      session.requestAnimationFrame(function onFrame(time: number, frame: any) {
        if (!xrSessionRef.current) return

        const pose = frame.getViewerPose(refSpace)
        if (!pose) {
          animFrameRef.current = session.requestAnimationFrame(onFrame)
          return
        }

        // Check for depth data
        const view = pose.views[0]
        if (view) {
          try {
            const depthInfo = frame.getDepthInformation?.(view)
            if (depthInfo) setHasDepthData(true)
          } catch { /* depth not available */ }

          const viewport = session.renderState.baseLayer!.getViewport(view)
          if (viewport && resolution.width === 0) {
            setResolution({ width: viewport.width, height: viewport.height })
          }
        }

        // Capture frames at interval
        const now = Date.now()
        if (now - lastCaptureRef.current >= FRAME_INTERVAL_MS) {
          lastCaptureRef.current = now
          captureXRFrame(gl as WebGLRenderingContext, session)
        }

        setElapsed(Math.floor((now - startTimeRef.current) / 1000))
        setCoveragePercent(Math.min((framesRef.current.length / TARGET_FRAMES) * 100, 100))

        if (framesRef.current.length >= MAX_FRAMES) {
          stopScanning()
          return
        }

        animFrameRef.current = session.requestAnimationFrame(onFrame)
      })

      session.addEventListener('end', () => {
        xrSessionRef.current = null
        if (framesRef.current.length >= MIN_FRAMES) {
          setState('reviewing')
        }
      })
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start AR session')
      setState('error')
    }
  }, [onFallbackToStandard, resolution.width])

  function captureXRFrame(gl: WebGLRenderingContext, session: any) {
    const layer = session.renderState.baseLayer
    if (!layer) return

    const width = layer.framebufferWidth || gl.drawingBufferWidth
    const height = layer.framebufferHeight || gl.drawingBufferHeight

    const pixels = new Uint8Array(width * height * 4)
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels)

    const offscreen = new OffscreenCanvas(width, height)
    const ctx2d = offscreen.getContext('2d')
    if (!ctx2d) return

    const imageData = new ImageData(new Uint8ClampedArray(pixels.buffer), width, height)

    // Flip vertically (WebGL reads bottom-up)
    const flipped = ctx2d.createImageData(width, height)
    for (let y = 0; y < height; y++) {
      const srcRow = (height - y - 1) * width * 4
      const dstRow = y * width * 4
      for (let x = 0; x < width * 4; x++) {
        flipped.data[dstRow + x] = imageData.data[srcRow + x]
      }
    }
    ctx2d.putImageData(flipped, 0, 0)

    offscreen.convertToBlob({ type: 'image/jpeg', quality: 0.9 }).then(blob => {
      if (blob) {
        framesRef.current.push(blob)
        setFrameCount(framesRef.current.length)
      }
    })
  }

  function stopScanning() {
    if (xrSessionRef.current) {
      xrSessionRef.current.end().catch(() => {})
      xrSessionRef.current = null
    }
    setState('reviewing')
  }

  function handleRetake() {
    framesRef.current = []
    setFrameCount(0)
    setElapsed(0)
    setCoveragePercent(0)
    setState('initializing')
    initXR()
  }

  function handleConfirm() {
    onFramesCaptured(framesRef.current, {
      frameCount: framesRef.current.length,
      durationSeconds: elapsed,
      deviceModel,
      tier: 'lidar',
      resolution,
      hasDepthData,
      xrSessionUsed: true,
    })
  }

  useEffect(() => {
    initXR()
    return () => {
      if (xrSessionRef.current) xrSessionRef.current.end().catch(() => {})
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [])

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  if (state === 'error') {
    return (
      <div className="fixed inset-0 z-50 bg-black flex items-center justify-center">
        <div className="max-w-sm mx-4 p-6 rounded-2xl bg-[#111113] border border-[#1F1F23] text-center">
          <Scan size={32} className="text-amber-400 mx-auto mb-3" />
          <p className="text-sm text-white font-medium mb-2">AR Scanning Unavailable</p>
          <p className="text-xs text-[#A1A1A8] mb-4">{errorMsg}</p>
          <div className="flex gap-2">
            <button
              onClick={onCancel}
              className="flex-1 px-4 py-2 rounded-lg bg-[#1F1F23] text-white text-xs font-medium"
            >
              Cancel
            </button>
            <button
              onClick={onFallbackToStandard}
              className="flex-1 px-4 py-2 rounded-lg bg-[#1A8FD6] text-white text-xs font-medium"
            >
              Use Camera Instead
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (state === 'initializing') {
    return (
      <div className="fixed inset-0 z-50 bg-black flex items-center justify-center">
        <div className="text-center">
          <Loader2 size={32} className="text-[#7C5CFF] animate-spin mx-auto mb-3" />
          <p className="text-sm text-white font-medium">Starting AR Scanner</p>
          <p className="text-xs text-white/40 mt-1">Point your phone at the floor to begin</p>
        </div>
      </div>
    )
  }

  if (state === 'reviewing') {
    return (
      <div className="fixed inset-0 z-50 bg-black flex items-center justify-center">
        <div className="max-w-sm mx-4 p-6 rounded-2xl bg-[#111113] border border-[#1F1F23]">
          <div className="text-center mb-5">
            <div className="w-14 h-14 rounded-2xl bg-[#17C5B0]/10 flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 size={28} className="text-[#17C5B0]" />
            </div>
            <p className="text-sm font-semibold text-white">AR Scan Complete</p>
            <p className="text-xs text-[#A1A1A8] mt-1">
              {hasDepthData ? 'LiDAR depth data captured' : 'High-resolution scan captured'}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2 mb-5">
            <div className="px-2 py-2 rounded-lg bg-[#0A0A0B] border border-[#1F1F23] text-center">
              <p className="text-lg font-bold text-white font-mono">{frameCount}</p>
              <p className="text-[9px] text-[#A1A1A8]">frames</p>
            </div>
            <div className="px-2 py-2 rounded-lg bg-[#0A0A0B] border border-[#1F1F23] text-center">
              <p className="text-lg font-bold text-white font-mono">{formatTime(elapsed)}</p>
              <p className="text-[9px] text-[#A1A1A8]">duration</p>
            </div>
            <div className="px-2 py-2 rounded-lg bg-[#0A0A0B] border border-[#1F1F23] text-center">
              <p className="text-lg font-bold text-[#7C5CFF] font-mono flex items-center justify-center gap-1">
                {hasDepthData && <Layers size={12} />}
                {hasDepthData ? 'Yes' : 'No'}
              </p>
              <p className="text-[9px] text-[#A1A1A8]">depth</p>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleRetake}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#1F1F23] text-white text-xs font-medium"
            >
              <RotateCcw size={14} />
              Retake
            </button>
            <button
              onClick={handleConfirm}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold"
            >
              <CheckCircle2 size={14} />
              Process
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Scanning state — the XR session takes over rendering, this is the HUD overlay
  return (
    <div className="fixed inset-0 z-50 pointer-events-none">
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />

      {/* HUD overlay */}
      <div className="absolute top-0 left-0 right-0 z-10 px-4 pt-[max(env(safe-area-inset-top),12px)] pb-2 pointer-events-auto">
        <div className="flex items-center justify-between">
          <button aria-label="Cancel scan" onClick={onCancel} className="p-2 rounded-full bg-black/40 text-white">
            <X size={20} />
          </button>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-full bg-[#7C5CFF]/30 text-[#7C5CFF] text-[10px] font-semibold flex items-center gap-1">
              <Eye size={10} />
              AR Mode
            </span>
            {hasDepthData && (
              <span className="px-2 py-0.5 rounded-full bg-[#17C5B0]/20 text-[#17C5B0] text-[10px] font-semibold flex items-center gap-1">
                <Layers size={10} />
                Depth
              </span>
            )}
          </div>
          <span className="text-xs text-white/60 font-mono">{formatTime(elapsed)}</span>
        </div>
      </div>

      {/* Bottom HUD */}
      <div className="absolute bottom-0 left-0 right-0 z-10 px-4 pb-[max(env(safe-area-inset-bottom),16px)] pt-3 bg-gradient-to-t from-black/70 to-transparent pointer-events-auto">
        {/* Coverage ring */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="relative w-12 h-12">
              <svg viewBox="0 0 48 48" className="w-full h-full -rotate-90">
                <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="3" />
                <circle
                  cx="24" cy="24" r="20" fill="none"
                  stroke={frameCount >= MIN_FRAMES ? '#17C5B0' : '#F59E0B'}
                  strokeWidth="3"
                  strokeDasharray={`${coveragePercent * 1.257} 125.7`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-bold text-white font-mono">{frameCount}</span>
              </div>
            </div>
            <div>
              <p className="text-xs text-white font-medium">{Math.round(coveragePercent)}% coverage</p>
              <p className="text-[10px] text-white/40">
                {frameCount < MIN_FRAMES ? `${MIN_FRAMES - frameCount} more frames needed` : 'Ready to process'}
              </p>
            </div>
          </div>

          <button
            onClick={stopScanning}
            disabled={frameCount < MIN_FRAMES}
            className="px-5 py-2.5 rounded-xl bg-white text-black text-xs font-semibold disabled:opacity-30 transition-all active:scale-95"
          >
            Done
          </button>
        </div>

        <p className="text-center text-[10px] text-white/30 flex items-center justify-center gap-1">
          <Move size={10} />
          Move slowly — scan all walls, floors, and fixtures
        </p>
      </div>
    </div>
  )
}
