import { useState, useEffect } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import { QueryClientProvider } from '@tanstack/react-query'
import { createCanadaQueryClient } from '@/lib/canada-queries'
import { CanadaPortalErrorBoundary } from './PortalPage'
import {
  LayoutDashboard,
  Target,
  Building2,
  GraduationCap,
  FileText,
  Users,
  Menu,
  X,
  LogOut,
  Plus,
  Settings,
  Trophy,
  CreditCard,
} from 'lucide-react'
import { MeridianEmblem } from '@/components/MeridianLogo'
import SalesPortalMobileNav from './SalesPortalMobileNav'
import { useSalesAuth } from '@/lib/sales-auth'
import { useMobile } from '@/hooks/useMobile'
import ClineAIChatWidget from '@/components/ClineAIChatWidget'

const salesNavBase = [
  { heading: 'Sales' },
  { path: '/canada/portal/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/canada/portal/leads', icon: Target, label: 'Leads' },
  { path: '/canada/portal/accounts', icon: Building2, label: 'Accounts' },
  { path: '/canada/portal/training', icon: GraduationCap, label: 'Training' },
  { path: '/canada/portal/proposals', icon: FileText, label: 'Proposals' },
] as const

const teamNavAdmin = { path: '/canada/portal/team', icon: Users, label: 'Team' } as const
const teamNavRep = { path: '/canada/portal/team', icon: Trophy, label: 'Leaderboard' } as const
// Recruiting pipeline: NOT a nav tab (Aidan's call, 2026-07-17) — the route
// stays live and is linked from the Team page instead.

const salesNavTail = [
  { path: '/canada/portal/badge', icon: CreditCard, label: 'My Badge' },
  { path: '/canada/portal/settings', icon: Settings, label: 'Settings' },
] as const

const adminNavItems = [
  { heading: 'Admin' },
] as const

const ADMIN_EMAILS = [
  'apierce@alphasale.co',
  'aidanpierce72@gmail.com',
  'aidanpierce@meridian.tips',
  'cheungenochmgmt@gmail.com',
  'aidanvietnguyen@gmail.com',
]

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

// Solid-fill avatar palette. Class-emitting so Tailwind keeps these in its pass.
const AVATAR_BG_CLASSES = [
  'bg-pm-accent',
  'bg-pm-amber-orange',
  'bg-pm-purple',
  'bg-[#ef4444]',
  'bg-[#3b82f6]',
  'bg-[#ec4899]',
]
function getAvatarBgClass(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AVATAR_BG_CLASSES[Math.abs(hash) % AVATAR_BG_CLASSES.length]
}

export default function CanadaSalesLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [queryClient] = useState(() => createCanadaQueryClient())
  const location = useLocation()
  const navigate = useNavigate()
  const { rep, logout } = useSalesAuth()
  const { isDesktop } = useMobile()

  function handleLogout() {
    logout()
    navigate('/canada/portal/login', { replace: true })
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

  // Preload sibling portal page chunks on idle. Trimmed in fix #3:
  // only the most-likely next tabs (Leads, Accounts)
  // get eager-imported, and the preload is gated to once per session
  // via sessionStorage so revisiting the layout doesn't re-chew the
  // network on every mount. The remaining tabs lazy-load on click
  // (one InlineFallback pulse per first visit) — preferable to
  // pre-fetching ~10 chunks that compete with the very first
  // useCanadaLeads fetch for bandwidth and main-thread time.
  useEffect(() => {
    const PRELOAD_KEY = 'meridian.canadaPortal.preloaded'
    if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(PRELOAD_KEY) === '1') {
      return
    }
    const preload = () => {
      void import('./CanadaPortalLeadsPage')
      void import('./CanadaPortalAccountsPage')
      if (typeof sessionStorage !== 'undefined') {
        sessionStorage.setItem(PRELOAD_KEY, '1')
      }
    }
    const ric = (window as unknown as { requestIdleCallback?: (cb: () => void) => number }).requestIdleCallback
    if (typeof ric === 'function') {
      ric(preload)
    } else {
      const t = setTimeout(preload, 250)
      return () => clearTimeout(t)
    }
  }, [])

  const isAdmin = rep?.email && ADMIN_EMAILS.some(a => a.toLowerCase() === rep.email.toLowerCase())
  const salesNavItems = [...salesNavBase, isAdmin ? teamNavAdmin : teamNavRep, ...salesNavTail]
  const allNav: NavEntry[] = isAdmin ? [...salesNavItems, ...adminNavItems] : [...salesNavItems]

  const sidebarContent = (
    <>
      {/* Logo area */}
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-pm-canada-border flex-shrink-0">
        <Link to="/canada/portal/dashboard" aria-label="Meridian sales portal home" className="flex items-center gap-2.5">
          <MeridianEmblem size={28} />
          <div className="flex flex-col">
            <span className="text-sm font-bold text-white leading-tight">Meridian</span>
            <span className="text-[8px] font-semibold text-pm-accent uppercase tracking-widest">
              Canada Sales Portal
            </span>
          </div>
        </Link>
        <button
          onClick={() => setSidebarOpen(false)}
          className="ml-auto lg:hidden p-1.5 rounded-lg text-pm-canada-text-muted hover:text-white hover:bg-pm-canada-border transition-colors"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
        {allNav.map((entry, i) => {
          if (isHeading(entry)) {
            return (
              <p
                key={i}
                className={clsx(
                  'text-2xs font-semibold text-pm-canada-text-muted uppercase tracking-wider px-3 mb-1',
                  i > 0 && 'mt-5 pt-4 border-t border-pm-canada-border'
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
                    ? 'bg-[rgba(0,212,170,0.08)] text-pm-accent'
                    : 'text-pm-canada-text-muted hover:text-white hover:bg-pm-canada-border/60'
                )
              }
            >
              <Icon size={18} className="transition-transform duration-200 group-hover:scale-110" />
              {label}
            </NavLink>
          )
        })}
      </nav>

      {/* User section at bottom */}
      <div className="p-4 border-t border-pm-canada-border flex-shrink-0">
        {rep ? (
          <div className="flex items-center gap-3">
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold text-white ${getAvatarBgClass(rep.name)}`}
            >
              {getInitials(rep.name)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-white truncate">{rep.name}</p>
              <p className="text-2xs text-pm-canada-text-muted truncate">Sales Rep</p>
            </div>
          </div>
        ) : null}
        <button
          onClick={handleLogout}
          className="mt-3 flex items-center gap-2 text-xs text-pm-canada-text-muted hover:text-pm-accent transition-colors w-full"
        >
          <LogOut size={14} />
          Sign out
        </button>
      </div>
    </>
  )

  return (
    <QueryClientProvider client={queryClient}>
    <div className="flex h-screen overflow-hidden bg-pm-canada-bg">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[260px] flex-shrink-0 bg-pm-canada-bg border-r border-pm-canada-border flex-col">
        {sidebarContent}
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-[260px] bg-pm-canada-bg border-r border-pm-canada-border flex flex-col transition-transform duration-300 ease-out lg:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {sidebarContent}
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-pm-canada-bg">
        {/* Mobile header */}
        <header className="lg:hidden h-14 flex items-center gap-3 px-4 border-b border-pm-canada-border bg-pm-canada-bg flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg text-pm-canada-text-muted hover:text-white hover:bg-pm-canada-border transition-colors -ml-1"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <Link to="/canada/portal/dashboard" aria-label="Meridian sales portal home" className="flex items-center gap-3">
            <MeridianEmblem size={24} />
            <div className="flex flex-col">
              <span className="text-sm font-bold text-white leading-tight">Meridian</span>
              <span className="text-[7px] font-semibold text-pm-accent uppercase tracking-widest">
                Canada Sales Portal
              </span>
            </div>
          </Link>
          <button
            onClick={() => navigate('/canada/portal/leads?new=true&t=' + Date.now())}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-pm-accent text-pm-canada-bg text-xs font-semibold hover:bg-pm-accent/90 transition-colors"
          >
            <Plus size={14} />
            New Lead
          </button>
        </header>

        {/* Desktop header with New Lead button */}
        <header className="hidden lg:flex h-14 items-center justify-end px-6 border-b border-pm-canada-border bg-pm-canada-bg flex-shrink-0">
          <button
            onClick={() => navigate('/canada/portal/leads?new=true&t=' + Date.now())}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-pm-accent text-pm-canada-bg text-sm font-semibold hover:bg-pm-accent/90 transition-colors"
          >
            <Plus size={16} />
            New Lead
          </button>
        </header>

        <main id="main-content" className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 mobile-nav-spacer">
            {/* Localized error boundary: a render-time throw inside a portal
                page keeps the sidebar usable and shows a contained fallback
                with "Try again / Back to Dashboard", instead of triggering
                the app-level boundary that white-screens the whole UI. */}
            <CanadaPortalErrorBoundary>
              <Outlet />
            </CanadaPortalErrorBoundary>
          </div>
        </main>
      </div>

      {!isDesktop && <SalesPortalMobileNav />}
      <ClineAIChatWidget />
    </div>
    </QueryClientProvider>
  )
}
