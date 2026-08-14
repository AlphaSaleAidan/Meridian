/**
 * Ad Spot console — where a rep watches a sold 30-second spot come together
 * and hands it over.
 *
 * One component, both markets: the US portal renders in hex brand colors and
 * Canada in its pm-canada-* tokens, so the palette arrives as a `theme` prop
 * rather than being forked into two near-identical files.
 *
 * The screen is built around one rule: never claim a spot is further along
 * than it is. Shot tiles show real per-shot state (with the actual clip
 * playable), assembly reports what it had to leave out, and "Deliver" is a
 * separate, deliberate action from "Assemble".
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle, Check, Clapperboard, Download, Loader2, RefreshCw, Send, Film,
} from 'lucide-react'
import {
  adSpotApi, adSpotPriceLabel, AD_SPOT_STATUS_LABEL,
  type AdSpotDetail, type AdSpotOrder, type AdSpotStatus,
} from '@/lib/ad-spot-api'

export interface AdSpotTheme {
  /** page + card surfaces */
  surface: string
  bg: string
  border: string
  /** text ramp: primary is white in both markets */
  muted: string
  faint: string
  /** brand accent (teal in both, different token systems) */
  accent: string
  accentBg: string
  accentBorder: string
  warn: string
}

/** Statuses where the server is still doing something — poll while here. */
const LIVE: AdSpotStatus[] = ['boarding', 'generating', 'assembling']

function StatusPill({ status, theme }: { status: AdSpotStatus; theme: AdSpotTheme }) {
  const tone =
    status === 'delivered' ? `${theme.accent} ${theme.accentBg}`
      : status === 'failed' ? `${theme.warn} bg-current/10`
        : `${theme.muted} ${theme.bg}`
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium ${tone}`}>
      {LIVE.includes(status) && <Loader2 size={11} className="animate-spin" />}
      {status === 'delivered' && <Check size={11} />}
      {status === 'failed' && <AlertTriangle size={11} />}
      {AD_SPOT_STATUS_LABEL[status]}
    </span>
  )
}

export default function AdSpotConsole({
  theme,
  repId,
  title = 'Ad Spots',
}: {
  theme: AdSpotTheme
  /** Scope the list to one rep. Omit to show the most recent orders. */
  repId?: string
  title?: string
}) {
  const [orders, setOrders] = useState<AdSpotOrder[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [detail, setDetail] = useState<AdSpotDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string>('')
  const [assembleNotes, setAssembleNotes] = useState<string[]>([])
  const pollRef = useRef<number | null>(null)

  const loadOrders = useCallback(async () => {
    try {
      const res = await adSpotApi.list(repId)
      setOrders(res.orders || [])
      setSelectedId(cur => cur || res.orders?.[0]?.id || '')
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load ad spots')
    } finally {
      setLoading(false)
    }
  }, [repId])

  const loadDetail = useCallback(async (id: string) => {
    if (!id) return
    try {
      setDetail(await adSpotApi.get(id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load that spot')
    }
  }, [])

  useEffect(() => { void loadOrders() }, [loadOrders])
  useEffect(() => { void loadDetail(selectedId) }, [selectedId, loadDetail])

  // Poll only while the server is actually working — a delivered spot is not
  // going to change on its own, and reps leave this tab open all day.
  useEffect(() => {
    const status = detail?.order?.status
    if (!status || !LIVE.includes(status)) return
    pollRef.current = window.setInterval(() => { void loadDetail(selectedId) }, 8000)
    return () => { if (pollRef.current) window.clearInterval(pollRef.current) }
  }, [detail?.order?.status, selectedId, loadDetail])

  async function run(key: string, fn: () => Promise<unknown>) {
    setBusy(key)
    setError(null)
    try {
      await fn()
      await loadDetail(selectedId)
      await loadOrders()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'That did not work')
    } finally {
      setBusy('')
    }
  }

  const order = detail?.order
  const shots = detail?.shots || []
  const completed = shots.filter(s => s.status === 'completed').length

  if (loading) {
    return (
      <div className={`flex items-center gap-2 p-6 ${theme.muted}`}>
        <Loader2 size={16} className="animate-spin" /> <span className="text-sm">Loading ad spots…</span>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clapperboard size={18} className={theme.accent} />
          <h1 className="text-lg font-bold text-white">{title}</h1>
        </div>
        <button
          onClick={() => void loadOrders()}
          className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border ${theme.border} ${theme.muted} hover:text-white transition-colors`}
        >
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {error && (
        <div className={`rounded-xl p-4 border ${theme.border} ${theme.surface}`}>
          <p className={`text-sm font-semibold ${theme.warn}`}>{error}</p>
        </div>
      )}

      {orders.length === 0 ? (
        <div className={`rounded-xl p-8 border ${theme.border} ${theme.surface} text-center`}>
          <Film size={24} className={`mx-auto mb-3 ${theme.faint}`} />
          <p className="text-sm text-white font-medium">No spots sold yet</p>
          <p className={`text-xs mt-1 ${theme.muted}`}>
            Toggle the 30-Second AI Advertisement on a deal and it lands here the moment you close.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
          {/* Order list */}
          <div className="space-y-2">
            {orders.map(o => (
              <button
                key={o.id}
                onClick={() => { setSelectedId(o.id); setAssembleNotes([]) }}
                className={`w-full text-left rounded-xl p-3 border transition-colors ${
                  o.id === selectedId ? `${theme.accentBorder} ${theme.accentBg}` : `${theme.border} ${theme.surface}`
                }`}
              >
                <p className="text-sm font-semibold text-white truncate">{o.business_name}</p>
                <div className="flex items-center justify-between mt-1.5">
                  <StatusPill status={o.status} theme={theme} />
                  <span className={`text-[11px] font-mono ${theme.muted}`}>{adSpotPriceLabel(o)}</span>
                </div>
              </button>
            ))}
          </div>

          {/* Detail */}
          {order && (
            <div className="space-y-4">
              <div className={`rounded-xl p-5 border ${theme.border} ${theme.surface}`}>
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div>
                    <h2 className="text-base font-bold text-white">{order.business_name}</h2>
                    <p className={`text-xs mt-0.5 ${theme.muted}`}>
                      {adSpotPriceLabel(order)} · {order.aspect_ratio || '9:16'} · {order.audio.replace(/_/g, ' + ')}
                      {order.rep_name ? ` · sold by ${order.rep_name}` : ''}
                    </p>
                  </div>
                  <StatusPill status={order.status} theme={theme} />
                </div>

                <p className={`text-[11px] font-mono uppercase tracking-wider mb-1 ${theme.faint}`}>The brief</p>
                <p className={`text-xs leading-relaxed ${theme.muted}`}>{order.goal}</p>
                {order.highlights && (
                  <p className={`text-xs mt-1.5 ${theme.muted}`}>
                    <span className={theme.faint}>Featuring: </span>{order.highlights}
                  </p>
                )}
                {order.status_detail && (
                  <p className={`text-[11px] mt-3 pt-3 border-t ${theme.border} ${theme.faint}`}>{order.status_detail}</p>
                )}
                {order.foundry_job_id ? (
                  <a
                    href={`https://foundry.meridian.tips/agency/jobs/${order.foundry_job_id}`}
                    target="_blank" rel="noopener noreferrer"
                    className={`inline-flex items-center gap-1.5 mt-2 text-[11px] ${theme.accent} hover:underline`}
                  >
                    <Film size={12} /> Creator contest is live on Foundry — the owner can pick from those cuts too
                  </a>
                ) : order.foundry_detail ? (
                  <p className={`text-[11px] mt-2 ${theme.faint}`}>Foundry contest: {order.foundry_detail}</p>
                ) : null}
              </div>

              {/* Shots */}
              <div className={`rounded-xl p-5 border ${theme.border} ${theme.surface}`}>
                <div className="flex items-center justify-between mb-3">
                  <p className={`text-[11px] font-mono uppercase tracking-wider ${theme.faint}`}>
                    Shots — {completed}/{detail?.shotsTotal ?? shots.length} generated
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                  {shots.map(shot => (
                    <div key={shot.id} className={`rounded-lg border ${theme.border} ${theme.bg} overflow-hidden`}>
                      {shot.video_url ? (
                        <video
                          src={shot.video_url}
                          controls
                          preload="metadata"
                          className="w-full aspect-video bg-black object-contain"
                        />
                      ) : (
                        <div className={`w-full aspect-video flex items-center justify-center ${theme.faint}`}>
                          {shot.status === 'failed'
                            ? <AlertTriangle size={18} />
                            : <Loader2 size={18} className="animate-spin" />}
                        </div>
                      )}
                      <div className="p-2.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[11px] font-mono text-white">Shot {shot.shot_number}</span>
                          <button
                            disabled={busy === `retry-${shot.shot_number}`}
                            onClick={() => void run(`retry-${shot.shot_number}`, () => adSpotApi.retryShot(order.id, shot.shot_number))}
                            className={`flex items-center gap-1 text-[10px] ${theme.muted} hover:text-white transition-colors disabled:opacity-50`}
                          >
                            {busy === `retry-${shot.shot_number}`
                              ? <Loader2 size={10} className="animate-spin" />
                              : <RefreshCw size={10} />}
                            Re-roll
                          </button>
                        </div>
                        {shot.beat && <p className={`text-[10px] mt-1 line-clamp-2 ${theme.muted}`}>{shot.beat}</p>}
                        {shot.error && <p className={`text-[10px] mt-1 ${theme.warn}`}>{shot.error}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* The cut */}
              <div className={`rounded-xl p-5 border ${theme.border} ${theme.surface}`}>
                <p className={`text-[11px] font-mono uppercase tracking-wider mb-3 ${theme.faint}`}>The cut</p>

                {order.master_url ? (
                  <video src={order.master_url} controls preload="metadata"
                    className="w-full max-h-[420px] bg-black rounded-lg mb-3 object-contain" />
                ) : (
                  <p className={`text-xs mb-3 ${theme.muted}`}>
                    {completed === 0
                      ? 'No footage yet — the cut can run once shots land.'
                      : `${completed} shot(s) ready. Assemble to cut the master.`}
                  </p>
                )}

                {(assembleNotes.length > 0 || (order.assembly_notes?.notes?.length ?? 0) > 0) && (
                  <div className={`rounded-lg border ${theme.border} ${theme.bg} p-3 mb-3`}>
                    <p className={`text-[10px] font-mono uppercase tracking-wider mb-1.5 ${theme.warn}`}>
                      What the cut left out
                    </p>
                    {(assembleNotes.length ? assembleNotes : order.assembly_notes?.notes || []).map(n => (
                      <p key={n} className={`text-[11px] ${theme.muted}`}>· {n}</p>
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    disabled={busy === 'assemble' || completed === 0}
                    onClick={() => void run('assemble', async () => {
                      setAssembleNotes([])
                      await adSpotApi.assemble(order.id)
                    })}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium rounded-lg border ${theme.accentBorder} ${theme.accentBg} ${theme.accent} disabled:opacity-40 transition-colors`}
                  >
                    {busy === 'assemble' ? <Loader2 size={13} className="animate-spin" /> : <Film size={13} />}
                    {order.master_url ? 'Re-cut master' : 'Assemble master'}
                  </button>

                  {order.master_url && (
                    <a href={order.master_url} target="_blank" rel="noopener noreferrer"
                      className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium rounded-lg border ${theme.border} ${theme.muted} hover:text-white transition-colors`}>
                      <Download size={13} /> Open master
                    </a>
                  )}

                  {order.master_url && order.status !== 'delivered' && (
                    <button
                      disabled={busy === 'deliver'}
                      onClick={() => void run('deliver', () => adSpotApi.deliver(order.id))}
                      className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium rounded-lg border ${theme.accentBorder} ${theme.accentBg} ${theme.accent} disabled:opacity-40 transition-colors`}
                    >
                      {busy === 'deliver' ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                      Mark delivered
                    </button>
                  )}

                  {order.status === 'delivered' && order.delivered_at && (
                    <span className={`text-[11px] ${theme.accent}`}>
                      Delivered {new Date(order.delivered_at).toLocaleDateString()}
                    </span>
                  )}
                </div>

                {order.master_url && order.status !== 'delivered' && (
                  <p className={`text-[10px] mt-2 ${theme.faint}`}>
                    Watch it before you mark it delivered — assembly cuts the picture and the read, it does not judge them.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
