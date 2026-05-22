import { useState, useEffect, useCallback, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Wifi } from 'lucide-react'
import { MeridianEmblem } from './MeridianLogo'
import { useAuth } from '@/lib/auth'

const PROCESSING_DURATION = 1200 // 20 minutes in seconds

const PROCESSING_KEYS = [
  { start: 'meridian_processing_start', done: 'meridian_processing_done' },
  { start: 'meridian_us_processing_start', done: 'meridian_us_processing_done' },
  { start: 'meridian_ca_processing_start', done: 'meridian_ca_processing_done' },
] as const

const TIPS = [
  'Revenue data updates every 15 minutes once your POS is connected.',
  'The Insights tab uses AI to detect anomalies in your sales patterns.',
  'Peak Hours analysis helps you optimize staffing for maximum profit.',
  'Product performance scores identify your top margin items.',
  'Customer segmentation helps you target the right audience.',
  'Forecasts use 30 days of data to predict future revenue trends.',
  'The Anomaly Detector catches unusual patterns before they cost you money.',
  'Staff performance tracking identifies your top performers.',
  'Menu Matrix analysis shows which items to promote, keep, or rethink.',
  'Set up cameras to unlock foot traffic and conversion analytics.',
]

function MiniRadar({ size = 32, label }: { size?: number; label?: string }) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <MeridianEmblem size={size} animate />
      {label && <span className="text-[9px] text-[#A1A1A8]/40 font-mono">{label}</span>}
    </div>
  )
}

function ConnectCTA() {
  const location = useLocation()
  const settingsPath = location.pathname.startsWith('/canada') ? '/canada/dashboard/settings' : '/app/settings'
  const [tipIdx, setTipIdx] = useState(() => Math.floor(Math.random() * TIPS.length))
  useEffect(() => {
    const i = setInterval(() => setTipIdx(p => (p + 1) % TIPS.length), 6000)
    return () => clearInterval(i)
  }, [])
  return (
    <div className="flex flex-col items-center gap-3 py-4">
      <div className="px-4 py-2 rounded-lg bg-[#111113] border border-[#1F1F23] max-w-xs text-center">
        <p className="text-[10px] text-[#7C5CFF] font-medium mb-0.5">Did you know?</p>
        <p className="text-[11px] text-[#A1A1A8]/70 leading-relaxed">{TIPS[tipIdx]}</p>
      </div>
      <Link
        to={settingsPath}
        className="flex items-center gap-2 px-4 py-2 bg-[#00d4aa] text-[#0A0A0B] text-xs font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
      >
        <Wifi size={14} /> Connect Your POS
      </Link>
    </div>
  )
}

function useProcessingState() {
  const getState = useCallback(() => {
    for (const { start, done } of PROCESSING_KEYS) {
      const startStr = localStorage.getItem(start)
      const doneStr = localStorage.getItem(done)
      if (startStr && doneStr !== '1') {
        const startTime = parseInt(startStr, 10)
        if (!isNaN(startTime)) {
          const elapsed = Math.floor((Date.now() - startTime) / 1000)
          return { active: true, elapsed, startKey: start, doneKey: done }
        }
      }
    }
    return { active: false, elapsed: 0, startKey: '', doneKey: '' }
  }, [])

  const [state, setState] = useState(getState)

  useEffect(() => {
    if (!state.active) return
    const id = setInterval(() => {
      const next = getState()
      if (!next.active) {
        clearInterval(id)
        setState(next)
        return
      }
      if (next.elapsed >= PROCESSING_DURATION) {
        localStorage.removeItem(next.startKey)
        localStorage.setItem(next.doneKey, '1')
        clearInterval(id)
        window.location.reload()
        return
      }
      setState(next)
    }, 1000)
    return () => clearInterval(id)
  }, [state.active, getState])

  return state
}

function ProcessingCTA({ elapsed }: { elapsed: number }) {
  const clamped = Math.min(elapsed, PROCESSING_DURATION)
  const pct = Math.round((clamped / PROCESSING_DURATION) * 100)
  const remainingSec = Math.max(PROCESSING_DURATION - clamped, 0)
  const remainingMin = Math.ceil(remainingSec / 60)

  return (
    <div className="flex flex-col items-center gap-4 py-6">
      <MeridianEmblem size={48} animate />
      <h2 className="text-lg font-semibold text-[#F5F5F7]">
        Your AI insights are being generated...
      </h2>
      <div className="w-full max-w-xs">
        <div className="h-2 rounded-full bg-[#1F1F23] overflow-hidden">
          <div
            className="h-full rounded-full bg-[#1A8FD6] transition-all duration-1000 ease-linear"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-[11px] text-[#A1A1A8] text-center mt-1.5">
          {pct}% complete &middot; ~{remainingMin} min remaining
        </p>
      </div>
      <p className="text-xs text-[#A1A1A8]/70 text-center max-w-sm leading-relaxed">
        Your revenue, products, and staff data are already loaded. Check back when analysis is complete.
      </p>
    </div>
  )
}

function StatCardShell({ label }: { label: string }) {
  return (
    <div className="card p-4 flex flex-col items-center justify-center min-h-[100px] gap-2">
      <p className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider font-medium">{label}</p>
      <MiniRadar size={28} />
      <div className="h-5 w-16 rounded bg-[#1F1F23]/50" />
    </div>
  )
}

function ChartShell({ title, height = 280 }: { title: string; height?: number }) {
  return (
    <div className="card p-4 sm:p-5" style={{ minHeight: height }}>
      <p className="text-sm font-semibold text-[#F5F5F7]/30 mb-4">{title}</p>
      <div className="relative" style={{ height: height - 60 }}>
        <div className="absolute inset-0 flex items-end gap-[3px] px-2 opacity-20">
          {[35, 50, 40, 65, 55, 75, 45, 80, 60, 70, 50, 85, 55, 68, 48, 72, 58, 78, 42, 62, 52, 74, 44, 66, 56, 76, 46, 82].map((h, i) => (
            <div key={i} className="flex-1 rounded-t bg-[#1A8FD6]" style={{ height: `${h}%` }} />
          ))}
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <MiniRadar size={48} label="Loading chart data..." />
        </div>
      </div>
    </div>
  )
}

function TableShell({ columns, rows = 6 }: { columns: string[]; rows?: number }) {
  return (
    <div className="card p-4 sm:p-5 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1F1F23]">
            {columns.map(c => (
              <th key={c} className="text-left text-[10px] text-[#A1A1A8]/40 uppercase tracking-wider font-medium py-2 px-2">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i} className="border-b border-[#1F1F23]/50">
              {columns.map((c, j) => (
                <td key={j} className="py-3 px-2">
                  {j === 0 && i === Math.floor(rows / 2) ? (
                    <MiniRadar size={20} />
                  ) : (
                    <div className="h-3 rounded bg-[#1F1F23]/40 animate-pulse" style={{ width: `${40 + Math.random() * 40}%` }} />
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function GridShell({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-4 flex flex-col items-center justify-center min-h-[140px] gap-3">
          <MiniRadar size={i === 1 || i === 4 ? 36 : 28} />
          <div className="space-y-1.5 w-full">
            <div className="h-3 rounded bg-[#1F1F23]/40 animate-pulse mx-auto" style={{ width: '60%' }} />
            <div className="h-2 rounded bg-[#1F1F23]/30 animate-pulse mx-auto" style={{ width: '40%' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

const PAGE_CONFIGS: Record<string, {
  stats: string[]
  sections: { type: 'chart' | 'table' | 'grid'; title: string; columns?: string[]; rows?: number; count?: number; height?: number }[]
}> = {
  Overview: {
    stats: ['Total Revenue', 'Transactions', 'Avg Ticket', 'Retention'],
    sections: [
      { type: 'grid', title: 'Top 3 Actions Today', count: 3 },
      { type: 'chart', title: 'Revenue Trend', height: 280 },
      { type: 'grid', title: 'Agent Activity', count: 5 },
    ],
  },
  Revenue: {
    stats: ['Total Revenue', 'Transactions', 'Refunds', 'Tips'],
    sections: [
      { type: 'chart', title: 'Daily Revenue Trend', height: 280 },
      { type: 'chart', title: 'Weekly Breakdown', height: 220 },
    ],
  },
  Products: {
    stats: ['Total Products', 'Revenue', 'Top Seller', 'Avg Price'],
    sections: [
      { type: 'chart', title: 'Top Products by Revenue', height: 280 },
      { type: 'table', title: 'Product Performance', columns: ['Product', 'Price', 'Revenue', 'Qty Sold', '% of Total'], rows: 8 },
    ],
  },
  Forecasts: {
    stats: ['Predicted Revenue', 'Forecast Days', 'Avg Confidence', 'Trend'],
    sections: [
      { type: 'chart', title: 'Revenue Forecast', height: 300 },
      { type: 'table', title: 'Forecast Breakdown', columns: ['Type', 'Period', 'Predicted', 'Lower', 'Upper', 'Confidence'], rows: 5 },
    ],
  },
  Insights: {
    stats: ['Total Insights', 'Critical', 'Opportunities', 'Avg Confidence'],
    sections: [
      { type: 'grid', title: 'AI Insights', count: 6 },
    ],
  },
  'AI Agents': {
    stats: ['Active Agents', 'Total Findings', 'Avg Confidence', 'Messages'],
    sections: [
      { type: 'grid', title: 'Agent Activity', count: 6 },
      { type: 'table', title: 'Agent Communication Log', columns: ['Source', '', 'Target', 'Trigger', 'Data'], rows: 4 },
    ],
  },
  'Top Actions': {
    stats: ['Total Actions', 'Critical', 'Revenue Impact', 'Avg Confidence'],
    sections: [
      { type: 'grid', title: 'Prioritized Actions', count: 3 },
    ],
  },
  Customers: {
    stats: ['Total Customers', 'New (30d)', 'Repeat Rate', 'Avg LTV', 'Churn Risk'],
    sections: [
      { type: 'grid', title: 'Customer Segments', count: 4 },
      { type: 'table', title: 'Cohort Retention', columns: ['Cohort', 'Customers', 'M0', 'M1', 'M2', 'M3'], rows: 5 },
    ],
  },
  Staff: {
    stats: ['Total Staff', 'Avg Revenue/Staff', 'Top Performer', 'Avg Ticket'],
    sections: [
      { type: 'table', title: 'Staff Performance', columns: ['Staff Member', 'Revenue', 'Transactions', 'Avg Ticket', 'Tips', 'Score'], rows: 6 },
    ],
  },
  'Peak Hours': {
    stats: ['Busiest Hour', 'Busiest Day', 'Peak Revenue', 'Avg Wait'],
    sections: [
      { type: 'chart', title: 'Hourly Revenue Heatmap', height: 300 },
    ],
  },
  Margins: {
    stats: ['Avg Margin', 'Highest Margin', 'Lowest Margin', 'Total COGS'],
    sections: [
      { type: 'chart', title: 'Margin Distribution', height: 300 },
      { type: 'table', title: 'Product Margins', columns: ['Product', 'Price', 'Cost', 'Margin', 'Margin %'], rows: 7 },
    ],
  },
  'Menu Matrix': {
    stats: ['Stars', 'Plowhorses', 'Puzzles', 'Dogs'],
    sections: [
      { type: 'chart', title: 'Menu Engineering Matrix', height: 320 },
      { type: 'table', title: 'Item Classification', columns: ['Item', 'Category', 'Popularity', 'Profitability', 'Class'], rows: 8 },
    ],
  },
  Anomalies: {
    stats: ['Active Anomalies', 'Critical', 'Revenue Impact', 'Resolved'],
    sections: [
      { type: 'grid', title: 'Detected Anomalies', count: 4 },
    ],
  },
  Notifications: {
    stats: ['Total', 'Unread', 'Critical', 'This Week'],
    sections: [
      { type: 'grid', title: 'Recent Notifications', count: 6 },
    ],
  },
  Inventory: {
    stats: ['Total Items', 'Low Stock', 'Overstocked', 'Expiring Soon'],
    sections: [
      { type: 'table', title: 'Inventory Status', columns: ['Item', 'Current Qty', 'Reorder Point', 'Status', 'Last Updated'], rows: 8 },
    ],
  },
}

interface DataPageSkeletonProps {
  title: string
  children: ReactNode
  layout?: 'stats' | 'chart' | 'table' | 'grid'
}

export default function DataPageSkeleton({ title, children }: DataPageSkeletonProps) {
  const { org } = useAuth()
  const location = useLocation()
  const isDemo = location.pathname.startsWith('/demo') || location.pathname.startsWith('/canada/demo')
  const processing = useProcessingState()

  // Demo mode always shows real content
  if (isDemo) return <>{children}</>

  // POS connected and analysis finished — show real content
  if (org?.pos_connected && !processing.active) return <>{children}</>

  // Either POS not connected, or POS connected but still processing
  const isProcessing = org?.pos_connected && processing.active
  const config = PAGE_CONFIGS[title] || PAGE_CONFIGS['Revenue']

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#F5F5F7]">{title}</h1>
        <p className="text-sm text-[#A1A1A8] mt-1">
          {isProcessing
            ? 'Your data is being analyzed by our AI agents'
            : 'Connect your POS to populate this view with live data'}
        </p>
      </div>

      <div className={`grid gap-3 ${config.stats.length === 5 ? 'grid-cols-2 lg:grid-cols-5' : 'grid-cols-2 lg:grid-cols-4'}`}>
        {config.stats.map(label => (
          <StatCardShell key={label} label={label} />
        ))}
      </div>

      {config.sections.map((section, i) => (
        <div key={i}>
          {section.type === 'chart' && <ChartShell title={section.title} height={section.height} />}
          {section.type === 'table' && <TableShell columns={section.columns || []} rows={section.rows} />}
          {section.type === 'grid' && <GridShell count={section.count} />}
        </div>
      ))}

      {isProcessing ? <ProcessingCTA elapsed={processing.elapsed} /> : <ConnectCTA />}
    </div>
  )
}
