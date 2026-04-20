import { useLocation } from 'react-router-dom'
import { Wifi, WifiOff, RefreshCw, CheckCircle2, AlertCircle, Clock, ExternalLink } from 'lucide-react'
import { clsx } from 'clsx'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatDateTime, formatRelative } from '@/lib/format'
import { LoadingPage, ErrorState } from '@/components/LoadingState'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'
const API_URL = import.meta.env.VITE_API_URL || ''

const statusIcons: Record<string, typeof Wifi> = {
  connected: CheckCircle2,
  syncing: RefreshCw,
  error: AlertCircle,
  pending: Clock,
  disconnected: WifiOff,
}

const statusColors: Record<string, string> = {
  connected: 'text-emerald-400',
  syncing: 'text-amber-400',
  error: 'text-red-400',
  pending: 'text-slate-400',
  disconnected: 'text-slate-500',
}

export default function SettingsPage() {
  const location = useLocation()
  const basePath = location.pathname.startsWith('/app') ? '/app' : '/demo'
  const conn = useApi(() => api.connection(ORG_ID), [])

  if (conn.loading) return <LoadingPage />
  if (conn.error) return <ErrorState message={conn.error} onRetry={conn.refetch} />

  const connections = conn.data!.connections

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-sm text-slate-400 mt-1">POS connections and account configuration</p>
      </div>

      {/* POS Connections */}
      <div className="card overflow-hidden">
        <div className="px-4 sm:px-5 py-4 border-b border-slate-800/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-white">POS Connections</h3>
          <a
            href={basePath === '/demo' ? '#' : `${API_URL}/api/square/authorize?org_id=${ORG_ID}`}
            onClick={basePath === '/demo' ? (e) => { e.preventDefault(); alert('Connect Square is disabled in demo mode. Sign up to connect your real POS!') } : undefined}
            className="px-4 py-2.5 sm:py-2 text-xs font-medium text-white bg-meridian-700 rounded-lg hover:bg-meridian-600 transition-colors inline-flex items-center gap-2"
          >
            <ExternalLink size={14} />
            Connect Square
          </a>
        </div>

        {connections.length > 0 ? (
          <div className="divide-y divide-slate-800/30">
            {connections.map(c => {
              const Icon = statusIcons[c.status] || WifiOff
              const color = statusColors[c.status] || 'text-slate-500'

              return (
                <div key={c.id} className="px-4 sm:px-5 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={clsx('p-2 rounded-lg bg-slate-800/60', color)}>
                        <Icon size={18} />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white capitalize">{c.provider}</p>
                        <p className="text-xs text-slate-400">
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
                      <span className="text-slate-500">Last Sync</span>
                      <p className="text-slate-300 mt-0.5">
                        {c.last_sync_at ? formatRelative(c.last_sync_at) : 'Never'}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500">Historical Import</span>
                      <p className="text-slate-300 mt-0.5">
                        {c.historical_import_complete ? '✅ Complete' : '⏳ In progress'}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500">Connected</span>
                      <p className="text-slate-300 mt-0.5">{formatDateTime(c.created_at)}</p>
                    </div>
                    {c.last_error && (
                      <div>
                        <span className="text-slate-500">Last Error</span>
                        <p className="text-red-400 mt-0.5 truncate">{c.last_error}</p>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="px-5 py-12 text-center">
            <WifiOff size={32} className="text-slate-600 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-300">No POS Connected</p>
            <p className="text-xs text-slate-500 mt-1">
              Connect your Square account to start getting insights.
            </p>
          </div>
        )}
      </div>

      {/* API Info */}
      <div className="card p-4 sm:p-5">
        <h3 className="text-sm font-semibold text-white mb-3">API Configuration</h3>
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between py-1.5 border-b border-slate-800/30">
            <span className="text-slate-400">API Server</span>
            <code className="text-slate-300 font-mono text-[11px] truncate max-w-[200px] sm:max-w-none">{API_URL || 'localhost:8000'}</code>
          </div>
          <div className="flex items-center justify-between py-1.5 border-b border-slate-800/30">
            <span className="text-slate-400">Organization</span>
            <code className="text-slate-300 font-mono text-[11px]">{ORG_ID}</code>
          </div>
          <div className="flex items-center justify-between py-1.5">
            <span className="text-slate-400">Version</span>
            <code className="text-slate-300 font-mono text-[11px]">0.2.0</code>
          </div>
        </div>
      </div>
    </div>
  )
}
