import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, TrendingUp, Package, Layers, Lightbulb,
  LineChart, Bell, Settings, Menu, Bot, Target, Users,
  UserCheck, Clock, DollarSign, ChefHat, AlertTriangle, Box,
  MapPin, Phone,
} from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from './MeridianLogo'

const navItems = [
  { path: '', icon: LayoutDashboard, label: 'Overview' },
  { path: 'agents', icon: Bot, label: 'Agents' },
  { path: 'actions', icon: Target, label: 'Top Actions' },
  { path: 'revenue', icon: TrendingUp, label: 'Revenue' },
  { path: 'forecasts', icon: LineChart, label: 'Forecasts' },
  { path: 'products', icon: Package, label: 'Products' },
  { path: 'margins', icon: DollarSign, label: 'Margins' },
  { path: 'menu-matrix', icon: ChefHat, label: 'Menu Matrix' },
  { path: 'anomalies', icon: AlertTriangle, label: 'Anomalies' },
  { path: 'customers', icon: Users, label: 'Customers' },
  { path: 'staff', icon: UserCheck, label: 'Staff' },
  { path: 'peak-hours', icon: Clock, label: 'Peak Hours' },
  { path: 'inventory', icon: Layers, label: 'Inventory' },
  { path: 'space', icon: Box, label: '3D Space' },
  { path: 'phone-orders', icon: Phone, label: 'Phone Orders' },
  { path: 'insights', icon: Lightbulb, label: 'Insights' },
  { path: 'notifications', icon: Bell, label: 'Notifications' },
  { path: 'settings', icon: Settings, label: 'Settings' },
]

export default function CanadaLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const basePath = '/canada/dashboard'

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
        <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5 no-scrollbar">
          {navItems.map(item => {
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
                <Icon size={16} className="flex-shrink-0" />
                <span className="truncate">{item.label}</span>
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
      <main className="flex-1 overflow-y-auto">
        {/* Mobile header */}
        <div className="lg:hidden sticky top-0 z-30 h-14 bg-[#0A0A0B]/95 backdrop-blur-sm border-b border-[#1F1F23] flex items-center gap-3 px-4">
          <button onClick={() => setSidebarOpen(true)} className="p-1.5 rounded-lg hover:bg-[#111113]">
            <Menu size={20} className="text-[#A1A1A8]" />
          </button>
          <MeridianEmblem size={24} animate={false} />
          <MeridianWordmark height={11} />
          <div className="flex items-center gap-1 ml-1">
            <MapPin size={8} className="text-red-400" />
            <span className="text-[8px] text-red-400 font-medium uppercase tracking-wider">CA</span>
          </div>
        </div>

        <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
