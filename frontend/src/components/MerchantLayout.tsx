import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import { Menu, MapPin } from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from './MeridianLogo'
import { useUnreadNotifications } from '@/hooks/useUnreadNotifications'
import { merchantPillars, MERCHANT_BASE_PATH, type Pillar } from '@/config/merchantPillars'
import { useModuleFlags } from '@/config/moduleFlags'

function PillarLink({ pillar, basePath, onNavigate }: { pillar: Pillar; basePath: string; onNavigate: () => void }) {
  const Icon = pillar.icon
  const { unreadCount } = useUnreadNotifications()
  const to = pillar.path ? `${basePath}/${pillar.path}` : basePath
  return (
    <NavLink
      to={to}
      end={!pillar.path}
      onClick={onNavigate}
      className={({ isActive }) => clsx(
        'flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150',
        isActive
          ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]'
          : 'text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#111113]',
      )}
    >
      <span className="relative flex-shrink-0">
        <Icon size={16} />
        {pillar.path === 'settings' && unreadCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </span>
      <span className="truncate">{pillar.label}</span>
    </NavLink>
  )
}

export default function MerchantLayout({ basePath = MERCHANT_BASE_PATH }: { basePath?: string } = {}) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const closeSidebar = () => setSidebarOpen(false)
  const flags = useModuleFlags()
  // Same chrome serves both regions: /canada/* keeps its existing branding,
  // the US mounts (/us/merchant, /demo) swap the region chip + rep-login link.
  const isCanada = useLocation().pathname.startsWith('/canada')
  const regionLabel = isCanada ? 'Canada' : 'US'
  const regionShort = isCanada ? 'CA' : 'US'
  const repLoginHref = isCanada ? '/canada/portal/login' : '/us/portal/login'

  // Filter pillars by their optional flag — disabled-never-delete pattern.
  const visiblePillars = merchantPillars.filter(p => !p.flag || flags[p.flag])
  const moneyPillars = visiblePillars.filter(p => !p.secondary && p.path !== 'settings')
  const secondaryPillars = visiblePillars.filter(p => p.secondary)
  const settingsPillar = visiblePillars.find(p => p.path === 'settings')
  // Mobile bottom-nav: money pillars + settings only (no secondary tabs, no overflow).
  const mobileNavPillars = [...moneyPillars, ...(settingsPillar ? [settingsPillar] : [])]

  return (
    // h-dvh (not h-screen): the shell scrolls via <main>, never the document,
    // so mobile browser chrome never retracts — 100vh (large viewport) makes
    // the overflow-hidden shell taller than the visible screen and the bottom
    // of the scrolled content sits permanently behind the chrome/bottom nav
    // ("can't scroll to the bottom" on long pages like Phone). 100dvh tracks
    // the real visible height; h-screen stays as the no-dvh fallback.
    <div className="flex h-screen supports-[height:100dvh]:h-dvh bg-[#0A0A0B] text-white overflow-hidden">
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 z-40 lg:hidden" onClick={closeSidebar} />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        'fixed inset-y-0 left-0 z-50 w-56 bg-[#0A0A0B] border-r border-[#1F1F23] flex flex-col transition-transform duration-200 lg:static lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
      )}>
        <div className="h-14 flex items-center gap-2.5 px-4 border-b border-[#1F1F23] flex-shrink-0">
          <MeridianEmblem size={28} animate />
          <div className="flex flex-col">
            <MeridianWordmark height={13} />
            <span className="text-[8px] font-bold text-[#17C5B0] uppercase tracking-[0.2em] mt-0.5">{regionLabel}</span>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5 no-scrollbar">
          {moneyPillars.map(p => (
            <PillarLink key={p.path || '_home'} pillar={p} basePath={basePath} onNavigate={closeSidebar} />
          ))}
          {secondaryPillars.length > 0 && (
            <div className="pt-2 mt-2 border-t border-[#1F1F23] space-y-0.5">
              {secondaryPillars.map(p => (
                <PillarLink key={p.path} pillar={p} basePath={basePath} onNavigate={closeSidebar} />
              ))}
            </div>
          )}
        </nav>

        {settingsPillar && (
          <div className="px-2 py-2 border-t border-[#1F1F23] flex-shrink-0">
            <PillarLink pillar={settingsPillar} basePath={basePath} onNavigate={closeSidebar} />
          </div>
        )}

        <div className="px-3 py-3 border-t border-[#1F1F23] flex-shrink-0">
          <a
            href={repLoginHref}
            className="text-[9px] text-[#A1A1A8]/20 hover:text-[#A1A1A8]/50 transition-colors block text-center py-1"
          >
            Sales Rep Access
          </a>
        </div>
      </aside>

      {/* Main content */}
      <main id="main-content" className="flex-1 overflow-y-auto">
        <div className="lg:hidden sticky top-0 z-30 h-14 bg-[#0A0A0B]/95 backdrop-blur-sm border-b border-[#1F1F23] flex items-center gap-3 px-4">
          <button aria-label="Open menu" onClick={() => setSidebarOpen(true)} className="p-1.5 rounded-lg hover:bg-[#111113]">
            <Menu size={20} className="text-[#A1A1A8]" />
          </button>
          <MeridianEmblem size={24} animate />
          <MeridianWordmark height={11} />
          <div className="flex items-center gap-1 ml-1">
            <MapPin size={8} className="text-[#17C5B0]" />
            <span className="text-[8px] text-[#17C5B0] font-medium uppercase tracking-wider">{regionShort}</span>
          </div>
        </div>

        <div className="p-3 sm:p-6 lg:p-8 max-w-7xl mx-auto pb-32 lg:pb-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile pillar bar — money pillars + settings only, respects module flags */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-[#0A0A0B]/95 backdrop-blur-lg border-t border-[#1F1F23]">
        <div className="flex items-stretch justify-around px-2 pb-[max(env(safe-area-inset-bottom),4px)]">
          {mobileNavPillars.map(p => {
            const Icon = p.icon
            const to = p.path ? `${basePath}/${p.path}` : basePath
            return (
              <NavLink
                key={p.path || '_home'}
                to={to}
                end={!p.path}
                className={({ isActive }) => clsx(
                  'flex flex-col items-center justify-center gap-0.5 py-2 px-2 min-w-[56px] min-h-[50px] transition-colors',
                  isActive ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/60',
                )}
              >
                <Icon size={20} strokeWidth={1.8} />
                <span className="text-[10px] font-medium">{p.label}</span>
              </NavLink>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
