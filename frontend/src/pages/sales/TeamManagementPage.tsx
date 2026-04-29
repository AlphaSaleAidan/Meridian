import { useState } from 'react'
import { Users, TrendingUp, DollarSign, Target, Search, MoreVertical } from 'lucide-react'
import { clsx } from 'clsx'

interface TeamMember {
  id: string
  name: string
  email: string
  phone: string
  commission_rate: number
  deals_open: number
  deals_won: number
  total_earned: number
  total_paid: number
  is_active: boolean
  joined: string
}

const DEMO_TEAM: TeamMember[] = [
  { id: '1', name: 'Sarah Mitchell', email: 'sarah@meridian.com', phone: '(555) 100-2000', commission_rate: 35, deals_open: 5, deals_won: 12, total_earned: 4280000, total_paid: 3500000, is_active: true, joined: '2025-09-15' },
  { id: '2', name: 'Demo Sales Rep', email: 'demo@meridian.com', phone: '(555) 123-4567', commission_rate: 35, deals_open: 8, deals_won: 7, total_earned: 1822000, total_paid: 960000, is_active: true, joined: '2026-01-20' },
  { id: '3', name: 'Marcus Johnson', email: 'marcus@meridian.com', phone: '(555) 300-4000', commission_rate: 40, deals_open: 3, deals_won: 18, total_earned: 6120000, total_paid: 5800000, is_active: true, joined: '2025-06-01' },
  { id: '4', name: 'Priya Patel', email: 'priya@meridian.com', phone: '(555) 400-5000', commission_rate: 30, deals_open: 6, deals_won: 4, total_earned: 980000, total_paid: 700000, is_active: true, joined: '2026-02-10' },
  { id: '5', name: 'Jake Torres', email: 'jake@meridian.com', phone: '(555) 500-6000', commission_rate: 30, deals_open: 0, deals_won: 2, total_earned: 320000, total_paid: 320000, is_active: false, joined: '2025-11-01' },
]

function formatCurrency(cents: number): string {
  return '$' + (cents / 100).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

export default function TeamManagementPage() {
  const [search, setSearch] = useState('')

  const team = DEMO_TEAM.filter(m => {
    if (!search) return true
    const s = search.toLowerCase()
    return m.name.toLowerCase().includes(s) || m.email.toLowerCase().includes(s)
  })

  const totalActive = DEMO_TEAM.filter(m => m.is_active).length
  const totalDealsWon = DEMO_TEAM.reduce((s, m) => s + m.deals_won, 0)
  const totalRevenue = DEMO_TEAM.reduce((s, m) => s + m.total_earned, 0)

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[#F5F5F7]">Team Management</h1>
        <p className="text-sm text-[#A1A1A8] mt-0.5">Manage your sales team performance and commissions.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="card p-4 border border-[#1F1F23]">
          <div className="flex items-center gap-2 mb-2">
            <Users size={14} className="text-[#1A8FD6]" />
            <span className="text-[10px] text-[#A1A1A8]">Active Reps</span>
          </div>
          <p className="text-lg font-bold text-[#F5F5F7]">{totalActive}</p>
        </div>
        <div className="card p-4 border border-[#1F1F23]">
          <div className="flex items-center gap-2 mb-2">
            <Target size={14} className="text-[#17C5B0]" />
            <span className="text-[10px] text-[#A1A1A8]">Total Deals Won</span>
          </div>
          <p className="text-lg font-bold text-[#F5F5F7]">{totalDealsWon}</p>
        </div>
        <div className="card p-4 border border-[#1F1F23]">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign size={14} className="text-[#7C5CFF]" />
            <span className="text-[10px] text-[#A1A1A8]">Total Commissions</span>
          </div>
          <p className="text-lg font-bold text-[#F5F5F7]">{formatCurrency(totalRevenue)}</p>
        </div>
        <div className="card p-4 border border-[#1F1F23]">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={14} className="text-[#F59E0B]" />
            <span className="text-[10px] text-[#A1A1A8]">Avg Close Rate</span>
          </div>
          <p className="text-lg font-bold text-[#F5F5F7]">
            {Math.round(DEMO_TEAM.reduce((s, m) => s + (m.deals_won / Math.max(m.deals_open + m.deals_won, 1)) * 100, 0) / DEMO_TEAM.length)}%
          </p>
        </div>
      </div>

      <div className="relative max-w-sm">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
        <input
          type="text" value={search} onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#17C5B0]/50"
          placeholder="Search team members..."
        />
      </div>

      <div className="card border border-[#1F1F23] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[#1F1F23]">
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Rep</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Rate</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Open Deals</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Won</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Earned</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Paid</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F1F23]">
              {team.map(member => (
                <tr key={member.id} className="hover:bg-[#111113] transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-[11px] font-medium text-[#F5F5F7]">{member.name}</p>
                    <p className="text-[10px] text-[#A1A1A8]/40">{member.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[11px] font-semibold text-[#7C5CFF]">{member.commission_rate}%</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[11px] text-[#F5F5F7]">{member.deals_open}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[11px] font-semibold text-[#17C5B0]">{member.deals_won}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[11px] font-semibold text-[#F5F5F7]">{formatCurrency(member.total_earned)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[11px] text-[#A1A1A8]">{formatCurrency(member.total_paid)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium',
                      member.is_active
                        ? 'bg-[#17C5B0]/10 text-[#17C5B0] border border-[#17C5B0]/20'
                        : 'bg-[#A1A1A8]/10 text-[#A1A1A8] border border-[#A1A1A8]/20'
                    )}>
                      {member.is_active ? 'Active' : 'Inactive'}
                    </span>
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
