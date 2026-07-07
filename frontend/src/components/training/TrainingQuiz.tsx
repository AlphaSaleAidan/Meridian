import { useState } from 'react'
import { CheckCircle2, RotateCcw, XCircle } from 'lucide-react'
import { PASS_SCORE, type CourseModule } from './course-data'

/**
 * 10-question module quiz. Answers are graded client-side; the parent persists
 * the attempt. On a fail (<PASS_SCORE) the parent resets video_watched so the
 * rep has to rewatch before retaking. Wrong questions are highlighted after
 * submit but the correct answers are never revealed — the video has them.
 */
export default function TrainingQuiz({
  module,
  accent,
  onSubmit,
  onFinished,
}: {
  module: CourseModule
  accent: string
  onSubmit: (score: number) => Promise<boolean>
  onFinished: (passed: boolean) => void
}) {
  const [answers, setAnswers] = useState<(number | null)[]>(module.quiz.map(() => null))
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ score: number; passed: boolean; wrong: number[] } | null>(null)

  const allAnswered = answers.every(a => a !== null)

  const handleSubmit = async () => {
    if (!allAnswered || saving) return
    const wrong: number[] = []
    module.quiz.forEach((q, i) => {
      if (answers[i] !== q.answer) wrong.push(i)
    })
    const score = module.quiz.length - wrong.length
    setSaving(true)
    try {
      const passed = await onSubmit(score)
      setResult({ score, passed, wrong })
    } finally {
      setSaving(false)
    }
  }

  if (result) {
    return (
      <div className="rounded-lg border border-white/10 bg-white/[0.02] p-5 text-center">
        {result.passed ? (
          <>
            <CheckCircle2 size={28} className="mx-auto mb-2" style={{ color: accent }} />
            <p className="text-sm font-bold text-white">
              Passed — {result.score}/{module.quiz.length}
            </p>
            <p className="text-[11px] text-white/40 mt-1">Nice. The next module is unlocked.</p>
            <button
              type="button"
              onClick={() => onFinished(true)}
              className="mt-4 rounded-lg px-4 py-2 text-xs font-semibold text-black"
              style={{ backgroundColor: accent }}
            >
              Continue
            </button>
          </>
        ) : (
          <>
            <XCircle size={28} className="mx-auto mb-2 text-amber-400" />
            <p className="text-sm font-bold text-white">
              {result.score}/{module.quiz.length} — you need {PASS_SCORE} to pass
            </p>
            <p className="text-[11px] text-white/40 mt-1">
              The {result.wrong.length} highlighted question{result.wrong.length === 1 ? '' : 's'} tripped you up.
              Rewatch the video — every answer is in it — then retake the quiz.
            </p>
            <button
              type="button"
              onClick={() => onFinished(false)}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-amber-400/40 px-4 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-400/10"
            >
              <RotateCcw size={13} /> Rewatch the video
            </button>
            <div className="mt-5 space-y-2 text-left">
              {result.wrong.map(i => (
                <div key={i} className="rounded-md border border-amber-400/20 bg-amber-400/5 px-3 py-2">
                  <span className="text-[11px] text-amber-200/90">
                    Q{i + 1}. {module.quiz[i].q}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-[11px] text-white/40">
        {module.quiz.length} questions · pass with {PASS_SCORE}/{module.quiz.length} · fail and you rewatch the video
      </p>
      {module.quiz.map((q, qi) => (
        <fieldset key={qi} className="rounded-lg border border-white/10 bg-white/[0.02] p-3.5">
          <legend className="sr-only">Question {qi + 1}</legend>
          <p className="text-[12.5px] font-medium text-white/90 mb-2">
            {qi + 1}. {q.q}
          </p>
          <div className="space-y-1.5">
            {q.options.map((opt, oi) => (
              <label
                key={oi}
                className={`flex cursor-pointer items-start gap-2 rounded-md border px-3 py-2 text-[12px] leading-snug transition-colors ${
                  answers[qi] === oi
                    ? 'border-white/25 bg-white/10 text-white'
                    : 'border-white/5 bg-white/[0.01] text-white/60 hover:border-white/15 hover:text-white/85'
                }`}
              >
                <input
                  type="radio"
                  name={`q-${module.id}-${qi}`}
                  checked={answers[qi] === oi}
                  onChange={() =>
                    setAnswers(prev => {
                      const next = [...prev]
                      next[qi] = oi
                      return next
                    })
                  }
                  className="mt-0.5 accent-current"
                />
                <span>{opt}</span>
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!allAnswered || saving}
        className="w-full rounded-lg px-4 py-2.5 text-xs font-semibold text-black transition-opacity disabled:opacity-40"
        style={{ backgroundColor: accent }}
      >
        {saving ? 'Scoring…' : allAnswered ? 'Submit answers' : `Answer all ${module.quiz.length} questions to submit`}
      </button>
    </div>
  )
}
