import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Wifi, WifiOff, RefreshCw, CheckCircle2, AlertCircle, Clock, ExternalLink, SlidersHorizontal, Building2, Check, CreditCard } from 'lucide-react'
import { clsx } from 'clsx'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatDateTime, formatRelative, formatCents } from '@/lib/format'
import { LoadingPage, ErrorState } from '@/components/LoadingState'
import { generateBusinessProfiles } from '@/lib/agent-data'
import ScrollReveal from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import POSSelectorPanel from '@/components/POSSelectorPanel'
import POSLogo from '@/components/POSLogo'
import { posSystemsByKey, type POSSystemKey } from '@/data/pos-systems'
import { useOrgId } from '@/hooks/useOrg'

const API_URL = import.meta.env.VITE_API_URL || ''

const statusIcons: Record<string, typeof Wifi> = {
  connected: CheckCircle2,
  syncing: RefreshCw,
  error: AlertCircle,
  pending: Clock,
  disconnected: WifiOff,
}

const statusColors: Record<string, string> = {
  connected: 'text-[#17C5B0]',
  syncing: 'text-amber-400',
  error: 'text-red-400',
  pending: 'text-[#A1A1A8]',
  disconnected: 'text-[#A1A1A8]/50',
}

function BusinessTuningPanel() {
  const profiles = generateBusinessProfiles()
  const [selected, setSelected] = useState<string>('coffee_shop')
  const profile = profiles.find(p => p.type === selected)!

  return (
    <div className="card overflow-hidden">
      <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex items-center gap-2">
        <SlidersHorizontal size={14} className="text-[#7C5CFF]" />
        <div>
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Business Type Tuning</h3>
          <p className="text-[10px] text-[#A1A1A8] mt-0.5">Agent thresholds adapt to your business category</p>
        </div>
      </div>
      <div className="p-4 sm:p-5 space-y-4">
        <div className="flex flex-wrap gap-2">
          {profiles.map(p => (
            <button
              key={p.type}
              onClick={() => setSelected(p.type)}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all',
                selected === p.type
                  ? 'bg-[#7C5CFF]/10 text-[#7C5CFF] border-[#7C5CFF]/20'
                  : 'text-[#A1A1A8] border-[#1F1F23] hover:text-[#F5F5F7] hover:border-[#A1A1A8]/20'
              )}
            >
              {selected === p.type && <Check size={12} />}
              <Building2 size={12} />
              {p.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <DashboardTiltCard className="card p-4 space-y-3">
            <h4 className="text-xs font-semibold text-[#F5F5F7]">Industry Benchmarks</h4>
            <div className="space-y-2 text-xs">
              {([
                ['Avg Ticket', formatCents(profile.benchmarks.avgTicketCents)],
                ['Target Margin', `${profile.benchmarks.marginPct}%`],
                ['Peak Hours', profile.benchmarks.peakHours],
                ['Top Category', profile.benchmarks.topCategory],
                ['Typical Waste', `${profile.benchmarks.wastePct}%`],
                ['Staffing Ratio', profile.benchmarks.staffingRatio],
              ] as const).map(([label, value]) => (
                <div key={label} className="flex items-center justify-between py-1 border-b border-[#1F1F23]/50 last:border-0">
                  <span className="text-[#A1A1A8]/60">{label}</span>
                  <span className="font-mono text-[#F5F5F7]">{value}</span>
                </div>
              ))}
            </div>
          </DashboardTiltCard>

          <DashboardTiltCard className="card p-4 space-y-3">
            <h4 className="text-xs font-semibold text-[#F5F5F7]">Agent Alert Thresholds</h4>
            <div className="space-y-2 text-xs">
              {([
                ['Void Alert', `>${profile.agentThresholds.voidAlertPct}%`, profile.agentThresholds.voidAlertPct > 1.5 ? 'text-amber-400' : 'text-[#17C5B0]'],
                ['Refund Alert', `>${profile.agentThresholds.refundAlertPct}%`, profile.agentThresholds.refundAlertPct > 3 ? 'text-amber-400' : 'text-[#17C5B0]'],
                ['Revenue Drop Alert', `>${profile.agentThresholds.revenueDropAlertPct}%`, 'text-red-400'],
                ['Low Margin Flag', `<${profile.agentThresholds.lowMarginPct}%`, 'text-amber-400'],
                ['High Margin Target', `>${profile.agentThresholds.highMarginPct}%`, 'text-[#17C5B0]'],
                ['Peak Staffing Min', `${profile.agentThresholds.peakStaffingMin} staff`, 'text-[#1A8FD6]'],
              ] as const).map(([label, value, color]) => (
                <div key={label} className="flex items-center justify-between py-1 border-b border-[#1F1F23]/50 last:border-0">
                  <span className="text-[#A1A1A8]/60">{label}</span>
                  <span className={clsx('font-mono font-semibold', color)}>{value}</span>
                </div>
              ))}
            </div>
          </DashboardTiltCard>
        </div>
      </div>
    </div>
  )
}

function BillingCard({ orgId, apiUrl }: { orgId: string; apiUrl: string }) {
  const [billing, setBilling] = useState<{
    status: string; tier: string | null; monthly_price_cents?: number;
    current_period_end?: string; auto_renew?: boolean;
    card_brand?: string; card_last4?: string; billing_method?: string
  } | null>(null)
  const [invoiceUrl, setInvoiceUrl] = useState<string | null>(null)
  const [billingError, setBillingError] = useState<string | null>(null)

  useEffect(() => {
    if (!orgId) return
    setBillingError(null)
    fetch(`${apiUrl}/api/billing/status/${orgId}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setBilling(d))
      .catch(() => { setBillingError('Could not load billing info') })
    fetch(`${apiUrl}/api/billing/invoice-url/${orgId}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setInvoiceUrl(d.invoice_url))
      .catch(() => { setBillingError('Could not load billing info') })
  }, [orgId, apiUrl])

  const statusLabel = billing?.status === 'active' ? 'Active' :
    billing?.status === 'pending_payment' ? 'Pending Payment' :
    billing?.status === 'past_due' ? 'Past Due' :
    billing?.status === 'trialing' ? 'Trial' : 'No Plan'

  const statusColor = billing?.status === 'active' ? 'text-[#17C5B0]' :
    billing?.status === 'past_due' ? 'text-red-400' :
    billing?.status === 'pending_payment' ? 'text-amber-400' : 'text-[#A1A1A8]'

  return (
    <div className="card overflow-hidden">
      <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CreditCard size={14} className="text-[#7C5CFF]" />
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Billing & Subscription</h3>
        </div>
        {invoiceUrl && (
          <a
            href={invoiceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 text-xs font-medium text-white bg-[#7C5CFF] rounded-lg hover:bg-[#6B4FE0] transition-all inline-flex items-center gap-2"
          >
            <ExternalLink size={12} />
            Pay Invoice
          </a>
        )}
      </div>
      <div className="p-4 sm:p-5 space-y-2 text-xs">
        {billingError && (
          <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{billingError}</div>
        )}
        <div className="flex items-center justify-between py-1.5 border-b border-[#1F1F23]/50">
          <span className="text-[#A1A1A8]/60">Status</span>
          <span className={clsx('font-semibold', statusColor)}>{statusLabel}</span>
        </div>
        {billing?.tier && (
          <div className="flex items-center justify-between py-1.5 border-b border-[#1F1F23]/50">
            <span className="text-[#A1A1A8]/60">Plan</span>
            <span className="text-[#F5F5F7] font-medium">{billing.tier.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
          </div>
        )}
        {billing?.monthly_price_cents != null && billing.monthly_price_cents > 0 && (
          <div className="flex items-center justify-between py-1.5 border-b border-[#1F1F23]/50">
            <span className="text-[#A1A1A8]/60">Monthly</span>
            <span className="text-[#F5F5F7] font-mono">{formatCents(billing.monthly_price_cents)}</span>
          </div>
        )}
        {billing?.current_period_end && (
          <div className="flex items-center justify-between py-1.5 border-b border-[#1F1F23]/50">
            <span className="text-[#A1A1A8]/60">Next Renewal</span>
            <span className="text-[#A1A1A8]">{new Date(billing.current_period_end).toLocaleDateString()}</span>
          </div>
        )}
        {billing?.card_brand && billing?.card_last4 && (
          <div className="flex items-center justify-between py-1.5 border-b border-[#1F1F23]/50">
            <span className="text-[#A1A1A8]/60">Card on File</span>
            <span className="text-[#F5F5F7] font-mono">{billing.card_brand} ****{billing.card_last4}</span>
          </div>
        )}
        {billing?.billing_method && (
          <div className="flex items-center justify-between py-1.5 border-b border-[#1F1F23]/50">
            <span className="text-[#A1A1A8]/60">Billing</span>
            <span className={clsx('text-xs font-medium',
              billing.billing_method === 'auto_subscription' ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'
            )}>
              {billing.billing_method === 'auto_subscription' ? 'Auto-Recurring' : 'Invoice'}
            </span>
          </div>
        )}
        <div className="flex items-center justify-between py-1.5">
          <span className="text-[#A1A1A8]/60">Auto-Renew</span>
          <span className={billing?.auto_renew !== false ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'}>
            {billing?.auto_renew !== false ? 'On' : 'Off'}
          </span>
        </div>
      </div>
    </div>
  )
}

export default function SettingsPage() {
  const location = useLocation()
  const basePath = location.pathname.startsWith('/app') ? '/app'
    : location.pathname.startsWith('/canada/demo') ? '/canada/demo'
    : '/demo'
  const orgId = useOrgId()
  const conn = useApi(() => api.connection(orgId), [orgId])

  if (conn.loading) return <LoadingPage />
  if (conn.error) return <ErrorState message={conn.error} onRetry={conn.refetch} />

  const connections = conn.data!.connections

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Settings</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">POS connections and account configuration</p>
        </div>
      </ScrollReveal>

      {/* POS Connections */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">POS Connections</h3>
{connections.length === 0 && (
            <a
              href={basePath === '/demo' ? '#' : `${API_URL}/api/square/authorize?org_id=${orgId}`}
              onClick={basePath === '/demo' ? (e: React.MouseEvent) => { e.preventDefault(); alert('Connect Square is disabled in demo mode. Sign up to connect your real POS!') } : undefined}
              className="px-4 py-2.5 sm:py-2 text-xs font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#6B4FE0] transition-all shadow-[0_0_16px_rgba(124,92,255,0.25)] hover:shadow-[0_0_24px_rgba(124,92,255,0.35)] inline-flex items-center gap-2"
            >
              <ExternalLink size={14} />
              Connect POS
            </a>
            )}
          </div>

          {connections.length > 0 ? (
            <div className="divide-y divide-[#1F1F23]/50">
              {connections.map(c => {
                const Icon = statusIcons[c.status] || WifiOff
                const color = statusColors[c.status] || 'text-[#A1A1A8]/50'

                return (
                  <div key={c.id} className="px-4 sm:px-5 py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {posSystemsByKey[c.provider] ? (
                          <POSLogo system={c.provider as POSSystemKey} size="md" />
                        ) : (
                          <div className={clsx('p-2 rounded-lg bg-[#1F1F23]/60', color)}>
                            <Icon size={18} />
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-medium text-[#F5F5F7] capitalize">{posSystemsByKey[c.provider]?.name || c.provider}</p>
                          <p className="text-xs text-[#A1A1A8]/50 font-mono">
                            Merchant: {c.merchant_id || 'Unknown'}
                          </p>
                        </div>
                      </div>
                      <span className={clsx('badge', {
                        'badge-green': c.status === 'connected',
                        'badge-amber': c.status === 'syncing' || c.status === 'pending',
                        'badge-red': c.status === 'error' || c.status === 'disconnected',
                      })}>
                        {c.status}
                      </span>
                    </div>

                    <div className="mt-3 grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 text-xs">
                      <div>
                        <span className="text-[#A1A1A8]/40">Last Sync</span>
                        <p className="text-[#A1A1A8] mt-0.5 font-mono">
                          {c.last_sync_at ? formatRelative(c.last_sync_at) : 'Never'}
                        </p>
                      </div>
                      <div>
                        <span className="text-[#A1A1A8]/40">Historical Import</span>
                        <p className="text-[#A1A1A8] mt-0.5">
                          {c.historical_import_complete ? '✅ Complete' : '⏳ In progress'}
                        </p>
                      </div>
                      <div>
                        <span className="text-[#A1A1A8]/40">Connected</span>
                        <p className="text-[#A1A1A8] mt-0.5 font-mono">{formatDateTime(c.created_at)}</p>
                      </div>
                      {c.last_error && (
                        <div>
                          <span className="text-[#A1A1A8]/40">Last Error</span>
                          <p className="text-red-400 mt-0.5 truncate">{c.last_error}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="p-4">
              <POSSelectorPanel defaultSelected="square" />
            </div>
          )}
        </div>
      </ScrollReveal>

      {/* Business Type Tuning */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <BusinessTuningPanel />
      </ScrollReveal>

      {/* Billing & Subscription */}
      <ScrollReveal variant="fadeUp" delay={0.2}>
        <BillingCard orgId={orgId} apiUrl={API_URL} />
      </ScrollReveal>

      {/* API Info */}
      <ScrollReveal variant="fadeUp" delay={0.25}>
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-3">API Configuration</h3>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between py-1.5 border-b border-[#1F1F23]/50">
              <span className="text-[#A1A1A8]/60">API Server</span>
              <code className="text-[#A1A1A8] font-mono text-[11px] truncate max-w-[200px] sm:max-w-none">{API_URL || 'localhost:8000'}</code>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-[#1F1F23]/50">
              <span className="text-[#A1A1A8]/60">Organization</span>
              <code className="text-[#A1A1A8] font-mono text-[11px]">{orgId}</code>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span className="text-[#A1A1A8]/60">Version</span>
              <code className="text-[#A1A1A8] font-mono text-[11px]">0.2.0</code>
            </div>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
