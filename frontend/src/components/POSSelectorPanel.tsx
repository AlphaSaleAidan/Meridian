import { useState, useRef, useEffect } from 'react'
import { clsx } from 'clsx'
import {
  Search, ChevronDown, CheckCircle2, Upload, ExternalLink, Bell,
  AlertTriangle, Wifi,
} from 'lucide-react'
import POSLogo, { POSStatusBadge } from './POSLogo'
import PasswordInput from '@/components/ui/PasswordInput'
import { getAuthHeaders } from '@/lib/supabase'
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
  // P6: rep attribution. Forwarded to /api/pos/connect as
  // connected_by_rep_id when present. Settings page omits;
  // rep-facing surfaces should pass useSalesAuth().rep?.rep_id.
  repId?: string | null
}

export default function POSSelectorPanel({
  onSelect,
  onConnect,
  onUploadCSV,
  onWaitlist,
  defaultSelected,
  className,
  repId,
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
              <LayoutA system={selected} onConnect={onConnect} isDemo={isDemo} repId={repId} />
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

// P6: per-provider credential field map. MUST match what the backend
// test/connect handlers read in src/api/routes/pos_connections.py —
// wrong keys = silent rejection at the "all required fields" check
// (the same bug the wizard fix in P1 closed). For unknown providers
// we default to a single `access_token` input.
const POS_FIELDS: Record<string, { key: string; label: string; placeholder: string }[]> = {
  square: [{ key: 'access_token', label: 'Access Token', placeholder: 'EAAAl…' }],
  clover: [
    { key: 'access_token', label: 'Access Token', placeholder: 'Your Clover access token' },
    { key: 'merchant_id',  label: 'Merchant ID',   placeholder: 'XXXXXXXXXX' },
  ],
  toast: [
    { key: 'client_id',       label: 'Client ID',       placeholder: 'Toast partner client_id' },
    { key: 'client_secret',   label: 'Client Secret',   placeholder: 'Toast partner client_secret' },
    { key: 'restaurant_guid', label: 'Restaurant GUID', placeholder: 'xxxxxxxx-xxxx-…' },
  ],
}

// Providers with server-side 1-click OAuth. For these we must NOT collect a
// pasted access token — that path 401s on a bad/stale token and silently leaves
// a "connected, no data" connection. Instead redirect to the authorize endpoint,
// which signs the merchant into the provider and mints a valid token via the
// callback. (Manual token entry stays for non-OAuth POS like Toast.)
const OAUTH_AUTHORIZE: Record<string, string> = {
  square: '/api/square/authorize',
  clover: '/api/clover/authorize',
  // Generic 1-click framework providers live under /api/pos/{key}/…
  stripe: '/api/pos/stripe/authorize',
}

// Post-OAuth status polling. Square/Clover have dedicated /api/{key}/status
// routes; framework providers use the generic /api/pos/{key}/status.
const OAUTH_STATUS: Record<string, string> = {
  stripe: '/api/pos/stripe/status',
}

function LayoutA({ system, onConnect, isDemo, repId }: {
  system: POSSystem; onConnect?: (s: POSSystem) => void; isDemo: boolean;
  repId?: string | null;
}) {
  const fields = POS_FIELDS[system.key] || [{ key: 'access_token', label: 'API Access Token', placeholder: `Paste your ${system.name} access token…` }]
  // P6: per-field credentials object (was a single `apiKey` string —
  // Clover + Toast were silently broken on this surface).
  const [creds, setCreds] = useState<Record<string, string>>({})
  const [testing, setTesting] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [testResult, setTestResult] = useState<{ valid: boolean; merchant?: string; error?: string } | null>(null)
  const [connectError, setConnectError] = useState('')
  const [connected, setConnected] = useState(false)
  // True while the merchant is approving in the OAuth tab we opened — the
  // original tab polls /status until the connection lands.
  const [waitingOAuth, setWaitingOAuth] = useState(false)
  const orgId = useOrgId()
  const apiBase = import.meta.env.VITE_API_URL || ''
  const oauthPath = OAUTH_AUTHORIZE[system.key]

  function startOAuth() {
    // Demo pages simulate a connection via onConnect. Real contexts never fake it.
    if (isDemo) { onConnect?.(system); return }
    if (!orgId || orgId === 'demo') {
      setConnectError('Your account is still loading — refresh the page and try again.')
      return
    }
    setConnectError('')
    const ret = encodeURIComponent(window.location.pathname + window.location.search)
    const rep = repId ? `&rep_id=${encodeURIComponent(repId)}` : ''
    // Open the provider sign-in in a NEW tab so this page keeps its session and
    // can watch the connection land via polling.
    window.open(
      `${apiBase}${oauthPath}?org_id=${encodeURIComponent(orgId)}&return_to=${ret}${rep}`,
      '_blank',
      'noopener',
    )
    setWaitingOAuth(true)
  }

  // Poll this provider's /status while the OAuth tab is open.
  useEffect(() => {
    if (!waitingOAuth || !orgId || orgId === 'demo') return
    let active = true
    const tick = async () => {
      try {
        const statusPath = OAUTH_STATUS[system.key] || `/api/${system.key}/status`
        // /status returns this org's connection state, so carry the merchant's
        // Supabase JWT — it was being polled anonymously (prep for the guard).
        const headers = await getAuthHeaders()
        const res = await fetch(`${apiBase}${statusPath}?org_id=${encodeURIComponent(orgId)}`, { headers })
        if (!res.ok) return
        const st = await res.json()
        if (active && st?.connected) {
          setWaitingOAuth(false)
          setConnected(true)
          onConnect?.(system)
        }
      } catch { /* transient — keep polling */ }
    }
    tick()
    const id = setInterval(tick, 4000)
    return () => { active = false; clearInterval(id) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [waitingOAuth, orgId, system.key])

  const allFilled = fields.every(f => (creds[f.key] || '').trim().length > 0)

  function buildCredentials(): Record<string, string> {
    const out: Record<string, string> = {}
    for (const f of fields) {
      const v = (creds[f.key] || '').trim()
      if (v) out[f.key] = v
    }
    return out
  }

  async function handleTest() {
    if (!allFilled) return
    setTesting(true)
    setTestResult(null)
    setConnectError('')
    try {
      const res = await fetch(`${apiBase}/api/pos/test-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pos_system: system.key, credentials: buildCredentials() }),
      })
      const data = await res.json()
      const ok = res.ok && data?.success !== false && data?.valid !== false
      setTestResult({
        valid: ok,
        merchant: data?.details?.business_name || data?.merchant_name,
        error: data?.message || data?.detail || data?.error,
      })
    } catch {
      setTestResult({ valid: false, error: 'Could not reach the server' })
    } finally {
      setTesting(false)
    }
  }

  async function handleConnect() {
    // Demo pages simulate; real contexts must never report a connection that
    // didn't reach the backend.
    if (isDemo) { onConnect?.(system); return }
    if (!allFilled) return
    if (!orgId || orgId === 'demo') {
      setConnectError('Your account is still loading — refresh the page and try again.')
      return
    }
    setConnecting(true)
    setConnectError('')
    try {
      const credsToSend = buildCredentials()
      const res = await fetch(`${apiBase}/api/pos/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: orgId,
          pos_system: system.key,
          credentials: credsToSend,
          // P6: Toast's restaurant_guid surfaces as a top-level
          // ConnectRequest field on the backend so it persists to
          // pos_connections.external_merchant_id.
          restaurant_guid: credsToSend.restaurant_guid,
          // P6: rep attribution forwarded when the surface has rep
          // context (Canada portal). Settings page leaves it null.
          connected_by_rep_id: repId || null,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setConnectError(data.detail || data.message || 'Failed to connect')
        return
      }
      setConnected(true)
      onConnect?.(system)
    } catch {
      setConnectError('Could not reach the server')
    } finally {
      setConnecting(false)
    }
  }

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

      {/* OAuth providers (Square, Clover): 1-click sign-in — no token to paste. */}
      {oauthPath && !isDemo && !connected && (
        <div className="space-y-2">
          {connectError && (
            <div className="flex items-center gap-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-[11px] text-red-400">
              <AlertTriangle size={12} /> {connectError}
            </div>
          )}
          {waitingOAuth ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 p-3 rounded-lg bg-[#1A8FD6]/10 border border-[#1A8FD6]/20">
                <Wifi size={14} className="text-[#1A8FD6] animate-pulse" />
                <span className="text-[12px] text-[#1A8FD6]">
                  Waiting for you to approve in the other tab…
                </span>
              </div>
              <button
                onClick={() => setWaitingOAuth(false)}
                className="w-full px-3 py-2 text-[11px] text-[#A1A1A8] hover:text-[#F5F5F7] border border-[#1F1F23] rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={startOAuth}
                className="w-full flex items-center justify-center gap-2 px-3 py-2.5 text-[12px] font-medium text-white rounded-lg transition-all"
                style={{ backgroundColor: system.brandColor }}
              >
                <Wifi size={12} /> Connect with {system.name}
              </button>
              <p className="text-[9px] text-[#A1A1A8]/40 text-center">
                You'll sign in to {system.name} securely in a new tab — no keys to copy or paste.
              </p>
            </>
          )}
        </div>
      )}

      {/* P6: per-provider credential inputs for non-OAuth POS (e.g. Toast).
          Square = 1 field; Clover = 2; Toast = 3. Unknown providers default
          to single access_token. */}
      {!oauthPath && !isDemo && !connected && (
        <div className="space-y-2">
          {fields.map(f => (
            <div key={f.key} className="space-y-1">
              <label className="text-[11px] font-medium text-[#A1A1A8]">{f.label}</label>
              <PasswordInput
                value={creds[f.key] || ''}
                onChange={e => {
                  setCreds(prev => ({ ...prev, [f.key]: e.target.value }))
                  setTestResult(null)
                  setConnectError('')
                }}
                placeholder={f.placeholder}
                className="w-full px-3 py-2.5 text-[12px] font-mono bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40"
              />
            </div>
          ))}
          {testResult && (
            <div className={clsx(
              'flex items-center gap-2 p-2 rounded-lg text-[11px]',
              testResult.valid ? 'bg-[#17C5B0]/10 border border-[#17C5B0]/20 text-[#17C5B0]' : 'bg-red-500/10 border border-red-500/20 text-red-400'
            )}>
              {testResult.valid ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
              {testResult.valid ? `Connected! Merchant: ${testResult.merchant || 'Verified'}` : (testResult.error || 'Invalid credentials')}
            </div>
          )}
          {connectError && (
            <div className="flex items-center gap-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-[11px] text-red-400">
              <AlertTriangle size={12} /> {connectError}
            </div>
          )}
          <div className="flex gap-2">
            <button
              onClick={handleTest}
              disabled={testing || !allFilled}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-[12px] font-medium border border-[#1F1F23] rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#A1A1A8]/30 disabled:opacity-40 transition-all"
            >
              {testing ? <><Wifi size={12} className="animate-pulse" /> Testing...</> : <><Wifi size={12} /> Test Connection</>}
            </button>
            <button
              onClick={handleConnect}
              disabled={connecting || !allFilled}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-[12px] font-medium text-white rounded-lg disabled:opacity-40 transition-all"
              style={{ backgroundColor: system.brandColor }}
            >
              {connecting ? <><Wifi size={12} className="animate-pulse" /> Connecting...</> : <><Wifi size={12} /> Connect &amp; Encrypt</>}
            </button>
          </div>
          <p className="text-[9px] text-[#A1A1A8]/40 text-center">
            Your key is encrypted with AES-256-GCM before storage. Meridian never stores plaintext credentials.
          </p>
        </div>
      )}

      {connected && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20">
          <CheckCircle2 size={14} className="text-[#17C5B0]" />
          <span className="text-[12px] text-[#17C5B0] font-medium">POS connected! Data sync is starting...</span>
        </div>
      )}

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

      {isDemo && (
        <button
          onClick={() => onConnect?.(system)}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 text-[13px] font-medium text-white rounded-lg transition-all"
          style={{ backgroundColor: system.brandColor }}
        >
          <Wifi size={14} />
          Connect {system.name} (Demo)
        </button>
      )}
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
