/**
 * Layout primitive that owns the query-status branches every portal page
 * used to hand-roll: loading skeleton, connection-error banner, empty state.
 *
 * Replaces audit findings #2, #6, #7, #10, #11 — each page is now just a
 * happy-path component, with the wrapper deciding what to render based on
 * the query result.
 *
 * The error-banner JSX was lifted verbatim from the canonical version that
 * lived inside CanadaPortalDashboardPage.tsx (the only page that had one
 * pre-Phase-2). Every page now uses the same banner.
 */

import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'

// ── PortalPage ─────────────────────────────────────────────────────────────

interface PortalPageProps {
  isLoading: boolean
  error: unknown
  /**
   * Caller's empty predicate (e.g. `deals.length === 0`). When the page has
   * nothing to render, isEmpty=true upgrades the skeleton to a true
   * first-paint state (replacing children) and lets the error banner replace
   * content rather than appearing above an empty page.
   */
  isEmpty?: boolean
  /** Rendered when status === success && isEmpty === true. */
  emptyState?: ReactNode
  /** Override the default centered spinner. */
  loadingSkeleton?: ReactNode
  /** Banner title; defaults to "Could not load your data". */
  errorTitle?: string
  /** Override the default `window.location.reload()` retry. */
  onRetry?: () => void
  children: ReactNode
}

function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  if (typeof err === 'string') return err
  return 'Check your connection and refresh.'
}

export function PortalPage({
  isLoading,
  error,
  isEmpty = false,
  emptyState,
  loadingSkeleton,
  errorTitle,
  onRetry,
  children,
}: PortalPageProps) {
  // 1. First-paint loading (nothing cached, no error yet). Skeleton replaces
  //    the page so an empty state can't flash before the data lands —
  //    closes the race that was audit finding #6.
  if (isLoading && isEmpty && !error) {
    return <>{loadingSkeleton ?? <PortalLoadingSkeleton />}</>
  }

  // 2. Error with no cached data — banner replaces page so a misleading
  //    empty state can't render alongside the failure.
  if (error && isEmpty) {
    return <PortalErrorBanner title={errorTitle} message={errorMessage(error)} onRetry={onRetry} />
  }

  // 3. Error with cached data — banner above stale content (matches the
  //    original Dashboard pattern; cached data stays readable while the
  //    user retries).
  if (error) {
    return (
      <>
        <PortalErrorBanner title={errorTitle} message={errorMessage(error)} onRetry={onRetry} />
        {children}
      </>
    )
  }

  // 4. Success + empty — explicit empty state.
  if (isEmpty && emptyState) {
    return <>{emptyState}</>
  }

  // 5. Success + data.
  return <>{children}</>
}

// ── Shared primitives (exported so pages can compose, e.g. a per-section
//    banner inside a page that doesn't want full-page status handling) ────

export function PortalLoadingSkeleton({ char = 'M' }: { char?: string }) {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="w-8 h-8 rounded-lg bg-pm-accent/15 border border-pm-accent/30 flex items-center justify-center animate-pulse">
        <span className="text-pm-accent font-bold text-sm">{char}</span>
      </div>
    </div>
  )
}

export function PortalErrorBanner({
  title = 'Could not load your data',
  message,
  onRetry,
}: {
  title?: string
  message: string
  onRetry?: () => void
}) {
  const handleRetry = onRetry ?? (() => window.location.reload())
  return (
    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3">
      <AlertTriangle size={18} className="text-red-400 flex-shrink-0" />
      <div className="flex-1">
        <p className="text-sm font-medium text-red-400">{title}</p>
        <p className="text-xs text-red-400/70 mt-0.5">{message}</p>
      </div>
      <button
        onClick={handleRetry}
        className="px-3 py-1.5 text-xs font-medium text-white border border-red-500/30 rounded-lg hover:bg-red-500/10 transition-colors"
      >
        Retry
      </button>
    </div>
  )
}

// ── Subtree error boundary ────────────────────────────────────────────────
// Localized to /canada/portal/* so a thrown render keeps the sidebar
// usable. Sits inside CanadaSalesLayout, between the layout chrome and the
// page Outlet. App-level <ErrorBoundary> at App.tsx still catches anything
// this boundary can't recover from.

interface BoundaryState {
  hasError: boolean
  error: Error | null
}

export class CanadaPortalErrorBoundary extends Component<{ children: ReactNode }, BoundaryState> {
  state: BoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): BoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[CanadaPortalErrorBoundary]', error, info?.componentStack)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="max-w-md mx-auto py-12 px-4 space-y-3">
        <PortalErrorBanner
          title="Something went wrong on this page"
          message={
            this.state.error?.message ??
            'An unexpected render error occurred. You can keep using other pages, or try this one again.'
          }
        />
        <div className="flex gap-2">
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="flex-1 px-3 py-2 text-xs font-medium text-pm-accent border border-pm-accent/30 rounded-lg hover:bg-pm-accent/10 transition-colors"
          >
            Try again
          </button>
          <Link
            to="/canada/portal/dashboard"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="flex-1 px-3 py-2 text-xs font-medium text-white border border-pm-canada-border rounded-lg hover:border-pm-canada-text-muted hover:text-pm-accent transition-colors text-center"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }
}
