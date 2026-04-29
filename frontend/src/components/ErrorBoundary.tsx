import { Component, type ReactNode } from 'react'
import { MeridianEmblem, MeridianWordmark } from './MeridianLogo'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
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
