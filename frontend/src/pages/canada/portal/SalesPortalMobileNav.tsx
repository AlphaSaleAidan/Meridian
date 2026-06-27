import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, Target, Building2, MoreHorizontal,
  GraduationCap, FileText, Users, Settings, X, Trophy, CreditCard,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useSalesAuth } from '@/lib/sales-auth'

const ADMIN_EMAILS = [
  'apierce@alphasale.co',
  'aidanpierce72@gmail.com',
  'aidanpierce@meridian.tips',
  'cheungenochmgmt@gmail.com',
  'aidanvietnguyen@gmail.com',
]

const PRIMARY_TABS = [
  { path: '/canada/portal/dashboard', icon: LayoutDashboard, label: 'Home' },
  { path: '/canada/portal/leads', icon: Target, label: 'Leads' },
  { path: '/canada/portal/accounts', icon: Building2, label: 'Accounts' },
]

function getMoreItems(isAdmin: boolean) {
  return [
    { path: '/canada/portal/training', icon: GraduationCap, label: 'Training' },
    { path: '/canada/portal/proposals', icon: FileText, label: 'Proposals' },
    { path: '/canada/portal/team', icon: isAdmin ? Users : Trophy, label: isAdmin ? 'Team' : 'Leaderboard' },
    { path: '/canada/portal/badge', icon: CreditCard, label: 'My Badge' },
    { path: '/canada/portal/settings', icon: Settings, label: 'Settings' },
  ]
}

export default function SalesPortalMobileNav() {
  const [moreOpen, setMoreOpen] = useState(false)
  const location = useLocation()
  const { rep } = useSalesAuth()
  const isAdmin = rep?.email && ADMIN_EMAILS.some(a => a.toLowerCase() === rep.email.toLowerCase())
  const MORE_ITEMS = getMoreItems(!!isAdmin)

  useEffect(() => { setMoreOpen(false) }, [location.pathname])

  const isMoreActive = MORE_ITEMS.some(item => location.pathname.startsWith(item.path))

  return (
    <>
      {moreOpen && (
        <div className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm lg:hidden" onClick={() => setMoreOpen(false)}>
          <div
            className="absolute bottom-0 left-0 right-0 bg-pm-canada-bg border-t border-pm-canada-border rounded-t-2xl pb-[max(env(safe-area-inset-bottom),16px)]"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-pm-canada-border">
              <span className="text-sm font-semibold text-white">More</span>
              <button aria-label="Close menu" onClick={() => setMoreOpen(false)} className="p-2 rounded-full bg-pm-canada-border text-pm-canada-text-muted">
                <X size={16} />
              </button>
            </div>
            <div className="grid grid-cols-3 gap-1 p-3">
              {MORE_ITEMS.map(item => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) => clsx(
                      'flex flex-col items-center gap-1.5 py-4 rounded-xl transition-colors min-h-[72px] justify-center',
                      isActive ? 'bg-pm-accent/10 text-pm-accent' : 'text-pm-canada-text-muted active:bg-pm-canada-border',
                    )}
                  >
                    <Icon size={22} />
                    <span className="text-2xs font-medium">{item.label}</span>
                  </NavLink>
                )
              })}
            </div>
          </div>
        </div>
      )}

      <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-pm-canada-bg/95 backdrop-blur-lg border-t border-pm-canada-border">
        <div className="flex items-stretch justify-around px-2 pb-[max(env(safe-area-inset-bottom),4px)]">
          {PRIMARY_TABS.map(item => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => clsx(
                  'flex flex-col items-center justify-center gap-0.5 py-2 px-3 min-w-[64px] min-h-[50px] transition-colors',
                  isActive ? 'text-pm-accent' : 'text-pm-canada-text-muted/60',
                )}
              >
                <Icon size={20} strokeWidth={1.8} />
                <span className="text-2xs font-medium">{item.label}</span>
              </NavLink>
            )
          })}
          <button
            onClick={() => setMoreOpen(true)}
            className={clsx(
              'flex flex-col items-center justify-center gap-0.5 py-2 px-3 min-w-[64px] min-h-[50px] transition-colors',
              isMoreActive ? 'text-pm-accent' : 'text-pm-canada-text-muted/60',
            )}
          >
            <MoreHorizontal size={20} strokeWidth={1.8} />
            <span className="text-2xs font-medium">More</span>
          </button>
        </div>
      </nav>
    </>
  )
}
