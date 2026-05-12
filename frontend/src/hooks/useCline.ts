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

export function useCline(): UseClineReturn {
  const orgId = useOrgId()
  const [messages, setMessages] = useState<ClineMessage[]>([])
  const [isThinking, setIsThinking] = useState(false)
  const [hasAlert, setHasAlert] = useState(false)
  const [alertMessage, setAlertMessage] = useState('')
  const convIdRef = useRef<string>(msgId())

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
    } catch (e) {
      const errMsg: ClineMessage = {
        id: msgId(),
        role: 'agent',
        content: 'Sorry, I couldn\'t connect right now. Please try again.',
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, errMsg])
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
