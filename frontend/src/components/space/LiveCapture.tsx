import { useState, useRef, useCallback, useEffect } from 'react'
import {
  Camera, X, CheckCircle2, AlertCircle, Loader2,
  RotateCcw, Pause, Play, Smartphone, ArrowRight,
  Move, ChevronUp,
} from 'lucide-react'

interface LiveCaptureProps {
  onFramesCaptured: (frames: Blob[], metadata: CaptureMetadata) => void
  onCancel: () => void
  tier: 'lidar' | 'standard'
  deviceModel: string | null
}

interface CaptureMetadata {
  frameCount: number
  durationSeconds: number
  deviceModel: string | null
  tier: 'lidar' | 'standard'
  resolution: { width: number; height: number }
}

type CaptureState = 'preview' | 'recording' | 'reviewing'

const FRAME_INTERVAL_MS = 600
const MIN_FRAMES = 20
const MAX_FRAMES = 200
const TARGET_FRAMES = 80

export default function LiveCapture({ onFramesCaptured, onCancel, tier, deviceModel }: LiveCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const captureIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const framesRef = useRef<Blob[]>([])
  const startTimeRef = useRef<number>(0)

  const [state, setState] = useState<CaptureState>('preview')
  const [frameCount, setFrameCount] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [cameraReady, setCameraReady] = useState(false)
  const [paused, setPaused] = useState(false)
  const [motionWarning, setMotionWarning] = useState<string | null>(null)
  const [resolution, setResolution] = useState({ width: 0, height: 0 })

  const startCamera = useCallback(async () => {
    try {
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: 'environment',
          width: { ideal: tier === 'lidar' ? 3840 : 1920 },
          height: { ideal: tier === 'lidar' ? 2160 : 1080 },
          frameRate: { ideal: 30 },
        },
        audio: false,
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()

        const track = stream.getVideoTracks()[0]
        const settings = track.getSettings()
        setResolution({ width: settings.width ?? 0, height: settings.height ?? 0 })
        setCameraReady(true)
      }
    } catch (err: any) {
      if (err.name === 'NotAllowedError') {
        setError('Camera access denied. Please allow camera access in your browser settings and reload.')
      } else if (err.name === 'NotFoundError') {
        setError('No rear camera found on this device.')
      } else {
        setError(`Camera error: ${err.message}`)
      }
    }
  }, [tier])

  useEffect(() => {
    startCamera()
    return () => {
      stopCamera()
      if (captureIntervalRef.current) clearInterval(captureIntervalRef.current)
    }
  }, [startCamera])

  useEffect(() => {
    if (state !== 'recording' || paused) return
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000))
    }, 1000)
    return () => clearInterval(timer)
  }, [state, paused])

  // Simple motion detection via accelerometer
  useEffect(() => {
    if (state !== 'recording') return
    let lastAccel = { x: 0, y: 0, z: 0 }
    let tooFastCount = 0

    function handleMotion(e: DeviceMotionEvent) {
      const a = e.accelerationIncludingGravity
      if (!a?.x || !a?.y || !a?.z) return
      const delta = Math.abs(a.x - lastAccel.x) + Math.abs(a.y - lastAccel.y) + Math.abs(a.z - lastAccel.z)
      lastAccel = { x: a.x, y: a.y, z: a.z }

      if (delta > 25) {
        tooFastCount++
        if (tooFastCount > 3) setMotionWarning('Slow down — moving too fast')
      } else {
        tooFastCount = Math.max(0, tooFastCount - 1)
        if (tooFastCount === 0) setMotionWarning(null)
      }
    }

    window.addEventListener('devicemotion', handleMotion)
    return () => window.removeEventListener('devicemotion', handleMotion)
  }, [state])

  function stopCamera() {
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    setCameraReady(false)
  }

  function captureFrame() {
    if (!videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0)
    canvas.toBlob(
      blob => {
        if (blob) {
          framesRef.current.push(blob)
          setFrameCount(framesRef.current.length)
          if (framesRef.current.length >= MAX_FRAMES) stopRecording()
        }
      },
      'image/jpeg',
      tier === 'lidar' ? 0.92 : 0.85,
    )
  }

  function startRecording() {
    framesRef.current = []
    setFrameCount(0)
    setElapsed(0)
    startTimeRef.current = Date.now()
    setState('recording')
    setPaused(false)

    captureIntervalRef.current = setInterval(() => {
      if (!paused) captureFrame()
    }, FRAME_INTERVAL_MS)
  }

  function togglePause() {
    setPaused(p => !p)
  }

  function stopRecording() {
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current)
      captureIntervalRef.current = null
    }
    setState('reviewing')
  }

  function handleRetake() {
    framesRef.current = []
    setFrameCount(0)
    setElapsed(0)
    setState('preview')
  }

  function handleConfirm() {
    stopCamera()
    onFramesCaptured(framesRef.current, {
      frameCount: framesRef.current.length,
      durationSeconds: Math.floor((Date.now() - startTimeRef.current) / 1000),
      deviceModel,
      tier,
      resolution,
    })
  }

  const progress = Math.min((frameCount / TARGET_FRAMES) * 100, 100)
  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col">
      {/* Camera feed */}
      <div className="relative flex-1 overflow-hidden">
        <video
          ref={videoRef}
          playsInline
          muted
          className="absolute inset-0 w-full h-full object-cover"
        />
        <canvas ref={canvasRef} className="hidden" />

        {/* Top bar */}
        <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 pt-[max(env(safe-area-inset-top),12px)] pb-2 bg-gradient-to-b from-black/70 to-transparent">
          <button onClick={onCancel} className="p-2 rounded-full bg-black/40 text-white">
            <X size={20} />
          </button>
          <div className="flex items-center gap-2">
            {tier === 'lidar' && (
              <span className="px-2 py-0.5 rounded-full bg-[#7C5CFF]/20 text-[#7C5CFF] text-[10px] font-semibold">
                LiDAR Enhanced
              </span>
            )}
            {state === 'recording' && (
              <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-[10px] font-semibold animate-pulse flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                REC {formatTime(elapsed)}
              </span>
            )}
          </div>
          {resolution.width > 0 && (
            <span className="text-[9px] text-white/40 font-mono">
              {resolution.width}x{resolution.height}
            </span>
          )}
        </div>

        {/* Center crosshair / guide overlay */}
        {state === 'recording' && (
          <>
            <div className="absolute inset-0 pointer-events-none">
              {/* Corner brackets */}
              <div className="absolute top-[15%] left-[10%] w-8 h-8 border-t-2 border-l-2 border-white/30 rounded-tl-lg" />
              <div className="absolute top-[15%] right-[10%] w-8 h-8 border-t-2 border-r-2 border-white/30 rounded-tr-lg" />
              <div className="absolute bottom-[25%] left-[10%] w-8 h-8 border-b-2 border-l-2 border-white/30 rounded-bl-lg" />
              <div className="absolute bottom-[25%] right-[10%] w-8 h-8 border-b-2 border-r-2 border-white/30 rounded-br-lg" />

              {/* Center dot */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                <div className="w-3 h-3 rounded-full border-2 border-white/50" />
              </div>
            </div>

            {/* Motion warning */}
            {motionWarning && (
              <div className="absolute top-[20%] left-1/2 -translate-x-1/2 z-10 px-4 py-2 rounded-full bg-amber-500/90 text-black text-xs font-semibold flex items-center gap-2 animate-bounce">
                <Move size={14} />
                {motionWarning}
              </div>
            )}

            {/* Guidance text */}
            <div className="absolute top-[calc(15%+40px)] left-1/2 -translate-x-1/2 z-10">
              {frameCount < 10 ? (
                <p className="text-white/70 text-xs text-center bg-black/40 px-3 py-1.5 rounded-full">
                  Walk slowly through your store
                </p>
              ) : frameCount < MIN_FRAMES ? (
                <p className="text-white/70 text-xs text-center bg-black/40 px-3 py-1.5 rounded-full">
                  Keep going — cover all areas
                </p>
              ) : frameCount < TARGET_FRAMES ? (
                <p className="text-[#17C5B0]/90 text-xs text-center bg-black/40 px-3 py-1.5 rounded-full flex items-center gap-1">
                  <CheckCircle2 size={12} /> Good coverage — keep scanning for better quality
                </p>
              ) : null}
            </div>
          </>
        )}

        {/* Camera permission error */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-20">
            <div className="max-w-sm mx-4 p-6 rounded-2xl bg-[#111113] border border-[#1F1F23] text-center">
              <AlertCircle size={32} className="text-red-400 mx-auto mb-3" />
              <p className="text-sm text-white font-medium mb-2">Camera Access Required</p>
              <p className="text-xs text-[#A1A1A8] mb-4">{error}</p>
              <button
                onClick={onCancel}
                className="px-4 py-2 rounded-lg bg-[#1F1F23] text-white text-xs font-medium"
              >
                Go Back
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Bottom controls */}
      <div className="relative z-10 bg-black px-4 pb-[max(env(safe-area-inset-bottom),16px)] pt-3">
        {/* Progress bar */}
        {(state === 'recording' || state === 'reviewing') && (
          <div className="mb-3">
            <div className="flex items-center justify-between text-[10px] mb-1">
              <span className="text-white/50">{frameCount} frames</span>
              <span className="text-white/50">
                {frameCount < MIN_FRAMES
                  ? `${MIN_FRAMES - frameCount} more needed`
                  : 'Ready to process'}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${progress}%`,
                  background: frameCount >= MIN_FRAMES
                    ? 'linear-gradient(90deg, #17C5B0, #1A8FD6)'
                    : 'linear-gradient(90deg, #F59E0B, #F59E0B)',
                }}
              />
            </div>
          </div>
        )}

        {/* Controls */}
        <div className="flex items-center justify-between">
          {state === 'preview' && (
            <>
              <div className="w-16" />
              <button
                onClick={startRecording}
                disabled={!cameraReady}
                className="w-16 h-16 rounded-full border-4 border-white flex items-center justify-center disabled:opacity-30 transition-all active:scale-95"
              >
                <div className="w-12 h-12 rounded-full bg-red-500" />
              </button>
              <div className="w-16 flex justify-end">
                <div className="text-[10px] text-white/30 text-right">
                  <Smartphone size={12} className="mx-auto mb-0.5" />
                  Hold steady
                </div>
              </div>
            </>
          )}

          {state === 'recording' && (
            <>
              <button
                onClick={togglePause}
                className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center text-white"
              >
                {paused ? <Play size={18} /> : <Pause size={18} />}
              </button>

              <button
                onClick={stopRecording}
                disabled={frameCount < MIN_FRAMES}
                className="w-16 h-16 rounded-full border-4 border-white flex items-center justify-center disabled:opacity-30 transition-all active:scale-95"
              >
                <div className="w-8 h-8 rounded-sm bg-red-500" />
              </button>

              <div className="w-12 text-center">
                <p className="text-lg font-bold text-white font-mono">{frameCount}</p>
                <p className="text-[9px] text-white/40">frames</p>
              </div>
            </>
          )}

          {state === 'reviewing' && (
            <>
              <button
                onClick={handleRetake}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-white/10 text-white text-xs font-medium"
              >
                <RotateCcw size={14} />
                Retake
              </button>

              <button
                onClick={handleConfirm}
                className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold"
              >
                <CheckCircle2 size={14} />
                Use {frameCount} Frames
                <ArrowRight size={14} />
              </button>
            </>
          )}
        </div>

        {/* Review stats */}
        {state === 'reviewing' && (
          <div className="flex items-center justify-center gap-4 mt-3 text-[10px] text-white/40">
            <span>{frameCount} frames captured</span>
            <span>{formatTime(elapsed)} duration</span>
            <span>{resolution.width}x{resolution.height}</span>
          </div>
        )}

        {/* Swipe up hint on preview */}
        {state === 'preview' && cameraReady && (
          <div className="flex flex-col items-center mt-3 text-white/30">
            <ChevronUp size={14} className="animate-bounce" />
            <p className="text-[10px]">Tap record and walk through your store</p>
          </div>
        )}

        {/* Loading indicator while camera initializes */}
        {!cameraReady && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black">
            <div className="text-center">
              <Loader2 size={24} className="text-[#1A8FD6] animate-spin mx-auto mb-2" />
              <p className="text-xs text-white/50">Starting camera...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
