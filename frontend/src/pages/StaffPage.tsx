import { clsx } from 'clsx'
import {
  Users, TrendingUp, TrendingDown, Minus, Award, Target,
  DollarSign,
} from 'lucide-react'
import { generateStaffPerformance, type StaffMember } from '@/lib/agent-data'
import { formatCents } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import AnalyzingDataState from '@/components/AnalyzingDataState'
import { useIsDemo } from '@/hooks/useOrg'

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'up') return <TrendingUp size={12} className="text-[#17C5B0]" />
  if (trend === 'down') return <TrendingDown size={12} className="text-red-400" />
  return <Minus size={12} className="text-[#A1A1A8]/40" />
}

function StaffCard({ member, rank }: { member: StaffMember; rank: number }) {
  const isTop = rank <= 2

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
            <TrendIcon trend={member.trend} />
            {rank === 1 && <Award size={14} className="text-amber-400" />}
          </div>
          <p className="text-xs text-[#A1A1A8]/50">{member.role}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-sm font-bold font-mono text-[#F5F5F7]">{formatCents(member.revenuePerHour)}</p>
          <p className="text-[10px] text-[#A1A1A8]/40">rev/hour</p>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2 text-center">
        <div>
          <p className="text-[10px] text-[#A1A1A8]/40">Avg Ticket</p>
          <p className="text-xs font-bold font-mono text-[#F5F5F7]">{formatCents(member.avgTicketCents)}</p>
        </div>
        <div>
          <p className="text-[10px] text-[#A1A1A8]/40">Txns/Shift</p>
          <p className="text-xs font-bold font-mono text-[#F5F5F7]">{member.transactionsPerShift}</p>
        </div>
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
      </div>
    </div>
  )
}

export default function StaffPage() {
  const isDemo = useIsDemo()
  const staff = generateStaffPerformance()

  if (!isDemo) {
    return (
      <div className="space-y-6">
        <ScrollReveal variant="fadeUp">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Staff Performance</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              Powered by Staff Performance Analyst agent
            </p>
          </div>
        </ScrollReveal>
        <AnalyzingDataState
          title="Analyzing staff performance"
          description="Our AI is correlating transaction data with shift schedules to rank your team by revenue per hour, upsell rates, and customer satisfaction."
        />
      </div>
    )
  }

  const avgRevPerHour = Math.round(staff.reduce((s, m) => s + m.revenuePerHour, 0) / staff.length)
  const avgUpsell = Math.round(staff.reduce((s, m) => s + m.upsellRate, 0) / staff.length)
  const topPerformer = staff[0]

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Staff Performance</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Powered by Staff Performance Analyst agent • Ranked by revenue per hour
          </p>
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
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
                <p className="stat-label">Avg Rev/Hour</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{formatCents(avgRevPerHour)}</p>
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
                <p className="stat-label">Avg Upsell</p>
                <p className="text-lg font-bold text-[#7C5CFF] font-mono">{avgUpsell}%</p>
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
                <p className="text-sm font-bold text-amber-400 truncate">{topPerformer.name}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="space-y-2">
          {staff.map((member, i) => (
            <StaffCard key={member.id} member={member} rank={i + 1} />
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
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                <span className="text-[#F5F5F7] font-medium">{topPerformer.name}</span> achieves a {topPerformer.upsellRate}% upsell rate —
                <span className="text-[#17C5B0] font-medium"> {Math.round(topPerformer.upsellRate / avgUpsell * 100 - 100)}% above team average</span>.
                Key differentiator: suggestive selling during morning rush when customers are time-constrained but open to add-ons.
                Recommended: Pair with {staff[staff.length - 1].name} for mentoring shifts to transfer technique.
                <span className="text-[#A1A1A8]/50"> (Confidence: 82%)</span>
              </p>
            </div>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
