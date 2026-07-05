import { useState, useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, TrendingUp, Package, Layers, Lightbulb,
  LineChart, Bell, Settings, Menu, Bot, Target, Users,
  UserCheck, Clock, DollarSign, ChefHat, AlertTriangle, Box,
  MapPin, Phone, Calendar, Globe, Monitor, Video,
} from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from './MeridianLogo'
import MobileNavBar from './MobileNavBar'
import CustomerWalkthrough from './CustomerWalkthrough'
import { RadarLoadingState } from './LoadingState'
import { useAuth } from '@/lib/auth'
import { useMobile } from '@/hooks/useMobile'
import { useUnreadNotifications } from '@/hooks/useUnreadNotifications'
import { canadaModuleFlags, type ModuleFlags } from '@/config/moduleFlags'

interface NavItem {
  path: string
  icon: typeof LayoutDashboard
  label: string
  desktopOnly?: boolean
  /** Module flag gating visibility. Omitted items are always shown. */
  flag?: keyof ModuleFlags
}

const navItems: NavItem[] = [
  { path: '', icon: LayoutDashboard, label: 'Overview' },
  { path: 'revenue', icon: TrendingUp, label: 'Revenue' },
  { path: 'insights', icon: Lightbulb, label: 'Insights', flag: 'insights' },
  { path: 'actions', icon: Target, label: 'Top Actions', flag: 'topActions' },
  { path: 'agents', icon: Bot, label: 'Agents', flag: 'agents' },
  { path: 'camera-intelligence', icon: Video, label: 'Camera Intel', flag: 'camera' },
  { path: 'customers', icon: Users, label: 'Customers', flag: 'customers' },
  { path: 'products', icon: Package, label: 'Products' },
  { path: 'margins', icon: DollarSign, label: 'Margins' },
  { path: 'forecasts', icon: LineChart, label: 'Forecasts' },
  { path: 'peak-hours', icon: Clock, label: 'Peak Hours' },
  { path: 'staff', icon: UserCheck, label: 'Staff' },
  { path: 'schedule', icon: Calendar, label: 'Schedule' },
  { path: 'inventory', icon: Layers, label: 'Inventory' },
  { path: 'anomalies', icon: AlertTriangle, label: 'Anomalies' },
  { path: 'menu-matrix', icon: ChefHat, label: 'Menu Matrix', desktopOnly: true },
  { path: 'phone-orders', icon: Phone, label: 'Phone Orders', flag: 'phoneCalls' },
  { path: 'my-website', icon: Globe, label: 'My Website', flag: 'myWebsite' },
  { path: 'space', icon: Box, label: '3D Space', flag: 'spaces3D' },
  { path: 'notifications', icon: Bell, label: 'Notifications' },
  { path: 'settings', icon: Settings, label: 'Settings' },
]

export default function CanadaLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showWalkthrough, setShowWalkthrough] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const basePath = '/canada/dashboard'
  const { user, org } = useAuth()
  const { isMobile, isTablet } = useMobile()
  const { unreadCount } = useUnreadNotifications()

  useEffect(() => {
    if (!user?.id) return
    // The dismissal flag is per-origin localStorage, so a returning customer on
    // a different origin (or with cleared storage) would get the walkthrough
    // stacked on them again. An onboarded org counts as already-dismissed.
    if (org?.onboarded) return
    const key = `meridian_walkthrough_${user.id}`
    if (localStorage.getItem(key) !== 'completed') {
      setShowWalkthrough(true)
    }
  }, [user?.id, org?.onboarded])

  // Redirect mobile users away from desktop-only pages
  useEffect(() => {
    if (!isMobile) return
    const currentPath = location.pathname.replace(basePath + '/', '')
    const desktopOnlyItem = navItems.find(
      i => i.desktopOnly && i.path === currentPath,
    )
    if (desktopOnlyItem) navigate(basePath, { replace: true })
  }, [isMobile, location.pathname, navigate])

  const enabledNavItems = navItems.filter(i => !i.flag || canadaModuleFlags[i.flag])
  const visibleNavItems = isMobile
    ? enabledNavItems.filter(i => !i.desktopOnly)
    : enabledNavItems

  return (
    <div className="flex h-screen bg-[#0A0A0B] text-white overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        'fixed inset-y-0 left-0 z-50 w-56 bg-[#0A0A0B] border-r border-[#1F1F23] flex flex-col transition-transform duration-200 lg:static lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
      )}>
        {/* Logo */}
        <div className="h-14 flex items-center gap-2.5 px-4 border-b border-[#1F1F23] flex-shrink-0">
          <MeridianEmblem size={28} animate />
          <div className="flex flex-col">
            <MeridianWordmark height={13} />
            <span className="text-[8px] font-bold text-[#17C5B0] uppercase tracking-[0.2em] mt-0.5">Canada</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5 no-scrollbar" data-walkthrough="sidebar-nav">
          {visibleNavItems.map(item => {
            const Icon = item.icon
            const to = item.path ? `${basePath}/${item.path}` : basePath
            return (
              <NavLink
                key={item.path}
                to={to}
                end={!item.path}
                className={({ isActive }) => clsx(
                  'flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150',
                  isActive
                    ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]'
                    : 'text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#111113]',
                )}
                onClick={() => setSidebarOpen(false)}
              >
                <span className="relative flex-shrink-0">
                  <Icon size={16} />
                  {item.path === 'notifications' && unreadCount > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                  )}
                </span>
                <span className="truncate">{item.label}</span>
                {item.desktopOnly && (
                  <Monitor size={10} className="ml-auto text-[#A1A1A8]/40 flex-shrink-0" />
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Bottom — discreet SR login */}
        <div className="px-3 py-3 border-t border-[#1F1F23] flex-shrink-0">
          <a
            href="/canada/portal/login"
            className="text-[9px] text-[#A1A1A8]/20 hover:text-[#A1A1A8]/50 transition-colors block text-center py-1"
          >
            Sales Rep Access
          </a>
        </div>
      </aside>

      {/* Main content */}
      <main id="main-content" className="flex-1 overflow-y-auto">
        {/* Mobile header */}
        <div className="lg:hidden sticky top-0 z-30 h-14 bg-[#0A0A0B]/95 backdrop-blur-sm border-b border-[#1F1F23] flex items-center gap-3 px-4">
          <button aria-label="Open menu" onClick={() => setSidebarOpen(true)} className="p-1.5 rounded-lg hover:bg-[#111113]">
            <Menu size={20} className="text-[#A1A1A8]" />
          </button>
          <MeridianEmblem size={24} animate />
          <MeridianWordmark height={11} />
          <div className="flex items-center gap-1 ml-1">
            <MapPin size={8} className="text-[#17C5B0]" />
            <span className="text-[8px] text-[#17C5B0] font-medium uppercase tracking-wider">CA</span>
          </div>
        </div>

        <div className="p-3 sm:p-6 lg:p-8 max-w-7xl mx-auto mobile-nav-spacer">
          <Outlet />
        </div>
      </main>

      {(isMobile || isTablet) && <MobileNavBar basePath={basePath} />}

      {showWalkthrough && user?.id && (
        <CustomerWalkthrough
          userId={user.id}
          posConnected={!!org?.pos_connected}
          onDismiss={() => setShowWalkthrough(false)}
        />
      )}
    </div>
  )
}
