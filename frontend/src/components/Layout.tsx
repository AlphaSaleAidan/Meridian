import { useState, useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
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
} from 'lucide-react'
import MeridianLogo, { MeridianEmblem, MeridianWordmark } from './MeridianLogo'

const navItems = [
  { path: '', icon: LayoutDashboard, label: 'Overview' },
  { path: 'revenue', icon: TrendingUp, label: 'Revenue' },
  { path: 'products', icon: Package, label: 'Products' },
  { path: 'inventory', icon: Layers, label: 'Inventory' },
  { path: 'insights', icon: Lightbulb, label: 'Insights' },
  { path: 'forecasts', icon: LineChart, label: 'Forecasts' },
  { path: 'notifications', icon: Bell, label: 'Alerts' },
  { path: 'settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const basePath = location.pathname.startsWith('/app') ? '/app' : '/demo'

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
        <MeridianLogo size={32} showText textSize="text-lg" />
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
      <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
        {navItems.map(({ path, icon: Icon, label }) => {
          const to = path ? `${basePath}/${path}` : basePath
          return (
            <NavLink
              key={path}
              to={to}
              end={!path}
              className={({ isActive }) =>
                clsx(
                  'group flex items-center gap-3 px-3 py-3 lg:py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/15'
                    : 'text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23]/60 border border-transparent'
                )
              }
            >
              <Icon size={18} className="transition-transform duration-200 group-hover:scale-110" />
              {label}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[#1F1F23] flex-shrink-0">
        <div className="text-[11px] text-[#A1A1A8]/40 font-mono">
          v0.2.0
        </div>
      </div>
    </>
  )

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[220px] flex-shrink-0 bg-[#0A0A0B] border-r border-[#1F1F23] flex-col">
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
          'fixed inset-y-0 left-0 z-50 w-[260px] bg-[#0A0A0B] border-r border-[#1F1F23] flex flex-col transition-transform duration-300 ease-out lg:hidden',
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
          <MeridianWordmark size="text-sm" />
          {basePath === '/demo' && (
            <span className="text-[10px] font-medium text-[#1A8FD6] bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 px-1.5 py-0.5 rounded">
              DEMO
            </span>
          )}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
