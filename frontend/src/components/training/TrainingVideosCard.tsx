import { useMemo, useState } from 'react'
import { Clapperboard, MonitorPlay, Smartphone, Zap } from 'lucide-react'

const VIDEO_BASE = '/training-videos'

type Format = 'landscape' | 'vertical' | 'brainrot'

const FORMATS: { id: Format; label: string; icon: typeof MonitorPlay; blurb: string }[] = [
  { id: 'landscape', label: 'Desktop', icon: MonitorPlay, blurb: 'Full 16:9 — best on a laptop' },
  { id: 'vertical', label: 'iPhone', icon: Smartphone, blurb: '9:16 — watch on your phone' },
  { id: 'brainrot', label: 'Brainrot', icon: Zap, blurb: 'Subway Surfers split-screen' },
]

const TOPICS = [
  {
    id: 'master',
    label: 'The Full Tour',
    blurb: 'All four connections in two minutes — phone line, POS, cameras, costs. Start here.',
    files: {
      landscape: 'meridian-connect-trailer.mp4',
      vertical: 'meridian-connect-trailer-vertical.mp4',
      brainrot: 'meridian-connect-trailer-brainrot.mp4',
    },
  },
  {
    id: 'phone',
    label: 'Phone Line Setup',
    blurb: 'Provision a number, pick a voice, load the menu, route orders — step by step.',
    files: {
      landscape: 'connect-phone.mp4',
      vertical: 'connect-phone-vertical.mp4',
      brainrot: 'connect-phone-brainrot.mp4',
    },
  },
  {
    id: 'pos',
    label: 'POS Connect',
    blurb: 'One-click Square/Clover connect and the first sync — the highest-value 5 minutes of onboarding.',
    files: {
      landscape: 'connect-pos.mp4',
      vertical: 'connect-pos-vertical.mp4',
      brainrot: 'connect-pos-brainrot.mp4',
    },
  },
  {
    id: 'camera',
    label: 'Camera Setup',
    blurb: 'All three ways to connect a camera, zones, and the privacy story (numbers only, never video).',
    files: {
      landscape: 'connect-camera.mp4',
      vertical: 'connect-camera-vertical.mp4',
      brainrot: 'connect-camera-brainrot.mp4',
    },
  },
  {
    id: 'csv',
    label: 'Costs & Real Margins',
    blurb: 'Upload a cost sheet and switch the margins page from estimates to real numbers.',
    files: {
      landscape: 'connect-csv.mp4',
      vertical: 'connect-csv-vertical.mp4',
      brainrot: 'connect-csv-brainrot.mp4',
    },
  },
]

/**
 * Training video library. One shared player; reps pick a topic and a format.
 * Files are served as static assets from /training-videos/ (nginx alias on the
 * edge host), so they survive dist redeploys and never ship in the bundle.
 */
export default function TrainingVideosCard({ accent = '#17C5B0' }: { accent?: string }) {
  const [topicId, setTopicId] = useState('master')
  const [format, setFormat] = useState<Format>('landscape')

  const topic = TOPICS.find(t => t.id === topicId) ?? TOPICS[0]
  const src = useMemo(() => `${VIDEO_BASE}/${topic.files[format]}`, [topic, format])

  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
      <header className="flex items-center gap-2.5 mb-1">
        <Clapperboard size={16} style={{ color: accent }} />
        <h2 className="text-sm font-bold text-white">Training Videos</h2>
      </header>
      <p className="text-[11px] text-white/40 mb-4">
        Watch how every connection is set up before you walk a merchant through it. Each video comes in
        desktop, iPhone, and split-screen formats — same content, pick whichever holds your attention.
      </p>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {FORMATS.map(f => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFormat(f.id)}
            title={f.blurb}
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-medium transition-colors ${
              format === f.id
                ? 'border-white/25 bg-white/10 text-white'
                : 'border-white/5 bg-white/[0.01] text-white/50 hover:border-white/15 hover:text-white/80'
            }`}
          >
            <f.icon size={12} />
            {f.label}
          </button>
        ))}
      </div>

      <div
        className={`mx-auto overflow-hidden rounded-lg border border-white/10 bg-black ${
          format === 'landscape' ? 'w-full' : 'max-w-[300px]'
        }`}
      >
        <video
          key={src}
          src={src}
          controls
          preload="metadata"
          playsInline
          className="block w-full"
        />
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {TOPICS.map(t => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTopicId(t.id)}
            className={`rounded-lg border p-3 text-left transition-colors ${
              t.id === topicId
                ? 'border-white/20 bg-white/[0.05]'
                : 'border-white/5 bg-white/[0.01] hover:border-white/15 hover:bg-white/[0.03]'
            }`}
          >
            <span className="block text-[12px] font-medium text-white/90">{t.label}</span>
            <span className="block text-[10.5px] text-white/40 leading-snug mt-0.5">{t.blurb}</span>
          </button>
        ))}
      </div>
    </section>
  )
}
