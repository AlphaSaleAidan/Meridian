import { useState } from 'react'
import { clsx } from 'clsx'
import { Search, Settings2, ChevronDown } from 'lucide-react'
import { posSystems, type POSSystem } from '@/data/pos-systems'
import POSLogo, { POSStatusBadge } from '@/components/POSLogo'
import type { POSSystemKey } from '@/data/pos-systems'
import ScrollReveal from '@/components/ScrollReveal'

const API_BASE = import.meta.env.VITE_API_URL || ''

const STATUS_OPTIONS = ['integrated', 'coming_soon', 'contingency', 'unsupported'] as const

const demoMerchantCounts: Record<string, number> = {
  square: 847,
  toast: 423,
  clover: 312,
  'lightspeed-restaurant': 89,
  'lightspeed-retail': 67,
  spoton: 134,
  revel: 45,
  touchbistro: 78,
  aloha: 156,
  micros: 203,
  heartland: 34,
  'shopify-pos': 56,
  'stripe-terminal': 29,
}

const demoWaitlistCounts: Record<string, number> = {
  'lightspeed-restaurant': 43,
  spoton: 27,
  touchbistro: 19,
  aloha: 31,
  micros: 22,
  heartland: 14,
  revel: 11,
  brink: 8,
  simphony: 5,
}

export default function POSCoveragePage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [statusOverrides, setStatusOverrides] = useState<Record<string, string>>({})
  const [editingKey, setEditingKey] = useState<string | null>(null)

  function handleStatusChange(systemKey: string, newStatus: string) {
    setStatusOverrides(prev => ({ ...prev, [systemKey]: newStatus }))
    setEditingKey(null)
    fetch(`${API_BASE}/api/pos/status?pos_system=${encodeURIComponent(systemKey)}&new_status=${encodeURIComponent(newStatus)}`, {
      method: 'PATCH',
    }).catch(() => {})
  }

  const filtered = posSystems.filter(s => {
    const matchesSearch = s.name.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'all' || s.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const totalMerchants = Object.values(demoMerchantCounts).reduce((s, v) => s + v, 0)
  const totalWaitlist = Object.values(demoWaitlistCounts).reduce((s, v) => s + v, 0)

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">POS System Coverage</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            <span className="font-mono">{posSystems.length}</span> systems tracked •
            <span className="font-mono"> {totalMerchants}</span> merchants connected •
            <span className="font-mono"> {totalWaitlist}</span> on waitlist
          </p>
        </div>
      </ScrollReveal>

      {/* Stats */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Integrated', count: posSystems.filter(s => s.status === 'integrated').length, color: 'text-[#17C5B0]' },
            { label: 'Coming Soon', count: posSystems.filter(s => s.status === 'coming_soon').length, color: 'text-amber-400' },
            { label: 'Manual Import', count: posSystems.filter(s => s.status === 'contingency').length, color: 'text-[#1A8FD6]' },
            { label: 'Contact Us', count: posSystems.filter(s => s.status === 'unsupported').length, color: 'text-[#A1A1A8]' },
          ].map(stat => (
            <div key={stat.label} className="card p-4">
              <p className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider">{stat.label}</p>
              <p className={clsx('text-2xl font-bold font-mono mt-1', stat.color)}>{stat.count}</p>
            </div>
          ))}
        </div>
      </ScrollReveal>

      {/* Filters */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1 sm:max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/50" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search POS systems..."
              className="w-full pl-9 pr-4 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/40 transition-all"
            />
          </div>
          <div className="period-toggle">
            {[
              { key: 'all', label: 'All' },
              { key: 'integrated', label: 'Integrated' },
              { key: 'coming_soon', label: 'Coming Soon' },
              { key: 'contingency', label: 'Manual' },
              { key: 'unsupported', label: 'Contact' },
            ].map(f => (
              <button
                key={f.key}
                onClick={() => setStatusFilter(f.key)}
                className={statusFilter === f.key ? 'period-btn-active' : 'period-btn-inactive'}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </ScrollReveal>

      {/* Table */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[700px]">
              <thead>
                <tr>
                  <th className="text-left">POS System</th>
                  <th className="text-center">Status</th>
                  <th className="text-right">Merchants</th>
                  <th className="text-right">Waitlist</th>
                  <th className="text-center">Effort</th>
                  <th className="text-center">Tier</th>
                  <th className="text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(system => (
                  <tr key={system.key}>
                    <td>
                      <div className="flex items-center gap-3">
                        <POSLogo system={system.key as POSSystemKey} size="sm" />
                        <div>
                          <p className="font-medium text-[#F5F5F7]">{system.name}</p>
                          <p className="text-[10px] text-[#A1A1A8]/40 truncate max-w-[200px]">
                            {system.integrationStatus.notes.slice(0, 60)}...
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="text-center">
                      <POSStatusBadge status={(statusOverrides[system.key] || system.status) as POSSystem['status']} />
                    </td>
                    <td className="text-right font-mono text-[#F5F5F7]">
                      {demoMerchantCounts[system.key] || 0}
                    </td>
                    <td className="text-right font-mono text-[#A1A1A8]">
                      {demoWaitlistCounts[system.key] || 0}
                    </td>
                    <td className="text-center">
                      <span className={clsx(
                        'text-[10px] font-medium px-1.5 py-0.5 rounded-full',
                        system.integrationStatus.estimatedIntegrationEffort === 'low' ? 'bg-[#17C5B0]/10 text-[#17C5B0]' :
                        system.integrationStatus.estimatedIntegrationEffort === 'medium' ? 'bg-amber-400/10 text-amber-400' :
                        'bg-red-400/10 text-red-400',
                      )}>
                        {system.integrationStatus.estimatedIntegrationEffort}
                      </span>
                    </td>
                    <td className="text-center font-mono text-[#A1A1A8] text-xs">
                      T{system.tier}
                    </td>
                    <td className="text-center">
                      <div className="relative inline-block">
                        <button
                          onClick={() => setEditingKey(editingKey === system.key ? null : system.key)}
                          className="flex items-center gap-1 px-2 py-1 text-[10px] text-[#A1A1A8] border border-[#1F1F23] rounded hover:border-[#2A2A2E] transition-colors"
                        >
                          <Settings2 size={10} /> <ChevronDown size={10} />
                        </button>
                        {editingKey === system.key && (
                          <div className="absolute z-50 right-0 mt-1 w-36 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] shadow-xl overflow-hidden">
                            {STATUS_OPTIONS.map(opt => (
                              <button
                                key={opt}
                                onClick={() => handleStatusChange(system.key, opt)}
                                className={clsx(
                                  'w-full text-left px-3 py-2 text-[11px] hover:bg-[#1F1F23]/50 transition-colors',
                                  (statusOverrides[system.key] || system.status) === opt ? 'text-[#17C5B0]' : 'text-[#A1A1A8]',
                                )}
                              >
                                {opt.replace('_', ' ')}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
