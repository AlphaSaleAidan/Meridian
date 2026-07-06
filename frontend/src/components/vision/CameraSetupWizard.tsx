import { useRef, useState } from 'react'
import { Camera, CheckCircle, Wifi, Shield, X, ChevronRight, ChevronLeft, AlertTriangle } from 'lucide-react'
import { clsx } from 'clsx'
import { getAuthHeaders } from '@/lib/supabase'
import PhoneCameraCard from '@/components/vision/PhoneCameraCard'

type ComplianceMode = 'anonymous' | 'opt_in_identity' | 'disabled'

interface CameraConfig {
  name: string
  rtsp_url: string
  compliance_mode: ComplianceMode
  active_hours: { start: string; end: string }
  zone_config: Record<string, unknown>
}

interface CameraSetupWizardProps {
  orgId: string
  onComplete: (camera: CameraConfig) => void
  onClose: () => void
}

const STEPS = ['Camera', 'Zones', 'Privacy', 'Confirm'] as const
type Step = (typeof STEPS)[number]

// Cameras launch LIVE in anonymous mode. The biometric identity tier
// (opt_in_identity) stays disabled until the consent-signage flow ships — mirrors
// the backend CAMERA_IDENTITY_ENABLED gate (vision.py). Flip to '1' to allow it.
const CAMERA_IDENTITY_ENABLED = import.meta.env.VITE_CAMERA_IDENTITY === '1'

// Zones are stored NORMALIZED (0–1) relative to the camera frame; the edge
// agent scales them to native pixels at runtime. Keys are lowercase slugs —
// the same names later appear in vision_visits.zones_visited.
type ZoneRect = { x1: number; y1: number; x2: number; y2: number }
type ZoneRects = Record<string, ZoneRect>

const ZONE_PRESETS = ['Door', 'Entry', 'Bar', 'Register', 'Seating Area', 'Restroom', 'Patio', 'Kitchen']
const ZONE_COLORS = ['#17C5B0', '#1A8FD6', '#7C5CFF', '#F0B35B', '#E06B5E', '#5BC8A0', '#D46BB8', '#8FA6B8']

const zoneSlug = (label: string) => label.trim().toLowerCase().replace(/\s+/g, '_')

function ZoneEditor({ zones, onChange }: { zones: ZoneRects; onChange: (z: ZoneRects) => void }) {
  const boxRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<{ key: string; mode: 'move' | 'resize'; startX: number; startY: number; rect: ZoneRect } | null>(null)
  const [customName, setCustomName] = useState('')

  const names = Object.keys(zones)
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

  const addZone = (label: string) => {
    const key = zoneSlug(label)
    if (!key || zones[key]) return
    const n = names.length
    const x1 = clamp(0.08 + (n % 3) * 0.3, 0, 0.7)
    const y1 = clamp(0.1 + Math.floor(n / 3) * 0.28, 0, 0.7)
    onChange({ ...zones, [key]: { x1, y1, x2: clamp(x1 + 0.26, 0, 1), y2: clamp(y1 + 0.24, 0, 1) } })
  }

  const removeZone = (key: string) => {
    const next = { ...zones }
    delete next[key]
    onChange(next)
  }

  const onPointerDown = (e: React.PointerEvent, key: string, mode: 'move' | 'resize') => {
    e.preventDefault()
    e.stopPropagation()
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    dragRef.current = { key, mode, startX: e.clientX, startY: e.clientY, rect: { ...zones[key] } }
  }

  const onPointerMove = (e: React.PointerEvent) => {
    const d = dragRef.current
    const box = boxRef.current
    if (!d || !box) return
    const b = box.getBoundingClientRect()
    const dx = (e.clientX - d.startX) / b.width
    const dy = (e.clientY - d.startY) / b.height
    const r = d.rect
    let next: ZoneRect
    if (d.mode === 'move') {
      const w = r.x2 - r.x1, h = r.y2 - r.y1
      const x1 = clamp(r.x1 + dx, 0, 1 - w), y1 = clamp(r.y1 + dy, 0, 1 - h)
      next = { x1, y1, x2: x1 + w, y2: y1 + h }
    } else {
      next = { x1: r.x1, y1: r.y1, x2: clamp(r.x2 + dx, r.x1 + 0.06, 1), y2: clamp(r.y2 + dy, r.y1 + 0.06, 1) }
    }
    onChange({ ...zones, [d.key]: next })
  }

  const onPointerUp = () => { dragRef.current = null }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {ZONE_PRESETS.map(label => {
          const used = !!zones[zoneSlug(label)]
          return (
            <button key={label} onClick={() => addZone(label)} disabled={used}
              className={clsx('px-2.5 py-1 rounded-full text-[10px] font-medium border transition-colors',
                used ? 'border-[#1F1F23] text-[#A1A1A8]/30' : 'border-[#1A8FD6]/30 text-[#1A8FD6] hover:bg-[#1A8FD6]/10')}>
              + {label}
            </button>
          )
        })}
      </div>
      <div className="flex gap-2">
        <input value={customName} onChange={e => setCustomName(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && customName.trim()) { addZone(customName); setCustomName('') } }}
          placeholder="Custom zone name…"
          className="flex-1 px-3 py-1.5 text-[11px] bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40" />
        <button onClick={() => { if (customName.trim()) { addZone(customName); setCustomName('') } }}
          className="px-3 py-1.5 text-[10px] font-medium rounded-lg border border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors">
          Add
        </button>
      </div>
      <div ref={boxRef} onPointerMove={onPointerMove} onPointerUp={onPointerUp}
        className="relative aspect-video bg-[#0A0A0B] border border-[#1F1F23] rounded-lg overflow-hidden select-none touch-none">
        {names.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <p className="text-[11px] text-[#A1A1A8]/40">Camera view — add a zone above to place it here</p>
          </div>
        )}
        {names.map((key, i) => {
          const r = zones[key]
          const color = ZONE_COLORS[i % ZONE_COLORS.length]
          return (
            <div key={key}
              onPointerDown={e => onPointerDown(e, key, 'move')}
              className="absolute rounded-md cursor-move"
              style={{
                left: `${r.x1 * 100}%`, top: `${r.y1 * 100}%`,
                width: `${(r.x2 - r.x1) * 100}%`, height: `${(r.y2 - r.y1) * 100}%`,
                border: `2px dashed ${color}`, background: `${color}1a`,
              }}>
              <span className="absolute -top-2 left-1 px-1.5 rounded text-[9px] font-bold"
                style={{ background: color, color: '#04211c' }}>
                {key.replace(/_/g, ' ')}
              </span>
              <button onPointerDown={e => e.stopPropagation()} onClick={() => removeZone(key)}
                className="absolute -top-2 -right-2 w-4 h-4 rounded-full bg-[#111113] border border-[#1F1F23] text-[#A1A1A8] hover:text-red-400 text-[9px] leading-none">
                ×
              </button>
              <div onPointerDown={e => onPointerDown(e, key, 'resize')}
                className="absolute -bottom-1 -right-1 w-3 h-3 rounded-sm cursor-nwse-resize"
                style={{ background: color }} />
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function CameraSetupWizard({ orgId, onComplete, onClose }: CameraSetupWizardProps) {
  const [step, setStep] = useState(0)
  const [config, setConfig] = useState<CameraConfig>({
    name: '',
    rtsp_url: '',
    compliance_mode: 'anonymous',
    active_hours: { start: '07:00', end: '22:00' },
    zone_config: {},
  })
  const [connectionTested, setConnectionTested] = useState(false)
  const [error, setError] = useState('')
  const [consentConfirmed, setConsentConfirmed] = useState(false)

  const currentStep = STEPS[step]

  const canAdvance = (): boolean => {
    switch (currentStep) {
      case 'Camera': return config.name.length > 0 && config.rtsp_url.length > 0
      case 'Zones': return true
      case 'Privacy': return consentConfirmed || config.compliance_mode === 'disabled'
      case 'Confirm': return true
      default: return false
    }
  }

  const apiBase = (import.meta.env.VITE_API_URL || '') as string

  // NOTE: This only validates the RTSP URL *format*. A live reachability test
  // against the camera happens on the edge agent (it's the only thing on the
  // local network that can reach the RTSP stream) and is not yet wired here, so
  // we deliberately do NOT claim the camera is "connected" — see the
  // coming-soon note rendered next to the button.
  const testConnection = () => {
    setError('')
    const urlPattern = /^rtsp:\/\/.+/i
    if (!urlPattern.test(config.rtsp_url)) {
      setConnectionTested(false)
      setError('Enter a valid RTSP URL (e.g., rtsp://192.168.1.100:554/stream1)')
      return
    }
    setConnectionTested(true)
  }

  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (submitting) return  // double-click here created duplicate cameras
    setSubmitting(true)
    setError('')
    try {
      const res = await fetch(`${apiBase}/api/vision/cameras`, {
        method: 'POST',
        // getAuthHeaders() already includes Content-Type; spreading it attaches
        // the Supabase JWT that require_org_access (CA-1/CA-2) now demands.
        headers: { ...(await getAuthHeaders()) },
        body: JSON.stringify({
          org_id: orgId,
          name: config.name,
          rtsp_url: config.rtsp_url,
          compliance_mode: config.compliance_mode,
          active_hours: config.active_hours,
          zone_config: config.zone_config,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        // FastAPI validation errors put an array of objects in `detail`
        const detail = typeof data.detail === 'string'
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail.map((d: any) => d?.msg).filter(Boolean).join('; ')
            : ''
        setError(detail || 'Failed to register camera')
        return
      }
      onComplete(config)
    } catch {
      setError('Could not reach the server. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#111113] border border-[#1F1F23] rounded-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
          <div className="flex items-center gap-2">
            <Camera size={16} className="text-[#1A8FD6]" />
            <h2 className="text-sm font-semibold text-[#F5F5F7]">Connect Camera</h2>
          </div>
          <button aria-label="Close setup" onClick={onClose} className="text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Progress */}
        <div className="px-5 py-3 border-b border-[#1F1F23]">
          <div className="flex items-center gap-1">
            {STEPS.map((s, i) => (
              <div key={s} className="flex items-center gap-1 flex-1">
                <div className={clsx(
                  'w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold transition-colors',
                  i < step ? 'bg-[#17C5B0] text-white' :
                  i === step ? 'bg-[#1A8FD6] text-white' :
                  'bg-[#1F1F23] text-[#A1A1A8]/40'
                )}>
                  {i < step ? <CheckCircle size={12} /> : i + 1}
                </div>
                <span className={clsx(
                  'text-[9px] hidden sm:inline',
                  i === step ? 'text-[#F5F5F7] font-medium' : 'text-[#A1A1A8]/40'
                )}>{s}</span>
                {i < STEPS.length - 1 && (
                  <div className={clsx(
                    'flex-1 h-px mx-1',
                    i < step ? 'bg-[#17C5B0]/40' : 'bg-[#1F1F23]'
                  )} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="px-5 py-5 space-y-4">
          {/* Step 2: Camera */}
          {currentStep === 'Camera' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Camera Connection</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Enter the RTSP URL from your IP camera and give it a name.
                </p>
              </div>
              <div className="flex items-start gap-2 p-3 rounded-lg border border-[#17C5B0]/20 bg-[#17C5B0]/5">
                <Shield size={14} className="text-[#17C5B0] flex-shrink-0 mt-0.5" />
                <p className="text-[10px] text-[#A1A1A8]">
                  Your video never leaves your premises — Meridian processes it on-site and
                  reports back only the analytics (walk-ins, occupancy, conversion). If your
                  cameras are on the same wifi network, that's all you need.
                </p>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Camera Name</label>
                  <input
                    type="text"
                    value={config.name}
                    onChange={e => setConfig(c => ({ ...c, name: e.target.value }))}
                    placeholder="e.g., Front Door, Checkout Area"
                    className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">RTSP URL</label>
                  <input
                    type="text"
                    value={config.rtsp_url}
                    onChange={e => {
                      setConfig(c => ({ ...c, rtsp_url: e.target.value }))
                      setConnectionTested(false)
                    }}
                    placeholder="rtsp://192.168.1.100:554/stream1"
                    className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40 font-mono"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={testConnection}
                    disabled={!config.rtsp_url}
                    className={clsx(
                      'px-3 py-1.5 text-[11px] rounded-lg font-medium transition-colors',
                      connectionTested
                        ? 'bg-[#17C5B0]/10 text-[#17C5B0] border border-[#17C5B0]/20'
                        : 'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/20 hover:bg-[#1A8FD6]/20'
                    )}
                  >
                    {connectionTested ? (
                      <span className="flex items-center gap-1.5"><CheckCircle size={11} /> URL format valid</span>
                    ) : (
                      <span className="flex items-center gap-1.5"><Wifi size={11} /> Check URL format</span>
                    )}
                  </button>
                  {error && <span className="text-[10px] text-red-400">{error}</span>}
                </div>
                <p className="text-[9px] text-[#A1A1A8]/40">
                  Live stream reachability is verified by the on-prem edge agent after setup — coming soon.
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Active From</label>
                    <input
                      type="time"
                      value={config.active_hours.start}
                      onChange={e => setConfig(c => ({ ...c, active_hours: { ...c.active_hours, start: e.target.value } }))}
                      className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/40"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Active Until</label>
                    <input
                      type="time"
                      value={config.active_hours.end}
                      onChange={e => setConfig(c => ({ ...c, active_hours: { ...c.active_hours, end: e.target.value } }))}
                      className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/40"
                    />
                  </div>
                </div>
              </div>

              {/* Zero-hardware Path A: use a phone/tablet you already own as the camera.
                  Registers via /api/vision/camera/register-browser and hands off to /cam. */}
              <div className="pt-1">
                <p className="text-[10px] font-medium text-[#A1A1A8]/60 uppercase tracking-wide mb-2">
                  Or use a phone as a camera — no IP camera needed
                </p>
                <PhoneCameraCard orgId={orgId} />
              </div>
            </>
          )}

          {/* Step 3: Zones */}
          {currentStep === 'Zones' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Detection Zones</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Tap a preset to drop it on the view, then drag to position and resize.
                  Zones tell Meridian what each area is, so dwell and conversion are
                  measured per area. Optional — you can skip and add zones later.
                </p>
              </div>
              <ZoneEditor
                zones={config.zone_config as ZoneRects}
                onChange={zones => setConfig(c => ({ ...c, zone_config: zones }))}
              />
            </>
          )}

          {/* Step 4: Privacy */}
          {currentStep === 'Privacy' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Privacy & Compliance</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Choose how visitor data is processed. No images are ever stored or transmitted.
                </p>
              </div>
              <div className="space-y-2">
                {([
                  {
                    mode: 'anonymous' as ComplianceMode,
                    label: 'Anonymous (Recommended)',
                    desc: 'Aggregate counts only. No face data processed. Safest for compliance.',
                    badge: 'GDPR/CCPA Safe',
                    badgeColor: '#17C5B0',
                  },
                  {
                    mode: 'opt_in_identity' as ComplianceMode,
                    label: 'Opt-in Identity',
                    desc: 'Detect repeat visitors via face embeddings (stored on-prem only, 90-day auto-delete).',
                    badge: 'Requires Consent Signage',
                    badgeColor: '#FBBF24',
                  },
                  {
                    mode: 'disabled' as ComplianceMode,
                    label: 'Disabled',
                    desc: 'Camera connected but no vision processing. Useful for future activation.',
                    badge: '',
                    badgeColor: '',
                  },
                ]).map(opt => {
                  // Identity tier is gated until the consent flow ships — show it
                  // but make it unselectable ("Coming soon") so anonymous launches.
                  const locked = opt.mode === 'opt_in_identity' && !CAMERA_IDENTITY_ENABLED
                  const badge = locked ? 'Coming soon' : opt.badge
                  const badgeColor = locked ? '#A1A1A8' : opt.badgeColor
                  return (
                  <button
                    key={opt.mode}
                    disabled={locked}
                    onClick={() => { if (!locked) setConfig(c => ({ ...c, compliance_mode: opt.mode })) }}
                    className={clsx(
                      'w-full p-3 rounded-lg border text-left transition-all',
                      locked && 'opacity-50 cursor-not-allowed',
                      config.compliance_mode === opt.mode
                        ? 'border-[#1A8FD6] bg-[#1A8FD6]/5'
                        : 'border-[#1F1F23] hover:border-[#A1A1A8]/20 bg-[#0A0A0B]'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <div className={clsx(
                        'w-3 h-3 rounded-full border-2',
                        config.compliance_mode === opt.mode ? 'border-[#1A8FD6] bg-[#1A8FD6]' : 'border-[#A1A1A8]/20'
                      )} />
                      <span className="text-xs font-medium text-[#F5F5F7]">{opt.label}</span>
                      {badge && (
                        <span className="text-[8px] font-bold px-1.5 py-0.5 rounded" style={{
                          color: badgeColor,
                          backgroundColor: `${badgeColor}15`,
                        }}>{badge}</span>
                      )}
                    </div>
                    <p className="text-[10px] text-[#A1A1A8]/60 mt-1 ml-5">
                      {locked ? 'Repeat-visitor identity is releasing soon. Anonymous analytics is live now.' : opt.desc}
                    </p>
                  </button>
                )})}
              </div>

              {config.compliance_mode !== 'disabled' && (
                <label className="flex items-start gap-2 p-3 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] cursor-pointer">
                  <input
                    type="checkbox"
                    checked={consentConfirmed}
                    onChange={e => setConsentConfirmed(e.target.checked)}
                    className="mt-0.5 accent-[#1A8FD6]"
                  />
                  <div>
                    <span className="text-[11px] text-[#F5F5F7] font-medium">
                      I confirm consent signage is posted in the camera's field of view
                    </span>
                    <p className="text-[9px] text-[#A1A1A8]/40 mt-0.5">
                      Required for compliance. Signage must inform customers that video analytics are in use.
                    </p>
                  </div>
                </label>
              )}

              <div className="flex items-start gap-2 p-3 rounded-lg border border-[#1F1F23]/50 bg-[#17C5B0]/5">
                <Shield size={14} className="text-[#17C5B0] flex-shrink-0 mt-0.5" />
                <div className="text-[10px] text-[#A1A1A8] space-y-1">
                  <p>No raw images or video are ever stored or transmitted to the cloud.</p>
                  <p>Face embeddings (opt-in only) stay on your hardware and auto-delete after 90 days.</p>
                  <p>Customers can request immediate deletion (CCPA/GDPR right to erasure).</p>
                </div>
              </div>
            </>
          )}

          {/* Step 5: Confirm */}
          {currentStep === 'Confirm' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Review & Activate</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Confirm your camera configuration before activating.
                </p>
              </div>
              <div className="space-y-2">
                {[
                  { label: 'Camera Name', value: config.name },
                  { label: 'RTSP URL', value: config.rtsp_url },
                  { label: 'Active Hours', value: `${config.active_hours.start} - ${config.active_hours.end}` },
                  { label: 'Privacy Mode', value: config.compliance_mode.replace('_', ' ') },
                ].map(item => (
                  <div key={item.label} className="flex justify-between py-2 border-b border-[#1F1F23]/50">
                    <span className="text-[11px] text-[#A1A1A8]">{item.label}</span>
                    <span className="text-[11px] text-[#F5F5F7] font-medium font-mono">{item.value}</span>
                  </div>
                ))}
              </div>
              <div className="flex items-start gap-2 p-3 rounded-lg border border-amber-400/20 bg-amber-400/5">
                <AlertTriangle size={14} className="text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-[10px] text-[#A1A1A8]">
                  Once activated, Meridian's on-site processor picks this camera up
                  automatically and the first analytics arrive within about 15 minutes.
                </p>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-4 border-t border-[#1F1F23]">
          <button
            onClick={() => step > 0 ? setStep(s => s - 1) : onClose()}
            className="flex items-center gap-1 text-[11px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
          >
            <ChevronLeft size={12} />
            {step > 0 ? 'Back' : 'Cancel'}
          </button>
          {currentStep === 'Confirm' ? (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex items-center gap-1.5 px-4 py-2 text-[11px] font-semibold rounded-lg bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-colors"
            >
              <CheckCircle size={12} /> {submitting ? 'Activating…' : 'Activate Camera'}
            </button>
          ) : (
            <button
              onClick={() => setStep(s => s + 1)}
              disabled={!canAdvance()}
              className={clsx(
                'flex items-center gap-1 px-4 py-2 text-[11px] font-semibold rounded-lg transition-colors',
                canAdvance()
                  ? 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90'
                  : 'bg-[#1F1F23] text-[#A1A1A8]/40 cursor-not-allowed'
              )}
            >
              Next <ChevronRight size={12} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
