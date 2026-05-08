import { useState, useEffect, Suspense, lazy } from 'react'
import { clsx } from 'clsx'
import {
  Layers, MapPin, Zap, Plus, Video, Trash2,
  Eye, Clock, Box, MoreVertical,
} from 'lucide-react'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { useOrgId } from '@/hooks/useOrg'
import { spacesService, type Space } from '@/lib/spaces-service'
import ScanWizard from '@/components/space/ScanWizard'

const SpaceViewer = lazy(() => import('@/components/space/SpaceViewer'))

export default function SpaceTab() {
  const orgId = useOrgId()
  const [spaces, setSpaces] = useState<Space[]>([])
  const [loading, setLoading] = useState(true)
  const [showWizard, setShowWizard] = useState(false)
  const [selectedSpace, setSelectedSpace] = useState<Space | null>(null)
  const [menuOpen, setMenuOpen] = useState<string | null>(null)

  useEffect(() => {
    loadSpaces()
  }, [orgId])

  async function loadSpaces() {
    setLoading(false)
    const data = await spacesService.list(orgId)
    setSpaces(data)
  }

  function handleScanComplete(spaceId: string) {
    setShowWizard(false)
    loadSpaces()
    spacesService.getById(spaceId).then(s => {
      if (s) setSelectedSpace(s)
    })
  }

  async function handleDelete(spaceId: string) {
    setMenuOpen(null)
    await spacesService.deleteSpace(spaceId)
    if (selectedSpace?.id === spaceId) setSelectedSpace(null)
    loadSpaces()
  }

  const readySpaces = spaces.filter(s => s.status === 'ready')
  const processingSpaces = spaces.filter(s => s.status === 'processing')
  const totalFrames = readySpaces.reduce((n, s) => n + (s.frame_count ?? 0), 0)

  if (selectedSpace) {
    return (
      <SpaceDetailView
        space={selectedSpace}
        onBack={() => setSelectedSpace(null)}
      />
    )
  }

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">3D Spaces</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              Video-based store mapping powered by LingBot-Map
            </p>
          </div>
          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1A8FD6] text-white text-xs font-medium hover:bg-[#1A8FD6]/90 transition-colors shadow-[0_0_16px_rgba(26,143,214,0.25)]"
          >
            <Plus size={14} />
            New Scan
          </button>
        </div>
      </ScrollReveal>

      {/* Stats bar */}
      {spaces.length > 0 && (
        <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <StaggerItem>
            <DashboardTiltCard className="card p-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                  <Box size={16} className="text-[#1A8FD6]" />
                </div>
                <div>
                  <p className="stat-label">Total Spaces</p>
                  <p className="text-lg font-bold text-[#F5F5F7] font-mono">{spaces.length}</p>
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
                  <p className="stat-label">Ready</p>
                  <p className="text-lg font-bold text-[#17C5B0] font-mono">{readySpaces.length}</p>
                </div>
              </div>
            </DashboardTiltCard>
          </StaggerItem>
          <StaggerItem>
            <DashboardTiltCard className="card p-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                  <Clock size={16} className="text-[#7C5CFF]" />
                </div>
                <div>
                  <p className="stat-label">Processing</p>
                  <p className="text-lg font-bold text-[#F5F5F7] font-mono">{processingSpaces.length}</p>
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
                  <p className="stat-label">Total Frames</p>
                  <p className="text-lg font-bold text-amber-400 font-mono">{totalFrames.toLocaleString()}</p>
                </div>
              </div>
            </DashboardTiltCard>
          </StaggerItem>
        </StaggerContainer>
      )}

      {/* Empty state */}
      {!loading && spaces.length === 0 && (
        <ScrollReveal variant="fadeUp">
          <div className="card p-8 border-[#1A8FD6]/10">
            <div className="flex flex-col items-center text-center max-w-md mx-auto">
              <div className="w-16 h-16 rounded-2xl bg-[#1A8FD6]/10 flex items-center justify-center mb-4">
                <Video size={32} className="text-[#1A8FD6]" />
              </div>
              <h3 className="text-base font-semibold text-[#F5F5F7]">Map Your Store in 3D</h3>
              <p className="text-xs text-[#A1A1A8] mt-2 leading-relaxed">
                Record a walkthrough video with any phone camera. LingBot-Map uses AI to reconstruct
                a full 3D model of your store — no LiDAR or special hardware required.
              </p>
              <div className="flex flex-wrap justify-center gap-4 mt-4 text-[10px] text-[#A1A1A8]/60">
                <span className="flex items-center gap-1"><Video size={10} /> Any phone camera</span>
                <span className="flex items-center gap-1"><MapPin size={10} /> Zone analytics</span>
                <span className="flex items-center gap-1"><Zap size={10} /> Heatmap overlays</span>
              </div>
              <button
                onClick={() => setShowWizard(true)}
                className="mt-6 flex items-center gap-2 px-6 py-2.5 rounded-lg bg-[#1A8FD6] text-white text-sm font-medium hover:bg-[#1A8FD6]/90 transition-colors shadow-[0_0_16px_rgba(26,143,214,0.25)]"
              >
                <Plus size={16} />
                Create First Scan
              </button>
            </div>
          </div>
        </ScrollReveal>
      )}

      {/* Space cards grid */}
      {spaces.length > 0 && (
        <StaggerContainer className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {spaces.map(space => (
            <StaggerItem key={space.id}>
              <div className="card overflow-hidden group hover:border-[#2A2A30] transition-all">
                {/* Thumbnail / preview */}
                <div
                  className="h-36 bg-[#111113] flex items-center justify-center cursor-pointer relative"
                  onClick={() => space.status === 'ready' && setSelectedSpace(space)}
                >
                  {space.status === 'ready' ? (
                    <>
                      <Box size={36} className="text-[#1A8FD6]/20" />
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1A8FD6] text-white text-xs font-medium">
                          <Eye size={12} />
                          View 3D
                        </div>
                      </div>
                    </>
                  ) : space.status === 'processing' ? (
                    <div className="text-center">
                      <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center mx-auto mb-2">
                        <div className="w-4 h-4 border-2 border-[#1A8FD6] border-t-transparent rounded-full animate-spin" />
                      </div>
                      <p className="text-[10px] text-[#A1A1A8]">Processing...</p>
                    </div>
                  ) : space.status === 'failed' ? (
                    <div className="text-center">
                      <p className="text-xs text-red-400">Failed</p>
                      <p className="text-[10px] text-[#A1A1A8] mt-0.5">{space.error_message}</p>
                    </div>
                  ) : (
                    <Box size={36} className="text-[#A1A1A8]/10" />
                  )}
                </div>

                {/* Info */}
                <div className="px-4 py-3 border-t border-[#1F1F23]">
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-[#F5F5F7] truncate">{space.name || 'Untitled Scan'}</p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className={clsx(
                          'text-[10px] font-medium px-1.5 py-0.5 rounded-full',
                          space.status === 'ready' ? 'bg-[#17C5B0]/10 text-[#17C5B0]' :
                          space.status === 'processing' ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]' :
                          space.status === 'failed' ? 'bg-red-400/10 text-red-400' :
                          'bg-[#A1A1A8]/10 text-[#A1A1A8]'
                        )}>
                          {space.status}
                        </span>
                        {space.frame_count && (
                          <span className="text-[10px] text-[#A1A1A8] font-mono">{space.frame_count.toLocaleString()} frames</span>
                        )}
                        {space.scan_duration_seconds && (
                          <span className="text-[10px] text-[#A1A1A8] font-mono">{Math.round(space.scan_duration_seconds / 60)}m scan</span>
                        )}
                      </div>
                    </div>
                    <div className="relative">
                      <button
                        onClick={() => setMenuOpen(menuOpen === space.id ? null : space.id)}
                        className="p-1 rounded text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
                      >
                        <MoreVertical size={14} />
                      </button>
                      {menuOpen === space.id && (
                        <>
                          <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(null)} />
                          <div className="absolute right-0 top-full mt-1 z-20 w-32 bg-[#111113] border border-[#1F1F23] rounded-lg shadow-xl overflow-hidden">
                            {space.status === 'ready' && (
                              <button
                                onClick={() => { setMenuOpen(null); setSelectedSpace(space) }}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
                              >
                                <Eye size={12} /> View
                              </button>
                            )}
                            <button
                              onClick={() => handleDelete(space.id)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-red-400/5 transition-colors"
                            >
                              <Trash2 size={12} /> Delete
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                  <p className="text-[10px] text-[#A1A1A8]/40 mt-2 font-mono">
                    {new Date(space.created_at).toLocaleDateString()}
                    {space.model_used && ` • ${space.model_used}`}
                  </p>
                </div>
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      )}

      {showWizard && (
        <ScanWizard
          orgId={orgId}
          onComplete={handleScanComplete}
          onCancel={() => setShowWizard(false)}
        />
      )}
    </div>
  )
}

function SpaceDetailView({ space, onBack }: { space: Space; onBack: () => void }) {
  const [viewMode, setViewMode] = useState<'3d' | 'heatmap' | 'zones'>('3d')
  const [showHotZones, setShowHotZones] = useState(true)

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="p-2 rounded-lg border border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            </button>
            <div>
              <h1 className="text-2xl font-bold text-[#F5F5F7]">{space.name || 'Untitled Scan'}</h1>
              <p className="text-sm text-[#A1A1A8] mt-0.5">
                {space.frame_count?.toLocaleString()} frames
                {space.scan_duration_seconds && ` • ${Math.round(space.scan_duration_seconds / 60)}m scan`}
                {space.model_used && ` • ${space.model_used}`}
              </p>
            </div>
          </div>
        </div>
      </ScrollReveal>

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

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <Suspense fallback={
          <div className="h-[400px] sm:h-[500px] rounded-xl bg-[#0A0A0B] border border-[#1F1F23] flex items-center justify-center">
            <p className="text-sm text-[#A1A1A8]/50">Loading 3D viewer...</p>
          </div>
        }>
          <SpaceViewer
            showHotZones={showHotZones}
            showSweep={viewMode === 'heatmap'}
            className="h-[400px] sm:h-[500px]"
          />
        </Suspense>
      </ScrollReveal>

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
                </tr>
              </thead>
              <tbody>
                {space.zones_configured ? (
                  <tr><td colSpan={5} className="text-center text-[#A1A1A8] text-xs py-6">Zone data loading...</td></tr>
                ) : (
                  <tr><td colSpan={5} className="text-center text-[#A1A1A8] text-xs py-6">
                    No zones configured yet. Use the zone editor in the 3D viewer to define store zones.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.2}>
        <div className="card p-4 border-[#17C5B0]/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
              <Zap size={16} className="text-[#17C5B0]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Spatial Optimization</h3>
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                Once zones are configured, Meridian will analyze traffic patterns and recommend layout
                optimizations to maximize revenue per square foot.
              </p>
            </div>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
