import { motion, useReducedMotion } from 'framer-motion'
import { Phone } from 'lucide-react'

import type { Vertical } from './verticals'

const EASE = 'linear' as const

/**
 * An instrument trace from live call to Meridian to the resulting system row.
 * The moving signal makes the data path legible without turning it into an illustration.
 */
export default function FlowDiagram({ vertical }: { vertical: Vertical }) {
  const reduced = useReducedMotion()
  const travel = reduced
    ? { initial: false as const, animate: { x: '0%' } }
    : { initial: { x: '-100%' }, animate: { x: ['-100%', '0%'] } }
  const verticalTravel = reduced
    ? { initial: false as const, animate: { y: '0%' } }
    : { initial: { y: '-100%' }, animate: { y: ['-100%', '0%'] } }

  const signalTransition = reduced
    ? { duration: 0 }
    : { duration: 3, ease: EASE, repeat: Infinity, repeatType: 'loop' as const }

  return (
    <div className="relative rounded-2xl border border-white/[0.07] bg-white/[0.03] px-6 py-10 sm:px-10">
      <div className="absolute bottom-[72px] left-1/2 top-[72px] w-px -translate-x-1/2 bg-white/15 sm:hidden">
        <motion.span
          className="absolute inset-0"
          {...verticalTravel}
          transition={signalTransition}
        >
          <span className="absolute bottom-0 left-1/2 h-2 w-2 -translate-x-1/2 translate-y-1/2 rounded-full bg-[#17C5B0] shadow-[0_0_14px_rgba(23,197,176,0.9)]" />
        </motion.span>
      </div>
      <div className="absolute left-[16.666%] right-[16.666%] top-[72px] hidden h-px bg-white/15 sm:block">
        <motion.span
          className="absolute inset-0"
          {...travel}
          transition={signalTransition}
        >
          <span className="absolute right-0 top-1/2 h-2 w-2 translate-x-1/2 -translate-y-1/2 rounded-full bg-[#17C5B0] shadow-[0_0_14px_rgba(23,197,176,0.9)]" />
        </motion.span>
      </div>

      <div className="relative grid gap-12 sm:grid-cols-3 sm:gap-6">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/15 bg-[#070B14]">
            <Phone className="h-5 w-5 text-slate-300" />
          </div>
          <div className="mt-4 font-mono text-xs font-medium uppercase tracking-wider text-white">The call</div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">answered &lt; 1 ring</div>
        </div>

        <div className="flex flex-col items-center text-center">
          <div className="flex h-16 min-w-28 items-center justify-center rounded-full border border-[#17C5B0]/50 bg-[#070B14] px-5 shadow-[0_0_40px_rgba(23,197,176,0.3)]">
            <span className="font-mono text-xs font-semibold tracking-[0.18em] text-[#17C5B0]">MERIDIAN</span>
          </div>
          <div className="mt-4 font-mono text-xs font-medium uppercase tracking-wider text-white">Meridian</div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">menu · prices · availability</div>
        </div>

        <div className="flex flex-col items-center text-center">
          <div className="flex min-h-16 items-center rounded-xl border border-[#17C5B0]/40 bg-[#070B14] px-4 py-3 font-mono text-xs text-white">
            {vertical.artifact.headline}
          </div>
          <div className="mt-4 font-mono text-xs font-medium uppercase tracking-wider text-white">{vertical.artifact.panel}</div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">landed mid-call</div>
        </div>
      </div>
    </div>
  )
}
