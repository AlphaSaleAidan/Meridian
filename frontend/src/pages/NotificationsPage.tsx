import { clsx } from 'clsx'
import { Bell, AlertTriangle, Info, Zap, FileText } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatRelative } from '@/lib/format'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

const priorityConfig: Record<string, { color: string; dot: string }> = {
  urgent: { color: 'text-red-400', dot: 'bg-red-400' },
  high: { color: 'text-amber-400', dot: 'bg-amber-400' },
  normal: { color: 'text-blue-400', dot: 'bg-blue-400' },
  low: { color: 'text-slate-400', dot: 'bg-slate-500' },
}

const sourceIcons: Record<string, typeof Bell> = {
  event: Zap,
  insight: Info,
  alert: AlertTriangle,
  report: FileText,
}

export default function NotificationsPage() {
  const notifs = useApi(() => api.notifications(ORG_ID, 50), [])

  if (notifs.loading) return <LoadingPage />
  if (notifs.error) return <ErrorState message={notifs.error} onRetry={notifs.refetch} />

  const data = notifs.data!
  const unread = data.notifications.filter(n => !n.acknowledged_at).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Notifications</h1>
        <p className="text-sm text-slate-400 mt-1">
          {data.total} notifications • {unread} unread
        </p>
      </div>

      {/* Notifications List */}
      {data.notifications.length > 0 ? (
        <div className="space-y-2">
          {data.notifications.map(n => {
            const pConfig = priorityConfig[n.priority] || priorityConfig.normal
            const Icon = sourceIcons[n.source_type || ''] || Bell
            const isRead = !!n.acknowledged_at

            return (
              <div
                key={n.id}
                className={clsx(
                  'card p-4 transition-all duration-200',
                  !isRead && 'border-l-2 border-l-meridian-600 bg-meridian-950/5'
                )}
              >
                <div className="flex items-start gap-3">
                  <div className={clsx('p-2 rounded-lg bg-slate-800/60 flex-shrink-0', pConfig.color)}>
                    <Icon size={16} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className={clsx('text-sm font-medium', isRead ? 'text-slate-300' : 'text-white')}>
                        {n.title}
                      </h4>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {!isRead && (
                          <span className={clsx('w-2 h-2 rounded-full', pConfig.dot)} />
                        )}
                        <span className="text-xs text-slate-500 hidden sm:inline">{formatRelative(n.created_at)}</span>
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">{n.body}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={clsx('badge', {
                        'badge-red': n.priority === 'urgent',
                        'badge-amber': n.priority === 'high',
                        'badge-blue': n.priority === 'normal',
                      })}>
                        {n.priority}
                      </span>
                      <span className="text-xs text-slate-600">{n.status}</span>
                      <span className="text-xs text-slate-500 sm:hidden ml-auto">{formatRelative(n.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <EmptyState
          title="No notifications"
          description="You'll receive alerts about revenue changes, inventory issues, and AI insights here."
        />
      )}
    </div>
  )
}
