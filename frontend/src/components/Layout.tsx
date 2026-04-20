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
  const location = useLocation()
  // Determine base path: /demo or /app
  const basePath = location.pathname.startsWith('/app') ? '/app' : '/demo'

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-[220px] flex-shrink-0 bg-slate-950 border-r border-slate-800/60 flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center gap-2.5 px-5 border-b border-slate-800/60">
          <div className="w-8 h-8 rounded-lg bg-meridian-700 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight text-white">Meridian</span>
          {basePath === '/demo' && (
            <span className="ml-auto text-[10px] font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded">
              DEMO
            </span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-3 space-y-1">
          {navItems.map(({ path, icon: Icon, label }) => {
            const to = path ? `${basePath}/${path}` : basePath
            return (
              <NavLink
                key={path}
                to={to}
                end={!path}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                    isActive
                      ? 'bg-meridian-700/15 text-meridian-400 border border-meridian-700/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                  )
                }
              >
                <Icon className="w-4.5 h-4.5" size={18} />
                {label}
              </NavLink>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800/60">
          <div className="text-xs text-slate-500">
            Meridian v0.2.0
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
