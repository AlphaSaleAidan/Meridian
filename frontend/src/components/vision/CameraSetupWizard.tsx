import { useEffect, useRef, useState } from 'react'
import { Camera, CheckCircle, Wifi, Shield, X, ChevronRight, ChevronLeft, AlertTriangle, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'

type ComplianceMode = 'anonymous' | 'opt_in_identity' | 'disabled'

interface ZoneDef {
  key: string
  label: string
  color: string
  enabled: boolean
}

interface CameraConfig {
  name: string
  rtsp_url: string
  compliance_mode: ComplianceMode
  active_hours: { start: string; end: string }
  zone_config: { zones: ZoneDef[] }
}

interface CameraSetupWizardProps {
  orgId: string
  onComplete: (camera: CameraConfig) => void
  onClose: () => void
}

const STEPS = ['Device', 'Camera', 'Zones', 'Privacy', 'Confirm'] as const
type Step = (typeof STEPS)[number]

const DEVICES = [
  { id: 'jetson-nano', name: 'Jetson Nano', cameras: '2-3', price: '$149', recommended: false },
  { id: 'jetson-orin-nano', name: 'Jetson Orin Nano', cameras: '4-6', price: '$249', recommended: true },
  { id: 'jetson-orin-nx', name: 'Jetson Orin NX', cameras: '8-12', price: '$499', recommended: false },
  { id: 'custom', name: 'Custom Linux + GPU', cameras: 'Varies', price: 'BYO', recommended: false },
] as const

const DEFAULT_ZONES: ZoneDef[] = [
  { key: 'entry', label: 'Entry', color: '#17C5B0', enabled: true },
  { key: 'browse', label: 'Browse', color: '#1A8FD6', enabled: true },
  { key: 'checkout', label: 'Checkout', color: '#7C5CFF', enabled: true },
]

// Per-brand RTSP main-stream path templates. The path is the part merchants
// almost never know, so picking a brand fills it in; it stays editable for
// odd firmware. "Other" defaults to a generic ONVIF-ish path.
const CAMERA_BRANDS = [
  { id: 'hikvision', label: 'Hikvision', path: '/Streaming/Channels/101' },
  { id: 'dahua', label: 'Dahua', path: '/cam/realmonitor?channel=1&subtype=0' },
  { id: 'amcrest', label: 'Amcrest', path: '/cam/realmonitor?channel=1&subtype=0' },
  { id: 'reolink', label: 'Reolink', path: '/h264Preview_01_main' },
  { id: 'axis', label: 'Axis', path: '/axis-media/media.amp' },
  { id: 'unifi', label: 'Ubiquiti UniFi', path: '/s0' },
  { id: 'generic', label: 'Other / ONVIF', path: '/stream1' },
] as const

type ConnMode = 'guided' | 'advanced'

interface RtspParts {
  brand: string
  ip: string
  port: string
  username: string
  password: string
  path: string
}

const DEFAULT_PARTS: RtspParts = {
  brand: 'hikvision',
  ip: '',
  port: '554',
  username: '',
  password: '',
  path: '/Streaming/Channels/101',
}

// Assemble an RTSP URL from guided fields. Credentials are percent-encoded so a
// password containing @ or : doesn't corrupt the host/port parsing.
function buildRtsp({ ip, port, username, password, path }: RtspParts): string {
  const host = ip.trim()
  if (!host) return ''
  const creds = username
    ? `${encodeURIComponent(username)}${password ? `:${encodeURIComponent(password)}` : ''}@`
    : ''
  const p = (port || '554').trim()
  const rawPath = path.trim()
  const finalPath = rawPath && !rawPath.startsWith('/') && !rawPath.startsWith('?') ? `/${rawPath}` : rawPath
  return `rtsp://${creds}${host}:${p}${finalPath}`
}

type UrlCheck = { ok: boolean; message: string; level: 'error' | 'warn' | 'ok' }

// The cloud API can't reach a camera on the merchant LAN, so this validates the
// URL shape and gives honest, specific feedback. The edge agent confirms the
// live feed after install (see the heartbeat poll on the Confirm step).
function checkRtspUrl(raw: string): UrlCheck {
  const url = raw.trim()
  if (!url) return { ok: false, message: 'Enter the RTSP URL from your camera.', level: 'error' }
  if (!/^rtsp:\/\//i.test(url)) {
    return { ok: false, message: 'URL must start with rtsp:// — e.g. rtsp://user:pass@192.168.1.100:554/stream1', level: 'error' }
  }
  const m = url.match(/^rtsp:\/\/(?:([^@/]+)@)?([^:/?#]+)(?::(\d+))?(\/[^?#]*)?/i)
  if (!m || !m[2]) {
    return { ok: false, message: "Couldn't find a host in that URL. Check the camera IP or hostname.", level: 'error' }
  }
  const [, creds, , port, path] = m
  if (port && !/^\d+$/.test(port)) {
    return { ok: false, message: 'Port must be numeric (RTSP is usually 554).', level: 'error' }
  }
  if (!creds) {
    return { ok: true, message: 'Valid format. Most IP cameras require credentials — rtsp://user:pass@host. The edge device confirms the live feed after install.', level: 'warn' }
  }
  if (!path || path === '/') {
    return { ok: true, message: 'Valid format, but no stream path (e.g. /stream1 or /h264). The edge device confirms the live feed after install.', level: 'warn' }
  }
  return { ok: true, message: 'Valid RTSP format. The edge device confirms the live feed once the agent is running.', level: 'ok' }
}

export default function CameraSetupWizard({ orgId, onComplete, onClose }: CameraSetupWizardProps) {
  const storageKey = `meridian-camera-wizard-${orgId || 'default'}`

  const [step, setStep] = useState(0)
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null)
  const [config, setConfig] = useState<CameraConfig>({
    name: '',
    rtsp_url: '',
    compliance_mode: 'anonymous',
    active_hours: { start: '07:00', end: '22:00' },
    zone_config: { zones: DEFAULT_ZONES },
  })
  const [connMode, setConnMode] = useState<ConnMode>('guided')
  const [parts, setParts] = useState<RtspParts>(DEFAULT_PARTS)
  const [urlCheck, setUrlCheck] = useState<UrlCheck | null>(null)
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState('')
  const [consentConfirmed, setConsentConfirmed] = useState(false)

  // Provisioning / heartbeat state (after Activate)
  const [registering, setRegistering] = useState(false)
  const [registeredCameraId, setRegisteredCameraId] = useState<string | null>(null)
  const [cameraStatus, setCameraStatus] = useState<'waiting' | 'online' | 'timeout' | null>(null)

  const mountedRef = useRef(true)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hydratedRef = useRef(false)

  const currentStep = STEPS[step]
  const provisioning = registeredCameraId !== null
  const zones = config.zone_config.zones
  const urlValidated = urlCheck?.ok === true

  // ─── Persist / restore in-progress wizard state ───────────────
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved) {
        const p = JSON.parse(saved)
        if (p.config) setConfig((c) => ({ ...c, ...p.config }))
        if (typeof p.step === 'number') setStep(Math.min(p.step, STEPS.length - 1))
        if (p.selectedDevice) setSelectedDevice(p.selectedDevice)
        if (p.connMode === 'guided' || p.connMode === 'advanced') setConnMode(p.connMode)
        if (p.parts) setParts((pt) => ({ ...pt, ...p.parts }))
      }
    } catch { /* ignore corrupt state */ }
    hydratedRef.current = true
    return () => {
      mountedRef.current = false
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!hydratedRef.current || provisioning) return
    try {
      localStorage.setItem(storageKey, JSON.stringify({ config, step, selectedDevice, connMode, parts }))
    } catch { /* quota — non-fatal */ }
  }, [config, step, selectedDevice, provisioning, storageKey])

  const clearProgress = () => {
    try { localStorage.removeItem(storageKey) } catch { /* ignore */ }
  }

  const canAdvance = (): boolean => {
    switch (currentStep) {
      case 'Device': return selectedDevice !== null
      case 'Camera': return config.name.trim().length > 0 && urlValidated
      case 'Zones': return zones.some((z) => z.enabled)
      case 'Privacy': return consentConfirmed || config.compliance_mode === 'disabled'
      case 'Confirm': return true
      default: return false
    }
  }

  const apiBase = (import.meta.env.VITE_API_URL || '') as string

  const validateUrl = () => {
    setValidating(true)
    setError('')
    const result = checkRtspUrl(config.rtsp_url)
    setUrlCheck(result)
    setValidating(false)
  }

  // Guided builder: merge a field change, rebuild the RTSP URL, and validate live
  // so the merchant never has to assemble or hand-check the URL themselves.
  const applyParts = (patch: Partial<RtspParts>) => {
    const next = { ...parts, ...patch }
    setParts(next)
    const url = buildRtsp(next)
    setConfig((c) => ({ ...c, rtsp_url: url }))
    setUrlCheck(url ? checkRtspUrl(url) : null)
  }

  const selectBrand = (id: string) => {
    const b = CAMERA_BRANDS.find((x) => x.id === id)
    applyParts({ brand: id, path: b ? b.path : parts.path })
  }

  const setZone = (key: string, patch: Partial<ZoneDef>) => {
    setConfig((c) => ({
      ...c,
      zone_config: { zones: c.zone_config.zones.map((z) => (z.key === key ? { ...z, ...patch } : z)) },
    }))
  }

  const pollHeartbeat = (camId: string) => {
    setCameraStatus('waiting')
    const deadline = Date.now() + 30_000
    const tick = async () => {
      try {
        const r = await fetch(`${apiBase}/api/vision/cameras/${encodeURIComponent(orgId)}`)
        if (r.ok) {
          const d = await r.json()
          const cam = (d.cameras || []).find((c: { id?: string }) => c.id === camId)
          if (cam && cam.status === 'online') {
            if (mountedRef.current) setCameraStatus('online')
            return
          }
        }
      } catch { /* keep polling */ }
      if (!mountedRef.current) return
      if (Date.now() < deadline) {
        pollTimerRef.current = setTimeout(tick, 3000)
      } else {
        setCameraStatus('timeout')
      }
    }
    tick()
  }

  const handleSubmit = async () => {
    setError('')
    if (!orgId) {
      // No org context (e.g. preview surfaces) — nothing to register against.
      clearProgress()
      onComplete(config)
      return
    }
    setRegistering(true)
    try {
      const res = await fetch(`${apiBase}/api/vision/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: orgId,
          name: config.name.trim(),
          rtsp_url: config.rtsp_url.trim(),
          compliance_mode: config.compliance_mode,
          active_hours: config.active_hours,
          zone_config: config.zone_config,
          edge_device_id: selectedDevice || undefined,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Failed to register camera')
        return
      }
      const created = await res.json().catch(() => null)
      const camId = created?.id ?? null
      clearProgress()
      if (camId) {
        setRegisteredCameraId(camId)
        pollHeartbeat(camId)
      } else {
        onComplete(config)
      }
    } catch {
      setError('Could not reach the server. Please try again.')
    } finally {
      if (mountedRef.current) setRegistering(false)
    }
  }

  const enabledZoneCount = zones.filter((z) => z.enabled).length

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
        {!provisioning && (
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
        )}

        {/* Step Content */}
        <div className="px-5 py-5 space-y-4">
          {/* Provisioning: waiting for the edge agent heartbeat */}
          {provisioning && (
            <div className="py-4 text-center space-y-4">
              {cameraStatus === 'online' ? (
                <>
                  <div className="w-12 h-12 rounded-full bg-[#17C5B0]/10 flex items-center justify-center mx-auto">
                    <CheckCircle size={24} className="text-[#17C5B0]" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-[#F5F5F7]">{config.name} is online</h3>
                    <p className="text-[11px] text-[#A1A1A8] mt-1">The edge agent connected to the camera and is reporting.</p>
                  </div>
                </>
              ) : cameraStatus === 'timeout' ? (
                <>
                  <div className="w-12 h-12 rounded-full bg-amber-400/10 flex items-center justify-center mx-auto">
                    <AlertTriangle size={24} className="text-amber-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-[#F5F5F7]">Camera registered — waiting on the edge device</h3>
                    <p className="text-[11px] text-[#A1A1A8] mt-1">
                      {config.name} is saved, but the edge agent hasn't reported in yet. Make sure the agent
                      is running on your device, then check its status anytime in Settings → Cameras.
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-full bg-[#1A8FD6]/10 flex items-center justify-center mx-auto">
                    <Loader2 size={24} className="text-[#1A8FD6] animate-spin" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-[#F5F5F7]">Waiting for the edge agent…</h3>
                    <p className="text-[11px] text-[#A1A1A8] mt-1">
                      {config.name} is registered. Start the edge agent on your device — it will connect to the
                      camera and report online here.
                    </p>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Step 1: Device */}
          {!provisioning && currentStep === 'Device' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Edge Device</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Meridian Vision runs on your hardware. No video leaves your premises.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-3">
                {DEVICES.map(device => (
                  <button
                    key={device.id}
                    onClick={() => setSelectedDevice(device.id)}
                    className={clsx(
                      'p-3 rounded-lg border text-left transition-all',
                      selectedDevice === device.id
                        ? 'border-[#1A8FD6] bg-[#1A8FD6]/5'
                        : 'border-[#1F1F23] hover:border-[#A1A1A8]/20 bg-[#0A0A0B]'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-xs font-medium text-[#F5F5F7]">{device.name}</span>
                        {device.recommended && (
                          <span className="ml-2 text-[8px] font-bold text-[#1A8FD6] bg-[#1A8FD6]/10 px-1.5 py-0.5 rounded">
                            RECOMMENDED
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-[#A1A1A8] font-mono">{device.price}</span>
                    </div>
                    <p className="text-[10px] text-[#A1A1A8]/60 mt-1">Supports {device.cameras} cameras</p>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Step 2: Camera */}
          {!provisioning && currentStep === 'Camera' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Camera Connection</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Enter the RTSP URL from your IP camera and give it a name.
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
                {/* Connection mode toggle */}
                <div className="flex items-center gap-1 p-0.5 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg w-fit">
                  {([
                    { id: 'guided' as ConnMode, label: 'Guided' },
                    { id: 'advanced' as ConnMode, label: 'Paste URL' },
                  ]).map(m => (
                    <button
                      key={m.id}
                      onClick={() => setConnMode(m.id)}
                      className={clsx(
                        'px-3 py-1 text-[10px] font-medium rounded-md transition-colors',
                        connMode === m.id ? 'bg-[#1A8FD6] text-white' : 'text-[#A1A1A8] hover:text-[#F5F5F7]'
                      )}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>

                {connMode === 'guided' ? (
                  <div className="space-y-3">
                    <div>
                      <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Camera Brand</label>
                      <div className="flex flex-wrap gap-1.5">
                        {CAMERA_BRANDS.map(b => (
                          <button
                            key={b.id}
                            onClick={() => selectBrand(b.id)}
                            className={clsx(
                              'px-2.5 py-1 text-[10px] rounded-md border transition-colors',
                              parts.brand === b.id
                                ? 'border-[#1A8FD6] bg-[#1A8FD6]/10 text-[#F5F5F7]'
                                : 'border-[#1F1F23] bg-[#0A0A0B] text-[#A1A1A8] hover:border-[#A1A1A8]/20'
                            )}
                          >
                            {b.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="col-span-2">
                        <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Camera IP</label>
                        <input
                          type="text"
                          inputMode="decimal"
                          value={parts.ip}
                          onChange={e => applyParts({ ip: e.target.value })}
                          placeholder="192.168.1.100"
                          className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40 font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Port</label>
                        <input
                          type="text"
                          inputMode="numeric"
                          value={parts.port}
                          onChange={e => applyParts({ port: e.target.value })}
                          placeholder="554"
                          className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40 font-mono"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Username</label>
                        <input
                          type="text"
                          autoComplete="off"
                          value={parts.username}
                          onChange={e => applyParts({ username: e.target.value })}
                          placeholder="admin"
                          className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40 font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Password</label>
                        <input
                          type="password"
                          autoComplete="off"
                          value={parts.password}
                          onChange={e => applyParts({ password: e.target.value })}
                          placeholder="••••••••"
                          className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40 font-mono"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Stream Path</label>
                      <input
                        type="text"
                        value={parts.path}
                        onChange={e => applyParts({ path: e.target.value })}
                        placeholder="/stream1"
                        className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40 font-mono"
                      />
                      <p className="text-[9px] text-[#A1A1A8]/40 mt-1">
                        Auto-filled from your camera brand. Most setups can leave this as-is.
                      </p>
                    </div>
                    {config.rtsp_url && (
                      <div className="px-3 py-2 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
                        <p className="text-[8px] uppercase tracking-wide text-[#A1A1A8]/40 mb-0.5">Connection URL</p>
                        <p className="text-[10px] text-[#A1A1A8] font-mono break-all">
                          rtsp://{parts.username ? `${parts.username}:••••@` : ''}{parts.ip || '…'}:{parts.port || '554'}{parts.path}
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">RTSP URL</label>
                    <input
                      type="text"
                      value={config.rtsp_url}
                      onChange={e => {
                        const v = e.target.value
                        setConfig(c => ({ ...c, rtsp_url: v }))
                        setUrlCheck(null)
                      }}
                      placeholder="rtsp://user:pass@192.168.1.100:554/stream1"
                      className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40 font-mono"
                    />
                    <p className="text-[9px] text-[#A1A1A8]/40 mt-1">
                      Find this in your camera's app under "RTSP" or "ONVIF". Most need a username and password.
                    </p>
                    <button
                      onClick={validateUrl}
                      disabled={validating || !config.rtsp_url}
                      className={clsx(
                        'mt-2 px-3 py-1.5 text-[11px] rounded-lg font-medium transition-colors disabled:opacity-40',
                        urlValidated
                          ? 'bg-[#17C5B0]/10 text-[#17C5B0] border border-[#17C5B0]/20'
                          : 'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/20 hover:bg-[#1A8FD6]/20'
                      )}
                    >
                      {validating ? (
                        <span className="flex items-center gap-1.5"><Wifi size={11} className="animate-pulse" /> Checking…</span>
                      ) : urlValidated ? (
                        <span className="flex items-center gap-1.5"><CheckCircle size={11} /> URL Validated</span>
                      ) : (
                        <span className="flex items-center gap-1.5"><Wifi size={11} /> Validate URL</span>
                      )}
                    </button>
                  </div>
                )}
                {urlCheck && (
                  <p className={clsx(
                    'text-[10px]',
                    urlCheck.level === 'error' ? 'text-red-400' :
                    urlCheck.level === 'warn' ? 'text-amber-400' :
                    'text-[#17C5B0]'
                  )}>
                    {urlCheck.message}
                  </p>
                )}
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
            </>
          )}

          {/* Step 3: Zones */}
          {!provisioning && currentStep === 'Zones' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Detection Zones</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Choose which areas to track. You'll draw the exact boundaries on the live image in the camera
                  management panel once the edge device is online.
                </p>
              </div>
              <div className="space-y-2">
                {zones.map(zone => (
                  <div
                    key={zone.key}
                    className={clsx(
                      'flex items-center gap-3 p-3 rounded-lg border transition-all',
                      zone.enabled ? 'border-[#1F1F23] bg-[#0A0A0B]' : 'border-[#1F1F23]/50 bg-[#0A0A0B]/50 opacity-60'
                    )}
                  >
                    <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: zone.color }} />
                    <input
                      type="text"
                      value={zone.label}
                      onChange={e => setZone(zone.key, { label: e.target.value })}
                      className="flex-1 px-2 py-1 text-[11px] bg-transparent border border-transparent rounded text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/40 focus:bg-[#111113]"
                    />
                    <button
                      onClick={() => setZone(zone.key, { enabled: !zone.enabled })}
                      aria-label={`${zone.enabled ? 'Disable' : 'Enable'} ${zone.label} zone`}
                      className={clsx(
                        'relative w-9 h-5 rounded-full transition-colors flex-shrink-0',
                        zone.enabled ? 'bg-[#1A8FD6]' : 'bg-[#1F1F23]'
                      )}
                    >
                      <span className={clsx(
                        'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all',
                        zone.enabled ? 'left-[18px]' : 'left-0.5'
                      )} />
                    </button>
                  </div>
                ))}
              </div>
              {enabledZoneCount === 0 && (
                <p className="text-[10px] text-amber-400">Enable at least one zone to continue.</p>
              )}
              <p className="text-[9px] text-[#A1A1A8]/40">
                Zones map raw foot traffic into entry, browse, and checkout funnels for conversion analytics.
              </p>
            </>
          )}

          {/* Step 4: Privacy */}
          {!provisioning && currentStep === 'Privacy' && (
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
                ]).map(opt => (
                  <button
                    key={opt.mode}
                    onClick={() => setConfig(c => ({ ...c, compliance_mode: opt.mode }))}
                    className={clsx(
                      'w-full p-3 rounded-lg border text-left transition-all',
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
                      {opt.badge && (
                        <span className="text-[8px] font-bold px-1.5 py-0.5 rounded" style={{
                          color: opt.badgeColor,
                          backgroundColor: `${opt.badgeColor}15`,
                        }}>{opt.badge}</span>
                      )}
                    </div>
                    <p className="text-[10px] text-[#A1A1A8]/60 mt-1 ml-5">{opt.desc}</p>
                  </button>
                ))}
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
          {!provisioning && currentStep === 'Confirm' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Review & Activate</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Confirm your camera configuration before activating.
                </p>
              </div>
              <div className="space-y-2">
                {[
                  { label: 'Edge Device', value: DEVICES.find(d => d.id === selectedDevice)?.name || '—' },
                  { label: 'Camera Name', value: config.name },
                  { label: 'RTSP URL', value: config.rtsp_url },
                  { label: 'Active Hours', value: `${config.active_hours.start} - ${config.active_hours.end}` },
                  { label: 'Zones', value: zones.filter(z => z.enabled).map(z => z.label).join(', ') || 'None' },
                  { label: 'Privacy Mode', value: config.compliance_mode.replace('_', ' ') },
                ].map(item => (
                  <div key={item.label} className="flex justify-between gap-3 py-2 border-b border-[#1F1F23]/50">
                    <span className="text-[11px] text-[#A1A1A8] flex-shrink-0">{item.label}</span>
                    <span className="text-[11px] text-[#F5F5F7] font-medium font-mono text-right break-all">{item.value}</span>
                  </div>
                ))}
              </div>
              {error && (
                <p className="text-[10px] text-red-400">{error}</p>
              )}
              <div className="flex items-start gap-2 p-3 rounded-lg border border-amber-400/20 bg-amber-400/5">
                <AlertTriangle size={14} className="text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-[10px] text-[#A1A1A8]">
                  The edge agent must be running on your device for the camera to start processing.
                  See the setup guide for Docker installation instructions.
                </p>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-4 border-t border-[#1F1F23]">
          {provisioning ? (
            <button
              onClick={() => onComplete(config)}
              className="w-full flex items-center justify-center gap-1.5 px-4 py-2 text-[11px] font-semibold rounded-lg bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 transition-colors"
            >
              {cameraStatus === 'online' ? (<><CheckCircle size={12} /> Done</>) : 'Finish — I\'ll check status later'}
            </button>
          ) : (
            <>
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
                  disabled={registering}
                  className="flex items-center gap-1.5 px-4 py-2 text-[11px] font-semibold rounded-lg bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 transition-colors disabled:opacity-50"
                >
                  {registering ? (<><Loader2 size={12} className="animate-spin" /> Activating…</>) : (<><CheckCircle size={12} /> Activate Camera</>)}
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
            </>
          )}
        </div>
      </div>
    </div>
  )
}
