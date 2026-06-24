// The 8 toggleable overlay layers + presets (Phase 5).
// Each maps to an existing swarm output (see docs/camera/streaming-overlays-plan.md).
// ponytail: plain data, no classes.

export type LayerKey =
  | 'detections' | 'pose' | 'identity' | 'journey'
  | 'zones' | 'heatmap' | 'pos_xref' | 'exceptions'

export interface LayerDef {
  key: LayerKey
  label: string
  hint: string
  gated?: boolean   // needs the analytics entitlement (server-enforced too)
}

export const LAYERS: LayerDef[] = [
  { key: 'detections', label: 'Detections', hint: 'Person boxes' },
  { key: 'pose', label: 'Pose', hint: 'Skeleton + posture' },
  { key: 'identity', label: 'Identity', hint: 'Anonymous re-ID badge', gated: true },
  { key: 'journey', label: 'Journey', hint: 'Movement trails' },
  { key: 'zones', label: 'Zones & counts', hint: 'Zone polygons + counters' },
  { key: 'heatmap', label: 'Heatmap', hint: 'Dwell / heat' },
  { key: 'pos_xref', label: 'POS x-ref', hint: 'Basket linked to a person', gated: true },
  { key: 'exceptions', label: 'Exceptions', hint: 'Anomaly markers', gated: true },
]

export type LayerState = Record<LayerKey, boolean>

const off = (): LayerState =>
  Object.fromEntries(LAYERS.map(l => [l.key, false])) as LayerState

export const PRESETS: Record<string, LayerState> = {
  Raw: off(),
  Operations: { ...off(), detections: true, zones: true, heatmap: true },
  'Loss Prevention': { ...off(), detections: true, identity: true, pos_xref: true, exceptions: true },
  All: Object.fromEntries(LAYERS.map(l => [l.key, true])) as LayerState,
}

// Mobile default: keep it light + legible.
export const MOBILE_DEFAULT = PRESETS.Operations

/** Per-camera overlay payload the swarm emits (time-aligned via frame_ts ms). */
export interface OverlayFrame {
  frame_ts: number
  boxes?: { id: number; x: number; y: number; w: number; h: number; conf?: number }[]
  poses?: { id: number; points: [number, number][]; posture?: string }[]
  ids?: { id: number; badge: string; x: number; y: number }[]
  journeys?: { id: number; trail: [number, number][] }[]
  zones?: { name: string; polygon: [number, number][]; count?: number }[]
  heatmap?: { grid: number[][]; cols: number; rows: number }
  xref?: { id: number; x: number; y: number; basketCents?: number; items?: number; checkedOut?: boolean }[]
  exceptions?: { id: number; x: number; y: number; kind: string }[]
}

// Coordinates from the swarm are normalized 0..1 (resolution-independent).
export const TIME_TOLERANCE_MS = 600  // fade overlays if agent output lags beyond this
