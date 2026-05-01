/**Lightweight error monitor — intercepts errors and batches to Cline API.

Captures: console.error, failed fetch, window.onerror, unhandledrejection,
rage clicks. Batches reports to /api/cline/report-error every 10s.
Target: <2KB bundle.
**/

const API_BASE = import.meta.env.VITE_API_URL || ''
const BATCH_INTERVAL = 10_000
const MAX_QUEUE = 20
const RAGE_CLICK_THRESHOLD = 3
const RAGE_CLICK_WINDOW = 800

interface ErrorEntry {
  message: string
  stack?: string
  url: string
  timestamp: number
}

let queue: ErrorEntry[] = []
let orgId = ''
let flushTimer: ReturnType<typeof setTimeout> | null = null
let clickTimes: number[] = []

function enqueue(entry: ErrorEntry) {
  if (queue.length >= MAX_QUEUE) queue.shift()
  queue.push(entry)
  scheduleFlush()
}

function scheduleFlush() {
  if (flushTimer) return
  flushTimer = setTimeout(flush, BATCH_INTERVAL)
}

async function flush() {
  flushTimer = null
  if (!queue.length || !orgId) return

  const batch = queue.splice(0, MAX_QUEUE)
  for (const entry of batch) {
    try {
      await fetch(`${API_BASE}/api/cline/report-error`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: orgId,
          message: entry.message,
          stack_trace: entry.stack || '',
          url: entry.url,
          user_agent: navigator.userAgent,
        }),
      })
    } catch {
      // Silent — don't recurse
    }
  }
}

export function initErrorMonitor(organizationId: string) {
  orgId = organizationId

  const origConsoleError = console.error
  console.error = (...args: unknown[]) => {
    origConsoleError.apply(console, args)
    const msg = args.map(a => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' ')
    enqueue({ message: msg.slice(0, 500), url: location.href, timestamp: Date.now() })
  }

  window.onerror = (message, source, lineno, colno, error) => {
    enqueue({
      message: String(message).slice(0, 500),
      stack: error?.stack?.slice(0, 2000),
      url: `${source || location.href}:${lineno}:${colno}`,
      timestamp: Date.now(),
    })
  }

  window.addEventListener('unhandledrejection', (e) => {
    const msg = e.reason instanceof Error ? e.reason.message : String(e.reason)
    enqueue({
      message: `Unhandled rejection: ${msg}`.slice(0, 500),
      stack: e.reason instanceof Error ? e.reason.stack?.slice(0, 2000) : undefined,
      url: location.href,
      timestamp: Date.now(),
    })
  })

  const origFetch = window.fetch
  window.fetch = async (...args) => {
    try {
      const res = await origFetch(...args)
      if (res.status >= 500) {
        const url = typeof args[0] === 'string' ? args[0] : (args[0] as Request)?.url || ''
        if (!url.includes('/api/cline/')) {
          enqueue({
            message: `Fetch ${res.status}: ${url}`.slice(0, 500),
            url: url.slice(0, 200),
            timestamp: Date.now(),
          })
        }
      }
      return res
    } catch (err) {
      const url = typeof args[0] === 'string' ? args[0] : (args[0] as Request)?.url || ''
      if (!url.includes('/api/cline/')) {
        enqueue({
          message: `Fetch error: ${err instanceof Error ? err.message : String(err)}`.slice(0, 500),
          url: url.slice(0, 200),
          timestamp: Date.now(),
        })
      }
      throw err
    }
  }

  document.addEventListener('click', () => {
    const now = Date.now()
    clickTimes.push(now)
    clickTimes = clickTimes.filter(t => now - t < RAGE_CLICK_WINDOW)
    if (clickTimes.length >= RAGE_CLICK_THRESHOLD) {
      enqueue({
        message: `Rage click detected (${clickTimes.length} clicks in ${RAGE_CLICK_WINDOW}ms)`,
        url: location.href,
        timestamp: now,
      })
      clickTimes = []
    }
  })
}

export function setErrorMonitorOrg(newOrgId: string) {
  orgId = newOrgId
}
