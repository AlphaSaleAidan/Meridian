/**IT Dashboard — Cline system oversight for admins/owners.

Shows health scores, merchant grid, error timeline, auto-fix success rate,
escalation queue, and conversation browser.
**/
import { useState } from 'react'
import { clsx } from 'clsx'
import {
  Activity, AlertTriangle, Bot, CheckCircle, Clock, Heart,
  MessageCircle, Shield, TrendingDown, TrendingUp, Wrench,
} from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { LoadingPage, ErrorState } from '@/components/LoadingState'

const API_BASE = import.meta.env.VITE_API_URL || ''

async function fetchITDashboard() {
  const res = await fetch(`${API_BASE}/api/admin/it-dashboard`)
  if (!res.ok) throw new Error(`Failed: ${res.status}`)
  return res.json()
}

function HealthGauge({ score, label }: { score: number; label: string }) {
  const color = score >= 80 ? 'text-emerald-400' : score >= 50 ? 'text-amber-400' : 'text-red-400'
  const bgColor = score >= 80 ? 'bg-emerald-500/10' : score >= 50 ? 'bg-amber-500/10' : 'bg-red-500/10'
  return (
    <div className="text-center">
      <div className={clsx('w-20 h-20 rounded-2xl flex items-center justify-center mx-auto', bgColor)}>
        <span className={clsx('text-3xl font-bold font-mono', color)}>{Math.round(score)}</span>
      </div>
      <p className="text-[11px] text-[#A1A1A8] mt-2 font-medium">{label}</p>
    </div>
  )
}

export default function ITDashboardPage() {
  const [tab, setTab] = useState<'overview' | 'errors' | 'chains'>('overview')
  const dashboard = useApi(fetchITDashboard, [])

  if (dashboard.loading) return <LoadingPage />
  if (dashboard.error) return <ErrorState message={dashboard.error} onRetry={dashboard.refetch} />

  const data = dashboard.data!
  const summary = data.summary || {}
  const healthByOrg = data.health_by_org || []
  const recentErrors = data.recent_errors || []
  const recentChains = data.recent_chains || []

  const tabs = [
    { key: 'overview' as const, label: 'Overview', icon: Activity },
    { key: 'errors' as const, label: `Errors (${recentErrors.length})`, icon: AlertTriangle },
    { key: 'chains' as const, label: 'Reasoning', icon: Bot },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center">
          <Shield size={20} className="text-[#17C5B0]" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">IT Health Dashboard</h1>
          <p className="text-sm text-[#A1A1A8]">Cline system oversight</p>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="card p-4 text-center">
          <HealthGauge score={summary.average_health_score || 0} label="Avg Health" />
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Heart size={16} className="text-[#1A8FD6]" />
            <span className="text-xs text-[#A1A1A8] uppercase tracking-wider">Orgs</span>
          </div>
          <p className="stat-value">{summary.total_organizations || 0}</p>
          <p className="text-[10px] text-[#A1A1A8]/50 mt-1">
            {summary.declining_orgs || 0} declining
          </p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-amber-400" />
            <span className="text-xs text-[#A1A1A8] uppercase tracking-wider">Errors</span>
          </div>
          <p className="stat-value">{summary.recent_errors_count || 0}</p>
          <p className="text-[10px] text-[#A1A1A8]/50 mt-1">last 24h</p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Bot size={16} className="text-[#7C5CFF]" />
            <span className="text-xs text-[#A1A1A8] uppercase tracking-wider">Failed Chains</span>
          </div>
          <p className="stat-value">{summary.failed_reasoning_chains || 0}</p>
          <p className="text-[10px] text-[#A1A1A8]/50 mt-1">reasoning failures</p>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="period-toggle">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={clsx(
              tab === t.key ? 'period-btn-active' : 'period-btn-inactive',
              'flex items-center gap-1.5',
            )}
          >
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-[#F5F5F7]">Merchant Health Grid</h2>
          {healthByOrg.length === 0 ? (
            <div className="card p-8 text-center text-sm text-[#A1A1A8]/50">
              No health data yet. Scores appear after agents run.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {healthByOrg.map((h: any, i: number) => (
                <div key={i} className="card p-4 flex items-center gap-3">
                  <div className={clsx(
                    'w-10 h-10 rounded-lg flex items-center justify-center font-bold font-mono text-sm',
                    h.score >= 80 ? 'bg-emerald-500/10 text-emerald-400'
                      : h.score >= 50 ? 'bg-amber-500/10 text-amber-400'
                      : 'bg-red-500/10 text-red-400',
                  )}>
                    {h.score}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#F5F5F7] truncate font-mono">
                      {h.business_id?.slice(0, 8)}...
                    </p>
                    <div className="flex items-center gap-1 mt-0.5">
                      {h.trend === 'improving' && <TrendingUp size={12} className="text-emerald-400" />}
                      {h.trend === 'declining' && <TrendingDown size={12} className="text-red-400" />}
                      {h.trend === 'stable' && <Activity size={12} className="text-[#A1A1A8]" />}
                      <span className="text-[10px] text-[#A1A1A8]">{h.trend || 'unknown'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'errors' && (
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-[#F5F5F7]">Error Timeline</h2>
          {recentErrors.length === 0 ? (
            <div className="card p-8 text-center">
              <CheckCircle size={24} className="text-emerald-400 mx-auto mb-2" />
              <p className="text-sm text-[#A1A1A8]/50">No recent errors</p>
            </div>
          ) : (
            recentErrors.map((err: any, i: number) => (
              <div key={i} className="card p-4 flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <AlertTriangle size={14} className="text-red-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-medium text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                      {err.error_type}
                    </span>
                    <span className="text-[10px] text-[#A1A1A8]/40 font-mono">{err.agent_name}</span>
                  </div>
                  <p className="text-sm text-[#F5F5F7] mt-1 line-clamp-2">{err.message || 'No message'}</p>
                  <p className="text-[10px] text-[#A1A1A8]/30 mt-1 font-mono">
                    {err.created_at ? new Date(err.created_at).toLocaleString() : ''}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'chains' && (
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-[#F5F5F7]">Reasoning Chains</h2>
          {recentChains.length === 0 ? (
            <div className="card p-8 text-center text-sm text-[#A1A1A8]/50">
              No reasoning chains recorded yet.
            </div>
          ) : (
            recentChains.map((chain: any, i: number) => (
              <div key={i} className="card p-4 flex items-center gap-3">
                <div className={clsx(
                  'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                  chain.error ? 'bg-red-500/10' : chain.verdict === 'actionable' ? 'bg-[#17C5B0]/10' : 'bg-[#1F1F23]',
                )}>
                  {chain.error ? (
                    <AlertTriangle size={14} className="text-red-400" />
                  ) : chain.verdict === 'actionable' ? (
                    <Wrench size={14} className="text-[#17C5B0]" />
                  ) : (
                    <CheckCircle size={14} className="text-[#A1A1A8]" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[#F5F5F7]">{chain.agent_name}</span>
                    <span className={clsx(
                      'text-[10px] font-medium px-1.5 py-0.5 rounded-full border',
                      chain.verdict === 'actionable' ? 'bg-[#17C5B0]/10 text-[#17C5B0] border-[#17C5B0]/20'
                        : chain.verdict === 'monitoring' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        : 'bg-[#1F1F23] text-[#A1A1A8] border-[#1F1F23]',
                    )}>
                      {chain.verdict || 'unknown'}
                    </span>
                  </div>
                  {chain.error && (
                    <p className="text-[11px] text-red-400/70 mt-0.5 truncate">{chain.error}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-[10px] text-[#A1A1A8]/40 font-mono">
                      conf: {chain.final_confidence ? `${(chain.final_confidence * 100).toFixed(0)}%` : '—'}
                    </span>
                    <span className="text-[10px] text-[#A1A1A8]/30 font-mono">
                      {chain.created_at ? new Date(chain.created_at).toLocaleString() : ''}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
