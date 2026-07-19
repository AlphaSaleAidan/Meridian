// Team Management — owner control center for employee accounts + RBAC (1c/1e).
// Owner creates accounts, sets role, and (for managers) walks a visibility +
// permission checklist. The invite email is sent from within the site via the
// backend's existing send_invite path.
import { useState } from 'react'
import { UserPlus, ShieldCheck, Eye, Loader2, Mail, Check } from 'lucide-react'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useApi } from '@/hooks/useApi'
import { teamApi, type Member, type Role, type Permissions } from '@/lib/team-api'
import { LoadingPage, ErrorState } from '@/components/LoadingState'

const LABELS: Record<string, string> = {
  financials: 'Financials (revenue, margins, taxes)',
  phone_agent_analytics: 'Phone-agent analytics',
  staff_pay: 'Staff pay',
  schedule: 'Team schedule',
  camera: 'Camera',
  chatbot: 'Customer chatbot',
  edit_schedule: 'Edit schedule',
  publish_schedule: 'Publish schedule',
  edit_punches: 'Edit time punches',
  change_phone_agent: 'Change phone-agent settings',
  manage_chatbot: 'Manage customer chatbot',
  invite_employees: 'Invite employees',
  manage_team: 'Manage team (create/edit members)',
  post_chat: 'Post in internal chat',
}

function emptyPerms(schema: { visibility: string[]; actions: string[] }): Permissions {
  return {
    visibility: Object.fromEntries(schema.visibility.map(k => [k, false])),
    actions: Object.fromEntries(schema.actions.map(k => [k, false])),
  }
}

function Toggle({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2 text-left w-full py-1.5 group"
    >
      <span className={`w-9 h-5 rounded-full relative transition-colors ${on ? 'bg-[#17C5B0]' : 'bg-[#2A2A30]'}`}>
        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${on ? 'left-4' : 'left-0.5'}`} />
      </span>
      <span className="text-sm text-[#E4E4E7] group-hover:text-white">{label}</span>
    </button>
  )
}

function CreateMemberForm({ orgId, schema, onCreated }: {
  orgId: string
  schema: { roles: Role[]; visibility: string[]; actions: string[] }
  onCreated: () => void
}) {
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<Role>('employee')
  const [perms, setPerms] = useState<Permissions>(emptyPerms(schema))
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const toggle = (cat: 'visibility' | 'actions', key: string) =>
    setPerms(p => ({ ...p, [cat]: { ...p[cat], [key]: !p[cat][key] } }))

  const submit = async () => {
    setErr(null); setMsg(null)
    if (!email.trim()) { setErr('Email is required'); return }
    setBusy(true)
    try {
      const res = await teamApi.createMember(orgId, {
        email: email.trim(), full_name: fullName.trim(), role,
        permissions: perms, send_invite: true,
      })
      setMsg(res.invite_sent ? `Invite emailed to ${email}` : `Account created for ${email}`)
      setEmail(''); setFullName(''); setRole('employee'); setPerms(emptyPerms(schema))
      onCreated()
    } catch (e: any) {
      setErr(e?.message?.replace(/^API \d+: /, '') || 'Could not create account')
    } finally { setBusy(false) }
  }

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center gap-2 text-white font-semibold">
        <UserPlus size={16} className="text-[#17C5B0]" /> Add a team member
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email"
          className="bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white" />
        <input value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Full name"
          className="bg-[#111114] border border-[#26262C] rounded-lg px-3 py-2 text-sm text-white" />
      </div>
      <div className="flex gap-2">
        {(['employee', 'manager'] as Role[]).map(r => (
          <button key={r} onClick={() => setRole(r)}
            className={`px-3 py-1.5 rounded-lg text-sm capitalize ${role === r ? 'bg-[#17C5B0] text-black font-medium' : 'bg-[#1A1A1E] text-[#A1A1A8]'}`}>
            {r}
          </button>
        ))}
      </div>

      {role === 'manager' && (
        <div className="grid sm:grid-cols-2 gap-4 pt-1">
          <div>
            <div className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-[#A1A1A8] mb-1">
              <Eye size={12} /> Can see
            </div>
            {schema.visibility.map(k => (
              <Toggle key={k} on={perms.visibility[k]} onClick={() => toggle('visibility', k)} label={LABELS[k] || k} />
            ))}
          </div>
          <div>
            <div className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-[#A1A1A8] mb-1">
              <ShieldCheck size={12} /> Can do
            </div>
            {schema.actions.filter(k => k !== 'post_chat').map(k => (
              <Toggle key={k} on={perms.actions[k]} onClick={() => toggle('actions', k)} label={LABELS[k] || k} />
            ))}
          </div>
        </div>
      )}
      {role === 'employee' && (
        <p className="text-xs text-[#A1A1A8]">
          Employees see their own shifts and the internal chat. Toggle “Team schedule” visibility
          below if you want them to see the full team schedule.
        </p>
      )}
      {role === 'employee' && (
        <Toggle on={perms.visibility.schedule} onClick={() => toggle('visibility', 'schedule')} label="Can see team schedule" />
      )}

      {err && <p className="text-sm text-red-400">{err}</p>}
      {msg && <p className="text-sm text-[#17C5B0] flex items-center gap-1"><Check size={14} /> {msg}</p>}
      <button onClick={submit} disabled={busy}
        className="flex items-center gap-2 bg-[#17C5B0] text-black font-medium px-4 py-2 rounded-lg text-sm disabled:opacity-50">
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
        Create & send invite
      </button>
    </div>
  )
}

function MemberRow({ m }: { m: Member }) {
  const grantedActions = Object.entries(m.permissions?.actions || {})
    .filter(([, v]) => v).map(([k]) => LABELS[k] || k)
  return (
    <div className="card p-4 flex items-center justify-between">
      <div>
        <div className="text-white text-sm font-medium">{m.full_name || m.email}</div>
        <div className="text-xs text-[#A1A1A8]">{m.email}</div>
        {m.role === 'manager' && grantedActions.length > 0 && (
          <div className="text-xs text-[#A1A1A8]/70 mt-1">Can: {grantedActions.join(', ')}</div>
        )}
      </div>
      <div className="flex items-center gap-2">
        <span className={`px-2 py-0.5 rounded text-xs capitalize ${
          m.role === 'owner' ? 'bg-amber-400/10 text-amber-400'
          : m.role === 'manager' ? 'bg-[#17C5B0]/10 text-[#17C5B0]'
          : 'bg-[#1F1F23] text-[#A1A1A8]'}`}>{m.role}</span>
        {m.invite_status === 'pending' && (
          <span className="px-2 py-0.5 rounded text-xs bg-blue-400/10 text-blue-300">invited</span>
        )}
      </div>
    </div>
  )
}

export default function TeamManagementPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const [reloadKey, setReloadKey] = useState(0)

  const schemaState = useApi(() => teamApi.permissionSchema(), [])
  const membersState = useApi(
    () => (orgId && !isDemo ? teamApi.members(orgId) : Promise.resolve({ members: [], total: 0 })),
    [orgId, isDemo, reloadKey],
  )

  if (isDemo) {
    return <div className="p-6 text-[#A1A1A8]">Team Management is available once your account is connected.</div>
  }
  if (schemaState.loading || membersState.loading) return <LoadingPage />
  if (membersState.error) return <ErrorState message={membersState.error} onRetry={membersState.refetch} />

  const schema = schemaState.data!
  const members = membersState.data?.members || []

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-4xl">
      <div>
        <h1 className="text-xl font-semibold text-white">Team</h1>
        <p className="text-sm text-[#A1A1A8]">Create accounts, set roles, and control what each person can see and do.</p>
      </div>
      <CreateMemberForm orgId={orgId} schema={schema} onCreated={() => setReloadKey(k => k + 1)} />
      <div className="space-y-2">
        <div className="text-xs uppercase tracking-wide text-[#A1A1A8]">Members ({members.length})</div>
        {members.length === 0 && <div className="text-sm text-[#A1A1A8]">No team members yet.</div>}
        {members.map(m => <MemberRow key={m.id} m={m} />)}
      </div>
    </div>
  )
}
