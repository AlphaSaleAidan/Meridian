import { useState, useRef, useEffect } from 'react'
import { clsx } from 'clsx'
import {
  Search, ChevronDown, CheckCircle2, Upload, ExternalLink, Bell,
  AlertTriangle, Wifi,
} from 'lucide-react'
import POSLogo, { POSStatusBadge } from './POSLogo'
import { posSystems, type POSSystem, type POSSystemKey } from '@/data/pos-systems'
import { useIsDemo, useOrgId } from '@/hooks/useOrg'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface POSSelectorPanelProps {
  onSelect?: (system: POSSystem) => void
  onConnect?: (system: POSSystem) => void
  onUploadCSV?: (system: POSSystem) => void
  onWaitlist?: (system: POSSystem, email: string) => void
  defaultSelected?: string
  className?: string
}

export default function POSSelectorPanel({
  onSelect,
  onConnect,
  onUploadCSV,
  onWaitlist,
  defaultSelected,
  className,
}: POSSelectorPanelProps) {
  const isDemo = useIsDemo()
  const orgId = useOrgId()
  const [selected, setSelected] = useState<POSSystem | null>(
    defaultSelected ? posSystems.find(s => s.key === defaultSelected) || null : null
  )
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [waitlistEmail, setWaitlistEmail] = useState('')
  const [waitlistSubmitted, setWaitlistSubmitted] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isDemo && !selected) {
      setSelected(posSystems.find(s => s.key === 'square') || null)
    }
  }, [isDemo, selected])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filtered = search.trim()
    ? posSystems.filter(s => s.name.toLowerCase().includes(search.toLowerCase()))
    : posSystems

  const groups = [
    { label: 'Currently Supported', icon: '✓', items: filtered.filter(s => s.status === 'integrated') },
    { label: 'Coming Soon', icon: '⏳', items: filtered.filter(s => s.status === 'coming_soon') },
    { label: 'Available via Manual Import', icon: '📋', items: filtered.filter(s => s.status === 'contingency') },
    { label: 'Contact Us to Get Started', icon: '📞', items: filtered.filter(s => s.status === 'unsupported') },
  ]

  function handleSelect(system: POSSystem) {
    setSelected(system)
    setDropdownOpen(false)
    setSearch('')
    setWaitlistSubmitted(false)
    setWaitlistEmail('')
    onSelect?.(system)

    if (orgId && orgId !== 'demo') {
      const status = system.status === 'integrated' ? 'connected'
        : system.status === 'contingency' ? 'manual'
        : 'pending'
      fetch(`${API_BASE}/api/pos/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org_id: orgId, pos_system: system.key, connection_status: status }),
      }).catch(() => {})
    }
  }

  function handleWaitlistSubmit() {
    if (!waitlistEmail.trim() || !selected) return
    setWaitlistSubmitted(true)
    onWaitlist?.(selected, waitlistEmail)

    fetch(`${API_BASE}/api/pos/waitlist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: waitlistEmail,
        pos_system: selected.key,
        org_id: orgId !== 'demo' ? orgId : undefined,
      }),
    }).catch(() => {})
  }

  return (
    <div className={clsx('space-y-4', className)}>
      {/* Dropdown Selector */}
      <div ref={dropdownRef} className="relative">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-[#1F1F23] bg-[#0F0F12] hover:border-[#2A2A2E] transition-colors text-left"
        >
          {selected ? (
            <>
              <POSLogo system={selected.key as POSSystemKey} size="md" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[#F5F5F7]">{selected.name}</p>
                <POSStatusBadge status={selected.status} />
              </div>
            </>
          ) : (
            <div className="flex-1">
              <p className="text-sm text-[#A1A1A8]/60">Select your POS system...</p>
            </div>
          )}
          <ChevronDown size={16} className={clsx('text-[#A1A1A8] transition-transform', dropdownOpen && 'rotate-180')} />
        </button>

        {/* Dropdown List */}
        {dropdownOpen && (
          <div className="absolute z-50 top-full mt-2 left-0 right-0 rounded-xl border border-[#1F1F23] bg-[#0A0A0B] shadow-2xl overflow-hidden">
            {/* Search */}
            <div className="p-3 border-b border-[#1F1F23]">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
                <input
                  type="text"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search POS systems..."
                  className="w-full pl-8 pr-3 py-2 text-[13px] rounded-lg bg-[#1F1F23] border border-[#2A2A2E] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40"
                  autoFocus
                />
              </div>
            </div>

            {/* Grouped Items */}
            <div className="max-h-[320px] overflow-y-auto">
              {groups.map(group => group.items.length > 0 && (
                <div key={group.label}>
                  <div className="px-3 py-2 bg-[#0F0F12] border-y border-[#1F1F23]/50">
                    <span className="text-[10px] font-medium text-[#A1A1A8]/50 uppercase tracking-wider">
                      {group.icon} {group.label}
                    </span>
                  </div>
                  {group.items.map(system => (
                    <button
                      key={system.key}
                      onClick={() => handleSelect(system)}
                      className={clsx(
                        'w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[#1F1F23]/50 transition-colors text-left',
                        selected?.key === system.key && 'bg-[#1A8FD6]/5',
                      )}
                    >
                      <POSLogo system={system.key as POSSystemKey} size="sm" />
                      <span className="text-[13px] text-[#F5F5F7] flex-1">{system.name}</span>
                      <POSStatusBadge status={system.status} />
                      {isDemo && system.status !== 'integrated' && (
                        <span className="text-[9px] text-[#A1A1A8]/30">(Demo)</span>
                      )}
                    </button>
                  ))}
                </div>
              ))}
              {filtered.length === 0 && (
                <div className="px-4 py-8 text-center">
                  <p className="text-[13px] text-[#A1A1A8]/50">No POS systems match "{search}"</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Connection Panel */}
      {selected && (
        <div className="rounded-xl border border-[#1F1F23] bg-[#0F0F12] overflow-hidden">
          {/* Panel Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[#1F1F23]">
            <POSLogo system={selected.key as POSSystemKey} size="lg" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-[#F5F5F7]">{selected.name}</h3>
              <p className="text-[11px] text-[#A1A1A8]/50">{selected.website}</p>
            </div>
            <POSStatusBadge status={selected.status} />
          </div>

          {/* Dynamic Content Based on Status */}
          <div className="p-4 space-y-4">
            {selected.status === 'integrated' && (
              <LayoutA system={selected} onConnect={onConnect} isDemo={isDemo} />
            )}
            {selected.status === 'coming_soon' && (
              <LayoutC
                system={selected}
                waitlistEmail={waitlistEmail}
                setWaitlistEmail={setWaitlistEmail}
                waitlistSubmitted={waitlistSubmitted}
                onSubmit={handleWaitlistSubmit}
              />
            )}
            {selected.status === 'contingency' && (
              <LayoutB
                system={selected}
                onUploadCSV={onUploadCSV}
                waitlistEmail={waitlistEmail}
                setWaitlistEmail={setWaitlistEmail}
                waitlistSubmitted={waitlistSubmitted}
                onWaitlistSubmit={handleWaitlistSubmit}
              />
            )}
            {selected.status === 'unsupported' && (
              <LayoutC
                system={selected}
                waitlistEmail={waitlistEmail}
                setWaitlistEmail={setWaitlistEmail}
                waitlistSubmitted={waitlistSubmitted}
                onSubmit={handleWaitlistSubmit}
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function LayoutA({ system, onConnect, isDemo }: { system: POSSystem; onConnect?: (s: POSSystem) => void; isDemo: boolean }) {
  return (
    <>
      <div>
        <p className="text-[12px] font-medium text-[#A1A1A8] mb-2">What Meridian needs from {system.name}:</p>
        <div className="space-y-1.5">
          {system.connectionRequirements.requiredCredentials.map(cred => (
            <div key={cred} className="flex items-center gap-2 text-[12px]">
              <CheckCircle2 size={12} className="text-[#17C5B0] flex-shrink-0" />
              <span className="text-[#F5F5F7]">{cred}</span>
            </div>
          ))}
        </div>
      </div>

      {system.connectionRequirements.planRequired && (
        <div className="text-[11px] text-[#A1A1A8]">
          <span className="text-[#A1A1A8]/50">Required Plan:</span>{' '}
          <span className="text-[#F5F5F7]">{system.connectionRequirements.planRequired}</span>
        </div>
      )}

      <div className="text-[11px] text-[#A1A1A8]">
        <span className="text-[#A1A1A8]/50">Required Permissions:</span>{' '}
        <span className="text-[#F5F5F7]">{system.connectionRequirements.requiredPermissions.join(', ')}</span>
      </div>

      <div>
        <p className="text-[11px] font-medium text-[#A1A1A8]/50 mb-2">Step-by-step:</p>
        <ol className="space-y-1">
          {system.connectionRequirements.stepByStepInstructions.map((step, i) => (
            <li key={i} className="flex gap-2 text-[12px] text-[#A1A1A8]">
              <span className="text-[#1A8FD6] font-mono font-bold flex-shrink-0">{i + 1}.</span>
              {step}
            </li>
          ))}
        </ol>
      </div>

      {/* Data Available */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(system.dataAvailable).map(([key, val]) => {
          if (key === 'historicalDays') return null
          return (
            <span key={key} className={clsx(
              'text-[10px] px-2 py-0.5 rounded-full border',
              val ? 'text-[#17C5B0] bg-[#17C5B0]/10 border-[#17C5B0]/20' : 'text-[#A1A1A8]/30 bg-[#1F1F23] border-[#1F1F23]',
            )}>
              {val ? '✓' : '✗'} {key.replace(/([A-Z])/g, ' $1').trim()}
            </span>
          )
        })}
      </div>

      <button
        onClick={() => onConnect?.(system)}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-white rounded-lg transition-all"
        style={{ backgroundColor: system.brandColor }}
      >
        <Wifi size={14} />
        {isDemo ? `Connect ${system.name} (Demo)` : `Connect ${system.name}`}
      </button>
    </>
  )
}

function LayoutB({
  system, onUploadCSV, waitlistEmail, setWaitlistEmail, waitlistSubmitted, onWaitlistSubmit,
}: {
  system: POSSystem
  onUploadCSV?: (s: POSSystem) => void
  waitlistEmail: string
  setWaitlistEmail: (v: string) => void
  waitlistSubmitted: boolean
  onWaitlistSubmit: () => void
}) {
  return (
    <>
      <p className="text-[12px] text-[#A1A1A8] leading-relaxed">
        Meridian doesn't have a direct <span className="text-[#F5F5F7] font-medium">{system.name}</span> integration yet,
        but you can still get your data flowing today.
      </p>

      {/* Option 1: CSV Export */}
      <div className="rounded-lg p-3 bg-[#0A0A0B] border border-[#1F1F23]">
        <p className="text-[11px] font-semibold text-[#F5F5F7] mb-2">Option 1 — CSV Export (Recommended)</p>
        <p className="text-[11px] text-[#A1A1A8] leading-relaxed mb-2">
          {system.contingencyPlan.exportInstructions}
        </p>
        <p className="text-[10px] text-[#A1A1A8]/50">
          Estimated setup time: <span className="text-[#F5F5F7]">{system.contingencyPlan.estimatedSetupTime}</span>
          {' '}• Format: <span className="text-[#F5F5F7]">{system.contingencyPlan.dataExportFormat}</span>
        </p>
      </div>

      {/* Option 2: Third-party bridge */}
      {system.contingencyPlan.thirdPartyBridge && (
        <div className="rounded-lg p-3 bg-[#0A0A0B] border border-[#1F1F23]">
          <p className="text-[11px] font-semibold text-[#F5F5F7] mb-1">
            Option 2 — {system.contingencyPlan.thirdPartyBridge}
          </p>
          <p className="text-[11px] text-[#A1A1A8]">
            Connect via {system.contingencyPlan.thirdPartyBridge} for automated data sync
          </p>
        </div>
      )}

      {/* Data Available */}
      <div>
        <p className="text-[10px] text-[#A1A1A8]/50 mb-1.5">What you'll be able to see:</p>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(system.dataAvailable).map(([key, val]) => {
            if (key === 'historicalDays') return null
            return (
              <span key={key} className={clsx(
                'text-[10px] px-1.5 py-0.5 rounded',
                val ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/30',
              )}>
                {val ? '✓' : '✗'} {key.replace(/([A-Z])/g, ' $1').trim()}
              </span>
            )
          })}
        </div>
      </div>

      {/* Limitations */}
      {system.contingencyPlan.limitations.length > 0 && (
        <div className="rounded-lg p-3 bg-amber-500/5 border border-amber-500/10">
          <div className="flex items-center gap-1.5 mb-1.5">
            <AlertTriangle size={11} className="text-amber-400" />
            <span className="text-[10px] font-medium text-amber-400">Limitations</span>
          </div>
          <ul className="space-y-0.5">
            {system.contingencyPlan.limitations.map((lim, i) => (
              <li key={i} className="text-[11px] text-[#A1A1A8]">• {lim}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-2">
        <button
          onClick={() => onUploadCSV?.(system)}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-[12px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors"
        >
          <Upload size={14} /> Upload CSV Now
        </button>
        {system.contingencyPlan.thirdPartyBridge && (
          <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-[12px] font-medium text-[#F5F5F7] border border-[#1F1F23] rounded-lg hover:border-[#2A2A2E] transition-colors">
            <ExternalLink size={14} /> Set Up {system.contingencyPlan.thirdPartyBridge}
          </button>
        )}
      </div>

      {/* Waitlist */}
      <WaitlistCapture
        system={system}
        email={waitlistEmail}
        setEmail={setWaitlistEmail}
        submitted={waitlistSubmitted}
        onSubmit={onWaitlistSubmit}
      />
    </>
  )
}

function LayoutC({
  system, waitlistEmail, setWaitlistEmail, waitlistSubmitted, onSubmit,
}: {
  system: POSSystem
  waitlistEmail: string
  setWaitlistEmail: (v: string) => void
  waitlistSubmitted: boolean
  onSubmit: () => void
}) {
  const effortToTimeline: Record<string, string> = {
    low: '2-4 weeks',
    medium: '1-2 months',
    high: '2-4 months',
  }

  return (
    <>
      <p className="text-[12px] text-[#A1A1A8] leading-relaxed">
        We're working on native <span className="text-[#F5F5F7] font-medium">{system.name}</span> integration.
        In the meantime, our team can help you set up a custom data connection.
      </p>

      {system.connectionRequirements.requiredCredentials.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-[#A1A1A8]/50 mb-1.5">What we'll need from you:</p>
          <ul className="space-y-1">
            {system.connectionRequirements.requiredCredentials.map(cred => (
              <li key={cred} className="text-[12px] text-[#A1A1A8] flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-[#A1A1A8]/30 flex-shrink-0" />
                {cred}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Manual export option */}
      {system.contingencyPlan.manualUploadSupported && (
        <div className="rounded-lg p-3 bg-[#0A0A0B] border border-[#1F1F23]">
          <p className="text-[11px] font-semibold text-[#F5F5F7] mb-1">Manual Data Import Available</p>
          <p className="text-[11px] text-[#A1A1A8] leading-relaxed">
            {system.contingencyPlan.exportInstructions}
          </p>
        </div>
      )}

      <div className="text-[11px] text-[#A1A1A8]">
        Estimated availability:{' '}
        <span className="text-[#F5F5F7] font-medium">
          {effortToTimeline[system.integrationStatus.estimatedIntegrationEffort] || 'TBD'}
        </span>
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-2">
        <a
          href="mailto:support@meridian.tips?subject=POS%20Integration%20Request"
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-[12px] font-medium text-white bg-[#7C5CFF] rounded-lg hover:bg-[#6B4FE0] transition-colors"
        >
          <ExternalLink size={14} /> Contact Our Team
        </a>
      </div>

      {/* Waitlist */}
      <WaitlistCapture
        system={system}
        email={waitlistEmail}
        setEmail={setWaitlistEmail}
        submitted={waitlistSubmitted}
        onSubmit={onSubmit}
      />
    </>
  )
}

function WaitlistCapture({
  system, email, setEmail, submitted, onSubmit,
}: {
  system: POSSystem
  email: string
  setEmail: (v: string) => void
  submitted: boolean
  onSubmit: () => void
}) {
  if (submitted) {
    return (
      <div className="flex items-center gap-2 text-[12px] text-[#17C5B0] py-2">
        <CheckCircle2 size={14} />
        We'll notify you when native {system.name} integration is ready!
      </div>
    )
  }

  return (
    <div className="border-t border-[#1F1F23] pt-3">
      <p className="text-[10px] text-[#A1A1A8]/50 mb-2">
        We're building native {system.name} integration
      </p>
      <div className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="your@email.com"
          className="flex-1 px-3 py-2 text-[12px] rounded-lg bg-[#0A0A0B] border border-[#1F1F23] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#17C5B0]/40"
        />
        <button
          onClick={onSubmit}
          disabled={!email.trim()}
          className="flex items-center gap-1.5 px-3 py-2 text-[11px] font-medium text-[#17C5B0] border border-[#17C5B0]/20 rounded-lg hover:bg-[#17C5B0]/10 disabled:opacity-40 transition-colors"
        >
          <Bell size={12} /> Notify Me
        </button>
      </div>
    </div>
  )
}
