/**
 * The workspace's data.
 *
 * TradeWorkspace itself is presentational — it is handed a day and renders it.
 * Everything needed to produce that day lives here: the book, the resources,
 * the services, the fortnight behind the trend, and the forecasts and
 * anomalies Meridian already ships.
 *
 * ONE COPY, TWO CALLERS. This started inside the preview harness, where it
 * only fed the sales demo. The public demos need exactly the same screen, and
 * a second copy would have drifted the moment either changed — the harness
 * would keep showing a version of the overview that no prospect ever sees.
 *
 * Every call is a call the portal already makes, so the numbers are derived
 * from what is actually on the book rather than written into a mock.
 */
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { bookingsApi, type Booking, type BusyBlock, type Resource, type Service } from '@/lib/bookings-api'
import type { NichePack } from '@/config/niches'
import type { RouteOrigin } from '@/components/RouteDay'
import TradeWorkspace from '@/components/overview/TradeWorkspace'

/**
 * Feeds the trade overview from the same endpoints the portal uses, so the
 * numbers on it are derived from the day actually on the book rather than
 * written into a mock.
 */
export default function TradeWorkspaceHost({
  merchantId, pack, shopName, origin,
}: {
  merchantId: string
  pack: NichePack
  shopName: string
  /** Where a mobile trade's day starts. Only used by the trades that drive. */
  origin: RouteOrigin
}) {
  const [bookings, setBookings] = useState<Booking[]>([])
  const [resources, setResources] = useState<Resource[]>([])
  const [busy, setBusy] = useState<BusyBlock[]>([])
  const [services, setServices] = useState<Service[]>([])
  const [history, setHistory] = useState<{ day: string; cents: number }[]>([])
  const [forecasts, setForecasts] = useState<any[]>([])
  const [anomalies, setAnomalies] = useState<any[]>([])
  const [fortnight, setFortnight] = useState<Booking[]>([])
  const [timezone, setTimezone] = useState('')
  // Open on a day this trade actually trades. A barbershop shut on Sundays
  // showing an empty Sunday is CORRECT and a terrible first impression, so the
  // demo walks forward to the next day it is open.
  const [day, setDay] = useState(() => nextOpenDay(pack))

  useEffect(() => { setDay(nextOpenDay(pack)) }, [pack])

  // The forecasting and anomaly detection Meridian already ships. Called the
  // same way the rest of the portal calls them.
  useEffect(() => {
    if (!pack.booksAtAll) { setForecasts([]); setAnomalies([]); return }
    Promise.all([
      api.forecasts(merchantId).catch(() => ({ forecasts: [] })),
      api.anomalies(merchantId).catch(() => ({ anomalies: [] })),
    ]).then(([f, a]: any[]) => {
      setForecasts(f.forecasts || [])
      setAnomalies(a.anomalies || [])
    })
  }, [pack])

  useEffect(() => {
    if (!pack.booksAtAll) return
    const start = new Date(`${day}T00:00:00`)
    const from = new Date(start.getTime() - 12 * 3600_000).toISOString()
    const to = new Date(start.getTime() + 24 * 3600_000).toISOString()
    Promise.all([
      bookingsApi.listBookings(merchantId, from, to, false).catch(() => []),
      bookingsApi.listResources(merchantId).catch(() => []),
      bookingsApi.listBusy(merchantId, from, to).catch(() => []),
      bookingsApi.availability(merchantId, day, 1).catch(() => null),
      bookingsApi.listServices(merchantId).catch(() => []),
    ]).then(([b, r, bz, av, sv]) => {
      setBookings(b)
      setResources(r)
      setBusy(bz)
      setServices(sv)
      if (av) setTimezone(av.timezone)
    })
  }, [pack, day])

  // A fortnight of booked revenue, read the same way the day is — so the trend
  // and the comparison come from real bookings rather than a drawn curve.
  useEffect(() => {
    if (!pack.booksAtAll) { setHistory([]); return }
    const end = new Date(`${day}T00:00:00`)
    const from = new Date(end.getTime() - 13 * 86400_000)
    Promise.all([
      bookingsApi.listBookings(
        merchantId, from.toISOString(),
        new Date(end.getTime() + 86400_000).toISOString(), false).catch(() => []),
      bookingsApi.listServices(merchantId).catch(() => []),
    ]).then(([rows, sv]) => {
      const price = new Map(sv.map((x) => [x.id, x.priceCents ?? 0]))
      const byDay = new Map<string, number>()
      for (let i = 0; i < 14; i++) {
        const d = new Date(from.getTime() + i * 86400_000)
        byDay.set(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`, 0)
      }
      for (const b of rows) {
        const d = new Date(b.startsAt)
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
        if (!byDay.has(key)) continue
        const cents = pack.avgCoverCents
          ? b.partySize * pack.avgCoverCents
          : (price.get(b.serviceId || '') ?? 0)
        byDay.set(key, (byDay.get(key) || 0) + cents)
      }
      setHistory([...byDay.entries()].map(([d, cents]) => ({ day: d, cents })))
      setFortnight(rows)
    })
  }, [pack, day])

  const stops = bookings
    .filter((b) => b.serviceAddress && b.serviceLat != null && b.serviceLng != null)
    .map((b) => ({
      booking: b,
      address: b.serviceAddress as string,
      lat: b.serviceLat as number,
      lng: b.serviceLng as number,
    }))

  const shiftDay = (delta: number) => {
    const d = new Date(`${day}T12:00:00`)
    d.setDate(d.getDate() + delta)
    setDay(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`)
  }

  return (
    <TradeWorkspace
      pack={pack}
      shopName={shopName}
      bookings={bookings}
      resources={resources}
      services={services}
      history={history}
      forecasts={forecasts}
      anomalies={anomalies}
      fortnight={fortnight}
      busy={busy}
      timezone={timezone}
      day={day}
      onShiftDay={shiftDay}
      stops={stops}
      origin={origin}
    />
  )
}

/** The next date this trade is open, starting today. */
function nextOpenDay(pack: NichePack): string {
  const d = new Date()
  for (let i = 0; i < 8; i++) {
    if (!pack.booksAtAll || pack.days.includes(d.getDay())) break
    d.setDate(d.getDate() + 1)
  }
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
