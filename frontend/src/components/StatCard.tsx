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
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="stat-label">{label}</p>
          <p className="stat-value">{value}</p>
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={clsx('p-2 rounded-lg bg-slate-800/60', iconColor)}>
            <Icon size={20} />
          </div>
        )}
      </div>
      {change && (
        <div className="mt-3 flex items-center gap-1.5">
          <span
            className={clsx('text-xs font-semibold', {
              'text-emerald-400': changeType === 'positive',
              'text-red-400': changeType === 'negative',
              'text-slate-400': changeType === 'neutral',
            })}
          >
            {change}
          </span>
          <span className="text-xs text-slate-500">vs prior 30d</span>
        </div>
      )}
    </div>
  )
}
