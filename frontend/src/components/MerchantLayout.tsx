import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import { ChevronRight, MapPin, MoreHorizontal } from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from './MeridianLogo'
import { useUnreadNotifications } from '@/hooks/useUnreadNotifications'
import { merchantPillars, comingSoonPillars, orderPillars, MERCHANT_BASE_PATH, type Pillar } from '@/config/merchantPillars'
import { useAuth } from '@/lib/auth'
import { useModuleFlags, useTradePack } from '@/config/moduleFlags'
import { usePublishHeight } from '@/hooks/usePublishHeight'

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
  // The mobile tab bar is permanent chrome under lg; above lg it is display:
  // none and measures zero, which is the right answer without a breakpoint
  // check here.
  const bottomNavRef = useRef<HTMLElement>(null)
  usePublishHeight(bottomNavRef, '--bottom-nav-h')
  // Desktop-sidebar links need no close handler (the sidebar is static there);
  // the mobile drawer is gone.
  const noop = () => {}

  // Whether the tab bar has more tabs off either edge, so we can show a fade +
  // chevron telling the user it scrolls. A demo has more tabs than fit; without
  // this cue the extra tabs look like they simply do not exist.
  const tabScrollerRef = useRef<HTMLDivElement>(null)
  const [tabOverflow, setTabOverflow] = useState({ left: false, right: false })
  useEffect(() => {
    const el = tabScrollerRef.current
    if (!el) return
    const update = () => setTabOverflow({
      left: el.scrollLeft > 4,
      right: el.scrollLeft + el.clientWidth < el.scrollWidth - 4,
    })
    update()
    el.addEventListener('scroll', update, { passive: true })
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => { el.removeEventListener('scroll', update); ro.disconnect() }
  }, [])
  const flags = useModuleFlags()
  const { org } = useAuth()
  // Same chrome serves both regions: /canada/* keeps its existing branding,
  // the US mounts (/us/merchant, /demo) show no region chip at all.
  const isCanada = useLocation().pathname.startsWith('/canada')
  const repLoginHref = isCanada ? '/canada/portal/login' : '/us/portal/login'
  // Demos also surface the roadmap-preview tabs in the bottom bar; a paying
  // merchant's bar carries only what their portal actually has.
  const isDemo = basePath === '/demo' || basePath === '/canada/demo'

  // Filter pillars by their optional flag — disabled-never-delete pattern —
  // then put them in the order this merchant's TRADE cares about. A barber
  // opens on the book; a takeout shop opens on the phone.
  const pack = useTradePack()
  /**
   * Roadmap previews ride along in BOTH public demos — never in a paying
   * merchant's portal. This was pinned to the Canada demo path, so a US
   * prospect saw four fewer tabs than a Canadian one despite /demo being
   * documented as a mirror of /canada/demo.
   *
   * They sit in the ONE list now rather than under a "Coming Soon" heading.
   * They follow Camera at the end of Everything else.
   * The heading sorted the navigation by our build status, which is our
   * problem and not the merchant's — and it did it twice over, since each of
   * those pages already says so in a banner at the top. Sorting by what a
   * trade uses is the only order that means anything to them.
   */
  // Trade-scoped tabs: a pillar that names its trades shows only there, and
  // one that excludes a trade never shows it.
  const forThisTrade = (p: Pillar) =>
    (!p.trades || p.trades.includes(pack.key)) && !p.excludeTrades?.includes(pack.key)
  const roadmapPillars = isDemo ? comingSoonPillars.filter(forThisTrade) : []
  const visiblePillars = orderPillars(
    merchantPillars.filter(p => (!p.flag || flags[p.flag]) && forThisTrade(p)),
    pack.pillarOrder,
  )
  /**
   * On the demos the workspace is lifted out of the list and pinned to the
   * top as "Today".
   *
   * The trade's own screen sitting fourth in a flat list of pillars said the
   * opposite of what the product does — it is where a merchant lives, and the
   * rest is where they go occasionally. Everything below the divider stays in
   * this trade's order, which is why a barber's Bookings sits above a
   * takeaway's Phone Calls.
   */
  const homePillar = isDemo ? visiblePillars.find(p => p.path === '') : undefined
  const moneyPillars = visiblePillars
    .filter(p => !p.secondary && p.path !== 'settings')
    .filter(p => !(homePillar && p.path === ''))
  const secondaryPillars = visiblePillars.filter(p => p.secondary)
  const settingsPillar = visiblePillars.find(p => p.path === 'settings')
  /**
   * ONE tab bar on mobile — four tabs and a More sheet.
   *
   * This has been through three shapes. First a bar AND a drawer that held
   * the same tabs twice. Then one scrolling bar holding everything — which
   * fixed the duplication but, at ten pillars, truncated every label and
   * hid half the product behind a sideways scroll nobody performs.
   *
   * The rule that survives both failures: every tab lives in EXACTLY ONE
   * place. The first four pillars — the trade's own order, so a golf course
   * leads with its tee sheet and a cafe with its inventory — sit in the bar;
   * everything else lives only inside More. No tab appears twice.
   */
  const mobileNavPillars = [
    // Today leads on mobile too — it is lifted out of moneyPillars above.
    ...(homePillar ? [{ ...homePillar, label: 'Today' }] : []),
    ...moneyPillars,
    ...secondaryPillars,
    ...roadmapPillars,
    ...(settingsPillar ? [settingsPillar] : []),
  ]
  const primaryNav = mobileNavPillars.slice(0, 4)
  const overflowNav = mobileNavPillars.slice(4)
  const [moreOpen, setMoreOpen] = useState(false)
  const { pathname } = useLocation()
  // Close the sheet whenever navigation lands, wherever it came from.
  useEffect(() => { setMoreOpen(false) }, [pathname])
  // The More tab lights up when the CURRENT page lives inside it, so the bar
  // always shows where you are even when where-you-are is not a bar tab.
  const overflowActive = overflowNav.some(p =>
    p.path ? pathname.startsWith(`${basePath}/${p.path}`) : pathname === basePath)

  return (
    // h-dvh (not h-screen): the shell scrolls via <main>, never the document,
    // so mobile browser chrome never retracts — 100vh (large viewport) makes
    // the overflow-hidden shell taller than the visible screen and the bottom
    // of the scrolled content sits permanently behind the chrome/bottom nav
    // ("can't scroll to the bottom" on long pages like Phone). 100dvh tracks
    // the real visible height; h-screen stays as the no-dvh fallback.
    <div className="flex h-screen supports-[height:100dvh]:h-dvh bg-[#0A0A0B] text-white overflow-hidden">
      {/* Desktop sidebar only. On mobile the bottom bar is the sole nav, so
          this is display:none rather than a slide-in drawer. */}
      <aside className="hidden lg:flex w-56 bg-[#0A0A0B] border-r border-[#1F1F23] flex-col flex-shrink-0">
        <div className="h-14 flex items-center gap-2.5 px-4 border-b border-[#1F1F23] flex-shrink-0">
          <Link to={basePath} aria-label="Meridian dashboard home" className="flex items-center gap-2.5">
            <MeridianEmblem size={28} animate />
            <div className="flex flex-col">
              <MeridianWordmark height={13} />
              {isCanada && (
                <span className="text-[8px] font-bold text-[#17C5B0] uppercase tracking-[0.2em] mt-0.5">Canada</span>
              )}
            </div>
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5 no-scrollbar">
          {homePillar && (
            <>
              <PillarLink
                pillar={{ ...homePillar, label: 'Today' }}
                basePath={basePath}
                onNavigate={noop}
              />
              <div className="pt-3 pb-1 px-3 text-[10px] uppercase tracking-wide text-[#4A4A52]">
                Everything else
              </div>
            </>
          )}
          {moneyPillars.map(p => (
            <PillarLink key={p.path || '_home'} pillar={p} basePath={basePath} onNavigate={noop} />
          ))}
          {[...secondaryPillars, ...roadmapPillars].length > 0 && (
            <div className="pt-2 mt-2 border-t border-[#1F1F23] space-y-0.5">
              {/* Camera first, then the roadmap previews — one continuous list
                  under Everything else. Camera below "My Website" read as an
                  afterthought when the roadmap items were merged above it. */}
              {[...secondaryPillars, ...roadmapPillars].map(p => (
                <PillarLink key={p.path} pillar={p} basePath={basePath} onNavigate={noop} />
              ))}
            </div>
          )}
        </nav>

        {settingsPillar && (
          <div className="px-2 py-2 border-t border-[#1F1F23] flex-shrink-0">
            <PillarLink pillar={settingsPillar} basePath={basePath} onNavigate={noop} />
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
      {/*
        The scroll container reserves room for the bars fixed OVER it.

        Fixed elements are out of flow, so <main> gave itself no room for the
        mobile tab bar or the cookie banner: you could scroll to the true end
        and still have the last 150-200 pixels sitting behind one of them,
        unreachable by any means. Each bar publishes its own height (they
        change with wrapping, and the banner is dismissible), and this adds
        them up.
      */}
      <main
        id="main-content"
        className="flex-1 overflow-y-auto overscroll-none touch-pan-y [-webkit-overflow-scrolling:touch]"
        style={{ paddingBottom: 'calc(var(--cookie-bar-h, 0px) + var(--bottom-nav-h, 0px))' }}
      >
        {/* Top bar is branding only now — navigation lives in the single bottom
            bar (with its "More" tab). No hamburger competing with it. */}
        <div className="lg:hidden sticky top-0 z-30 h-14 bg-[#0A0A0B]/95 backdrop-blur-sm border-b border-[#1F1F23] flex items-center gap-3 px-4">
          <Link to={basePath} aria-label="Meridian dashboard home" className="flex items-center gap-3">
            <MeridianEmblem size={24} animate />
            <MeridianWordmark height={11} />
          </Link>
          {isCanada && (
            <div className="flex items-center gap-1 ml-1">
              <MapPin size={8} className="text-[#17C5B0]" />
              <span className="text-[8px] text-[#17C5B0] font-medium uppercase tracking-wider">CA</span>
            </div>
          )}
        </div>

        <div className="p-3 sm:p-6 lg:p-8 max-w-7xl mx-auto pb-32 lg:pb-8">
          <Outlet />
        </div>
      </main>

      {/* The single mobile tab bar. Every category lives here and only here.
          When the tabs fit, flex-1 spreads them across the width; when a trade
          has more than fit (a demo shows ~8), min-w keeps each tappable and the
          row scrolls horizontally — no tab is ever hidden behind a drawer. */}
      <nav
        ref={bottomNavRef}
        className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-[#0A0A0B]/95 backdrop-blur-lg border-t border-[#1F1F23]"
      >
        {/* Left fade: appears once you have scrolled right, so it is clear the
            row came from somewhere. */}
        <div
          aria-hidden
          className={clsx(
            'pointer-events-none absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-[#0A0A0B] to-transparent transition-opacity duration-200',
            tabOverflow.left ? 'opacity-100' : 'opacity-0',
          )}
        />
        {/* Right fade + chevron: the cue that there are more tabs to the right.
            Fades out when the row is scrolled to its end. */}
        <div
          aria-hidden
          className={clsx(
            'pointer-events-none absolute inset-y-0 right-0 flex items-center justify-end pr-1 w-10 bg-gradient-to-l from-[#0A0A0B] via-[#0A0A0B]/90 to-transparent transition-opacity duration-200',
            tabOverflow.right ? 'opacity-100' : 'opacity-0',
          )}
        >
          <ChevronRight size={18} className="text-[#1A8FD6]" strokeWidth={2.25} />
        </div>
        <div
          ref={tabScrollerRef}
          className="flex items-stretch overflow-x-auto no-scrollbar snap-x pb-[max(env(safe-area-inset-bottom),4px)] [-webkit-overflow-scrolling:touch]"
        >
          {primaryNav.map(p => {
            const Icon = p.icon
            const to = p.path ? `${basePath}/${p.path}` : basePath
            return (
              <NavLink
                key={p.path || '_home'}
                to={to}
                end={!p.path}
                onClick={() => setMoreOpen(false)}
                className={({ isActive }) => clsx(
                  'flex flex-1 shrink-0 snap-start flex-col items-center justify-center gap-0.5 py-2 px-1 min-w-[68px] min-h-[54px] transition-colors',
                  isActive && !moreOpen ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/60',
                )}
              >
                <Icon size={20} strokeWidth={1.8} />
                <span className="text-[10px] font-medium truncate max-w-full">{p.label}</span>
              </NavLink>
            )
          })}
          {overflowNav.length > 0 && (
            <button
              onClick={() => setMoreOpen(v => !v)}
              aria-expanded={moreOpen}
              aria-label="More sections"
              className={clsx(
                'flex flex-1 shrink-0 snap-start flex-col items-center justify-center gap-0.5 py-2 px-1 min-w-[68px] min-h-[54px] transition-colors',
                moreOpen || overflowActive ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/60',
              )}
            >
              <MoreHorizontal size={20} strokeWidth={1.8} />
              <span className="text-[10px] font-medium">More</span>
            </button>
          )}
        </div>
      </nav>

      {/* The More sheet — holds ONLY the tabs the bar does not, and closes on
          any pick. A backdrop, so a stray tap dismisses instead of acting. */}
      {moreOpen && overflowNav.length > 0 && (
        <>
          <button
            aria-label="Close menu"
            onClick={() => setMoreOpen(false)}
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          />
          <div
            className="fixed left-2 right-2 z-50 rounded-xl border border-[#1F1F23] bg-[#0E0E11]/98 p-2 backdrop-blur-lg lg:hidden"
            style={{ bottom: 'calc(var(--bottom-nav-h, 64px) + 8px)' }}
          >
            <div className="grid grid-cols-3 gap-1">
              {overflowNav.map(p => {
                const Icon = p.icon
                const to = p.path ? `${basePath}/${p.path}` : basePath
                return (
                  <NavLink
                    key={p.path || '_home'}
                    to={to}
                    end={!p.path}
                    onClick={() => setMoreOpen(false)}
                    className={({ isActive }) => clsx(
                      'flex min-h-[64px] flex-col items-center justify-center gap-1 rounded-lg py-2 px-1 transition-colors',
                      isActive ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]',
                    )}
                  >
                    <Icon size={20} strokeWidth={1.8} />
                    <span className="text-[10px] font-medium truncate max-w-full">{p.label}</span>
                  </NavLink>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
