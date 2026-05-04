import { MeridianEmblem } from './MeridianLogo'

interface AnalyzingDataStateProps {
  title?: string
  description?: string
  compact?: boolean
}

export default function AnalyzingDataState({
  title = 'We are analyzing your data',
  description = 'Our AI agents are processing your POS transactions and generating insights. Check back in about an hour!',
  compact = false,
}: AnalyzingDataStateProps) {
  return (
    <div className={compact ? 'py-8' : 'py-16'}>
      <div className="flex flex-col items-center gap-4 text-center max-w-sm mx-auto">
        <MeridianEmblem size={compact ? 56 : 80} animate />
        <div className="space-y-2">
          <p className="text-sm font-semibold text-[#F5F5F7]">{title}</p>
          <p className="text-xs text-[#A1A1A8]/60 leading-relaxed">{description}</p>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-[#17C5B0] font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-[#17C5B0] animate-pulse" />
          Agents running
        </div>
      </div>
    </div>
  )
}

export function AnalyzingSection({
  title = 'Analyzing...',
  description = 'This section will populate once enough data has been processed.',
}: { title?: string; description?: string }) {
  return (
    <div className="card p-6">
      <div className="flex items-center gap-4">
        <MeridianEmblem size={40} animate />
        <div>
          <p className="text-sm font-medium text-[#F5F5F7]">{title}</p>
          <p className="text-xs text-[#A1A1A8]/50 mt-0.5">{description}</p>
        </div>
      </div>
    </div>
  )
}
