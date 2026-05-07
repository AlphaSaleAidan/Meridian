import { useState, useRef, useEffect, useMemo } from 'react'
import { clsx } from 'clsx'
import {
  Search, ChevronDown, CheckCircle2, Clock, ClipboardList,
  ExternalLink, Wifi, Upload, Bell, Check,
} from 'lucide-react'
import POSLogo, { POSStatusBadge } from './POSLogo'
import { posSystems, type POSSystem, type POSSystemKey } from '@/data/pos-systems'

interface PortalPOSPickerProps {
  value: string | null
  onChange: (posKey: string) => void
  mode: 'lead-detail' | 'new-customer'
  className?: string
}

const STATUS_COLORS: Record<string, string> = {
  integrated: '#00d4aa',
  coming_soon: '#fbbf24',
  contingency: '#7c3aed',
}

const DATA_KEYS = ['sales', 'inventory', 'employees', 'customers', 'menuItems', 'realTime'] as const

export default function PortalPOSPicker({ value, onChange, mode, className }: PortalPOSPickerProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [waitlistEmail, setWaitlistEmail] = useState('')
  const [waitlistSubmitted, setWaitlistSubmitted] = useState(false)
  const [accessToken, setAccessToken] = useState('')
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
    setAccessToken('')
  }, [value])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? posSystems.filter(s => s.name.toLowerCase().includes(q)) : posSystems
  }, [search])

  const groups: { label: string; icon: React.ReactNode; status: string; items: POSSystem[] }[] = useMemo(() => [
    { label: 'Currently Supported', icon: <CheckCircle2 size={14} className="text-[#00d4aa]" />, status: 'integrated', items: filtered.filter(s => s.status === 'integrated') },
    { label: 'Coming Soon', icon: <Clock size={14} className="text-amber-400" />, status: 'coming_soon', items: filtered.filter(s => s.status === 'coming_soon') },
    { label: 'Available via Manual Import', icon: <ClipboardList size={14} className="text-[#6b7a74]" />, status: 'contingency', items: filtered.filter(s => s.status === 'contingency') },
  ], [filtered])

  function handleSelect(sys: POSSystem) {
    onChange(sys.key)
    setOpen(false)
    setSearch('')
  }

  return (
    <div className={clsx('relative', className)} ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={clsx(
          'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-colors',
          'bg-[#0f1512] border-[#1a2420] hover:border-[#4a5550]',
          open && 'border-[#00d4aa]/50 ring-1 ring-[#00d4aa]/20',
        )}
      >
        {selected ? (
          <>
            <POSLogo system={selected.key as POSSystemKey} size="sm" />
            <span className="flex-1 text-sm text-white font-medium">{selected.name}</span>
            <POSStatusBadge status={selected.status} />
          </>
        ) : (
          <span className="flex-1 text-sm text-[#6b7a74]">Select POS system...</span>
        )}
        <ChevronDown size={16} className={clsx('text-[#6b7a74] transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute z-50 left-0 right-0 mt-1 bg-[#0f1512] border border-[#1a2420] rounded-lg shadow-xl overflow-hidden">
          <div className="p-2">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#6b7a74]" />
              <input
                autoFocus
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search POS systems..."
                className="w-full pl-8 pr-3 py-2 text-xs bg-[#0a0f0d] border border-[#1a2420] rounded-md text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50"
              />
            </div>
          </div>
          <div className="max-h-[320px] overflow-y-auto">
            {groups.map(g => g.items.length > 0 && (
              <div key={g.status}>
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0a0f0d]">
                  {g.icon}
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6b7a74]">{g.label}</span>
                </div>
                {g.items.map(sys => (
                  <button
                    key={sys.key}
                    type="button"
                    onClick={() => handleSelect(sys)}
                    className={clsx(
                      'w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors hover:bg-[#1a2420]/50',
                      value === sys.key && 'bg-[#00d4aa]/5',
                    )}
                  >
                    <POSLogo system={sys.key as POSSystemKey} size="sm" />
                    <span className="flex-1 text-xs text-white font-medium">{sys.name}</span>
                    <POSStatusBadge status={sys.status} />
                    {sys.status !== 'integrated' && (
                      <span className="text-[9px] text-[#4a5550] font-medium">(Demo)</span>
                    )}
                  </button>
                ))}
              </div>
            ))}
            {filtered.length === 0 && (
              <p className="text-xs text-[#4a5550] text-center py-4">No POS systems match your search.</p>
            )}
          </div>
        </div>
      )}

      {selected && <DetailCard system={selected} />}

      {selected && selected.status === 'integrated' && mode === 'lead-detail' && (
        <div className="mt-3">
          <label className="text-xs text-[#6b7a74] block mb-1.5">{selected.name} Access Token</label>
          <input
            type="text"
            value={accessToken}
            onChange={e => setAccessToken(e.target.value)}
            className="w-full px-3 py-2.5 bg-[#0f1512] border border-[#1a2420] rounded-lg text-sm text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50 focus:ring-1 focus:ring-[#00d4aa]/20 transition-colors"
            placeholder="Paste access token..."
          />
          <p className="text-[11px] text-[#4a5550] mt-1.5">
            Find this in your {selected.name} dashboard under Settings &gt; API
          </p>
        </div>
      )}
    </div>
  )

  function DetailCard({ system }: { system: POSSystem }) {
    const color = STATUS_COLORS[system.status] ?? '#6b7a74'

    return (
      <div className="mt-3 bg-[#0f1512] border border-[#1a2420] rounded-xl p-4 space-y-4">
        <div className="flex items-center gap-3">
          <POSLogo system={system.key as POSSystemKey} size="lg" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">{system.name}</span>
              <POSStatusBadge status={system.status} />
            </div>
            <a
              href={system.website}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-[#6b7a74] hover:text-[#00d4aa] transition-colors"
            >
              {system.website.replace(/^https?:\/\//, '')} <ExternalLink size={10} />
            </a>
          </div>
        </div>

        {system.status === 'integrated' && <IntegratedDetail system={system} color={color} />}
        {system.status === 'coming_soon' && <ComingSoonDetail system={system} />}
        {system.status === 'contingency' && <ContingencyDetail system={system} />}
      </div>
    )
  }

  function IntegratedDetail({ system, color }: { system: POSSystem; color: string }) {
    const { connectionRequirements: cr, dataAvailable } = system
    return (
      <>
        <div>
          <p className="text-xs font-semibold text-white mb-2">What Meridian needs from {system.name}:</p>
          <div className="space-y-1.5">
            {cr.requiredCredentials.map(c => (
              <div key={c} className="flex items-center gap-2">
                <Check size={12} className="text-[#00d4aa] flex-shrink-0" />
                <span className="text-[11px] text-[#6b7a74]">{c}</span>
              </div>
            ))}
          </div>
        </div>
        {cr.planRequired && (
          <p className="text-[11px] text-[#6b7a74]">
            <span className="text-white font-medium">Required Plan:</span> {cr.planRequired}
          </p>
        )}
        {cr.requiredPermissions.length > 0 && (
          <p className="text-[11px] text-[#6b7a74]">
            <span className="text-white font-medium">Required Permissions:</span>{' '}
            {cr.requiredPermissions.join(', ')}
          </p>
        )}
        <div>
          <p className="text-xs font-semibold text-white mb-2">Steps:</p>
          <ol className="space-y-1.5">
            {cr.stepByStepInstructions.map((s, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-[10px] font-bold text-[#00d4aa] mt-px w-4 flex-shrink-0">{i + 1}.</span>
                <span className="text-[11px] text-[#6b7a74]">{s}</span>
              </li>
            ))}
          </ol>
        </div>
        <DataPills data={dataAvailable} />
        <button
          type="button"
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg transition-all text-[#0a0f0d]"
          style={{ backgroundColor: '#00d4aa', borderColor: system.brandColor }}
        >
          <Wifi size={16} /> Connect {system.name} (Demo)
        </button>
      </>
    )
  }

  function ComingSoonDetail({ system }: { system: POSSystem }) {
    return (
      <>
        <p className="text-[11px] text-[#6b7a74] leading-relaxed">
          {system.integrationStatus.notes}
        </p>
        <button
          type="button"
          disabled
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg bg-[#1a2420] text-[#4a5550] cursor-not-allowed"
        >
          Coming Soon
        </button>
        {!waitlistSubmitted ? (
          <div className="flex gap-2">
            <input
              type="email"
              value={waitlistEmail}
              onChange={e => setWaitlistEmail(e.target.value)}
              placeholder="your@email.com"
              className="flex-1 px-3 py-2 text-xs bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50"
            />
            <button
              type="button"
              onClick={() => waitlistEmail.trim() && setWaitlistSubmitted(true)}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-amber-400/10 border border-amber-400/20 text-amber-400 rounded-lg hover:bg-amber-400/20 transition-colors"
            >
              <Bell size={12} /> Notify Me
            </button>
          </div>
        ) : (
          <p className="text-[11px] text-[#00d4aa] flex items-center gap-1.5">
            <CheckCircle2 size={12} /> We'll email you when {system.name} is live.
          </p>
        )}
      </>
    )
  }

  function ContingencyDetail({ system }: { system: POSSystem }) {
    const { contingencyPlan: cp, dataAvailable } = system
    return (
      <>
        <div>
          <p className="text-xs font-semibold text-white mb-1.5">CSV Export Instructions:</p>
          <p className="text-[11px] text-[#6b7a74] leading-relaxed">{cp.exportInstructions}</p>
        </div>
        <button
          type="button"
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg bg-[#7c3aed]/10 border border-[#7c3aed]/30 text-[#7c3aed] hover:bg-[#7c3aed]/20 transition-colors"
        >
          <Upload size={16} /> Upload CSV
        </button>
        <DataPills data={dataAvailable} />
        {cp.limitations.length > 0 && (
          <div>
            <p className="text-[11px] text-[#4a5550] font-medium mb-1">Limitations:</p>
            <ul className="space-y-0.5">
              {cp.limitations.map(l => (
                <li key={l} className="text-[10px] text-[#4a5550]">• {l}</li>
              ))}
            </ul>
          </div>
        )}
      </>
    )
  }
}

function DataPills({ data }: { data: POSSystem['dataAvailable'] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {DATA_KEYS.map(k => (
        <span
          key={k}
          className={clsx(
            'text-[10px] px-2 py-0.5 rounded-full border font-medium',
            data[k]
              ? 'text-[#00d4aa] bg-[#00d4aa]/10 border-[#00d4aa]/20'
              : 'text-[#4a5550] bg-[#1a2420] border-[#1a2420]',
          )}
        >
          {k === 'menuItems' ? 'menu items' : k === 'realTime' ? 'real-time' : k}
        </span>
      ))}
    </div>
  )
}
