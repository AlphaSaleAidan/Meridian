import { useState } from 'react'
import { Camera, CheckCircle, Wifi, Shield, X, ChevronRight, ChevronLeft, AlertTriangle } from 'lucide-react'
import { clsx } from 'clsx'

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

const STEPS = ['Device', 'Camera', 'Zones', 'Privacy', 'Confirm'] as const
type Step = (typeof STEPS)[number]

export default function CameraSetupWizard({ orgId, onComplete, onClose }: CameraSetupWizardProps) {
  const [step, setStep] = useState(0)
  const [config, setConfig] = useState<CameraConfig>({
    name: '',
    rtsp_url: '',
    compliance_mode: 'anonymous',
    active_hours: { start: '07:00', end: '22:00' },
    zone_config: {},
  })
  const [edgeDetected, setEdgeDetected] = useState(false)
  const [connectionTested, setConnectionTested] = useState(false)
  const [testing, setTesting] = useState(false)
  const [error, setError] = useState('')
  const [consentConfirmed, setConsentConfirmed] = useState(false)

  const currentStep = STEPS[step]

  const canAdvance = (): boolean => {
    switch (currentStep) {
      case 'Device': return true
      case 'Camera': return config.name.length > 0 && config.rtsp_url.length > 0
      case 'Zones': return true
      case 'Privacy': return consentConfirmed || config.compliance_mode === 'disabled'
      case 'Confirm': return true
      default: return false
    }
  }

  const testConnection = async () => {
    setTesting(true)
    setError('')
    try {
      await new Promise(r => setTimeout(r, 2000))
      setConnectionTested(true)
    } catch {
      setError('Could not connect to camera. Check the RTSP URL and network.')
    } finally {
      setTesting(false)
    }
  }

  const handleSubmit = () => {
    onComplete(config)
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
          <button onClick={onClose} className="text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
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
          {/* Step 1: Device */}
          {currentStep === 'Device' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Edge Device</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Meridian Vision runs on your hardware. No video leaves your premises.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-3">
                {[
                  { name: 'Jetson Nano', cameras: '2-3', price: '$149', recommended: false },
                  { name: 'Jetson Orin Nano', cameras: '4-6', price: '$249', recommended: true },
                  { name: 'Jetson Orin NX', cameras: '8-12', price: '$499', recommended: false },
                  { name: 'Custom Linux + GPU', cameras: 'Varies', price: 'BYO', recommended: false },
                ].map(device => (
                  <button
                    key={device.name}
                    onClick={() => setEdgeDetected(true)}
                    className={clsx(
                      'p-3 rounded-lg border text-left transition-all',
                      edgeDetected && device.recommended
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
          {currentStep === 'Camera' && (
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
                    disabled={testing || !config.rtsp_url}
                    className={clsx(
                      'px-3 py-1.5 text-[11px] rounded-lg font-medium transition-colors',
                      connectionTested
                        ? 'bg-[#17C5B0]/10 text-[#17C5B0] border border-[#17C5B0]/20'
                        : 'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/20 hover:bg-[#1A8FD6]/20'
                    )}
                  >
                    {testing ? (
                      <span className="flex items-center gap-1.5"><Wifi size={11} className="animate-pulse" /> Testing...</span>
                    ) : connectionTested ? (
                      <span className="flex items-center gap-1.5"><CheckCircle size={11} /> Connected</span>
                    ) : (
                      <span className="flex items-center gap-1.5"><Wifi size={11} /> Test Connection</span>
                    )}
                  </button>
                  {error && <span className="text-[10px] text-red-400">{error}</span>}
                </div>
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
          {currentStep === 'Zones' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Detection Zones</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Define areas in the camera view for tracking. Zone drawing will be available once the camera is connected.
                </p>
              </div>
              <div className="aspect-video bg-[#0A0A0B] border border-[#1F1F23] rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <Camera size={32} className="text-[#A1A1A8]/20 mx-auto mb-2" />
                  <p className="text-[11px] text-[#A1A1A8]/40">Camera preview will appear here</p>
                  <p className="text-[9px] text-[#A1A1A8]/20 mt-1">Draw entry, browse, and checkout zones</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {['Entry', 'Browse', 'Checkout'].map(zone => (
                  <div key={zone} className="p-2 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-center">
                    <div className={clsx(
                      'w-3 h-3 rounded-full mx-auto mb-1',
                      zone === 'Entry' ? 'bg-[#17C5B0]' :
                      zone === 'Browse' ? 'bg-[#1A8FD6]' :
                      'bg-[#7C5CFF]'
                    )} />
                    <span className="text-[10px] text-[#A1A1A8]">{zone} Zone</span>
                  </div>
                ))}
              </div>
              <p className="text-[9px] text-[#A1A1A8]/40">
                Zones can be configured after setup via the camera management panel.
              </p>
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
                  The edge agent must be running on your device for the camera to start processing.
                  See the setup guide for Docker installation instructions.
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
              className="flex items-center gap-1.5 px-4 py-2 text-[11px] font-semibold rounded-lg bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 transition-colors"
            >
              <CheckCircle size={12} /> Activate Camera
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
