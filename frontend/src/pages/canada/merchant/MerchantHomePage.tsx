import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  DollarSign, ShoppingCart, Receipt, Percent, ArrowUpRight, Plug, Sparkles,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCad, formatCadMo, formatNumber, formatPercent } from '@/lib/format'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import { useMerchantBasePath } from '@/hooks/useMerchantBasePath'
import Top3ActionsPanel from '@/components/Top3ActionsPanel'

/**
 * Canada-merchant home — the payable hero surface.
 *
 * Net sales count up on mount, recoverable revenue (money left on the table)
 * is surfaced in CA$, and four money tiles (net sales, transactions, avg
 * ticket, gross margin) carry 30-day sparklines. Honest empty states: when no
 * POS is connected we show a connect CTA, never a fake number.
 *
 * Scoped to /canada/merchant only — the shared OverviewPage (live on /app) is
 * left untouched. All colors come from the pm.* design tokens.
 */

function useCountUp(target: number, durationMs = 900): number {
  const [val, setVal] = useState(0)
  const raf = useRef<number | undefined>(undefined)
  useEffect(() => {
    if (typeof window !== 'undefined' &&
        window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      setVal(target)
      return
    }
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs)
      const eased = 1 - Math.pow(1 - t, 3)
      setVal(target * eased)
      if (t < 1) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => { if (raf.current) cancelAnimationFrame(raf.current) }
  }, [target, durationMs])
  return val
}

function Sparkline({ values, className }: { values: number[]; className?: string }) {
  if (!values || values.length < 2) return null
  const w = 100, h = 28
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w
      const y = h - ((v - min) / range) * h
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      className={clsx('w-full h-7', className)}
    >
      <polyline
        points={pts}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        vectorEffect="non-scaling-stroke"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}

interface TileProps {
  label: string
  value: string
  icon: typeof DollarSign
  iconColor: string
  sparkColor?: string
  spark?: number[]
  change?: string
  changeType?: 'positive' | 'negative'
  subtitle?: string
}

function MoneyTile({
  label, value, icon: Icon, iconColor, sparkColor, spark, change, changeType, subtitle,
}: TileProps) {
  return (
    <div className="rounded-xl bg-pm-surface border border-pm-border p-4 sm:p-5 flex flex-col">
      <div className="flex items-start justify-between gap-2">
        <p className="text-2xs font-medium uppercase tracking-wider text-pm-muted truncate">{label}</p>
        <span className={clsx('p-1.5 rounded-lg bg-pm-border/60 flex-shrink-0', iconColor)}>
          <Icon size={15} />
        </span>
      </div>
      <p className="mt-2 text-xl sm:text-2xl font-bold font-mono text-pm-text tracking-tight">{value}</p>
      {change && (
        <p className={clsx(
          'mt-1 text-2xs font-semibold font-mono',
          changeType === 'negative' ? 'text-pm-amber-orange' : 'text-pm-teal',
        )}>
          {change}{subtitle ? ` · ${subtitle}` : ''}
        </p>
      )}
      {!change && subtitle && (
        <p className="mt-1 text-2xs text-pm-muted/70">{subtitle}</p>
      )}
      {spark && spark.length > 1 && (
        <div className={clsx('mt-auto pt-3', sparkColor ?? 'text-pm-blue')}>
          <Sparkline values={spark} />
        </div>
      )}
    </div>
  )
}

export default function MerchantHomePage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const posConnected = !!org?.pos_connected
  const skip = !isDemo && !posConnected
  const basePath = useMerchantBasePath()

  const overview = useApi(() => (skip ? api.overview('') : api.overview(orgId)), [orgId, skip])
  // Pull a year of daily revenue so the sparklines reflect backfilled history,
  // not just the last 30 days (which is empty for a merchant whose data predates
  // the connect).
  const revenue = useApi(() => (skip ? api.revenue('', 365) : api.revenue(orgId, 365)), [orgId, skip])
  const margins = useApi<{ items: Array<{ revenueCents: number; marginCents: number }> }>(
    () => (skip ? Promise.resolve({ items: [] }) : api.margins(orgId)),
    [orgId, skip],
  )

  const data = overview.data
  const net30d = data?.revenue_cents_30d ?? 0
  const lifetimeCents = data?.lifetime_revenue_cents ?? 0
  // No sales in the last 30 days but the merchant has backfilled history →
  // show all-time figures instead of a bare $0 ("connected but nothing shows").
  const showLifetime = net30d === 0 && lifetimeCents > 0
  const netCents = showLifetime ? lifetimeCents : net30d
  const txCount = showLifetime
    ? (data?.lifetime_transaction_count ?? 0)
    : (data?.transaction_count_30d ?? 0)
  const avgTicket = showLifetime
    ? (data?.lifetime_avg_ticket_cents ?? 0)
    : (data?.avg_ticket_cents ?? 0)
  const periodLabel = showLifetime ? 'all time' : '30 days'
  const lastActivity = data?.last_activity_at
    ? new Date(data.last_activity_at).toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })
    : null
  const animatedNet = useCountUp(skip ? 0 : netCents)

  // ── Data-destination scaffold: no POS connected ───────────────────────
  // Instead of a bare "connect" card, show the real home layout with empty
  // placeholders so the merchant sees exactly where their numbers will land.
  if (skip) {
    return (
      <div className="space-y-6 max-w-content">
        <div>
          <h1 className="text-2xl font-bold text-pm-text">
            {org?.business_name ? `Welcome, ${org.business_name}` : 'Welcome'}
          </h1>
          <p className="text-sm text-pm-muted mt-1">
            Here's where your numbers will live. Connect your POS to fill it in.
          </p>
        </div>

        {/* Connect banner */}
        <div className="rounded-2xl bg-pm-teal/[0.06] border border-pm-teal/25 p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center gap-4">
          <span className="inline-flex p-3 rounded-2xl bg-pm-teal/10 text-pm-teal flex-shrink-0">
            <Plug size={26} />
          </span>
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-semibold text-pm-text">Connect your point of sale</h2>
            <p className="mt-0.5 text-sm text-pm-muted">
              One click brings your sales, inventory and call data into Meridian.
              About four minutes — first month free.
            </p>
          </div>
          <Link
            to={`${basePath}/onboard`}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-pm-teal text-pm-bg font-bold text-sm hover:bg-pm-teal/90 transition-colors flex-shrink-0"
          >
            Connect your POS
            <ArrowUpRight size={16} />
          </Link>
        </div>

        {/* Hero scaffold: net sales destination */}
        <div className="rounded-2xl bg-pm-surface border border-pm-border p-6 sm:p-8">
          <p className="text-2xs font-semibold uppercase tracking-wider text-pm-muted">Net sales · 30 days</p>
          <p className="mt-1.5 text-4xl sm:text-5xl font-bold font-mono text-pm-text/15 tracking-tight tabular-nums">—</p>
          <p className="mt-2 text-sm text-pm-muted/60">Your net sales appear here once connected</p>
        </div>

        {/* Four money tile destinations */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {[
            { label: 'Net Sales', icon: DollarSign, color: 'text-pm-teal' },
            { label: 'Transactions', icon: ShoppingCart, color: 'text-pm-blue' },
            { label: 'Avg Ticket', icon: Receipt, color: 'text-pm-blue' },
            { label: 'Gross Margin', icon: Percent, color: 'text-pm-amber-gold' },
          ].map(({ label, icon: Icon, color }) => (
            <div key={label} className="rounded-xl bg-pm-surface border border-pm-border p-4 sm:p-5 flex flex-col">
              <div className="flex items-start justify-between gap-2">
                <p className="text-2xs font-medium uppercase tracking-wider text-pm-muted truncate">{label}</p>
                <span className={clsx('p-1.5 rounded-lg bg-pm-border/60 flex-shrink-0', color)}>
                  <Icon size={15} />
                </span>
              </div>
              <p className="mt-2 text-xl sm:text-2xl font-bold font-mono text-pm-text/15 tracking-tight">—</p>
            </div>
          ))}
        </div>

        {/* Top 3 Actions — pre-connection teaser (standby agents + locked state) */}
        <Top3ActionsPanel connected={false} />

        {/* Pillar quick links — already navigable */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { to: 'inventory', label: 'Inventory', hint: 'Stock, margins & forecasts' },
            { to: 'schedule', label: 'Schedule', hint: 'Shifts & peak hours' },
            { to: 'phone', label: 'Phone Calls', hint: 'Orders taken by phone' },
          ].map(p => (
            <Link
              key={p.to}
              to={`${basePath}/${p.to}`}
              className="group flex items-center justify-between rounded-xl bg-pm-surface border border-pm-border p-4 hover:border-pm-blue/40 transition-colors"
            >
              <div>
                <p className="text-sm font-semibold text-pm-text">{p.label}</p>
                <p className="text-2xs text-pm-muted mt-0.5">{p.hint}</p>
              </div>
              <ArrowUpRight size={16} className="text-pm-muted group-hover:text-pm-blue transition-colors" />
            </Link>
          ))}
        </div>
      </div>
    )
  }

  if (overview.loading || !data) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-7 w-48 rounded bg-pm-surface" />
        <div className="h-28 rounded-2xl bg-pm-surface" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {[0, 1, 2, 3].map(i => <div key={i} className="h-32 rounded-xl bg-pm-surface" />)}
        </div>
      </div>
    )
  }

  const daily = revenue.data?.daily ?? []
  const revSpark = daily.map(d => d.revenue_cents)
  const txSpark = daily.map(d => d.transactions)
  const ticketSpark = daily.map(d => d.avg_ticket_cents)

  const marginItems = margins.data?.items ?? []
  const totalRev = marginItems.reduce((s, m) => s + (m.revenueCents || 0), 0)
  const totalMargin = marginItems.reduce((s, m) => s + (m.marginCents || 0), 0)
  const marginPct = totalRev > 0 ? (totalMargin / totalRev) * 100 : null

  const recoverableCents = data.money_left_score?.total_score_cents ?? 0
  const changeType = data.revenue_change_pct >= 0 ? 'positive' : 'negative'

  return (
    <div className="space-y-6 max-w-content">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-pm-text">
            {org?.business_name || 'Dashboard'}
          </h1>
          <p className="text-sm text-pm-muted mt-1">
            {showLifetime
              ? <>All time · <span className="font-mono">{data.lifetime_days_with_data}</span> days with data</>
              : <>Last 30 days · <span className="font-mono">{data.days_with_data}</span> days with data</>}
          </p>
        </div>
        <span className={clsx(
          'self-start inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-2xs font-medium',
          data.connection.status === 'connected'
            ? 'bg-pm-teal/10 text-pm-teal'
            : 'bg-pm-amber-orange/10 text-pm-amber-orange',
        )}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {data.connection.provider ? `${data.connection.provider} · ` : ''}
          {data.connection.status === 'connected' ? 'Connected' : data.connection.status}
        </span>
      </div>

      {/* Hero: net sales (count-up) + recoverable revenue */}
      <div className="rounded-2xl bg-pm-surface border border-pm-border p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div>
            <p className="text-2xs font-semibold uppercase tracking-wider text-pm-muted">Net sales · {periodLabel}</p>
            <p className="mt-1.5 text-4xl sm:text-5xl font-bold font-mono text-pm-text tracking-tight tabular-nums">
              {formatCad(animatedNet / 100)}
            </p>
            {showLifetime ? (
              <p className="mt-2 text-sm font-semibold font-mono text-pm-muted">
                No sales in the last 30 days{lastActivity ? ` · last activity ${lastActivity}` : ''}
              </p>
            ) : (
              <p className={clsx(
                'mt-2 text-sm font-semibold font-mono',
                changeType === 'negative' ? 'text-pm-amber-orange' : 'text-pm-teal',
              )}>
                {formatPercent(data.revenue_change_pct)} vs. prior 30 days
              </p>
            )}
          </div>
          {recoverableCents > 0 && (
            <Link
              to={`${basePath}/inventory`}
              className="group rounded-xl border border-pm-amber-gold/25 bg-pm-amber-gold/5 p-4 hover:bg-pm-amber-gold/10 transition-colors"
            >
              <div className="flex items-center gap-1.5 text-pm-amber-gold">
                <Sparkles size={14} />
                <span className="text-2xs font-semibold uppercase tracking-wider">Recoverable</span>
              </div>
              <p className="mt-1 text-2xl font-bold font-mono text-pm-amber-gold tabular-nums">
                {formatCadMo(recoverableCents / 100)}
              </p>
              <p className="mt-0.5 text-2xs text-pm-muted group-hover:text-pm-text transition-colors">
                Money left on the table — see how →
              </p>
            </Link>
          )}
        </div>
      </div>

      {/* Four money tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <MoneyTile
          label="Net Sales"
          value={formatCad(netCents / 100)}
          icon={DollarSign}
          iconColor="text-pm-teal"
          sparkColor="text-pm-teal"
          spark={revSpark}
          change={showLifetime ? undefined : formatPercent(data.revenue_change_pct)}
          changeType={changeType}
          subtitle={showLifetime ? 'all time' : '30d'}
        />
        <MoneyTile
          label="Transactions"
          value={formatNumber(txCount)}
          icon={ShoppingCart}
          iconColor="text-pm-blue"
          sparkColor="text-pm-blue"
          spark={txSpark}
          subtitle={periodLabel}
        />
        <MoneyTile
          label="Avg Ticket"
          value={formatCad(avgTicket / 100)}
          icon={Receipt}
          iconColor="text-pm-blue"
          sparkColor="text-pm-blue"
          spark={ticketSpark}
          subtitle={periodLabel}
        />
        <MoneyTile
          label="Gross Margin"
          value={marginPct != null ? `${marginPct.toFixed(1)}%` : '—'}
          icon={Percent}
          iconColor={marginPct != null && marginPct < 55 ? 'text-pm-amber-orange' : 'text-pm-amber-gold'}
          subtitle={marginPct != null ? 'blended' : 'analyzing…'}
        />
      </div>

      {/* Top 3 Actions */}
      <Top3ActionsPanel />

      {/* Pillar quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { to: 'inventory', label: 'Inventory', hint: 'Stock, margins & forecasts' },
          { to: 'schedule', label: 'Schedule', hint: 'Shifts & peak hours' },
          { to: 'phone', label: 'Phone Calls', hint: 'Orders taken by phone' },
        ].map(p => (
          <Link
            key={p.to}
            to={`${basePath}/${p.to}`}
            className="group flex items-center justify-between rounded-xl bg-pm-surface border border-pm-border p-4 hover:border-pm-blue/40 transition-colors"
          >
            <div>
              <p className="text-sm font-semibold text-pm-text">{p.label}</p>
              <p className="text-2xs text-pm-muted mt-0.5">{p.hint}</p>
            </div>
            <ArrowUpRight size={16} className="text-pm-muted group-hover:text-pm-blue transition-colors" />
          </Link>
        ))}
      </div>
    </div>
  )
}
