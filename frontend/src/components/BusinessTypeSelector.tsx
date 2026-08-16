/**
 * The opening screen of the demo.
 *
 * This is the first thing a prospect sees and the only decision they make
 * before the product renders, so it does two jobs: it asks the question, and
 * it shows that the answer changes something. Ten trades grouped into four
 * families reads as "there is a version of this for me"; five loose tiles read
 * as a settings menu.
 *
 * Icons are stroke components, never emoji — a coloured glyph is the one thing
 * on this screen that cannot be themed, and it is the thing the eye lands on
 * first.
 *
 * MOTION. This is a once-per-visit surface, so a short entrance is worth it —
 * but a staggered reveal of ten cards is a delay before the prospect can act.
 * The stagger is 22ms and capped, the whole sequence is under 400ms, and it is
 * a fade with a small lift rather than anything that moves the hit target far.
 * Selection itself is instant: the check does not animate in, because a person
 * clicking through four options in a row would watch the same flourish four
 * times. All of it is off under prefers-reduced-motion.
 */
import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { clsx } from 'clsx'
import {
  BUSINESS_GROUPS, BUSINESS_TYPES, useDemoContext, type BusinessType,
} from '@/lib/demo-context'

export default function BusinessTypeSelector() {
  const { showSelector, setBusinessType } = useDemoContext()
  const [selected, setSelected] = useState<BusinessType | null>(null)

  if (!showSelector) return null

  const chosen = BUSINESS_TYPES.find((b) => b.id === selected)
  // One running index across every group so the stagger reads as a single
  // sequence rather than four sequences restarting.
  let order = 0

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
      <style>{`
        @keyframes mtdRise { from { opacity: 0; transform: translateY(6px) } to { opacity: 1; transform: none } }
        .mtd-rise { animation: mtdRise .26s cubic-bezier(.2,.7,.3,1) both }
        @media (prefers-reduced-motion: reduce) {
          .mtd-rise { animation: none }
        }
      `}</style>

      <div className="flex max-h-[92vh] w-full max-w-[940px] flex-col overflow-hidden rounded-2xl border border-[#1F1F23] bg-[#111113] shadow-2xl">
        <div className="px-6 pb-4 pt-8 text-center">
          <h2 className="text-xl font-bold text-[#F5F5F7] sm:text-2xl">
            What type of business are you?
          </h2>
          <p className="mt-2 text-sm text-[#A1A1A8]">
            Meridian is set up differently for each one. Pick yours and the demo
            opens the way your portal would.
          </p>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-2">
          {BUSINESS_GROUPS.map((group) => {
            const inGroup = BUSINESS_TYPES.filter((b) => b.group === group)
            if (inGroup.length === 0) return null
            return (
              <section key={group} className="mb-5 last:mb-2">
                <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6B6B73]">
                  {group}
                </h3>
                {/* Three across, because every group but Retail holds exactly
                    three: two columns left a single card stranded on its own
                    row under each heading, and the whole screen scrolled. */}
                <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 md:grid-cols-3">
                  {inGroup.map((bt) => {
                    const Icon = bt.icon
                    const isSelected = selected === bt.id
                    // Cap the delay so the last card is never a wait.
                    const delay = Math.min(order++ * 22, 260)
                    return (
                      <button
                        key={bt.id}
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => setSelected(bt.id)}
                        style={{ animationDelay: `${delay}ms` }}
                        className={clsx(
                          'mtd-rise group relative rounded-xl border p-3.5 text-left',
                          'transition-colors duration-150',
                          'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#17C5B0] focus-visible:ring-offset-2 focus-visible:ring-offset-[#111113]',
                          isSelected
                            ? 'border-[#17C5B0] bg-[#17C5B0]/5'
                            : 'border-[#1F1F23] bg-[#0A0A0B] hover:border-[#2A2A2E] hover:bg-[#141416]',
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <span
                            className={clsx(
                              'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors duration-150',
                              isSelected
                                ? 'border-[#17C5B0]/40 bg-[#17C5B0]/10 text-[#17C5B0]'
                                : 'border-[#1F1F23] bg-[#111113] text-[#A1A1A8] group-hover:text-[#F5F5F7]',
                            )}
                          >
                            <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
                          </span>
                          <div className="min-w-0 pr-5">
                            <p className={clsx(
                              'text-sm font-semibold transition-colors duration-150',
                              isSelected ? 'text-[#17C5B0]' : 'text-[#F5F5F7]',
                            )}>
                              {bt.label}
                            </p>
                            <p className="mt-0.5 text-xs leading-relaxed text-[#A1A1A8]/70">
                              {bt.description}
                            </p>
                          </div>
                        </div>
                        {isSelected && (
                          <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-[#17C5B0]">
                            <svg width="10" height="8" viewBox="0 0 10 8" fill="none" aria-hidden="true">
                              <path d="M1 4L3.5 6.5L9 1" stroke="#0A0A0B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>
              </section>
            )
          })}
        </div>

        <div className="flex shrink-0 items-center justify-between gap-4 border-t border-[#1F1F23] px-6 py-4">
          <p className="min-w-0 text-xs text-[#6B6B73]">
            {chosen
              ? <>Opening the <span className="text-[#A1A1A8]">{chosen.label}</span> version.</>
              : 'Pick a business type to continue.'}
          </p>
          <button
            type="button"
            disabled={!selected}
            onClick={() => selected && setBusinessType(selected)}
            className={clsx(
              'flex shrink-0 items-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold transition-colors duration-150',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#17C5B0] focus-visible:ring-offset-2 focus-visible:ring-offset-[#111113]',
              selected
                ? 'cursor-pointer bg-[#17C5B0] text-[#0A0A0B] hover:bg-[#17C5B0]/90'
                : 'cursor-not-allowed bg-[#1F1F23] text-[#A1A1A8]/40',
            )}
          >
            View My Demo
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  )
}
