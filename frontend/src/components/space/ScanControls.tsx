import { useState, useEffect, useCallback } from 'react'
import { clsx } from 'clsx'
import {
  Box, Camera, ScanLine, Layers,
  Smartphone, CheckCircle2, AlertCircle, XCircle, Wifi,
} from 'lucide-react'
import ScrollReveal from '@/components/ScrollReveal'
import AnalyzingDataState from '@/components/AnalyzingDataState'

export type ScanCapability = 'ready' | 'camera-only' | 'not-supported' | 'checking'

interface XRSystem {
  isSessionSupported(mode: string): Promise<boolean>
}

export function useScanCapability(): { capability: ScanCapability; hasCamera: boolean; hasDepth: boolean } {
  const [capability, setCapability] = useState<ScanCapability>('checking')
  const [hasCamera, setHasCamera] = useState(false)
  const [hasDepth, setHasDepth] = useState(false)

  useEffect(() => {
    async function detect() {
      const mediaDevices = !!navigator.mediaDevices?.getUserMedia
      if (!mediaDevices) {
        setCapability('not-supported')
        return
      }

      try {
        const devices = await navigator.mediaDevices.enumerateDevices()
        const cam = devices.some(d => d.kind === 'videoinput')
        setHasCamera(cam)

        let depthDetected = false
        if ('xr' in navigator) {
          const xr = (navigator as Navigator & { xr?: XRSystem }).xr
          if (typeof xr?.isSessionSupported === 'function') {
            try {
              depthDetected = await xr.isSessionSupported('immersive-ar')
            } catch { depthDetected = false }
          }
        }
        setHasDepth(depthDetected)

        if (cam && depthDetected) setCapability('ready')
        else if (cam) setCapability('camera-only')
        else setCapability('not-supported')
      } catch {
        setCapability('not-supported')
      }
    }
    detect()
  }, [])

  return { capability, hasCamera, hasDepth }
}

export const capabilityConfig: Record<ScanCapability, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  ready:           { label: 'LiDAR Ready',   color: 'text-[#17C5B0]', icon: CheckCircle2 },
  'camera-only':   { label: 'Camera Only',   color: 'text-amber-400',  icon: AlertCircle },
  'not-supported': { label: 'Not Supported', color: 'text-red-400',    icon: XCircle },
  checking:        { label: 'Detecting...',  color: 'text-[#A1A1A8]',  icon: Wifi },
}

export function ScanButton({ onScan, isDemo }: { onScan: () => void; isDemo: boolean }) {
  const [scanning, setScanning] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const { capability } = useScanCapability()
  const capConfig = capabilityConfig[capability]
  const CapIcon = capConfig.icon

  const handleScan = useCallback(() => {
    if (isDemo) {
      setShowModal(true)
      return
    }
    if (capability === 'not-supported') return
    setScanning(true)
    onScan()
    setTimeout(() => setScanning(false), 3000)
  }, [isDemo, capability, onScan])

  return (
    <>
      <div className="flex items-center gap-2">
        <div className={clsx('flex items-center gap-1 text-[10px] font-mono', capConfig.color)}>
          <CapIcon size={10} />
          {capConfig.label}
        </div>
        <button
          onClick={handleScan}
          disabled={scanning || (!isDemo && capability === 'not-supported')}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all',
            scanning
              ? 'bg-[#17C5B0]/20 text-[#17C5B0] border border-[#17C5B0]/30 animate-pulse'
              : capability === 'not-supported' && !isDemo
              ? 'bg-[#1F1F23]/50 text-[#A1A1A8]/40 border border-[#1F1F23] cursor-not-allowed'
              : 'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/20 hover:bg-[#1A8FD6]/15',
          )}
        >
          {scanning ? (
            <>
              <ScanLine size={14} className="animate-spin" />
              Scanning...
            </>
          ) : (
            <>
              <Camera size={14} />
              New Scan
            </>
          )}
        </button>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowModal(false)}>
          <div className="card p-6 max-w-sm mx-4 border border-[#1F1F23]" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center">
                <ScanLine size={20} className="text-[#1A8FD6]" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7]">LiDAR Scan Simulation</h3>
                <p className="text-[10px] text-[#A1A1A8]">Demo mode</p>
              </div>
            </div>
            <p className="text-xs text-[#A1A1A8] leading-relaxed mb-4">
              In production, this launches a LiDAR scan using your device's depth sensor (iPhone 12 Pro+ or iPad Pro with LiDAR).
              The scan creates a 3D model of your store for traffic analysis and layout optimization.
            </p>
            <div className="space-y-1.5 mb-5">
              <p className="text-[10px] text-[#A1A1A8]/60 flex items-center gap-1.5">
                <Smartphone size={10} /> Requires LiDAR-equipped iOS device
              </p>
              <p className="text-[10px] text-[#A1A1A8]/60 flex items-center gap-1.5">
                <ScanLine size={10} /> 2-5 minute scan time
              </p>
              <p className="text-[10px] text-[#A1A1A8]/60 flex items-center gap-1.5">
                <Layers size={10} /> Outputs USDZ/GLB 3D model
              </p>
            </div>
            <button onClick={() => setShowModal(false)} className="w-full py-2 rounded-lg bg-[#1A8FD6] text-white text-xs font-medium hover:bg-[#1A8FD6]/90 transition-colors">
              Got it
            </button>
          </div>
        </div>
      )}
    </>
  )
}

export function ProductionSpaceSetup() {
  const { capability } = useScanCapability()
  const capConfig = capabilityConfig[capability]
  const CapIcon = capConfig.icon

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">3D Space</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            LiDAR store mapping & spatial analytics
          </p>
        </div>
      </ScrollReveal>

      <div className="card p-6 border-[#1A8FD6]/10">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
            <Box size={24} className="text-[#1A8FD6]" />
          </div>
          <div className="space-y-3">
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Set Up 3D Space Mapping</h3>
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                Use your iPhone or iPad's LiDAR scanner to create a 3D model of your store.
                Meridian will overlay foot traffic heatmaps, identify dead zones, and optimize your layout for revenue.
              </p>
            </div>
            <div className="flex flex-wrap gap-4 text-[10px] text-[#A1A1A8]/60">
              <span className="flex items-center gap-1"><Smartphone size={10} /> Requires LiDAR-equipped device</span>
              <span className="flex items-center gap-1"><ScanLine size={10} /> 2-5 minute scan</span>
              <span className="flex items-center gap-1"><Layers size={10} /> USDZ/GLB format</span>
            </div>
            <div className="flex items-center gap-3">
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1A8FD6] text-white text-xs font-medium hover:bg-[#1A8FD6]/90 transition-colors shadow-[0_0_16px_rgba(26,143,214,0.25)]">
                <Camera size={14} />
                Open Scanner
              </button>
              <div className={clsx('flex items-center gap-1 text-[10px] font-mono', capConfig.color)}>
                <CapIcon size={10} />
                {capConfig.label}
              </div>
            </div>
            {capability === 'not-supported' && (
              <p className="text-[10px] text-red-400/70">
                Your device does not support camera access. Use an iPhone 12 Pro or newer with LiDAR for best results.
              </p>
            )}
            {capability === 'camera-only' && (
              <p className="text-[10px] text-amber-400/70">
                Camera detected but no depth sensor. Photogrammetry will be used instead of LiDAR — results may vary.
              </p>
            )}
          </div>
        </div>
      </div>

      <AnalyzingDataState
        title="No scans yet"
        description="Once you scan your store, Meridian will generate a 3D model with traffic heatmaps, zone analytics, and layout optimization recommendations."
        compact
      />
    </div>
  )
}
