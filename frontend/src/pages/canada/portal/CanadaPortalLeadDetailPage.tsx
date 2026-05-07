import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Check, Sparkles, Wifi, X, Upload, Trash2,
  FileText, Eye, Mail,
} from 'lucide-react'
import { canadaSalesDemoData, type Deal, type DealStage } from '@/lib/canada-sales-demo-data'

const STAGE_TO_STEP: Record<DealStage, number> = {
  prospecting: 1,
  contacted: 2,
  demo_scheduled: 3,
  proposal_sent: 4,
  negotiation: 5,
  closed_won: 6,
  closed_lost: 0,
}

const STEPS = [
  { num: 1, label: 'Lead Created' },
  { num: 2, label: 'Proposal' },
  { num: 3, label: 'Checkout' },
  { num: 4, label: 'Connect POS' },
  { num: 5, label: 'Monitoring' },
  { num: 6, label: 'Sale Complete' },
]

const DEMO_FILES = [
  { id: '1', name: 'proposal_v2.pdf', description: 'Monthly pricing proposal', tag: 'Proposal' },
  { id: '2', name: 'contract_draft.pdf', description: 'Service agreement draft', tag: 'Contract' },
  { id: '3', name: 'pos_setup_guide.pdf', description: 'POS integration instructions', tag: 'Setup' },
]

function HorizontalStepper({ currentStep }: { currentStep: number }) {
  return (
    <div className="w-full py-6">
      <div className="flex items-center justify-between">
        {STEPS.map((step, idx) => (
          <div key={step.num} className="flex items-center flex-1 last:flex-none">
            {/* Circle */}
            <div className="flex flex-col items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${
                  step.num < currentStep
                    ? 'bg-[#00d4aa] text-white'
                    : step.num === currentStep
                    ? 'border-2 border-[#00d4aa] text-[#00d4aa] bg-transparent'
                    : 'bg-[#1a2420] text-[#6b7a74]'
                }`}
              >
                {step.num < currentStep ? <Check size={18} /> : step.num}
              </div>
              <span className={`text-[10px] mt-1.5 whitespace-nowrap ${
                step.num <= currentStep ? 'text-[#00d4aa]' : 'text-[#6b7a74]'
              }`}>
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {idx < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 mt-[-18px] ${
                step.num < currentStep ? 'bg-[#00d4aa]' : 'bg-[#1a2420]'
              }`} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function CanadaPortalLeadDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [deal, setDeal] = useState<Deal | null>(null)
  const [loading, setLoading] = useState(true)

  // Step 2 state
  const [monthlyPrice, setMonthlyPrice] = useState(500)
  const [setupFee, setSetupFee] = useState('250')
  const [firstMonthFree, setFirstMonthFree] = useState(false)

  // Step 4 state
  const [selectedPOS, setSelectedPOS] = useState<string | null>(null)
  const [accessToken, setAccessToken] = useState('')

  // Files state
  const [files, setFiles] = useState(DEMO_FILES)

  useEffect(() => {
    canadaSalesDemoData.deals().then(deals => {
      const found = deals.find(d => d.id === id)
      setDeal(found || null)
      if (found) {
        setMonthlyPrice(Math.round(found.monthly_value / 100) || 500)
      }
      setLoading(false)
    })
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#00d4aa] font-bold text-sm">S</span>
        </div>
      </div>
    )
  }

  if (!deal) {
    return (
      <div className="space-y-4">
        <Link to="/canada/portal/leads" className="inline-flex items-center gap-1.5 text-sm text-[#6b7a74] hover:text-white transition-colors">
          <ArrowLeft size={16} /> Leads
        </Link>
        <div className="text-center py-16 text-[#6b7a74]">Lead not found.</div>
      </div>
    )
  }

  const currentStep = STAGE_TO_STEP[deal.stage]

  function removeFile(fileId: string) {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#0f1512] border border-[#1a2420] rounded-lg text-sm text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50 focus:ring-1 focus:ring-[#00d4aa]/20 transition-colors'

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Back link */}
      <Link to="/canada/portal/leads" className="inline-flex items-center gap-1.5 text-sm text-[#6b7a74] hover:text-white transition-colors">
        <ArrowLeft size={16} /> Leads
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">{deal.business_name}</h1>
        <p className="text-sm text-[#6b7a74] mt-1">
          {deal.contact_name} &middot; ${deal.monthly_value.toLocaleString('en-CA')} CAD/mo &middot; {deal.contact_email}
        </p>
      </div>

      {/* Stepper */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
        <HorizontalStepper currentStep={currentStep} />
      </div>

      {/* Step 2 - Proposal */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Step 2 — Proposal</h2>

        {/* Monthly Price Slider */}
        <div>
          <label className="text-xs text-[#6b7a74] block mb-1.5">Monthly Price</label>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={250}
              max={1000}
              step={25}
              value={monthlyPrice}
              onChange={e => setMonthlyPrice(Number(e.target.value))}
              className="flex-1 h-2 bg-[#1a2420] rounded-full appearance-none cursor-pointer accent-[#00d4aa]"
            />
            <span className="text-sm font-semibold text-white w-24 text-right">${monthlyPrice} CAD</span>
          </div>
        </div>

        {/* Setup Fee */}
        <div>
          <label className="text-xs text-[#6b7a74] block mb-1.5">Setup Fee (CAD)</label>
          <input
            type="text"
            value={setupFee}
            onChange={e => setSetupFee(e.target.value)}
            className={inputClass}
            placeholder="e.g. 250"
          />
        </div>

        {/* First month free */}
        <label className="flex items-center gap-3 cursor-pointer">
          <div className={`w-9 h-5 rounded-full transition-colors relative ${firstMonthFree ? 'bg-[#00d4aa]' : 'bg-[#1a2420]'}`}
            onClick={() => setFirstMonthFree(!firstMonthFree)}
          >
            <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${firstMonthFree ? 'translate-x-4' : 'translate-x-0.5'}`} />
          </div>
          <span className="text-sm text-white">First month free</span>
        </label>

        {/* Buttons */}
        <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all">
          <Sparkles size={16} /> Regenerate Proposal
        </button>
        <div className="flex gap-3">
          <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 transition-all">
            <Eye size={16} /> View Proposal
          </button>
          <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 transition-all">
            <Mail size={16} /> Email Proposal
          </button>
        </div>
      </div>

      {/* Step 4 - Connect POS */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Step 4 — Connect POS</h2>

        {/* POS Cards */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { id: 'square', name: 'Square', emoji: '🟦' },
            { id: 'clover', name: 'Clover', emoji: '🍀' },
            { id: 'toast', name: 'Toast', emoji: '🍞' },
          ].map(pos => (
            <button
              key={pos.id}
              onClick={() => setSelectedPOS(pos.id)}
              className={`relative flex flex-col items-center gap-2 p-4 rounded-xl border transition-all ${
                selectedPOS === pos.id
                  ? 'border-[#00d4aa] bg-[#00d4aa]/5'
                  : 'border-[#1a2420] hover:border-[#4a5550]'
              }`}
            >
              {selectedPOS === pos.id && (
                <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-[#00d4aa] flex items-center justify-center">
                  <Check size={10} className="text-white" />
                </div>
              )}
              <span className="text-2xl">{pos.emoji}</span>
              <span className="text-xs font-medium text-white">{pos.name}</span>
            </button>
          ))}
        </div>

        {/* Access Token */}
        <div>
          <label className="text-xs text-[#6b7a74] block mb-1.5">Access Token</label>
          <input
            type="text"
            value={accessToken}
            onChange={e => setAccessToken(e.target.value)}
            className={inputClass}
            placeholder="Paste access token..."
          />
          <p className="text-[11px] text-[#4a5550] mt-1.5">
            Find this in your POS dashboard under Settings &gt; API
          </p>
        </div>

        {/* Save button */}
        <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all">
          <Wifi size={16} /> Save & Test Connection
        </button>
      </div>

      {/* Project Files */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Project Files</h2>
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#00d4aa] border border-[#00d4aa]/30 rounded-lg hover:bg-[#00d4aa]/10 transition-all">
            <Upload size={14} /> Upload
          </button>
        </div>

        <div className="space-y-2">
          {files.map(file => (
            <div key={file.id} className="flex items-center gap-3 p-3 bg-[#0a0f0d] border border-[#1a2420] rounded-lg">
              <FileText size={16} className="text-[#6b7a74] flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate">{file.name}</p>
                <p className="text-[11px] text-[#4a5550]">{file.description}</p>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-[#1a2420] text-[#6b7a74] font-medium flex-shrink-0">
                {file.tag}
              </span>
              <button
                onClick={() => removeFile(file.id)}
                className="p-1 rounded hover:bg-red-500/10 transition-colors flex-shrink-0"
              >
                <Trash2 size={14} className="text-[#6b7a74] hover:text-red-400" />
              </button>
            </div>
          ))}
          {files.length === 0 && (
            <p className="text-xs text-[#4a5550] text-center py-4">No files uploaded yet.</p>
          )}
        </div>
      </div>

      {/* Mark as Lost */}
      <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium rounded-lg hover:bg-red-500/15 transition-all">
        <X size={16} /> Mark as Lost
      </button>
    </div>
  )
}
