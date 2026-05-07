import { useState, useRef, useEffect } from 'react'
import { MessageCircle, X, Send, Zap, ChevronRight } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
}

const QUICK_ACTIONS = [
  { label: 'How do I add a lead?', prompt: 'How do I add a new lead in the Canada portal?' },
  { label: 'Explain commission rates', prompt: 'How do commission rates work for Canadian sales reps?' },
  { label: 'POS connection help', prompt: 'How do I connect a Moneris POS system for a client?' },
  { label: 'Training overview', prompt: 'What training modules should I complete first?' },
]

const CANNED_RESPONSES: Record<string, string> = {
  'lead': 'To add a new lead, go to the **Leads** page and click **"New Lead"**. Fill in the business name, contact info, vertical, city, province, and monthly price in CA$. The lead will be saved and appear in your pipeline.',
  'commission': 'Your commission rate is set by your manager (typically 35%). You earn commission on each active client\'s monthly revenue. Commissions are tracked as pending → earned → paid. View your earnings on the **Dashboard**.',
  'pos': 'To connect a POS system:\n1. Go to the lead\'s detail page\n2. Scroll to **Step 4: Connect POS**\n3. Select the POS provider (Moneris, Square, Clover, etc.)\n4. Follow the integration guide in **Training → POS Connection Guides**',
  'training': 'Start with **New Rep Onboarding** (45 min), then move to **Perfecting Your Pitch** (30 min). The **Camera Intelligence Setup** and **POS Connection Guides** are also recommended early on. Track your progress on the Training page.',
}

function getResponse(input: string): string {
  const lower = input.toLowerCase()
  if (lower.includes('lead') || lower.includes('prospect')) return CANNED_RESPONSES['lead']
  if (lower.includes('commission') || lower.includes('payout') || lower.includes('rate')) return CANNED_RESPONSES['commission']
  if (lower.includes('pos') || lower.includes('moneris') || lower.includes('connect')) return CANNED_RESPONSES['pos']
  if (lower.includes('training') || lower.includes('module') || lower.includes('learn')) return CANNED_RESPONSES['training']
  return 'I can help with leads, commissions, POS connections, and training. Try asking about one of those topics, or use the quick actions above.'
}

export default function ClineAIChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  function handleSend(text?: string) {
    const msg = text || input.trim()
    if (!msg) return

    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', text: msg }
    setMessages(prev => [...prev, userMsg])
    setInput('')

    setTimeout(() => {
      const response: Message = { id: crypto.randomUUID(), role: 'assistant', text: getResponse(msg) }
      setMessages(prev => [...prev, response])
    }, 400 + Math.random() * 400)
  }

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-[#00d4aa] text-[#0a0f0d] shadow-lg shadow-[#00d4aa]/20 flex items-center justify-center hover:bg-[#00d4aa]/90 transition-all hover:scale-105"
        >
          <MessageCircle size={22} />
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-[360px] max-h-[520px] bg-[#0f1512] border border-[#1a2420] rounded-xl shadow-2xl shadow-black/40 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a2420]">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-[#00d4aa]/15 flex items-center justify-center">
                <Zap size={14} className="text-[#00d4aa]" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">Cline AI</p>
                <p className="text-[10px] text-[#6b7a74]">Sales assistant</p>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-[#1a2420] text-[#6b7a74] transition-colors">
              <X size={16} />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-[200px] max-h-[340px]">
            {messages.length === 0 && (
              <div className="text-center py-6">
                <Zap size={24} className="text-[#00d4aa] mx-auto mb-2" />
                <p className="text-sm font-medium text-white">How can I help?</p>
                <p className="text-xs text-[#6b7a74] mt-1">Ask a question or use a quick action.</p>
                <div className="mt-4 space-y-2">
                  {QUICK_ACTIONS.map(action => (
                    <button
                      key={action.label}
                      onClick={() => handleSend(action.prompt)}
                      className="w-full flex items-center justify-between px-3 py-2 bg-[#0a0f0d] rounded-lg text-left hover:bg-[#1a2420]/50 transition-colors group"
                    >
                      <span className="text-xs text-[#6b7a74] group-hover:text-white transition-colors">{action.label}</span>
                      <ChevronRight size={12} className="text-[#4a5550]" />
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-lg text-xs leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-[#00d4aa] text-[#0a0f0d]'
                    : 'bg-[#0a0f0d] text-[#6b7a74] border border-[#1a2420]'
                }`}>
                  {msg.text.split('\n').map((line, i) => (
                    <p key={i} className={i > 0 ? 'mt-1' : ''}>{line}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="px-3 py-3 border-t border-[#1a2420]">
            <form
              onSubmit={e => { e.preventDefault(); handleSend() }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                className="flex-1 px-3 py-2 bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-xs text-white placeholder-[#4a5550] focus:outline-none focus:border-[#00d4aa]/50"
                placeholder="Ask Cline anything..."
              />
              <button
                type="submit"
                disabled={!input.trim()}
                className="w-8 h-8 rounded-lg bg-[#00d4aa] text-[#0a0f0d] flex items-center justify-center disabled:opacity-30 hover:bg-[#00d4aa]/90 transition-all"
              >
                <Send size={14} />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
