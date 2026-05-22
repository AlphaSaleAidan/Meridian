import { useState } from 'react'
import { Video, Plus, Wifi, WifiOff, Activity, Users, Clock, TrendingUp, Eye, MapPin, ArrowUpRight, X, CheckCircle2, Copy, Check } from 'lucide-react'
import { useIsDemo } from '@/hooks/useOrg'
import { getActiveBusinessType, isCanadaPath } from '@/lib/demo-context'
import ScrollReveal from '@/components/ScrollReveal'

interface CameraDevice {
  id: string
  name: string
  location: string
  status: 'online' | 'offline' | 'setup'
  rtspUrl: string
  lastHeartbeat: string
  zones: string[]
  metrics: {
    entriesTotal: number
    exitsTotal: number
    avgOccupancy: number
    avgDwellSec: number
    peakHour: string
    conversionRate: number
  }
}

interface TrafficBucket {
  time: string
  entries: number
  exits: number
  occupancy: number
}

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
    status: i < 3 ? 'online' : 'setup',
    rtspUrl: `rtsp://192.168.1.${100 + i}:554/stream1`,
    lastHeartbeat: i < 3 ? `${Math.floor(Math.random() * 30) + 1}s ago` : 'Never',
    zones: i === 0 ? ['entry', 'exit'] : i === 1 ? ['browse', 'dwell'] : ['queue'],
    metrics: {
      entriesTotal: Math.floor(Math.random() * 800) + 200,
      exitsTotal: Math.floor(Math.random() * 750) + 180,
      avgOccupancy: Math.round((Math.random() * 15 + 3) * 10) / 10,
      avgDwellSec: Math.floor(Math.random() * 300) + 60,
      peakHour: `${Math.floor(Math.random() * 4) + 11}:00`,
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

export default function CameraIntelligencePage() {
  const isDemo = useIsDemo()
  const [cameras, setCameras] = useState<CameraDevice[]>(generateDemoCameras)
  const [traffic] = useState<TrafficBucket[]>(generateTrafficTimeline)
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null)

  // Add Camera wizard
  const [showAddCamera, setShowAddCamera] = useState(false)
  const [addStep, setAddStep] = useState(0)
  const [newCam, setNewCam] = useState({ name: '', location: '', rtspUrl: '' })
  const [copiedCamId, setCopiedCamId] = useState<string | null>(null)

  function handleAddCamera() {
    const cam: CameraDevice = {
      id: `cam-${Date.now()}`,
      name: newCam.name || `Camera ${cameras.length + 1}`,
      location: newCam.location,
      status: 'setup',
      rtspUrl: newCam.rtspUrl,
      lastHeartbeat: 'Never',
      zones: [],
      metrics: { entriesTotal: 0, exitsTotal: 0, avgOccupancy: 0, avgDwellSec: 0, peakHour: '--', conversionRate: 0 },
    }
    setCameras(prev => [...prev, cam])
    setShowAddCamera(false)
    setAddStep(0)
    setNewCam({ name: '', location: '', rtspUrl: '' })
  }

  function copyToClipboard(camId: string, text: string) {
    navigator.clipboard.writeText(text).then(() => { setCopiedCamId(camId); setTimeout(() => setCopiedCamId(null), 2000) })
  }

  const onlineCameras = cameras.filter(c => c.status === 'online')
  const totalEntries = onlineCameras.reduce((s, c) => s + c.metrics.entriesTotal, 0)
  const totalExits = onlineCameras.reduce((s, c) => s + c.metrics.exitsTotal, 0)
  const avgOccupancy = onlineCameras.length > 0
    ? Math.round(onlineCameras.reduce((s, c) => s + c.metrics.avgOccupancy, 0) / onlineCameras.length * 10) / 10
    : 0
  const avgConversion = onlineCameras.length > 0
    ? Math.round(onlineCameras.reduce((s, c) => s + c.metrics.conversionRate, 0) / onlineCameras.length * 100)
    : 0

  const maxTraffic = Math.max(...traffic.map(t => t.entries), 1)

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Camera Intelligence</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              {onlineCameras.length}/{cameras.length} cameras online • Real-time foot traffic & behavior analytics
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
            <button onClick={() => setShowAddCamera(true)} className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium rounded-lg bg-[#17C5B0] text-[#0A0A0B] hover:bg-[#14b3a0] transition-colors">
              <Plus size={13} /> Add Camera
            </button>
          </div>
        </div>
      </ScrollReveal>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Total Entries', value: totalEntries.toLocaleString(), icon: Users, color: '#17C5B0' },
          { label: 'Total Exits', value: totalExits.toLocaleString(), icon: TrendingUp, color: '#1A8FD6' },
          { label: 'Avg Occupancy', value: `${avgOccupancy}`, icon: MapPin, color: '#f59e0b' },
          { label: 'Conversion', value: `${avgConversion}%`, icon: Activity, color: '#7c3aed' },
        ].map(card => (
          <div key={card.label} className="bg-[#111113] rounded-xl p-4 border border-[#1F1F23]">
            <div className="flex items-center gap-2 mb-2">
              <card.icon size={14} style={{ color: card.color }} />
              <span className="text-[11px] text-[#A1A1A8]">{card.label}</span>
            </div>
            <p className="text-xl font-bold text-[#F5F5F7]">{card.value}</p>
          </div>
        ))}
      </div>

      {/* Traffic Timeline */}
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

      {/* Camera Grid */}
      <div>
        <h2 className="text-[14px] font-semibold text-[#F5F5F7] mb-3">Connected Cameras</h2>
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
                    cam.status === 'online' ? 'bg-[#17C5B0]/10' : 'bg-[#A1A1A8]/10'
                  }`}>
                    <Video size={14} className={cam.status === 'online' ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'} />
                  </div>
                  <div>
                    <p className="text-[13px] font-medium text-[#F5F5F7]">{cam.location}</p>
                    <p className="text-[10px] text-[#A1A1A8] font-mono">{cam.name} • {cam.rtspUrl}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {cam.status === 'online' ? (
                    <><Wifi size={12} className="text-[#17C5B0]" /><span className="text-[10px] text-[#17C5B0]">Live</span></>
                  ) : cam.status === 'setup' ? (
                    <><WifiOff size={12} className="text-[#A1A1A8]" /><span className="text-[10px] text-[#A1A1A8]">Setup</span></>
                  ) : (
                    <><WifiOff size={12} className="text-red-400" /><span className="text-[10px] text-red-400">Offline</span></>
                  )}
                </div>
              </div>

              {cam.status === 'online' && (
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#1F1F23]">
                  <div>
                    <p className="text-[10px] text-[#A1A1A8]">Entries</p>
                    <p className="text-[13px] font-semibold text-[#F5F5F7]">{cam.metrics.entriesTotal}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#A1A1A8]">Avg Dwell</p>
                    <p className="text-[13px] font-semibold text-[#F5F5F7]">{Math.round(cam.metrics.avgDwellSec / 60)}m</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#A1A1A8]">Peak</p>
                    <p className="text-[13px] font-semibold text-[#F5F5F7]">{cam.metrics.peakHour}</p>
                  </div>
                </div>
              )}

              {selectedCamera === cam.id && cam.status === 'online' && (
                <div className="mt-3 pt-3 border-t border-[#1F1F23] space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-[#0A0A0B] rounded-lg p-2.5">
                      <p className="text-[10px] text-[#A1A1A8]">Conversion Rate</p>
                      <p className="text-[15px] font-bold text-[#17C5B0]">{Math.round(cam.metrics.conversionRate * 100)}%</p>
                    </div>
                    <div className="bg-[#0A0A0B] rounded-lg p-2.5">
                      <p className="text-[10px] text-[#A1A1A8]">Avg Occupancy</p>
                      <p className="text-[15px] font-bold text-[#1A8FD6]">{cam.metrics.avgOccupancy}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {cam.zones.map(zone => (
                      <span key={zone} className="px-2 py-0.5 rounded text-[10px] font-medium bg-[#7c3aed]/10 text-[#7c3aed] border border-[#7c3aed]/20">
                        {zone}
                      </span>
                    ))}
                  </div>
                  <p className="text-[10px] text-[#A1A1A8]">
                    <Clock size={10} className="inline mr-1" />Last heartbeat: {cam.lastHeartbeat}
                  </p>
                </div>
              )}

              {cam.status === 'setup' && (
                <div className="pt-3 border-t border-[#1F1F23] space-y-2">
                  <p className="text-[11px] font-medium text-[#F5F5F7]">Setup Instructions</p>
                  <ol className="text-[10px] text-[#A1A1A8] space-y-1 list-decimal list-inside">
                    <li>Ensure your camera is connected to the same network</li>
                    <li>Open your camera's admin panel and enable RTSP streaming</li>
                    <li>Copy the RTSP URL (usually <span className="font-mono text-[#1A8FD6]">rtsp://IP:554/stream1</span>)</li>
                    <li>Meridian's edge agent will auto-detect and connect</li>
                  </ol>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[9px] font-mono text-[#A1A1A8]/60 truncate flex-1">{cam.rtspUrl}</span>
                    <button onClick={(e) => { e.stopPropagation(); copyToClipboard(cam.id, cam.rtspUrl) }}
                      className="text-[9px] text-[#1A8FD6] hover:text-[#17C5B0] transition-colors flex items-center gap-1">
                      {copiedCamId === cam.id ? <><Check size={9} /> Copied</> : <><Copy size={9} /> Copy URL</>}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Add Camera Wizard */}
      {showAddCamera && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" onClick={() => { setShowAddCamera(false); setAddStep(0); setNewCam({ name: '', location: '', rtspUrl: '' }) }}>
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div className="relative w-full max-w-md bg-[#111113] border border-[#1F1F23] rounded-xl shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
              <h3 className="text-sm font-bold text-[#F5F5F7]">Add Camera</h3>
              <button onClick={() => { setShowAddCamera(false); setAddStep(0) }} className="text-[#A1A1A8] hover:text-white transition-colors">
                <X size={16} />
              </button>
            </div>

            {/* Steps indicator */}
            <div className="flex items-center gap-1 px-5 pt-4">
              {['Location', 'Connection', 'Confirm'].map((label, i) => (
                <div key={label} className="flex-1 flex flex-col items-center gap-1">
                  <div className={`w-full h-1 rounded-full transition-colors ${i <= addStep ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]'}`} />
                  <span className={`text-[9px] font-medium ${i <= addStep ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/30'}`}>{label}</span>
                </div>
              ))}
            </div>

            <div className="px-5 py-4 space-y-4">
              {addStep === 0 && (
                <>
                  <div>
                    <label className="text-xs text-[#A1A1A8] block mb-1">Camera Name</label>
                    <input value={newCam.name} onChange={e => setNewCam(p => ({ ...p, name: e.target.value }))}
                      placeholder={`Camera ${cameras.length + 1}`}
                      className="w-full px-3 py-2.5 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50" />
                  </div>
                  <div>
                    <label className="text-xs text-[#A1A1A8] block mb-1">Location</label>
                    <input value={newCam.location} onChange={e => setNewCam(p => ({ ...p, location: e.target.value }))}
                      placeholder="e.g. Front Entrance, Kitchen, Parking Lot"
                      className="w-full px-3 py-2.5 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50" />
                  </div>
                </>
              )}

              {addStep === 1 && (
                <>
                  <div>
                    <label className="text-xs text-[#A1A1A8] block mb-1">RTSP Stream URL</label>
                    <input value={newCam.rtspUrl} onChange={e => setNewCam(p => ({ ...p, rtspUrl: e.target.value }))}
                      placeholder="rtsp://192.168.1.100:554/stream1"
                      className="w-full px-3 py-2.5 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 font-mono" />
                  </div>
                  <div className="bg-[#0A0A0B] rounded-lg p-3 space-y-2 border border-[#1F1F23]">
                    <p className="text-[11px] font-medium text-[#F5F5F7]">Where to find your RTSP URL</p>
                    <ol className="text-[10px] text-[#A1A1A8] space-y-1 list-decimal list-inside">
                      <li>Open your camera's web admin panel (usually at its IP address)</li>
                      <li>Go to <span className="text-[#F5F5F7]">Network</span> → <span className="text-[#F5F5F7]">RTSP Settings</span></li>
                      <li>Enable RTSP and copy the stream URL</li>
                      <li>Common format: <span className="font-mono text-[#1A8FD6]">rtsp://IP:554/stream1</span></li>
                    </ol>
                    <p className="text-[9px] text-[#A1A1A8]/50">Works with Hikvision, Dahua, Reolink, Amcrest, Axis, and most IP cameras.</p>
                  </div>
                </>
              )}

              {addStep === 2 && (
                <>
                  <div className="text-center py-2">
                    <div className="w-12 h-12 rounded-full bg-[#17C5B0]/10 border border-[#17C5B0]/30 flex items-center justify-center mx-auto mb-3">
                      <Video size={20} className="text-[#17C5B0]" />
                    </div>
                    <p className="text-sm font-medium text-[#F5F5F7]">Ready to Connect</p>
                  </div>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                      <span className="text-[#A1A1A8]">Name</span>
                      <span className="text-[#F5F5F7] font-medium">{newCam.name || `Camera ${cameras.length + 1}`}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                      <span className="text-[#A1A1A8]">Location</span>
                      <span className="text-[#F5F5F7]">{newCam.location || '—'}</span>
                    </div>
                    <div className="flex justify-between py-2">
                      <span className="text-[#A1A1A8]">Stream</span>
                      <span className="text-[#F5F5F7] font-mono text-[11px]">{newCam.rtspUrl || '—'}</span>
                    </div>
                  </div>
                  <p className="text-[10px] text-[#A1A1A8] text-center">
                    Meridian's edge agent will begin monitoring automatically once the camera is reachable.
                  </p>
                </>
              )}
            </div>

            <div className="flex justify-between px-5 py-4 border-t border-[#1F1F23]">
              <button onClick={() => addStep > 0 ? setAddStep(addStep - 1) : setShowAddCamera(false)}
                className="px-4 py-2 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
                {addStep === 0 ? 'Cancel' : 'Back'}
              </button>
              {addStep < 2 ? (
                <button onClick={() => setAddStep(addStep + 1)}
                  disabled={(addStep === 0 && !newCam.location.trim()) || (addStep === 1 && !newCam.rtspUrl.trim())}
                  className="px-4 py-2 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-40 transition-colors">
                  Next
                </button>
              ) : (
                <button onClick={handleAddCamera}
                  className="px-4 py-2 bg-[#17C5B0] text-white text-sm font-medium rounded-lg hover:bg-[#17C5B0]/90 transition-colors flex items-center gap-1.5">
                  <CheckCircle2 size={14} /> Add Camera
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
