import { useState } from 'react'
import { MonitorPlay, Smartphone } from 'lucide-react'
import { COURSE_MODULES, type CourseFormat } from './course-data'

const VIDEO_BASE = '/training-videos'

// Playbook doc → training video(s). First match wins; most-specific first.
// Sections without a natural video home (cheatsheets, most troubleshooting)
// intentionally get none.
const VIDEO_MAP: { match: (path: string) => boolean; topics: string[] }[] = [
  { match: p => p === '00-getting-started/02-product-overview.md', topics: ['master', 'phone', 'pos', 'camera', 'csv'] },
  { match: p => p.startsWith('00-getting-started/'), topics: ['master'] },
  { match: p => p.startsWith('10-pos-integrations/'), topics: ['pos'] },
  { match: p => p.startsWith('20-camera-integrations/'), topics: ['camera'] },
  { match: p => p.startsWith('30-features/vision/'), topics: ['camera'] },
  { match: p => p.startsWith('30-features/pos-analytics/'), topics: ['csv'] },
  { match: p => p === '40-troubleshooting/pos-connection-failures.md' || p === '40-troubleshooting/backfill-stuck.md', topics: ['pos'] },
  { match: p => p === '40-troubleshooting/camera-offline.md', topics: ['camera'] },
]

export function videosForDoc(path: string): string[] {
  return VIDEO_MAP.find(m => m.match(path))?.topics ?? []
}

/**
 * Inline training video panel shown above a playbook doc when the doc's
 * section has a matching connect video. Same files the Training Course uses.
 */
export default function PlaybookVideo({ docPath }: { docPath: string }) {
  const topics = videosForDoc(docPath)
  const [topicId, setTopicId] = useState<string | null>(null)
  const [format, setFormat] = useState<CourseFormat>('landscape')

  if (topics.length === 0) return null

  const activeId = topicId && topics.includes(topicId) ? topicId : topics[0]
  const module = COURSE_MODULES.find(m => m.id === activeId)
  if (!module) return null

  return (
    <div className="mb-5 rounded-xl border border-[#1a2420] bg-[#1a2420]/40 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wider text-[#4a5550] mr-1">Watch</span>
          {topics.map(t => {
            const m = COURSE_MODULES.find(x => x.id === t)
            if (!m) return null
            return (
              <button
                key={t}
                type="button"
                onClick={() => setTopicId(t)}
                className={`rounded-full border px-2.5 py-1 text-[10.5px] font-medium transition-colors ${
                  t === activeId
                    ? 'border-[#00d4aa]/50 bg-[#00d4aa]/10 text-[#00d4aa]'
                    : 'border-[#1a2420] text-[#6b7a74] hover:text-[#c8d0cc] hover:border-[#2a3630]'
                }`}
              >
                {m.title}
              </button>
            )
          })}
        </div>
        <div className="flex gap-1">
          {([
            { id: 'landscape' as const, label: 'Desktop', icon: MonitorPlay },
            { id: 'vertical' as const, label: 'iPhone', icon: Smartphone },
          ]).map(f => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFormat(f.id)}
              className={`flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-medium transition-colors ${
                format === f.id
                  ? 'border-[#00d4aa]/50 bg-[#00d4aa]/10 text-[#00d4aa]'
                  : 'border-[#1a2420] text-[#6b7a74] hover:text-[#c8d0cc]'
              }`}
            >
              <f.icon size={10} /> {f.label}
            </button>
          ))}
        </div>
      </div>
      <div
        className={`mx-auto overflow-hidden rounded-lg border border-[#1a2420] bg-black ${
          format === 'landscape' ? 'w-full' : 'max-w-[260px]'
        }`}
      >
        <video
          key={`${activeId}-${format}`}
          src={`${VIDEO_BASE}/${module.files[format]}`}
          controls
          preload="metadata"
          playsInline
          className="block w-full"
        />
      </div>
    </div>
  )
}
