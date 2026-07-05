import { useCallback, useEffect, useMemo, useState } from 'react'
import { Video, Plus, Wifi, WifiOff, Activity, Users, Clock, TrendingUp, Eye, MapPin, ArrowUpRight, Timer } from 'lucide-react'
import { useIsDemo, useOrgId } from '@/hooks/useOrg'
import { getActiveBusinessType, isCanadaPath } from '@/lib/demo-context'
import { api } from '@/lib/api'
import { getAuthHeaders } from '@/lib/supabase'
import CameraSetupWizard from '@/components/vision/CameraSetupWizard'
import ScrollReveal from '@/components/ScrollReveal'

interface CameraDevice {
  id: string
  name: string
  location: string
  online: boolean
  everSeen: boolean
  rtspUrl: string
  lastHeartbeat: string
  zones: string[]
  metrics: {
    entriesTotal: number
    exitsTotal: number
    avgOccupancy: number
    avgDwellSec: number | null
    conversionRate: number | null
  }
}

interface TrafficBucket {
  time: string
  entries: number
  exits: number
  occupancy: number
}

interface TrafficSummary {
  total_entries: number
  total_exits: number
  avg_occupancy: number
  avg_queue_wait_sec: number
  avg_conversion_rate: number
  buckets_count: number
}

const ONLINE_WINDOW_MS = 5 * 60 * 1000

function heartbeatLabel(iso: string | null): string {
  if (!iso) return 'Never'
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 0) return 'Just now'
  const mins = Math.floor(ms / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

// ── Demo data (demo mode only — real merchants get live API data below) ──

function generateDemoCameras(): CameraDevice[] {
  const biz = getActiveBusinessType()
  const locations: Record<string, string[]> = {
    restaurant: ['Front Entrance', 'Dining Room', 'Bar Area', 'Kitchen Pass'],
    coffee_shop: ['Main Door', 'Counter Area', 'Seating Zone', 'Drive-Through'],
    fast_food: ['Entrance', 'Order Counter', 'Drive-Through Lane', 'Parking Lot'],
    auto_shop: ['Service Bay 1', 'Waiting Room', 'Front Desk', 'Parking'],
    smoke_shop: ['Entry Door', 'Display Wall', 'Checkout', 'Back Room'],
  }
  const locs = locations[biz] || locations.restaurant

  return locs.map((loc, i) => ({
    id: `cam-${i + 1}`,
    name: `Camera ${i + 1}`,
    location: loc,
    online: i < 3,
    everSeen: i < 3,
    rtspUrl: `rtsp://192.168.1.${100 + i}:554/stream1`,
    lastHeartbeat: i < 3 ? `${Math.floor(Math.random() * 30) + 1}s ago` : 'Never',
    zones: i === 0 ? ['entry', 'exit'] : i === 1 ? ['browse', 'dwell'] : ['queue'],
    metrics: {
      entriesTotal: Math.floor(Math.random() * 800) + 200,
      exitsTotal: Math.floor(Math.random() * 750) + 180,
      avgOccupancy: Math.round((Math.random() * 15 + 3) * 10) / 10,
      avgDwellSec: Math.floor(Math.random() * 300) + 60,
      conversionRate: Math.round((Math.random() * 0.4 + 0.3) * 100) / 100,
    },
  }))
}

function generateTrafficTimeline(): TrafficBucket[] {
  const buckets: TrafficBucket[] = []
  for (let h = 6; h <= 22; h++) {
    const peak = h >= 11 && h <= 14 ? 1.8 : h >= 17 && h <= 20 ? 1.5 : 1
    buckets.push({
      time: `${h}:00`,
      entries: Math.floor((Math.random() * 20 + 5) * peak),
      exits: Math.floor((Math.random() * 18 + 4) * peak),
      occupancy: Math.floor((Math.random() * 12 + 3) * peak),
    })
  }
  return buckets
}

function demoSummary(cams: CameraDevice[]): TrafficSummary {
  const online = cams.filter(c => c.online)
  return {
    total_entries: online.reduce((s, c) => s + c.metrics.entriesTotal, 0),
    total_exits: online.reduce((s, c) => s + c.metrics.exitsTotal, 0),
    avg_occupancy: online.length ? Math.round(online.reduce((s, c) => s + c.metrics.avgOccupancy, 0) / online.length * 10) / 10 : 0,
    avg_queue_wait_sec: 74,
    avg_conversion_rate: online.length ? online.reduce((s, c) => s + (c.metrics.conversionRate ?? 0), 0) / online.length : 0,
    buckets_count: online.length * 32,
  }
}

// Map API rows → CameraDevice, folding per-camera traffic aggregates in.
function mapApiCameras(rows: any[], traffic: any[]): CameraDevice[] {
  const perCam: Record<string, { entries: number; exits: number; occ: number[]; conv: number[] }> = {}
  for (const t of traffic) {
    const key = t.camera_id
    if (!key) continue
    const agg = (perCam[key] ||= { entries: 0, exits: 0, occ: [], conv: [] })
    agg.entries += t.entries || 0
    agg.exits += t.exits || 0
    if (t.occupancy_avg != null) agg.occ.push(t.occupancy_avg)
    if (t.conversion_rate != null) agg.conv.push(t.conversion_rate)
  }
  const avg = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0)

  return rows.map((c, i) => {
    const hb = c.last_heartbeat || null
    const online = !!hb && Date.now() - new Date(hb).getTime() < ONLINE_WINDOW_MS
    let zones: string[] = []
    try {
      const zc = typeof c.zone_config === 'string' ? JSON.parse(c.zone_config) : c.zone_config
      zones = zc && typeof zc === 'object' ? Object.keys(zc) : []
    } catch { /* zone_config unparseable — show none */ }
    const agg = perCam[c.id]
    return {
      id: c.id,
      name: c.name || `Camera ${i + 1}`,
      location: c.location || c.name || `Camera ${i + 1}`,
      online,
      everSeen: !!hb,
      rtspUrl: c.rtsp_url || '',
      lastHeartbeat: heartbeatLabel(hb),
      zones,
      metrics: {
        entriesTotal: agg?.entries ?? 0,
        exitsTotal: agg?.exits ?? 0,
        avgOccupancy: Math.round(avg(agg?.occ ?? []) * 10) / 10,
        avgDwellSec: null,
        conversionRate: agg?.conv?.length ? avg(agg.conv) : null,
      },
    }
  })
}

// Aggregate raw 15-min buckets into an hourly today-timeline.
function buildTimeline(traffic: any[]): TrafficBucket[] {
  const today = new Date().toISOString().slice(0, 10)
  const byHour: Record<number, TrafficBucket & { occN: number }> = {}
  for (const t of traffic) {
    const b = String(t.bucket || '')
    if (!b.startsWith(today)) continue
    const h = new Date(b).getHours()
    const slot = (byHour[h] ||= { time: `${h}:00`, entries: 0, exits: 0, occupancy: 0, occN: 0 })
    slot.entries += t.entries || 0
    slot.exits += t.exits || 0
    if (t.occupancy_avg != null) { slot.occupancy += t.occupancy_avg; slot.occN += 1 }
  }
  return Object.keys(byHour).map(Number).sort((a, b) => a - b).map(h => {
    const s = byHour[h]
    return { time: s.time, entries: s.entries, exits: s.exits, occupancy: s.occN ? Math.round(s.occupancy / s.occN) : 0 }
  })
}

export default function CameraIntelligencePage() {
  const isDemo = useIsDemo()
  const orgId = useOrgId()

  const [cameras, setCameras] = useState<CameraDevice[]>(() => (isDemo ? generateDemoCameras() : []))
  const [traffic, setTraffic] = useState<TrafficBucket[]>(() => (isDemo ? generateTrafficTimeline() : []))
  const [summary, setSummary] = useState<TrafficSummary | null>(null)
  const [loading, setLoading] = useState(!isDemo)
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null)
  const [showAddCamera, setShowAddCamera] = useState(false)

  const loadReal = useCallback(async () => {
    if (isDemo || !orgId) return
    setLoading(true)
    try {
      const [camRes, trafficRes] = await Promise.all([
        api.cameras(orgId),
        (async () => {
          const headers = await getAuthHeaders()
          const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/vision/traffic/${orgId}?days=7`, {
            credentials: 'include',
            headers: { ...headers, Accept: 'application/json' },
          })
          if (!res.ok) return { traffic: [], summary: null }
          return res.json()
        })(),
      ])
      const rows = trafficRes.traffic || []
      setCameras(mapApiCameras(camRes.cameras || [], rows))
      setTraffic(buildTimeline(rows))
      setSummary(trafficRes.summary || null)
    } catch {
      // keep whatever we had; page shows empty state rather than fake numbers
    } finally {
      setLoading(false)
    }
  }, [isDemo, orgId])

  useEffect(() => { void loadReal() }, [loadReal])

  const effectiveSummary = useMemo<TrafficSummary>(() => {
    if (isDemo) return demoSummary(cameras)
    return summary || { total_entries: 0, total_exits: 0, avg_occupancy: 0, avg_queue_wait_sec: 0, avg_conversion_rate: 0, buckets_count: 0 }
  }, [isDemo, cameras, summary])

  const onlineCount = cameras.filter(c => c.online).length
  const hasTraffic = isDemo || (effectiveSummary.buckets_count ?? 0) > 0
  const maxTraffic = Math.max(...traffic.map(t => t.entries), 1)

  const cards = [
    { label: 'Walk-ins (7 days)', value: effectiveSummary.total_entries.toLocaleString(), icon: Users, color: '#17C5B0' },
    { label: 'Walk-outs (7 days)', value: effectiveSummary.total_exits.toLocaleString(), icon: TrendingUp, color: '#1A8FD6' },
    { label: 'Avg Occupancy', value: `${effectiveSummary.avg_occupancy}`, icon: MapPin, color: '#f59e0b' },
    { label: 'Avg Queue Wait', value: effectiveSummary.avg_queue_wait_sec ? `${Math.round(effectiveSummary.avg_queue_wait_sec)}s` : '—', icon: Timer, color: '#e5484d' },
    { label: 'Walk-in → Sale', value: hasTraffic ? `${Math.round(effectiveSummary.avg_conversion_rate * 100)}%` : '—', icon: Activity, color: '#7c3aed' },
  ]

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Camera Intelligence</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              {cameras.length === 0 && !loading
                ? 'No cameras connected yet • Foot traffic & behavior analytics'
                : `${onlineCount} of ${cameras.length} camera${cameras.length === 1 ? '' : 's'} online • Real-time foot traffic & behavior analytics`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isDemo && (
              <a
                href={isCanadaPath() ? '/canada/demo/camera-analytics' : '/demo/camera-analytics'}
                className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium rounded-lg border border-[#7c3aed]/30 bg-[#7c3aed]/10 text-[#7c3aed] hover:bg-[#7c3aed]/20 transition-colors"
              >
                <Eye size={13} /> Live Camera Demo <ArrowUpRight size={11} />
              </a>
            )}
            {!isDemo && (
              <button onClick={() => setShowAddCamera(true)} className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium rounded-lg bg-[#17C5B0] text-[#0A0A0B] hover:bg-[#14b3a0] transition-colors">
                <Plus size={13} /> Add Camera
              </button>
            )}
          </div>
        </div>
      </ScrollReveal>

      {/* Hard numbers — real merchants see live vision_traffic data */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3" data-walkthrough="camera-stats">
        {cards.map(card => (
          <div key={card.label} className="bg-[#111113] rounded-xl p-4 border border-[#1F1F23]">
            <div className="flex items-center gap-2 mb-2">
              <card.icon size={14} style={{ color: card.color }} />
              <span className="text-[11px] text-[#A1A1A8]">{card.label}</span>
            </div>
            <p className="text-xl font-bold text-[#F5F5F7]">{card.value}</p>
          </div>
        ))}
      </div>

      {!isDemo && !hasTraffic && !loading && (
        <div className="bg-[#111113] rounded-xl p-5 border border-[#1F1F23] text-center">
          <p className="text-[13px] text-[#F5F5F7] font-medium">
            {cameras.length === 0 ? 'Connect a camera to start measuring walk-ins, occupancy and conversion' : 'Waiting for first data from your cameras'}
          </p>
          <p className="text-[11px] text-[#A1A1A8] mt-1">
            {cameras.length === 0
              ? 'The numbers above go live as soon as your first camera reports in — typically within 15 minutes of setup.'
              : 'Cameras report every 15 minutes. Numbers appear here automatically.'}
          </p>
        </div>
      )}

      {/* Traffic Timeline */}
      {(isDemo || traffic.length > 0) && (
        <div className="bg-[#111113] rounded-xl p-5 border border-[#1F1F23]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[14px] font-semibold text-[#F5F5F7]">Today's Traffic</h2>
            <span className="text-[11px] text-[#A1A1A8]">All cameras combined</span>
          </div>
          <div className="flex items-end gap-1 h-32">
            {traffic.map((bucket, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full flex flex-col items-center">
                  <div
                    className="w-full rounded-t bg-[#17C5B0]/60"
                    style={{ height: `${(bucket.entries / maxTraffic) * 100}px` }}
                  />
                </div>
                {i % 3 === 0 && (
                  <span className="text-[9px] text-[#A1A1A8]/50 font-mono">{bucket.time}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Camera Grid */}
      <div>
        <h2 className="text-[14px] font-semibold text-[#F5F5F7] mb-3">Connected Cameras</h2>
        {cameras.length === 0 && !loading ? (
          <div className="bg-[#111113] rounded-xl p-8 border border-[#1F1F23] text-center">
            <Video size={22} className="mx-auto text-[#A1A1A8] mb-2" />
            <p className="text-[13px] text-[#F5F5F7] font-medium">No cameras yet</p>
            <p className="text-[11px] text-[#A1A1A8] mt-1 mb-4">Add your first camera — any RTSP-capable IP camera works.</p>
            <button onClick={() => setShowAddCamera(true)} className="px-4 py-2 text-[12px] font-medium rounded-lg bg-[#17C5B0] text-[#0A0A0B] hover:bg-[#14b3a0] transition-colors">
              Add Camera
            </button>
          </div>
        ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {cameras.map(cam => (
            <div
              key={cam.id}
              onClick={() => setSelectedCamera(selectedCamera === cam.id ? null : cam.id)}
              className={`bg-[#111113] rounded-xl p-4 border cursor-pointer transition-all ${
                selectedCamera === cam.id ? 'border-[#17C5B0]/50 bg-[#17C5B0]/5' : 'border-[#1F1F23] hover:border-[#2A2A2E]'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    cam.online ? 'bg-[#17C5B0]/10' : 'bg-[#A1A1A8]/10'
                  }`}>
                    <Video size={14} className={cam.online ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'} />
                  </div>
                  <div>
                    <p className="text-[13px] font-medium text-[#F5F5F7]">{cam.location}</p>
                    <p className="text-[10px] text-[#A1A1A8] font-mono">{cam.name}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {cam.online ? (
                    <><Wifi size={12} className="text-[#17C5B0]" /><span className="text-[10px] text-[#17C5B0]">Live</span></>
                  ) : !cam.everSeen ? (
                    <><WifiOff size={12} className="text-[#A1A1A8]" /><span className="text-[10px] text-[#A1A1A8]">Waiting for device</span></>
                  ) : (
                    <><WifiOff size={12} className="text-red-400" /><span className="text-[10px] text-red-400">Offline</span></>
                  )}
                </div>
              </div>

              {cam.everSeen && (
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#1F1F23]">
                  <div>
                    <p className="text-[10px] text-[#A1A1A8]">Walk-ins</p>
                    <p className="text-[13px] font-semibold text-[#F5F5F7]">{cam.metrics.entriesTotal}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#A1A1A8]">Walk-outs</p>
                    <p className="text-[13px] font-semibold text-[#F5F5F7]">{cam.metrics.exitsTotal}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#A1A1A8]">{cam.metrics.avgDwellSec != null ? 'Avg Dwell' : 'Occupancy'}</p>
                    <p className="text-[13px] font-semibold text-[#F5F5F7]">
                      {cam.metrics.avgDwellSec != null ? `${Math.round(cam.metrics.avgDwellSec / 60)}m` : cam.metrics.avgOccupancy}
                    </p>
                  </div>
                </div>
              )}

              {selectedCamera === cam.id && cam.everSeen && (
                <div className="mt-3 pt-3 border-t border-[#1F1F23] space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-[#0A0A0B] rounded-lg p-2.5">
                      <p className="text-[10px] text-[#A1A1A8]">Walk-in → Sale</p>
                      <p className="text-[15px] font-bold text-[#17C5B0]">
                        {cam.metrics.conversionRate != null ? `${Math.round(cam.metrics.conversionRate * 100)}%` : '—'}
                      </p>
                    </div>
                    <div className="bg-[#0A0A0B] rounded-lg p-2.5">
                      <p className="text-[10px] text-[#A1A1A8]">Avg Occupancy</p>
                      <p className="text-[15px] font-bold text-[#1A8FD6]">{cam.metrics.avgOccupancy}</p>
                    </div>
                  </div>
                  {cam.zones.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {cam.zones.map(zone => (
                        <span key={zone} className="px-2 py-0.5 rounded text-[10px] font-medium bg-[#7c3aed]/10 text-[#7c3aed] border border-[#7c3aed]/20">
                          {zone}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="text-[10px] text-[#A1A1A8]">
                    <Clock size={10} className="inline mr-1" />Last heartbeat: {cam.lastHeartbeat}
                  </p>
                </div>
              )}

              {!cam.everSeen && (
                <div className="pt-3 border-t border-[#1F1F23] space-y-2">
                  <p className="text-[11px] font-medium text-[#F5F5F7]">Waiting for first connection</p>
                  <ol className="text-[10px] text-[#A1A1A8] space-y-1 list-decimal list-inside">
                    <li>Ensure your camera is connected to the same network as the Meridian edge device</li>
                    <li>Enable RTSP streaming in your camera's admin panel</li>
                    <li>The edge agent connects automatically and reports within 15 minutes</li>
                  </ol>
                </div>
              )}
            </div>
          ))}
        </div>
        )}
      </div>

      {/* Add Camera — the real setup wizard (registers via /api/vision/cameras) */}
      {showAddCamera && (
        <CameraSetupWizard
          orgId={orgId}
          onComplete={() => { setShowAddCamera(false); void loadReal() }}
          onClose={() => setShowAddCamera(false)}
        />
      )}
    </div>
  )
}
