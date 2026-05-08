import { clsx } from 'clsx'
import {
  Video, Camera, Plus,
} from 'lucide-react'
import ScrollReveal from '@/components/ScrollReveal'
import AnalyzingDataState from '@/components/AnalyzingDataState'

export function ScanButton({ onScan }: { onScan: () => void; isDemo?: boolean }) {
  return (
    <button
      onClick={onScan}
      className={clsx(
        'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all',
        'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/20 hover:bg-[#1A8FD6]/15',
      )}
    >
      <Camera size={14} />
      New Scan
    </button>
  )
}

export function ProductionSpaceSetup() {
  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">3D Space</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Video-based store mapping & spatial analytics
          </p>
        </div>
      </ScrollReveal>

      <div className="card p-6 border-[#1A8FD6]/10">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
            <Video size={24} className="text-[#1A8FD6]" />
          </div>
          <div className="space-y-3">
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Set Up 3D Space Mapping</h3>
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                Record a walkthrough video of your store with any phone camera. LingBot-Map uses AI to
                reconstruct a full 3D model — no LiDAR or special hardware required.
                Meridian overlays foot traffic heatmaps, identifies dead zones, and optimizes your layout for revenue.
              </p>
            </div>
            <div className="flex flex-wrap gap-4 text-[10px] text-[#A1A1A8]/60">
              <span className="flex items-center gap-1"><Camera size={10} /> Any phone camera</span>
              <span className="flex items-center gap-1"><Video size={10} /> 30s–5min video</span>
            </div>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1A8FD6] text-white text-xs font-medium hover:bg-[#1A8FD6]/90 transition-colors shadow-[0_0_16px_rgba(26,143,214,0.25)]">
              <Plus size={14} />
              Create First Scan
            </button>
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
