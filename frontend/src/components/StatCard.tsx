import { clsx } from 'clsx'
import type { LucideIcon } from 'lucide-react'

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
  iconColor = 'text-meridian-400',
  subtitle,
}: StatCardProps) {
  return (
    <div className="card p-4 sm:p-5">
      <div className="flex items-start justify-between">
        <div className="space-y-1 min-w-0">
          <p className="stat-label truncate">{label}</p>
          <p className="text-lg sm:text-2xl font-bold text-white tracking-tight">{value}</p>
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={clsx('p-1.5 sm:p-2 rounded-lg bg-slate-800/60 flex-shrink-0', iconColor)}>
            <Icon size={16} className="sm:w-5 sm:h-5" />
          </div>
        )}
      </div>
      {change && (
        <div className="mt-2 sm:mt-3 flex items-center gap-1.5">
          <span
            className={clsx('text-xs font-semibold', {
              'text-emerald-400': changeType === 'positive',
              'text-red-400': changeType === 'negative',
              'text-slate-400': changeType === 'neutral',
            })}
          >
            {change}
          </span>
          <span className="text-xs text-slate-500 hidden sm:inline">vs prior 30d</span>
        </div>
      )}
    </div>
  )
}
