import { useMemo, useState } from 'react'

import { COST_ROWS } from './verticals'

/**
 * The section no competitor dares to ship: prices, side by side, with
 * per-minute economics. Only honest numbers — each row is public pricing
 * (theirs) or measured cost (ours). The slider answers the merchant's real
 * question ("what do missed calls cost ME?") with their own inputs, so the
 * output is their arithmetic, not our claim.
 */
export default function CostMath() {
  const [callsPerDay, setCallsPerDay] = useState(30)
  const [missedPct, setMissedPct] = useState(25)
  const [avgOrder, setAvgOrder] = useState(35)

  const monthly = useMemo(() => {
    const missedPerDay = (callsPerDay * missedPct) / 100
    // Not every missed call was an order; half is the conservative industry
    // assumption competitors also use — stated on-page, not hidden.
    return Math.round(missedPerDay * 0.5 * avgOrder * 30)
  }, [callsPerDay, missedPct, avgOrder])

  return (
    <div className="grid gap-8 lg:grid-cols-[1.2fr,1fr] lg:items-start">
      <div className="overflow-x-auto rounded-2xl border border-[#EAE5DC] bg-white shadow-[0_8px_30px_rgba(23,26,32,0.06)]">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead>
            <tr className="border-b border-[#EAE5DC] font-mono text-xs uppercase tracking-wider text-[#9BA0A8]">
              <th className="px-5 py-3.5 font-medium">Service</th>
              <th className="px-5 py-3.5 font-medium">Price</th>
              <th className="px-5 py-3.5 font-medium">Per minute</th>
              <th className="px-5 py-3.5 font-medium">What you get</th>
            </tr>
          </thead>
          <tbody>
            {COST_ROWS.map((row) => (
              <tr
                key={row.who}
                className={
                  row.who === 'Meridian'
                    ? 'border-b border-[#EAE5DC] bg-[#1A8FD6]/[0.08]'
                    : 'border-b border-[#EAE5DC] last:border-0'
                }
              >
                <td className="px-5 py-4 font-semibold text-[#171A20]">{row.who}</td>
                <td className="px-5 py-4 font-mono text-[#171A20]">{row.price}</td>
                <td className="px-5 py-4 font-mono text-[#171A20]">{row.perMin}</td>
                <td className="px-5 py-4 text-[#5B6069]">{row.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="border-t border-[#EAE5DC] px-5 py-3 text-xs text-[#9BA0A8]">
          Competitor pricing as publicly listed, Sept 2026. Our $0.104/min is measured
          cost of a live call through the whole stack — ask us to show the math.
        </p>
      </div>

      <div className="rounded-2xl border border-[#EAE5DC] bg-white p-6 shadow-[0_8px_30px_rgba(23,26,32,0.06)]">
        <h3 className="text-2xl font-extrabold tracking-tight text-[#171A20]">What do missed calls cost you?</h3>
        <div className="mt-5 space-y-5">
          {[
            { label: 'Calls per day', value: callsPerDay, set: setCallsPerDay, min: 5, max: 150, fmt: (v: number) => `${v}` },
            { label: 'Missed at peak', value: missedPct, set: setMissedPct, min: 5, max: 60, fmt: (v: number) => `${v}%` },
            { label: 'Average order', value: avgOrder, set: setAvgOrder, min: 10, max: 150, fmt: (v: number) => `$${v}` },
          ].map((s) => (
            <label key={s.label} className="block">
              <span className="flex items-baseline justify-between text-sm text-[#5B6069]">
                {s.label}
                <span className="font-mono text-[#171A20]">{s.fmt(s.value)}</span>
              </span>
              <input
                type="range"
                min={s.min}
                max={s.max}
                value={s.value}
                onChange={(e) => s.set(Number(e.target.value))}
                className="mt-2 w-full accent-[#1A8FD6]"
              />
            </label>
          ))}
        </div>
        <div className="mt-6 rounded-xl bg-[#171A20] px-5 py-4">
          <span className="font-mono text-xs uppercase tracking-widest text-white/60">
            Walking out the door, monthly
          </span>
          <div className="mt-1 text-4xl font-extrabold tracking-tight text-white">${monthly.toLocaleString()}</div>
          <p className="mt-1 text-xs text-white/60">
            assuming half of missed calls were orders — the conservative case
          </p>
        </div>
      </div>
    </div>
  )
}
