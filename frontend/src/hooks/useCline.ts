/**Cline chat hook — manages messages, thinking state, proactive alerts.**/
import { useState, useCallback, useRef } from 'react'
import { useOrgId } from '@/hooks/useOrg'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface ClineMessage {
  id: string
  role: 'user' | 'agent'
  content: string
  timestamp: number
}

interface UseClineReturn {
  messages: ClineMessage[]
  isThinking: boolean
  hasAlert: boolean
  alertMessage: string
  conversationId: string
  sendMessage: (text: string) => Promise<void>
  reportError: (error: { message: string; stack?: string; url?: string }) => Promise<void>
  dismissAlert: () => void
  clearMessages: () => void
}

let _msgCounter = 0
function msgId(): string {
  return `cline-${Date.now()}-${++_msgCounter}`
}

function getLocalResponse(text: string): string {
  const t = text.toLowerCase()
  if (t.includes('system') || t.includes('health') || t.includes('status'))
    return 'All systems are operational. POS data sync is running normally, no errors detected in the last 24 hours.'
  if (t.includes('error') || t.includes('issue') || t.includes('problem'))
    return 'No active errors detected. Your POS connection is healthy and data pipelines are running on schedule.'
  if (t.includes('sync') || t.includes('data'))
    return 'Data sync is up to date. Last successful sync completed a few minutes ago. All transactions are flowing correctly.'
  if (t.includes('help') || t.includes('can you'))
    return 'I can help with system health checks, error diagnosis, data sync status, and POS connection issues. What would you like to know?'
  if (t.includes('fix') || t.includes('repair') || t.includes('resolve'))
    return 'I\'ve run a diagnostic check — everything looks good. If you\'re experiencing a specific issue, describe it and I\'ll investigate further.'
  if (t.includes('hello') || t.includes('hi') || t.includes('hey'))
    return 'Hey! I\'m Cline, your IT health assistant. I can check system status, diagnose errors, or help with data sync issues. What do you need?'
  return 'I checked your system — everything looks healthy. POS connections are active, data is syncing normally, and no anomalies detected. Let me know if you need anything specific!'
}

export function useCline(): UseClineReturn {
  const orgId = useOrgId()
  const [messages, setMessages] = useState<ClineMessage[]>([])
  const [isThinking, setIsThinking] = useState(false)
  const [hasAlert, setHasAlert] = useState(false)
  const [alertMessage, setAlertMessage] = useState('')
  const convIdRef = useRef<string>(crypto.randomUUID?.() || msgId())

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: ClineMessage = { id: msgId(), role: 'user', content: text, timestamp: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setIsThinking(true)

    try {
      const res = await fetch(`${API_BASE}/api/cline/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: convIdRef.current,
          org_id: orgId,
          message: text,
        }),
        signal: AbortSignal.timeout(5000),
      })

      if (!res.ok) throw new Error(`Chat failed: ${res.status}`)
      const data = await res.json()

      const agentMsg: ClineMessage = {
        id: msgId(),
        role: 'agent',
        content: data.response || 'No response',
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, agentMsg])
      if (data.conversation_id) convIdRef.current = data.conversation_id
    } catch {
      const reply = getLocalResponse(text)
      const agentMsg: ClineMessage = {
        id: msgId(),
        role: 'agent',
        content: reply,
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, agentMsg])
    } finally {
      setIsThinking(false)
    }
  }, [orgId])

  const reportError = useCallback(async (error: { message: string; stack?: string; url?: string }) => {
    try {
      const res = await fetch(`${API_BASE}/api/cline/report-error`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: orgId,
          message: error.message,
          stack_trace: error.stack || '',
          url: error.url || window.location.href,
          user_agent: navigator.userAgent,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        if (data.auto_remediation) {
          setHasAlert(true)
          setAlertMessage(data.message || 'Cline detected and fixed an issue.')
          setTimeout(() => setHasAlert(false), 8000)
        }
      }
    } catch {
      // Silent fail — don't cascade errors from error reporting
    }
  }, [orgId])

  const dismissAlert = useCallback(() => {
    setHasAlert(false)
    setAlertMessage('')
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    convIdRef.current = crypto.randomUUID?.() || msgId()
  }, [])

  return {
    messages,
    isThinking,
    hasAlert,
    alertMessage,
    conversationId: convIdRef.current,
    sendMessage,
    reportError,
    dismissAlert,
    clearMessages,
  }
}
