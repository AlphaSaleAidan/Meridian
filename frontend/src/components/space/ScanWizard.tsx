import { useState, useRef, useCallback, useEffect, lazy, Suspense } from 'react'
import { clsx } from 'clsx'
import {
  Video, Upload, X, CheckCircle2, AlertCircle,
  Smartphone, ArrowRight, Loader2, RotateCcw,
  Camera, Monitor, ChevronLeft, Scan, Layers,
  Eye, Zap, Box,
} from 'lucide-react'
import { spacesService, type ProcessingJob } from '@/lib/spaces-service'
import { getDeviceCapabilities, isMobile, type DeviceCapabilities } from '@/lib/device-capabilities'

const LiveCapture = lazy(() => import('./LiveCapture'))
const WebXRScan = lazy(() => import('./WebXRScan'))

type WizardStep = 'detect' | 'choose' | 'instructions' | 'capture' | 'upload' | 'upload-splat' | 'processing' | 'complete'
type ScanMode = 'live-camera' | 'ar-scan' | 'video-upload' | 'splat-upload'

interface ScanWizardProps {
  orgId: string
  onComplete: (spaceId: string) => void
  onCancel: () => void
}

const VIDEO_TIPS = [
  { icon: Smartphone, text: 'Walk slowly through the entire store' },
  { icon: Camera, text: 'Keep the camera at chest height, pointed straight ahead' },
  { icon: RotateCcw, text: 'Overlap areas — scan aisles in a snake pattern' },
  { icon: Monitor, text: 'Good lighting improves 3D quality significantly' },
]

export default function ScanWizard({ orgId, onComplete, onCancel }: ScanWizardProps) {
  const [step, setStep] = useState<WizardStep>('detect')
  const [scanMode, setScanMode] = useState<ScanMode>('live-camera')
  const [scanName, setScanName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [job, setJob] = useState<ProcessingJob | null>(null)
  const [spaceId, setSpaceId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [capabilities, setCapabilities] = useState<DeviceCapabilities | null>(null)
  const [capturedFrames, setCapturedFrames] = useState<Blob[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // Detect device capabilities on mount
  useEffect(() => {
    async function detect() {
      let caps: DeviceCapabilities
      try {
        caps = await getDeviceCapabilities()
      } catch {
        caps = { tier: 'standard', deviceModel: null, hasLiDAR: false, webXRSupported: false, rearCameraSupported: false, maxResolution: 'medium' }
      }
      setCapabilities(caps)

      if (!isMobile()) {
        setScanMode('video-upload')
        setStep('instructions')
        return
      }

      if (caps.hasLiDAR && caps.webXRSupported) {
        setScanMode('ar-scan')
      } else if (caps.rearCameraSupported) {
        setScanMode('live-camera')
      } else {
        setScanMode('splat-upload')
      }
      setStep('choose')
    }
    detect()
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    const f = e.dataTransfer.files[0]
    if (f && f.type.startsWith('video/')) {
      setFile(f)
      setError(null)
    } else {
      setError('Please upload a video file (MP4, MOV, WebM)')
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      setError(null)
    }
  }, [])

  async function handleVideoUpload() {
    if (!file || !scanName.trim()) return
    setUploading(true)
    setError(null)

    try {
      const result = await spacesService.uploadVideo(orgId, scanName.trim(), file)
      setSpaceId(result.spaceId)
      setStep('processing')
      startPolling(result.jobId)
    } catch {
      setError('Upload failed. Please try again.')
      setUploading(false)
    }
  }

  async function handleSplatUpload() {
    if (!file || !scanName.trim()) return
    setUploading(true)
    setError(null)
    try {
      const result = await spacesService.uploadSplatFile(orgId, scanName.trim(), file)
      setSpaceId(result.spaceId)
      setStep('complete')
    } catch {
      setError('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  async function handleFramesUpload(frames: Blob[], metadata: any) {
    if (frames.length === 0) return
    setStep('processing')
    setUploading(true)
    setError(null)

    const name = scanName.trim() || `Scan ${new Date().toLocaleDateString()}`

    try {
      const result = await spacesService.uploadFrames(orgId, name, frames, metadata)
      setSpaceId(result.spaceId)
      startPolling(result.jobId)
    } catch {
      setError('Frame upload failed. Please try again.')
      setStep('choose')
      setUploading(false)
    }
  }

  function startPolling(jobId: string) {
    pollRef.current = setInterval(async () => {
      const status = await spacesService.getJobStatus(jobId)
      if (status) {
        setJob(status)
        if (status.status === 'complete') {
          if (pollRef.current) clearInterval(pollRef.current)
          setStep('complete')
        } else if (status.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current)
          setError(status.error_message || 'Processing failed')
        }
      }
    }, 1000)
  }

  function handleLiveCaptureComplete(frames: Blob[], metadata: any) {
    setCapturedFrames(frames)
    handleFramesUpload(frames, metadata)
  }

  function handleXRCaptureComplete(frames: Blob[], metadata: any) {
    setCapturedFrames(frames)
    handleFramesUpload(frames, metadata)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Live camera or AR scan — render fullscreen
  if (step === 'capture') {
    return (
      <Suspense fallback={
        <div className="fixed inset-0 z-50 bg-black flex items-center justify-center">
          <Loader2 size={24} className="text-[#1A8FD6] animate-spin" />
        </div>
      }>
        {scanMode === 'ar-scan' ? (
          <WebXRScan
            onFramesCaptured={handleXRCaptureComplete}
            onCancel={onCancel}
            onFallbackToStandard={() => { setScanMode('live-camera'); }}
            deviceModel={capabilities?.deviceModel ?? null}
          />
        ) : (
          <LiveCapture
            onFramesCaptured={handleLiveCaptureComplete}
            onCancel={onCancel}
            tier={capabilities?.tier ?? 'standard'}
            deviceModel={capabilities?.deviceModel ?? null}
          />
        )}
      </Suspense>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="card w-full max-w-lg mx-4 border border-[#1F1F23] max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
          <div className="flex items-center gap-3">
            {(step === 'upload' || step === 'instructions' || step === 'upload-splat') && (
              <button
                onClick={() => setStep(isMobile() ? 'choose' : 'instructions')}
                className="p-1 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
            )}
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">
                {step === 'detect' ? 'Detecting Device...' :
                 step === 'choose' ? 'Choose Scan Mode' :
                 step === 'instructions' ? 'Scan Your Store' :
                 step === 'upload' ? 'Upload Video' :
                 step === 'upload-splat' ? 'Upload 3D Scan' :
                 step === 'processing' ? 'Processing Scan' :
                 'Scan Complete'}
              </h3>
              <p className="text-[10px] text-[#A1A1A8] mt-0.5">
                {step === 'detect' ? 'Checking camera capabilities...' :
                 step === 'choose' ? 'We detected your device — pick the best mode' :
                 step === 'instructions' ? 'Video-based 3D mapping — no special hardware needed' :
                 step === 'upload' ? 'Upload a walkthrough video of your store' :
                 step === 'upload-splat' ? 'Load a Gaussian Splat from any scanning app' :
                 step === 'processing' ? 'Building your 3D model' :
                 'Your 3D space is ready to explore'}
              </p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-1.5 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5">
          {/* Detecting */}
          {step === 'detect' && (
            <div className="py-8 text-center">
              <Loader2 size={24} className="text-[#1A8FD6] animate-spin mx-auto mb-3" />
              <p className="text-xs text-[#A1A1A8]">Checking your device capabilities...</p>
            </div>
          )}

          {/* Choose scan mode */}
          {step === 'choose' && capabilities && (
            <div className="space-y-4">
              {/* Device badge */}
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#111113] border border-[#1F1F23]">
                <Smartphone size={14} className="text-[#A1A1A8]" />
                <span className="text-xs text-[#A1A1A8]">
                  {capabilities.deviceModel || 'Mobile device'}
                </span>
                {capabilities.hasLiDAR && (
                  <span className="ml-auto px-2 py-0.5 rounded-full bg-[#7C5CFF]/10 text-[#7C5CFF] text-[9px] font-semibold">
                    LiDAR
                  </span>
                )}
              </div>

              {!capabilities.rearCameraSupported && (
                <div className="px-3 py-2 rounded-lg bg-amber-400/5 border border-amber-400/15">
                  <p className="text-[10px] text-amber-400">
                    Camera requires HTTPS. Use "Upload 3D Scan" to load a file from Scaniverse or another scanning app.
                  </p>
                </div>
              )}

              {/* AR Scan option — only show for LiDAR devices on HTTPS */}
              {capabilities.hasLiDAR && capabilities.rearCameraSupported && (
                <button
                  onClick={() => { setScanMode('ar-scan'); setStep('capture') }}
                  className="w-full text-left p-4 rounded-xl border-2 border-[#7C5CFF]/30 bg-[#7C5CFF]/5 hover:border-[#7C5CFF]/50 transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[#7C5CFF]/10 flex items-center justify-center flex-shrink-0">
                      <Scan size={20} className="text-[#7C5CFF]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-[#F5F5F7]">AR Scan</p>
                        <span className="px-1.5 py-0.5 rounded bg-[#7C5CFF]/20 text-[#7C5CFF] text-[9px] font-bold">RECOMMENDED</span>
                      </div>
                      <p className="text-xs text-[#A1A1A8] mt-0.5">
                        Real-time 3D scanning using your LiDAR sensor. Walk through your store and watch the model build live.
                      </p>
                      <div className="flex items-center gap-3 mt-2 text-[10px] text-[#A1A1A8]/60">
                        <span className="flex items-center gap-1"><Layers size={10} /> Depth data</span>
                        <span className="flex items-center gap-1"><Eye size={10} /> AR overlay</span>
                        <span className="flex items-center gap-1"><Zap size={10} /> Best quality</span>
                      </div>
                    </div>
                    <ArrowRight size={16} className="text-[#7C5CFF] mt-1 opacity-50 group-hover:opacity-100 transition-opacity" />
                  </div>
                </button>
              )}

              {/* Live Camera option — only on HTTPS */}
              {capabilities.rearCameraSupported && (
                <button
                  onClick={() => { setScanMode('live-camera'); setStep('capture') }}
                  className={clsx(
                    'w-full text-left p-4 rounded-xl border-2 transition-all group',
                    capabilities.hasLiDAR
                      ? 'border-[#1F1F23] hover:border-[#2A2A30]'
                      : 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5 hover:border-[#1A8FD6]/50'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
                      <Camera size={20} className="text-[#1A8FD6]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-[#F5F5F7]">Live Camera</p>
                        {!capabilities.hasLiDAR && (
                          <span className="px-1.5 py-0.5 rounded bg-[#1A8FD6]/20 text-[#1A8FD6] text-[9px] font-bold">RECOMMENDED</span>
                        )}
                      </div>
                      <p className="text-xs text-[#A1A1A8] mt-0.5">
                        Open your camera and walk through the store. We capture frames automatically — works on any phone.
                      </p>
                      <div className="flex items-center gap-3 mt-2 text-[10px] text-[#A1A1A8]/60">
                        <span className="flex items-center gap-1"><Camera size={10} /> Any camera</span>
                        <span className="flex items-center gap-1"><Smartphone size={10} /> No app needed</span>
                      </div>
                    </div>
                    <ArrowRight size={16} className="text-[#1A8FD6] mt-1 opacity-50 group-hover:opacity-100 transition-opacity" />
                  </div>
                </button>
              )}

              {/* Video upload fallback */}
              <button
                onClick={() => { setScanMode('video-upload'); setStep('instructions') }}
                className="w-full text-left p-4 rounded-xl border-2 border-[#1F1F23] hover:border-[#2A2A30] transition-all group"
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#A1A1A8]/10 flex items-center justify-center flex-shrink-0">
                    <Upload size={20} className="text-[#A1A1A8]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[#F5F5F7]">Upload Video</p>
                    <p className="text-xs text-[#A1A1A8] mt-0.5">
                      Already have a walkthrough video? Upload it directly.
                    </p>
                  </div>
                  <ArrowRight size={16} className="text-[#A1A1A8] mt-1 opacity-50 group-hover:opacity-100 transition-opacity" />
                </div>
              </button>

              {/* 3D file upload (Gaussian Splat) */}
              <button
                onClick={() => { setScanMode('splat-upload'); setStep('upload-splat') }}
                className="w-full text-left p-4 rounded-xl border-2 border-[#17C5B0]/20 hover:border-[#17C5B0]/40 transition-all group"
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
                    <Box size={20} className="text-[#17C5B0]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[#F5F5F7]">Upload 3D Scan</p>
                    <p className="text-xs text-[#A1A1A8] mt-0.5">
                      Have a .splat or .ply file from Scaniverse, Polycam, or another scanning app? Load it directly.
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-[10px] text-[#A1A1A8]/60">
                      <span className="flex items-center gap-1"><Box size={10} /> Gaussian Splat</span>
                      <span className="flex items-center gap-1"><Eye size={10} /> Instant preview</span>
                    </div>
                  </div>
                  <ArrowRight size={16} className="text-[#17C5B0] mt-1 opacity-50 group-hover:opacity-100 transition-opacity" />
                </div>
              </button>
            </div>
          )}

          {/* Instructions (video upload path) */}
          {step === 'instructions' && (
            <div className="space-y-5">
              <div className="rounded-xl bg-[#1A8FD6]/5 border border-[#1A8FD6]/15 p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
                    <Video size={20} className="text-[#1A8FD6]" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[#F5F5F7]">How it works</p>
                    <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                      Record a walkthrough video of your store using any phone camera. Our AI
                      reconstructs a full 3D model from standard RGB video — no LiDAR or special sensors needed.
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2.5">
                <p className="text-xs font-semibold text-[#A1A1A8] uppercase tracking-wider">Tips for best results</p>
                {VIDEO_TIPS.map(({ icon: Icon, text }) => (
                  <div key={text} className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#111113] border border-[#1F1F23]">
                    <Icon size={14} className="text-[#17C5B0] flex-shrink-0" />
                    <p className="text-xs text-[#A1A1A8]">{text}</p>
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-3 pt-2">
                <div className="flex-1 text-[10px] text-[#A1A1A8]/50">
                  Supported: MP4, MOV, WebM • 30s–5min recommended
                </div>
                <button
                  onClick={() => setStep('upload')}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1A8FD6] text-white text-xs font-medium hover:bg-[#1A8FD6]/90 transition-colors"
                >
                  Continue
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Upload */}
          {step === 'upload' && (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-[#A1A1A8] block mb-1.5">Scan Name</label>
                <input
                  type="text"
                  value={scanName}
                  onChange={e => setScanName(e.target.value)}
                  placeholder="e.g. Main Floor, Back Room"
                  className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#4a4a52] focus:outline-none focus:border-[#1A8FD6]/50"
                />
              </div>

              <div
                onDragOver={e => { e.preventDefault(); setDragActive(true) }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={clsx(
                  'relative flex flex-col items-center justify-center gap-3 p-8 rounded-xl border-2 border-dashed cursor-pointer transition-all',
                  dragActive
                    ? 'border-[#1A8FD6] bg-[#1A8FD6]/5'
                    : file
                    ? 'border-[#17C5B0]/30 bg-[#17C5B0]/5'
                    : 'border-[#1F1F23] bg-[#111113] hover:border-[#2A2A30]'
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                {file ? (
                  <>
                    <div className="w-10 h-10 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center">
                      <CheckCircle2 size={20} className="text-[#17C5B0]" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-medium text-[#F5F5F7]">{file.name}</p>
                      <p className="text-[10px] text-[#A1A1A8] mt-0.5">{formatFileSize(file.size)}</p>
                    </div>
                    <button
                      onClick={e => { e.stopPropagation(); setFile(null) }}
                      className="text-[10px] text-[#A1A1A8] hover:text-red-400 transition-colors"
                    >
                      Remove & choose another
                    </button>
                  </>
                ) : (
                  <>
                    <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center">
                      <Upload size={20} className="text-[#1A8FD6]" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm text-[#F5F5F7]">
                        Drop video here or <span className="text-[#1A8FD6] font-medium">browse</span>
                      </p>
                      <p className="text-[10px] text-[#A1A1A8] mt-0.5">MP4, MOV, WebM up to 500 MB</p>
                    </div>
                  </>
                )}
              </div>

              {error && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-400/5 border border-red-400/15">
                  <AlertCircle size={14} className="text-red-400 flex-shrink-0" />
                  <p className="text-xs text-red-400">{error}</p>
                </div>
              )}

              <button
                onClick={handleVideoUpload}
                disabled={!file || !scanName.trim() || uploading}
                className={clsx(
                  'w-full flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs font-medium transition-all',
                  file && scanName.trim() && !uploading
                    ? 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90'
                    : 'bg-[#1F1F23] text-[#A1A1A8]/40 cursor-not-allowed'
                )}
              >
                {uploading ? (
                  <><Loader2 size={14} className="animate-spin" /> Uploading...</>
                ) : (
                  <><Upload size={14} /> Start Processing</>
                )}
              </button>
            </div>
          )}

          {/* Upload .splat file */}
          {step === 'upload-splat' && (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-[#A1A1A8] block mb-1.5">Scan Name</label>
                <input
                  type="text"
                  value={scanName}
                  onChange={e => setScanName(e.target.value)}
                  placeholder="e.g. Main Floor, Showroom"
                  className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#4a4a52] focus:outline-none focus:border-[#17C5B0]/50"
                />
              </div>

              <div
                onDragOver={e => { e.preventDefault(); setDragActive(true) }}
                onDragLeave={() => setDragActive(false)}
                onDrop={e => {
                  e.preventDefault(); setDragActive(false)
                  const f = e.dataTransfer.files[0]
                  if (f && (f.name.endsWith('.splat') || f.name.endsWith('.ply'))) {
                    setFile(f); setError(null)
                  } else { setError('Please upload a .splat or .ply file') }
                }}
                onClick={() => fileInputRef.current?.click()}
                className={clsx(
                  'relative flex flex-col items-center justify-center gap-3 p-8 rounded-xl border-2 border-dashed cursor-pointer transition-all',
                  dragActive ? 'border-[#17C5B0] bg-[#17C5B0]/5'
                    : file ? 'border-[#17C5B0]/30 bg-[#17C5B0]/5'
                    : 'border-[#1F1F23] bg-[#111113] hover:border-[#2A2A30]'
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".splat,.ply"
                  onChange={e => {
                    const f = e.target.files?.[0]
                    if (f) { setFile(f); setError(null) }
                  }}
                  className="hidden"
                />
                {file ? (
                  <>
                    <div className="w-10 h-10 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center">
                      <CheckCircle2 size={20} className="text-[#17C5B0]" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-medium text-[#F5F5F7]">{file.name}</p>
                      <p className="text-[10px] text-[#A1A1A8] mt-0.5">
                        {(file.size / (1024 * 1024)).toFixed(1)} MB
                        {file.name.endsWith('.splat') && ` • ~${Math.floor(file.size / 32).toLocaleString()} splats`}
                      </p>
                    </div>
                    <button
                      onClick={e => { e.stopPropagation(); setFile(null) }}
                      className="text-[10px] text-[#A1A1A8] hover:text-red-400 transition-colors"
                    >
                      Remove & choose another
                    </button>
                  </>
                ) : (
                  <>
                    <div className="w-10 h-10 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center">
                      <Box size={20} className="text-[#17C5B0]" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm text-[#F5F5F7]">
                        Drop .splat file here or <span className="text-[#17C5B0] font-medium">browse</span>
                      </p>
                      <p className="text-[10px] text-[#A1A1A8] mt-0.5">
                        .splat or .ply from Scaniverse, Polycam, or SuperSplat
                      </p>
                    </div>
                  </>
                )}
              </div>

              {error && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-400/5 border border-red-400/15">
                  <AlertCircle size={14} className="text-red-400 flex-shrink-0" />
                  <p className="text-xs text-red-400">{error}</p>
                </div>
              )}

              <button
                onClick={handleSplatUpload}
                disabled={!file || !scanName.trim() || uploading}
                className={clsx(
                  'w-full flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs font-medium transition-all',
                  file && scanName.trim() && !uploading
                    ? 'bg-[#17C5B0] text-[#0A0A0B] hover:bg-[#17C5B0]/90'
                    : 'bg-[#1F1F23] text-[#A1A1A8]/40 cursor-not-allowed'
                )}
              >
                {uploading ? (
                  <><Loader2 size={14} className="animate-spin" /> Loading...</>
                ) : (
                  <><Eye size={14} /> View 3D Space</>
                )}
              </button>
            </div>
          )}

          {/* Processing */}
          {step === 'processing' && (
            <div className="space-y-5 py-4">
              <div className="text-center">
                <div className="w-14 h-14 rounded-2xl bg-[#1A8FD6]/10 flex items-center justify-center mx-auto mb-4">
                  <Loader2 size={28} className="text-[#1A8FD6] animate-spin" />
                </div>
                <p className="text-sm font-semibold text-[#F5F5F7]">Building 3D Model</p>
                <p className="text-xs text-[#A1A1A8] mt-1">
                  {scanMode === 'ar-scan'
                    ? 'Processing LiDAR-enhanced scan with depth data'
                    : 'Reconstructing your store from captured frames'}
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#A1A1A8]">Progress</span>
                  <span className="font-mono text-[#1A8FD6]">{job?.progress_pct ?? 0}%</span>
                </div>
                <div className="h-2 rounded-full bg-[#1F1F23] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] transition-all duration-500"
                    style={{ width: `${job?.progress_pct ?? 0}%` }}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <ProcessingStep label="Extracting frames" done={(job?.progress_pct ?? 0) >= 10} active={(job?.progress_pct ?? 0) < 10} />
                <ProcessingStep label="Running depth estimation" done={(job?.progress_pct ?? 0) >= 30} active={(job?.progress_pct ?? 0) >= 10 && (job?.progress_pct ?? 0) < 30} />
                <ProcessingStep label="Camera pose estimation" done={(job?.progress_pct ?? 0) >= 50} active={(job?.progress_pct ?? 0) >= 30 && (job?.progress_pct ?? 0) < 50} />
                <ProcessingStep label="Building point cloud" done={(job?.progress_pct ?? 0) >= 75} active={(job?.progress_pct ?? 0) >= 50 && (job?.progress_pct ?? 0) < 75} />
                <ProcessingStep label="Generating 3D model" done={(job?.progress_pct ?? 0) >= 95} active={(job?.progress_pct ?? 0) >= 75 && (job?.progress_pct ?? 0) < 95} />
                <ProcessingStep label="Finalizing" done={(job?.progress_pct ?? 0) >= 100} active={(job?.progress_pct ?? 0) >= 95 && (job?.progress_pct ?? 0) < 100} />
              </div>

              {job?.frame_count && (
                <p className="text-center text-[10px] text-[#A1A1A8]/50 font-mono">
                  {job.frame_count.toLocaleString()} frames processed
                </p>
              )}
            </div>
          )}

          {/* Complete */}
          {step === 'complete' && (
            <div className="space-y-5 py-4">
              <div className="text-center">
                <div className="w-14 h-14 rounded-2xl bg-[#17C5B0]/10 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 size={28} className="text-[#17C5B0]" />
                </div>
                <p className="text-sm font-semibold text-[#F5F5F7]">3D Model Ready</p>
                <p className="text-xs text-[#A1A1A8] mt-1">
                  Your store has been reconstructed successfully
                </p>
              </div>

              {job && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="px-3 py-2.5 rounded-lg bg-[#111113] border border-[#1F1F23]">
                    <p className="text-[10px] text-[#A1A1A8]">Frames</p>
                    <p className="text-sm font-bold text-[#F5F5F7] font-mono">{job.frame_count?.toLocaleString()}</p>
                  </div>
                  <div className="px-3 py-2.5 rounded-lg bg-[#111113] border border-[#1F1F23]">
                    <p className="text-[10px] text-[#A1A1A8]">Status</p>
                    <p className="text-sm font-bold text-[#17C5B0]">Ready</p>
                  </div>
                </div>
              )}

              <button
                onClick={() => spaceId && onComplete(spaceId)}
                className="w-full flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold hover:bg-[#17C5B0]/90 transition-colors"
              >
                View 3D Space
                <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ProcessingStep({ label, done, active }: { label: string; done: boolean; active: boolean }) {
  return (
    <div className="flex items-center gap-2.5 px-3 py-1.5">
      {done ? (
        <CheckCircle2 size={14} className="text-[#17C5B0]" />
      ) : active ? (
        <Loader2 size={14} className="text-[#1A8FD6] animate-spin" />
      ) : (
        <div className="w-3.5 h-3.5 rounded-full border border-[#2A2A30]" />
      )}
      <span className={clsx(
        'text-xs',
        done ? 'text-[#17C5B0]' : active ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/40'
      )}>
        {label}
      </span>
    </div>
  )
}
