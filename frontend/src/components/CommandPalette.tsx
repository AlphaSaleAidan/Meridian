import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, ArrowRight } from 'lucide-react'
import {
  LayoutDashboard, TrendingUp, Package, Layers, Lightbulb, LineChart,
  Bell, Settings, Bot, Target, Users, UserCheck, Clock, DollarSign,
  ChefHat, AlertTriangle, Box, Phone, Globe, Calendar, Video,
} from 'lucide-react'

interface SearchItem {
  path: string
  label: string
  group: string
  icon: typeof LayoutDashboard
  keywords?: string
}

const ITEMS: SearchItem[] = [
  { path: '', label: 'Overview', group: 'Dashboard', icon: LayoutDashboard, keywords: 'home dashboard main' },
  { path: 'revenue', label: 'Revenue', group: 'Intelligence', icon: TrendingUp, keywords: 'sales money income' },
  { path: 'insights', label: 'Insights', group: 'Intelligence', icon: Lightbulb, keywords: 'ai recommendations tips' },
  { path: 'actions', label: 'Top Actions', group: 'Intelligence', icon: Target, keywords: 'todo priority' },
  { path: 'forecasts', label: 'Forecasts', group: 'Intelligence', icon: LineChart, keywords: 'predictions future trends' },
  { path: 'anomalies', label: 'Anomalies', group: 'Intelligence', icon: AlertTriangle, keywords: 'alerts unusual spikes' },
  { path: 'products', label: 'Products', group: 'Operations', icon: Package, keywords: 'items catalog menu' },
  { path: 'margins', label: 'Margins', group: 'Operations', icon: DollarSign, keywords: 'profit cost pricing' },
  { path: 'menu-matrix', label: 'Menu Matrix', group: 'Operations', icon: ChefHat, keywords: 'engineering optimization' },
  { path: 'inventory', label: 'Inventory', group: 'Operations', icon: Layers, keywords: 'stock supply count' },
  { path: 'peak-hours', label: 'Peak Hours', group: 'Operations', icon: Clock, keywords: 'busy times traffic' },
  { path: 'customers', label: 'Customers', group: 'People', icon: Users, keywords: 'clients patrons' },
  { path: 'staff', label: 'Staff', group: 'People', icon: UserCheck, keywords: 'employees team workers' },
  { path: 'schedule', label: 'Schedule', group: 'People', icon: Calendar, keywords: 'shifts timetable roster' },
  { path: 'agents', label: 'AI Agents', group: 'Tools', icon: Bot, keywords: 'automation intelligence' },
  { path: 'camera-intelligence', label: 'Camera Intel', group: 'Tools', icon: Video, keywords: 'vision surveillance traffic' },
  { path: 'phone-orders', label: 'Phone Orders', group: 'Tools', icon: Phone, keywords: 'calls ordering voice' },
  { path: 'my-website', label: 'My Website', group: 'Tools', icon: Globe, keywords: 'site builder online' },
  { path: 'space', label: '3D Space', group: 'Tools', icon: Box, keywords: 'floor plan layout' },
  { path: 'notifications', label: 'Notifications', group: 'System', icon: Bell, keywords: 'alerts messages inbox' },
  { path: 'settings', label: 'Settings', group: 'System', icon: Settings, keywords: 'preferences config account' },
]

interface CommandPaletteProps {
  basePath: string
}

export default function CommandPalette({ basePath }: CommandPaletteProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selectedIdx, setSelectedIdx] = useState(0)
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(prev => !prev)
      }
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    if (open) {
      setQuery('')
      setSelectedIdx(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  const filtered = query.trim()
    ? ITEMS.filter(item => {
        const q = query.toLowerCase()
        return item.label.toLowerCase().includes(q)
          || item.group.toLowerCase().includes(q)
          || (item.keywords || '').includes(q)
      })
    : ITEMS

  const handleSelect = useCallback((item: SearchItem) => {
    const to = item.path ? `${basePath}/${item.path}` : basePath
    navigate(to)
    setOpen(false)
  }, [basePath, navigate])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIdx(prev => Math.min(prev + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIdx(prev => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter' && filtered[selectedIdx]) {
      handleSelect(filtered[selectedIdx])
    }
  }, [filtered, selectedIdx, handleSelect])

  useEffect(() => {
    setSelectedIdx(0)
  }, [query])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" onClick={() => setOpen(false)}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-md mx-4 bg-[#111113] border border-[#1F1F23] rounded-xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[#1F1F23]">
          <Search size={16} className="text-[#A1A1A8] flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            aria-label="Search commands"
            placeholder="Search pages..."
            className="flex-1 bg-transparent text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none"
          />
          <kbd className="hidden sm:inline-flex text-[10px] font-mono text-[#A1A1A8]/40 bg-[#0A0A0B] border border-[#1F1F23] px-1.5 py-0.5 rounded">
            ESC
          </kbd>
        </div>

        <div className="max-h-[300px] overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <p className="px-4 py-6 text-center text-xs text-[#A1A1A8]/40">No results found</p>
          ) : (
            filtered.map((item, i) => {
              const Icon = item.icon
              return (
                <button
                  key={item.path || '_root'}
                  onClick={() => handleSelect(item)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                    i === selectedIdx
                      ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]'
                      : 'text-[#A1A1A8] hover:bg-[#1F1F23]/60 hover:text-[#F5F5F7]'
                  }`}
                >
                  <Icon size={16} className="flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium">{item.label}</span>
                    <span className="text-[10px] ml-2 opacity-40">{item.group}</span>
                  </div>
                  {i === selectedIdx && <ArrowRight size={14} className="flex-shrink-0 opacity-40" />}
                </button>
              )
            })
          )}
        </div>

        <div className="flex items-center gap-3 px-4 py-2 border-t border-[#1F1F23] text-[10px] text-[#A1A1A8]/30">
          <span><kbd className="font-mono">↑↓</kbd> navigate</span>
          <span><kbd className="font-mono">↵</kbd> select</span>
          <span><kbd className="font-mono">esc</kbd> close</span>
        </div>
      </div>
    </div>
  )
}
