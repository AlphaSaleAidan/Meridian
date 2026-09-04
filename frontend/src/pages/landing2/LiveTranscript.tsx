import { useEffect, useRef, useState } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'
import { Phone } from 'lucide-react'

import { BorderBeam } from '@/components/ui/BorderBeam'
import type { TranscriptLine, VerticalArtifact } from './verticals'

const EASE = [0.16, 1, 0.3, 1] as const

/**
 * The page's signature: a call transcript that plays itself out, then the
 * artifact it created (order row, booking, tee time) lands in a product
 * panel beside it. The transcript IS the demo and the artifact IS the proof —
 * no illustration stands in for either.
 *
 * Timing is per-line, not per-character: a voice call reads in beats, and a
 * character-typewriter reads as a chatbot. Reduced motion shows everything
 * settled.
 */
export default function LiveTranscript({
  lines,
  artifact,
  restartKey,
}: {
  lines: TranscriptLine[]
  artifact: VerticalArtifact
  restartKey: string
}) {
  const rootRef = useRef<HTMLDivElement>(null)
  const inView = useInView(rootRef, { once: false, amount: 0.4 })
  const reduced = useReducedMotion()
  const [shown, setShown] = useState(0)

  useEffect(() => {
    setShown(reduced ? lines.length : 0)
  }, [restartKey, reduced, lines.length])

  useEffect(() => {
    if (reduced || !inView || shown >= lines.length) return
    const t = setTimeout(() => setShown((n) => n + 1), shown === 0 ? 450 : 1500)
    return () => clearTimeout(t)
  }, [inView, shown, lines.length, reduced, restartKey])

  const done = shown >= lines.length

  return (
    <div ref={rootRef} className="grid gap-4 lg:grid-cols-[1.15fr,1fr] items-start">
      {/* The call */}
      <div className="rounded-2xl border border-[#EAE5DC] bg-white shadow-[0_8px_30px_rgba(23,26,32,0.06)]">
        <div className="flex items-center gap-2.5 border-b border-[#EAE5DC] px-5 py-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#17C5B0] opacity-60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#17C5B0]" />
          </span>
          <span className="font-mono text-xs tracking-wide text-[#9BA0A8]">
            LIVE CALL · answered before the second ring
          </span>
          <Phone className="ml-auto h-3.5 w-3.5 shrink-0 text-[#9BA0A8]" />
        </div>
        <div className="space-y-3 px-5 py-5 min-h-[260px]">
          {lines.slice(0, shown).map((line, i) => (
            <motion.div
              key={`${restartKey}-${i}`}
              initial={reduced ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: EASE }}
              className={line.speaker === 'agent' ? 'flex justify-end' : 'flex'}
            >
              <div
                className={
                  line.speaker === 'agent'
                    ? 'max-w-[85%] rounded-2xl rounded-br-md bg-[#1A8FD6] px-4 py-2.5 text-[15px] leading-snug text-white'
                    : 'max-w-[85%] rounded-2xl rounded-bl-md bg-[#F3F0E9] px-4 py-2.5 text-[15px] leading-snug text-[#171A20]'
                }
              >
                {line.speaker === 'agent' && (
                  <span className="mb-0.5 block font-mono text-[10px] uppercase tracking-widest text-white/75">
                    Meridian
                  </span>
                )}
                {line.text}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* The artifact it produced */}
      <div className="rounded-2xl border border-[#EAE5DC] bg-[#FBF8F3] shadow-[0_8px_30px_rgba(23,26,32,0.06)]">
        <div className="border-b border-[#EAE5DC] px-5 py-3">
          <span className="font-mono text-xs tracking-wide text-[#9BA0A8]">{artifact.panel}</span>
        </div>
        <div className="px-5 py-5">
          <motion.div
            key={`${restartKey}-artifact`}
            initial={reduced ? false : { opacity: 0, scale: 0.97, y: 8 }}
            animate={done ? { opacity: 1, scale: 1, y: 0 } : { opacity: 0.25, scale: 0.97, y: 8 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="relative overflow-hidden rounded-xl border border-[#17C5B0]/60 bg-white p-4"
          >
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-semibold text-[#171A20]">{artifact.headline}</span>
              {artifact.amount && (
                <span className="font-mono text-sm text-[#171A20]">{artifact.amount}</span>
              )}
            </div>
            <p className="mt-1 text-sm text-[#5B6069]">{artifact.detail}</p>
            <p className="mt-3 font-mono text-[11px] uppercase tracking-widest text-[#0FA894]">
              {done ? 'Landed while the caller was still on the line' : 'Waiting for the call…'}
            </p>
            {done && (
              <BorderBeam size={140} duration={8} colorFrom="#17C5B0" colorTo="#1A8FD6" />
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
