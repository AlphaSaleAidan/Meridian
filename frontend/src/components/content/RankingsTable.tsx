import { useState } from 'react'
import { ArrowUp, ArrowDown, Minus, ChevronUp, ChevronDown } from 'lucide-react'
import { clsx } from 'clsx'
import type { ContentRanking } from '@/lib/content-demo-data'

interface RankingsTableProps {
  rankings: ContentRanking[]
}

type SortKey = 'rank_position' | 'rank_change'

const AI_COLORS: Record<string, string> = {
  chatgpt: 'bg-blue-500/15 text-blue-400 border-blue-500/20',
  claude: 'bg-amber-500/15 text-amber-400 border-amber-500/20',
  perplexity: 'bg-teal-500/15 text-teal-400 border-teal-500/20',
}

const AI_LABELS: Record<string, string> = {
  chatgpt: 'ChatGPT',
  claude: 'Claude',
  perplexity: 'Perplexity',
}

export default function RankingsTable({ rankings }: RankingsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('rank_position')
  const [sortAsc, setSortAsc] = useState(true)

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(prev => !prev)
    } else {
      setSortKey(key)
      setSortAsc(key === 'rank_position')
    }
  }

  const sorted = [...rankings].sort((a, b) => {
    const diff = a[sortKey] - b[sortKey]
    return sortAsc ? diff : -diff
  })

  function SortIcon({ column }: { column: SortKey }) {
    if (sortKey !== column) return null
    return sortAsc
      ? <ChevronUp size={12} className="inline ml-0.5" />
      : <ChevronDown size={12} className="inline ml-0.5" />
  }

  function formatDate(iso: string): string {
    const d = new Date(iso)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1F1F23]">
            <th className="text-left text-[10px] text-[#A1A1A8]/40 uppercase tracking-wider font-medium py-2.5 px-4">
              Keyword
            </th>
            <th
              className="text-left text-[10px] text-[#A1A1A8]/40 uppercase tracking-wider font-medium py-2.5 px-4 cursor-pointer select-none hover:text-[#A1A1A8]"
              onClick={() => handleSort('rank_position')}
            >
              Position <SortIcon column="rank_position" />
            </th>
            <th
              className="text-left text-[10px] text-[#A1A1A8]/40 uppercase tracking-wider font-medium py-2.5 px-4 cursor-pointer select-none hover:text-[#A1A1A8]"
              onClick={() => handleSort('rank_change')}
            >
              Change <SortIcon column="rank_change" />
            </th>
            <th className="text-left text-[10px] text-[#A1A1A8]/40 uppercase tracking-wider font-medium py-2.5 px-4">
              AI Citations
            </th>
            <th className="text-left text-[10px] text-[#A1A1A8]/40 uppercase tracking-wider font-medium py-2.5 px-4 hidden sm:table-cell">
              Last Checked
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(r => (
            <tr key={r.keyword} className="border-b border-[#1F1F23]/50 hover:bg-[#1F1F23]/30 transition-colors">
              <td className="py-3 px-4 text-[#F5F5F7] font-medium">{r.keyword}</td>
              <td className="py-3 px-4 font-mono text-[#F5F5F7]">#{r.rank_position}</td>
              <td className="py-3 px-4">
                {r.rank_change > 0 ? (
                  <span className="inline-flex items-center gap-0.5 text-[#17C5B0] font-mono text-xs font-semibold">
                    <ArrowUp size={12} /> {r.rank_change}
                  </span>
                ) : r.rank_change < 0 ? (
                  <span className="inline-flex items-center gap-0.5 text-red-400 font-mono text-xs font-semibold">
                    <ArrowDown size={12} /> {Math.abs(r.rank_change)}
                  </span>
                ) : (
                  <span className="inline-flex items-center text-[#A1A1A8] font-mono text-xs">
                    <Minus size={12} />
                  </span>
                )}
              </td>
              <td className="py-3 px-4">
                {r.ai_platforms_cited.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {r.ai_platforms_cited.map(p => (
                      <span
                        key={p}
                        className={clsx(
                          'text-[10px] font-medium px-1.5 py-0.5 rounded border',
                          AI_COLORS[p] || 'bg-[#1F1F23] text-[#A1A1A8] border-[#1F1F23]',
                        )}
                      >
                        {AI_LABELS[p] || p}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-[#A1A1A8]/40 text-xs">--</span>
                )}
              </td>
              <td className="py-3 px-4 text-[#A1A1A8] text-xs hidden sm:table-cell">
                {formatDate(r.checked_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
