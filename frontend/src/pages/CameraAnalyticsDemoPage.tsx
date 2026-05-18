import { useState, useRef, useEffect, useCallback } from 'react'
import { Camera, Eye, EyeOff, Play, Square, RefreshCw, Activity, User, Hand, Smile, Box } from 'lucide-react'
import { useWebcam } from '@/hooks/useWebcam'
import { useMediaPipeTracking } from '@/hooks/useMediaPipeTracking'
import { classifyGesture, computeEngagement, type GestureResult } from '@/lib/gesture-classifier'

type TrackingMode = 'pose' | 'hands' | 'face' | 'objects'

const MODE_COLORS: Record<TrackingMode, string> = {
  pose: '#00d4aa',
  hands: '#7c3aed',
  face: '#f59e0b',
  objects: '#ef4444',
}

const MODE_ICONS: Record<TrackingMode, typeof User> = {
  pose: User,
  hands: Hand,
  face: Smile,
  objects: Box,
}

export default function CameraAnalyticsDemoPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const heatmapRef = useRef<Float32Array>(new Float32Array(16 * 12))
  const { videoRef, isActive, isLoading: camLoading, error: camError, devices, activeDeviceId, start, stop, switchCamera } = useWebcam()

  const [modes, setModes] = useState({ pose: true, hands: true, face: true, objects: true })
  const { isLoading: modelsLoading, isReady, error: modelError, fps, poseResults, handResults, faceResults, objectResults, initialize, startTracking, stopTracking } = useMediaPipeTracking(videoRef, modes)

  const [gesture, setGesture] = useState<GestureResult>({ gesture: 'unknown', confidence: 0, description: '' })
  const [engagement, setEngagement] = useState(0)
  const [personCount, setPersonCount] = useState(0)
  const [handCount, setHandCount] = useState(0)
  const [faceCount, setFaceCount] = useState(0)

  const toggleMode = (mode: TrackingMode) => {
    setModes(m => ({ ...m, [mode]: !m[mode] }))
  }

  const handleStart = async () => {
    await start()
    if (!isReady) await initialize()
  }

  useEffect(() => {
    if (isActive && isReady) startTracking()
  }, [isActive, isReady, startTracking])

  // Process results and draw overlay
  useEffect(() => {
    if (!poseResults && !handResults && !faceResults && !objectResults) return

    const canvas = canvasRef.current
    const video = videoRef.current
    if (!canvas || !video) return

    canvas.width = video.videoWidth || 1280
    canvas.height = video.videoHeight || 720
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Draw pose landmarks + skeleton
    if (poseResults?.landmarks?.length) {
      setPersonCount(poseResults.landmarks.length)

      for (const landmarks of poseResults.landmarks) {
        const g = classifyGesture(landmarks)
        setGesture(g)
        setEngagement(computeEngagement(landmarks))

        if (modes.pose) {
          // Draw connections
          const connections = [
            [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
            [11, 23], [12, 24], [23, 24], [23, 25], [25, 27],
            [24, 26], [26, 28], [15, 17], [16, 18], [15, 19],
            [16, 20], [17, 19], [18, 20], [0, 1], [1, 2],
            [2, 3], [3, 7], [0, 4], [4, 5], [5, 6], [6, 8],
          ]

          ctx.strokeStyle = MODE_COLORS.pose
          ctx.lineWidth = 2
          for (const [a, b] of connections) {
            const la = landmarks[a]
            const lb = landmarks[b]
            if (la && lb && (la.visibility || 0) > 0.5 && (lb.visibility || 0) > 0.5) {
              ctx.beginPath()
              ctx.moveTo(la.x * canvas.width, la.y * canvas.height)
              ctx.lineTo(lb.x * canvas.width, lb.y * canvas.height)
              ctx.stroke()
            }
          }

          // Draw landmarks
          for (const lm of landmarks) {
            if ((lm.visibility || 0) > 0.5) {
              ctx.fillStyle = MODE_COLORS.pose
              ctx.beginPath()
              ctx.arc(lm.x * canvas.width, lm.y * canvas.height, 4, 0, Math.PI * 2)
              ctx.fill()
            }
          }

          // Gesture label above head
          const nose = landmarks[0]
          if (nose && g.gesture !== 'unknown') {
            ctx.font = 'bold 16px Inter, sans-serif'
            ctx.fillStyle = MODE_COLORS.pose
            ctx.textAlign = 'center'
            ctx.fillText(`${g.gesture} (${Math.round(g.confidence * 100)}%)`, nose.x * canvas.width, nose.y * canvas.height - 30)
          }
        }

        // Update heatmap (divide frame into 16x12 grid)
        for (const lm of landmarks) {
          if ((lm.visibility || 0) > 0.5) {
            const gx = Math.min(Math.floor(lm.x * 16), 15)
            const gy = Math.min(Math.floor(lm.y * 12), 11)
            if (gx >= 0 && gy >= 0) {
              heatmapRef.current[gy * 16 + gx] += 0.1
            }
          }
        }
      }
    } else {
      setPersonCount(0)
    }

    // Draw hand landmarks
    if (handResults?.landmarks?.length && modes.hands) {
      setHandCount(handResults.landmarks.length)
      for (const landmarks of handResults.landmarks) {
        const handConnections = [
          [0, 1], [1, 2], [2, 3], [3, 4],
          [0, 5], [5, 6], [6, 7], [7, 8],
          [5, 9], [9, 10], [10, 11], [11, 12],
          [9, 13], [13, 14], [14, 15], [15, 16],
          [13, 17], [17, 18], [18, 19], [19, 20], [0, 17],
        ]
        ctx.strokeStyle = MODE_COLORS.hands
        ctx.lineWidth = 2
        for (const [a, b] of handConnections) {
          const la = landmarks[a]
          const lb = landmarks[b]
          if (la && lb) {
            ctx.beginPath()
            ctx.moveTo(la.x * canvas.width, la.y * canvas.height)
            ctx.lineTo(lb.x * canvas.width, lb.y * canvas.height)
            ctx.stroke()
          }
        }
        for (const lm of landmarks) {
          ctx.fillStyle = MODE_COLORS.hands
          ctx.beginPath()
          ctx.arc(lm.x * canvas.width, lm.y * canvas.height, 3, 0, Math.PI * 2)
          ctx.fill()
        }
      }
    } else {
      setHandCount(handResults?.landmarks?.length || 0)
    }

    // Draw face mesh
    if (faceResults?.faceLandmarks?.length && modes.face) {
      setFaceCount(faceResults.faceLandmarks.length)
      for (const landmarks of faceResults.faceLandmarks) {
        ctx.fillStyle = `${MODE_COLORS.face}40`
        for (let i = 0; i < landmarks.length; i += 3) {
          const lm = landmarks[i]
          if (lm) {
            ctx.beginPath()
            ctx.arc(lm.x * canvas.width, lm.y * canvas.height, 1, 0, Math.PI * 2)
            ctx.fill()
          }
        }
      }
    } else {
      setFaceCount(faceResults?.faceLandmarks?.length || 0)
    }

    // Draw object bounding boxes
    if (objectResults?.detections?.length && modes.objects) {
      for (const det of objectResults.detections) {
        const bb = det.boundingBox
        if (!bb) continue
        ctx.strokeStyle = MODE_COLORS.objects
        ctx.lineWidth = 2
        ctx.strokeRect(bb.originX, bb.originY, bb.width, bb.height)

        const label = det.categories?.[0]
        if (label) {
          ctx.font = '12px Inter, sans-serif'
          ctx.fillStyle = MODE_COLORS.objects
          ctx.fillText(`${label.categoryName} ${Math.round(label.score * 100)}%`, bb.originX + 4, bb.originY - 6)
        }
      }
    }
  }, [poseResults, handResults, faceResults, objectResults, modes, videoRef])

  // Draw heatmap mini-canvas
  const heatmapCanvasRef = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const hc = heatmapCanvasRef.current
    if (!hc) return
    const ctx = hc.getContext('2d')
    if (!ctx) return

    const interval = setInterval(() => {
      const data = heatmapRef.current
      const max = Math.max(...data, 1)
      ctx.clearRect(0, 0, 160, 120)

      for (let y = 0; y < 12; y++) {
        for (let x = 0; x < 16; x++) {
          const val = data[y * 16 + x] / max
          if (val > 0.01) {
            const r = Math.round(val * 255)
            const g = Math.round((1 - val) * 100)
            ctx.fillStyle = `rgba(${r}, ${g}, 50, ${Math.min(val + 0.2, 0.9)})`
            ctx.fillRect(x * 10, y * 10, 10, 10)
          }
        }
      }
    }, 500)
    return () => clearInterval(interval)
  }, [])

  const error = camError || modelError

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-white p-4 lg:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/30 flex items-center justify-center">
              <Camera size={18} className="text-[#00d4aa]" />
            </div>
            <div>
              <h1 className="text-[18px] font-bold">Camera Analytics</h1>
              <p className="text-[11px] text-[#6b7a74]">Real-time pose, gesture, hand, face & object tracking</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {fps > 0 && (
              <div className="px-3 py-1.5 rounded-lg bg-[#0f1512] border border-[#1a2420] text-[12px] font-mono">
                <Activity size={12} className="inline mr-1.5 text-[#00d4aa]" />{fps} FPS
              </div>
            )}
            {devices.length > 1 && (
              <select
                value={activeDeviceId}
                onChange={e => switchCamera(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-[#0f1512] border border-[#1a2420] text-[12px] text-white"
              >
                {devices.map(d => (
                  <option key={d.deviceId} value={d.deviceId}>
                    {d.label || `Camera ${d.deviceId.slice(0, 8)}`}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
          {/* Video + Canvas */}
          <div className="relative rounded-xl overflow-hidden border border-[#1a2420] bg-[#0f1512] aspect-video">
            <video
              ref={videoRef}
              className="absolute inset-0 w-full h-full object-cover"
              playsInline
              muted
            />
            <canvas
              ref={canvasRef}
              className="absolute inset-0 w-full h-full object-cover pointer-events-none"
            />

            {!isActive && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-[#0A0A0B]/80">
                <Camera size={48} className="text-[#6b7a74]" />
                <p className="text-[13px] text-[#6b7a74] text-center max-w-xs">
                  {modelsLoading ? 'Loading AI models...' : camLoading ? 'Starting camera...' : 'Click Start to begin camera analytics'}
                </p>
                <button
                  onClick={handleStart}
                  disabled={camLoading || modelsLoading}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-[#00d4aa] text-[#0A0A0B] text-[13px] font-semibold hover:bg-[#00c49e] disabled:opacity-50 transition-colors"
                >
                  {camLoading || modelsLoading ? (
                    <><RefreshCw size={14} className="animate-spin" /> Loading...</>
                  ) : (
                    <><Play size={14} /> Start Camera</>
                  )}
                </button>
              </div>
            )}

            {isActive && (
              <button
                onClick={() => { stopTracking(); stop() }}
                className="absolute top-3 right-3 p-2 rounded-lg bg-[#0A0A0B]/60 border border-[#1a2420] hover:bg-red-500/20 transition-colors"
              >
                <Square size={14} className="text-red-400" />
              </button>
            )}

            {error && (
              <div className="absolute bottom-3 left-3 right-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-[12px] text-red-400">
                {error}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-3">
            {/* Tracking Modes */}
            <div className="rounded-xl p-4 bg-[#0f1512] border border-[#1a2420]">
              <p className="text-[11px] font-mono text-[#6b7a74] tracking-wider mb-3">TRACKING MODES</p>
              <div className="space-y-2">
                {(Object.keys(modes) as TrackingMode[]).map(mode => {
                  const Icon = MODE_ICONS[mode]
                  const labels: Record<TrackingMode, string> = { pose: 'Skeleton (33 pts)', hands: 'Hands (42 pts)', face: 'Face (478 pts)', objects: 'Objects' }
                  return (
                    <button
                      key={mode}
                      onClick={() => toggleMode(mode)}
                      className={`flex items-center gap-2.5 w-full px-3 py-2 rounded-lg border text-[12px] transition-all ${
                        modes[mode]
                          ? 'border-[' + MODE_COLORS[mode] + ']/40 bg-[' + MODE_COLORS[mode] + ']/5 text-white'
                          : 'border-[#1a2420] text-[#6b7a74] hover:border-[#2a3430]'
                      }`}
                      style={modes[mode] ? { borderColor: `${MODE_COLORS[mode]}40`, backgroundColor: `${MODE_COLORS[mode]}08` } : {}}
                    >
                      {modes[mode] ? <Eye size={13} style={{ color: MODE_COLORS[mode] }} /> : <EyeOff size={13} />}
                      <Icon size={13} style={modes[mode] ? { color: MODE_COLORS[mode] } : {}} />
                      <span>{labels[mode]}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Live Metrics */}
            <div className="rounded-xl p-4 bg-[#0f1512] border border-[#1a2420]">
              <p className="text-[11px] font-mono text-[#6b7a74] tracking-wider mb-3">LIVE METRICS</p>
              <div className="space-y-2.5">
                <MetricRow label="People" value={String(personCount)} color="#00d4aa" />
                <MetricRow label="Gesture" value={gesture.gesture} color="#00d4aa" />
                <MetricRow label="Confidence" value={`${Math.round(gesture.confidence * 100)}%`} color="#00d4aa" />
                <MetricRow label="Hands" value={`${handCount} detected`} color="#7c3aed" />
                <MetricRow label="Faces" value={`${faceCount} detected`} color="#f59e0b" />
                <MetricRow label="Engagement" value={`${Math.round(engagement * 100)}%`} color={engagement > 0.6 ? '#00d4aa' : '#f59e0b'} />
              </div>
            </div>

            {/* Gesture Description */}
            {gesture.gesture !== 'unknown' && (
              <div className="rounded-xl p-4 bg-[#0f1512] border border-[#1a2420]">
                <p className="text-[11px] font-mono text-[#6b7a74] tracking-wider mb-2">GESTURE INSIGHT</p>
                <p className="text-[12px] text-[#9ca8a3] leading-relaxed">{gesture.description}</p>
              </div>
            )}

            {/* Zone Heatmap */}
            <div className="rounded-xl p-4 bg-[#0f1512] border border-[#1a2420]">
              <p className="text-[11px] font-mono text-[#6b7a74] tracking-wider mb-3">ZONE HEATMAP</p>
              <canvas
                ref={heatmapCanvasRef}
                width={160}
                height={120}
                className="w-full rounded-lg border border-[#1a2420]"
              />
              <p className="text-[10px] text-[#4a5550] mt-2">Accumulates over time — shows where you spend the most time</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricRow({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[12px] text-[#6b7a74]">{label}</span>
      <span className="text-[12px] font-medium" style={{ color }}>{value}</span>
    </div>
  )
}
