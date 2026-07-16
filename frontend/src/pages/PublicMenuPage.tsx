import { useState, useEffect, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { UtensilsCrossed } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || ''

/* ── Types (GET /api/menu/public/{slug}) ─────────────────────── */

interface PublicMenuItem {
  name: string
  description?: string
  price?: number
  category?: string
  sizes?: string[]
  size_prices?: Record<string, number>
  topping_price?: number
  sold_out: boolean
}

interface PublicMenu {
  slug: string
  business_name: string
  items: PublicMenuItem[]
  updated_at?: string
}

/** Price string rendered the same way the phone agent quotes it:
 *  per-size "medium $14 / large $18" else a single "$12.00". */
export function priceLabel(item: PublicMenuItem): string {
  const sp = item.size_prices
  if (sp && Object.keys(sp).length > 0) {
    const order = item.sizes?.length ? item.sizes : Object.keys(sp)
    const parts = order.filter(s => sp[s] != null).map(s => `${s} $${Number(sp[s]).toFixed(sp[s] % 1 ? 2 : 0)}`)
    let label = parts.join(' / ')
    if (item.topping_price) label += ` · +$${Number(item.topping_price).toFixed(item.topping_price % 1 ? 2 : 0)}/topping`
    return label
  }
  if (item.price != null && item.price > 0) return `$${Number(item.price).toFixed(2)}`
  return ''
}

/** Group items into ordered category sections ("Menu" catch-all last). */
export function groupByCategory(items: PublicMenuItem[]): Array<{ category: string; items: PublicMenuItem[] }> {
  const sections = new Map<string, PublicMenuItem[]>()
  for (const item of items) {
    const key = (item.category || '').trim() || 'Menu'
    if (!sections.has(key)) sections.set(key, [])
    sections.get(key)!.push(item)
  }
  const out = [...sections.entries()].map(([category, list]) => ({ category, items: list }))
  // Keep first-seen order but push the uncategorized catch-all to the end.
  return out.sort((a, b) => Number(a.category === 'Menu') - Number(b.category === 'Menu'))
}

/* ── Page ────────────────────────────────────────────────────── */

export default function PublicMenuPage() {
  const { slug } = useParams<{ slug: string }>()
  const [menu, setMenu] = useState<PublicMenu | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'notfound'>('loading')

  useEffect(() => {
    if (!slug) { setState('notfound'); return }
    let cancelled = false
    fetch(`${API_BASE}/api/menu/public/${slug}`)
      .then(res => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data: PublicMenu) => { if (!cancelled) { setMenu(data); setState('ready') } })
      .catch(() => { if (!cancelled) setState('notfound') })
    return () => { cancelled = true }
  }, [slug])

  useEffect(() => {
    if (menu?.business_name) document.title = `${menu.business_name} — Menu`
    return () => { document.title = 'Meridian' }
  }, [menu?.business_name])

  const sections = useMemo(() => groupByCategory(menu?.items || []), [menu?.items])

  if (state === 'loading') {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#17C5B0] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (state === 'notfound' || !menu) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center gap-3 px-6 text-center">
        <UtensilsCrossed size={28} className="text-[#A1A1A8]/50" />
        <h1 className="text-lg font-semibold text-[#F5F5F7]">Menu not found</h1>
        <p className="text-sm text-[#A1A1A8]">This menu isn't published or the link is out of date.</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Header */}
        <header className="mb-8 text-center">
          <p className="text-[10px] uppercase tracking-[0.25em] text-[#17C5B0] mb-2">Menu</p>
          <h1 className="text-2xl sm:text-3xl font-semibold">{menu.business_name || 'Our Menu'}</h1>
        </header>

        {/* Category sections */}
        {sections.length === 0 && (
          <p className="text-center text-sm text-[#A1A1A8] py-12">No items on the menu yet — check back soon.</p>
        )}
        <div className="space-y-8">
          {sections.map(section => (
            <section key={section.category}>
              <h2 className="text-xs font-semibold uppercase tracking-[0.15em] text-[#A1A1A8] border-b border-[#1F1F23] pb-2 mb-3">
                {section.category}
              </h2>
              <ul className="space-y-1">
                {section.items.map(item => (
                  <li
                    key={item.name}
                    className={`flex items-start justify-between gap-4 rounded-lg px-3 py-2.5 ${
                      item.sold_out ? 'opacity-45' : 'hover:bg-[#111113]'
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className={`text-sm font-medium ${item.sold_out ? 'line-through decoration-[#A1A1A8]/60' : ''}`}>
                          {item.name}
                        </p>
                        {item.sold_out && (
                          <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-[#2A2A30] text-[#A1A1A8] whitespace-nowrap">
                            Sold out today
                          </span>
                        )}
                      </div>
                      {item.description && (
                        <p className="text-xs text-[#A1A1A8] mt-0.5 leading-relaxed">{item.description}</p>
                      )}
                    </div>
                    <span className="text-sm font-mono text-[#17C5B0] whitespace-nowrap pt-0.5">
                      {priceLabel(item)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        {/* Footer */}
        <footer className="mt-12 pt-6 border-t border-[#1F1F23] text-center">
          <p className="text-[10px] text-[#A1A1A8]/50">
            Menu hosted by <span className="text-[#A1A1A8]">Meridian</span>
            {menu.updated_at ? ` · updated ${new Date(menu.updated_at).toLocaleDateString()}` : ''}
          </p>
        </footer>
      </div>
    </div>
  )
}
