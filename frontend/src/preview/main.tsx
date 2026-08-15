/**
 * Per-trade demo shell.
 *
 * Pick a trade and you are inside that trade's Meridian: its navigation, in
 * its order, with its vocabulary and a day's worth of its work on the book.
 * The PAGE COMPONENTS are the real ones — BookingsPage, BookingsSetupPage,
 * BookingsWizard, unmodified — and the navigation is computed by the same
 * functions the portal calls (flagsForMerchant, orderPillars). What is
 * replaced is the backend: fixtureApi answers /api/bookings with the same
 * wire shapes FastAPI returns.
 *
 * Switching trade rebuilds the merchant from the pack, so a barbershop really
 * has chairs and thirty-minute cuts and a detailer really has bays and
 * four-hour jobs. Nothing here relabels a restaurant.
 *
 * Not imported by the app.
 */
import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AlertTriangle, Info } from 'lucide-react'
import { AuthProvider } from '@/lib/auth'
import BookingsPage from '@/pages/BookingsPage'
import BookingsSetupPage from '@/pages/BookingsSetupPage'
import BookingsWizard from '@/pages/BookingsWizard'
import { merchantPillars, orderPillars, type Pillar } from '@/config/merchantPillars'
import { flagsForMerchant } from '@/config/moduleFlags'
import { ALL_PACKS, type NichePack } from '@/config/niches'
import TradeVersions from './TradeVersions'
import { BASE_LOCATION, configureForTrade, installFixtureApi } from './fixtureApi'
import TradeOverview from '@/components/overview/TradeOverview'
import { bookingsApi, type Booking, type BusyBlock, type Resource } from '@/lib/bookings-api'
import '@/index.css'

installFixtureApi()

const MERCHANT = import.meta.env.VITE_ORG_ID || 'preview-bookings'
const BASE_PATH = '/us/merchant'

/** A demo shop name per trade — a portal titled "Preview Merchant" reads as a
 *  fixture; one titled "Fade Room" reads as a shop. */
const SHOP: Record<string, string> = {
  barbershop: 'The Fade Room',
  nails: 'Lacquer Lash Bar',
  detailing: 'Apex Auto Detail',
  mobiledetailing: 'Roadside Shine Mobile',
  restaurant: 'Maple & Vine',
  quickservice: 'Sorrento Pizza',
  medspa: 'Northline Aesthetics',
  other: 'Preview Merchant',
}

/** Pillars whose pages need backends this preview does not stand up. Named
 *  honestly rather than faked — a demo that invents an inventory screen is a
 *  demo that lies about what is built. */
const NOT_IN_PREVIEW: Record<string, string> = {
  '': 'Home and Revenue — the trade’s headline number lands here.',
  phone: 'Phone Orders and the agent setup wizard. Live in the product; needs the phone backend, which this preview does not run.',
  inventory: 'Products, margins, forecasts, menu matrix, anomalies. Needs POS data.',
  schedule: 'Rotas, peak hours, staff, time clock, team chat.',
  camera: 'Live cameras and analytics.',
  settings: 'General settings and notifications.',
  actions: 'The do-this-next list.',
  tax: 'CPA handoff.',
}

function Shell() {
  const [pack, setPack] = useState<NichePack>(ALL_PACKS[0])
  const [pillarPath, setPillarPath] = useState<string>('bookings')
  const [view, setView] = useState<string>('book')
  const [runKey, setRunKey] = useState(0)
  const [ready, setReady] = useState(false)

  // Rebuild the fixture merchant whenever the trade changes, then remount the
  // pages so they refetch against the new shop.
  useEffect(() => {
    configureForTrade(pack)
    setRunKey((n) => n + 1)
    setReady(true)
    const flags = flagsForMerchant(BASE_PATH, pack.modules)
    // Land on the pillar this trade actually opens on.
    const first = orderPillars(
      merchantPillars.filter((p) => !p.flag || flags[p.flag]),
      pack.pillarOrder,
    )[0]
    setPillarPath(first?.path ?? '')
    setView(first?.segments[0]?.view ?? '')
  }, [pack])

  const flags = flagsForMerchant(BASE_PATH, pack.modules)
  const pillars = orderPillars(
    merchantPillars.filter((p) => !p.flag || flags[p.flag]),
    pack.pillarOrder,
  )
  const active: Pillar | undefined = pillars.find((p) => p.path === pillarPath)

  return (
    <div className="min-h-screen bg-[#0B0B0F] text-white">
      <header className="border-b border-white/10 bg-[#101016]">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-6 gap-y-3 px-6 py-3.5">
          <div>
            <div className="text-sm font-semibold tracking-tight">
              Meridian 2.0 — trade demos
            </div>
            <div className="text-xs text-white/40">
              preview build · branch feat/booking-reservations
            </div>
          </div>

          <div className="ml-auto flex flex-wrap items-center gap-1.5">
            {ALL_PACKS.map((p) => (
              <button
                key={p.key}
                onClick={() => setPack(p)}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                  pack.key === p.key
                    ? 'border-[#1A8FD6]/60 bg-[#1A8FD6]/15 text-[#1A8FD6]'
                    : 'border-white/10 text-white/50 hover:text-white/85'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="border-b border-amber-400/20 bg-amber-400/5">
        <div className="mx-auto flex max-w-[1400px] items-start gap-2 px-6 py-2.5 text-xs text-amber-200/80">
          <AlertTriangle className="mt-px h-3.5 w-3.5 shrink-0" />
          <span>
            Sample data — every guest, chair and phone number is invented. The screens,
            the navigation and the failure behaviour are the real ones.
          </span>
        </div>
      </div>

      <div className="mx-auto flex max-w-[1400px] gap-6 px-6 py-6">
        {/* Portal chrome: this trade's navigation, in this trade's order. */}
        <aside className="w-56 shrink-0">
          <div className="mb-3 px-3">
            <div className="text-sm font-semibold text-[#F5F5F7]">{SHOP[pack.key]}</div>
            <div className="text-xs text-[#6B6B73]">{pack.label}</div>
          </div>
          <nav className="space-y-0.5">
            {pillars.map((p) => (
              <button
                key={p.path || 'home'}
                onClick={() => {
                  setPillarPath(p.path)
                  setView(p.segments[0]?.view ?? '')
                }}
                className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  pillarPath === p.path
                    ? 'bg-[#1A8FD6]/15 text-[#1A8FD6]'
                    : 'text-[#A1A1A8] hover:bg-white/5 hover:text-[#F5F5F7]'
                }`}
              >
                <p.icon className="h-4 w-4 shrink-0" />
                {p.label}
              </button>
            ))}
          </nav>

          <div className="mt-6 space-y-0.5 border-t border-[#1F1F23] pt-4">
            <button
              onClick={() => { setPillarPath('__firstrun'); setRunKey((n) => n + 1) }}
              className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                pillarPath === '__firstrun'
                  ? 'bg-white/10 text-white' : 'text-[#6B6B73] hover:text-[#A1A1A8]'
              }`}
            >
              First run
            </button>
            <button
              onClick={() => setPillarPath('__versions')}
              className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                pillarPath === '__versions'
                  ? 'bg-white/10 text-white' : 'text-[#6B6B73] hover:text-[#A1A1A8]'
              }`}
            >
              Compare trades
            </button>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          {pillarPath === '__versions' ? (
            <TradeVersions />
          ) : pillarPath === '__firstrun' ? (
            <BookingsWizard
              key={`wiz-${pack.key}-${runKey}`}
              merchantId={MERCHANT}
              onDone={() => { configureForTrade(pack); setPillarPath('bookings'); setView('book') }}
              onSkip={() => { setPillarPath('bookings'); setView('setup') }}
            />
          ) : active && active.path === 'bookings' ? (
            <>
              <div className="mb-4 flex gap-1 rounded-lg border border-[#1F1F23] p-0.5">
                {active.segments.map((sg) => (
                  <button
                    key={sg.view}
                    onClick={() => setView(sg.view)}
                    className={`rounded-md px-3 py-1.5 text-xs transition-colors ${
                      view === sg.view
                        ? 'bg-[#1A8FD6]/15 text-[#1A8FD6]'
                        : 'text-[#A1A1A8] hover:text-[#F5F5F7]'
                    }`}
                  >
                    {sg.label}
                  </button>
                ))}
              </div>
              {ready && (view === 'setup'
                ? <BookingsSetupPage key={`setup-${pack.key}-${runKey}`} />
                : <BookingsPage key={`book-${pack.key}-${runKey}`} />)}
            </>
          ) : active && active.path === '' ? (
            <OverviewHost key={`ov-${pack.key}-${runKey}`} pack={pack} />
          ) : (
            <NotWired pillar={active} pack={pack} />
          )}
        </main>
      </div>
    </div>
  )
}

/**
 * Feeds the trade overview from the same endpoints the portal uses, so the
 * numbers on it are derived from the day actually on the book rather than
 * written into a mock.
 */
function OverviewHost({ pack }: { pack: NichePack }) {
  const [bookings, setBookings] = useState<Booking[]>([])
  const [resources, setResources] = useState<Resource[]>([])
  const [busy, setBusy] = useState<BusyBlock[]>([])
  const [timezone, setTimezone] = useState('')

  useEffect(() => {
    if (!pack.booksAtAll) return
    const now = new Date()
    const day = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
    const start = new Date(`${day}T00:00:00`)
    const from = new Date(start.getTime() - 12 * 3600_000).toISOString()
    const to = new Date(start.getTime() + 24 * 3600_000).toISOString()
    Promise.all([
      bookingsApi.listBookings(MERCHANT, from, to, false).catch(() => []),
      bookingsApi.listResources(MERCHANT).catch(() => []),
      bookingsApi.listBusy(MERCHANT, from, to).catch(() => []),
      bookingsApi.availability(MERCHANT, day, 1).catch(() => null),
    ]).then(([b, r, bz, av]) => {
      setBookings(b)
      setResources(r)
      setBusy(bz)
      if (av) setTimezone(av.timezone)
    })
  }, [pack])

  const stops = bookings
    .filter((b) => b.serviceAddress && b.serviceLat != null && b.serviceLng != null)
    .map((b) => ({
      booking: b,
      address: b.serviceAddress as string,
      lat: b.serviceLat as number,
      lng: b.serviceLng as number,
    }))

  return (
    <TradeOverview
      pack={pack}
      bookings={bookings}
      resources={resources}
      busy={busy}
      timezone={timezone}
      stops={stops}
      origin={BASE_LOCATION}
    />
  )
}

function NotWired({ pillar, pack }: { pillar?: Pillar; pack: NichePack }) {
  const path = pillar?.path ?? ''
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-[#F5F5F7]">
          {pillar?.label || 'Overview'}
        </h1>
        <p className="mt-0.5 text-sm text-[#A1A1A8]">
          {NOT_IN_PREVIEW[path] || 'Part of the product; not stood up in this preview.'}
        </p>
      </header>

      {path === '' && (
        <div className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
          <div className="text-[11px] uppercase tracking-wide text-[#A1A1A8]">
            {pack.homeMetric.label}
          </div>
          <div className="mt-1 font-mono text-3xl font-semibold text-[#F5F5F7]">——</div>
          <p className="mt-2 max-w-xl text-xs text-[#6B6B73]">{pack.homeMetric.help}</p>
          <p className="mt-4 max-w-xl text-sm text-[#A1A1A8]">
            Each trade opens on a different number. Wiring this into the real home
            page is the next step — the config that decides it is already live, and
            it is what a merchant sees every morning.
          </p>
        </div>
      )}

      <div className="flex items-start gap-2 rounded-xl border border-[#1F1F23] bg-[#0E0E11] p-4">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-[#6B6B73]" />
        <p className="text-sm text-[#A1A1A8]">
          This pillar's pages exist in the product. The preview only stands up the
          bookings backend, so rather than invent a screen, it says so — the point of
          the demo is which pillars this trade gets and in what order, and that part
          is real.
        </p>
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
