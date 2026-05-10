import { useState } from 'react'
import { clsx } from 'clsx'
import { Wifi, ChevronRight, Check, Loader2, ShieldCheck } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'

const providers = [
  { id: 'square', label: 'Square', desc: 'POS, payments, inventory', color: '#006AFF' },
  { id: 'clover', label: 'Clover', desc: 'POS, orders, reporting', color: '#43B02A' },
  { id: 'toast', label: 'Toast', desc: 'Restaurant POS & management', color: '#FF6600' },
  { id: 'lightspeed', label: 'Lightspeed', desc: 'Retail & restaurant POS', color: '#E4002B' },
  { id: 'other', label: 'Other', desc: 'Custom API integration', color: '#7C5CFF' },
]

const providerFields: Record<string, { label: string; placeholder: string }[]> = {
  square: [{ label: 'Access Token', placeholder: 'EAAAl...' }],
  clover: [
    { label: 'API Key', placeholder: 'Your Clover API key' },
    { label: 'Merchant ID', placeholder: 'XXXXXXXXXX' },
  ],
  toast: [
    { label: 'API Key', placeholder: 'Your Toast API key' },
    { label: 'Restaurant GUID', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' },
  ],
  lightspeed: [{ label: 'API Key', placeholder: 'Your Lightspeed API key' }],
  other: [
    { label: 'Provider Name', placeholder: 'e.g. Revel, Shopify POS' },
    { label: 'API Key', placeholder: 'Your API key or access token' },
  ],
}

type Step = 'welcome' | 'provider' | 'credentials' | 'connecting' | 'done'

export default function OnboardingWizard() {
  const { org, connectPos } = useAuth()
  const [step, setStep] = useState<Step>('welcome')
  const [provider, setProvider] = useState<string | null>(null)
  const [fields, setFields] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  function selectProvider(id: string) {
    setProvider(id)
    setFields(providerFields[id].map(() => ''))
    setStep('credentials')
  }

  async function handleConnect() {
    if (!provider) return
    const apiKey = fields.join('::')
    if (fields.some(f => !f.trim())) {
      setError('All fields are required')
      return
    }
    setError(null)
    setStep('connecting')

    const err = await connectPos(provider, apiKey)
    if (err) {
      setError(err)
      setStep('credentials')
      return
    }

    await new Promise(r => setTimeout(r, 2000))
    setStep('done')
  }

  const stepIndex = { welcome: 0, provider: 1, credentials: 2, connecting: 3, done: 4 }
  const progress = ['Account Created', 'Select POS', 'Enter Credentials', 'Connecting', 'Live']

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-lg">
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <MeridianEmblem size={32} />
          <MeridianWordmark className="text-lg" />
        </div>

        {/* Progress bar */}
        <div className="flex items-center gap-1 mb-8 px-4">
          {progress.map((label, i) => (
            <div key={label} className="flex-1 flex flex-col items-center gap-1.5">
              <div className="w-full flex items-center">
                <div className={clsx(
                  'w-full h-1 rounded-full transition-colors duration-500',
                  i <= stepIndex[step] ? 'bg-[#1A8FD6]' : 'bg-[#1F1F23]'
                )} />
              </div>
              <span className={clsx(
                'text-[9px] font-medium transition-colors',
                i <= stepIndex[step] ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/30'
              )}>{label}</span>
            </div>
          ))}
        </div>

        <div className="card p-6 sm:p-8 border border-[#1F1F23]">

          {/* Welcome */}
          {step === 'welcome' && (
            <div className="text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-[#1A8FD6]/10 flex items-center justify-center mx-auto">
                <Wifi size={24} className="text-[#1A8FD6]" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-[#F5F5F7]">
                  Welcome{org?.owner_name ? `, ${org.owner_name.split(' ')[0]}` : ''}!
                </h2>
                <p className="text-sm text-[#A1A1A8] mt-1">
                  Let's connect <span className="text-[#F5F5F7] font-medium">{org?.business_name || 'your business'}</span> to start getting real-time insights.
                </p>
              </div>
              <div className="space-y-2 text-left pt-2">
                {[
                  'Connect your POS system securely',
                  'We import up to 18 months of transaction history',
                  '26 AI agents start analyzing your data immediately',
                ].map(t => (
                  <div key={t} className="flex items-start gap-2">
                    <Check size={14} className="text-[#17C5B0] flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-[#A1A1A8]">{t}</p>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setStep('provider')}
                className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 transition-all flex items-center justify-center gap-2"
              >
                Connect POS <ChevronRight size={16} />
              </button>
            </div>
          )}

          {/* Provider Selection */}
          {step === 'provider' && (
            <div className="space-y-4">
              <div className="text-center">
                <h2 className="text-lg font-bold text-[#F5F5F7]">Select Your POS System</h2>
                <p className="text-xs text-[#A1A1A8] mt-1">We'll walk you through connecting it securely</p>
              </div>
              <div className="space-y-2">
                {providers.map(p => (
                  <button
                    key={p.id}
                    onClick={() => selectProvider(p.id)}
                    className="w-full flex items-center gap-3 p-3 rounded-lg border border-[#1F1F23] hover:border-[#1A8FD6]/30 hover:bg-[#1A8FD6]/5 transition-all text-left group"
                  >
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: `${p.color}15` }}
                    >
                      <span className="text-sm font-bold" style={{ color: p.color }}>
                        {p.label[0]}
                      </span>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-[#F5F5F7]">{p.label}</p>
                      <p className="text-[10px] text-[#A1A1A8]/60">{p.desc}</p>
                    </div>
                    <ChevronRight size={14} className="text-[#A1A1A8]/30 group-hover:text-[#1A8FD6] transition-colors" />
                  </button>
                ))}
              </div>
              <button
                onClick={() => setStep('welcome')}
                className="w-full text-center text-[11px] text-[#A1A1A8] hover:text-[#1A8FD6] transition-colors pt-1"
              >
                Back
              </button>
            </div>
          )}

          {/* Credentials */}
          {step === 'credentials' && provider && (
            <div className="space-y-4">
              <div className="text-center">
                <h2 className="text-lg font-bold text-[#F5F5F7]">
                  Connect {providers.find(p => p.id === provider)?.label}
                </h2>
                <p className="text-xs text-[#A1A1A8] mt-1">
                  Enter your API credentials below. Find them in your {providers.find(p => p.id === provider)?.label} dashboard under Developer/API settings.
                </p>
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
              )}

              <div className="space-y-3">
                {providerFields[provider].map((field, i) => (
                  <div key={field.label}>
                    <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">{field.label}</label>
                    <input
                      type={field.label.toLowerCase().includes('key') || field.label.toLowerCase().includes('token') ? 'password' : 'text'}
                      value={fields[i]}
                      onChange={e => {
                        const next = [...fields]
                        next[i] = e.target.value
                        setFields(next)
                      }}
                      className="w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors font-mono"
                      placeholder={field.placeholder}
                    />
                  </div>
                ))}
              </div>

              <div className="flex items-start gap-2 p-3 rounded-lg bg-[#17C5B0]/5 border border-[#17C5B0]/10">
                <ShieldCheck size={14} className="text-[#17C5B0] flex-shrink-0 mt-0.5" />
                <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                  Your credentials are encrypted and stored securely. We use read-only access to import transaction data — we never modify your POS.
                </p>
              </div>

              <button
                onClick={handleConnect}
                className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 transition-all"
              >
                Connect & Import Data
              </button>
              <button
                onClick={() => { setStep('provider'); setError(null) }}
                className="w-full text-center text-[11px] text-[#A1A1A8] hover:text-[#1A8FD6] transition-colors"
              >
                Choose different provider
              </button>
            </div>
          )}

          {/* Connecting */}
          {step === 'connecting' && (
            <div className="text-center space-y-6 py-4">
              <Loader2 size={40} className="text-[#1A8FD6] animate-spin mx-auto" />
              <div>
                <h2 className="text-lg font-bold text-[#F5F5F7]">Connecting to {providers.find(p => p.id === provider)?.label}...</h2>
                <p className="text-xs text-[#A1A1A8] mt-2">Validating credentials and starting data import</p>
              </div>
              <div className="space-y-2 text-left max-w-xs mx-auto">
                {[
                  { label: 'Authenticating', done: true },
                  { label: 'Connecting to POS API', done: true },
                  { label: 'Starting transaction import', done: false },
                ].map(s => (
                  <div key={s.label} className="flex items-center gap-2">
                    {s.done ? (
                      <Check size={12} className="text-[#17C5B0]" />
                    ) : (
                      <Loader2 size={12} className="text-[#1A8FD6] animate-spin" />
                    )}
                    <span className={clsx('text-xs', s.done ? 'text-[#17C5B0]' : 'text-[#A1A1A8]')}>{s.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Done */}
          {step === 'done' && (
            <div className="text-center space-y-4 py-2">
              <div className="w-14 h-14 rounded-2xl bg-[#17C5B0]/10 flex items-center justify-center mx-auto">
                <Check size={28} className="text-[#17C5B0]" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-[#F5F5F7]">You're all set!</h2>
                <p className="text-sm text-[#A1A1A8] mt-1">
                  Your POS is connected. We're importing your transaction history now.
                </p>
              </div>
              <div className="p-3 rounded-lg bg-[#1A8FD6]/5 border border-[#1A8FD6]/10 text-xs text-[#A1A1A8] leading-relaxed">
                Historical data import usually takes 1-2 hours. Your AI agents will start generating insights as data flows in. We'll notify you when your first insights are ready.
              </div>
              <button
                onClick={() => window.location.reload()}
                className="w-full py-2.5 bg-[#17C5B0] text-white text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all"
              >
                Go to Dashboard
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
