import { useEffect, useState } from 'react'
import { UtensilsCrossed, Plus, Trash2, Save, Loader2, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react'
import { phoneService } from '@/lib/phone-service'

interface EditableItem {
  name: string
  price: string   // string while editing; parsed on save
  category: string
  sizes?: string[]
}

/**
 * Menu editor on the merchant home page: the phone agent's ported menu
 * (POS sync / photo scan / wizard) shown as editable rows so the merchant can
 * correct names, prices, and categories without re-running the setup wizard.
 * Saves straight back to phone_agent_config.menu_items.
 */
export default function MenuEditorCard({ orgId }: { orgId: string }) {
  const [items, setItems] = useState<EditableItem[]>([])
  const [exists, setExists] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let alive = true
    phoneService.getConfig(orgId).then(cfg => {
      if (!alive) return
      setExists(!!cfg.exists)
      setItems((cfg.menu_items || []).map((m: any) => ({
        name: String(m.name || ''),
        price: m.price != null ? String(m.price) : '',
        category: String(m.category || ''),
        sizes: Array.isArray(m.sizes) ? m.sizes : undefined,
      })))
      setLoading(false)
    })
    return () => { alive = false }
  }, [orgId])

  const edit = (i: number, field: keyof EditableItem, value: string) => {
    setItems(prev => prev.map((it, idx) => (idx === i ? { ...it, [field]: value } : it)))
    setDirty(true); setSaved(false)
  }
  const remove = (i: number) => { setItems(prev => prev.filter((_, idx) => idx !== i)); setDirty(true); setSaved(false) }
  const add = () => { setItems(prev => [...prev, { name: '', price: '', category: '' }]); setDirty(true); setSaved(false); setExpanded(true) }

  const save = async () => {
    setSaving(true)
    const menu_items = items
      .filter(it => it.name.trim())
      .map(it => ({
        name: it.name.trim(),
        ...(it.price.trim() && !Number.isNaN(parseFloat(it.price)) ? { price: parseFloat(it.price) } : {}),
        ...(it.category.trim() ? { category: it.category.trim() } : {}),
        ...(it.sizes?.length ? { sizes: it.sizes } : {}),
      }))
    const ok = await phoneService.saveConfig({ merchant_id: orgId, menu_items })
    setSaving(false)
    if (ok) { setSaved(true); setDirty(false) }
  }

  // No phone agent yet → nothing to edit; keep the home page clean.
  if (loading || !exists) return null

  const shown = expanded ? items : items.slice(0, 5)

  return (
    <div className="card p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20 flex items-center justify-center">
            <UtensilsCrossed size={14} className="text-[#17C5B0]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Phone Agent Menu</h3>
            <p className="text-[10px] text-[#A1A1A8]">{items.length} items — what the AI reads to callers. Fix anything that ported wrong.</p>
          </div>
        </div>
        <button
          onClick={save}
          disabled={saving || !dirty}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-[#17C5B0] text-white hover:bg-[#17C5B0]/90 disabled:opacity-40 transition-colors"
        >
          {saving ? <Loader2 size={12} className="animate-spin" /> : saved ? <CheckCircle2 size={12} /> : <Save size={12} />}
          {saving ? 'Saving…' : saved ? 'Saved' : 'Save menu'}
        </button>
      </div>

      <div className="space-y-1.5">
        {shown.map((it, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              className="flex-1 px-2.5 py-1.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-xs text-[#F5F5F7] focus:outline-none focus:border-[#17C5B0]/50"
              value={it.name} placeholder="Item name"
              onChange={e => edit(i, 'name', e.target.value)}
            />
            <div className="relative w-24">
              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-[#A1A1A8]">$</span>
              <input
                className="w-full pl-5 pr-2 py-1.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-xs text-[#F5F5F7] focus:outline-none focus:border-[#17C5B0]/50"
                value={it.price} placeholder="0.00" inputMode="decimal"
                onChange={e => edit(i, 'price', e.target.value)}
              />
            </div>
            <input
              className="w-28 px-2.5 py-1.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-xs text-[#F5F5F7] focus:outline-none focus:border-[#17C5B0]/50 hidden sm:block"
              value={it.category} placeholder="Category"
              onChange={e => edit(i, 'category', e.target.value)}
            />
            <button onClick={() => remove(i)} className="p-1.5 text-[#A1A1A8] hover:text-red-400 transition-colors" aria-label="Remove item">
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <button onClick={add} className="flex items-center gap-1 text-xs text-[#17C5B0] hover:text-[#17C5B0]/80">
          <Plus size={12} /> Add item
        </button>
        {items.length > 5 && (
          <button onClick={() => setExpanded(v => !v)} className="flex items-center gap-1 text-[10px] text-[#A1A1A8] hover:text-[#F5F5F7]">
            {expanded ? <><ChevronUp size={11} /> Show less</> : <><ChevronDown size={11} /> Show all {items.length}</>}
          </button>
        )}
      </div>
    </div>
  )
}
