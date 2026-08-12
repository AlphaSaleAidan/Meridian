// Booking calendar — the rep's upcoming demos, grouped by day (agenda view).
// Fed by dialer_appointments; each was created by a booking that also promoted
// the lead into the pipeline. Reps mark done / no-show / cancel here.
import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, CheckCircle2, Clock, UserX, XCircle } from 'lucide-react'
import { dialerApi, dialerAdminApi, type Appointment, type AppointmentStatus } from '@/lib/dialer-api'

function dayKey(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })
}

export function AppointmentsCalendar({ admin = false }: { admin?: boolean }) {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['dialer', admin ? 'admin-appointments' : 'appointments'],
    queryFn: () => (admin ? dialerAdminApi.appointments(30) : dialerApi.appointments(30)),
    refetchInterval: 30000,
  })

  const patch = useMutation({
    mutationFn: ({ id, status }: { id: string; status: AppointmentStatus }) =>
      dialerApi.patchAppointment(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dialer'] }),
  })

  const grouped = useMemo(() => {
    const rows = (data?.appointments ?? []).filter(a => a.status !== 'cancelled')
    const byDay = new Map<string, Appointment[]>()
    for (const a of rows) {
      const k = dayKey(a.scheduled_at)
      if (!byDay.has(k)) byDay.set(k, [])
      byDay.get(k)!.push(a)
    }
    return [...byDay.entries()]
  }, [data])

  if (isLoading) {
    return <p className="text-sm text-pm-canada-text-muted py-10 text-center">Loading your calendar…</p>
  }
  if (grouped.length === 0) {
    return (
      <div className="text-center py-14 space-y-1.5">
        <CalendarDays size={22} className="mx-auto text-pm-canada-text-faint" />
        <p className="text-sm text-pm-canada-text-muted">No demos booked yet.</p>
        <p className="text-2xs text-pm-canada-text-faint">Book one from a call and it lands here — and in your pipeline.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {grouped.map(([day, appts]) => (
        <div key={day}>
          <p className="text-2xs uppercase tracking-[0.14em] text-pm-canada-text-faint mb-2">{day}</p>
          <div className="space-y-2">
            {appts.map(a => (
              <div key={a.id} className="bg-pm-canada-surface border border-pm-canada-border rounded-xl px-4 py-3 flex items-center gap-3">
                <div className="text-center shrink-0 w-14">
                  <p className="text-sm font-semibold text-white tabular-nums">
                    {new Date(a.scheduled_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                  </p>
                  <p className="text-2xs text-pm-canada-text-faint inline-flex items-center gap-0.5"><Clock size={9} />{a.duration_min}m</p>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-white truncate">{a.business_name || a.contact_name || a.phone_e164}</p>
                  <p className="text-2xs text-pm-canada-text-faint truncate">
                    {a.title}{admin && a.rep_name ? ` · ${a.rep_name}` : ''}{a.status === 'completed' ? ' · done' : a.status === 'no_show' ? ' · no-show' : ''}
                  </p>
                </div>
                {a.status === 'booked' && (
                  <div className="flex items-center gap-1 shrink-0">
                    <IconBtn label="Mark done" tone="accent" onClick={() => patch.mutate({ id: a.id, status: 'completed' })}><CheckCircle2 size={15} /></IconBtn>
                    <IconBtn label="No-show" tone="amber" onClick={() => patch.mutate({ id: a.id, status: 'no_show' })}><UserX size={15} /></IconBtn>
                    <IconBtn label="Cancel" tone="red" onClick={() => patch.mutate({ id: a.id, status: 'cancelled' })}><XCircle size={15} /></IconBtn>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function IconBtn({ children, label, tone, onClick }: {
  children: React.ReactNode; label: string; tone: 'accent' | 'amber' | 'red'; onClick: () => void
}) {
  const tones = {
    accent: 'text-pm-canada-text-faint hover:text-pm-accent hover:bg-pm-accent/10',
    amber: 'text-pm-canada-text-faint hover:text-pm-amber-orange hover:bg-pm-amber-orange/10',
    red: 'text-pm-canada-text-faint hover:text-red-400 hover:bg-red-500/10',
  }
  return (
    <button onClick={onClick} aria-label={label} title={label}
      className={`p-1.5 rounded-md transition-colors ${tones[tone]}`}>
      {children}
    </button>
  )
}
