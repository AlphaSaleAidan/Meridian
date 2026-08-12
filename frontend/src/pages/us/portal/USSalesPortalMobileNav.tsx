import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, Target, Building2, MoreHorizontal,
  GraduationCap, Users, Settings, X, CreditCard, PhoneCall,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const PRIMARY_TABS = [
  { path: '/us/portal/dashboard', icon: LayoutDashboard, label: 'Home' },
  { path: '/us/portal/leads', icon: Target, label: 'Leads' },
  { path: '/us/portal/accounts', icon: Building2, label: 'Accounts' },
]

const MORE_ITEMS = [
  { path: '/us/portal/auto-dialer', icon: PhoneCall, label: 'Auto Dialer' },
  { path: '/us/portal/training', icon: GraduationCap, label: 'Training' },
  { path: '/us/portal/team', icon: Users, label: 'Team' },
  { path: '/us/portal/badge', icon: CreditCard, label: 'My Badge' },
  { path: '/us/portal/settings', icon: Settings, label: 'Settings' },
]

export default function USSalesPortalMobileNav() {
  const [moreOpen, setMoreOpen] = useState(false)
  const location = useLocation()

  useEffect(() => { setMoreOpen(false) }, [location.pathname])

  const isMoreActive = MORE_ITEMS.some(item => location.pathname.startsWith(item.path))

  return (
    <>
      {moreOpen && (
        <div className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm lg:hidden" onClick={() => setMoreOpen(false)}>
          <div
            className="absolute bottom-0 left-0 right-0 bg-[#0A0A0B] border-t border-[#1F1F23] rounded-t-2xl pb-[max(env(safe-area-inset-bottom),16px)]"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-[#1F1F23]">
              <span className="text-sm font-semibold text-white">More</span>
              <button onClick={() => setMoreOpen(false)} className="p-2 rounded-full bg-[#1F1F23] text-[#A1A1A8]">
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
                      isActive ? 'bg-[#17C5B0]/10 text-[#17C5B0]' : 'text-[#A1A1A8] active:bg-[#1F1F23]',
                    )}
                  >
                    <Icon size={22} />
                    <span className="text-[10px] font-medium">{item.label}</span>
                  </NavLink>
                )
              })}
            </div>
          </div>
        </div>
      )}

      <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-[#0A0A0B]/95 backdrop-blur-lg border-t border-[#1F1F23]">
        <div className="flex items-stretch justify-around px-2 pb-[max(env(safe-area-inset-bottom),4px)]">
          {PRIMARY_TABS.map(item => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => clsx(
                  'flex flex-col items-center justify-center gap-0.5 py-2 px-3 min-w-[64px] min-h-[50px] transition-colors',
                  isActive ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/60',
                )}
              >
                <Icon size={20} strokeWidth={1.8} />
                <span className="text-[10px] font-medium">{item.label}</span>
              </NavLink>
            )
          })}
          <button
            onClick={() => setMoreOpen(true)}
            className={clsx(
              'flex flex-col items-center justify-center gap-0.5 py-2 px-3 min-w-[64px] min-h-[50px] transition-colors',
              isMoreActive ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/60',
            )}
          >
            <MoreHorizontal size={20} strokeWidth={1.8} />
            <span className="text-[10px] font-medium">More</span>
          </button>
        </div>
      </nav>
    </>
  )
}
