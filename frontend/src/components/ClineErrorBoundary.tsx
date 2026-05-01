/**Cline error boundary — catches React crashes, reports to Cline API.**/
import { Component, type ReactNode } from 'react'
import { AlertTriangle, MessageCircle, RefreshCw } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface Props {
  children: ReactNode
  orgId?: string
  onOpenChat?: () => void
}

interface State {
  hasError: boolean
  error: Error | null
  reported: boolean
}

export default class ClineErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null, reported: false }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    this.reportToCline(error, info.componentStack || '')
  }

  async reportToCline(error: Error, componentStack: string) {
    if (this.state.reported) return
    this.setState({ reported: true })

    try {
      await fetch(`${API_BASE}/api/cline/report-error`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: this.props.orgId || '',
          message: `React crash: ${error.message}`,
          stack_trace: `${error.stack || ''}\n\nComponent stack:${componentStack}`.slice(0, 2000),
          url: window.location.href,
          user_agent: navigator.userAgent,
        }),
      })
    } catch {
      // Silent — don't cascade
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, reported: false })
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="flex items-center justify-center min-h-[60vh] px-4">
        <div className="max-w-md w-full text-center">
          <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle size={24} className="text-amber-400" />
          </div>
          <h2 className="text-lg font-semibold text-[#F5F5F7] mb-2">
            Something broke, but Cline is already on it
          </h2>
          <p className="text-sm text-[#A1A1A8] mb-6">
            This error has been automatically reported. Our self-healing agent is analyzing the issue.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#1A8FD6] text-white text-sm font-medium hover:bg-[#1A8FD6]/90 transition-colors min-h-[44px]"
            >
              <RefreshCw size={16} />
              Try again
            </button>
            {this.props.onOpenChat && (
              <button
                onClick={this.props.onOpenChat}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-[#1F1F23] text-[#A1A1A8] text-sm font-medium hover:text-[#F5F5F7] hover:bg-[#1F1F23]/60 transition-colors min-h-[44px]"
              >
                <MessageCircle size={16} />
                Chat with Cline
              </button>
            )}
          </div>
          {this.state.error && (
            <details className="mt-6 text-left">
              <summary className="text-[10px] text-[#A1A1A8]/40 cursor-pointer hover:text-[#A1A1A8]/60">
                Technical details
              </summary>
              <pre className="mt-2 p-3 rounded-lg bg-[#0A0A0B] border border-[#1F1F23] text-[10px] text-[#A1A1A8]/50 font-mono overflow-x-auto max-h-32">
                {this.state.error.message}
              </pre>
            </details>
          )}
        </div>
      </div>
    )
  }
}
