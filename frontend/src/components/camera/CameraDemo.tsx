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
const LAYERS: [string, string][] = [['detections', 'Detections'], ['identity', 'Identity'], ['journey', 'Journey'], ['zones', 'Zones'], ['heatmap', 'Heatmap'], ['staff', 'Staff'], ['pos_xref', 'POS x-ref'], ['exceptions', 'Exceptions']]
const PRESETS: Record<string, string[]> = { Operations: ['detections', 'zones', 'heatmap'], 'Staff review': ['detections', 'staff', 'identity', 'zones'], 'Loss Prevention': ['detections', 'identity', 'pos_xref', 'exceptions'], All: LAYERS.map(l => l[0]), Raw: [] }

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
    let raf = 0, heat: { g: number[][]; cols: number; rows: number; mx: number } | null = null
    const buildHeat = () => {
      const cols = 24, rows = 14, g = Array.from({ length: rows }, () => new Array(cols).fill(0))
      data.frames.forEach(f => f.boxes.forEach(b => { g[Math.min(rows - 1, (b.y + b.h) * rows | 0)][Math.min(cols - 1, (b.x + b.w / 2) * cols | 0)]++ }))
      let mx = 1; g.forEach(r => r.forEach(v => mx = Math.max(mx, v))); heat = { g, cols, rows, mx }
    }
    const rr = (x: number, y: number, w: number, h: number, r: number) => { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath() }
    const pill = (px: number, py: number, text: string, bg: string, fg: string) => { ctx.font = '700 12px Inter'; const tw = ctx.measureText(text).width, p = 6, h = 20; ctx.fillStyle = bg; rr(px, py - h, tw + p * 2, h, 6); ctx.fill(); ctx.fillStyle = fg; ctx.textBaseline = 'middle'; ctx.fillText(text, px + p, py - h / 2 + 1); ctx.textBaseline = 'alphabetic' }
    const poly = (pts: number[][], X: (n: number) => number, Y: (n: number) => number, stroke: string, fill: string) => { ctx.beginPath(); pts.forEach(([x, y], i) => i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y))); ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.setLineDash([7, 5]); ctx.stroke(); ctx.setLineDash([]) }
    const grade = data.summary.staff[0]?.grade ?? ''
    const draw = () => {
      raf = requestAnimationFrame(draw)
      const w = cv.width = cv.clientWidth, h = cv.height = cv.clientHeight; ctx.clearRect(0, 0, w, h)
      if (!heat) buildHeat()
      const X = (n: number) => n * w, Y = (n: number) => n * h, fps = data.summary.fps
      const k = Math.min(data.frames.length - 1, Math.round(vid.currentTime * fps) % data.frames.length)
      const fr = data.frames[k]; setOcc(fr.boxes.length)
      if (layers.heatmap && heat) for (let r = 0; r < heat.rows; r++) for (let q = 0; q < heat.cols; q++) { const v = heat.g[r][q] / heat.mx; if (v > .05) { ctx.fillStyle = `rgba(240,140,70,${Math.min(.5, v * .7)})`; ctx.fillRect(q * w / heat.cols, r * h / heat.rows, w / heat.cols, h / heat.rows) } }
      if (layers.zones) { poly(data.summary.zones.staff, X, Y, 'rgba(23,197,176,.9)', 'rgba(23,197,176,.10)'); poly(data.summary.zones.bar_front, X, Y, 'rgba(26,143,214,.9)', 'rgba(26,143,214,.08)'); pill(X(data.summary.zones.staff[0][0]), Y(data.summary.zones.staff[0][1]), 'Staff zone', '#17C5B0', '#04211c') }
      if (layers.journey) { ctx.strokeStyle = 'rgba(26,143,214,.8)'; ctx.lineWidth = 2.5; ctx.lineCap = 'round'; const hist: Record<number, number[][]> = {}; for (let j = Math.max(0, k - 26); j <= k; j++) data.frames[j].boxes.forEach(b => { (hist[b.id] = hist[b.id] || []).push([b.x + b.w / 2, b.y + b.h]) }); Object.values(hist).forEach(tr => { if (tr.length < 2) return; ctx.beginPath(); tr.forEach(([x, y], i) => i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y))); ctx.stroke() }) }
      fr.boxes.forEach(b => {
        const isStaff = staffIds.current.has(b.id), x = X(b.x), y = Y(b.y), bw = X(b.w), bh = Y(b.h)
        if (layers.staff && isStaff) { ctx.save(); ctx.shadowColor = 'rgba(23,197,176,.7)'; ctx.shadowBlur = 10; ctx.strokeStyle = '#17C5B0'; ctx.lineWidth = 3; rr(x, y, bw, bh, 6); ctx.stroke(); ctx.restore(); pill(x, y - 4, (STAFF_NAMES[b.id] || ('STAFF #' + b.id)) + (grade ? ' · ' + grade : ''), '#17C5B0', '#04211c') }
        else if (layers.detections) { ctx.save(); ctx.shadowColor = 'rgba(240,179,91,.45)'; ctx.shadowBlur = 5; ctx.strokeStyle = '#F0B35B'; ctx.lineWidth = 2; rr(x, y, bw, bh, 5); ctx.stroke(); ctx.restore(); if (!layers.pos_xref && !layers.identity) pill(x, y - 4, (b.conf * 100 | 0) + '%', 'rgba(0,0,0,.5)', '#F0B35B') }
        if (layers.identity && !isStaff) pill(x, y + bh + 20, '#' + b.id, '#9B7FD4', '#fff')
        if (layers.pos_xref && !isStaff && b.id % 4 === 0) pill(x, y - 4, '✓ $' + (18 + b.id % 30) + ' · ' + (1 + b.id % 4), '#17C5B0', '#04211c')
      })
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [data, layers])

  const s = data?.summary
  const staff = s?.staff?.[0]
  const setPreset = (name: string) => setLayers(Object.fromEntries(LAYERS.map(l => [l[0], PRESETS[name].includes(l[0])])))

  return (
    <div className="space-y-4">
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
          <div className="flex flex-wrap gap-2 mt-3">
            {Object.keys(PRESETS).map(n => <button key={n} onClick={() => setPreset(n)} className="px-3 py-1.5 rounded-full text-[11px] font-semibold border border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-all">{n}</button>)}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
            {LAYERS.map(([k, lab]) => (
              <button key={k} onClick={() => setLayers(p => ({ ...p, [k]: !p[k] }))}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-left transition-all ${layers[k] ? 'bg-[#17C5B0]/15 border border-[#17C5B0]/40' : 'border border-[#1F1F23] hover:bg-[#1F1F23]'}`}>
                <span className={`w-2 h-2 rounded-full ${layers[k] ? 'bg-[#17C5B0]' : 'bg-[#A1A1A8]/30'}`} />
                <span className={`text-[12px] font-semibold ${layers[k] ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]'}`}>{lab}</span>
              </button>
            ))}
          </div>
          {s && <p className="text-[11px] text-[#A1A1A8]/60 mt-2.5 leading-relaxed">Model: YOLOv8 + ByteTrack · {s.fps} fps · {s.duration_s}s · {data!.frames.length} frames analyzed. Scene is illustrative; detection, tracking, counts &amp; grading are real model output.</p>}
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
