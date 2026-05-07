/**Floating Cline chat widget — bottom-right, Meridian dark + teal accent.

Mobile: expands to full sheet. Desktop: side panel.
Pulses when proactive alert is active. Auto-attaches page URL + org_id.
**/
import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { clsx } from 'clsx'
import { MessageCircle, X, Send, Bot, Loader2 } from 'lucide-react'
import { useCline } from '@/hooks/useCline'
import ClineProactiveAlert from './ClineProactiveAlert'

export default function ClineChatWidget() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { messages, isThinking, hasAlert, alertMessage, sendMessage, dismissAlert } = useCline()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open])

  async function handleSend() {
    const text = input.trim()
    if (!text || isThinking) return
    setInput('')
    await sendMessage(text)
  }

  const chatPanel = (
    <>
      {/* Backdrop (mobile) */}
      <div
        className={clsx(
          'fixed inset-0 z-50 bg-black/60 transition-opacity duration-300 lg:hidden',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={() => setOpen(false)}
      />

      {/* Panel */}
      <div
        className={clsx(
          'fixed z-50 flex flex-col bg-[#0A0A0B] border border-[#1F1F23] shadow-2xl transition-all duration-300 ease-out',
          // Mobile: bottom sheet
          'inset-x-0 bottom-0 rounded-t-2xl max-h-[80vh]',
          // Desktop: side panel
          'lg:inset-auto lg:bottom-20 lg:right-6 lg:w-[380px] lg:h-[520px] lg:rounded-2xl',
          open ? 'translate-y-0 lg:translate-y-0 lg:opacity-100 lg:scale-100'
               : 'translate-y-full lg:translate-y-4 lg:opacity-0 lg:scale-95 lg:pointer-events-none',
        )}
        role="dialog"
        aria-label="Cline IT assistant"
      >
        {/* Drag handle (mobile) */}
        <div className="flex justify-center pt-2 pb-0 lg:hidden">
          <div className="h-1 w-10 rounded-full bg-[#A1A1A8]/30" />
        </div>

        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[#1F1F23] flex-shrink-0">
          <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
            <Bot size={18} className="text-[#17C5B0]" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold text-[#F5F5F7]">Cline</p>
            <p className="text-[10px] text-[#A1A1A8]/60">IT Health Assistant</p>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="p-2 rounded-lg text-[#A1A1A8] hover:text-white hover:bg-[#1F1F23] transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {messages.length === 0 && (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-2xl bg-[#17C5B0]/10 flex items-center justify-center mx-auto mb-3">
                <Bot size={24} className="text-[#17C5B0]" />
              </div>
              <p className="text-sm font-medium text-[#F5F5F7]">Hi! I'm Cline</p>
              <p className="text-xs text-[#A1A1A8] mt-1">
                Ask me about system health, errors, or data sync status.
              </p>
              <div className="flex flex-wrap justify-center gap-2 mt-4">
                {['How is my system?', 'Any errors?', 'Fix sync issues'].map(q => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="px-3 py-1.5 rounded-full border border-[#1F1F23] text-[11px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#17C5B0]/30 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map(msg => (
            <div
              key={msg.id}
              className={clsx(
                'max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm',
                msg.role === 'user'
                  ? 'ml-auto bg-[#1A8FD6] text-white rounded-br-md'
                  : 'bg-[#1F1F23] text-[#F5F5F7] rounded-bl-md',
              )}
            >
              {msg.content}
            </div>
          ))}

          {isThinking && (
            <div className="flex items-center gap-2 text-[#A1A1A8] text-sm">
              <Loader2 size={14} className="animate-spin text-[#17C5B0]" />
              <span>Cline is thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-[#1F1F23] flex-shrink-0">
          <form
            onSubmit={e => { e.preventDefault(); handleSend() }}
            className="flex items-center gap-2"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask Cline anything..."
              className="flex-1 bg-[#1F1F23] border border-[#1F1F23] rounded-lg px-3 py-2.5 text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#17C5B0]/40 transition-colors min-h-[44px]"
              disabled={isThinking}
            />
            <button
              type="submit"
              disabled={!input.trim() || isThinking}
              className="p-2.5 rounded-lg bg-[#17C5B0] text-white hover:bg-[#17C5B0]/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="Send"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>
    </>
  )

  return (
    <>
      {/* Proactive alert toast */}
      <ClineProactiveAlert
        message={alertMessage}
        visible={hasAlert && !open}
        onDismiss={dismissAlert}
      />

      {/* Floating trigger button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className={clsx(
            'fixed z-40 bottom-20 sm:bottom-6 right-4 sm:right-6',
            'w-10 h-10 rounded-full shadow-lg flex items-center justify-center',
            'bg-[#17C5B0] text-white hover:bg-[#17C5B0]/90 transition-all duration-200',
            'hover:scale-105 active:scale-95',
            hasAlert && 'animate-pulse ring-2 ring-[#17C5B0]/50 ring-offset-2 ring-offset-[#0A0A0B]',
          )}
          aria-label="Open Cline assistant"
        >
          <MessageCircle size={16} />
        </button>
      )}

      {/* Chat panel — portal to body for z-index isolation */}
      {createPortal(chatPanel, document.body)}
    </>
  )
}
