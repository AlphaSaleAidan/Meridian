import { useState } from 'react'
import { X, Check } from 'lucide-react'
import type { ScheduleStaffMember } from '@/lib/agent-data'
import type { BusinessType } from '@/lib/demo-context'

const STAFF_COLORS = [
  '#17C5B0', '#1A8FD6', '#E06B5E', '#D4A843', '#9B7FD4', '#4CAF50',
  '#FF7043', '#26C6DA', '#AB47BC', '#78909C', '#EC407A', '#8D6E63',
]

const ROLES_BY_TYPE: Record<string, string[]> = {
  coffee_shop: ['barista', 'bar_lead', 'cashier', 'supervisor'],
  restaurant: ['server', 'bartender', 'host', 'kitchen', 'runner', 'manager'],
  fast_food: ['counter', 'drive_through', 'kitchen', 'manager'],
  auto_shop: ['technician', 'advisor', 'parts_counter'],
  smoke_shop: ['associate', 'shift_lead'],
}

const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

interface Props {
  open: boolean
  onClose: () => void
  onSave: (member: Omit<ScheduleStaffMember, 'id'>) => void
  businessType: BusinessType
  existing?: ScheduleStaffMember
}

export default function AddStaffModal({ open, onClose, onSave, businessType, existing }: Props) {
  const [name, setName] = useState(existing?.name || '')
  const [role, setRole] = useState(existing?.role || '')
  const [color, setColor] = useState(existing?.color || STAFF_COLORS[0])
  const [hourlyRate, setHourlyRate] = useState(existing ? String(existing.hourlyRate / 100) : '')
  const [availability, setAvailability] = useState<Record<string, { available: boolean; start: string; end: string }>>(
    existing?.availability || Object.fromEntries(DAY_KEYS.map(d => [d, { available: true, start: '09:00', end: '17:00' }]))
  )

  if (!open) return null

  const roles = ROLES_BY_TYPE[businessType] || ROLES_BY_TYPE.coffee_shop

  function handleSave() {
    if (!name.trim() || !role) return
    onSave({
      name: name.trim(),
      role,
      color,
      hourlyRate: hourlyRate ? Math.round(parseFloat(hourlyRate) * 100) : 0,
      availability,
    })
    onClose()
  }

  function toggleDay(day: string) {
    setAvailability(prev => ({
      ...prev,
      [day]: { ...prev[day], available: !prev[day].available },
    }))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-[#0A0A0B] border border-[#1F1F23] rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
          <h2 className="text-sm font-semibold text-[#F5F5F7]">
            {existing ? 'Edit Staff Member' : 'Add Staff Member'}
          </h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-[#1F1F23] text-[#A1A1A8]">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Name */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8]/60 block mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] focus:border-[#1A8FD6]/40 focus:outline-none transition-colors"
              placeholder="Staff name"
            />
          </div>

          {/* Role */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8]/60 block mb-1">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] focus:border-[#1A8FD6]/40 focus:outline-none transition-colors"
            >
              <option value="">Select role...</option>
              {roles.map(r => (
                <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          {/* Color */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8]/60 block mb-1">Color</label>
            <div className="flex flex-wrap gap-2">
              {STAFF_COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className="w-7 h-7 rounded-full flex items-center justify-center transition-transform hover:scale-110"
                  style={{ backgroundColor: c }}
                >
                  {color === c && <Check size={14} className="text-white" />}
                </button>
              ))}
            </div>
          </div>

          {/* Hourly Rate */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8]/60 block mb-1">
              Hourly Rate (optional)
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[#A1A1A8]/40">$</span>
              <input
                type="number"
                step="0.25"
                min="0"
                value={hourlyRate}
                onChange={(e) => setHourlyRate(e.target.value)}
                className="w-full pl-7 pr-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] focus:border-[#1A8FD6]/40 focus:outline-none transition-colors"
                placeholder="0.00"
              />
            </div>
          </div>

          {/* Availability */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8]/60 block mb-2">Availability</label>
            <div className="space-y-1.5">
              {DAY_KEYS.map((day, i) => (
                <div key={day} className="flex items-center gap-2">
                  <button
                    onClick={() => toggleDay(day)}
                    className={`w-10 text-[10px] font-semibold rounded py-1 text-center transition-colors ${
                      availability[day]?.available
                        ? 'bg-[#17C5B0]/15 text-[#17C5B0]'
                        : 'bg-[#1F1F23] text-[#A1A1A8]/30'
                    }`}
                  >
                    {DAY_LABELS[i]}
                  </button>
                  {availability[day]?.available && (
                    <div className="flex items-center gap-1 text-[10px] text-[#A1A1A8]/50 font-mono">
                      <input
                        type="time"
                        value={availability[day]?.start || '09:00'}
                        onChange={(e) => setAvailability(prev => ({
                          ...prev,
                          [day]: { ...prev[day], start: e.target.value },
                        }))}
                        className="bg-[#1F1F23] border border-[#1F1F23] rounded px-1.5 py-0.5 text-[10px] text-[#F5F5F7] focus:outline-none"
                      />
                      <span>–</span>
                      <input
                        type="time"
                        value={availability[day]?.end || '17:00'}
                        onChange={(e) => setAvailability(prev => ({
                          ...prev,
                          [day]: { ...prev[day], end: e.target.value },
                        }))}
                        className="bg-[#1F1F23] border border-[#1F1F23] rounded px-1.5 py-0.5 text-[10px] text-[#F5F5F7] focus:outline-none"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-[#1F1F23]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || !role}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            {existing ? 'Update' : 'Add Member'}
          </button>
        </div>
      </div>
    </div>
  )
}
