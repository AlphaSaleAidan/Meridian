import { LAYERS, PRESETS, type LayerKey, type LayerState } from './overlay-layers'

/**
 * Instrument-panel of overlay toggles + presets. Gated layers (identity / pos_xref /
 * exceptions) are disabled unless the org is entitled (allowedLayers, server-enforced).
 * ponytail: pure controlled component; persistence is the parent's job.
 */
export default function LayerManager({
  state, allowed, onChange,
}: {
  state: LayerState
  allowed: Set<LayerKey>
  onChange: (next: LayerState) => void
}) {
  const toggle = (k: LayerKey) => onChange({ ...state, [k]: !state[k] })
  const applyPreset = (name: string) => {
    // never enable a gated layer the org can't see
    const p = { ...PRESETS[name] }
    for (const l of LAYERS) if (l.gated && !allowed.has(l.key)) p[l.key] = false
    onChange(p)
  }

  return (
    <div className="rounded-2xl bg-[#0E0E10]/95 border border-[#1F1F23] p-3 backdrop-blur-sm">
      <div className="flex flex-wrap gap-1.5 mb-2.5">
        {Object.keys(PRESETS).map(name => (
          <button key={name} onClick={() => applyPreset(name)}
            className="px-2.5 py-1 rounded-full text-[11px] font-semibold border border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] active:scale-95 transition-all">
            {name}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {LAYERS.map(l => {
          const locked = l.gated && !allowed.has(l.key)
          const on = state[l.key] && !locked
          return (
            <button key={l.key} disabled={locked} onClick={() => toggle(l.key)}
              title={locked ? 'Upgrade required' : l.hint}
              className={`flex items-center gap-2 px-2.5 py-2 rounded-xl text-left transition-all ${
                locked ? 'opacity-40 cursor-not-allowed border border-[#1F1F23]'
                : on ? 'bg-[#17C5B0]/15 border border-[#17C5B0]/40'
                : 'border border-[#1F1F23] hover:bg-[#1F1F23]'
              }`}>
              <span className={`w-2 h-2 rounded-full shrink-0 ${on ? 'bg-[#17C5B0]' : 'bg-[#A1A1A8]/30'}`} />
              <span className="min-w-0">
                <span className={`block text-[12px] font-semibold truncate ${on ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]'}`}>{l.label}{l.gated ? ' ★' : ''}</span>
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
