import { clsx } from 'clsx'
import {
  User, Clock, MapPin, Heart, TrendingUp, Tag,
  ChevronDown, ChevronUp,
} from 'lucide-react'
import { useState } from 'react'

interface Profile {
  id: string
  embedding_hash: string
  visit_count: number
  first_seen: string
  last_seen: string
  avg_dwell_sec: number
  favorite_zone: string
  visit_pattern: string
  gender: string
  age_range: string
  avg_sentiment: string
  total_pos_spend_cents: number
  predicted_ltv: number
  is_opted_in: boolean
  tags: string[]
}

interface Visit {
  entered_at: string
  exited_at: string
  dwell_seconds: number
  zones_visited: string[]
  emotion_entry: string
  emotion_exit: string
  pos_transaction_id: string | null
}

interface Props {
  profile: Profile
  onExpand?: (profileId: string) => void
  expanded?: boolean
  visits?: Visit[]
}

const tagStyles: Record<string, string> = {
  VIP: 'bg-[#7C5CFF]/10 text-[#7C5CFF] border-[#7C5CFF]/20',
  Regular: 'bg-[#17C5B0]/10 text-[#17C5B0] border-[#17C5B0]/20',
  'At-Risk': 'bg-red-500/10 text-red-400 border-red-500/20',
  'Window Shopper': 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  New: 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/20',
}

const sentimentEmoji: Record<string, string> = {
  happy: '😊', neutral: '😐', sad: '😔', angry: '😠', surprise: '😮',
  fear: '😨', disgust: '🤢',
}

function formatCents(cents: number): string {
  return `$${(cents / 100).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function timeAgo(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const now = new Date()
  const days = Math.floor((now.getTime() - d.getTime()) / 86400000)
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 7) return `${days}d ago`
  if (days < 30) return `${Math.floor(days / 7)}w ago`
  return `${Math.floor(days / 30)}mo ago`
}

export default function CustomerProfileCard({ profile, onExpand, expanded, visits }: Props) {
  const p = profile

  const autoTags: string[] = [...(p.tags || [])]
  if (p.visit_count >= 10 && !autoTags.includes('VIP')) autoTags.unshift('VIP')
  else if (p.visit_count >= 4 && !autoTags.includes('Regular')) autoTags.unshift('Regular')
  else if (p.visit_count === 1 && !autoTags.includes('New')) autoTags.unshift('New')

  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => onExpand?.(p.id)}
        className="w-full p-4 text-left hover:bg-[#1F1F23]/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
            <User size={18} className="text-[#1A8FD6]" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-[#F5F5F7] font-mono">
                #{p.embedding_hash}
              </span>
              {p.gender && (
                <span className="text-[10px] text-[#A1A1A8]/50">{p.gender}</span>
              )}
              {p.age_range && (
                <span className="text-[10px] text-[#A1A1A8]/50">{p.age_range}</span>
              )}
              {p.avg_sentiment && (
                <span className="text-sm">{sentimentEmoji[p.avg_sentiment] || '😐'}</span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1 text-[10px] text-[#A1A1A8]/60">
              <span className="flex items-center gap-1">
                <Heart size={10} /> {p.visit_count} visits
              </span>
              <span className="flex items-center gap-1">
                <Clock size={10} /> {Math.round(p.avg_dwell_sec / 60)}min avg
              </span>
              {p.favorite_zone && (
                <span className="flex items-center gap-1">
                  <MapPin size={10} /> {p.favorite_zone}
                </span>
              )}
            </div>
          </div>

          <div className="text-right flex-shrink-0 space-y-1">
            <p className="text-sm font-bold text-[#4FE3C1] font-mono">
              {formatCents(p.predicted_ltv)}<span className="text-[10px] font-normal text-[#A1A1A8]/40">/yr</span>
            </p>
            {p.total_pos_spend_cents > 0 && (
              <p className="text-[10px] text-[#A1A1A8]/50 font-mono">
                {formatCents(p.total_pos_spend_cents)} spent
              </p>
            )}
          </div>

          <div className="flex-shrink-0 text-[#A1A1A8]/40">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </div>

        <div className="flex items-center gap-1.5 mt-2 flex-wrap">
          {autoTags.map(tag => (
            <span
              key={tag}
              className={clsx(
                'text-[10px] font-medium px-1.5 py-0.5 rounded border',
                tagStyles[tag] || 'bg-[#1F1F23] text-[#A1A1A8] border-[#1F1F23]',
              )}
            >
              {tag}
            </span>
          ))}
          <span className="text-[10px] text-[#A1A1A8]/30 ml-auto">
            last seen {timeAgo(p.last_seen)}
          </span>
        </div>
      </button>

      {expanded && visits && (
        <div className="border-t border-[#1F1F23] px-4 py-3 bg-[#0A0A0B]/50">
          <p className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider mb-2 font-medium">
            Visit History
          </p>
          {visits.length === 0 ? (
            <p className="text-xs text-[#A1A1A8]/40">No visits recorded</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {visits.slice(0, 20).map((v, i) => (
                <div key={i} className="flex items-center gap-3 text-[11px]">
                  <span className="text-[#A1A1A8]/40 font-mono w-16 flex-shrink-0">
                    {new Date(v.entered_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  </span>
                  <span className="text-[#F5F5F7] font-mono w-10">
                    {v.dwell_seconds ? `${Math.round(v.dwell_seconds / 60)}m` : '—'}
                  </span>
                  <div className="flex items-center gap-1 flex-1 min-w-0">
                    {(v.zones_visited || []).map((z, j) => (
                      <span key={j} className="text-[10px] text-[#A1A1A8]/50 bg-[#1F1F23] px-1 py-0.5 rounded">
                        {z}
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {v.emotion_entry && <span className="text-sm">{sentimentEmoji[v.emotion_entry] || '😐'}</span>}
                    {v.emotion_entry && v.emotion_exit && <span className="text-[#A1A1A8]/30">→</span>}
                    {v.emotion_exit && <span className="text-sm">{sentimentEmoji[v.emotion_exit] || '😐'}</span>}
                  </div>
                  {v.pos_transaction_id && (
                    <span className="text-[10px] text-[#4FE3C1] font-mono">$</span>
                  )}
                </div>
              ))}
            </div>
          )}
          {p.visit_pattern && (
            <p className="text-[10px] text-[#A1A1A8]/40 mt-2 pt-2 border-t border-[#1F1F23]">
              Pattern: <span className="text-[#F5F5F7]">{p.visit_pattern}</span>
            </p>
          )}
        </div>
      )}
    </div>
  )
}
