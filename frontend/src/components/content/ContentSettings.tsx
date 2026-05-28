import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Instagram,
  Facebook,
  Linkedin,
  Globe,
  MapPin,
  Music2,
  ArrowLeft,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useNavigate, useLocation } from 'react-router-dom'

interface PlatformRow {
  id: string
  label: string
  icon: typeof Instagram
  color: string
  connected: boolean
}

const DEFAULT_PLATFORMS: PlatformRow[] = [
  { id: 'instagram', label: 'Instagram', icon: Instagram, color: 'text-purple-400', connected: true },
  { id: 'facebook', label: 'Facebook', icon: Facebook, color: 'text-blue-400', connected: true },
  { id: 'tiktok', label: 'TikTok', icon: Music2, color: 'text-[#F5F5F7]', connected: false },
  { id: 'linkedin', label: 'LinkedIn', icon: Linkedin, color: 'text-blue-500', connected: false },
  { id: 'google_business', label: 'Google Business', icon: MapPin, color: 'text-green-400', connected: true },
]

export default function ContentSettings() {
  const navigate = useNavigate()
  const location = useLocation()
  const basePath = location.pathname.replace(/\/content\/settings$/, '')

  const [platforms] = useState<PlatformRow[]>(DEFAULT_PLATFORMS)
  const [wpUrl, setWpUrl] = useState('')
  const [wpPassword, setWpPassword] = useState('')
  const [autoPublish, setAutoPublish] = useState(false)
  const [approvalEmail, setApprovalEmail] = useState('')

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(basePath + '/content')}
          className="p-1.5 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Content Settings</h1>
          <p className="text-sm text-[#A1A1A8] mt-0.5">Manage your social platforms and publishing preferences</p>
        </div>
      </div>

      {/* Social Platforms */}
      <div className="card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-[#F5F5F7]">Social Platforms</h2>
        <div className="space-y-2">
          {platforms.map(p => {
            const Icon = p.icon
            return (
              <div
                key={p.id}
                className="flex items-center justify-between py-3 px-4 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]"
              >
                <div className="flex items-center gap-3">
                  <Icon size={18} className={p.color} />
                  <span className="text-sm text-[#F5F5F7] font-medium">{p.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={clsx(
                      'text-[10px] font-medium px-2 py-0.5 rounded-full border',
                      p.connected
                        ? 'text-[#17C5B0] bg-[#17C5B0]/10 border-[#17C5B0]/20'
                        : 'text-[#A1A1A8]/60 bg-[#1F1F23] border-[#1F1F23]',
                    )}
                  >
                    {p.connected ? 'Connected' : 'Not Connected'}
                  </span>
                  <button
                    className={clsx(
                      'text-[11px] font-medium px-3 py-1.5 rounded-md transition-colors',
                      p.connected
                        ? 'text-[#A1A1A8] bg-[#1F1F23] hover:bg-[#1F1F23]/80'
                        : 'text-white bg-[#1A8FD6] hover:bg-[#1A8FD6]/90',
                    )}
                  >
                    {p.connected ? 'Disconnect' : 'Connect'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* WordPress */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Globe size={16} className="text-blue-400" />
          <h2 className="text-sm font-semibold text-[#F5F5F7]">WordPress</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-[11px] text-[#A1A1A8] font-medium mb-1 block">Site URL</label>
            <input
              type="url"
              placeholder="https://yoursite.com"
              value={wpUrl}
              onChange={e => setWpUrl(e.target.value)}
              className="w-full text-sm bg-[#0A0A0B] border border-[#1F1F23] text-[#F5F5F7] rounded-lg px-3 py-2 focus:border-[#1A8FD6] focus:outline-none placeholder:text-[#A1A1A8]/30"
            />
          </div>
          <div>
            <label className="text-[11px] text-[#A1A1A8] font-medium mb-1 block">Application Password</label>
            <input
              type="password"
              placeholder="xxxx xxxx xxxx xxxx"
              value={wpPassword}
              onChange={e => setWpPassword(e.target.value)}
              className="w-full text-sm bg-[#0A0A0B] border border-[#1F1F23] text-[#F5F5F7] rounded-lg px-3 py-2 focus:border-[#1A8FD6] focus:outline-none placeholder:text-[#A1A1A8]/30"
            />
          </div>
        </div>
        <button className="text-[11px] font-semibold bg-[#1A8FD6] text-white px-4 py-2 rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
          Save WordPress
        </button>
      </div>

      {/* Publishing Preferences */}
      <div className="card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-[#F5F5F7]">Publishing Preferences</h2>
        <div className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm text-[#F5F5F7]">Auto-publish approved posts</p>
            <p className="text-[11px] text-[#A1A1A8]/60">
              Automatically publish posts at their scheduled time after approval
            </p>
          </div>
          <button
            onClick={() => setAutoPublish(prev => !prev)}
            className={clsx(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
              autoPublish ? 'bg-[#1A8FD6]' : 'bg-[#1F1F23]',
            )}
          >
            <span
              className={clsx(
                'inline-block h-4 w-4 rounded-full bg-white transition-transform',
                autoPublish ? 'translate-x-6' : 'translate-x-1',
              )}
            />
          </button>
        </div>
        <div>
          <label className="text-[11px] text-[#A1A1A8] font-medium mb-1 block">Approval notification email</label>
          <input
            type="email"
            placeholder="you@example.com"
            value={approvalEmail}
            onChange={e => setApprovalEmail(e.target.value)}
            className="w-full max-w-sm text-sm bg-[#0A0A0B] border border-[#1F1F23] text-[#F5F5F7] rounded-lg px-3 py-2 focus:border-[#1A8FD6] focus:outline-none placeholder:text-[#A1A1A8]/30"
          />
        </div>
      </div>
    </motion.div>
  )
}
