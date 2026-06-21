import { Clock, Wifi } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import ScrollReveal from '@/components/ScrollReveal'

interface AwaitingDataBannerProps {
  posConnected: boolean
  label: string
}

export default function AwaitingDataBanner({ posConnected, label }: AwaitingDataBannerProps) {
  const location = useLocation()
  const settingsPath = location.pathname.startsWith('/canada/merchant')
    ? '/canada/merchant/settings'
    : location.pathname.startsWith('/canada/demo')
    ? '/canada/demo/settings'
    : location.pathname.startsWith('/canada')
    ? '/canada/dashboard/settings'
    : '/app/settings'

  return (
    <ScrollReveal variant="fadeUp">
      <div className="card p-3 border-[#1A8FD6]/15 flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
          <Clock size={14} className="text-[#1A8FD6]" />
        </div>
        <p className="text-xs text-[#A1A1A8] leading-relaxed flex-1">
          {posConnected
            ? `Collecting transactions — your ${label} fills in as sales are recorded over the coming days.`
            : `This is a live preview of your ${label}. Connect your POS and it fills in automatically as transactions are recorded.`}
        </p>
        {!posConnected && (
          <Link
            to={settingsPath}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#00d4aa] text-[#0A0A0B] text-[11px] font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all flex-shrink-0 whitespace-nowrap"
          >
            <Wifi size={12} /> Connect POS
          </Link>
        )}
      </div>
    </ScrollReveal>
  )
}
