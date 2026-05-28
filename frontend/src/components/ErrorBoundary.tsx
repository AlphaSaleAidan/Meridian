import { Component, lazy, type ReactNode, type ComponentType } from 'react'
import { MeridianEmblem, MeridianWordmark } from './MeridianLogo'

function isChunkLoadError(error: Error): boolean {
  return (
    error.message.includes('Failed to fetch dynamically imported module') ||
    error.message.includes('Loading chunk') ||
    error.name === 'ChunkLoadError'
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function lazyRetry<T extends ComponentType<any>>(
  factory: () => Promise<{ default: T }>,
): React.LazyExoticComponent<T> {
  return lazy(() =>
    factory().catch(() => {
      sessionStorage.setItem('meridian_chunk_reload', String(Date.now()))
      window.location.reload()
      return new Promise(() => {})
    }),
  )
}

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  info: string
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null, info: '' }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, info: '' }
  }

  componentDidCatch(error: Error, errorInfo: { componentStack?: string }) {
    this.setState({ info: errorInfo?.componentStack || '' })
    console.error('[ErrorBoundary]', error, errorInfo?.componentStack)

    if (isChunkLoadError(error)) {
      const key = 'meridian_chunk_reload'
      const last = sessionStorage.getItem(key)
      if (!last || Date.now() - Number(last) > 10_000) {
        sessionStorage.setItem(key, String(Date.now()))
        window.location.reload()
      }
    }
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-sm text-center space-y-4">
          <div className="flex items-center justify-center gap-2.5 mb-6">
            <MeridianEmblem size={32} />
            <MeridianWordmark className="text-lg" />
          </div>
          <div className="card p-6 border border-red-500/20 space-y-3">
            <h2 className="text-sm font-semibold text-[#F5F5F7]">Something went wrong</h2>
            <p className="text-xs text-[#A1A1A8]">
              An unexpected error occurred. Try refreshing the page.
            </p>
            {this.state.error && (
              <p className="text-[10px] font-mono text-red-400/60 break-all">
                {this.state.error.message}
              </p>
            )}
            {this.state.info && (
              <details className="mt-2">
                <summary className="text-[9px] text-[#A1A1A8]/40 cursor-pointer">Stack trace</summary>
                <pre className="text-[8px] font-mono text-[#A1A1A8]/30 mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-all">
                  {this.state.info}
                </pre>
              </details>
            )}
            {this.state.error?.stack && (
              <details className="mt-1">
                <summary className="text-[9px] text-[#A1A1A8]/40 cursor-pointer">Error stack</summary>
                <pre className="text-[8px] font-mono text-[#A1A1A8]/30 mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-all">
                  {this.state.error.stack}
                </pre>
              </details>
            )}
            <button
              onClick={() => window.location.reload()}
              className="w-full py-2 bg-[#1A8FD6] text-white text-xs font-semibold rounded-lg hover:bg-[#1A8FD6]/90 transition-all"
            >
              Reload Page
            </button>
          </div>
        </div>
      </div>
    )
  }
}
