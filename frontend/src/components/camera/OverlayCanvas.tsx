import { useEffect, useRef } from 'react'
import { type LayerState, type OverlayFrame, TIME_TOLERANCE_MS } from './overlay-layers'

const AMBER = '#F0B35B', TEAL = '#17C5B0', BLUE = '#1A8FD6', RED = '#E06B5E', PURPLE = '#9B7FD4'

/**
 * Draws the enabled overlay layers over the live <video>, scaled to its displayed size.
 * Coords are normalized 0..1 (resolution-independent). If the latest frame is older than
 * the tolerance window, the overlay fades + the parent can show an "analysis catching up"
 * chip (we just dim here). ponytail: one canvas, one rAF loop, no per-layer components.
 */
export default function OverlayCanvas({
  frame, layers, getVideoTime,
}: {
  frame: OverlayFrame | null
  layers: LayerState
  getVideoTime: () => number  // video presentation time in ms (for time-sync)
}) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const cv = ref.current
    if (!cv) return
    const ctx = cv.getContext('2d')
    if (!ctx) return
    let raf = 0

    const draw = () => {
      raf = requestAnimationFrame(draw)
      const parent = cv.parentElement
      if (!parent) return
      const w = parent.clientWidth, h = parent.clientHeight
      if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h }
      ctx.clearRect(0, 0, w, h)
      if (!frame) return

      // time-sync: dim if the analysis lags the video
      const lag = Math.abs(getVideoTime() - frame.frame_ts)
      ctx.globalAlpha = lag > TIME_TOLERANCE_MS ? 0.35 : 1
      const X = (n: number) => n * w
      const Y = (n: number) => n * h

      if (layers.heatmap && frame.heatmap) {
        const { grid, cols, rows } = frame.heatmap
        const cw = w / cols, ch = h / rows
        for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
          const v = grid[r]?.[c] ?? 0
          if (v <= 0) continue
          ctx.fillStyle = `rgba(240,179,91,${Math.min(0.5, v * 0.5)})`
          ctx.fillRect(c * cw, r * ch, cw, ch)
        }
      }
      if (layers.zones && frame.zones) for (const z of frame.zones) {
        ctx.strokeStyle = TEAL; ctx.lineWidth = 2; ctx.beginPath()
        z.polygon.forEach(([x, y], i) => i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y)))
        ctx.closePath(); ctx.stroke()
        if (z.count != null) { ctx.fillStyle = TEAL; ctx.font = '600 13px Inter'
          ctx.fillText(`${z.name}: ${z.count}`, X(z.polygon[0][0]) + 4, Y(z.polygon[0][1]) + 16) }
      }
      if (layers.journey && frame.journeys) for (const j of frame.journeys) {
        ctx.strokeStyle = BLUE; ctx.lineWidth = 2; ctx.beginPath()
        j.trail.forEach(([x, y], i) => i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y)))
        ctx.stroke()
      }
      if (layers.detections && frame.boxes) for (const b of frame.boxes) {
        ctx.strokeStyle = AMBER; ctx.lineWidth = 2
        ctx.strokeRect(X(b.x), Y(b.y), X(b.w), Y(b.h))
        if (b.conf != null) { ctx.fillStyle = AMBER; ctx.font = '600 11px Inter'
          ctx.fillText(`${Math.round(b.conf * 100)}%`, X(b.x), Y(b.y) - 4) }
      }
      if (layers.pose && frame.poses) for (const p of frame.poses) {
        ctx.fillStyle = TEAL
        for (const [x, y] of p.points) { ctx.beginPath(); ctx.arc(X(x), Y(y), 3, 0, 7); ctx.fill() }
        if (p.posture) { ctx.font = '500 11px Inter'; ctx.fillText(p.posture, X(p.points[0][0]), Y(p.points[0][1]) - 6) }
      }
      if (layers.identity && frame.ids) for (const idb of frame.ids) {
        ctx.fillStyle = PURPLE; ctx.font = '700 12px Inter'
        ctx.fillText(idb.badge, X(idb.x), Y(idb.y))
      }
      if (layers.pos_xref && frame.xref) for (const x of frame.xref) {
        ctx.fillStyle = TEAL; ctx.font = '700 12px Inter'
        const tag = x.checkedOut ? '✓ ' : ''
        const val = x.basketCents != null ? `$${(x.basketCents / 100).toFixed(0)}` : ''
        ctx.fillText(`${tag}${val}${x.items ? ` · ${x.items}` : ''}`, X(x.x), Y(x.y))
      }
      if (layers.exceptions && frame.exceptions) for (const ex of frame.exceptions) {
        ctx.fillStyle = RED; ctx.beginPath(); ctx.arc(X(ex.x), Y(ex.y), 7, 0, 7); ctx.fill()
        ctx.globalAlpha *= 0.5; ctx.beginPath(); ctx.arc(X(ex.x), Y(ex.y), 12, 0, 7); ctx.fill()
        ctx.globalAlpha = lag > TIME_TOLERANCE_MS ? 0.35 : 1
      }
      ctx.globalAlpha = 1
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [frame, layers, getVideoTime])

  return <canvas ref={ref} className="absolute inset-0 pointer-events-none" />
}
