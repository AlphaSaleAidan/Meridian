import { clsx } from 'clsx'
import { Wifi, WifiOff, Loader2, AlertCircle } from 'lucide-react'

interface Props {
  status: string
  provider?: string | null
  lastSync?: string | null
}

const statusConfig: Record<string, { label: string; icon: typeof Wifi; color: string; dot: string }> = {
  connected: { label: 'Connected', icon: Wifi, color: 'text-emerald-400', dot: 'bg-emerald-400' },
  syncing: { label: 'Syncing', icon: Loader2, color: 'text-amber-400', dot: 'bg-amber-400' },
  error: { label: 'Error', icon: AlertCircle, color: 'text-red-400', dot: 'bg-red-400' },
  pending: { label: 'Pending', icon: Loader2, color: 'text-slate-400', dot: 'bg-slate-400' },
  disconnected: { label: 'Disconnected', icon: WifiOff, color: 'text-slate-500', dot: 'bg-slate-500' },
}

export default function ConnectionBadge({ status, provider }: Props) {
  const config = statusConfig[status] || statusConfig.disconnected
  const Icon = config.icon

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/60 border border-slate-700/40">
      <span className={clsx('w-2 h-2 rounded-full', config.dot, {
        'animate-pulse': status === 'syncing',
      })} />
      <Icon size={14} className={config.color} />
      <span className="text-xs font-medium text-slate-300">
        {provider ? `${provider.charAt(0).toUpperCase() + provider.slice(1)} • ` : ''}{config.label}
      </span>
    </div>
  )
}
