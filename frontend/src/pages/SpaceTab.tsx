import { useState, Suspense, lazy } from 'react'
import { clsx } from 'clsx'
import {
  Box, Camera, ScanLine, Layers, MapPin, Zap,
  Smartphone, Share2, Download, RefreshCw,
} from 'lucide-react'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import AnalyzingDataState from '@/components/AnalyzingDataState'
import { useIsDemo } from '@/hooks/useOrg'

const SpaceViewer = lazy(() => import('@/components/space/SpaceViewer'))

type ViewMode = '3d' | 'heatmap' | 'zones'

interface ZoneStat {
  id: string
  name: string
  traffic: number
  dwellMinutes: number
  conversionPct: number
  revenuePerSqFt: number
  trend: 'up' | 'down' | 'flat'
}

const demoZones: ZoneStat[] = [
  { id: 'counter', name: 'POS Counter', traffic: 342, dwellMinutes: 2.1, conversionPct: 94, revenuePerSqFt: 187, trend: 'up' },
  { id: 'display', name: 'Feature Display', traffic: 278, dwellMinutes: 3.8, conversionPct: 42, revenuePerSqFt: 124, trend: 'up' },
  { id: 'entrance', name: 'Entrance Zone', traffic: 512, dwellMinutes: 0.4, conversionPct: 68, revenuePerSqFt: 45, trend: 'flat' },
  { id: 'shelf-a', name: 'High-Value Shelf', traffic: 156, dwellMinutes: 4.2, conversionPct: 38, revenuePerSqFt: 203, trend: 'down' },
]

function ScanButton({ onScan }: { onScan: () => void }) {
  const [scanning, setScanning] = useState(false)

  function handleScan() {
    setScanning(true)
    onScan()
    setTimeout(() => setScanning(false), 3000)
  }

  return (
    <button
      onClick={handleScan}
      disabled={scanning}
      className={clsx(
        'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all',
        scanning
          ? 'bg-[#17C5B0]/20 text-[#17C5B0] border border-[#17C5B0]/30 animate-pulse'
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
  )
}

export default function SpaceTab() {
  const isDemo = useIsDemo()
  const [viewMode, setViewMode] = useState<ViewMode>('3d')
  const [showHotZones, setShowHotZones] = useState(true)
  const [lastScan] = useState('2 hours ago')

  if (!isDemo) {
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
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1A8FD6] text-white text-xs font-medium hover:bg-[#1A8FD6]/90 transition-colors shadow-[0_0_16px_rgba(26,143,214,0.25)]">
                <Camera size={14} />
                Open Scanner
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

  const zones = demoZones
  const totalTraffic = zones.reduce((s, z) => s + z.traffic, 0)
  const avgDwell = (zones.reduce((s, z) => s + z.dwellMinutes, 0) / zones.length).toFixed(1)
  const avgConversion = Math.round(zones.reduce((s, z) => s + z.conversionPct, 0) / zones.length)

  return (
    <div className="space-y-6">
      {/* Header */}
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">3D Space</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              LiDAR store mapping • Last scan: <span className="font-mono text-[#17C5B0]">{lastScan}</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ScanButton onScan={() => {}} />
            <button className="p-2 rounded-lg border border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors">
              <Share2 size={14} />
            </button>
            <button className="p-2 rounded-lg border border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors">
              <Download size={14} />
            </button>
          </div>
        </div>
      </ScrollReveal>

      {/* Stats */}
      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <MapPin size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Zones</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{zones.length}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <Zap size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">Total Traffic</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{totalTraffic}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                <RefreshCw size={16} className="text-[#7C5CFF]" />
              </div>
              <div>
                <p className="stat-label">Avg Dwell</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{avgDwell}m</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <Layers size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">Conversion</p>
                <p className="text-lg font-bold text-amber-400 font-mono">{avgConversion}%</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      {/* View mode toggle */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <div className="flex items-center gap-3">
          <div className="period-toggle">
            {([
              { key: '3d' as const, label: '3D View' },
              { key: 'heatmap' as const, label: 'Heatmap' },
              { key: 'zones' as const, label: 'Zones' },
            ]).map(m => (
              <button
                key={m.key}
                onClick={() => setViewMode(m.key)}
                className={viewMode === m.key ? 'period-btn-active' : 'period-btn-inactive'}
              >
                {m.label}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-1.5 text-[10px] text-[#A1A1A8] cursor-pointer ml-auto">
            <input
              type="checkbox"
              checked={showHotZones}
              onChange={e => setShowHotZones(e.target.checked)}
              className="rounded border-[#1F1F23] bg-[#111113] text-[#17C5B0] focus:ring-[#17C5B0]/20 w-3.5 h-3.5"
            />
            Show hot zones
          </label>
        </div>
      </ScrollReveal>

      {/* 3D Viewer */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <Suspense fallback={
          <div className="h-[400px] sm:h-[500px] rounded-xl bg-[#0A0A0B] border border-[#1F1F23] flex items-center justify-center">
            <p className="text-sm text-[#A1A1A8]/50">Loading 3D viewer...</p>
          </div>
        }>
          <SpaceViewer
            showHotZones={showHotZones && (viewMode === '3d' || viewMode === 'heatmap')}
            showSweep={viewMode === '3d'}
            className="h-[400px] sm:h-[500px]"
          />
        </Suspense>
      </ScrollReveal>

      {/* Zone Details Table */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
            <div className="flex items-center gap-2">
              <MapPin size={14} className="text-[#17C5B0]" />
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Zone Analytics</h3>
            </div>
            <p className="text-[10px] text-[#A1A1A8] mt-0.5">
              Traffic flow, dwell time, and conversion by store zone
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[500px]">
              <thead>
                <tr>
                  <th className="text-left">Zone</th>
                  <th className="text-right">Traffic</th>
                  <th className="text-right">Dwell Time</th>
                  <th className="text-right">Conversion</th>
                  <th className="text-right">Rev/sq ft</th>
                  <th className="text-center">Trend</th>
                </tr>
              </thead>
              <tbody>
                {zones.map(z => (
                  <tr key={z.id}>
                    <td className="font-medium text-[#F5F5F7]">{z.name}</td>
                    <td className="text-right font-mono text-[#F5F5F7]">{z.traffic}</td>
                    <td className="text-right font-mono text-[#A1A1A8]">{z.dwellMinutes}m</td>
                    <td className="text-right">
                      <span className={clsx(
                        'font-mono font-medium',
                        z.conversionPct >= 70 ? 'text-[#17C5B0]' : z.conversionPct >= 40 ? 'text-[#F5F5F7]' : 'text-amber-400',
                      )}>
                        {z.conversionPct}%
                      </span>
                    </td>
                    <td className="text-right font-mono text-[#F5F5F7]">${z.revenuePerSqFt}</td>
                    <td className="text-center">
                      <span className={clsx(
                        'text-[10px] font-medium px-1.5 py-0.5 rounded-full',
                        z.trend === 'up' ? 'bg-[#17C5B0]/10 text-[#17C5B0]' :
                        z.trend === 'down' ? 'bg-red-400/10 text-red-400' :
                        'bg-[#A1A1A8]/10 text-[#A1A1A8]',
                      )}>
                        {z.trend === 'up' ? '↑' : z.trend === 'down' ? '↓' : '→'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>

      {/* AI Recommendation */}
      <ScrollReveal variant="fadeUp" delay={0.2}>
        <div className="card p-4 border-[#17C5B0]/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
              <Zap size={16} className="text-[#17C5B0]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Spatial Optimization</h3>
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                Your <span className="text-[#F5F5F7] font-medium">Feature Display</span> has high dwell time (3.8m) but only 42% conversion.
                Consider adding price tags or promotional signage. Moving high-margin items from <span className="text-[#F5F5F7] font-medium">High-Value Shelf</span> (decreasing traffic)
                to the Feature Display could increase revenue by an estimated
                <span className="text-[#17C5B0] font-medium"> $340/month</span>.
                <span className="text-[#A1A1A8]/50"> (Confidence: 76%)</span>
              </p>
            </div>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
