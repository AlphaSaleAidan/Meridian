import { useEffect, useRef, useState } from 'react'

/**
 * Canada demo: replays a real YOLO+ByteTrack analysis (pre-computed, shipped as static
 * assets) over a CCTV-style clip, with live overlays + a named staff scorecard. The
 * detection/tracking/counts/grade are real model output; the scene is illustrative.
 * Used by LiveCamerasPage in demo mode so /canada/demo/camera shows the working tech.
 */
type Box = { id: number; x: number; y: number; w: number; h: number; conf: number }
type Frame = { t: number; boxes: Box[] }
type Staff = { id: string; score: number; grade: string; coverage_pct: number; customer_pct: number; engagement_pct: number; served: number }
type Data = { summary: { fps: number; duration_s: number; unique_people: number; peak_occupancy: number; entries: number; customers_served: number; staff: Staff[]; zones: { staff: number[][]; bar_front: number[][] } }; frames: Frame[] }

const STAFF_NAMES: Record<number, string> = { 7: 'Maria L.' } // demo roster; customers stay anonymous
// Every layer is real model output — these are the exact signals the edge agent
// turns into data (vision_traffic / vision_visits): tracks, zones, dwell, heat.
const LAYERS: [string, string][] = [['detections', 'Detections'], ['identity', 'Identity'], ['journey', 'Journey'], ['dwell', 'Dwell'], ['zones', 'Zones'], ['heatmap', 'Heatmap'], ['staff', 'Staff']]
const PRESETS: Record<string, string[]> = { Operations: ['detections', 'zones', 'heatmap'], 'Staff review': ['detections', 'staff', 'identity', 'zones'], 'Customer flow': ['detections', 'identity', 'journey', 'dwell'], All: LAYERS.map(l => l[0]), Raw: [] }

export default function CameraDemo() {
  const vidRef = useRef<HTMLVideoElement>(null)
  const cvRef = useRef<HTMLCanvasElement>(null)
  const [data, setData] = useState<Data | null>(null)
  const [layers, setLayers] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(LAYERS.map(l => [l[0], PRESETS.Operations.includes(l[0])])))
  const [occ, setOcc] = useState(0)
  const staffIds = useRef<Set<number>>(new Set())

  useEffect(() => {
    fetch('/camera-demo/tap-room.json').then(r => r.json()).then((d: Data) => {
      setData(d); staffIds.current = new Set(d.summary.staff.map(s => parseInt(s.id.slice(1))))
    }).catch(() => {})
  }, [])

  useEffect(() => {
    const cv = cvRef.current, vid = vidRef.current
    if (!cv || !vid || !data) return
    const ctx = cv.getContext('2d'); if (!ctx) return
    let raf = 0
    // Heatmap is derived from the (immutable) clip data — build once, not per frame.
    const heat = (() => {
      const cols = 24, rows = 14, g = Array.from({ length: rows }, () => new Array(cols).fill(0))
      data.frames.forEach(f => f.boxes.forEach(b => { g[Math.min(rows - 1, (b.y + b.h) * rows | 0)][Math.min(cols - 1, (b.x + b.w / 2) * cols | 0)]++ }))
      let mx = 1; g.forEach(r => r.forEach(v => mx = Math.max(mx, v))); return { g, cols, rows, mx }
    })()
    const rr = (x: number, y: number, w: number, h: number, r: number) => { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath() }
    const pill = (px: number, py: number, text: string, bg: string, fg: string) => { ctx.font = '700 12px Inter'; const tw = ctx.measureText(text).width, p = 6, h = 20; ctx.fillStyle = bg; rr(px, py - h, tw + p * 2, h, 6); ctx.fill(); ctx.fillStyle = fg; ctx.textBaseline = 'middle'; ctx.fillText(text, px + p, py - h / 2 + 1); ctx.textBaseline = 'alphabetic' }
    const poly = (pts: number[][], X: (n: number) => number, Y: (n: number) => number, stroke: string, fill: string) => { ctx.beginPath(); pts.forEach(([x, y], i) => i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y))); ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.setLineDash([7, 5]); ctx.stroke(); ctx.setLineDash([]) }
    const grade = data.summary.staff[0]?.grade ?? ''
    const fps = data.summary.fps
    // Dwell = frames since the track first appeared — same signal the edge agent
    // writes to vision_visits.dwell_seconds.
    const firstSeen = new Map<number, number>()
    data.frames.forEach((f, i) => f.boxes.forEach(b => { if (!firstSeen.has(b.id)) firstSeen.set(b.id, i) }))
    const inPoly = (px: number, py: number, pts: number[][]) => {
      let inside = false
      for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        const [xi, yi] = pts[i], [xj, yj] = pts[j]
        if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside
      }
      return inside
    }
    // --- Smoothing layer -------------------------------------------------
    // The clip data is keyframed at 24fps; drawing it raw makes boxes teleport on
    // any frame-skip and makes labels/counters flicker frame-to-frame. We keep a
    // per-id "rendered" state and ease it toward the current keyframe each rAF:
    // positions/size glide, confidence is damped, and boxes fade in/out instead of
    // popping. Frame-rate independent via exponential smoothing on dt.
    type RBox = { x: number; y: number; w: number; h: number; conf: number; op: number; live: boolean }
    const rboxes = new Map<number, RBox>()
    const ease = (cur: number, target: number, dt: number, tc: number) => cur + (target - cur) * (1 - Math.exp(-dt / tc))
    let occSmooth = -1, lastOccEmit = 0, last = 0
    const draw = (now: number) => {
      raf = requestAnimationFrame(draw)
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 0.016; last = now
      // Assigning canvas.width/height flushes the bitmap + resets all ctx state, so
      // only do it on an actual resize; clearRect handles the per-frame wipe.
      if (cv.width !== cv.clientWidth) cv.width = cv.clientWidth
      if (cv.height !== cv.clientHeight) cv.height = cv.clientHeight
      const w = cv.width, h = cv.height; ctx.clearRect(0, 0, w, h)
      const X = (n: number) => n * w, Y = (n: number) => n * h
      const k = Math.min(data.frames.length - 1, Math.round(vid.currentTime * fps) % data.frames.length)
      const fr = data.frames[k]
      // Ease + throttle the "in frame" counter so it reads as a calm live number
      // rather than flipping 10↔14 every animation frame.
      occSmooth = occSmooth < 0 ? fr.boxes.length : ease(occSmooth, fr.boxes.length, dt, 0.6)
      if (now - lastOccEmit > 1100) { lastOccEmit = now; const v = Math.round(occSmooth); setOcc(prev => prev === v ? prev : v) }
      // Reconcile rendered boxes against this keyframe's targets.
      rboxes.forEach(r => { r.live = false })
      fr.boxes.forEach(b => {
        let r = rboxes.get(b.id)
        if (!r) { r = { x: b.x, y: b.y, w: b.w, h: b.h, conf: b.conf, op: 0, live: true }; rboxes.set(b.id, r) }
        r.live = true
        r.x = ease(r.x, b.x, dt, 0.07); r.y = ease(r.y, b.y, dt, 0.07)
        r.w = ease(r.w, b.w, dt, 0.07); r.h = ease(r.h, b.h, dt, 0.07)
        r.conf = ease(r.conf, b.conf, dt, 0.45)
        r.op = ease(r.op, 1, dt, 0.12)
      })
      rboxes.forEach((r, id) => { if (!r.live) { r.op = ease(r.op, 0, dt, 0.14); if (r.op < 0.02) rboxes.delete(id) } })
      if (layers.heatmap) for (let r = 0; r < heat.rows; r++) for (let q = 0; q < heat.cols; q++) { const v = heat.g[r][q] / heat.mx; if (v > .05) { ctx.fillStyle = `rgba(240,140,70,${Math.min(.5, v * .7)})`; ctx.fillRect(q * w / heat.cols, r * h / heat.rows, w / heat.cols, h / heat.rows) } }
      if (layers.zones) {
        const inStaff = fr.boxes.filter(b => inPoly(b.x + b.w / 2, b.y + b.h, data.summary.zones.staff)).length
        const inBar = fr.boxes.filter(b => inPoly(b.x + b.w / 2, b.y + b.h, data.summary.zones.bar_front)).length
        poly(data.summary.zones.staff, X, Y, 'rgba(23,197,176,.9)', 'rgba(23,197,176,.10)')
        poly(data.summary.zones.bar_front, X, Y, 'rgba(26,143,214,.9)', 'rgba(26,143,214,.08)')
        pill(X(data.summary.zones.staff[0][0]), Y(data.summary.zones.staff[0][1]), `Staff zone · ${inStaff}`, '#17C5B0', '#04211c')
        pill(X(data.summary.zones.bar_front[0][0]), Y(data.summary.zones.bar_front[0][1]), `Bar · ${inBar}`, '#1A8FD6', '#03141f')
      }
      if (layers.journey) { ctx.strokeStyle = 'rgba(26,143,214,.8)'; ctx.lineWidth = 2.5; ctx.lineCap = 'round'; const hist: Record<number, number[][]> = {}; for (let j = Math.max(0, k - 26); j <= k; j++) data.frames[j].boxes.forEach(b => { (hist[b.id] = hist[b.id] || []).push([b.x + b.w / 2, b.y + b.h]) }); Object.values(hist).forEach(tr => { if (tr.length < 2) return; ctx.beginPath(); tr.forEach(([x, y], i) => i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y))); ctx.stroke() }) }
      rboxes.forEach((r, id) => {
        const isStaff = staffIds.current.has(id), x = X(r.x), y = Y(r.y), bw = X(r.w), bh = Y(r.h)
        ctx.globalAlpha = r.op < 0 ? 0 : r.op > 1 ? 1 : r.op
        if (layers.staff && isStaff) { ctx.save(); ctx.shadowColor = 'rgba(23,197,176,.7)'; ctx.shadowBlur = 10; ctx.strokeStyle = '#17C5B0'; ctx.lineWidth = 3; rr(x, y, bw, bh, 6); ctx.stroke(); ctx.restore(); pill(x, y - 4, (STAFF_NAMES[id] || ('STAFF #' + id)) + (grade ? ' · ' + grade : ''), '#17C5B0', '#04211c') }
        else if (layers.detections) { ctx.save(); ctx.shadowColor = 'rgba(240,179,91,.45)'; ctx.shadowBlur = 5; ctx.strokeStyle = '#F0B35B'; ctx.lineWidth = 2; rr(x, y, bw, bh, 5); ctx.stroke(); ctx.restore(); if (!layers.identity) pill(x, y - 4, Math.round(r.conf * 100) + '%', 'rgba(0,0,0,.5)', '#F0B35B') }
        if (layers.identity && !isStaff) pill(x, y + bh + 20, '#' + id, '#9B7FD4', '#fff')
        if (layers.dwell && !isStaff) {
          const dwellS = Math.max(0, Math.round((k - (firstSeen.get(id) ?? k)) / fps))
          pill(x, y + bh + (layers.identity ? 42 : 20), `⏱ ${Math.floor(dwellS / 60)}:${String(dwellS % 60).padStart(2, '0')}`, 'rgba(0,0,0,.55)', '#F5F5F7')
        }
      })
      ctx.globalAlpha = 1
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [data, layers])

  const s = data?.summary
  const staff = s?.staff?.[0]
  const setPreset = (name: string) => setLayers(Object.fromEntries(LAYERS.map(l => [l[0], PRESETS[name].includes(l[0])])))

  return (
    <div className="space-y-4" data-testid="camera-demo">
      <div>
        <h1 className="text-xl font-bold text-[#F5F5F7]">Camera intelligence — live</h1>
        <p className="text-[12px] text-[#A1A1A8] mt-0.5">Real-time person detection, tracking, zones &amp; staff grading — computed by the vision model (YOLO + ByteTrack), not mocked.</p>
      </div>
      <div className="grid lg:grid-cols-[1.55fr_1fr] gap-4">
        <div>
          <div className="relative rounded-2xl overflow-hidden border border-[#1F1F23] bg-black aspect-video">
            <video ref={vidRef} src="/camera-demo/tap-room.mp4" autoPlay muted loop playsInline className="absolute inset-0 w-full h-full object-cover" />
            <canvas ref={cvRef} className="absolute inset-0 w-full h-full pointer-events-none" />
            <div className="absolute top-2 left-2 px-2 py-1 rounded-lg bg-black/55 text-[12px] font-bold text-white flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#E06B5E] animate-pulse" />LIVE</div>
            <div className="absolute top-2 right-2 px-2.5 py-1 rounded-lg bg-black/55 text-[12px] font-bold text-white">{occ} in frame</div>
            <div className="absolute inset-0 pointer-events-none" style={{ boxShadow: 'inset 0 0 120px 24px rgba(0,0,0,.55)' }} />
            <div className="absolute bottom-2 left-3 font-mono text-[11px] text-white/70">CAM-01 · TAP ROOM</div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3" data-testid="camera-presets">
            {Object.keys(PRESETS).map(n => <button key={n} data-testid={`camera-preset-${n}`} onClick={() => setPreset(n)} className="px-3 py-1.5 rounded-full text-[11px] font-semibold border border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-all">{n}</button>)}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2" data-testid="camera-layers">
            {LAYERS.map(([k, lab]) => (
              <button key={k} data-testid={`camera-layer-${k}`} aria-pressed={!!layers[k]} onClick={() => setLayers(p => ({ ...p, [k]: !p[k] }))}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-left transition-all ${layers[k] ? 'bg-[#17C5B0]/15 border border-[#17C5B0]/40' : 'border border-[#1F1F23] hover:bg-[#1F1F23]'}`}>
                <span className={`w-2 h-2 rounded-full ${layers[k] ? 'bg-[#17C5B0]' : 'bg-[#A1A1A8]/30'}`} />
                <span className={`text-[12px] font-semibold ${layers[k] ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]'}`}>{lab}</span>
              </button>
            ))}
          </div>
          {s && <p className="text-[11px] text-[#A1A1A8]/60 mt-2.5 leading-relaxed">Model: YOLOv8 + ByteTrack · {s.fps} fps · {s.duration_s}s · {data!.frames.length} frames analyzed. Scene is illustrative; every overlay — detection, tracking, dwell, zones, heat &amp; grading — is real model output, the same signals your cameras turn into data.</p>}
        </div>
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl bg-[#111113] border border-[#1F1F23] p-4">
            <h3 className="text-[13px] font-bold text-[#F5F5F7] mb-2.5">Live data</h3>
            <div className="grid grid-cols-2 gap-2">
              {s && [['Peak occupancy', s.peak_occupancy], ['Unique people', s.unique_people], ['Entries', s.entries], ['Customers served', s.customers_served]].map(([l, v]) => (
                <div key={l} className="bg-[#0E0E10] border border-[#1F1F23] rounded-xl px-3 py-2"><b className="block text-xl font-extrabold text-[#F5F5F7]">{v}</b><span className="text-[10px] text-[#A1A1A8] uppercase tracking-wide">{l}</span></div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl bg-[#111113] border border-[#1F1F23] p-4">
            <h3 className="text-[13px] font-bold text-[#F5F5F7] mb-2.5">Staff grading</h3>
            {staff ? (<>
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center font-extrabold text-xl"
                  style={{ color: staff.grade === 'A' ? '#17C5B0' : staff.grade === 'B' ? '#5BC8A0' : '#F0B35B', background: '#17C5B033', border: '1px solid #17C5B066' }}>{staff.grade}</div>
                <div className="flex-1">
                  <div className="text-[13px] font-bold text-[#F5F5F7]">{STAFF_NAMES[parseInt(staff.id.slice(1))] || ('Bartender ' + staff.id)} · score {staff.score}/100</div>
                  {[['Station coverage', staff.coverage_pct, '#17C5B0'], ['Customer coverage', staff.customer_pct, '#17C5B0'], ['Engagement', staff.engagement_pct, '#F0B35B']].map(([l, v, c]) => (
                    <div key={l as string} className="flex items-center gap-2 text-[11px] text-[#A1A1A8] my-0.5"><span className="w-[88px] shrink-0">{l}</span><span className="h-1.5 rounded" style={{ width: `${v}%`, background: c as string }} />{v}%</div>
                  ))}
                </div>
              </div>
              <p className="text-[11px] text-[#A1A1A8]/70 mt-2.5">💡 {staff.engagement_pct < 45 ? 'Solid presence & coverage — coach to be more hands-on with customers.' : 'Good all-round; a small lift in proactive service pushes to an A.'}</p>
            </>) : <p className="text-[12px] text-[#A1A1A8]/60">Loading…</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
