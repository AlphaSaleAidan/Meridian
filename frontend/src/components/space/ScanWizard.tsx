import { useState, useRef, useCallback, useEffect } from 'react'
import { clsx } from 'clsx'
import {
  Video, Upload, X, CheckCircle2, AlertCircle,
  Smartphone, ArrowRight, Loader2, RotateCcw,
  Camera, Monitor, ChevronLeft,
} from 'lucide-react'
import { spacesService, type ProcessingJob } from '@/lib/spaces-service'

type WizardStep = 'instructions' | 'upload' | 'processing' | 'complete'

interface ScanWizardProps {
  orgId: string
  onComplete: (spaceId: string) => void
  onCancel: () => void
}

const TIPS = [
  { icon: Smartphone, text: 'Walk slowly through the entire store' },
  { icon: Camera, text: 'Keep the camera at chest height, pointed straight ahead' },
  { icon: RotateCcw, text: 'Overlap areas — scan aisles in a snake pattern' },
  { icon: Monitor, text: 'Good lighting improves 3D quality significantly' },
]

export default function ScanWizard({ orgId, onComplete, onCancel }: ScanWizardProps) {
  const [step, setStep] = useState<WizardStep>('instructions')
  const [scanName, setScanName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [job, setJob] = useState<ProcessingJob | null>(null)
  const [spaceId, setSpaceId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
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

  async function handleUpload() {
    if (!file || !scanName.trim()) return
    setUploading(true)
    setError(null)

    try {
      const result = await spacesService.uploadVideo(orgId, scanName.trim(), file)
      setSpaceId(result.spaceId)
      setStep('processing')

      pollRef.current = setInterval(async () => {
        const status = await spacesService.getJobStatus(result.jobId)
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
    } catch {
      setError('Upload failed. Please try again.')
      setUploading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="card w-full max-w-lg mx-4 border border-[#1F1F23] max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
          <div className="flex items-center gap-3">
            {step !== 'instructions' && step !== 'complete' && (
              <button
                onClick={() => setStep(step === 'upload' ? 'instructions' : 'upload')}
                className="p-1 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
            )}
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">
                {step === 'instructions' ? 'Scan Your Store' :
                 step === 'upload' ? 'Upload Video' :
                 step === 'processing' ? 'Processing Scan' :
                 'Scan Complete'}
              </h3>
              <p className="text-[10px] text-[#A1A1A8] mt-0.5">
                {step === 'instructions' ? 'Video-based 3D mapping — no special hardware needed' :
                 step === 'upload' ? 'Upload a walkthrough video of your store' :
                 step === 'processing' ? 'LingBot-Map is building your 3D model' :
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
          {/* Step 1: Instructions */}
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
                      Record a walkthrough video of your store using any phone camera. Our AI (LingBot-Map)
                      reconstructs a full 3D model from standard RGB video — no LiDAR or special sensors needed.
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2.5">
                <p className="text-xs font-semibold text-[#A1A1A8] uppercase tracking-wider">Tips for best results</p>
                {TIPS.map(({ icon: Icon, text }) => (
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

          {/* Step 2: Upload */}
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
                onClick={handleUpload}
                disabled={!file || !scanName.trim() || uploading}
                className={clsx(
                  'w-full flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs font-medium transition-all',
                  file && scanName.trim() && !uploading
                    ? 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90'
                    : 'bg-[#1F1F23] text-[#A1A1A8]/40 cursor-not-allowed'
                )}
              >
                {uploading ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload size={14} />
                    Start Processing
                  </>
                )}
              </button>
            </div>
          )}

          {/* Step 3: Processing */}
          {step === 'processing' && (
            <div className="space-y-5 py-4">
              <div className="text-center">
                <div className="w-14 h-14 rounded-2xl bg-[#1A8FD6]/10 flex items-center justify-center mx-auto mb-4">
                  <Loader2 size={28} className="text-[#1A8FD6] animate-spin" />
                </div>
                <p className="text-sm font-semibold text-[#F5F5F7]">Building 3D Model</p>
                <p className="text-xs text-[#A1A1A8] mt-1">
                  LingBot-Map is reconstructing your store in 3D
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

          {/* Step 4: Complete */}
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
