import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2, Wifi, Camera, Box, Smartphone, ArrowRight,
  Loader2, X, Clock, WifiOff,
} from 'lucide-react'
import POSSystemPicker from './POSSystemPicker'
import CameraSetupWizard from './vision/CameraSetupWizard'
import { useAuth } from '@/lib/auth'
import { useOrgId } from '@/hooks/useOrg'

interface WalkthroughStep {
  key: string
  label: string
  icon: typeof Wifi
  description: string
}

const WALKTHROUGH_STEPS: WalkthroughStep[] = [
  { key: 'pos', label: 'POS Connection', icon: Wifi, description: 'Verify your POS system is connected and data is flowing.' },
  { key: 'insights', label: 'Data Insights', icon: Clock, description: 'We\'re processing your data to generate insights.' },
  { key: 'cameras', label: 'Camera Setup', icon: Camera, description: 'Connect your cameras for real-time intelligence.' },
  { key: '3dspace', label: '3D Space', icon: Box, description: 'Set up your 3D digital space.' },
  { key: 'phone', label: 'Phone Orders', icon: Smartphone, description: 'AI-powered phone ordering for your business.' },
]

const INSIGHT_MESSAGES = [
  "We're connecting to your POS and pulling transaction data...",
  "Crunching the numbers — analyzing your sales patterns...",
  "Building your revenue insights from the last 30 days...",
  "Almost there — generating your product performance matrix...",
  "Analyzing peak hours and customer flow patterns...",
  "Calculating margin breakdowns across your menu...",
  "Identifying your top performers and hidden opportunities...",
  "Running anomaly detection on recent transactions...",
  "Your personalized insights are being crafted right now...",
  "Just a few more minutes — we want to make sure everything is accurate...",
]

function getStorageKey(userId: string) {
  return `meridian_walkthrough_${userId}`
}

interface CustomerWalkthroughProps {
  userId: string
  posConnected?: boolean
  onDismiss: () => void
}

export default function CustomerWalkthrough({ userId, posConnected = false, onDismiss }: CustomerWalkthroughProps) {
  const navigate = useNavigate()
  const { connectPos } = useAuth()
  const orgId = useOrgId()
  const [showCameraWizard, setShowCameraWizard] = useState(false)
  const [cameraConnected, setCameraConnected] = useState(false)
  const storageKey = getStorageKey(userId)
  const [currentStep, setCurrentStep] = useState(0)
  const [posVerified, setPosVerified] = useState(posConnected)
  const [insightTimer, setInsightTimer] = useState(0)
  const [insightMessageIdx, setInsightMessageIdx] = useState(0)
  const [dismissed, setDismissed] = useState(false)

  const [posProvider, setPosProvider] = useState<string | null>(null)
  const [posApiKey, setPosApiKey] = useState('')
  const [connectingPos, setConnectingPos] = useState(false)
  const [posError, setPosError] = useState<string | null>(null)

  useEffect(() => {
    const saved = localStorage.getItem(storageKey)
    if (saved === 'completed') {
      setDismissed(true)
    }
  }, [storageKey])

  useEffect(() => {
    if (posConnected) setPosVerified(true)
  }, [posConnected])

  const insightTimerMax = 30 * 60
  useEffect(() => {
    if (currentStep !== 1 || !posVerified) return
    const interval = setInterval(() => {
      setInsightTimer(prev => {
        if (prev >= insightTimerMax) {
          clearInterval(interval)
          return insightTimerMax
        }
        return prev + 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [currentStep, posVerified])

  useEffect(() => {
    if (currentStep !== 1 || !posVerified) return
    const msgInterval = setInterval(() => {
      setInsightMessageIdx(prev => (prev + 1) % INSIGHT_MESSAGES.length)
    }, 12000)
    return () => clearInterval(msgInterval)
  }, [currentStep, posVerified])

  async function handleConnectPos() {
    if (!posProvider) { setPosError('Select a POS system first'); return }
    if (!posApiKey.trim()) { setPosError('Enter your API access token'); return }
    setConnectingPos(true)
    setPosError(null)
    // P1: connectPos now takes a credentials object; single-field
    // walkthrough → access_token (works for Square + most generic-REST).
    const err = await connectPos(posProvider, { access_token: posApiKey.trim() })
    setConnectingPos(false)
    if (err) { setPosError(err); return }
    setPosVerified(true)
  }

  const handleComplete = useCallback(() => {
    localStorage.setItem(storageKey, 'completed')
    setDismissed(true)
    onDismiss()
  }, [storageKey, onDismiss])

  if (dismissed) return null

  const step = WALKTHROUGH_STEPS[currentStep]
  const insightProgress = Math.min((insightTimer / insightTimerMax) * 100, 100)
  const insightsDone = insightTimer >= insightTimerMax
  const formatTime = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl bg-[#0f1512] border border-[#1a2420] rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-[#1a2420] flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Welcome to Meridian</h2>
              <p className="text-xs text-[#6b7a74] mt-0.5">Let's get everything set up for your business.</p>
            </div>
            <button aria-label="Close walkthrough" onClick={handleComplete} className="p-1.5 rounded-lg hover:bg-[#1a2420] transition-colors">
              <X size={18} className="text-[#6b7a74]" />
            </button>
          </div>

          <div className="flex gap-1.5 mt-4">
            {WALKTHROUGH_STEPS.map((s, i) => (
              <div key={s.key} className="flex-1 flex flex-col items-center gap-1">
                <div className={`w-full h-1 rounded-full ${
                  i < currentStep ? 'bg-[#00d4aa]' :
                  i === currentStep ? 'bg-[#00d4aa] animate-pulse' :
                  'bg-[#1a2420]'
                }`} />
                <span className={`text-[9px] font-medium ${
                  i <= currentStep ? 'text-[#00d4aa]' : 'text-[#4a5550]'
                }`}>{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6 min-h-[280px] overflow-y-auto">
          {step.key === 'pos' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl border flex items-center justify-center ${
                  posVerified ? 'bg-[#00d4aa]/10 border-[#00d4aa]/20' : 'bg-amber-500/10 border-amber-500/20'
                }`}>
                  {posVerified ? <Wifi size={24} className="text-[#00d4aa]" /> : <WifiOff size={24} className="text-amber-400" />}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">POS Connection</h3>
                  <p className="text-xs text-[#6b7a74]">{posVerified ? 'Your POS is connected and data is flowing.' : 'Connect your POS to start receiving insights.'}</p>
                </div>
              </div>

              {posVerified ? (
                <div className="flex items-center gap-2 p-4 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
                  <CheckCircle2 size={18} className="text-[#00d4aa]" />
                  <span className="text-sm text-[#00d4aa] font-medium">POS connected — data is flowing into your dashboard.</span>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <WifiOff size={16} className="text-amber-400" />
                    <span className="text-xs text-amber-400 font-medium">POS not connected yet — connect now to unlock your insights.</span>
                  </div>

                  <POSSystemPicker
                    value={posProvider}
                    onChange={setPosProvider}
                    mode="new-customer"
                    portalContext="canada"
                  />

                  {posProvider && (
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-medium text-[#6b7a74]">API Access Token</label>
                      <input
                        type="password"
                        value={posApiKey}
                        onChange={e => { setPosApiKey(e.target.value); setPosError(null) }}
                        placeholder="Paste your access token from the POS developer portal..."
                        className="w-full px-3 py-2.5 text-xs font-mono bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-white placeholder-[#4a5550] focus:outline-none focus:border-[#00d4aa]/40"
                      />
                      <p className="text-[9px] text-[#4a5550]">
                        Your token is encrypted with AES-256-GCM before storage. We never store plaintext keys.
                      </p>
                    </div>
                  )}

                  {posError && (
                    <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{posError}</div>
                  )}

                  <button
                    onClick={handleConnectPos}
                    disabled={connectingPos || !posProvider || !posApiKey.trim()}
                    className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
                  >
                    {connectingPos ? <Loader2 size={16} className="animate-spin" /> : <><Wifi size={16} /> Test &amp; Connect POS</>}
                  </button>

                  <p className="text-[10px] text-[#4a5550] text-center">
                    You can also connect later from Settings — but the 30-minute insight timer won't start until your POS is linked.
                  </p>
                </div>
              )}
            </div>
          )}

          {step.key === 'insights' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-[#7C5CFF]/10 border border-[#7C5CFF]/20 flex items-center justify-center">
                  <Clock size={24} className="text-[#7C5CFF]" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Generating Your Insights</h3>
                  <p className="text-xs text-[#6b7a74]">
                    {posVerified
                      ? "We're eating through all the data — your insights will be ready shortly!"
                      : 'Connect your POS first to start the insight engine.'}
                  </p>
                </div>
              </div>

              {!posVerified ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <WifiOff size={16} className="text-amber-400" />
                    <span className="text-sm text-amber-400 font-medium">Waiting for POS connection...</span>
                  </div>
                  <p className="text-xs text-[#6b7a74]">
                    Go back to <button onClick={() => setCurrentStep(0)} className="text-[#00d4aa] underline">Step 1</button> to connect your POS, or connect later from Settings. The 30-minute timer starts once your POS is linked.
                  </p>
                </div>
              ) : (
                <>
                  <div className="p-4 rounded-lg bg-[#0a0f0d] border border-[#1a2420] space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[#6b7a74]">Processing data...</span>
                      <span className="text-[#7C5CFF] font-mono">{formatTime(insightTimer)} / 30:00</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[#1a2420] overflow-hidden">
                      <div className="h-full bg-[#7C5CFF] rounded-full transition-all duration-1000" style={{ width: `${insightProgress}%` }} />
                    </div>
                    <p className="text-xs text-[#6b7a74] italic animate-pulse">{INSIGHT_MESSAGES[insightMessageIdx]}</p>
                  </div>

                  {insightsDone ? (
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
                      <CheckCircle2 size={16} className="text-[#00d4aa]" />
                      <span className="text-xs text-[#00d4aa] font-medium">Insights ready! Check your Revenue, Products, and Insights tabs.</span>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-xs text-[#6b7a74]">
                        <strong className="text-white">Revenue &amp; sales numbers</strong> will appear in your dashboard as they come in — no need to wait.
                      </p>
                      <p className="text-xs text-[#6b7a74]">
                        <strong className="text-white">Deep insights</strong> like product analysis, anomaly detection, and forecasts take about 30 minutes to generate from your full dataset.
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {step.key === 'cameras' && (
            <div className="space-y-4">
              {showCameraWizard && (
                <CameraSetupWizard
                  orgId={orgId}
                  onComplete={() => { setShowCameraWizard(false); setCameraConnected(true) }}
                  onClose={() => setShowCameraWizard(false)}
                />
              )}

              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl border flex items-center justify-center ${
                  cameraConnected ? 'bg-[#00d4aa]/10 border-[#00d4aa]/20' : 'bg-[#F59E0B]/10 border-[#F59E0B]/20'
                }`}>
                  <Camera size={24} className={cameraConnected ? 'text-[#00d4aa]' : 'text-[#F59E0B]'} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Camera Setup</h3>
                  <p className="text-xs text-[#6b7a74]">
                    {cameraConnected ? 'Camera registered! The edge agent will start processing once it connects.' : 'Connect your cameras for real-time customer intelligence.'}
                  </p>
                </div>
              </div>

              {cameraConnected ? (
                <div className="flex items-center gap-2 p-4 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
                  <CheckCircle2 size={18} className="text-[#00d4aa]" />
                  <span className="text-sm text-[#00d4aa] font-medium">Camera registered. You can add more cameras later in Settings.</span>
                </div>
              ) : (
                <>
                  <div className="p-4 rounded-lg bg-[#0a0f0d] border border-[#1a2420] space-y-3">
                    <p className="text-sm text-white font-medium">How to connect your cameras:</p>
                    <ol className="text-xs text-[#6b7a74] space-y-2 list-decimal list-inside">
                      <li>Ensure your camera system is on the same network</li>
                      <li>Click <strong className="text-white">"Set Up Camera"</strong> below to open the wizard</li>
                      <li>Enter your camera's name and RTSP stream URL</li>
                      <li>Choose your privacy settings and activate</li>
                    </ol>
                  </div>

                  <button
                    onClick={() => setShowCameraWizard(true)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#F59E0B] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#F59E0B]/90 transition-all"
                  >
                    <Camera size={16} /> Set Up Camera
                  </button>

                  <p className="text-[10px] text-[#4a5550] text-center">
                    You can skip this step and add cameras later from Settings.
                  </p>
                </>
              )}
            </div>
          )}

          {step.key === '3dspace' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center">
                  <Box size={24} className="text-[#1A8FD6]" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">3D Digital Space</h3>
                  <p className="text-xs text-[#6b7a74]">Create a digital twin of your business.</p>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-[#0a0f0d] border border-[#1a2420] space-y-3">
                <p className="text-sm text-white font-medium">Setting up your 3D space:</p>
                <ol className="text-xs text-[#6b7a74] space-y-2 list-decimal list-inside">
                  <li>Navigate to the <strong className="text-white">Space</strong> tab in your dashboard</li>
                  <li>Upload a floor plan or start from a template that matches your layout</li>
                  <li>Place cameras, POS terminals, and key zones on the map</li>
                  <li>Meridian will overlay real-time data on your digital space</li>
                </ol>
              </div>

              <button
                onClick={() => { handleComplete(); navigate('/canada/dashboard/space') }}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-all"
              >
                <Box size={16} /> Go to 3D Space Setup
              </button>
            </div>
          )}

          {step.key === 'phone' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-[#6b7a74]/10 border border-[#6b7a74]/20 flex items-center justify-center">
                  <Smartphone size={24} className="text-[#6b7a74]" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">AI Phone Orders</h3>
                  <p className="text-xs text-[#6b7a74]">Automated phone ordering powered by AI.</p>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-[#0a0f0d] border border-[#2a3430] space-y-3">
                <div className="flex items-center gap-2 mb-1">
                  <div className="px-2 py-0.5 rounded bg-[#f0b429]/15 text-[#f0b429] text-[10px] font-semibold uppercase tracking-wider">Coming Soon</div>
                </div>
                <p className="text-sm text-white font-medium">AI-powered phone ordering is in development.</p>
                <p className="text-xs text-[#6b7a74]">
                  Soon, Meridian will answer your phone, take orders using natural conversation, and send them straight to your POS. We'll notify you as soon as it's ready.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#1a2420] flex items-center justify-between flex-shrink-0">
          <button
            onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
            disabled={currentStep === 0}
            className="px-4 py-2 text-sm text-[#6b7a74] hover:text-white disabled:opacity-30 transition-colors"
          >
            Back
          </button>

          <span className="text-xs text-[#4a5550]">{currentStep + 1} of {WALKTHROUGH_STEPS.length}</span>

          {currentStep < WALKTHROUGH_STEPS.length - 1 ? (
            <button
              onClick={() => setCurrentStep(prev => prev + 1)}
              className="flex items-center gap-2 px-4 py-2 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
            >
              Next <ArrowRight size={14} />
            </button>
          ) : (
            <button
              onClick={handleComplete}
              className="flex items-center gap-2 px-4 py-2 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
            >
              <CheckCircle2 size={14} /> Complete Setup
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
