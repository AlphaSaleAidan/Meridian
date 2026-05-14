import { clsx } from 'clsx'
import { Star, HelpCircle, Truck, XCircle, ArrowUpRight } from 'lucide-react'
import { generateMenuEngineering, type MenuEngItem, type MenuQuadrant } from '@/lib/agent-data'
import { formatCentsCompact } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'

const quadrantConfig: Record<MenuQuadrant, { label: string; color: string; bg: string; border: string; icon: typeof Star; desc: string }> = {
  star:      { label: 'Stars',       color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10', border: 'border-[#17C5B0]/15', icon: Star,       desc: 'High profit + high popularity' },
  puzzle:    { label: 'Puzzles',     color: 'text-[#7C5CFF]', bg: 'bg-[#7C5CFF]/10',  border: 'border-[#7C5CFF]/15',  icon: HelpCircle, desc: 'High profit but low popularity' },
  plowhorse: { label: 'Plowhorses', color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10', border: 'border-[#1A8FD6]/15', icon: Truck,      desc: 'Popular but low profit' },
  dog:       { label: 'Dogs',        color: 'text-[#A1A1A8]', bg: 'bg-[#A1A1A8]/10',  border: 'border-[#A1A1A8]/15',  icon: XCircle,    desc: 'Low profit + low popularity' },
}

function QuadrantCard({ quadrant, items }: { quadrant: MenuQuadrant; items: MenuEngItem[] }) {
  const cfg = quadrantConfig[quadrant]
  const Icon = cfg.icon
  return (
    <DashboardTiltCard className={clsx('card p-4', cfg.border)}>
      <div className="flex items-center gap-2 mb-3">
        <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center', cfg.bg)}>
          <Icon size={14} className={cfg.color} />
        </div>
        <div>
          <h4 className={clsx('text-xs font-semibold', cfg.color)}>{cfg.label}</h4>
          <p className="text-[9px] text-[#A1A1A8]/40">{cfg.desc}</p>
        </div>
        <span className="ml-auto text-[10px] font-mono text-[#A1A1A8]/40">{items.length} items</span>
      </div>
      <div className="space-y-2">
        {items.map(item => (
          <div key={item.name} className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-[#F5F5F7]">{item.name}</p>
              <p className="text-[10px] text-[#A1A1A8]/50">{item.monthlySales} sold/mo • {item.marginPct}% margin</p>
            </div>
            <span className="text-[10px] font-mono text-[#F5F5F7]">{formatCentsCompact(item.revenueCents)}</span>
          </div>
        ))}
      </div>
      {items.length > 0 && (
        <div className={clsx('mt-3 pt-2 border-t border-[#1F1F23] text-[10px]', cfg.color)}>
          <ArrowUpRight size={10} className="inline mr-1" />
          {items[0].recommendation}
        </div>
      )}
    </DashboardTiltCard>
  )
}

export default function MenuEngineeringPage() {
  const items = generateMenuEngineering()

  const stars = items.filter(i => i.quadrant === 'star')
  const puzzles = items.filter(i => i.quadrant === 'puzzle')
  const plowhorses = items.filter(i => i.quadrant === 'plowhorse')
  const dogs = items.filter(i => i.quadrant === 'dog')

  const avgPopularity = 100
  const avgProfit = 100

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Menu Engineering</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            BCG matrix analysis — every item classified by profitability and popularity
          </p>
        </div>
      </ScrollReveal>

      {/* Summary stats */}
      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {([
          { q: 'star' as const, items: stars },
          { q: 'puzzle' as const, items: puzzles },
          { q: 'plowhorse' as const, items: plowhorses },
          { q: 'dog' as const, items: dogs },
        ]).map(({ q, items: qItems }) => {
          const cfg = quadrantConfig[q]
          const rev = qItems.reduce((s, i) => s + i.revenueCents, 0)
          return (
            <StaggerItem key={q}>
              <DashboardTiltCard className="card p-4">
                <div className="flex items-center gap-2">
                  <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center', cfg.bg)}>
                    <cfg.icon size={16} className={cfg.color} />
                  </div>
                  <div>
                    <p className="stat-label">{cfg.label}</p>
                    <p className={clsx('text-lg font-bold font-mono', cfg.color)}>{qItems.length}</p>
                  </div>
                  <span className="ml-auto text-[10px] font-mono text-[#A1A1A8]/40">{formatCentsCompact(rev)}</span>
                </div>
              </DashboardTiltCard>
            </StaggerItem>
          )
        })}
      </StaggerContainer>

      {/* Scatter plot (CSS-based) */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Profitability vs Popularity Matrix</h3>
          <div className="relative w-full aspect-square max-w-[500px] mx-auto">
            {/* Quadrant backgrounds */}
            <div className="absolute inset-0 grid grid-cols-2 grid-rows-2">
              <div className="bg-[#7C5CFF]/5 border-r border-b border-[#1F1F23] flex items-center justify-center">
                <span className="text-[10px] text-[#7C5CFF]/30 font-medium">Puzzles</span>
              </div>
              <div className="bg-[#17C5B0]/5 border-b border-[#1F1F23] flex items-center justify-center">
                <span className="text-[10px] text-[#17C5B0]/30 font-medium">Stars</span>
              </div>
              <div className="bg-[#A1A1A8]/5 border-r border-[#1F1F23] flex items-center justify-center">
                <span className="text-[10px] text-[#A1A1A8]/20 font-medium">Dogs</span>
              </div>
              <div className="bg-[#1A8FD6]/5 flex items-center justify-center">
                <span className="text-[10px] text-[#1A8FD6]/30 font-medium">Plowhorses</span>
              </div>
            </div>
            {/* Axis labels */}
            <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[9px] text-[#A1A1A8]/40 font-mono">Popularity →</div>
            <div className="absolute -left-5 top-1/2 -translate-y-1/2 -rotate-90 text-[9px] text-[#A1A1A8]/40 font-mono">Profitability →</div>
            {/* Data points */}
            {items.map(item => {
              const x = Math.min(95, Math.max(5, (item.popularityIndex / 200) * 100))
              const y = Math.min(95, Math.max(5, 100 - (item.profitabilityIndex / 200) * 100))
              const cfg = quadrantConfig[item.quadrant]
              return (
                <div
                  key={item.name}
                  className="absolute w-3 h-3 rounded-full group cursor-default"
                  style={{ left: `${x}%`, top: `${y}%`, backgroundColor: cfg.color.includes('17C5B0') ? '#17C5B0' : cfg.color.includes('7C5CFF') ? '#7C5CFF' : cfg.color.includes('1A8FD6') ? '#1A8FD6' : '#A1A1A8', transform: 'translate(-50%, -50%)' }}
                >
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-[#0A0A0B] border border-[#1F1F23] rounded text-[10px] text-[#F5F5F7] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    {item.name} — {item.monthlySales}/mo, {item.marginPct}% margin
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </ScrollReveal>

      {/* Quadrant detail cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ScrollReveal variant="fadeUp" delay={0.15}><QuadrantCard quadrant="star" items={stars} /></ScrollReveal>
        <ScrollReveal variant="fadeUp" delay={0.2}><QuadrantCard quadrant="puzzle" items={puzzles} /></ScrollReveal>
        <ScrollReveal variant="fadeUp" delay={0.25}><QuadrantCard quadrant="plowhorse" items={plowhorses} /></ScrollReveal>
        <ScrollReveal variant="fadeUp" delay={0.3}><QuadrantCard quadrant="dog" items={dogs} /></ScrollReveal>
      </div>
    </div>
  )
}
