import { clsx } from 'clsx'
import {
  Users, TrendingUp, TrendingDown, Minus, Award, Target,
  DollarSign,
} from 'lucide-react'
import { generateStaffPerformance, type StaffMember } from '@/lib/agent-data'
import { formatCents } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { useApi } from '@/hooks/useApi'
import { LoadingPage, ErrorState } from '@/components/LoadingState'
import DataPageSkeleton from '@/components/DataPageSkeleton'

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'up') return <TrendingUp size={12} className="text-[#17C5B0]" />
  if (trend === 'down') return <TrendingDown size={12} className="text-red-400" />
  return <Minus size={12} className="text-[#A1A1A8]/40" />
}

// Real connected-merchant data has revenueCents set; demo data carries the
// richer synthetic fields (upsell/rating/rev-per-hour). Render whichever we have.
function StaffCard({ member, rank, teamRevenue }: { member: StaffMember; rank: number; teamRevenue: number }) {
  const isTop = rank <= 2
  const real = member.revenueCents != null
  const revenue = member.revenueCents ?? member.revenuePerHour
  const txns = member.transactionCount ?? member.transactionsPerShift
  const sharePct = teamRevenue > 0 ? Math.round((revenue / teamRevenue) * 100) : 0

  return (
    <div className={clsx('card-hover p-4', isTop && 'border-[#17C5B0]/10')}>
      <div className="flex items-center gap-3 mb-3">
        <div className={clsx(
          'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 font-bold text-sm font-mono',
          rank === 1 ? 'bg-amber-400/10 text-amber-400' : rank === 2 ? 'bg-[#A1A1A8]/10 text-[#A1A1A8]' : 'bg-[#1F1F23] text-[#A1A1A8]/50'
        )}>
          #{rank}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-[#F5F5F7]">{member.name}</h4>
            {!real && <TrendIcon trend={member.trend} />}
            {rank === 1 && <Award size={14} className="text-amber-400" />}
          </div>
          {member.role && <p className="text-xs text-[#A1A1A8]/50">{member.role}</p>}
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-sm font-bold font-mono text-[#F5F5F7]">{formatCents(revenue)}</p>
          <p className="text-[10px] text-[#A1A1A8]/40">{real ? 'revenue' : 'rev/hour'}</p>
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <div>
          <p className="text-[10px] text-[#A1A1A8]/40">Avg Ticket</p>
          <p className="text-xs font-bold font-mono text-[#F5F5F7]">{formatCents(member.avgTicketCents)}</p>
        </div>
        <div>
          <p className="text-[10px] text-[#A1A1A8]/40">Transactions</p>
          <p className="text-xs font-bold font-mono text-[#F5F5F7]">{txns}</p>
        </div>
        {real ? (
          <>
            <div>
              <p className="text-[10px] text-[#A1A1A8]/40">Tips</p>
              <p className="text-xs font-bold font-mono text-[#F5F5F7]">{formatCents(member.tipCents ?? 0)}</p>
            </div>
            <div>
              <p className="text-[10px] text-[#A1A1A8]/40">% of Sales</p>
              <p className="text-xs font-bold font-mono text-[#F5F5F7]">{sharePct}%</p>
            </div>
          </>
        ) : (
          <>
            <div>
              <p className="text-[10px] text-[#A1A1A8]/40">Upsell Rate</p>
              <p className={clsx('text-xs font-bold font-mono', member.upsellRate >= 25 ? 'text-[#17C5B0]' : member.upsellRate >= 15 ? 'text-[#F5F5F7]' : 'text-amber-400')}>
                {member.upsellRate}%
              </p>
            </div>
            <div>
              <p className="text-[10px] text-[#A1A1A8]/40">Rating</p>
              <p className="text-xs font-bold font-mono text-[#F5F5F7]">{member.customerRating}</p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function StaffPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const posConnected = !!org?.pos_connected
  const apiData = useApi(() => api.staff(orgId), [orgId])

  const staff: StaffMember[] = isDemo ? generateStaffPerformance() : (apiData.data?.staff ?? [])

  // Before a POS is connected, the analytics endpoint isn't reachable for this
  // org — show the data-destination scaffold instead of a stuck spinner / 401.
  if (!isDemo && !posConnected) return <DataPageSkeleton title="Staff"><div /></DataPageSkeleton>
  if (!isDemo && apiData.loading) return <LoadingPage />
  if (!isDemo && apiData.error) return <ErrorState message={apiData.error} onRetry={apiData.refetch} />

  const rev = (m: StaffMember) => m.revenueCents ?? m.revenuePerHour ?? 0
  const sorted = [...staff].sort((a, b) => rev(b) - rev(a))
  const teamRevenue = sorted.reduce((s, m) => s + rev(m), 0)
  const avgTicket = sorted.length ? Math.round(sorted.reduce((s, m) => s + (m.avgTicketCents || 0), 0) / sorted.length) : 0
  const topPerformer = sorted[0] ?? null
  const topShare = teamRevenue > 0 && topPerformer ? Math.round((rev(topPerformer) / teamRevenue) * 100) : 0

  return (
    <DataPageSkeleton title="Staff" layout="table">
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Staff Performance</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Powered by Staff Performance Analyst agent • Ranked by revenue per hour
          </p>
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4" data-walkthrough="staff-stats">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <Users size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Team Size</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{staff.length}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <DollarSign size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">Total Revenue</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{formatCents(teamRevenue)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                <Target size={16} className="text-[#7C5CFF]" />
              </div>
              <div>
                <p className="stat-label">Avg Ticket</p>
                <p className="text-lg font-bold text-[#7C5CFF] font-mono">{formatCents(avgTicket)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <Award size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">Top Performer</p>
                <p className="text-sm font-bold text-amber-400 truncate">{topPerformer?.name ?? '—'}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="space-y-2">
          {sorted.map((member, i) => (
            <StaffCard key={member.id} member={member} rank={i + 1} teamRevenue={teamRevenue} />
          ))}
        </div>
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card p-4 border-[#7C5CFF]/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center flex-shrink-0">
              <Target size={16} className="text-[#7C5CFF]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">AI Coaching Insight</h3>
              {topPerformer ? (
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                <span className="text-[#F5F5F7] font-medium">{topPerformer.name}</span> leads the team with
                <span className="text-[#17C5B0] font-medium"> {formatCents(rev(topPerformer))}</span> in sales — {topShare}% of total revenue.
                {sorted.length > 1 && <> {sorted[sorted.length - 1].name} has the most room to grow — a mentoring shift could lift overall ticket size.</>}
              </p>
              ) : (
              <p className="text-xs text-[#A1A1A8]/50 mt-1">No staff data available yet.</p>
              )}
            </div>
          </div>
        </div>
      </ScrollReveal>
    </div>
    </DataPageSkeleton>
  )
}
