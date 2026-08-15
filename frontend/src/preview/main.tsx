/**
 * Preview harness for the two Bookings screens.
 *
 * The PAGE COMPONENTS are the real ones, unmodified — this renders
 * src/pages/BookingsPage.tsx and BookingsSetupPage.tsx exactly as the portal
 * does. What is replaced is the backend: fixtureApi intercepts /api/bookings
 * and answers with the same wire shapes, so the screens can be clicked
 * without a login, a database or a merchant's real guest list.
 *
 * Not imported by the app.
 */
import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/lib/auth'
import BookingsPage from '@/pages/BookingsPage'
import BookingsSetupPage from '@/pages/BookingsSetupPage'
import { installFixtureApi } from './fixtureApi'
import '@/index.css'

installFixtureApi()

const TABS = [
  { key: 'book', label: "Today's Book", Component: BookingsPage },
  { key: 'setup', label: 'Set up', Component: BookingsSetupPage },
] as const

function Shell() {
  const [tab, setTab] = useState<'book' | 'setup'>('book')
  const Active = TABS.find((t) => t.key === tab)!.Component

  return (
    <div className="min-h-screen bg-[#0B0B0F] text-white">
      <header className="border-b border-white/10 bg-[#101016]">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
          <div>
            <div className="text-sm font-semibold tracking-tight">Meridian — Bookings</div>
            <div className="text-xs text-white/40">
              preview build · branch feat/booking-reservations
            </div>
          </div>
          <nav className="ml-auto flex gap-1 rounded-lg bg-white/5 p-1">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={
                  'rounded-md px-4 py-1.5 text-sm transition-colors ' +
                  (tab === t.key
                    ? 'bg-white/10 text-white'
                    : 'text-white/50 hover:text-white/80')
                }
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <div className="border-b border-amber-400/20 bg-amber-400/5">
        <div className="mx-auto flex max-w-6xl items-start gap-2 px-6 py-2.5 text-xs text-amber-200/80">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
               className="mt-px h-4 w-4 shrink-0" aria-hidden="true">
            <path d="M12 9v4M12 17h.01M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.7 3.86a2 2 0 0 0-3.4 0Z"
                  strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>
            Sample data. Every guest, table and phone number on this page is invented —
            no real merchant's book is shown. The screens, the layout and the failure
            behaviour are the real ones.
          </span>
        </div>
      </div>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Active />
      </main>
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
