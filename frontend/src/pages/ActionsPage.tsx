import { Zap } from 'lucide-react'
import ScrollReveal from '@/components/ScrollReveal'
import Top3ActionsPanel from '@/components/Top3ActionsPanel'
import DataPageSkeleton from '@/components/DataPageSkeleton'

export default function ActionsPage() {
  return (
    <DataPageSkeleton title="Top Actions" layout="grid">
      <div className="space-y-6">
        <ScrollReveal variant="fadeUp">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Top Actions Today</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              The highest-impact moves for your business, refreshed automatically — act on them or pass.
            </p>
          </div>
        </ScrollReveal>

        <ScrollReveal variant="fadeUp" delay={0.05}>
          <Top3ActionsPanel />
        </ScrollReveal>

        <ScrollReveal variant="fadeUp" delay={0.15}>
          <div className="card p-4 border-[#1A8FD6]/10">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
                <Zap size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7]">How these are chosen</h3>
                <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                  Two <span className="text-[#17C5B0] font-medium">instant wins</span> rotate in every day — low-effort
                  pricing, staffing and menu moves that drive immediate revenue. One{' '}
                  <span className="text-[#d4af37] font-medium">strategic move</span> refreshes weekly for bigger changes
                  that take more time to roll out. The Action Prioritizer ranks every recommendation by ROI potential,
                  effort, confidence and time sensitivity. Reject anything that doesn't fit and the next best move takes
                  its place.
                </p>
              </div>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </DataPageSkeleton>
  )
}
