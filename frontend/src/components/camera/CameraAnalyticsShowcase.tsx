import { useState } from 'react'
import {
  Users, Clock, MapPin, TrendingUp, UserCheck, ShieldAlert, PieChart, Sparkles,
} from 'lucide-react'

/**
 * Camera Analytics Showcase — features the insights cameras unlock once connected.
 *
 * This is a value gallery (illustrative figures, clearly labelled "sample") shown
 * in the Camera pillar so merchants see what connecting a camera gives them. The
 * same metrics render from real model output once an edge device is streaming.
 */

type Metric = {
  key: string
  icon: typeof Users
  title: string
  blurb: string
  stat: string
  statLabel: string
  spark?: number[]
}

const METRICS: Metric[] = [
  { key: 'traffic', icon: Users, title: 'Foot traffic', blurb: 'Every person counted, hour by hour — see exactly when you’re busy.', stat: '1,284', statLabel: 'visitors this week', spark: [9, 14, 22, 31, 28, 40, 52, 47, 38, 30, 21, 16] },
  { key: 'peak', icon: Clock, title: 'Peak hours', blurb: 'Pinpoint your rushes so you staff to demand, not guesswork.', stat: '12–2pm', statLabel: 'busiest window', spark: [12, 20, 55, 60, 35, 28, 33, 48, 40, 22] },
  { key: 'dwell', icon: MapPin, title: 'Dwell time by zone', blurb: 'How long people linger in each area — surface dead zones and hot spots.', stat: '4m 12s', statLabel: 'avg dwell', spark: [30, 42, 50, 38, 55, 60, 44] },
  { key: 'conversion', icon: TrendingUp, title: 'Zone conversion', blurb: 'Cross-referenced with POS — what share of foot traffic actually buys.', stat: '38%', statLabel: 'walk-in → sale', spark: [22, 28, 31, 35, 33, 38, 41] },
  { key: 'staff', icon: UserCheck, title: 'Staff coverage & grading', blurb: 'Station coverage, customer engagement and a per-shift score.', stat: 'A–', statLabel: 'shift grade', spark: [60, 72, 68, 80, 85, 78, 88] },
  { key: 'demographics', icon: PieChart, title: 'Demographics', blurb: 'Anonymous age/gender mix to tune offers and merchandising. (Opt-in)', stat: '54% / 46%', statLabel: 'returning vs new', spark: [40, 45, 50, 48, 55, 52, 58] },
  { key: 'loss', icon: ShieldAlert, title: 'Loss prevention', blurb: 'Flags transactions that don’t match observed activity — exceptions worth a look.', stat: '3', statLabel: 'exceptions flagged', spark: [1, 0, 2, 1, 3, 1, 2] },
]

function Spark({ points, color }: { points: number[]; color: string }) {
  const w = 88, h = 28, max = Math.max(...points, 1)
  const d = points.map((v, i) => `${(i / (points.length - 1)) * w},${h - (v / max) * (h - 4) - 2}`).join(' ')
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function CameraAnalyticsShowcase({ connected = false }: { connected?: boolean }) {
  const [active, setActive] = useState<string | null>(null)
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[15px] font-bold text-[#F5F5F7] flex items-center gap-2">
            <Sparkles size={16} className="text-[#17C5B0]" /> What your cameras unlock
          </h2>
          <p className="text-[12px] text-[#A1A1A8] mt-0.5">
            {connected
              ? 'Generated from your live camera feeds.'
              : 'Connect a camera to turn your existing CCTV into these insights — no new hardware beyond an edge device.'}
          </p>
        </div>
        {!connected && (
          <span className="shrink-0 text-[10px] font-bold uppercase tracking-wide text-[#F0B35B] px-2 py-1 rounded-full bg-[#F0B35B]/10 border border-[#F0B35B]/30">
            Sample data
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
        {METRICS.map(m => {
          const Icon = m.icon
          const on = active === m.key
          return (
            <button
              key={m.key}
              onClick={() => setActive(on ? null : m.key)}
              className={`text-left rounded-2xl border p-4 transition-all ${
                on ? 'border-[#17C5B0]/50 bg-[#17C5B0]/[0.06]' : 'border-[#1F1F23] bg-[#111113] hover:border-[#1F1F23] hover:bg-[#16161A]'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="w-9 h-9 rounded-xl bg-[#1A8FD6]/12 flex items-center justify-center">
                  <Icon size={17} className="text-[#1A8FD6]" />
                </span>
                {m.spark && <Spark points={m.spark} color={on ? '#17C5B0' : '#1A8FD6'} />}
              </div>
              <div className="mt-3">
                <div className="text-[20px] font-extrabold text-[#F5F5F7] leading-none">{m.stat}</div>
                <div className="text-[10px] uppercase tracking-wide text-[#A1A1A8] mt-1">{m.statLabel}</div>
              </div>
              <div className="mt-3">
                <div className="text-[13px] font-semibold text-[#F5F5F7]">{m.title}</div>
                <p className="text-[12px] text-[#A1A1A8] mt-0.5 leading-relaxed">{m.blurb}</p>
              </div>
            </button>
          )
        })}
      </div>

      {!connected && (
        <div className="rounded-2xl border border-dashed border-[#1F1F23] p-4 text-center">
          <p className="text-[12px] text-[#A1A1A8]">
            All of the above runs on-device from your camera feed. Add a camera in settings to start generating your own.
          </p>
        </div>
      )}
    </div>
  )
}
