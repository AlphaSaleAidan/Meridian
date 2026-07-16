import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertCircle, CheckCircle2, Info, Loader2, Zap } from 'lucide-react'
import {
  phoneService, type TestOrderResponse, type TestOrderStatus,
} from '@/lib/phone-service'

/**
 * Kitchen prove-out card — the last mile of phone-agent onboarding.
 *
 * Sends a clearly-marked TEST ORDER through the REAL dispatch pipeline
 * (POST /api/phone/test-order/{merchant_id}) and shows a live per-channel
 * checklist while polling the status endpoint:
 *
 *   POS ticket created ✓ / ✗ (with the exact error)
 *   Reached the kitchen ✓ (POS-confirmed make-able state) / printer check
 *   Merchant SMS sent ✓ / ✗
 *
 * Demo mode simulates the sequence locally — nothing hits the backend.
 */

type Phase = 'idle' | 'sending' | 'polling' | 'done' | 'error'

const POLL_INTERVAL_MS = 3_000
const POLL_BUDGET_MS = 50_000 // backend polls Square ~30s; leave headroom

type RowState = 'ok' | 'fail' | 'pending' | 'info' | 'idle'

function Row({ state, label, detail }: { state: RowState; label: string; detail?: string }) {
  return (
    <div className="flex items-start gap-2.5">
      {state === 'ok' && <CheckCircle2 size={15} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />}
      {state === 'fail' && <AlertCircle size={15} className="text-red-400 mt-0.5 flex-shrink-0" />}
      {state === 'pending' && <Loader2 size={15} className="text-[#1A8FD6] animate-spin mt-0.5 flex-shrink-0" />}
      {state === 'info' && <Info size={15} className="text-amber-400 mt-0.5 flex-shrink-0" />}
      {state === 'idle' && <div className="w-[15px] h-[15px] rounded-full border border-[#2A2A30] mt-0.5 flex-shrink-0" />}
      <div className="min-w-0">
        <p className="text-xs text-[#F5F5F7] leading-relaxed">{label}</p>
        {detail && <p className="text-[10px] text-[#A1A1A8] mt-0.5 break-words">{detail}</p>}
      </div>
    </div>
  )
}

export function TestOrderProveOut({ orgId, isDemo }: { orgId: string | null; isDemo: boolean }) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<TestOrderResponse | null>(null)
  const [status, setStatus] = useState<TestOrderStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => { if (pollTimer.current) clearTimeout(pollTimer.current) }, [])

  const busy = phase === 'sending' || phase === 'polling'

  const send = useCallback(async () => {
    if (busy) return
    if (pollTimer.current) clearTimeout(pollTimer.current)
    setError(null); setStatus(null); setResult(null)

    if (isDemo) {
      // Demo mode: simulate the full sequence locally (no backend writes).
      setPhase('sending')
      pollTimer.current = setTimeout(() => {
        setResult({
          ok: true, order_id: 'demo', pos_order_id: 'DEMO-TICKET-1', pos_system: 'square',
          demo_safe: true, verifying: true,
          channels: { pos: { status: 'sent' }, customer_sms: { status: 'skipped_disabled' }, merchant_sms: { status: 'sent' } },
          item: 'Cheese Pizza', total: 14,
        })
        setPhase('polling')
        pollTimer.current = setTimeout(() => {
          setStatus({
            order_id: 'demo', pos_delivery_status: 'sent', merchant_notify_status: 'sent',
            fulfillment_state: 'OPEN', fulfillment_confirmed_at: new Date().toISOString(),
          })
          setPhase('done')
        }, 2500)
      }, 900)
      return
    }

    if (!orgId) {
      setError('Your account is still being set up — refresh and try again.')
      setPhase('error')
      return
    }

    setPhase('sending')
    try {
      const res = await phoneService.sendTestOrder(orgId)
      setResult(res)
      if (res.order_id && res.verifying) {
        setPhase('polling')
        const startedAt = Date.now()
        const poll = async () => {
          const st = await phoneService.getTestOrderStatus(orgId, res.order_id!)
          if (st) setStatus(st)
          const confirmed = !!st?.fulfillment_confirmed_at
          const terminal = st?.fulfillment_state === 'CANCELED' || st?.fulfillment_state === 'unsupported'
          if (confirmed || terminal || Date.now() - startedAt > POLL_BUDGET_MS) {
            setPhase('done')
            return
          }
          pollTimer.current = setTimeout(poll, POLL_INTERVAL_MS)
        }
        pollTimer.current = setTimeout(poll, POLL_INTERVAL_MS)
      } else {
        setPhase('done')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Test order failed')
      setPhase('error')
    }
  }, [busy, isDemo, orgId])

  // ── Derive the checklist from the immediate result + polled status ──
  const posStatus = status?.pos_delivery_status || result?.channels?.pos?.status
  const posError = (status?.delivery_detail?.pos?.error as string | undefined)
    || result?.channels?.pos?.error
  const merchantStatus = status?.merchant_notify_status || result?.channels?.merchant_sms?.status
  const merchantError = (status?.delivery_detail?.merchant_sms?.error as string | undefined)
    || result?.channels?.merchant_sms?.error

  let posRow: { state: RowState; label: string; detail?: string }
  if (!posStatus) posRow = { state: phase === 'sending' ? 'pending' : 'idle', label: 'POS ticket created' }
  else if (posStatus === 'sent') posRow = {
    state: 'ok', label: 'Test ticket created in your POS',
    detail: result?.pos_order_id ? `Order ${result.pos_order_id}` : undefined,
  }
  else if (posStatus === 'demo_safe') posRow = {
    state: 'info', label: 'Demo-safe mode — POS write skipped',
    detail: 'This account is flagged demo-safe, so no live ticket was created.',
  }
  else if (posStatus === 'skipped_no_pos') posRow = {
    state: 'info', label: 'No POS connected',
    detail: 'Orders are delivered to you by SMS instead — connect a POS for direct tickets.',
  }
  else if (posStatus.startsWith('skipped')) posRow = {
    state: 'info', label: 'POS delivery is turned off for this account',
  }
  else posRow = { state: 'fail', label: 'POS ticket failed', detail: posError || posStatus }

  let kitchenRow: { state: RowState; label: string; detail?: string }
  if (posStatus !== 'sent') kitchenRow = {
    state: 'idle', label: 'Reached the kitchen', detail: posStatus ? 'Skipped — no POS ticket was created.' : undefined,
  }
  else if (status?.fulfillment_confirmed_at) kitchenRow = {
    state: 'ok', label: 'Reached the kitchen — your POS confirms the ticket is live',
    detail: status.fulfillment_state ? `POS order state: ${status.fulfillment_state}` : undefined,
  }
  else if (status?.fulfillment_state === 'unsupported') kitchenRow = {
    state: 'info', label: 'Auto-check not available for this POS yet',
    detail: 'Check that the ticket printed in the kitchen.',
  }
  else if (status?.fulfillment_state === 'CANCELED') kitchenRow = {
    state: 'fail', label: 'Ticket was canceled on the POS side',
  }
  else if (phase === 'polling') kitchenRow = {
    state: 'pending', label: 'Confirming with your POS…', detail: 'Usually takes under 30 seconds.',
  }
  else if (phase === 'done') kitchenRow = {
    state: 'fail', label: "Couldn't confirm the ticket reached the kitchen",
    detail: status?.fulfillment_state
      ? `Last POS state: ${status.fulfillment_state} — check the printer or contact support.`
      : 'Check the kitchen printer, or contact support.',
  }
  else kitchenRow = { state: 'idle', label: 'Reached the kitchen' }

  let smsRow: { state: RowState; label: string; detail?: string }
  if (!merchantStatus) smsRow = { state: phase === 'sending' ? 'pending' : 'idle', label: 'Order alert texted to you' }
  else if (merchantStatus === 'sent') smsRow = { state: 'ok', label: 'Order alert texted to your notification number' }
  else if (merchantStatus === 'skipped_no_number') smsRow = {
    state: 'info', label: 'No notification number set',
    detail: 'Add a transfer number in the Routing step to get order texts.',
  }
  else if (merchantStatus.startsWith('skipped')) smsRow = {
    state: 'info', label: 'Merchant order texts are turned off',
  }
  else smsRow = { state: 'fail', label: 'Order alert SMS failed', detail: merchantError || merchantStatus }

  return (
    <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-[#F5F5F7]">Prove it reaches the kitchen</p>
          <p className="text-[10px] text-[#A1A1A8] mt-0.5 leading-relaxed">
            This sends a clearly-marked test ticket to your POS — check that it prints in the
            kitchen, then delete it.
          </p>
        </div>
        <button
          onClick={send}
          disabled={busy}
          className="flex items-center gap-1.5 px-3 py-2 bg-[#1A8FD6] text-white text-xs font-semibold rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-colors flex-shrink-0"
        >
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
          {phase === 'sending' ? 'Sending…' : phase === 'polling' ? 'Checking…'
            : phase === 'done' || phase === 'error' ? 'Send again' : 'Send test order'}
        </button>
      </div>

      {error && (
        <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] flex items-center gap-2">
          <AlertCircle size={12} className="flex-shrink-0" /> {error}
        </div>
      )}

      {(result || busy) && (
        <div className="space-y-2 pt-1">
          <Row {...posRow} />
          <Row {...kitchenRow} />
          <Row {...smsRow} />
          {result?.item && (
            <p className="text-[9px] text-[#A1A1A8]/50 pt-0.5">
              Test ticket: 1× {result.item} for “MERIDIAN TEST ORDER” — marked “TEST — do not make”.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
