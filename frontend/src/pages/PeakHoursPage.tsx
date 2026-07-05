import { Clock, TrendingUp, Users, Zap } from 'lucide-react'
import { generatePeakHourHeatmap, type PeakHourCell } from '@/lib/agent-data'
import PeakHoursHeatmap from '@/components/PeakHoursHeatmap'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { isUuid } from '@/lib/schedule-api'
import { useApi } from '@/hooks/useApi'
import { LoadingPage, ErrorState } from '@/components/LoadingState'

const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const dayFull = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const hourLabels = Array.from({ length: 24 }, (_, i) => {
  if (i === 0) return '12a'
  if (i < 12) return `${i}a`
  if (i === 12) return '12p'
  return `${i - 12}p`
})

export default function PeakHoursPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const posConnected = !!org?.pos_connected
  // Real merchants: the SAME per-(day, hour) POS source the Schedule page's
  // Auto-fill and Expected-traffic use (/api/schedule/peak-hours — SQL over
  // real transactions). Previously this page fetched the hour-of-day-only
  // /revenue/hourly aggregate and FABRICATED the weekday axis with a synthetic
  // day factor, so every day (e.g. Sunday) was a scaled clone of the same
  // curve and disagreed with the schedule pillar.
  const peakData = useApi(
    () => (isDemo || !isUuid(orgId))
      ? Promise.resolve(null)
      : api.schedulePeakHours(orgId, 8),
    [orgId, isDemo],
  )

  // Before a POS is connected the endpoint has nothing to aggregate. Rather
  // than a generic scaffold, render the heatmap *shell* (empty cells) so the
  // merchant sees exactly what will fill in as transactions roll in. Only
  // surface loading / error states once a POS is actually connected.
  if (!isDemo && posConnected && peakData.loading) return <LoadingPage />
  if (!isDemo && posConnected && peakData.error) return <ErrorState message={peakData.error} onRetry={peakData.refetch} />

  let cells: PeakHourCell[]
  if (isDemo) {
    cells = generatePeakHourHeatmap()
  } else {
    const weeks = Math.max(1, peakData.data?.weeks ?? 8)
    cells = (peakData.data?.peaks ?? []).map(p => ({
      day: p.day,
      hour: p.hour,
      intensity: p.intensity,
      // txn_count / revenue_cents are totals over the analyzed weeks —
      // divide so the stats below read as honest weekly figures.
      transactions: Math.round(p.txn_count / weeks),
      revenue: Math.round(p.revenue_cents / weeks),
    }))
  }

  const peakCell = cells.length ? cells.reduce((max, c) => c.intensity > max.intensity ? c : max, cells[0]) : null
  const totalTxns = cells.reduce((s, c) => s + c.transactions, 0)
  const morningRevenue = cells.filter(c => c.hour >= 7 && c.hour < 10).reduce((s, c) => s + c.revenue, 0)
  const totalRevenue = cells.reduce((s, c) => s + c.revenue, 0)
  const morningPct = totalRevenue > 0 ? Math.round(morningRevenue / totalRevenue * 100) : 0
  // Real merchant with no transaction signal yet — show the heatmap shell.
  const awaitingData = !isDemo && cells.length === 0

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Peak Hours</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Powered by Peak Hour Optimizer agent • Transaction density analysis
          </p>
        </div>
      </ScrollReveal>

      {awaitingData && (
        <ScrollReveal variant="fadeUp">
          <div className="card p-3 border-[#1A8FD6]/15 flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
              <Clock size={14} className="text-[#1A8FD6]" />
            </div>
            <p className="text-xs text-[#A1A1A8] leading-relaxed">
              {posConnected
                ? 'Collecting transactions — your heatmap will light up as sales are recorded over the coming days.'
                : 'Connect your POS to start filling this heatmap. Each cell brightens as transactions are recorded for that day and hour.'}
            </p>
          </div>
        </ScrollReveal>
      )}

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <Zap size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">Peak Hour</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{peakCell ? hourLabels[peakCell.hour] : '—'}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <Clock size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Peak Day</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{peakCell ? dayNames[peakCell.day] : '—'}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                <TrendingUp size={16} className="text-[#7C5CFF]" />
              </div>
              <div>
                <p className="stat-label">AM Revenue</p>
                <p className="text-lg font-bold text-[#7C5CFF] font-mono">{morningPct}%</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <Users size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">Weekly Txns</p>
                <p className="text-lg font-bold text-amber-400 font-mono">{totalTxns.toLocaleString()}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <PeakHoursHeatmap cells={cells} />
      </ScrollReveal>

      {!awaitingData && (
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card p-4 border-[#17C5B0]/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
              <Zap size={16} className="text-[#17C5B0]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Peak Hour Optimizer Recommendation</h3>
              {isDemo ? (
                <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                  Your <span className="text-[#F5F5F7] font-medium">7-9AM window</span> generates {morningPct}% of daily revenue
                  but current staffing is 1 person below optimal. Adding 1 staff member during this window would
                  reduce average queue time from 4.2 to 2.1 minutes and recover an estimated
                  <span className="text-[#17C5B0] font-medium"> $520/month</span> in lost walkout revenue.
                  <span className="text-[#A1A1A8]/50"> (Confidence: 88%)</span>
                </p>
              ) : (
                // Real merchants only see numbers derived from their POS
                // transactions — no invented dollars or confidence figures.
                <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                  Your busiest window is{' '}
                  <span className="text-[#F5F5F7] font-medium">
                    {peakCell ? `${dayFull[peakCell.day]} around ${hourLabels[peakCell.hour]}` : '—'}
                  </span>
                  {morningPct > 0 && (
                    <> and the 7-9AM window generates <span className="text-[#17C5B0] font-medium">{morningPct}%</span> of weekly revenue</>
                  )}
                  . Staff your strongest people into these windows — the Schedule page&apos;s Auto-fill
                  optimizes against this same demand signal.
                </p>
              )}
            </div>
          </div>
        </div>
      </ScrollReveal>
      )}
    </div>
  )
}
