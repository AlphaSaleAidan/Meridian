// Internal team chat — org-scoped channels + messages (1d, employee/basic view).
import { useState, useEffect, useRef } from 'react'
import { Send, Hash, Loader2 } from 'lucide-react'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useApi } from '@/hooks/useApi'
import { teamApi, type Channel, type TeamMessage } from '@/lib/team-api'
import { LoadingPage, ErrorState } from '@/components/LoadingState'

export default function TeamChatPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const [channelId, setChannelId] = useState<string>('')
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  const channelsState = useApi(
    () => (orgId && !isDemo ? teamApi.channels(orgId) : Promise.resolve({ channels: [] as Channel[] })),
    [orgId, isDemo],
  )
  const channels = channelsState.data?.channels || []
  const activeChannel = channelId || channels[0]?.id || ''

  const msgState = useApi(
    () => (activeChannel && !isDemo ? teamApi.messages(orgId, activeChannel) : Promise.resolve({ messages: [] as TeamMessage[] })),
    [orgId, activeChannel, isDemo, reloadKey],
  )

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [msgState.data])

  if (isDemo) return <div className="p-6 text-[#A1A1A8]">Team chat is available once your account is connected.</div>
  if (channelsState.loading) return <LoadingPage />
  if (channelsState.error) return <ErrorState message={channelsState.error} onRetry={channelsState.refetch} />

  const send = async () => {
    const text = draft.trim()
    if (!text || !activeChannel) return
    setSending(true)
    try {
      await teamApi.postMessage(orgId, activeChannel, text)
      setDraft('')
      setReloadKey(k => k + 1)
    } catch { /* surfaced by next fetch */ } finally { setSending(false) }
  }

  const messages = msgState.data?.messages || []

  return (
    <div className="p-4 sm:p-6 max-w-3xl">
      <h1 className="text-xl font-semibold text-white mb-3">Team Chat</h1>
      <div className="flex gap-1.5 mb-3 flex-wrap">
        {channels.map(c => (
          <button key={c.id} onClick={() => setChannelId(c.id)}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-sm ${
              c.id === activeChannel ? 'bg-[#17C5B0] text-black font-medium' : 'bg-[#1A1A1E] text-[#A1A1A8]'}`}>
            <Hash size={12} />{c.name}
          </button>
        ))}
      </div>

      <div ref={scrollRef} className="card h-[52vh] overflow-y-auto p-4 space-y-3">
        {msgState.loading && <div className="text-sm text-[#A1A1A8]">Loading…</div>}
        {!msgState.loading && messages.length === 0 && (
          <div className="text-sm text-[#A1A1A8]">No messages yet. Say hello 👋</div>
        )}
        {messages.map(m => (
          <div key={m.id} className="text-sm">
            <span className="text-[#17C5B0] font-medium">{m.author_name}</span>
            <span className="text-[#A1A1A8]/50 text-xs ml-2">
              {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            <div className="text-[#E4E4E7] whitespace-pre-wrap">{m.body}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-2 mt-3">
        <input value={draft} onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder="Message your team…"
          className="flex-1 bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white" />
        <button onClick={send} disabled={sending || !draft.trim()}
          className="bg-[#17C5B0] text-black px-4 rounded-lg disabled:opacity-50 flex items-center">
          {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </div>
    </div>
  )
}
