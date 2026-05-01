/**Responsive layout: desktop sidebar + mobile bottom tab nav.**/
import { useState, useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useIsMobile } from '@/hooks/useIsMobile'
import { Sheet, SheetHeader, SheetContent } from '@/components/ui/sheet'
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
  MoreHorizontal,
} from 'lucide-react'
import MeridianLogo, { MeridianEmblem, MeridianWordmark } from './MeridianLogo'
import { useAuth } from '@/lib/auth'
import OnboardingWizard from '@/pages/OnboardingWizard'

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
  { path: 'insights', icon: Lightbulb, label: 'Insights' },
  { path: 'notifications', icon: Bell, label: 'Notifications' },
  { path: 'settings', icon: Settings, label: 'Settings' },
]

const bottomTabItems = [
  { path: '', icon: LayoutDashboard, label: 'Home' },
  { path: 'revenue', icon: TrendingUp, label: 'Revenue' },
  { path: 'agents', icon: Bot, label: 'Agents' },
  { path: 'insights', icon: Lightbulb, label: 'Insights' },
]

export default function ResponsiveLayout() {
  const [sheetOpen, setSheetOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { org, logout } = useAuth()
  const isMobile = useIsMobile()
  const basePath = location.pathname.startsWith('/app') ? '/app' : '/demo'
  const isApp = basePath === '/app'
  const needsOnboarding = isApp && org && !org.pos_connected && !org.onboarded

  async function handleLogout() {
    await logout()
    navigate('/customer/login', { replace: true })
  }

  useEffect(() => {
    setSheetOpen(false)
  }, [location.pathname])

  const navList = (
    <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
      {navItems.map(({ path, icon: Icon, label }) => {
        const to = path ? `${basePath}/${path}` : basePath
        return (
          <NavLink
            key={path}
            to={to}
            end={!path}
            className={({ isActive }) =>
              cn(
                'group flex items-center gap-3 px-3 py-3 lg:py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] border border-[#1A8FD6]/15'
                  : 'text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23]/60 border border-transparent',
              )
            }
          >
            <Icon size={18} className="transition-transform duration-200 group-hover:scale-110" />
            {label}
          </NavLink>
        )
      })}
    </nav>
  )

  const sidebarFooter = (
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
        <div className="text-[11px] text-[#A1A1A8]/40 font-mono">v0.2.0</div>
      )}
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Desktop sidebar ── */}
      <aside className="hidden lg:flex w-[230px] flex-shrink-0 bg-[#0A0A0B] border-r border-[#1F1F23] flex-col">
        <div className="h-16 flex items-center gap-2.5 px-5 border-b border-[#1F1F23] flex-shrink-0">
          <MeridianLogo size={32} showWordmark />
          {basePath === '/demo' && (
            <span className="ml-auto text-[10px] font-medium text-[#1A8FD6] bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 px-1.5 py-0.5 rounded">
              DEMO
            </span>
          )}
        </div>
        {navList}
        {sidebarFooter}
      </aside>

      {/* ── Mobile nav sheet (full menu) ── */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen} side="left">
        <SheetHeader onClose={() => setSheetOpen(false)}>
          <div className="flex items-center gap-2">
            <MeridianEmblem size={24} />
            <MeridianWordmark className="text-sm" />
            {basePath === '/demo' && (
              <span className="text-[10px] font-medium text-[#1A8FD6] bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 px-1.5 py-0.5 rounded">
                DEMO
              </span>
            )}
          </div>
        </SheetHeader>
        <SheetContent>
          {navList}
          {sidebarFooter}
        </SheetContent>
      </Sheet>

      {/* ── Main content ── */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#0A0A0B]">
        {/* Mobile top bar */}
        <header className="lg:hidden h-14 flex items-center gap-3 px-4 border-b border-[#1F1F23] bg-[#0A0A0B] flex-shrink-0">
          <button
            onClick={() => setSheetOpen(true)}
            className="p-2 rounded-lg text-[#A1A1A8] hover:text-white hover:bg-[#1F1F23] transition-colors -ml-1 min-h-[44px] min-w-[44px] flex items-center justify-center"
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

        {/* Page content — bottom padding for mobile tab bar */}
        <main className={cn('flex-1 overflow-y-auto', isMobile && 'pb-20')}>
          {needsOnboarding ? (
            <OnboardingWizard />
          ) : (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
              <Outlet />
            </div>
          )}
        </main>

        {/* ── Mobile bottom tab bar ── */}
        {isMobile && (
          <nav className="fixed bottom-0 inset-x-0 z-30 bg-[#0A0A0B]/95 backdrop-blur-md border-t border-[#1F1F23] safe-area-inset-bottom">
            <div className="flex items-stretch">
              {bottomTabItems.map(({ path, icon: Icon, label }) => {
                const to = path ? `${basePath}/${path}` : basePath
                return (
                  <NavLink
                    key={path}
                    to={to}
                    end={!path}
                    className={({ isActive }) =>
                      cn(
                        'flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-[56px] transition-colors',
                        isActive ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/60',
                      )
                    }
                  >
                    <Icon size={20} />
                    <span className="text-[10px] font-medium">{label}</span>
                  </NavLink>
                )
              })}
              {/* More tab opens full nav */}
              <button
                onClick={() => setSheetOpen(true)}
                className="flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-[56px] text-[#A1A1A8]/60 transition-colors active:text-[#F5F5F7]"
              >
                <MoreHorizontal size={20} />
                <span className="text-[10px] font-medium">More</span>
              </button>
            </div>
          </nav>
        )}
      </div>
    </div>
  )
}
