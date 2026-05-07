import { useState, useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard,
  Target,
  Building2,
  GraduationCap,
  Users,
  Settings,
  Menu,
  X,
  LogOut,
  Plus,
} from 'lucide-react'
import { MeridianEmblem } from '@/components/MeridianLogo'
import { useSalesAuth } from '@/lib/sales-auth'

const salesNavItems = [
  { heading: 'Sales' },
  { path: '/sales/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/sales/leads', icon: Target, label: 'Leads' },
  { path: '/sales/accounts', icon: Building2, label: 'Accounts' },
  { path: '/sales/training', icon: GraduationCap, label: 'Training' },
  { path: '/sales/settings', icon: Settings, label: 'Settings' },
] as const

const adminNavItems = [
  { heading: 'Admin' },
  { path: '/sales/team', icon: Users, label: 'Team Management' },
] as const

type NavHeading = { heading: string }
type NavItem = { path: string; icon: typeof LayoutDashboard; label: string }
type NavEntry = NavHeading | NavItem

function isHeading(entry: NavEntry): entry is NavHeading {
  return 'heading' in entry
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map(w => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

function getAvatarColor(name: string): string {
  const colors = ['#1A8FD6', '#17C5B0', '#7C5CFF', '#F59E0B', '#ef4444', '#ec4899']
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

export default function SalesLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { rep, logout } = useSalesAuth()

  function handleLogout() {
    logout()
    navigate('/sales/login', { replace: true })
  }

  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSidebarOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const allNav: NavEntry[] = [...salesNavItems, ...adminNavItems]

  const sidebarContent = (
    <>
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-[#1F1F23] flex-shrink-0">
        <MeridianEmblem size={28} />
        <div className="flex flex-col">
          <span className="text-sm font-bold text-[#F5F5F7] leading-tight">Meridian</span>
          <span className="text-[8px] font-semibold text-[#17C5B0] uppercase tracking-widest">
            Sales Portal
          </span>
        </div>
        <button
          onClick={() => setSidebarOpen(false)}
          className="ml-auto lg:hidden p-1.5 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
        {allNav.map((entry, i) => {
          if (isHeading(entry)) {
            return (
              <p
                key={i}
                className={clsx(
                  'text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider px-3 mb-1',
                  i > 0 && 'mt-5 pt-4 border-t border-[#1F1F23]'
                )}
              >
                {entry.heading}
              </p>
            )
          }
          const { path, icon: Icon, label } = entry
          return (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                clsx(
                  'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-[#17C5B0]/8 text-[#17C5B0]'
                    : 'text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23]/60'
                )
              }
            >
              <Icon size={18} className="transition-transform duration-200 group-hover:scale-110" />
              {label}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-4 border-t border-[#1F1F23] flex-shrink-0">
        {rep ? (
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold text-white"
              style={{ backgroundColor: getAvatarColor(rep.name) }}
            >
              {getInitials(rep.name)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-[#F5F5F7] truncate">{rep.name}</p>
              <p className="text-[11px] text-[#A1A1A8]/50 truncate">Sales Rep</p>
            </div>
          </div>
        ) : null}
        <button
          onClick={handleLogout}
          className="mt-3 flex items-center gap-2 text-xs text-[#A1A1A8] hover:text-[#17C5B0] transition-colors w-full"
        >
          <LogOut size={14} />
          Sign out
        </button>
      </div>
    </>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-[#0A0A0B]">
      <aside className="hidden lg:flex w-[260px] flex-shrink-0 bg-[#0A0A0B] border-r border-[#1F1F23] flex-col">
        {sidebarContent}
      </aside>

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-[260px] bg-[#0A0A0B] border-r border-[#1F1F23] flex flex-col transition-transform duration-300 ease-out lg:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {sidebarContent}
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden bg-[#0A0A0B]">
        <header className="lg:hidden h-14 flex items-center gap-3 px-4 border-b border-[#1F1F23] bg-[#0A0A0B] flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors -ml-1"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <MeridianEmblem size={24} />
          <div className="flex flex-col">
            <span className="text-sm font-bold text-[#F5F5F7] leading-tight">Meridian</span>
            <span className="text-[7px] font-semibold text-[#17C5B0] uppercase tracking-widest">
              Sales Portal
            </span>
          </div>
          <button
            onClick={() => navigate('/sales/leads?new=true')}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold hover:bg-[#17C5B0]/90 transition-colors"
          >
            <Plus size={14} />
            New Lead
          </button>
        </header>

        <header className="hidden lg:flex h-14 items-center justify-end px-6 border-b border-[#1F1F23] bg-[#0A0A0B] flex-shrink-0">
          <button
            onClick={() => navigate('/sales/leads?new=true')}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold hover:bg-[#17C5B0]/90 transition-colors"
          >
            <Plus size={16} />
            New Lead
          </button>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
