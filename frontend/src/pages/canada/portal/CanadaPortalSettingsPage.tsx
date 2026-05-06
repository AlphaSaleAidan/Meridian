import { useState } from 'react'
import { User, Bell, Shield, Check } from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'

export default function CanadaPortalSettingsPage() {
  const { rep } = useSalesAuth()
  const [saved, setSaved] = useState(false)
  const [notifications, setNotifications] = useState({
    email_new_lead: true,
    email_commission: true,
    email_payout: true,
    email_weekly_report: true,
  })

  function handleSave() {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#17C5B0]/50 focus:ring-1 focus:ring-[#17C5B0]/20 transition-colors'

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-[#F5F5F7]">Settings</h1>
        <p className="text-sm text-[#A1A1A8] mt-0.5">Manage your account preferences.</p>
      </div>

      <div className="card border border-[#1F1F23] p-5">
        <div className="flex items-center gap-2 mb-4">
          <User size={16} className="text-[#1A8FD6]" />
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Profile</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Name</label>
            <input type="text" defaultValue={rep?.name || ''} className={inputClass} />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
            <input type="email" defaultValue={rep?.email || ''} className={inputClass} readOnly />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Phone</label>
            <input type="tel" defaultValue={rep?.phone || ''} className={inputClass} />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Commission Rate</label>
            <input type="text" value={rep ? `${rep.commission_rate}%` : ''} className={inputClass} readOnly />
          </div>
        </div>
      </div>

      <div className="card border border-[#1F1F23] p-5">
        <div className="flex items-center gap-2 mb-4">
          <Bell size={16} className="text-[#7C5CFF]" />
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Notifications</h2>
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
                <p className="text-[11px] font-medium text-[#F5F5F7]">{item.label}</p>
                <p className="text-[10px] text-[#A1A1A8]/40">{item.desc}</p>
              </div>
              <button
                onClick={() => setNotifications(prev => ({ ...prev, [item.key]: !prev[item.key] }))}
                className={`w-9 h-5 rounded-full transition-colors relative ${notifications[item.key] ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]'}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${notifications[item.key] ? 'left-[18px]' : 'left-0.5'}`} />
              </button>
            </label>
          ))}
        </div>
      </div>

      <div className="card border border-[#1F1F23] p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={16} className="text-[#F59E0B]" />
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Security</h2>
        </div>
        <button className="px-4 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A2E] transition-colors">
          Change Password
        </button>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all"
        >
          {saved ? <><Check size={16} /> Saved</> : 'Save Changes'}
        </button>
      </div>
    </div>
  )
}
