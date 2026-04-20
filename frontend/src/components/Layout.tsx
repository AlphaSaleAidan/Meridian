import { useState, useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard,
  TrendingUp,
  Package,
  Lightbulb,
  LineChart,
  Bell,
  Settings,
  Zap,
  Menu,
  X,
} from 'lucide-react'

const navItems = [
  { path: '', icon: LayoutDashboard, label: 'Overview' },
  { path: 'revenue', icon: TrendingUp, label: 'Revenue' },
  { path: 'products', icon: Package, label: 'Products' },
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
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-slate-800/60 flex-shrink-0">
        <div className="w-8 h-8 rounded-lg bg-meridian-700 flex items-center justify-center">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <span className="font-bold text-lg tracking-tight text-white">Meridian</span>
        {basePath === '/demo' && (
          <span className="ml-auto text-[10px] font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded">
            DEMO
          </span>
        )}
        {/* Close button (mobile only) */}
        <button
          onClick={() => setSidebarOpen(false)}
          className="ml-auto lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {navItems.map(({ path, icon: Icon, label }) => {
          const to = path ? `${basePath}/${path}` : basePath
          return (
            <NavLink
              key={path}
              to={to}
              end={!path}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-3 lg:py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-meridian-700/15 text-meridian-400 border border-meridian-700/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800/60 flex-shrink-0">
        <div className="text-xs text-slate-500">
          Meridian v0.2.0
        </div>
      </div>
    </>
  )

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[220px] flex-shrink-0 bg-slate-950 border-r border-slate-800/60 flex-col">
        {sidebarContent}
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Mobile sidebar drawer */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-[260px] bg-slate-950 border-r border-slate-800/60 flex flex-col transition-transform duration-300 ease-out lg:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {sidebarContent}
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile top bar */}
        <header className="lg:hidden h-14 flex items-center gap-3 px-4 border-b border-slate-800/60 bg-slate-950 flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors -ml-1"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-meridian-700 flex items-center justify-center">
              <Zap className="w-3 h-3 text-white" />
            </div>
            <span className="font-semibold text-sm text-white">Meridian</span>
          </div>
          {basePath === '/demo' && (
            <span className="text-[10px] font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded">
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
