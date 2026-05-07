import { useState, useRef, useEffect, useMemo } from 'react'
import { clsx } from 'clsx'
import {
  Search, ChevronDown, CheckCircle2, Clock, ClipboardList,
  ExternalLink, Wifi, Upload, Bell, Check, AlertTriangle, Phone,
} from 'lucide-react'
import POSLogo, { POSStatusBadge } from './POSLogo'
import { posSystems, type POSSystem, type POSSystemKey } from '@/data/pos-systems'

interface POSSystemPickerProps {
  value: string | null
  onChange: (posKey: string) => void
  mode: 'lead-detail' | 'new-customer'
  portalContext: 'us' | 'canada'
  currency?: 'USD' | 'CAD'
  className?: string
}

interface PickerTheme {
  bg: string
  bgDeep: string
  border: string
  borderHover: string
  borderFocus: string
  accent: string
  accentText: string
  accentBg: string
  teal: string
  tealBg: string
  tealBorder: string
  text: string
  textMuted: string
  textDim: string
  selectedBg: string
  hoverBg: string
  ringFocus: string
  sectionBg: string
  inputBg: string
  inputBorder: string
  placeholder: string
}

const themes: Record<'us' | 'canada', PickerTheme> = {
  us: {
    bg: 'bg-[#0F0F12]',
    bgDeep: 'bg-[#0A0A0B]',
    border: 'border-[#1F1F23]',
    borderHover: 'hover:border-[#2A2A2E]',
    borderFocus: 'focus:border-[#1A8FD6]/40',
    accent: '#1A8FD6',
    accentText: 'text-[#1A8FD6]',
    accentBg: 'bg-[#1A8FD6]',
    teal: 'text-[#17C5B0]',
    tealBg: 'bg-[#17C5B0]/10',
    tealBorder: 'border-[#17C5B0]/20',
    text: 'text-[#F5F5F7]',
    textMuted: 'text-[#A1A1A8]',
    textDim: 'text-[#A1A1A8]/50',
    selectedBg: 'bg-[#1A8FD6]/5',
    hoverBg: 'hover:bg-[#1F1F23]/50',
    ringFocus: 'focus:ring-[#1A8FD6]/20',
    sectionBg: 'bg-[#0F0F12]',
    inputBg: 'bg-[#1F1F23]',
    inputBorder: 'border-[#2A2A2E]',
    placeholder: 'placeholder-[#A1A1A8]/30',
  },
  canada: {
    bg: 'bg-[#0f1512]',
    bgDeep: 'bg-[#0a0f0d]',
    border: 'border-[#1a2420]',
    borderHover: 'hover:border-[#4a5550]',
    borderFocus: 'focus:border-[#00d4aa]/50',
    accent: '#00d4aa',
    accentText: 'text-[#00d4aa]',
    accentBg: 'bg-[#00d4aa]',
    teal: 'text-[#00d4aa]',
    tealBg: 'bg-[#00d4aa]/10',
    tealBorder: 'border-[#00d4aa]/20',
    text: 'text-white',
    textMuted: 'text-[#6b7a74]',
    textDim: 'text-[#4a5550]',
    selectedBg: 'bg-[#00d4aa]/5',
    hoverBg: 'hover:bg-[#1a2420]/50',
    ringFocus: 'focus:ring-[#00d4aa]/20',
    sectionBg: 'bg-[#0a0f0d]',
    inputBg: 'bg-[#0a0f0d]',
    inputBorder: 'border-[#1a2420]',
    placeholder: 'placeholder-[#6b7a74]',
  },
}

export default function POSSystemPicker({
  value,
  onChange,
  mode,
  portalContext,
  currency = portalContext === 'canada' ? 'CAD' : 'USD',
  className,
}: POSSystemPickerProps) {
  const t = themes[portalContext]
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [waitlistEmail, setWaitlistEmail] = useState('')
  const [waitlistSubmitted, setWaitlistSubmitted] = useState(false)
  const [credentialValues, setCredentialValues] = useState<Record<string, string>>({})
  const ref = useRef<HTMLDivElement>(null)

  const selected = useMemo(
    () => (value ? posSystems.find(s => s.key === value) ?? null : null),
    [value],
  )

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => {
    setWaitlistEmail('')
    setWaitlistSubmitted(false)
    setCredentialValues({})
  }, [value])

  const available = useMemo(() => {
    let systems = posSystems
    if (portalContext === 'canada') {
      systems = systems.filter(s => s.canadaAvailable !== false)
    }
    return systems
  }, [portalContext])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? available.filter(s => s.name.toLowerCase().includes(q)) : available
  }, [search, available])

  const groups = useMemo(() => [
    { label: 'Currently Supported', icon: <CheckCircle2 size={14} className={t.teal} />, status: 'integrated' as const, items: filtered.filter(s => s.status === 'integrated') },
    { label: 'Coming Soon', icon: <Clock size={14} className="text-amber-400" />, status: 'coming_soon' as const, items: filtered.filter(s => s.status === 'coming_soon') },
    { label: 'Available via Manual Import', icon: <ClipboardList size={14} className={t.textMuted} />, status: 'contingency' as const, items: filtered.filter(s => s.status === 'contingency') },
    { label: 'Contact Us', icon: <Phone size={14} className={t.textDim} />, status: 'unsupported' as const, items: filtered.filter(s => s.status === 'unsupported') },
  ], [filtered, t])

  function handleSelect(sys: POSSystem) {
    onChange(sys.key)
    setOpen(false)
    setSearch('')
  }

  function updateCredential(fieldId: string, val: string) {
    setCredentialValues(prev => ({ ...prev, [fieldId]: val }))
  }

  return (
    <div className={clsx('relative', className)} ref={ref}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={clsx(
          'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-colors',
          t.bg, t.border, t.borderHover,
          open && `${t.borderFocus} ring-1 ${t.ringFocus}`,
        )}
      >
        {selected ? (
          <>
            <POSLogo system={selected.key as POSSystemKey} size="sm" />
            <span className={clsx('flex-1 text-sm font-medium', t.text)}>{selected.name}</span>
            <POSStatusBadge status={selected.status} />
            {portalContext === 'canada' && selected.canadaAvailable && (
              <span className="text-[9px] font-medium text-[#6b7a74]">CA</span>
            )}
          </>
        ) : (
          <span className={clsx('flex-1 text-sm', t.textMuted)}>Search POS systems...</span>
        )}
        <ChevronDown size={16} className={clsx(t.textMuted, 'transition-transform', open && 'rotate-180')} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className={clsx('absolute z-50 left-0 right-0 mt-1 rounded-lg border shadow-xl overflow-hidden', t.bg, t.border)}>
          <div className="p-2">
            <div className="relative">
              <Search size={14} className={clsx('absolute left-2.5 top-1/2 -translate-y-1/2', t.textMuted)} />
              <input
                autoFocus
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search POS systems..."
                className={clsx(
                  'w-full pl-8 pr-3 py-2 text-xs rounded-md focus:outline-none',
                  t.inputBg, t.inputBorder, 'border', t.text, t.placeholder, t.borderFocus,
                )}
              />
            </div>
          </div>
          <div className="max-h-[400px] overflow-y-auto">
            {groups.map(g => g.items.length > 0 && (
              <div key={g.status}>
                <div className={clsx('flex items-center gap-1.5 px-3 py-1.5', t.sectionBg)}>
                  {g.icon}
                  <span className={clsx('text-[10px] font-semibold uppercase tracking-wider', t.textMuted)}>{g.label}</span>
                </div>
                {g.items.map(sys => (
                  <button
                    key={sys.key}
                    type="button"
                    onClick={() => handleSelect(sys)}
                    className={clsx(
                      'w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors',
                      t.hoverBg,
                      value === sys.key && t.selectedBg,
                    )}
                  >
                    <POSLogo system={sys.key as POSSystemKey} size="sm" />
                    <span className={clsx('flex-1 text-xs font-medium', t.text)}>{sys.name}</span>
                    <POSStatusBadge status={sys.status} />
                    {sys.status !== 'integrated' && (
                      <span className={clsx('text-[9px] font-medium', t.textDim)}>(Demo)</span>
                    )}
                    {portalContext === 'canada' && sys.canadaAvailable && (
                      <span className="text-[9px] font-medium text-[#6b7a74]">CA</span>
                    )}
                  </button>
                ))}
              </div>
            ))}
            {filtered.length === 0 && (
              <p className={clsx('text-xs text-center py-4', t.textDim)}>No POS systems match your search.</p>
            )}
          </div>
        </div>
      )}

      {/* Detail card */}
      {selected && (
        <DetailCard
          system={selected}
          theme={t}
          mode={mode}
          portalContext={portalContext}
          credentialValues={credentialValues}
          onCredentialChange={updateCredential}
          waitlistEmail={waitlistEmail}
          onWaitlistEmailChange={setWaitlistEmail}
          waitlistSubmitted={waitlistSubmitted}
          onWaitlistSubmit={() => waitlistEmail.trim() && setWaitlistSubmitted(true)}
        />
      )}
    </div>
  )
}

type Theme = PickerTheme

function DetailCard({
  system, theme: t, mode, portalContext,
  credentialValues, onCredentialChange,
  waitlistEmail, onWaitlistEmailChange, waitlistSubmitted, onWaitlistSubmit,
}: {
  system: POSSystem
  theme: Theme
  mode: 'lead-detail' | 'new-customer'
  portalContext: 'us' | 'canada'
  credentialValues: Record<string, string>
  onCredentialChange: (fieldId: string, val: string) => void
  waitlistEmail: string
  onWaitlistEmailChange: (v: string) => void
  waitlistSubmitted: boolean
  onWaitlistSubmit: () => void
}) {
  return (
    <div className={clsx('mt-3 rounded-xl border p-4 space-y-4', t.bg, t.border)}>
      {/* Header */}
      <div className="flex items-center gap-3">
        <POSLogo system={system.key as POSSystemKey} size="lg" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={clsx('text-sm font-semibold', t.text)}>{system.name}</span>
            <POSStatusBadge status={system.status} />
          </div>
          <a
            href={system.website}
            target="_blank"
            rel="noopener noreferrer"
            className={clsx('inline-flex items-center gap-1 text-[11px] transition-colors', t.textMuted, `hover:${t.teal}`)}
          >
            {system.website.replace(/^https?:\/\//, '')} <ExternalLink size={10} />
          </a>
        </div>
      </div>

      {/* Status-dependent content */}
      {system.status === 'integrated' && (
        <IntegratedContent
          system={system} theme={t} mode={mode}
          credentialValues={credentialValues}
          onCredentialChange={onCredentialChange}
        />
      )}
      {system.status === 'coming_soon' && (
        <ComingSoonContent
          system={system} theme={t}
          waitlistEmail={waitlistEmail}
          onWaitlistEmailChange={onWaitlistEmailChange}
          waitlistSubmitted={waitlistSubmitted}
          onWaitlistSubmit={onWaitlistSubmit}
        />
      )}
      {system.status === 'contingency' && (
        <ManualImportContent system={system} theme={t} />
      )}
      {system.status === 'unsupported' && (
        <ComingSoonContent
          system={system} theme={t}
          waitlistEmail={waitlistEmail}
          onWaitlistEmailChange={onWaitlistEmailChange}
          waitlistSubmitted={waitlistSubmitted}
          onWaitlistSubmit={onWaitlistSubmit}
        />
      )}
    </div>
  )
}

function IntegratedContent({
  system, theme: t, mode, credentialValues, onCredentialChange,
}: {
  system: POSSystem
  theme: Theme
  mode: 'lead-detail' | 'new-customer'
  credentialValues: Record<string, string>
  onCredentialChange: (fieldId: string, val: string) => void
}) {
  const reqs = system.merchantRequirements ?? []
  const steps: { step: number; title: string; instruction: string; srAction?: string }[] =
    system.setupSteps ?? system.connectionRequirements.stepByStepInstructions.map((s, i) => ({
      step: i + 1,
      title: `Step ${i + 1}`,
      instruction: s,
    }))
  const { connectionRequirements: cr, dataAvailable } = system

  return (
    <>
      {/* Requirements */}
      <div>
        <p className={clsx('text-xs font-semibold mb-2', t.text)}>What Meridian needs from {system.name}:</p>
        <div className="space-y-1.5">
          {(reqs.length > 0 ? reqs.map(r => r.label) : cr.requiredCredentials).map(cred => (
            <div key={cred} className="flex items-center gap-2">
              <Check size={12} className={clsx(t.teal, 'flex-shrink-0')} />
              <span className={clsx('text-[11px]', t.textMuted)}>{cred}</span>
            </div>
          ))}
        </div>
      </div>

      {cr.planRequired && (
        <p className={clsx('text-[11px]', t.textMuted)}>
          <span className={clsx('font-medium', t.text)}>Required Plan:</span> {cr.planRequired}
        </p>
      )}

      {cr.requiredPermissions.length > 0 && (
        <p className={clsx('text-[11px]', t.textMuted)}>
          <span className={clsx('font-medium', t.text)}>Required Permissions:</span>{' '}
          {cr.requiredPermissions.join(', ')}
        </p>
      )}

      {/* Steps */}
      <div>
        <p className={clsx('text-xs font-semibold mb-2', t.text)}>Steps:</p>
        <ol className="space-y-1.5">
          {steps.map((s, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className={clsx('text-[10px] font-bold mt-px w-4 flex-shrink-0', t.teal)}>{s.step}.</span>
              <div>
                <span className={clsx('text-[11px]', t.textMuted)}>{s.instruction}</span>
                {s.srAction && mode === 'lead-detail' && (
                  <span className={clsx('text-[10px] block', t.textDim)}>SR: {s.srAction}</span>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>

      <DataPills data={dataAvailable} theme={t} />

      {/* Credential inputs (lead-detail mode only) */}
      {mode === 'lead-detail' && reqs.length > 0 && reqs.filter(r => r.fieldType !== 'oauth_button').map(req => (
        <div key={req.fieldId}>
          <label className={clsx('text-xs block mb-1.5', t.textMuted)}>{req.label}</label>
          {req.fieldType === 'file_upload' ? (
            <div className={clsx('flex items-center justify-center gap-2 px-4 py-6 rounded-lg border border-dashed cursor-pointer', t.border, t.bg)}>
              <Upload size={16} className={t.textMuted} />
              <span className={clsx('text-xs', t.textMuted)}>Click or drag to upload</span>
            </div>
          ) : (
            <input
              type={req.fieldType === 'password' ? 'password' : 'text'}
              value={credentialValues[req.fieldId] || ''}
              onChange={e => onCredentialChange(req.fieldId, e.target.value)}
              className={clsx(
                'w-full px-3 py-2.5 rounded-lg border text-sm focus:outline-none focus:ring-1 transition-colors',
                t.bg, t.border, t.text, t.placeholder, t.borderFocus, t.ringFocus,
              )}
              placeholder={req.placeholder}
            />
          )}
          <p className={clsx('text-[11px] mt-1.5', t.textDim)}>{req.howToFind}</p>
        </div>
      ))}

      {/* Auto-generated credential inputs when merchantRequirements not defined */}
      {mode === 'lead-detail' && reqs.length === 0 && (
        <AutoCredentialFields system={system} theme={t} credentialValues={credentialValues} onCredentialChange={onCredentialChange} />
      )}

      {/* Connect button */}
      <button
        type="button"
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg transition-all text-white"
        style={{ backgroundColor: t.accent }}
      >
        <Wifi size={16} /> Connect {system.name} (Demo)
      </button>

      {/* SR notes */}
      {mode === 'lead-detail' && system.notesForSR && (
        <p className={clsx('text-[11px] leading-relaxed', t.textDim)}>
          <span className={clsx('font-medium', t.textMuted)}>SR Notes:</span> {system.notesForSR}
        </p>
      )}
    </>
  )
}

function ComingSoonContent({
  system, theme: t,
  waitlistEmail, onWaitlistEmailChange, waitlistSubmitted, onWaitlistSubmit,
}: {
  system: POSSystem
  theme: Theme
  waitlistEmail: string
  onWaitlistEmailChange: (v: string) => void
  waitlistSubmitted: boolean
  onWaitlistSubmit: () => void
}) {
  return (
    <>
      <p className={clsx('text-[11px] leading-relaxed', t.textMuted)}>
        {system.integrationStatus.notes}
      </p>

      {system.connectionRequirements.requiredCredentials.length > 0 && (
        <div>
          <p className={clsx('text-xs font-semibold mb-1.5', t.text)}>What we'll need from {system.name}:</p>
          <ul className="space-y-1">
            {system.connectionRequirements.requiredCredentials.map(cred => (
              <li key={cred} className={clsx('text-[11px] flex items-center gap-2', t.textMuted)}>
                <span className={clsx('w-1 h-1 rounded-full flex-shrink-0', t.textDim)} style={{ backgroundColor: 'currentColor' }} />
                {cred}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Manual export interim */}
      {system.contingencyPlan.manualUploadSupported && (
        <div className={clsx('rounded-lg p-3 border', t.bgDeep, t.border)}>
          <p className={clsx('text-[11px] font-semibold mb-1', t.text)}>In the meantime — Manual Export</p>
          <p className={clsx('text-[11px] leading-relaxed', t.textMuted)}>
            {system.contingencyPlan.exportInstructions}
          </p>
        </div>
      )}

      <button
        type="button"
        disabled
        className={clsx('w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg cursor-not-allowed', t.textDim)}
        style={{ backgroundColor: 'rgba(128,128,128,0.1)' }}
      >
        Coming Soon
      </button>

      {!waitlistSubmitted ? (
        <div className="flex gap-2">
          <input
            type="email"
            value={waitlistEmail}
            onChange={e => onWaitlistEmailChange(e.target.value)}
            placeholder="your@email.com"
            className={clsx(
              'flex-1 px-3 py-2 text-xs rounded-lg border focus:outline-none',
              t.bgDeep, t.border, t.text, t.placeholder, t.borderFocus,
            )}
          />
          <button
            type="button"
            onClick={onWaitlistSubmit}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-amber-400/10 border border-amber-400/20 text-amber-400 rounded-lg hover:bg-amber-400/20 transition-colors"
          >
            <Bell size={12} /> Notify Me
          </button>
        </div>
      ) : (
        <p className={clsx('text-[11px] flex items-center gap-1.5', t.teal)}>
          <CheckCircle2 size={12} /> We'll email you when {system.name} is live.
        </p>
      )}
    </>
  )
}

function ManualImportContent({ system, theme: t }: { system: POSSystem; theme: Theme }) {
  const { contingencyPlan: cp, dataAvailable } = system

  return (
    <>
      <div>
        <p className={clsx('text-xs font-semibold mb-1.5', t.text)}>How to export your {system.name} data:</p>
        <p className={clsx('text-[11px] leading-relaxed', t.textMuted)}>{cp.exportInstructions}</p>
      </div>

      <div className={clsx('rounded-lg p-3 border', t.bgDeep, t.border)}>
        <p className={clsx('text-[11px] font-semibold mb-1', t.text)}>What to do with the export:</p>
        <p className={clsx('text-[11px]', t.textMuted)}>
          Upload the {cp.dataExportFormat} below — Meridian will map the columns automatically.
        </p>
      </div>

      {/* Upload zone */}
      <button
        type="button"
        className={clsx(
          'w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg border transition-colors',
          'bg-[#7c3aed]/10 border-[#7c3aed]/30 text-[#7c3aed] hover:bg-[#7c3aed]/20',
        )}
      >
        <Upload size={16} /> Upload {cp.dataExportFormat}
      </button>

      <DataPills data={dataAvailable} theme={t} />

      {cp.limitations.length > 0 && (
        <div className="rounded-lg p-3 bg-amber-500/5 border border-amber-500/10">
          <div className="flex items-center gap-1.5 mb-1">
            <AlertTriangle size={11} className="text-amber-400" />
            <span className="text-[10px] font-medium text-amber-400">Limitations</span>
          </div>
          <ul className="space-y-0.5">
            {cp.limitations.map(l => (
              <li key={l} className={clsx('text-[10px]', t.textDim)}>• {l}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}

function AutoCredentialFields({
  system, theme: t, credentialValues, onCredentialChange,
}: {
  system: POSSystem
  theme: Theme
  credentialValues: Record<string, string>
  onCredentialChange: (fieldId: string, val: string) => void
}) {
  const auth = system.authMethod ?? (system.integrationStatus.oauthSupported ? 'oauth2' : system.integrationStatus.apiAvailable ? 'api_key' : 'manual_export')
  const creds = system.connectionRequirements.requiredCredentials

  if (auth === 'oauth2') {
    return (
      <>
        <button
          type="button"
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg transition-all text-white"
          style={{ backgroundColor: t.accent }}
        >
          <ExternalLink size={14} /> Authorize with {system.name}
        </button>
        {creds.filter(c => !c.toLowerCase().includes('oauth')).map(cred => {
          const fieldId = cred.toLowerCase().replace(/[^a-z0-9]+/g, '_')
          return (
            <div key={fieldId}>
              <label className={clsx('text-xs block mb-1.5', t.textMuted)}>{cred}</label>
              <input
                type="text"
                value={credentialValues[fieldId] || ''}
                onChange={e => onCredentialChange(fieldId, e.target.value)}
                className={clsx(
                  'w-full px-3 py-2.5 rounded-lg border text-sm focus:outline-none focus:ring-1 transition-colors',
                  t.bg, t.border, t.text, t.placeholder, t.borderFocus, t.ringFocus,
                )}
                placeholder={`Enter ${cred}`}
              />
            </div>
          )
        })}
      </>
    )
  }

  if (auth === 'manual_export') {
    return (
      <div className={clsx('flex items-center justify-center gap-2 px-4 py-8 rounded-lg border border-dashed cursor-pointer', t.border, t.bg)}>
        <Upload size={16} className={t.textMuted} />
        <span className={clsx('text-xs', t.textMuted)}>Upload {system.contingencyPlan.dataExportFormat || 'CSV'} export from {system.name}</span>
      </div>
    )
  }

  const fields: { id: string; label: string; type: 'text' | 'password' }[] = []
  for (const cred of creds) {
    const lower = cred.toLowerCase()
    const id = lower.replace(/[^a-z0-9]+/g, '_')
    const isSecret = lower.includes('secret') || lower.includes('password') || lower.includes('key')
    fields.push({ id, label: cred, type: isSecret ? 'password' : 'text' })
  }

  if (fields.length === 0 && auth === 'api_key') {
    fields.push({ id: 'api_key', label: 'API Key', type: 'password' })
  }
  if (fields.length === 0 && auth === 'api_key_plus_secret') {
    fields.push({ id: 'api_key', label: 'API Key', type: 'password' }, { id: 'api_secret', label: 'API Secret', type: 'password' })
  }
  if (fields.length === 0 && auth === 'username_password') {
    fields.push({ id: 'username', label: 'Username', type: 'text' }, { id: 'password', label: 'Password', type: 'password' })
  }

  return (
    <>
      {fields.map(f => (
        <div key={f.id}>
          <label className={clsx('text-xs block mb-1.5', t.textMuted)}>{f.label}</label>
          <input
            type={f.type}
            value={credentialValues[f.id] || ''}
            onChange={e => onCredentialChange(f.id, e.target.value)}
            className={clsx(
              'w-full px-3 py-2.5 rounded-lg border text-sm focus:outline-none focus:ring-1 transition-colors',
              t.bg, t.border, t.text, t.placeholder, t.borderFocus, t.ringFocus,
            )}
            placeholder={`Enter ${f.label}`}
          />
        </div>
      ))}
    </>
  )
}

const DATA_KEYS = ['sales', 'inventory', 'employees', 'customers', 'menuItems', 'realTime'] as const

function DataPills({ data, theme: t }: { data: POSSystem['dataAvailable']; theme: Theme }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {DATA_KEYS.map(k => (
        <span
          key={k}
          className={clsx(
            'text-[10px] px-2 py-0.5 rounded-full border font-medium',
            data[k]
              ? `${t.teal} ${t.tealBg} ${t.tealBorder}`
              : `${t.textDim} bg-transparent ${t.border}`,
          )}
        >
          {k === 'menuItems' ? 'menu items' : k === 'realTime' ? 'real-time' : k}
        </span>
      ))}
    </div>
  )
}
