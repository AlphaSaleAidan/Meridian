import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Settings, User, Bell, Shield, Check, Eye, EyeOff, Loader2 } from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase } from '@/lib/supabase'

export default function CanadaPortalSettingsPage() {
  const { rep } = useSalesAuth()
  const [searchParams] = useSearchParams()
  const isPasswordReset = searchParams.get('reset') === '1'
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [name, setName] = useState(rep?.name || '')
  const [phone, setPhone] = useState(rep?.phone || '')

  const [showPwSection, setShowPwSection] = useState(isPasswordReset)
  const [pw, setPw] = useState('')
  const [pwConfirm, setPwConfirm] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [pwDone, setPwDone] = useState(false)
  const [pwError, setPwError] = useState('')
  const [showPw, setShowPw] = useState(false)

  const [notifications, setNotifications] = useState(() => {
    try {
      const stored = localStorage.getItem('meridian_notification_prefs')
      if (stored) return JSON.parse(stored)
    } catch { /* ignore */ }
    return {
      email_new_lead: true,
      email_commission: true,
      email_payout: true,
      email_weekly_report: true,
    }
  })

  const [saveError, setSaveError] = useState('')

  async function handleSave() {
    setSaving(true)
    setSaveError('')
    try {
      if (supabase && rep?.rep_id) {
        const { error } = await supabase.from('sales_reps').update({ name, phone }).eq('id', rep.rep_id)
        if (error) throw new Error(error.message)
      }
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  async function handlePasswordChange() {
    setPwError('')
    if (pw.length < 8) { setPwError('Password must be at least 8 characters'); return }
    if (pw !== pwConfirm) { setPwError('Passwords do not match'); return }
    setPwSaving(true)
    try {
      if (supabase) {
        const { error } = await supabase.auth.updateUser({ password: pw })
        if (error) { setPwError(error.message); return }
      }
      setPwDone(true)
      setPw('')
      setPwConfirm('')
      setTimeout(() => { setPwDone(false); setShowPwSection(false) }, 2000)
    } finally {
      setPwSaving(false)
    }
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-sm text-white placeholder-[#6b7a74]/40 focus:outline-none focus:border-[#00d4aa]/50 focus:ring-1 focus:ring-[#00d4aa]/20 transition-colors'

  return (
    <div className="space-y-6 max-w-2xl">
      {isPasswordReset && (
        <div className="p-4 rounded-xl bg-[#f59e0b]/10 border border-[#f59e0b]/20">
          <p className="text-sm font-semibold text-[#f59e0b]">Set your new password</p>
          <p className="text-xs text-[#f59e0b]/70 mt-0.5">Enter a new password below to complete your password reset.</p>
        </div>
      )}
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-sm text-[#6b7a74] mt-0.5">Manage your account preferences.</p>
      </div>

      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <User size={16} className="text-[#00d4aa]" />
          <h2 className="text-sm font-semibold text-white">Profile</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Name</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Email</label>
            <input type="email" defaultValue={rep?.email || ''} className={inputClass} readOnly />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Phone</label>
            <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Commission Rate</label>
            <input type="text" value={rep ? `${rep.commission_rate}%` : ''} className={inputClass} readOnly />
          </div>
        </div>
      </div>

      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Bell size={16} className="text-[#7C5CFF]" />
          <h2 className="text-sm font-semibold text-white">Notifications</h2>
        </div>
        <div className="space-y-3">
          {[
            { key: 'email_new_lead' as const, label: 'New lead assignments', desc: 'Get notified when a new lead is assigned to you' },
            { key: 'email_commission' as const, label: 'Commission earned', desc: 'Receive alerts when commissions are recorded' },
            { key: 'email_payout' as const, label: 'Payout processed', desc: 'Get notified when payouts are completed' },
            { key: 'email_weekly_report' as const, label: 'Weekly sales report', desc: 'Receive a weekly summary of your sales activity' },
          ].map(item => (
            <label key={item.key} className="flex items-center justify-between py-2 cursor-pointer">
              <div>
                <p className="text-[11px] font-medium text-white">{item.label}</p>
                <p className="text-[10px] text-[#6b7a74]/40">{item.desc}</p>
              </div>
              <button
                onClick={() => setNotifications((prev: Record<string, boolean>) => { const next = { ...prev, [item.key]: !prev[item.key] }; localStorage.setItem('meridian_notification_prefs', JSON.stringify(next)); return next })}
                className={`w-9 h-5 rounded-full transition-colors relative ${notifications[item.key] ? 'bg-[#00d4aa]' : 'bg-[#1a2420]'}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${notifications[item.key] ? 'left-[18px]' : 'left-0.5'}`} />
              </button>
            </label>
          ))}
        </div>
      </div>

      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={16} className="text-[#F59E0B]" />
          <h2 className="text-sm font-semibold text-white">Security</h2>
        </div>
        {!showPwSection ? (
          <button
            onClick={() => setShowPwSection(true)}
            className="px-4 py-2 bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-sm text-[#6b7a74] hover:text-white hover:border-[#2a3a34] transition-colors"
          >
            Change Password
          </button>
        ) : (
          <div className="space-y-3">
            <div className="relative">
              <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">New Password</label>
              <input
                type={showPw ? 'text' : 'password'}
                value={pw}
                onChange={e => setPw(e.target.value)}
                className={inputClass}
                placeholder="At least 8 characters"
              />
              <button type="button" onClick={() => setShowPw(p => !p)} className="absolute right-3 top-[30px] text-[#6b7a74]">
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <div>
              <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Confirm Password</label>
              <input
                type={showPw ? 'text' : 'password'}
                value={pwConfirm}
                onChange={e => setPwConfirm(e.target.value)}
                className={inputClass}
                placeholder="Re-enter password"
              />
            </div>
            {pwError && <p className="text-xs text-red-400">{pwError}</p>}
            <div className="flex gap-2">
              <button
                onClick={handlePasswordChange}
                disabled={pwSaving}
                className="flex items-center gap-2 px-4 py-2 bg-[#F59E0B] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#F59E0B]/90 disabled:opacity-50 transition-all"
              >
                {pwSaving ? <Loader2 size={14} className="animate-spin" /> : pwDone ? <Check size={14} /> : null}
                {pwDone ? 'Updated' : 'Update Password'}
              </button>
              <button
                onClick={() => { setShowPwSection(false); setPw(''); setPwConfirm(''); setPwError('') }}
                className="px-4 py-2 border border-[#1a2420] rounded-lg text-sm text-[#6b7a74] hover:text-white transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {saveError && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20">
          <p className="text-xs text-red-400">{saveError}</p>
        </div>
      )}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : saved ? <><Check size={16} /> Saved</> : 'Save Changes'}
        </button>
      </div>
    </div>
  )
}
