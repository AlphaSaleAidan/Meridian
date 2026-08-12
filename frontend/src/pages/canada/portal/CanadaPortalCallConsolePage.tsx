// Canada SR portal — Call Console (admin or better). Live floor wall, call
// history with post-hoc processing, team callbacks, DNC manager, analytics.
// Nav hiding is not a guard: this page re-checks the tier itself and the
// backend enforces require_org_admin on every /api/dialer/admin endpoint.
import { useState } from 'react'
import { Activity, BarChart3, CalendarClock, CalendarDays, Headphones, ListChecks, PhoneOff } from 'lucide-react'
import { repTier, useSalesAuth } from '@/lib/sales-auth'
import { isCanadaAdmin } from '@/lib/canada-admins'
import { AdminLiveBoard } from '@/components/dialer/AdminLiveBoard'
import { AdminCallsTable } from '@/components/dialer/AdminCallsTable'
import { AdminAnalytics, AdminCallbacks, AdminDncPanel } from '@/components/dialer/AdminPanels'
import { AppointmentsCalendar } from '@/components/dialer/AppointmentsCalendar'

type Tab = 'live' | 'calls' | 'calendar' | 'callbacks' | 'dnc' | 'analytics'

const TABS: { id: Tab; label: string; icon: typeof Activity }[] = [
  { id: 'live', label: 'Live board', icon: Activity },
  { id: 'calls', label: 'Calls', icon: ListChecks },
  { id: 'calendar', label: 'Calendar', icon: CalendarDays },
  { id: 'callbacks', label: 'Callbacks', icon: CalendarClock },
  { id: 'dnc', label: 'DNC', icon: PhoneOff },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
]

export default function CanadaPortalCallConsolePage() {
  const { rep } = useSalesAuth()
  const [tab, setTab] = useState<Tab>('live')

  const admin = repTier(rep) === 'admin' || isCanadaAdmin(rep?.email)
  if (!admin) {
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-2">
        <Headphones size={22} className="mx-auto text-pm-canada-text-faint" />
        <p className="text-sm font-medium text-white">Admin access required</p>
        <p className="text-xs text-pm-canada-text-muted">
          The Call Console is limited to admin-level users.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-white flex items-center gap-2">
          <Headphones size={20} className="text-pm-accent" />
          Call Console
        </h1>
        <p className="text-xs text-pm-canada-text-muted mt-0.5">
          Watch the floor, process calls as they land, and manage callbacks and the DNC list.
        </p>
      </div>

      <div className="flex gap-1.5 flex-wrap border-b border-pm-canada-border pb-3">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              tab === id
                ? 'bg-pm-accent/10 text-pm-accent border border-pm-accent/30'
                : 'text-pm-canada-text-muted border border-transparent hover:text-white hover:border-pm-canada-border'
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'live' && <AdminLiveBoard />}
      {tab === 'calls' && <AdminCallsTable />}
      {tab === 'calendar' && <AppointmentsCalendar admin />}
      {tab === 'callbacks' && <AdminCallbacks />}
      {tab === 'dnc' && <AdminDncPanel />}
      {tab === 'analytics' && <AdminAnalytics />}
    </div>
  )
}
