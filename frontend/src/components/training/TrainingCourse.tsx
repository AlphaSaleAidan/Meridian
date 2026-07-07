import { useState } from 'react'
import {
  CheckCircle2, FileSignature, GraduationCap, Lock, MonitorPlay,
  PlayCircle, Smartphone,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import {
  markVideoWatched, recordQuizAttempt, useTrainingProgress,
} from '@/lib/training-progress'
import { COURSE_MODULES, PASS_SCORE, type CourseFormat } from './course-data'
import TrainingQuiz from './TrainingQuiz'
import CodeOfConductCard from './CodeOfConductCard'

const VIDEO_BASE = '/training-videos'
const CONDUCT_STEP = 'conduct'

const FORMATS: { id: CourseFormat; label: string; icon: typeof MonitorPlay }[] = [
  { id: 'landscape', label: 'Desktop', icon: MonitorPlay },
  { id: 'vertical', label: 'iPhone', icon: Smartphone },
]

/**
 * The rep Training Course: five video modules in order, a 4-question quiz
 * after each (pass with PASS_SCORE, fail = rewatch), and the Code of Conduct
 * signature at the end. Course completion unlocks lead creation for
 * non-admin reps (UI gate here, RLS on canada_leads as the hard layer).
 * Watching either format — desktop or iPhone — counts.
 */
export default function TrainingCourse({ accent = '#17C5B0' }: { accent?: string }) {
  const { rep } = useSalesAuth()
  const { state, refetch } = useTrainingProgress(rep)
  const [selected, setSelected] = useState<string | null>(null)
  const [format, setFormat] = useState<CourseFormat>('landscape')
  const [quizMode, setQuizMode] = useState(false)
  // Local watched flags: instant UX + keeps the course usable before the
  // progress migration is applied (state.available === false).
  const [localWatched, setLocalWatched] = useState<Record<string, boolean>>({})

  if (!rep) return null

  const passedCount = COURSE_MODULES.filter(m => state.byModule[m.id]?.passed).length
  const allPassed = passedCount === COURSE_MODULES.length
  const firstOpenIdx = COURSE_MODULES.findIndex(m => !state.byModule[m.id]?.passed)

  const stepUnlocked = (id: string) => {
    if (id === CONDUCT_STEP) return allPassed
    const idx = COURSE_MODULES.findIndex(m => m.id === id)
    return firstOpenIdx === -1 || idx <= firstOpenIdx
  }

  const defaultStep = allPassed
    ? CONDUCT_STEP
    : COURSE_MODULES[firstOpenIdx === -1 ? 0 : firstOpenIdx].id
  const activeStep = selected && stepUnlocked(selected) ? selected : defaultStep
  const activeModule = COURSE_MODULES.find(m => m.id === activeStep)

  const selectStep = (id: string) => {
    if (!stepUnlocked(id)) return
    setSelected(id)
    setQuizMode(false)
  }

  const totalSteps = COURSE_MODULES.length + 1
  const doneSteps = passedCount + (state.signedCurrent ? 1 : 0)

  const progress = activeModule ? state.byModule[activeModule.id] : undefined
  const watched = activeModule
    ? (progress?.video_watched ?? false) || (localWatched[activeModule.id] ?? false)
    : false
  const modulePassed = progress?.passed ?? false

  const handleVideoEnded = () => {
    if (!activeModule) return
    setLocalWatched(prev => ({ ...prev, [activeModule.id]: true }))
    markVideoWatched(rep, activeModule.id)
      .then(refetch)
      .catch(err => console.warn('[training] could not save watch progress:', err))
  }

  const handleQuizSubmit = async (score: number) => {
    if (!activeModule) return false
    let passed = score >= PASS_SCORE
    try {
      passed = await recordQuizAttempt(rep, activeModule.id, score, activeModule.quiz.length, progress)
    } catch (err) {
      console.warn('[training] could not save quiz attempt:', err)
    }
    if (!passed) setLocalWatched(prev => ({ ...prev, [activeModule.id]: false }))
    refetch()
    return passed
  }

  const handleQuizFinished = (passed: boolean) => {
    setQuizMode(false)
    if (passed) setSelected(null) // fall through to the next unlocked step
  }

  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
      <header className="flex flex-wrap items-center justify-between gap-2 mb-1">
        <div className="flex items-center gap-2.5">
          <GraduationCap size={18} style={{ color: accent }} />
          <h2 className="text-sm font-bold text-white">Training Course</h2>
        </div>
        <span className="text-[11px] text-white/40">
          {doneSteps}/{totalSteps} steps complete
        </span>
      </header>
      <p className="text-[11px] text-white/40 mb-4">
        Watch each video, pass its quiz ({PASS_SCORE}/4 to pass — fail and you rewatch), then sign
        the Code of Conduct. Finishing the course unlocks lead creation.
      </p>

      {!state.available && (
        <p className="mb-4 rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-[11px] text-amber-300/90">
          Progress tracking isn't live yet — videos and quizzes work, but your results won't be
          saved until the database update lands.
        </p>
      )}

      {state.courseComplete && (
        <p className="mb-4 flex items-center gap-2 rounded-lg border px-3 py-2 text-[11.5px] font-medium"
          style={{ borderColor: `${accent}44`, backgroundColor: `${accent}11`, color: accent }}>
          <CheckCircle2 size={14} /> Course complete — lead creation is unlocked.
        </p>
      )}

      {/* Step rail */}
      <div className="mb-4 flex flex-wrap gap-1.5">
        {COURSE_MODULES.map((m, i) => {
          const passed = state.byModule[m.id]?.passed
          const unlocked = stepUnlocked(m.id)
          const active = activeStep === m.id
          return (
            <button
              key={m.id}
              type="button"
              onClick={() => selectStep(m.id)}
              disabled={!unlocked}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-medium transition-colors ${
                active
                  ? 'border-white/30 bg-white/10 text-white'
                  : unlocked
                    ? 'border-white/10 bg-white/[0.02] text-white/60 hover:border-white/20 hover:text-white/90'
                    : 'border-white/5 bg-transparent text-white/25'
              }`}
            >
              {passed ? (
                <CheckCircle2 size={12} style={{ color: accent }} />
              ) : unlocked ? (
                <PlayCircle size={12} />
              ) : (
                <Lock size={11} />
              )}
              {i + 1}. {m.title}
            </button>
          )
        })}
        <button
          type="button"
          onClick={() => selectStep(CONDUCT_STEP)}
          disabled={!allPassed}
          className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-medium transition-colors ${
            activeStep === CONDUCT_STEP
              ? 'border-white/30 bg-white/10 text-white'
              : allPassed
                ? 'border-white/10 bg-white/[0.02] text-white/60 hover:border-white/20 hover:text-white/90'
                : 'border-white/5 bg-transparent text-white/25'
          }`}
        >
          {state.signedCurrent ? (
            <CheckCircle2 size={12} style={{ color: accent }} />
          ) : allPassed ? (
            <FileSignature size={12} />
          ) : (
            <Lock size={11} />
          )}
          6. Code of Conduct
        </button>
      </div>

      {/* Active step panel */}
      {activeStep === CONDUCT_STEP ? (
        <CodeOfConductCard
          rep={rep}
          signature={state.signature}
          signedCurrent={state.signedCurrent}
          accent={accent}
          onSigned={refetch}
        />
      ) : activeModule && quizMode && !modulePassed ? (
        <TrainingQuiz
          module={activeModule}
          accent={accent}
          onSubmit={handleQuizSubmit}
          onFinished={handleQuizFinished}
        />
      ) : activeModule ? (
        <div>
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[12px] text-white/60">{activeModule.blurb}</p>
            <div className="flex gap-1.5">
              {FORMATS.map(f => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setFormat(f.id)}
                  className={`flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10.5px] font-medium transition-colors ${
                    format === f.id
                      ? 'border-white/25 bg-white/10 text-white'
                      : 'border-white/5 text-white/45 hover:border-white/15 hover:text-white/75'
                  }`}
                >
                  <f.icon size={11} /> {f.label}
                </button>
              ))}
            </div>
          </div>

          <div
            className={`mx-auto overflow-hidden rounded-lg border border-white/10 bg-black ${
              format === 'landscape' ? 'w-full' : 'max-w-[300px]'
            }`}
          >
            <video
              key={`${activeModule.id}-${format}`}
              src={`${VIDEO_BASE}/${activeModule.files[format]}`}
              controls
              preload="metadata"
              playsInline
              onEnded={handleVideoEnded}
              className="block w-full"
            />
          </div>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            {modulePassed ? (
              <span className="flex items-center gap-1.5 text-[11.5px] font-medium" style={{ color: accent }}>
                <CheckCircle2 size={13} /> Passed
                {progress?.best_score != null && ` · best ${progress.best_score}/${activeModule.quiz.length}`}
                {' '}— review anytime
              </span>
            ) : (
              <>
                <span className="text-[11px] text-white/40">
                  {watched
                    ? 'Video watched — the quiz is open.'
                    : 'Watch the video to the end (any format) to unlock the quiz.'}
                  {progress && progress.attempts > 0 && ` Attempt ${progress.attempts + 1}.`}
                </span>
                <button
                  type="button"
                  onClick={() => setQuizMode(true)}
                  disabled={!watched}
                  className="rounded-lg px-4 py-2 text-xs font-semibold text-black transition-opacity disabled:opacity-35"
                  style={{ backgroundColor: accent }}
                >
                  Take the quiz
                </button>
              </>
            )}
          </div>
        </div>
      ) : null}
    </section>
  )
}
