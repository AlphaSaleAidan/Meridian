import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Check, Sparkles, Wifi, X, Upload, Trash2,
  FileText, Eye, Mail, CheckCircle2, Loader2, Download, ChevronRight, Pencil, Save,
} from 'lucide-react'
import POSSystemPicker from '@/components/POSSystemPicker'
import { type Deal, type DealStage } from '@/lib/canada-sales-demo-data'
import { canadaLeadsService } from '@/lib/canada-leads-service'
import { getPlan } from '@/lib/canada-proposal-plans'
import { getPosSystem, validateCredentials, serializeCredentials } from '@/lib/pos-credentials'
import { generateProposalPdf } from '@/lib/generate-proposal-pdf'
import { useSalesAuth } from '@/lib/sales-auth'

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
  { num: 1, label: 'Prospecting' },
  { num: 2, label: 'Contacted' },
  { num: 3, label: 'Demo' },
  { num: 4, label: 'Proposal Sent' },
  { num: 5, label: 'Negotiation' },
  { num: 6, label: 'Closed Won' },
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
  const { rep } = useSalesAuth()
  const [deal, setDeal] = useState<Deal | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({ business_name: '', contact_name: '', contact_email: '', contact_phone: '', notes: '' })
  const [editSaving, setEditSaving] = useState(false)

  // Step 2 state
  const [monthlyPrice, setMonthlyPrice] = useState(500)
  const [setupFee, setSetupFee] = useState('250')
  const [firstMonthFree, setFirstMonthFree] = useState(false)

  // Proposal state
  const [proposalBlob, setProposalBlob] = useState<Blob | null>(null)
  const [proposalGenerating, setProposalGenerating] = useState(false)
  const [proposalEmailing, setProposalEmailing] = useState(false)
  const [proposalSent, setProposalSent] = useState(false)

  // Step 4 state
  const [selectedPOS, setSelectedPOS] = useState<string | null>(null)
  const [posConnecting, setPosConnecting] = useState(false)
  const [posConnected, setPosConnected] = useState(false)
  const [posError, setPosError] = useState<string | null>(null)

  async function handleCredentialSubmit(posKey: string, credentials: Record<string, string>) {
    const system = getPosSystem(posKey)
    if (!system) return

    const { valid, errors } = validateCredentials(system, credentials)
    if (!valid) {
      const firstError = Object.values(errors)[0]
      setPosError(firstError)
      return
    }

    setPosConnecting(true)
    setPosError(null)

    const { provider, credentials: creds } = serializeCredentials(system, credentials)

    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/onboarding/connect-pos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deal_id: deal?.id,
          provider,
          credentials: creds,
          business_name: deal?.business_name,
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setPosError(body.detail || 'Connection failed — check credentials and try again.')
        setPosConnecting(false)
        return
      }

      setPosConnected(true)
      setPosConnecting(false)

      if (deal && deal.stage === 'proposal_sent') {
        await canadaLeadsService.updateStage(deal.id, 'negotiation')
        setDeal(prev => prev ? { ...prev, stage: 'negotiation' } : prev)
      }
    } catch {
      setPosError('Network error — please try again.')
      setPosConnecting(false)
    }
  }

  const buildProposalInput = useCallback(() => {
    if (!deal || !rep) return null
    const closestPlan = monthlyPrice >= 750 ? 'command' : monthlyPrice >= 375 ? 'premium' : 'standard'
    const plan = getPlan(closestPlan)
    return {
      businessName: deal.business_name,
      ownerName: deal.contact_name,
      email: deal.contact_email,
      plan,
      customPrice: monthlyPrice,
      setupFee: Number(setupFee) || 0,
      firstMonthFree,
      rep,
    }
  }, [deal, rep, monthlyPrice, setupFee, firstMonthFree])

  async function handleGenerateProposal() {
    const input = buildProposalInput()
    if (!input) return
    setProposalGenerating(true)
    try {
      const blob = await generateProposalPdf(input)
      setProposalBlob(blob)
      if (deal && deal.stage === 'prospecting') {
        await canadaLeadsService.updateStage(deal.id, 'contacted')
        setDeal(prev => prev ? { ...prev, stage: 'contacted' } : prev)
      }
    } catch (err) {
      console.error('[Proposal] Generation failed:', err)
    } finally {
      setProposalGenerating(false)
    }
  }

  async function handleViewProposal() {
    let blob = proposalBlob
    if (!blob) {
      const input = buildProposalInput()
      if (!input) return
      setProposalGenerating(true)
      try {
        blob = await generateProposalPdf(input)
        setProposalBlob(blob)
      } finally {
        setProposalGenerating(false)
      }
    }
    if (blob) {
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    }
  }

  function handleDownloadProposal() {
    if (!proposalBlob || !deal) return
    const url = URL.createObjectURL(proposalBlob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Meridian_Proposal_${deal.business_name.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  async function handleEmailProposal() {
    if (!deal) return
    if (!proposalBlob) await handleGenerateProposal()
    setProposalEmailing(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      await fetch(`${API_BASE}/api/email/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template: 'proposal_sent',
          to: deal.contact_email,
          first_name: deal.contact_name.split(' ')[0],
          portal: 'canada',
          extra: {
            business_name: deal.business_name,
            rep_name: rep?.name || '',
            rep_email: rep?.email || '',
            plan_name: monthlyPrice >= 750 ? 'Command' : monthlyPrice >= 375 ? 'Premium' : 'Standard',
            monthly_price: `CA$${monthlyPrice.toLocaleString()}`,
          },
        }),
      })
      setProposalSent(true)
      if (deal.stage === 'contacted' || deal.stage === 'demo_scheduled') {
        await canadaLeadsService.updateStage(deal.id, 'proposal_sent')
        setDeal(prev => prev ? { ...prev, stage: 'proposal_sent' } : prev)
      }
    } catch (err) {
      console.error('[Proposal] Email failed:', err)
    } finally {
      setProposalEmailing(false)
    }
  }

  // Files state
  const [files, setFiles] = useState(DEMO_FILES)

  useEffect(() => {
    canadaLeadsService.getById(id!).then(found => {
      setDeal(found)
      if (found) {
        setMonthlyPrice(found.monthly_value || 500)
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

  function handleUpload() {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf,.doc,.docx,.xls,.xlsx,.csv,.png,.jpg,.jpeg'
    input.onchange = () => {
      const file = input.files?.[0]
      if (!file) return
      const ext = file.name.split('.').pop()?.toUpperCase() || 'File'
      setFiles(prev => [...prev, { id: String(Date.now()), name: file.name, description: `Uploaded ${ext} file`, tag: ext }])
    }
    input.click()
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#0f1512] border border-[#1a2420] rounded-lg text-sm text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50 focus:ring-1 focus:ring-[#00d4aa]/20 transition-colors'

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Back link */}
      <Link to="/canada/portal/leads" className="inline-flex items-center gap-1.5 text-sm text-[#6b7a74] hover:text-white transition-colors">
        <ArrowLeft size={16} /> Leads
      </Link>

      {/* Header */}
      {editing ? (
        <div className="bg-[#0f1512] border border-[#00d4aa]/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#00d4aa]">Edit Lead</h2>
            <button onClick={() => setEditing(false)} className="text-xs text-[#6b7a74] hover:text-white">Cancel</button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input value={editForm.business_name} onChange={e => setEditForm(f => ({ ...f, business_name: e.target.value }))} className={inputClass} placeholder="Business Name" />
            <input value={editForm.contact_name} onChange={e => setEditForm(f => ({ ...f, contact_name: e.target.value }))} className={inputClass} placeholder="Contact Name" />
            <input value={editForm.contact_email} onChange={e => setEditForm(f => ({ ...f, contact_email: e.target.value }))} className={inputClass} placeholder="Email" />
            <input value={editForm.contact_phone} onChange={e => setEditForm(f => ({ ...f, contact_phone: e.target.value }))} className={inputClass} placeholder="Phone" />
            <textarea value={editForm.notes} onChange={e => setEditForm(f => ({ ...f, notes: e.target.value }))} className={inputClass + ' sm:col-span-2 resize-none h-20'} placeholder="Notes" />
          </div>
          <button
            disabled={editSaving}
            onClick={async () => {
              setEditSaving(true)
              await canadaLeadsService.update(deal.id, editForm)
              setDeal(prev => prev ? { ...prev, ...editForm } : prev)
              setEditing(false)
              setEditSaving(false)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
          >
            {editSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save Changes
          </button>
        </div>
      ) : (
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{deal.business_name}</h1>
            <p className="text-sm text-[#6b7a74] mt-1">
              {deal.contact_name} &middot; <span className="text-[#f0b429] font-semibold">CA${deal.monthly_value.toLocaleString()}/mo</span> &middot; {deal.contact_email}
            </p>
          </div>
          <button
            onClick={() => {
              setEditForm({
                business_name: deal.business_name,
                contact_name: deal.contact_name,
                contact_email: deal.contact_email,
                contact_phone: deal.contact_phone,
                notes: deal.notes,
              })
              setEditing(true)
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#6b7a74] border border-[#1a2420] rounded-lg hover:text-white hover:border-[#2a3430] transition-colors"
          >
            <Pencil size={12} /> Edit
          </button>
        </div>
      )}

      {/* Stepper */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
        <HorizontalStepper currentStep={currentStep} />
      </div>

      {/* Step 2 - Proposal */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Proposal</h2>

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
            <span className="text-sm font-semibold text-[#f0b429] w-28 text-right">CA${monthlyPrice.toLocaleString()}/mo</span>
          </div>
        </div>

        {/* Setup Fee */}
        <div>
          <label className="text-xs text-[#6b7a74] block mb-1.5">Setup Fee</label>
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
        <button
          onClick={handleGenerateProposal}
          disabled={proposalGenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
        >
          {proposalGenerating ? (
            <><Loader2 size={16} className="animate-spin" /> Generating…</>
          ) : (
            <><Sparkles size={16} /> {proposalBlob ? 'Regenerate Proposal' : 'Generate Proposal'}</>
          )}
        </button>

        {proposalBlob && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
            <CheckCircle2 size={16} className="text-[#00d4aa]" />
            <span className="text-xs text-[#00d4aa] font-medium">Proposal ready — 9 slides, PDF generated.</span>
            <button onClick={handleDownloadProposal} className="ml-auto text-[#00d4aa] hover:text-white transition-colors">
              <Download size={14} />
            </button>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleViewProposal}
            disabled={proposalGenerating}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 disabled:opacity-50 transition-all"
          >
            <Eye size={16} /> View Proposal
          </button>
          <button
            onClick={handleEmailProposal}
            disabled={proposalEmailing || proposalGenerating}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] text-white text-sm font-medium rounded-lg hover:border-[#00d4aa]/30 disabled:opacity-50 transition-all"
          >
            {proposalEmailing ? (
              <><Loader2 size={16} className="animate-spin" /> Sending…</>
            ) : proposalSent ? (
              <><CheckCircle2 size={16} className="text-[#00d4aa]" /> Sent!</>
            ) : (
              <><Mail size={16} /> Email Proposal</>
            )}
          </button>
        </div>
      </div>

      {/* Step 4 - Connect POS */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Connect POS</h2>
        <POSSystemPicker
          value={selectedPOS}
          onChange={k => { setSelectedPOS(k); setPosConnected(false); setPosError(null) }}
          onCredentialSubmit={handleCredentialSubmit}
          mode="lead-detail"
          portalContext="canada"
        />

        {posError && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
            {posError}
          </div>
        )}

        {posConnected && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
            <CheckCircle2 size={16} className="text-[#00d4aa]" />
            <span className="text-xs text-[#00d4aa] font-medium">
              POS connected — the swarm is pulling data now.
            </span>
          </div>
        )}

        {!posConnected && selectedPOS && (
          <button
            onClick={() => handleCredentialSubmit(selectedPOS, {})}
            disabled={posConnecting}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
          >
            {posConnecting ? (
              <><Loader2 size={16} className="animate-spin" /> Connecting...</>
            ) : (
              <><Wifi size={16} /> Save & Test Connection</>
            )}
          </button>
        )}
      </div>

      {/* Project Files */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Project Files</h2>
          <button onClick={handleUpload} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#00d4aa] border border-[#00d4aa]/30 rounded-lg hover:bg-[#00d4aa]/10 transition-all">
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

      {/* Stage Advancement */}
      {deal.stage !== 'closed_won' && deal.stage !== 'closed_lost' && (
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white">Advance Deal</h2>
          {deal.stage === 'negotiation' ? (
            <button
              onClick={async () => {
                if (!confirm('Close this deal as won? This will mark it as a completed sale.')) return
                await canadaLeadsService.updateStage(deal.id, 'closed_won')
                setDeal(prev => prev ? { ...prev, stage: 'closed_won' } : prev)
              }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
            >
              <CheckCircle2 size={16} /> Close Deal — Sale Complete
            </button>
          ) : (
            <button
              onClick={async () => {
                const order: DealStage[] = ['prospecting', 'contacted', 'demo_scheduled', 'proposal_sent', 'negotiation']
                const stageLabels: Record<string, string> = { contacted: 'Contacted', demo_scheduled: 'Demo Scheduled', proposal_sent: 'Proposal Sent', negotiation: 'Negotiation' }
                const idx = order.indexOf(deal.stage)
                if (idx >= 0 && idx < order.length - 1) {
                  const nextStage = order[idx + 1]
                  if (!confirm(`Advance this deal to "${stageLabels[nextStage]}"?`)) return
                  await canadaLeadsService.updateStage(deal.id, nextStage)
                  setDeal(prev => prev ? { ...prev, stage: nextStage } : prev)
                }
              }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-[#00d4aa]/30 text-[#00d4aa] text-sm font-medium rounded-lg hover:bg-[#00d4aa]/10 transition-all"
            >
              <ChevronRight size={16} /> Advance to Next Stage
            </button>
          )}
        </div>
      )}

      {/* Convert to Customer (when closed_won) */}
      {deal.stage === 'closed_won' && (
        <div className="bg-[#0f1512] border border-[#00d4aa]/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-[#00d4aa]" />
            <h2 className="text-sm font-semibold text-[#00d4aa]">Deal Closed — Ready to Onboard</h2>
          </div>
          <p className="text-xs text-[#6b7a74]">
            This deal is closed. Create a customer account to provision their Meridian dashboard, connect their POS, and start billing.
          </p>
          <button
            onClick={() => navigate(`/canada/portal/new-customer?lead=${deal.id}&name=${encodeURIComponent(deal.business_name)}&contact=${encodeURIComponent(deal.contact_name)}&email=${encodeURIComponent(deal.contact_email)}&phone=${encodeURIComponent(deal.contact_phone)}&vertical=${encodeURIComponent(deal.vertical)}`)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
          >
            <Sparkles size={16} /> Create Customer Account
          </button>
        </div>
      )}

      {/* Mark as Lost */}
      {deal.stage !== 'closed_won' && deal.stage !== 'closed_lost' && (
        <button
          onClick={async () => {
            if (!confirm('Mark this deal as lost? You can still view it in the Closed tab.')) return
            await canadaLeadsService.updateStage(deal.id, 'closed_lost')
            navigate('/canada/portal/leads')
          }}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium rounded-lg hover:bg-red-500/15 transition-all"
        >
          <X size={16} /> Mark as Lost
        </button>
      )}
    </div>
  )
}
