import { useState, useEffect } from 'react'
import { Mail, Send, CheckCircle, AlertTriangle, MousePointerClick, Eye, RefreshCw } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface EmailStats {
  total_sent: number
  delivered: number
  bounced: number
  opened: number
  clicked: number
  errors: number
  open_rate: number
  click_rate: number
}

interface EmailLogEntry {
  id: string
  to_address: string
  template: string
  subject: string
  status: string
  postal_status: string | null
  created_at: string
  opened_at: string | null
  clicked_at: string | null
}

function StatCard({ label, value, sub, icon: Icon, color }: {
  label: string
  value: string | number
  sub?: string
  icon: typeof Mail
  color: string
}) {
  return (
    <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] text-[#A1A1A8] font-medium">{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center`} style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
          <Icon size={16} style={{ color }} />
        </div>
      </div>
      <p className="text-2xl font-bold text-[#F5F5F7]">{value}</p>
      {sub && <p className="text-[11px] text-[#52525B] mt-1">{sub}</p>}
    </div>
  )
}

function statusBadge(status: string | null) {
  const s = status || 'pending'
  const colors: Record<string, string> = {
    sent: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    delivered: 'bg-green-500/10 text-green-400 border-green-500/20',
    bounced: 'bg-red-500/10 text-red-400 border-red-500/20',
    failed: 'bg-red-500/10 text-red-400 border-red-500/20',
    error: 'bg-red-500/10 text-red-400 border-red-500/20',
    skipped: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    pending: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  }
  const cls = colors[s] || colors.pending
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium border ${cls}`}>
      {s}
    </span>
  )
}

export default function EmailDashboardPage() {
  const [stats, setStats] = useState<EmailStats | null>(null)
  const [log, setLog] = useState<EmailLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  async function load() {
    setLoading(true)
    try {
      const [statsRes, logRes] = await Promise.all([
        fetch(`${API_BASE}/api/email/stats`),
        fetch(`${API_BASE}/api/email/log?limit=100${filter ? `&template=${filter}` : ''}`),
      ])
      if (statsRes.ok) setStats(await statsRes.json())
      if (logRes.ok) {
        const data = await logRes.json()
        setLog(data.data || [])
      }
    } catch (e) {
      console.error('Failed to load email data:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filter])

  const templates = ['welcome', 'onboarding_reminder', 'onboarding_complete', 'weekly_report', 'anomaly_alert', 'pos_connected', 'password_reset', 'invite', 'lead_assigned', 'trial_expiring', 'payment_receipt']

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Email Dashboard</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">Postal delivery tracking and analytics</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#A1A1A8] hover:text-white hover:border-[#2F2F33] transition-colors">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Sent" value={stats.total_sent} icon={Send} color="#1A8FD6" />
          <StatCard label="Delivered" value={stats.delivered} icon={CheckCircle} color="#22C55E" />
          <StatCard label="Open Rate" value={`${stats.open_rate}%`} sub={`${stats.opened} opened`} icon={Eye} color="#A855F7" />
          <StatCard label="Click Rate" value={`${stats.click_rate}%`} sub={`${stats.clicked} clicked`} icon={MousePointerClick} color="#F59E0B" />
        </div>
      )}

      {stats && (stats.bounced > 0 || stats.errors > 0) && (
        <div className="flex gap-4">
          {stats.bounced > 0 && (
            <div className="flex items-center gap-2 px-3 py-2 bg-red-500/5 border border-red-500/15 rounded-lg">
              <AlertTriangle size={14} className="text-red-400" />
              <span className="text-sm text-red-400">{stats.bounced} bounced</span>
            </div>
          )}
          {stats.errors > 0 && (
            <div className="flex items-center gap-2 px-3 py-2 bg-red-500/5 border border-red-500/15 rounded-lg">
              <AlertTriangle size={14} className="text-red-400" />
              <span className="text-sm text-red-400">{stats.errors} errors</span>
            </div>
          )}
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setFilter('')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${!filter ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/20' : 'bg-[#111113] text-[#A1A1A8] border border-[#1F1F23] hover:text-white'}`}
        >
          All
        </button>
        {templates.map(t => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === t ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/20' : 'bg-[#111113] text-[#A1A1A8] border border-[#1F1F23] hover:text-white'}`}
          >
            {t.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Log table */}
      <div className="bg-[#111113] border border-[#1F1F23] rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1F1F23]">
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-[#52525B] uppercase tracking-wider">Recipient</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-[#52525B] uppercase tracking-wider">Template</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-[#52525B] uppercase tracking-wider">Subject</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-[#52525B] uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-[#52525B] uppercase tracking-wider">Sent</th>
              </tr>
            </thead>
            <tbody>
              {log.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-[#52525B]">
                    {loading ? 'Loading...' : 'No emails sent yet'}
                  </td>
                </tr>
              )}
              {log.map(entry => (
                <tr key={entry.id} className="border-b border-[#1F1F23]/50 hover:bg-[#0A0A0B]/50">
                  <td className="px-4 py-3 text-[#F5F5F7] font-mono text-xs">{entry.to_address}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-[#A1A1A8] bg-[#0A0A0B] px-2 py-0.5 rounded border border-[#1F1F23]">
                      {entry.template}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#A1A1A8] text-xs max-w-[200px] truncate">{entry.subject}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {statusBadge(entry.postal_status || entry.status)}
                      {entry.opened_at && <Eye size={12} className="text-purple-400" />}
                      {entry.clicked_at && <MousePointerClick size={12} className="text-amber-400" />}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[#52525B] text-xs">
                    {new Date(entry.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
