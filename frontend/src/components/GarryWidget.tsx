import { useState, useRef, useEffect, useCallback } from 'react'
import { X, Send, Sparkles, ChevronRight, Square } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || ''

const QUICK_ACTIONS = [
  { label: 'Write a LinkedIn post', prompt: 'Write a LinkedIn post about how Meridian helps restaurant owners find hidden revenue. Make it punchy and include a hook stat.' },
  { label: 'Email subject lines', prompt: 'Give me 10 email subject lines for a cold outreach campaign targeting smoke shop owners in Canada.' },
  { label: 'Instagram caption', prompt: 'Write 3 Instagram captions for Meridian. Short, bold, with a CTA. Target: small business owners.' },
  { label: 'Google Ad copy', prompt: 'Write 3 Google responsive search ads for Meridian targeting "POS analytics for restaurants". Include headlines and descriptions.' },
  { label: 'Case study template', prompt: 'Create a case study template for a Meridian customer success story. Restaurant vertical, CA$ amounts.' },
  { label: 'Video script (30s)', prompt: 'Write a 30-second video ad script for Meridian. Hook, problem, solution, CTA. Energetic tone.' },
]

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  streaming?: boolean
}

export default function GarryWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [threadId] = useState(() => crypto.randomUUID())
  const scrollRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages])

  const send = useCallback(async (text?: string) => {
    const msg = (text ?? input).trim()
    if (!msg || loading) return
    setInput('')
    setLoading(true)

    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', text: msg }
    const assistantId = crypto.randomUUID()
    setMessages(prev => [
      ...prev,
      userMsg,
      { id: assistantId, role: 'assistant', text: '', streaming: true },
    ])

    try {
      abortRef.current = new AbortController()

      const resp = await fetch(`${API_BASE}/api/garry/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, thread_id: threadId }),
        signal: abortRef.current.signal,
      })

      if (!resp.ok || !resp.body) throw new Error(`Stream failed: ${resp.status}`)

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const raw = line.slice(5).trim()
          if (raw === '[DONE]') break
          try {
            const parsed = JSON.parse(raw)
            if (parsed.error) {
              accumulated = parsed.error
            } else if (parsed.content) {
              accumulated += parsed.content
            }
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId ? { ...m, text: accumulated, streaming: true } : m
              )
            )
          } catch {
            // non-JSON line, skip
          }
        }
      }

      setMessages(prev =>
        prev.map(m => (m.id === assistantId ? { ...m, streaming: false } : m))
      )
    } catch (err: unknown) {
      const errMsg = err instanceof Error && err.name === 'AbortError'
        ? '_(stopped)_'
        : `Sorry, I hit an error. Try again. (${err instanceof Error ? err.message : String(err)})`
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId ? { ...m, text: errMsg, streaming: false } : m
        )
      )
    } finally {
      setLoading(false)
    }
  }, [input, loading, threadId])

  function stop() {
    abortRef.current?.abort()
    setLoading(false)
  }

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 rounded-full bg-[#00d4aa] text-[#0a0f0d] shadow-lg shadow-[#00d4aa]/30 flex items-center justify-center hover:bg-[#00d4aa]/90 transition-all hover:scale-105 gap-1.5 px-4"
          style={{ width: 'auto', height: '44px' }}
        >
          <Sparkles size={16} />
          <span className="text-[13px] font-bold">Garry</span>
        </button>
      )}

      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-[400px] max-h-[580px] bg-[#0f1512] border border-[#1a2420] rounded-xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a2420] bg-[#0a0f0d]">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center">
                <Sparkles size={15} className="text-[#00d4aa]" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">Garry</p>
                <p className="text-[10px] text-[#6b7a74]">Meridian Marketing AI · powered by Qwen</p>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-[#1a2420] text-[#6b7a74] transition-colors">
              <X size={16} />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-[220px] max-h-[420px]">
            {messages.length === 0 && (
              <div className="py-4">
                <p className="text-sm font-semibold text-white mb-1">Hey, I'm Garry 👋</p>
                <p className="text-xs text-[#6b7a74] mb-4">Your Meridian marketing co-pilot. Give me a brief and I'll write the copy.</p>
                <div className="space-y-1.5">
                  {QUICK_ACTIONS.map(a => (
                    <button
                      key={a.label}
                      onClick={() => send(a.prompt)}
                      className="w-full flex items-center justify-between px-3 py-2 bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-left hover:border-[#00d4aa]/30 hover:bg-[#1a2420]/50 transition-all group"
                    >
                      <span className="text-[11px] text-[#6b7a74] group-hover:text-white transition-colors">{a.label}</span>
                      <ChevronRight size={11} className="text-[#4a5550] flex-shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[90%] px-3 py-2.5 rounded-xl text-xs leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-[#00d4aa] text-[#0a0f0d] font-medium'
                    : 'bg-[#0a0f0d] text-[#c8d5d0] border border-[#1a2420]'
                }`}>
                  {msg.text}
                  {msg.streaming && <span className="inline-block w-1.5 h-3 bg-[#00d4aa] ml-0.5 animate-pulse rounded-sm" />}
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="px-3 py-3 border-t border-[#1a2420]">
            <form onSubmit={e => { e.preventDefault(); send() }} className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
                rows={2}
                className="flex-1 px-3 py-2 bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-xs text-white placeholder-[#4a5550] focus:outline-none focus:border-[#00d4aa]/50 resize-none"
                placeholder="Brief Garry on what to write..."
              />
              {loading ? (
                <button
                  type="button"
                  onClick={stop}
                  className="w-8 h-8 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400 flex items-center justify-center hover:bg-red-500/30 transition-all flex-shrink-0"
                >
                  <Square size={12} />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="w-8 h-8 rounded-lg bg-[#00d4aa] text-[#0a0f0d] flex items-center justify-center disabled:opacity-30 hover:bg-[#00d4aa]/90 transition-all flex-shrink-0"
                >
                  <Send size={13} />
                </button>
              )}
            </form>
            <p className="text-[9px] text-[#4a5550] mt-1.5 text-center">Shift+Enter for new line · Enter to send</p>
          </div>
        </div>
      )}
    </>
  )
}
