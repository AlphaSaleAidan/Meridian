import { TrendingUp, DollarSign, Lightbulb, BarChart3, Bell, Zap } from 'lucide-react'
import TiltCard from './TiltCard'
import ScrollReveal from './ScrollReveal'

const features = [
  {
    icon: DollarSign,
    title: 'Money Left on the Table',
    desc: 'AI surfaces pricing gaps and upsell opportunities with exact dollar amounts.',
    span: 'md:col-span-2 md:row-span-2',
    visual: (
      <div className="mt-4 rounded-lg bg-[#0A0A0B] border border-[#1F1F23] p-4 font-mono text-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[#A1A1A8]">Monthly opportunity</span>
          <span className="text-[#1A8FD6] font-semibold">CA$3,229</span>
        </div>
        <div className="space-y-2">
          {[
            { label: 'Bundle pricing', value: 'CA$1,228', pct: 38 },
            { label: 'Peak hour staffing', value: 'CA$994', pct: 31 },
            { label: 'Menu optimization', value: 'CA$1,007', pct: 31 },
          ].map(item => (
            <div key={item.label}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#A1A1A8]">{item.label}</span>
                <span className="text-[#F5F5F7]">{item.value}</span>
              </div>
              <div className="h-1 bg-[#1F1F23] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#1A8FD6] rounded-full"
                  style={{ width: `${item.pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    icon: TrendingUp,
    title: 'Revenue Intelligence',
    desc: 'Real-time tracking with hourly, daily, and weekly breakdowns.',
    span: 'md:col-span-1',
    visual: (
      <div className="mt-4 flex items-end gap-1 h-16">
        {[35, 42, 28, 56, 48, 62, 55, 70, 65, 78, 72, 85].map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm bg-[#1A8FD6]"
            style={{ height: `${h}%`, opacity: 0.3 + (i / 12) * 0.7 }}
          />
        ))}
      </div>
    ),
  },
  {
    icon: BarChart3,
    title: 'Forecasting',
    desc: 'AI predictions with confidence intervals for the next 14 days.',
    span: 'md:col-span-1',
    visual: (
      <div className="mt-4 font-mono text-xs">
        <div className="flex items-center gap-2 text-[#17C5B0]">
          <span>↑ 12.4%</span>
          <span className="text-[#A1A1A8]">vs last week</span>
        </div>
        <div className="text-2xl font-semibold text-[#F5F5F7] mt-1">CA$19,706</div>
        <div className="text-[#A1A1A8]">projected next 7d</div>
      </div>
    ),
  },
  {
    icon: Lightbulb,
    title: 'Actionable Insights',
    desc: 'Data-backed recommendations on staffing, products, and promotions.',
    span: 'md:col-span-1',
    visual: (
      <div className="mt-4 space-y-2">
        {['Increase latte price by CA$0.69', 'Add morning pastry bundle'].map(text => (
          <div key={text} className="flex items-center gap-2 text-xs bg-[#0A0A0B] rounded-md px-3 py-2 border border-[#1F1F23]">
            <div className="w-1.5 h-1.5 rounded-full bg-[#1A8FD6] flex-shrink-0" />
            <span className="text-[#A1A1A8]">{text}</span>
          </div>
        ))}
      </div>
    ),
  },
  {
    icon: Bell,
    title: 'Smart Alerts',
    desc: 'Get notified when metrics deviate from your established patterns.',
    span: 'md:col-span-1',
    visual: (
      <div className="mt-4 text-xs space-y-2">
        <div className="flex items-center gap-2 text-[#F5F5F7]">
          <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          <span>Revenue 18% below Tuesday avg</span>
        </div>
        <div className="flex items-center gap-2 text-[#A1A1A8]">
          <div className="w-2 h-2 rounded-full bg-[#17C5B0]" />
          <span>Espresso sales up 24% this week</span>
        </div>
      </div>
    ),
  },
  {
    icon: Zap,
    title: '60-Second Setup',
    desc: 'One-click Square, Clover, or Toast connection. No API keys, no config files.',
    span: 'md:col-span-2 md:col-start-2',
    visual: (
      <div className="mt-4 flex items-center gap-4">
        {['Connect', 'Analyze', 'Profit'].map((step, i) => (
          <div key={step} className="flex items-center gap-2">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
              i === 2 ? 'bg-[#1A8FD6] text-white' : 'bg-[#1F1F23] text-[#A1A1A8]'
            }`}>
              {i + 1}
            </div>
            <span className="text-xs text-[#A1A1A8]">{step}</span>
            {i < 2 && <div className="w-8 h-px bg-[#1F1F23]" />}
          </div>
        ))}
      </div>
    ),
  },
]

export default function CanadaBentoGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {features.map((f, i) => (
        <ScrollReveal key={f.title} delay={i * 0.08} className={f.span}>
          <TiltCard
            className="h-full bg-[#111113] border border-[#1F1F23] rounded-xl p-6 hover:border-[#2A2A30] transition-colors duration-300"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <f.icon size={16} className="text-[#1A8FD6]" />
              </div>
              <h3 className="text-[#F5F5F7] font-medium text-sm">{f.title}</h3>
            </div>
            <p className="text-[#A1A1A8] text-xs leading-relaxed">{f.desc}</p>
            {f.visual}
          </TiltCard>
        </ScrollReveal>
      ))}
    </div>
  )
}
