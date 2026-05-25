import { useState, useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { clsx } from 'clsx'
import {
  LayoutDashboard,
  TrendingUp,
  Package,
  Layers,
  Lightbulb,
  LineChart,
  Bell,
  Settings,
  Menu,
  X,
  Bot,
  Target,
  Users,
  UserCheck,
  Clock,
  DollarSign,
  LogOut,
  ChefHat,
  AlertTriangle,
  Box,
  Phone,
  Globe,
  Calendar,
  Video,
} from 'lucide-react'
import MeridianLogo, { MeridianEmblem, MeridianWordmark } from './MeridianLogo'
import MobileNavBar from './MobileNavBar'
import { useAuth } from '@/lib/auth'
import { useMobile } from '@/hooks/useMobile'
import { useUnreadNotifications } from '@/hooks/useUnreadNotifications'
import OnboardingWizard from '@/pages/OnboardingWizard'
import ClineChatWidget from './ClineChatWidget'
import ClineErrorBoundary from './ClineErrorBoundary'
import CommandPalette from './CommandPalette'
import OfflineBanner from './OfflineBanner'

const navGroups = [
  {
    label: null,
    items: [
      { path: '', icon: LayoutDashboard, label: 'Overview' },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { path: 'revenue', icon: TrendingUp, label: 'Revenue' },
      { path: 'insights', icon: Lightbulb, label: 'Insights' },
      { path: 'actions', icon: Target, label: 'Top Actions' },
      { path: 'forecasts', icon: LineChart, label: 'Forecasts' },
      { path: 'anomalies', icon: AlertTriangle, label: 'Anomalies' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { path: 'products', icon: Package, label: 'Products' },
      { path: 'margins', icon: DollarSign, label: 'Margins' },
      { path: 'menu-matrix', icon: ChefHat, label: 'Menu Matrix' },
      { path: 'inventory', icon: Layers, label: 'Inventory' },
      { path: 'peak-hours', icon: Clock, label: 'Peak Hours' },
    ],
  },
  {
    label: 'People',
    items: [
      { path: 'customers', icon: Users, label: 'Customers' },
      { path: 'staff', icon: UserCheck, label: 'Staff' },
      { path: 'schedule', icon: Calendar, label: 'Schedule' },
    ],
  },
  {
    label: 'Tools',
    items: [
      { path: 'agents', icon: Bot, label: 'AI Agents' },
      { path: 'camera-intelligence', icon: Video, label: 'Camera Intel' },
      { path: 'phone-orders', icon: Phone, label: 'Phone Orders' },
      { path: 'my-website', icon: Globe, label: 'My Website' },
      { path: 'space', icon: Box, label: '3D Space' },
    ],
  },
  {
    label: null,
    items: [
      { path: 'notifications', icon: Bell, label: 'Notifications' },
      { path: 'settings', icon: Settings, label: 'Settings' },
    ],
  },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { org, logout } = useAuth()
  const { isDesktop } = useMobile()
  const { unreadCount } = useUnreadNotifications()
  const basePath = location.pathname.startsWith('/app') ? '/app'
    : location.pathname.startsWith('/canada/demo') ? '/canada/demo'
    : location.pathname.startsWith('/canada/dashboard') ? '/canada/dashboard'
    : '/demo'
  const isApp = basePath === '/app'
  const needsOnboarding = isApp && org && !org.pos_connected && !org.onboarded

  async function handleLogout() {
    await logout()
    navigate('/customer/login', { replace: true })
  }

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  // Close sidebar on escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSidebarOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-[#1F1F23] flex-shrink-0">
        <MeridianLogo size={32} showWordmark />
        {basePath === '/demo' && (
          <span className="ml-auto text-[10px] font-medium text-[#1A8FD6] bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 px-1.5 py-0.5 rounded">
            DEMO
          </span>
        )}
        {/* Close button (mobile only) */}
        <button
          onClick={() => setSidebarOpen(false)}
          className="ml-auto lg:hidden p-1.5 rounded-lg text-[#A1A1A8] hover:text-white hover:bg-[#1F1F23] transition-colors"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-3 overflow-y-auto" data-walkthrough="sidebar-nav">
        {navGroups.map((group, gi) => (
          <div key={gi} className={gi > 0 ? 'mt-3' : ''}>
            {group.label && (
              <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider text-[#A1A1A8]/30">{group.label}</p>
            )}
            <div className="space-y-0.5">
              {group.items.map(({ path, icon: Icon, label }) => {
                const to = path ? `${basePath}/${path}` : basePath
                return (
                  <NavLink
                    key={path}
                    to={to}
                    end={!path}
                    className={({ isActive }) =>
                      clsx(
                        'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 min-h-[44px] lg:min-h-0',
                        isActive
                          ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/15'
                          : 'text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23]/60 border border-transparent'
                      )
                    }
                  >
                    <span className="relative">
                      <Icon size={18} className="transition-transform duration-200 group-hover:scale-110" />
                      {path === 'notifications' && unreadCount > 0 && (
                        <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
                          {unreadCount > 9 ? '9+' : unreadCount}
                        </span>
                      )}
                    </span>
                    {label}
                  </NavLink>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[#1F1F23] flex-shrink-0">
        {isApp && org ? (
          <div className="space-y-2">
            <div>
              <p className="text-[11px] font-medium text-[#F5F5F7] truncate">{org.business_name}</p>
              <p className="text-[10px] text-[#A1A1A8]/40 truncate">{org.email}</p>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-[10px] text-[#A1A1A8]/50 hover:text-red-400 transition-colors"
            >
              <LogOut size={10} />
              Sign out
            </button>
          </div>
        ) : (
          <div className="text-[11px] text-[#A1A1A8]/40 font-mono">
            v0.2.0
          </div>
        )}
      </div>
    </>
  )

  return (
    <div className="flex h-screen overflow-hidden">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[200] focus:px-4 focus:py-2 focus:bg-[#1A8FD6] focus:text-white focus:rounded-lg focus:text-sm focus:font-medium">
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[230px] flex-shrink-0 bg-[#0A0A0B] border-r border-[#1F1F23] flex-col">
        {sidebarContent}
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Mobile sidebar drawer */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-[85vw] max-w-[280px] bg-[#0A0A0B] border-r border-[#1F1F23] flex flex-col transition-transform duration-300 ease-out lg:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {sidebarContent}
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#0A0A0B]">
        {/* Mobile top bar */}
        <header className="lg:hidden h-14 flex items-center gap-3 px-4 border-b border-[#1F1F23] bg-[#0A0A0B] flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg text-[#A1A1A8] hover:text-white hover:bg-[#1F1F23] transition-colors -ml-1"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <MeridianEmblem size={24} />
          <MeridianWordmark className="text-sm" />
          {basePath === '/demo' && (
            <span className="text-[10px] font-medium text-[#1A8FD6] bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 px-1.5 py-0.5 rounded">
              DEMO
            </span>
          )}
        </header>

        {/* Page content */}
        <main id="main-content" className="flex-1 overflow-y-auto">
          <OfflineBanner />
          {needsOnboarding ? (
            <OnboardingWizard />
          ) : (
            <ClineErrorBoundary orgId={org?.org_id}>
              <AnimatePresence mode="wait">
                <motion.div
                  key={location.pathname}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 mobile-nav-spacer"
                >
                  <Outlet />
                </motion.div>
              </AnimatePresence>
            </ClineErrorBoundary>
          )}
        </main>

        {/* Cline IT assistant */}
        <ClineChatWidget />
      </div>

      {!isDesktop && <MobileNavBar basePath={basePath} />}
      <CommandPalette basePath={basePath} />
    </div>
  )
}
