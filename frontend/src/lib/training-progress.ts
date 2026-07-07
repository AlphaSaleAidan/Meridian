// Rep Training Course progress: per-module video/quiz state and the Code of
// Conduct signature, stored in Supabase (rep_training_progress /
// rep_conduct_signatures — see supabase/migrations/20260707_rep_training_course.sql).
// Rows are keyed by lowercased rep email because auth.uid() never equals
// sales_reps.id in this schema; RLS enforces email ownership.

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { useSalesAuth, type SalesRepProfile } from '@/lib/sales-auth'
import { CONDUCT_VERSION, PASS_SCORE } from '@/components/training/course-data'

export const REQUIRED_MODULE_IDS = ['master', 'phone', 'pos', 'camera', 'csv'] as const

// Mirrors backend ADMIN_EMAILS (src/api/auth.py). Platform admins skip the
// training lock in the UI; the RLS-side bypass is is_admin() (admin_users).
const TRAINING_EXEMPT_EMAILS = [
  'apierce@alphasale.co',
  'aidanpierce72@gmail.com',
  'aidanpierce@meridian.tips',
  'cheungenochmgmt@gmail.com',
  'aidanvietnguyen@gmail.com',
]

export function isTrainingExempt(email: string | null | undefined): boolean {
  if (!email) return false
  const normalized = email.toLowerCase()
  return TRAINING_EXEMPT_EMAILS.includes(normalized)
}

export interface ModuleProgress {
  module_id: string
  video_watched: boolean
  attempts: number
  best_score: number | null
  passed: boolean
  passed_at: string | null
}

export interface ConductSignature {
  signed_name: string
  conduct_version: string
  signed_at: string
}

export interface TrainingState {
  /** false when Supabase is unconfigured or the tables aren't migrated yet —
   *  gates fail OPEN in that case (RLS isn't enforcing either). */
  available: boolean
  byModule: Record<string, ModuleProgress>
  signature: ConductSignature | null
  /** signed the CURRENT conduct version (drives the course UI) */
  signedCurrent: boolean
  /** all modules passed + any conduct version signed — matches the SQL
   *  rep_training_complete() used by the canada_leads insert policy */
  courseComplete: boolean
}

const EMPTY_STATE: TrainingState = {
  available: false,
  byModule: {},
  signature: null,
  signedCurrent: false,
  courseComplete: false,
}

async function fetchTrainingState(email: string): Promise<TrainingState> {
  if (!supabase) return EMPTY_STATE
  try {
    const [progressRes, sigRes] = await Promise.all([
      supabase
        .from('rep_training_progress')
        .select('module_id, video_watched, attempts, best_score, passed, passed_at')
        .eq('rep_email', email),
      supabase
        .from('rep_conduct_signatures')
        .select('signed_name, conduct_version, signed_at')
        .eq('rep_email', email)
        .order('signed_at', { ascending: false }),
    ])
    if (progressRes.error) throw progressRes.error
    if (sigRes.error) throw sigRes.error

    const byModule: Record<string, ModuleProgress> = {}
    for (const row of progressRes.data ?? []) byModule[row.module_id] = row

    const signatures = sigRes.data ?? []
    const signature = signatures[0] ?? null
    const signedCurrent = signatures.some(s => s.conduct_version === CONDUCT_VERSION)
    const allPassed = REQUIRED_MODULE_IDS.every(id => byModule[id]?.passed)

    return {
      available: true,
      byModule,
      signature,
      signedCurrent,
      courseComplete: allPassed && signatures.length > 0,
    }
  } catch (err) {
    // Table missing (migration not applied) or transient failure — fail open
    // and let the course UI show that progress tracking isn't live yet.
    console.warn('[training] progress unavailable:', err)
    return EMPTY_STATE
  }
}

function trainingKey(email: string | undefined) {
  return ['rep-training', email ?? 'anon']
}

export function useTrainingProgress(rep: SalesRepProfile | null) {
  const email = rep?.email?.toLowerCase()
  const qc = useQueryClient()
  const query = useQuery({
    queryKey: trainingKey(email),
    queryFn: () => fetchTrainingState(email!),
    enabled: !!email && !!supabase,
    staleTime: 30_000,
  })
  return {
    state: query.data ?? EMPTY_STATE,
    isLoading: query.isLoading,
    refetch: () => qc.invalidateQueries({ queryKey: trainingKey(email) }),
  }
}

/** Gate for lead-creation surfaces. locked=true only when we positively know
 *  the rep hasn't finished the course; loading and pre-migration states fail
 *  open (the Supabase RLS policy is the hard enforcement layer). */
export function useTrainingLock() {
  const { rep } = useSalesAuth()
  const { state, isLoading } = useTrainingProgress(rep)
  const exempt = isTrainingExempt(rep?.email)
  const locked = !!rep && !exempt && !isLoading && state.available && !state.courseComplete
  return { locked, loading: isLoading, state }
}

// ─── Writes ──────────────────────────────────────────────────

function repKeys(rep: SalesRepProfile) {
  return { rep_id: rep.rep_id, rep_email: rep.email.toLowerCase() }
}

export async function markVideoWatched(rep: SalesRepProfile, moduleId: string): Promise<void> {
  if (!supabase) return
  const { error } = await supabase.from('rep_training_progress').upsert(
    {
      ...repKeys(rep),
      module_id: moduleId,
      video_watched: true,
      video_watched_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    { onConflict: 'rep_email,module_id' },
  )
  if (error) throw new Error(error.message)
}

export async function recordQuizAttempt(
  rep: SalesRepProfile,
  moduleId: string,
  score: number,
  quizTotal: number,
  prev: ModuleProgress | undefined,
): Promise<boolean> {
  if (!supabase) return score >= PASS_SCORE
  const passed = score >= PASS_SCORE
  const alreadyPassed = prev?.passed ?? false
  const { error } = await supabase.from('rep_training_progress').upsert(
    {
      ...repKeys(rep),
      module_id: moduleId,
      attempts: (prev?.attempts ?? 0) + 1,
      quiz_total: quizTotal,
      best_score: Math.max(score, prev?.best_score ?? 0),
      passed: alreadyPassed || passed,
      passed_at: alreadyPassed || !passed ? prev?.passed_at ?? null : new Date().toISOString(),
      // Failing resets the video: the rep must rewatch before retaking.
      video_watched: passed,
      updated_at: new Date().toISOString(),
    },
    { onConflict: 'rep_email,module_id' },
  )
  if (error) throw new Error(error.message)
  return passed
}

export async function signConduct(rep: SalesRepProfile, signedName: string): Promise<void> {
  if (!supabase) return
  const { error } = await supabase.from('rep_conduct_signatures').insert({
    ...repKeys(rep),
    signed_name: signedName.trim(),
    conduct_version: CONDUCT_VERSION,
  })
  if (error) throw new Error(error.message)
}
