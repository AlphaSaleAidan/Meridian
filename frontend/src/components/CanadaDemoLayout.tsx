import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, TrendingUp, Package, Layers, Lightbulb,
  LineChart, Bell, Settings, Menu, Bot, Target, Users,
  UserCheck, Clock, DollarSign, ChefHat, AlertTriangle, Box,
  MapPin, Phone, Calendar, Globe, Monitor, Video,
} from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from './MeridianLogo'
import MobileNavBar from './MobileNavBar'
import { DemoContextProvider } from '@/lib/demo-context'
import { useMobile } from '@/hooks/useMobile'
import BusinessTypeSelector from './BusinessTypeSelector'
import DemoHeaderBadge from './DemoHeaderBadge'
import SEO from './SEO'

interface NavItem {
  path: string
  icon: typeof LayoutDashboard
  label: string
  desktopOnly?: boolean
}

// Mirrors the live /canada/dashboard portal nav (CanadaLayout) so the demo
// shell matches the new customer portal. The camera path is `camera-analytics`
// to match the route registered under /canada/demo in App.tsx.
const navItems: NavItem[] = [
  { path: '', icon: LayoutDashboard, label: 'Overview' },
  { path: 'revenue', icon: TrendingUp, label: 'Revenue' },
  { path: 'insights', icon: Lightbulb, label: 'Insights' },
  { path: 'actions', icon: Target, label: 'Top Actions' },
  { path: 'agents', icon: Bot, label: 'Agents' },
  { path: 'camera-analytics', icon: Video, label: 'Camera Intel' },
  { path: 'customers', icon: Users, label: 'Customers' },
  { path: 'products', icon: Package, label: 'Products' },
  { path: 'margins', icon: DollarSign, label: 'Margins' },
  { path: 'forecasts', icon: LineChart, label: 'Forecasts' },
  { path: 'peak-hours', icon: Clock, label: 'Peak Hours' },
  { path: 'staff', icon: UserCheck, label: 'Staff' },
  { path: 'schedule', icon: Calendar, label: 'Schedule' },
  { path: 'inventory', icon: Layers, label: 'Inventory' },
  { path: 'anomalies', icon: AlertTriangle, label: 'Anomalies' },
  { path: 'menu-matrix', icon: ChefHat, label: 'Menu Matrix', desktopOnly: true },
  { path: 'phone-orders', icon: Phone, label: 'Phone Orders' },
  { path: 'my-website', icon: Globe, label: 'My Website' },
  { path: 'space', icon: Box, label: '3D Space' },
  { path: 'notifications', icon: Bell, label: 'Notifications' },
  { path: 'settings', icon: Settings, label: 'Settings' },
]

function CanadaDemoShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const basePath = '/canada/demo'
  const { isMobile, isTablet } = useMobile()

  const visibleNavItems = isMobile ? navItems.filter(i => !i.desktopOnly) : navItems

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
          <MeridianEmblem size={28} animate={false} />
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
                </span>
                <span className="truncate">{item.label}</span>
                {item.desktopOnly && (
                  <Monitor size={10} className="ml-auto text-[#A1A1A8]/40 flex-shrink-0" />
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Bottom — discreet SR login (matches the live portal) */}
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
          <MeridianEmblem size={24} animate={false} />
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
    </div>
  )
}

export default function CanadaDemoLayout() {
  return (
    <DemoContextProvider>
      <SEO
        title="Meridian Intelligence — Interactive Demo (Canada)"
        description="Explore Meridian's AI-powered POS analytics with live demo data in Canadian dollars. Revenue insights, anomaly detection, forecasting, and more."
        path="/canada/demo"
        noindex
      />
      <BusinessTypeSelector />
      <DemoHeaderBadge />
      <CanadaDemoShell />
    </DemoContextProvider>
  )
}
