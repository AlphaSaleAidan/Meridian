import { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { X, Send, Sparkles, ChevronRight, Square, Wrench, FileCode, Search, Database, Activity } from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import { getAuthHeaders } from '@/lib/supabase'
import { isUsAdmin } from '@/lib/us-admins'

const API_BASE = import.meta.env.VITE_API_URL || ''

const QUICK_ACTIONS = [
  { label: 'System status', prompt: 'Check the system status — processes, memory, disk.' },
  { label: 'Show pending patches', prompt: 'List all pending patches waiting for review.' },
  { label: 'Write a LinkedIn post', prompt: 'Write a LinkedIn post about how Meridian helps restaurant owners find hidden revenue.' },
  { label: 'Email subject lines', prompt: 'Give me 10 email subject lines for a cold outreach campaign targeting smoke shop owners in Canada.' },
  { label: 'Check active reps', prompt: 'Query the sales_reps table and show me who is active.' },
  { label: 'Review landing page', prompt: 'Read the landing page component and suggest improvements to the copy.' },
]

const TOOL_ICONS: Record<string, typeof Wrench> = {
  read_file: FileCode,
  search_code: Search,
  propose_patch: FileCode,
  system_status: Activity,
  list_patches: FileCode,
  run_query: Database,
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'tool'
  text: string
  streaming?: boolean
  toolName?: string
}

const HIDDEN_PATHS = ['/', '/landing', '/canada', '/canada/landing']

export default function GarryWidget() {
  const { pathname } = useLocation()
  const { rep } = useSalesAuth()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [threadId] = useState(() => crypto.randomUUID())
  const scrollRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  if (!isUsAdmin(rep?.email)) return null
  if (HIDDEN_PATHS.includes(pathname)) return null

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

      // Forward the authenticated session JWT — backend trusts that for admin ops.
      // Never embed a static admin key in the client bundle.
      const authHeaders = await getAuthHeaders()
      const headers: Record<string, string> = {
        ...authHeaders,
        'Content-Type': 'application/json',
      }

      const resp = await fetch(`${API_BASE}/api/garry/chat`, {
        method: 'POST',
        headers,
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
            } else if (parsed.tool_call) {
              const toolMsg: Message = {
                id: crypto.randomUUID(),
                role: 'tool',
                text: `Using ${parsed.tool_call.name}...`,
                toolName: parsed.tool_call.name,
              }
              setMessages(prev => {
                const idx = prev.findIndex(m => m.id === assistantId)
                if (idx === -1) return [...prev, toolMsg]
                const before = prev.slice(0, idx)
                const after = prev.slice(idx)
                return [...before, toolMsg, ...after]
              })
              continue
            } else if (parsed.tool_result) {
              continue
            }
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId ? { ...m, text: accumulated, streaming: true } : m
              )
            )
          } catch {
            // non-JSON line
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
        <div className="fixed bottom-6 right-3 sm:right-6 z-50 w-[calc(100vw-1.5rem)] max-w-[440px] max-h-[620px] bg-[#0f1512] border border-[#1a2420] rounded-xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a2420] bg-[#0a0f0d]">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center">
                <Sparkles size={15} className="text-[#00d4aa]" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">Garry</p>
                <p className="text-[10px] text-[#6b7a74]">Meridian AI Agent · admin only</p>
              </div>
            </div>
            <button aria-label="Close assistant" onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-[#1a2420] text-[#6b7a74] transition-colors">
              <X size={16} />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-[260px] max-h-[460px]">
            {messages.length === 0 && (
              <div className="py-4">
                <p className="text-sm font-semibold text-white mb-1">Hey, I'm Garry</p>
                <p className="text-xs text-[#6b7a74] mb-4">
                  I can read code, propose patches, query the database, and write marketing content.
                  Changes I propose go through a review queue before deployment.
                </p>
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
            {messages.map(msg => {
              if (msg.role === 'tool') {
                const Icon = TOOL_ICONS[msg.toolName || ''] || Wrench
                return (
                  <div key={msg.id} className="flex items-center gap-2 px-3 py-1.5 bg-[#0a0f0d]/50 border border-[#1a2420]/50 rounded-lg">
                    <Icon size={11} className="text-[#00d4aa] flex-shrink-0" />
                    <span className="text-[10px] text-[#4a5550] font-mono">{msg.text}</span>
                  </div>
                )
              }
              return (
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
              )
            })}
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
                placeholder="Ask Garry to read code, propose patches, query data..."
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
            <p className="text-[9px] text-[#4a5550] mt-1.5 text-center">Admin-only · Patches require approval before deployment</p>
          </div>
        </div>
      )}
    </>
  )
}
