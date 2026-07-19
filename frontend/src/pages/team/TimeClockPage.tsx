// Time Clock — scheduled vs ACTUAL hours with variance highlighting (1b).
// Owners/managers with edit_punches can correct a punch (audited server-side).
import { useState } from 'react'
import { Clock, AlertTriangle } from 'lucide-react'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useApi } from '@/hooks/useApi'
import { teamApi, type HoursRow } from '@/lib/team-api'
import { LoadingPage, ErrorState } from '@/components/LoadingState'

// Monday of the current week as YYYY-MM-DD (matches the scheduler's week model).
function currentWeekStart(): string {
  const d = new Date()
  const day = (d.getDay() + 6) % 7 // 0 = Monday
  d.setDate(d.getDate() - day)
  return d.toISOString().slice(0, 10)
}

function VarianceBadge({ v }: { v: number }) {
  if (Math.abs(v) < 0.25) return <span className="text-[#A1A1A8] text-sm">on track</span>
  const over = v > 0
  return (
    <span className={`inline-flex items-center gap-1 text-sm font-medium ${over ? 'text-amber-400' : 'text-blue-300'}`}>
      <AlertTriangle size={12} />
      {over ? '+' : ''}{v.toFixed(1)}h {over ? 'over' : 'under'}
    </span>
  )
}

export default function TimeClockPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const [week, setWeek] = useState(currentWeekStart())

  const state = useApi(
    () => (orgId && !isDemo ? teamApi.hoursSummary(orgId, week) : Promise.resolve({ week_start: week, rows: [] as HoursRow[] })),
    [orgId, isDemo, week],
  )

  if (isDemo) return <div className="p-6 text-[#A1A1A8]">Time clock is available once your account is connected.</div>
  if (state.loading) return <LoadingPage />
  if (state.error) return <ErrorState message={state.error} onRetry={state.refetch} />

  const rows = state.data?.rows || []
  const totalSched = rows.reduce((s, r) => s + r.scheduled_hours, 0)
  const totalActual = rows.reduce((s, r) => s + r.actual_hours, 0)

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-4xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white flex items-center gap-2">
            <Clock size={18} className="text-[#17C5B0]" /> Time Clock
          </h1>
          <p className="text-sm text-[#A1A1A8]">Scheduled vs actual hours worked this week.</p>
        </div>
        <input type="date" value={week} onChange={e => setWeek(e.target.value)}
          className="bg-[#111114] border border-[#26262C] rounded-lg px-3 py-1.5 text-sm text-white" />
      </div>

      <div className="grid grid-cols-2 gap-3 max-w-md">
        <div className="card p-4">
          <div className="text-xs text-[#A1A1A8] uppercase">Scheduled</div>
          <div className="text-2xl font-semibold text-white">{totalSched.toFixed(1)}h</div>
        </div>
        <div className="card p-4">
          <div className="text-xs text-[#A1A1A8] uppercase">Actual</div>
          <div className="text-2xl font-semibold text-white">{totalActual.toFixed(1)}h</div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="grid grid-cols-4 gap-2 px-4 py-2 text-xs uppercase tracking-wide text-[#A1A1A8] border-b border-[#1F1F23]">
          <div>Employee</div><div className="text-right">Scheduled</div>
          <div className="text-right">Actual</div><div className="text-right">Variance</div>
        </div>
        {rows.length === 0 && <div className="px-4 py-6 text-sm text-[#A1A1A8]">No hours recorded for this week.</div>}
        {rows.map(r => (
          <div key={r.employee_id}
            className={`grid grid-cols-4 gap-2 px-4 py-3 items-center border-b border-[#141418] last:border-0 ${r.variance_flag ? 'bg-amber-400/[0.03]' : ''}`}>
            <div className="text-sm text-white">{r.name}</div>
            <div className="text-sm text-[#A1A1A8] text-right">{r.scheduled_hours.toFixed(1)}h</div>
            <div className="text-sm text-white text-right">{r.actual_hours.toFixed(1)}h</div>
            <div className="text-right"><VarianceBadge v={r.variance_hours} /></div>
          </div>
        ))}
      </div>
      <p className="text-xs text-[#A1A1A8]/70">
        Punch corrections are audited: every edit records who changed it and why.
      </p>
    </div>
  )
}
