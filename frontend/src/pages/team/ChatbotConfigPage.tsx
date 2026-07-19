// Customer chatbot config — owner customization (1d).
// Business name/tone, allowed topics, canned answers, escalation-to-human.
// LLM calls route through the shared LiteLLM gateway server-side.
import { useState, useEffect } from 'react'
import { Bot, Plus, Trash2, Loader2, Check } from 'lucide-react'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useApi } from '@/hooks/useApi'
import { teamApi } from '@/lib/team-api'
import { LoadingPage, ErrorState } from '@/components/LoadingState'

interface Canned { q: string; a: string }

export default function ChatbotConfigPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const state = useApi(
    () => (orgId && !isDemo ? teamApi.chatbotConfig(orgId) : Promise.resolve({ config: null })),
    [orgId, isDemo],
  )

  const [enabled, setEnabled] = useState(false)
  const [businessName, setBusinessName] = useState('')
  const [tone, setTone] = useState('friendly')
  const [greeting, setGreeting] = useState('')
  const [topics, setTopics] = useState('')
  const [canned, setCanned] = useState<Canned[]>([])
  const [escalate, setEscalate] = useState(false)
  const [contact, setContact] = useState('')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const c = state.data?.config
    if (!c) return
    setEnabled(!!c.enabled); setBusinessName(c.business_name || ''); setTone(c.tone || 'friendly')
    setGreeting(c.greeting || ''); setTopics((c.allowed_topics || []).join(', '))
    setCanned(c.canned_answers || []); setEscalate(!!c.escalation_to_human)
    setContact(c.escalation_contact || '')
  }, [state.data])

  if (isDemo) return <div className="p-6 text-[#A1A1A8]">The customer chatbot is available once your account is connected.</div>
  if (state.loading) return <LoadingPage />
  if (state.error) return <ErrorState message={state.error} onRetry={state.refetch} />

  const save = async () => {
    setBusy(true); setSaved(false)
    try {
      await teamApi.saveChatbotConfig(orgId, {
        enabled, business_name: businessName, tone, greeting,
        allowed_topics: topics.split(',').map(t => t.trim()).filter(Boolean),
        canned_answers: canned.filter(c => c.q.trim() && c.a.trim()),
        escalation_to_human: escalate, escalation_contact: contact,
      })
      setSaved(true)
    } catch { /* ignore */ } finally { setBusy(false) }
  }

  return (
    <div className="p-4 sm:p-6 space-y-4 max-w-2xl">
      <div className="flex items-center gap-2">
        <Bot size={18} className="text-[#17C5B0]" />
        <h1 className="text-xl font-semibold text-white">Customer Chatbot</h1>
      </div>
      <p className="text-sm text-[#A1A1A8]">
        A customizable assistant for your customers. Answers route through Meridian's AI with
        your rules below. Canned answers are used first — no AI cost for common questions.
      </p>

      <label className="flex items-center gap-2 text-sm text-white">
        <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
        Enable the chatbot on my site
      </label>

      <div className="grid sm:grid-cols-2 gap-3">
        <input value={businessName} onChange={e => setBusinessName(e.target.value)} placeholder="Business name"
          className="bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white" />
        <select value={tone} onChange={e => setTone(e.target.value)}
          className="bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white">
          {['friendly', 'professional', 'casual', 'formal'].map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <textarea value={greeting} onChange={e => setGreeting(e.target.value)} placeholder="Greeting (first message)"
        className="w-full bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white" rows={2} />

      <div>
        <label className="text-xs uppercase tracking-wide text-[#A1A1A8]">Allowed topics (comma-separated)</label>
        <input value={topics} onChange={e => setTopics(e.target.value)} placeholder="hours, menu, reservations"
          className="w-full mt-1 bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white" />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs uppercase tracking-wide text-[#A1A1A8]">Canned answers</label>
          <button onClick={() => setCanned(c => [...c, { q: '', a: '' }])}
            className="text-xs text-[#17C5B0] flex items-center gap-1"><Plus size={12} /> Add</button>
        </div>
        {canned.map((c, i) => (
          <div key={i} className="flex gap-2 items-start">
            <input value={c.q} placeholder="If they ask…"
              onChange={e => setCanned(list => list.map((x, j) => j === i ? { ...x, q: e.target.value } : x))}
              className="flex-1 bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white" />
            <input value={c.a} placeholder="Answer with…"
              onChange={e => setCanned(list => list.map((x, j) => j === i ? { ...x, a: e.target.value } : x))}
              className="flex-1 bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white" />
            <button onClick={() => setCanned(list => list.filter((_, j) => j !== i))} className="text-[#A1A1A8] hover:text-red-400 py-2">
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <label className="flex items-center gap-2 text-sm text-white">
        <input type="checkbox" checked={escalate} onChange={e => setEscalate(e.target.checked)} />
        Offer to hand off to a human
      </label>
      {escalate && (
        <input value={contact} onChange={e => setContact(e.target.value)} placeholder="Escalation contact (phone or email)"
          className="w-full bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white" />
      )}

      <div className="flex items-center gap-3">
        <button onClick={save} disabled={busy}
          className="flex items-center gap-2 bg-[#17C5B0] text-black font-medium px-4 py-2 rounded-lg text-sm disabled:opacity-50">
          {busy ? <Loader2 size={14} className="animate-spin" /> : null} Save
        </button>
        {saved && <span className="text-sm text-[#17C5B0] flex items-center gap-1"><Check size={14} /> Saved</span>}
      </div>
    </div>
  )
}
