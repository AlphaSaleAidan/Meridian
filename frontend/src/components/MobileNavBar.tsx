import { NavLink, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, TrendingUp, Lightbulb, Target, Bot,
  MoreHorizontal, X, Users, Package, DollarSign, LineChart,
  Clock, UserCheck, Calendar, Layers, AlertTriangle, Phone,
  Globe, Bell, Settings, Video, Box, ChefHat,
} from 'lucide-react'
import { useState, useEffect } from 'react'

interface TabItem {
  path: string
  icon: typeof LayoutDashboard
  label: string
}

const PRIMARY_TABS: TabItem[] = [
  { path: '', icon: LayoutDashboard, label: 'Home' },
  { path: 'revenue', icon: TrendingUp, label: 'Revenue' },
  { path: 'insights', icon: Lightbulb, label: 'Insights' },
  { path: 'actions', icon: Target, label: 'Actions' },
]

const MORE_ITEMS: TabItem[] = [
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

interface MobileNavBarProps {
  basePath: string
}

export default function MobileNavBar({ basePath }: MobileNavBarProps) {
  const [moreOpen, setMoreOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMoreOpen(false)
  }, [location.pathname])

  const currentPath = location.pathname.replace(basePath + '/', '').replace(basePath, '')
  const isMoreActive = MORE_ITEMS.some(item => item.path === currentPath)

  return (
    <>
      {/* More menu overlay */}
      {moreOpen && (
        <div className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm lg:hidden" onClick={() => setMoreOpen(false)}>
          <div
            className="absolute bottom-0 left-0 right-0 bg-[#111113] border-t border-[#1F1F23] rounded-t-2xl max-h-[70vh] overflow-y-auto pb-[max(env(safe-area-inset-bottom),16px)]"
            onClick={e => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-[#111113] px-4 pt-3 pb-2 border-b border-[#1F1F23] flex items-center justify-between z-10">
              <span className="text-sm font-semibold text-[#F5F5F7]">All Features</span>
              <button
                onClick={() => setMoreOpen(false)}
                className="p-2 rounded-full bg-[#1F1F23] text-[#A1A1A8]"
              >
                <X size={16} />
              </button>
            </div>
            <div className="grid grid-cols-4 gap-1 p-3">
              {MORE_ITEMS.map(item => {
                const Icon = item.icon
                const to = item.path ? `${basePath}/${item.path}` : basePath
                return (
                  <NavLink
                    key={item.path}
                    to={to}
                    className={({ isActive }) => clsx(
                      'flex flex-col items-center gap-1.5 py-3 px-1 rounded-xl transition-colors min-h-[72px] justify-center',
                      isActive
                        ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]'
                        : 'text-[#A1A1A8] active:bg-[#1F1F23]',
                    )}
                  >
                    <Icon size={20} />
                    <span className="text-[10px] font-medium leading-tight text-center">{item.label}</span>
                  </NavLink>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Bottom tab bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-[#0A0A0B]/95 backdrop-blur-lg border-t border-[#1F1F23]">
        <div className="flex items-stretch justify-around px-2 pb-[max(env(safe-area-inset-bottom),4px)]">
          {PRIMARY_TABS.map(item => {
            const Icon = item.icon
            const to = item.path ? `${basePath}/${item.path}` : basePath
            return (
              <NavLink
                key={item.path}
                to={to}
                end={!item.path}
                className={({ isActive }) => clsx(
                  'flex flex-col items-center justify-center gap-0.5 py-2 px-3 min-w-[64px] min-h-[50px] transition-colors',
                  isActive
                    ? 'text-[#1A8FD6]'
                    : 'text-[#A1A1A8]/60',
                )}
              >
                <Icon size={20} strokeWidth={1.8} />
                <span className="text-[10px] font-medium">{item.label}</span>
              </NavLink>
            )
          })}
          <button
            onClick={() => setMoreOpen(true)}
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
