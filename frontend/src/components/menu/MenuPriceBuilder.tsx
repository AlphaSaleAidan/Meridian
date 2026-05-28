import { useState, useMemo, useCallback } from 'react'
import { clsx } from 'clsx'
import {
  Plus, Upload, Trash2, ArrowUpDown, ChevronDown,
  Lightbulb, TrendingUp, AlertTriangle, XCircle, Star,
  HelpCircle, Truck, Check, X,
} from 'lucide-react'
import type { MenuQuadrant } from '@/lib/agent-data'

// ─── Types ──────────────────────────────────────────────────

interface PriceBuilderItem {
  id: string
  name: string
  category: string
  recipeCost: number
  currentPrice: number
  monthlySales: number
  aiSuggestion: string
}

type SortField = 'name' | 'category' | 'recipeCost' | 'currentPrice' | 'foodCostPct' | 'margin' | 'monthlySales' | 'quadrant'
type SortDir = 'asc' | 'desc'

const CATEGORIES = ['Mains', 'Starters', 'Sides', 'Dessert', 'Drinks', 'Specials'] as const

// ─── Helpers ────────────────────────────────────────────────

function uid(): string {
  return Math.random().toString(36).slice(2, 10)
}

function foodCostPct(recipeCost: number, price: number): number {
  return price > 0 ? (recipeCost / price) * 100 : 0
}

function margin(recipeCost: number, price: number): number {
  return price - recipeCost
}

function classifyQuadrant(itemMargin: number, sales: number, avgMargin: number, avgSales: number): MenuQuadrant {
  if (sales >= avgSales && itemMargin >= avgMargin) return 'star'
  if (sales < avgSales && itemMargin >= avgMargin) return 'puzzle'
  if (sales >= avgSales && itemMargin < avgMargin) return 'plowhorse'
  return 'dog'
}

function foodCostColor(pct: number): string {
  if (pct <= 30) return '#17C5B0'
  if (pct <= 35) return '#F59E0B'
  return '#EF4444'
}

function usd(n: number): string {
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function usdCompact(n: number): string {
  if (n >= 1000) return '$' + (n / 1000).toFixed(1) + 'k'
  return '$' + n.toFixed(0)
}

const quadrantCfg: Record<MenuQuadrant, { label: string; color: string; bg: string; icon: typeof Star }> = {
  star:      { label: 'Star',      color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10', icon: Star },
  puzzle:    { label: 'Puzzle',    color: 'text-[#7C5CFF]', bg: 'bg-[#7C5CFF]/10',  icon: HelpCircle },
  plowhorse: { label: 'Plowhorse', color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10', icon: Truck },
  dog:       { label: 'Dog',       color: 'text-[#A1A1A8]', bg: 'bg-[#A1A1A8]/10',  icon: XCircle },
}

// ─── Demo data ──────────────────────────────────────────────

function createDemoItems(): PriceBuilderItem[] {
  return [
    { id: uid(), name: 'House Burger',          category: 'Mains',    recipeCost: 4.50, currentPrice: 14.99, monthlySales: 340, aiSuggestion: 'Star item — raise to $16.49. Demand won\'t drop. Est. +$4,380/yr' },
    { id: uid(), name: 'Grilled Salmon',        category: 'Mains',    recipeCost: 8.20, currentPrice: 24.99, monthlySales: 210, aiSuggestion: 'Healthy margin. Consider a lunch portion at $18.99 to boost volume' },
    { id: uid(), name: 'Truffle Fries',          category: 'Sides',    recipeCost: 2.80, currentPrice: 11.99, monthlySales: 45,  aiSuggestion: 'Puzzle — high margin but underordered. Add a photo on the menu' },
    { id: uid(), name: 'Caesar Salad',           category: 'Starters', recipeCost: 2.10, currentPrice: 10.99, monthlySales: 280, aiSuggestion: 'Solid plowhorse. Raise price to $11.99 gradually' },
    { id: uid(), name: 'Chicken Wings (12pc)',   category: 'Starters', recipeCost: 4.90, currentPrice: 15.99, monthlySales: 310, aiSuggestion: 'Star — protect placement. Never discount' },
    { id: uid(), name: 'Margherita Pizza',       category: 'Mains',    recipeCost: 3.20, currentPrice: 13.99, monthlySales: 260, aiSuggestion: 'Good margin. Bundle with a drink for +$2 avg check' },
    { id: uid(), name: 'Garden Salad',           category: 'Starters', recipeCost: 1.80, currentPrice: 8.99,  monthlySales: 30,  aiSuggestion: 'Dog — low margin, low sales. Replace with a seasonal special' },
    { id: uid(), name: 'Fish Tacos',             category: 'Mains',    recipeCost: 5.10, currentPrice: 14.49, monthlySales: 180, aiSuggestion: 'Plowhorse — popular but tight margin. Raise to $15.99' },
    { id: uid(), name: 'Chocolate Lava Cake',    category: 'Dessert',  recipeCost: 2.40, currentPrice: 9.99,  monthlySales: 75,  aiSuggestion: 'Puzzle — high margin dessert. Train servers to suggest it' },
    { id: uid(), name: 'Craft IPA Pint',         category: 'Drinks',   recipeCost: 1.50, currentPrice: 7.99,  monthlySales: 380, aiSuggestion: 'Star — huge margin, top seller. Feature on tap board' },
    { id: uid(), name: 'House Lemonade',         category: 'Drinks',   recipeCost: 0.60, currentPrice: 4.49,  monthlySales: 220, aiSuggestion: 'Excellent margin. Offer refills to increase perceived value' },
    { id: uid(), name: 'Mac & Cheese',           category: 'Sides',    recipeCost: 1.90, currentPrice: 7.49,  monthlySales: 150, aiSuggestion: 'Plowhorse — add bacon for $2 more to boost margin' },
    { id: uid(), name: 'Loaded Nachos',          category: 'Starters', recipeCost: 4.20, currentPrice: 12.99, monthlySales: 40,  aiSuggestion: 'Dog — cost is high for the return. Simplify recipe or remove' },
    { id: uid(), name: 'NY Cheesecake',          category: 'Dessert',  recipeCost: 2.00, currentPrice: 8.99,  monthlySales: 55,  aiSuggestion: 'Puzzle — pair with coffee as a combo to drive orders' },
    { id: uid(), name: 'Ribeye Steak (12oz)',    category: 'Specials', recipeCost: 12.50, currentPrice: 34.99, monthlySales: 95, aiSuggestion: 'Premium anchor item. Keeps other prices looking reasonable' },
  ]
}

// ─── Inline edit cell ───────────────────────────────────────

function EditableText({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const commit = () => { onChange(draft); setEditing(false) }
  if (!editing) return <span className="cursor-pointer hover:text-[#1A8FD6] transition-colors" onClick={() => { setDraft(value); setEditing(true) }}>{value}</span>
  return <input autoFocus value={draft} onChange={e => setDraft(e.target.value)} onBlur={commit} onKeyDown={e => e.key === 'Enter' && commit()} className="w-full bg-[#0A0A0B] border border-[#1A8FD6] rounded px-1.5 py-0.5 text-[#F5F5F7] text-xs font-medium outline-none" />
}

function EditableDollar({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value.toFixed(2))
  const commit = () => { const n = parseFloat(draft); onChange(isNaN(n) ? 0 : Math.max(0, n)); setEditing(false) }
  if (!editing) return <span className="cursor-pointer hover:text-[#1A8FD6] transition-colors font-mono" onClick={() => { setDraft(value.toFixed(2)); setEditing(true) }}>{usd(value)}</span>
  return <input autoFocus type="number" step="0.01" min="0" value={draft} onChange={e => setDraft(e.target.value)} onBlur={commit} onKeyDown={e => e.key === 'Enter' && commit()} className="w-20 bg-[#0A0A0B] border border-[#1A8FD6] rounded px-1.5 py-0.5 text-[#F5F5F7] text-xs font-mono outline-none" />
}

function EditableNumber({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(value))
  const commit = () => { const n = parseInt(draft, 10); onChange(isNaN(n) ? 0 : Math.max(0, n)); setEditing(false) }
  if (!editing) return <span className="cursor-pointer hover:text-[#1A8FD6] transition-colors font-mono" onClick={() => { setDraft(String(value)); setEditing(true) }}>{value.toLocaleString()}</span>
  return <input autoFocus type="number" step="1" min="0" value={draft} onChange={e => setDraft(e.target.value)} onBlur={commit} onKeyDown={e => e.key === 'Enter' && commit()} className="w-20 bg-[#0A0A0B] border border-[#1A8FD6] rounded px-1.5 py-0.5 text-[#F5F5F7] text-xs font-mono outline-none" />
}

function CategorySelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1 text-xs text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
        {value} <ChevronDown size={10} />
      </button>
      {open && (
        <div className="absolute z-20 top-full left-0 mt-1 bg-[#131316] border border-[#1F1F23] rounded-lg shadow-xl py-1 min-w-[120px]">
          {CATEGORIES.map(c => (
            <button key={c} onClick={() => { onChange(c); setOpen(false) }} className={clsx('block w-full text-left px-3 py-1.5 text-xs hover:bg-[#1F1F23] transition-colors', c === value ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]')}>
              {c}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Bulk actions bar ───────────────────────────────────────

function BulkBar({ count, onAdjust, onCategory, onClear }: { count: number; onAdjust: () => void; onCategory: () => void; onClear: () => void }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 rounded-lg">
      <span className="text-xs font-medium text-[#1A8FD6]">{count} selected</span>
      <button onClick={onAdjust} className="text-[10px] font-medium text-[#F5F5F7] bg-[#1F1F23] hover:bg-[#2A2A30] px-2.5 py-1 rounded transition-colors">Adjust Price</button>
      <button onClick={onCategory} className="text-[10px] font-medium text-[#F5F5F7] bg-[#1F1F23] hover:bg-[#2A2A30] px-2.5 py-1 rounded transition-colors">Change Category</button>
      <button onClick={onClear} className="ml-auto text-[10px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">Clear</button>
    </div>
  )
}

// ─── Bulk adjust modal ──────────────────────────────────────

function BulkAdjustModal({ onApply, onClose }: { onApply: (mode: 'pct' | 'dollar', val: number) => void; onClose: () => void }) {
  const [mode, setMode] = useState<'pct' | 'dollar'>('pct')
  const [val, setVal] = useState('5')
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[#131316] border border-[#1F1F23] rounded-xl p-5 w-[340px] shadow-2xl">
        <h3 className="text-sm font-semibold text-[#F5F5F7] mb-3">Adjust Prices</h3>
        <div className="flex gap-2 mb-3">
          <button onClick={() => setMode('pct')} className={clsx('text-[11px] px-3 py-1.5 rounded', mode === 'pct' ? 'bg-[#1A8FD6] text-white' : 'bg-[#1F1F23] text-[#A1A1A8]')}>Percentage</button>
          <button onClick={() => setMode('dollar')} className={clsx('text-[11px] px-3 py-1.5 rounded', mode === 'dollar' ? 'bg-[#1A8FD6] text-white' : 'bg-[#1F1F23] text-[#A1A1A8]')}>Dollar Amount</button>
        </div>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs text-[#A1A1A8]">{mode === 'pct' ? '+/- %' : '+/- $'}</span>
          <input type="number" value={val} onChange={e => setVal(e.target.value)} className="flex-1 bg-[#0A0A0B] border border-[#1F1F23] rounded px-2 py-1.5 text-xs font-mono text-[#F5F5F7] outline-none focus:border-[#1A8FD6]" />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="text-[11px] px-3 py-1.5 text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">Cancel</button>
          <button onClick={() => { const n = parseFloat(val); if (!isNaN(n)) onApply(mode, n) }} className="text-[11px] px-3 py-1.5 bg-[#1A8FD6] text-white rounded hover:bg-[#1574B8] transition-colors">Apply</button>
        </div>
      </div>
    </div>
  )
}

function BulkCategoryModal({ onApply, onClose }: { onApply: (cat: string) => void; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[#131316] border border-[#1F1F23] rounded-xl p-5 w-[300px] shadow-2xl">
        <h3 className="text-sm font-semibold text-[#F5F5F7] mb-3">Change Category</h3>
        <div className="space-y-1">
          {CATEGORIES.map(c => (
            <button key={c} onClick={() => onApply(c)} className="block w-full text-left px-3 py-2 text-xs text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] rounded transition-colors">{c}</button>
          ))}
        </div>
        <div className="flex justify-end mt-3">
          <button onClick={onClose} className="text-[11px] px-3 py-1.5 text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">Cancel</button>
        </div>
      </div>
    </div>
  )
}

// ─── Main component ─────────────────────────────────────────

export default function MenuPriceBuilder() {
  const [items, setItems] = useState<PriceBuilderItem[]>(createDemoItems)
  const [sortField, setSortField] = useState<SortField>('monthlySales')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [filterCat, setFilterCat] = useState<string>('All')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [showAdjust, setShowAdjust] = useState(false)
  const [showCatModal, setShowCatModal] = useState(false)

  // Computed averages for quadrant classification
  const avgMargin = useMemo(() => {
    if (items.length === 0) return 0
    return items.reduce((s, i) => s + margin(i.recipeCost, i.currentPrice), 0) / items.length
  }, [items])

  const avgSales = useMemo(() => {
    if (items.length === 0) return 0
    return items.reduce((s, i) => s + i.monthlySales, 0) / items.length
  }, [items])

  const getQuadrant = useCallback((item: PriceBuilderItem): MenuQuadrant => {
    return classifyQuadrant(margin(item.recipeCost, item.currentPrice), item.monthlySales, avgMargin, avgSales)
  }, [avgMargin, avgSales])

  // Filter + sort
  const displayed = useMemo(() => {
    let list = filterCat === 'All' ? [...items] : items.filter(i => i.category === filterCat)
    list.sort((a, b) => {
      let av: number | string = 0, bv: number | string = 0
      switch (sortField) {
        case 'name': av = a.name.toLowerCase(); bv = b.name.toLowerCase(); break
        case 'category': av = a.category; bv = b.category; break
        case 'recipeCost': av = a.recipeCost; bv = b.recipeCost; break
        case 'currentPrice': av = a.currentPrice; bv = b.currentPrice; break
        case 'foodCostPct': av = foodCostPct(a.recipeCost, a.currentPrice); bv = foodCostPct(b.recipeCost, b.currentPrice); break
        case 'margin': av = margin(a.recipeCost, a.currentPrice); bv = margin(b.recipeCost, b.currentPrice); break
        case 'monthlySales': av = a.monthlySales; bv = b.monthlySales; break
        case 'quadrant': av = getQuadrant(a); bv = getQuadrant(b); break
      }
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    return list
  }, [items, filterCat, sortField, sortDir, getQuadrant])

  // Summary stats
  const stats = useMemo(() => {
    const totalItems = items.length
    const avgFoodCost = totalItems > 0 ? items.reduce((s, i) => s + foodCostPct(i.recipeCost, i.currentPrice), 0) / totalItems : 0
    const monthlyRevenue = items.reduce((s, i) => s + i.currentPrice * i.monthlySales, 0)
    const opportunities = items.filter(i => i.aiSuggestion.length > 0).length
    return { totalItems, avgFoodCost, monthlyRevenue, opportunities }
  }, [items])

  // Pricing opportunities
  const topOpportunities = useMemo(() => {
    return [
      { text: 'Raise House Burger from $14.99 to $16.49 (+$1.50) — Star item, demand won\'t drop. Est. +$4,380/yr', impact: 4380, type: 'raise' as const },
      { text: 'Consider removing Garden Salad (Dog) — low margin, low sales. Replace with a seasonal special.', impact: 0, type: 'remove' as const },
      { text: 'Truffle Fries is a Puzzle — try repositioning on menu with a photo. High margin but underordered.', impact: 1800, type: 'reposition' as const },
      { text: 'Fish Tacos: raise from $14.49 to $15.99 (+$1.50). Popular plowhorse, small increase goes unnoticed. Est. +$3,240/yr', impact: 3240, type: 'raise' as const },
      { text: 'Bundle NY Cheesecake + coffee as a $12.99 combo. Currently sells 55/mo separately — combo could push 90/mo.', impact: 2400, type: 'reposition' as const },
    ]
  }, [])

  // Mutations
  const updateItem = (id: string, patch: Partial<PriceBuilderItem>) => {
    setItems(prev => prev.map(i => i.id === id ? { ...i, ...patch } : i))
  }
  const deleteItem = (id: string) => {
    setItems(prev => prev.filter(i => i.id !== id))
    setSelected(prev => { const next = new Set(prev); next.delete(id); return next })
  }
  const addItem = () => {
    setItems(prev => [...prev, { id: uid(), name: 'New Item', category: 'Mains', recipeCost: 0, currentPrice: 0, monthlySales: 0, aiSuggestion: '' }])
  }

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortDir('desc') }
  }

  const toggleSelect = (id: string) => {
    setSelected(prev => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next })
  }
  const toggleSelectAll = () => {
    if (selected.size === displayed.length) setSelected(new Set())
    else setSelected(new Set(displayed.map(i => i.id)))
  }

  const applyBulkAdjust = (mode: 'pct' | 'dollar', val: number) => {
    setItems(prev => prev.map(i => {
      if (!selected.has(i.id)) return i
      const newPrice = mode === 'pct' ? i.currentPrice * (1 + val / 100) : i.currentPrice + val
      return { ...i, currentPrice: Math.max(0, Math.round(newPrice * 100) / 100) }
    }))
    setShowAdjust(false)
  }

  const applyBulkCategory = (cat: string) => {
    setItems(prev => prev.map(i => selected.has(i.id) ? { ...i, category: cat } : i))
    setShowCatModal(false)
  }

  const SortHeader = ({ field, children, className }: { field: SortField; children: React.ReactNode; className?: string }) => (
    <th className={clsx('py-2.5 px-2 text-[10px] font-medium text-[#A1A1A8] cursor-pointer select-none hover:text-[#F5F5F7] transition-colors whitespace-nowrap', className)} onClick={() => toggleSort(field)}>
      <span className="inline-flex items-center gap-0.5">
        {children}
        <ArrowUpDown size={9} className={sortField === field ? 'text-[#1A8FD6]' : 'opacity-30'} />
      </span>
    </th>
  )

  return (
    <div className="space-y-5">
      {/* Summary stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Total Items" value={String(stats.totalItems)} />
        <StatCard label="Avg Food Cost %" value={stats.avgFoodCost.toFixed(1) + '%'} color={foodCostColor(stats.avgFoodCost)} />
        <StatCard label="Monthly Revenue" value={usdCompact(stats.monthlyRevenue)} color="#17C5B0" />
        <StatCard label="Pricing Opportunities" value={String(stats.opportunities)} color="#7C5CFF" />
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <select
            value={filterCat}
            onChange={e => setFilterCat(e.target.value)}
            className="appearance-none bg-[#131316] border border-[#1F1F23] text-xs text-[#A1A1A8] rounded-lg pl-3 pr-7 py-2 outline-none focus:border-[#1A8FD6] transition-colors cursor-pointer"
          >
            <option value="All">All Categories</option>
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <ChevronDown size={10} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#A1A1A8] pointer-events-none" />
        </div>
        <div className="ml-auto flex gap-2">
          <button
            className="group relative flex items-center gap-1.5 text-[11px] font-medium text-[#A1A1A8] bg-[#131316] border border-[#1F1F23] rounded-lg px-3 py-2 opacity-50 cursor-not-allowed"
            disabled
          >
            <Upload size={12} /> Import from POS
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-[#0A0A0B] border border-[#1F1F23] rounded text-[10px] text-[#A1A1A8] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
              Connect POS to import your menu
            </span>
          </button>
          <button onClick={addItem} className="flex items-center gap-1.5 text-[11px] font-medium text-[#F5F5F7] bg-[#1A8FD6] hover:bg-[#1574B8] rounded-lg px-3 py-2 transition-colors">
            <Plus size={12} /> Add Item
          </button>
        </div>
      </div>

      {/* Bulk bar */}
      {selected.size > 0 && (
        <BulkBar
          count={selected.size}
          onAdjust={() => setShowAdjust(true)}
          onCategory={() => setShowCatModal(true)}
          onClear={() => setSelected(new Set())}
        />
      )}

      {/* Table */}
      <div className="overflow-x-auto -mx-4 sm:mx-0 rounded-lg border border-[#1F1F23]">
        <table className="w-full min-w-[900px] text-xs">
          <thead className="bg-[#131316] border-b border-[#1F1F23]">
            <tr>
              <th className="py-2.5 px-2 w-8">
                <input type="checkbox" checked={displayed.length > 0 && selected.size === displayed.length} onChange={toggleSelectAll} className="accent-[#1A8FD6] w-3.5 h-3.5 cursor-pointer" />
              </th>
              <SortHeader field="name" className="text-left">Item Name</SortHeader>
              <SortHeader field="category" className="text-left">Category</SortHeader>
              <SortHeader field="recipeCost" className="text-right">Recipe Cost</SortHeader>
              <SortHeader field="currentPrice" className="text-right">Current Price</SortHeader>
              <SortHeader field="foodCostPct" className="text-right">Food Cost %</SortHeader>
              <SortHeader field="margin" className="text-right">Margin</SortHeader>
              <SortHeader field="monthlySales" className="text-right">Mo. Sales</SortHeader>
              <SortHeader field="quadrant" className="text-center">Quadrant</SortHeader>
              <th className="py-2.5 px-2 text-[10px] font-medium text-[#A1A1A8] text-left">AI Suggestion</th>
              <th className="py-2.5 px-2 w-10" />
            </tr>
          </thead>
          <tbody>
            {displayed.map(item => {
              const fc = foodCostPct(item.recipeCost, item.currentPrice)
              const mg = margin(item.recipeCost, item.currentPrice)
              const q = getQuadrant(item)
              const qcfg = quadrantCfg[q]
              const QIcon = qcfg.icon
              return (
                <tr key={item.id} className="border-b border-[#1F1F23] hover:bg-[#1A8FD6]/[0.03] transition-colors">
                  <td className="py-2 px-2">
                    <input type="checkbox" checked={selected.has(item.id)} onChange={() => toggleSelect(item.id)} className="accent-[#1A8FD6] w-3.5 h-3.5 cursor-pointer" />
                  </td>
                  <td className="py-2 px-2 text-[#F5F5F7] font-medium">
                    <EditableText value={item.name} onChange={v => updateItem(item.id, { name: v })} />
                  </td>
                  <td className="py-2 px-2">
                    <CategorySelect value={item.category} onChange={v => updateItem(item.id, { category: v })} />
                  </td>
                  <td className="py-2 px-2 text-right">
                    <EditableDollar value={item.recipeCost} onChange={v => updateItem(item.id, { recipeCost: v })} />
                  </td>
                  <td className="py-2 px-2 text-right">
                    <EditableDollar value={item.currentPrice} onChange={v => updateItem(item.id, { currentPrice: v })} />
                  </td>
                  <td className="py-2 px-2 text-right font-mono" style={{ color: foodCostColor(fc) }}>
                    {fc.toFixed(1)}%
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-[#F5F5F7]">
                    {usd(mg)}
                  </td>
                  <td className="py-2 px-2 text-right">
                    <EditableNumber value={item.monthlySales} onChange={v => updateItem(item.id, { monthlySales: v })} />
                  </td>
                  <td className="py-2 px-2 text-center">
                    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium', qcfg.bg, qcfg.color)}>
                      <QIcon size={9} /> {qcfg.label}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-[10px] text-[#A1A1A8] max-w-[200px] truncate" title={item.aiSuggestion}>
                    {item.aiSuggestion || '—'}
                  </td>
                  <td className="py-2 px-2">
                    <button onClick={() => deleteItem(item.id)} className="text-[#A1A1A8]/40 hover:text-[#EF4444] transition-colors p-1">
                      <Trash2 size={12} />
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {displayed.length === 0 && (
          <div className="py-12 text-center text-xs text-[#A1A1A8]">
            No items {filterCat !== 'All' ? `in "${filterCat}"` : ''} — click "Add Item" to get started
          </div>
        )}
      </div>

      {/* AI Pricing Suggestions */}
      <div className="card p-4 sm:p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-7 h-7 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
            <Lightbulb size={14} className="text-[#7C5CFF]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">AI Pricing Suggestions</h3>
            <p className="text-[10px] text-[#A1A1A8]">Top opportunities based on your menu data</p>
          </div>
        </div>
        <div className="space-y-3">
          {topOpportunities.map((opp, i) => (
            <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
              <div className={clsx('w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5', opp.type === 'raise' ? 'bg-[#17C5B0]/10' : opp.type === 'remove' ? 'bg-[#EF4444]/10' : 'bg-[#1A8FD6]/10')}>
                {opp.type === 'raise' ? <TrendingUp size={12} className="text-[#17C5B0]" /> : opp.type === 'remove' ? <AlertTriangle size={12} className="text-[#EF4444]" /> : <Lightbulb size={12} className="text-[#1A8FD6]" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-[#F5F5F7] leading-relaxed">{opp.text}</p>
              </div>
              {opp.impact > 0 && (
                <span className="text-[10px] font-mono font-medium text-[#17C5B0] bg-[#17C5B0]/10 px-2 py-0.5 rounded-full whitespace-nowrap flex-shrink-0">
                  +${opp.impact.toLocaleString()}/yr
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Modals */}
      {showAdjust && <BulkAdjustModal onApply={applyBulkAdjust} onClose={() => setShowAdjust(false)} />}
      {showCatModal && <BulkCategoryModal onApply={applyBulkCategory} onClose={() => setShowCatModal(false)} />}
    </div>
  )
}

// ─── Stat card (local) ──────────────────────────────────────

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="card p-4">
      <p className="text-[10px] text-[#A1A1A8] mb-1">{label}</p>
      <p className="text-lg font-bold font-mono" style={color ? { color } : { color: '#F5F5F7' }}>{value}</p>
    </div>
  )
}
