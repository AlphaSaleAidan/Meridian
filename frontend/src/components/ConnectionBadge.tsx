import { clsx } from 'clsx'
import { Wifi, WifiOff, Loader2, AlertCircle } from 'lucide-react'

interface Props {
  status: string
  provider?: string | null
  lastSync?: string | null
  onConnect?: () => void
}

const statusConfig: Record<string, { label: string; icon: typeof Wifi; color: string; dot: string }> = {
  connected: { label: 'Connected', icon: Wifi, color: 'text-[#4FE3C1]', dot: 'bg-[#4FE3C1]' },
  syncing: { label: 'Syncing', icon: Loader2, color: 'text-amber-400', dot: 'bg-amber-400' },
  error: { label: 'Error', icon: AlertCircle, color: 'text-red-400', dot: 'bg-red-400' },
  pending: { label: 'Pending', icon: Loader2, color: 'text-[#A1A1A8]', dot: 'bg-[#A1A1A8]' },
  disconnected: { label: 'Disconnected', icon: WifiOff, color: 'text-[#A1A1A8]/50', dot: 'bg-[#A1A1A8]/50' },
}

export default function ConnectionBadge({ status, provider, onConnect }: Props) {
  const config = statusConfig[status] || statusConfig.disconnected
  const Icon = config.icon

  return (
    <div className="inline-flex items-center gap-2">
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#111113] border border-[#1F1F23]">
        <span className={clsx('w-2 h-2 rounded-full', config.dot, {
          'animate-pulse': status === 'syncing',
        })} />
        <Icon size={14} className={config.color} />
        <span className="text-xs font-medium text-[#A1A1A8]">
          {provider ? `${provider.charAt(0).toUpperCase() + provider.slice(1)} • ` : ''}{config.label}
        </span>
      </div>
      {onConnect && status !== 'connected' && (
        <button
          onClick={onConnect}
          className="px-3 py-1.5 text-xs font-medium text-[#F5F5F7] bg-[#1A8FD6] rounded-full hover:bg-[#1574B8] transition-colors duration-200"
        >
          Connect
        </button>
      )}
    </div>
  )
}
