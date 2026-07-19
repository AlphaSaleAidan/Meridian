import { useMemo, useState } from 'react'
import {
  Building2, DollarSign, Receipt, Phone, ArrowRightLeft,
  Link2, Send, CheckCircle2, XCircle, MinusCircle, Loader2,
} from 'lucide-react'
import StatCard from '@/components/StatCard'
import CommandTierGate from '@/components/CommandTierGate'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import { useApi } from '@/hooks/useApi'
import { useOrgId } from '@/hooks/useOrg'
import { formatCents, formatNumber } from '@/lib/format'
import { hubApi, type HubOverview, type PushDownResult } from '@/lib/hub-api'

/**
 * Multi-Location Hub (Command tier).
 *
 * One owner, one login, many locations. The active hub org is the merchant's
 * current org (useOrgId); the backend gate verifies membership + Command tier on
 * every call. All aggregation and push-down is scoped server-side to the orgs
 * this identity actually belongs to — the UI never supplies an org list of its
 * own choosing.
 */
function HubInner() {
  const hubOrgId = useOrgId()
  const { data: overview, loading, error, refetch } =
    useApi<HubOverview>(() => hubApi.overview(hubOrgId), [hubOrgId])

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [greeting, setGreeting] = useState('')
  const [pushing, setPushing] = useState(false)
  const [pushResult, setPushResult] = useState<PushDownResult | null>(null)

  const locations = overview?.locations ?? []
  const totals = overview?.totals

  const toggle = (orgId: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(orgId)) next.delete(orgId)
      else next.add(orgId)
      return next
    })
  }

  const canPush = selected.size > 0 && greeting.trim().length > 0 && !pushing

  const runPush = async () => {
    if (!canPush) return
    setPushing(true)
    setPushResult(null)
    try {
      const res = await hubApi.pushDown(
        hubOrgId,
        'chatbot_config',
        { greeting: greeting.trim() },
        Array.from(selected),
      )
      setPushResult(res)
    } catch (e: any) {
      setPushResult({ config_type: 'chatbot_config', results: [{ org_id: '*', status: 'error', detail: String(e?.message || e) }] })
    } finally {
      setPushing(false)
    }
  }

  const statusIcon = (status: string) => {
    if (status === 'applied') return <CheckCircle2 className="w-4 h-4 text-emerald-400" />
    if (status === 'skipped_not_owned' || status === 'not_implemented') return <MinusCircle className="w-4 h-4 text-[#8E8E93]" />
    return <XCircle className="w-4 h-4 text-rose-400" />
  }

  if (loading) return <LoadingPage />
  if (error) return <ErrorState message={error} onRetry={refetch} />
  if (!overview || locations.length === 0) {
    return (
      <EmptyState
        title="No connected locations yet"
        description="Connect the Meridian portals you own to run them all from one hub."
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Building2 className="w-5 h-5 text-[#1A8FD6]" />
        <h1 className="text-2xl font-bold text-[#F5F5F7]">Multi-Location Hub</h1>
        <span className="text-sm text-[#8E8E93]">
          {formatNumber(overview.location_count)} location{overview.location_count === 1 ? '' : 's'} · {overview.window_days}d
        </span>
      </div>

      {/* Unified totals */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Total revenue" value={formatCents(totals?.revenue_cents ?? 0)} icon={DollarSign} />
        <StatCard label="Total transactions" value={formatNumber(totals?.transaction_count ?? 0)} icon={Receipt} />
        <StatCard label="Phone calls" value={formatNumber(totals?.phone_call_count ?? 0)} icon={Phone} />
      </div>

      {/* Per-location table + branch selection */}
      <div className="card p-0 overflow-hidden">
        <div className="px-5 py-3 border-b border-white/5 flex items-center gap-2">
          <ArrowRightLeft className="w-4 h-4 text-[#1A8FD6]" />
          <h2 className="font-semibold text-[#F5F5F7]">Locations</h2>
          <span className="text-xs text-[#8E8E93] ml-auto">Select branches to push config to</span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[#8E8E93] border-b border-white/5">
              <th className="px-5 py-2 w-8"></th>
              <th className="px-5 py-2">Location</th>
              <th className="px-5 py-2 text-right">Revenue</th>
              <th className="px-5 py-2 text-right">Txns</th>
              <th className="px-5 py-2 text-right">Calls</th>
            </tr>
          </thead>
          <tbody>
            {locations.map(loc => (
              <tr key={loc.org_id} className="border-b border-white/5 hover:bg-white/[0.02]">
                <td className="px-5 py-3">
                  <input
                    type="checkbox"
                    checked={selected.has(loc.org_id)}
                    onChange={() => toggle(loc.org_id)}
                    aria-label={`Select ${loc.name}`}
                  />
                </td>
                <td className="px-5 py-3 text-[#F5F5F7]">
                  {loc.name || loc.org_id}
                  {loc.plan_tier && <span className="ml-2 text-xs text-[#8E8E93]">{loc.plan_tier}</span>}
                </td>
                <td className="px-5 py-3 text-right font-mono text-[#F5F5F7]">{formatCents(loc.revenue_cents)}</td>
                <td className="px-5 py-3 text-right font-mono text-[#8E8E93]">{formatNumber(loc.transaction_count)}</td>
                <td className="px-5 py-3 text-right font-mono text-[#8E8E93]">{formatNumber(loc.phone_call_count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Franchise push-down: chatbot greeting (wired v1 config type) */}
      <div className="card p-5 space-y-3">
        <div className="flex items-center gap-2">
          <Send className="w-4 h-4 text-[#1A8FD6]" />
          <h2 className="font-semibold text-[#F5F5F7]">Push agent greeting to selected locations</h2>
        </div>
        <p className="text-sm text-[#8E8E93]">
          Deploy a new phone/website agent greeting to the {selected.size} selected
          location{selected.size === 1 ? '' : 's'}. Only locations you own or administer
          receive it; each result is confirmed per-branch below.
        </p>
        <textarea
          value={greeting}
          onChange={e => setGreeting(e.target.value)}
          placeholder="Thanks for calling! How can we help you today?"
          className="input w-full min-h-[80px]"
        />
        <button className="btn-primary inline-flex items-center gap-2" disabled={!canPush} onClick={runPush}>
          {pushing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />}
          Push to {selected.size} location{selected.size === 1 ? '' : 's'}
        </button>

        {pushResult && (
          <div className="mt-3 space-y-1">
            {pushResult.results.map(r => (
              <div key={r.org_id} className="flex items-center gap-2 text-sm">
                {statusIcon(r.status)}
                <span className="text-[#F5F5F7]">
                  {locations.find(l => l.org_id === r.org_id)?.name || r.org_id}
                </span>
                <span className="text-[#8E8E93]">— {r.status.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function HubPage() {
  return (
    <CommandTierGate>
      <HubInner />
    </CommandTierGate>
  )
}
