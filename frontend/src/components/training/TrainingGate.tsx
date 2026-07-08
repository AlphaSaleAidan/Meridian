import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { GraduationCap, Lock } from 'lucide-react'
import { useTrainingLock, REQUIRED_MODULE_IDS } from '@/lib/training-progress'

/**
 * Blocks a lead-creation surface until the rep finishes the Training Course.
 * Admins are exempt; while loading (or before the progress migration exists)
 * it fails open — the {canada,us}_leads RLS insert policy is the hard enforcement.
 */
export default function TrainingGate({ children }: { children: ReactNode }) {
  const { locked, state } = useTrainingLock()
  const { pathname } = useLocation()
  const trainingPath = pathname.startsWith('/us') ? '/us/portal/training' : '/canada/portal/training'

  if (!locked) return <>{children}</>

  const passed = REQUIRED_MODULE_IDS.filter(id => state.byModule[id]?.passed).length
  const done = passed + (state.signature ? 1 : 0)

  return (
    <div className="mx-auto max-w-md rounded-xl border border-white/10 bg-white/[0.02] p-8 text-center mt-10">
      <Lock size={26} className="mx-auto mb-3 text-white/40" />
      <h2 className="text-base font-bold text-white">Finish training to create leads</h2>
      <p className="mt-2 text-[12px] leading-relaxed text-white/50">
        Lead creation unlocks after you complete the Training Course — five short videos, a quick
        quiz after each, and the Code of Conduct signature. You're {done} of 6 steps in.
      </p>
      <Link
        to={trainingPath}
        className="mt-5 inline-flex items-center gap-2 rounded-lg bg-pm-accent px-4 py-2.5 text-xs font-semibold text-pm-canada-bg hover:bg-pm-accent/90 transition-all"
      >
        <GraduationCap size={15} /> Go to the Training Course
      </Link>
    </div>
  )
}
