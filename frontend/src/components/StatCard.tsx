import { clsx } from 'clsx'
import type { LucideIcon } from 'lucide-react'
import DashboardTiltCard from './DashboardTiltCard'

interface StatCardProps {
  label: string
  value: string
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  icon?: LucideIcon
  iconColor?: string
  subtitle?: string
}

export default function StatCard({
  label,
  value,
  change,
  changeType = 'neutral',
  icon: Icon,
  iconColor = 'text-[#1A8FD6]',
  subtitle,
}: StatCardProps) {
  return (
    <DashboardTiltCard className="card p-4 sm:p-5 group">
      <div className="flex items-start justify-between">
        <div className="space-y-1 min-w-0">
          <p className="stat-label truncate">{label}</p>
          <p className="text-lg sm:text-2xl font-bold text-[#F5F5F7] tracking-tight font-mono">
            {value}
          </p>
          {subtitle && <p className="text-xs text-[#A1A1A8]/60">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={clsx(
            'p-1.5 sm:p-2 rounded-lg bg-[#1F1F23]/60 flex-shrink-0 transition-all duration-300 group-hover:bg-[#1A8FD6]/10',
            iconColor
          )}>
            <Icon size={16} className="sm:w-5 sm:h-5 transition-transform duration-300 group-hover:scale-110" />
          </div>
        )}
      </div>
      {change && (
        <div className="mt-2 sm:mt-3 flex items-center gap-1.5">
          <span
            className={clsx('text-xs font-semibold font-mono', {
              'text-[#17C5B0]': changeType === 'positive',
              'text-red-400': changeType === 'negative',
              'text-[#A1A1A8]': changeType === 'neutral',
            })}
          >
            {change}
          </span>
          <span className="text-xs text-[#A1A1A8]/50 hidden sm:inline">vs prior 30d</span>
        </div>
      )}
    </DashboardTiltCard>
  )
}
