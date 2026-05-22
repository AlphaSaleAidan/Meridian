import { NavLink, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, TrendingUp, Lightbulb, Target, Bot,
  MoreHorizontal, X, Users, Package, DollarSign, LineChart,
  Clock, UserCheck, Calendar, Layers, AlertTriangle, Phone,
  Globe, Bell, Settings, Video, Box, ChefHat, Star,
} from 'lucide-react'
import { useState, useEffect, useRef, useCallback } from 'react'
import { useUnreadNotifications } from '@/hooks/useUnreadNotifications'

interface TabItem { path: string; icon: typeof LayoutDashboard; label: string }

const ALL_ITEMS: TabItem[] = [
  { path: '', icon: LayoutDashboard, label: 'Home' },
  { path: 'revenue', icon: TrendingUp, label: 'Revenue' },
  { path: 'insights', icon: Lightbulb, label: 'Insights' },
  { path: 'actions', icon: Target, label: 'Actions' },
  { path: 'agents', icon: Bot, label: 'AI Agents' },
  { path: 'camera-intelligence', icon: Video, label: 'Camera Intel' },
  { path: 'customers', icon: Users, label: 'Customers' },
  { path: 'products', icon: Package, label: 'Products' },
  { path: 'margins', icon: DollarSign, label: 'Margins' },
  { path: 'forecasts', icon: LineChart, label: 'Forecasts' },
  { path: 'peak-hours', icon: Clock, label: 'Peak Hours' },
  { path: 'staff', icon: UserCheck, label: 'Staff' },
  { path: 'schedule', icon: Calendar, label: 'Schedule' },
  { path: 'inventory', icon: Layers, label: 'Inventory' },
  { path: 'anomalies', icon: AlertTriangle, label: 'Anomalies' },
  { path: 'menu-matrix', icon: ChefHat, label: 'Menu Matrix' },
  { path: 'phone-orders', icon: Phone, label: 'Phone Orders' },
  { path: 'my-website', icon: Globe, label: 'My Website' },
  { path: 'space', icon: Box, label: '3D Space' },
  { path: 'notifications', icon: Bell, label: 'Notifications' },
  { path: 'settings', icon: Settings, label: 'Settings' },
]

const STORAGE_KEY = 'meridian_nav_favorites'
const DEFAULT_FAVS = ['', 'revenue', 'insights', 'actions']
const MAX_FAVS = 4

function loadFavorites(): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (Array.isArray(raw) && raw.length <= MAX_FAVS && raw[0] === '') return raw
  } catch { /* ignore */ }
  return DEFAULT_FAVS
}

interface MobileNavBarProps { basePath: string }

export default function MobileNavBar({ basePath }: MobileNavBarProps) {
  const [moreOpen, setMoreOpen] = useState(false)
  const [customizeOpen, setCustomizeOpen] = useState(false)
  const [favorites, setFavorites] = useState(loadFavorites)
  const [hint, setHint] = useState('')
  const location = useLocation()
  const { unreadCount } = useUnreadNotifications()
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => { setMoreOpen(false); setCustomizeOpen(false) }, [location.pathname])

  useEffect(() => {
    if (!hint) return
    const t = setTimeout(() => setHint(''), 2000)
    return () => clearTimeout(t)
  }, [hint])

  const saveFavorites = useCallback((next: string[]) => {
    setFavorites(next)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }, [])

  const toggleFavorite = useCallback((path: string) => {
    if (path === '') return // Home is permanent
    setFavorites(prev => {
      if (prev.includes(path)) {
        const next = prev.filter(p => p !== path)
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
        return next
      }
      if (prev.length >= MAX_FAVS) { setHint('Remove a tab first (max 4)'); return prev }
      const next = [...prev, path]
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const startLongPress = useCallback(() => {
    longPressTimer.current = setTimeout(() => { setCustomizeOpen(true) }, 500)
  }, [])
  const cancelLongPress = useCallback(() => {
    if (longPressTimer.current) { clearTimeout(longPressTimer.current); longPressTimer.current = null }
  }, [])

  const primaryTabs = ALL_ITEMS.filter(i => favorites.includes(i.path))
    .sort((a, b) => favorites.indexOf(a.path) - favorites.indexOf(b.path))
  const currentPath = location.pathname.replace(basePath + '/', '').replace(basePath, '')
  const nonPrimaryPaths = new Set(favorites)
  const moreItems = ALL_ITEMS.filter(i => !nonPrimaryPaths.has(i.path))
  const isMoreActive = moreItems.some(i => i.path === currentPath)

  const overlayOpen = moreOpen || customizeOpen

  return (
    <>
      {overlayOpen && (
        <div className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm lg:hidden" onClick={() => { setMoreOpen(false); setCustomizeOpen(false) }}>
          <div
            className="absolute bottom-0 left-0 right-0 bg-[#111113] border-t border-[#1F1F23] rounded-t-2xl max-h-[70vh] overflow-y-auto pb-[max(env(safe-area-inset-bottom),16px)]"
            onClick={e => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-[#111113] px-4 pt-3 pb-2 border-b border-[#1F1F23] flex items-center justify-between z-10">
              <span className="text-sm font-semibold text-[#F5F5F7]">
                {customizeOpen ? 'Customize Tabs' : 'All Features'}
              </span>
              <button
                onClick={() => { setMoreOpen(false); setCustomizeOpen(false) }}
                className="p-2 rounded-full bg-[#1F1F23] text-[#A1A1A8]"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            {customizeOpen ? (
              <div className="px-3 pt-2 pb-3">
                {hint && (
                  <div className="mb-2 text-center text-xs text-amber-400 py-1.5 bg-amber-400/10 rounded-lg">{hint}</div>
                )}
                <p className="text-[11px] text-[#A1A1A8] mb-2 px-1">Star up to 4 items for your tab bar. Home is always first.</p>
                {ALL_ITEMS.map(item => {
                  const Icon = item.icon
                  const starred = favorites.includes(item.path)
                  const isHome = item.path === ''
                  return (
                    <button
                      key={item.path || '_home'}
                      onClick={() => toggleFavorite(item.path)}
                      disabled={isHome}
                      className={clsx(
                        'flex items-center w-full gap-3 px-3 py-2.5 rounded-xl transition-colors',
                        isHome ? 'opacity-60 cursor-default' : 'active:bg-[#1F1F23]',
                      )}
                    >
                      <Icon size={18} className={starred ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'} />
                      <span className={clsx('flex-1 text-left text-sm', starred ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>
                        {item.label}
                      </span>
                      <Star
                        size={18}
                        className={starred ? 'text-[#1A8FD6] fill-[#1A8FD6]' : 'text-[#A1A1A8]'}
                      />
                    </button>
                  )
                })}
                <button
                  onClick={() => setCustomizeOpen(false)}
                  className="mt-3 w-full py-2.5 rounded-xl bg-[#1A8FD6] text-white text-sm font-semibold"
                >
                  Done
                </button>
              </div>
            ) : (
              <>
                <button
                  onClick={() => { setMoreOpen(false); setCustomizeOpen(true) }}
                  className="mx-3 mt-2 mb-1 px-3 py-2 rounded-xl bg-[#1F1F23] text-[#1A8FD6] text-xs font-medium w-[calc(100%-24px)] text-center"
                >
                  Customize tabs
                </button>
                <div className="grid grid-cols-4 gap-1 p-3">
                  {moreItems.map(item => {
                    const Icon = item.icon
                    const to = item.path ? `${basePath}/${item.path}` : basePath
                    return (
                      <NavLink
                        key={item.path}
                        to={to}
                        className={({ isActive }) => clsx(
                          'flex flex-col items-center gap-1.5 py-3 px-1 rounded-xl transition-colors min-h-[72px] justify-center',
                          isActive ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]' : 'text-[#A1A1A8] active:bg-[#1F1F23]',
                        )}
                      >
                        <span className="relative">
                          <Icon size={20} />
                          {item.path === 'notifications' && unreadCount > 0 && (
                            <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
                              {unreadCount > 9 ? '9+' : unreadCount}
                            </span>
                          )}
                        </span>
                        <span className="text-[10px] font-medium leading-tight text-center">{item.label}</span>
                      </NavLink>
                    )
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-[#0A0A0B]/95 backdrop-blur-lg border-t border-[#1F1F23]">
        <div className="flex items-stretch justify-around px-2 pb-[max(env(safe-area-inset-bottom),4px)]">
          {primaryTabs.map(item => {
            const Icon = item.icon
            const to = item.path ? `${basePath}/${item.path}` : basePath
            return (
              <NavLink
                key={item.path || '_home'}
                to={to}
                end={!item.path}
                onTouchStart={startLongPress}
                onTouchEnd={cancelLongPress}
                onTouchMove={cancelLongPress}
                className={({ isActive }) => clsx(
                  'flex flex-col items-center justify-center gap-0.5 py-2 px-3 min-w-[64px] min-h-[50px] transition-colors',
                  isActive ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/60',
                )}
              >
                <Icon size={20} strokeWidth={1.8} />
                <span className="text-[10px] font-medium">{item.label}</span>
              </NavLink>
            )
          })}
          <button
            onClick={() => setMoreOpen(true)}
            aria-label="More features"
            className={clsx(
              'flex flex-col items-center justify-center gap-0.5 py-2 px-3 min-w-[64px] min-h-[50px] transition-colors',
              isMoreActive ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/60',
            )}
          >
            <MoreHorizontal size={20} strokeWidth={1.8} />
            <span className="text-[10px] font-medium">More</span>
          </button>
        </div>
      </nav>
    </>
  )
}
