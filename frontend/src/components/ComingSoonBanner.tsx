import { Clock } from 'lucide-react'

/**
 * Roadmap marker for the Canada demo's Coming Soon pillars.
 *
 * The page below renders for real so a prospect can see what is being built,
 * which makes it essential that the surface says plainly that it is not part
 * of the product they would be buying today. Kept deliberately quiet — one
 * teal rule, no gradient, no badge animation — so it reads as a note on the
 * page rather than a promotion.
 */
export default function ComingSoonBanner({ label, sampleData = false }: { label: string; sampleData?: boolean }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-[#1F1F23] border-l-2 border-l-[#17C5B0] bg-[#111113] px-4 py-3">
      <Clock size={15} className="mt-0.5 flex-shrink-0 text-[#17C5B0]" aria-hidden />
      <div className="min-w-0">
        <p className="text-[13px] font-semibold text-[#F5F5F7]">
          {label} is coming soon
        </p>
        <p className="mt-0.5 text-[12px] leading-relaxed text-[#A1A1A8]">
          A preview of what we're building next — it isn't part of the current
          Meridian plan.{sampleData ? ' The figures below are sample data.' : ''}
        </p>
      </div>
    </div>
  )
}
