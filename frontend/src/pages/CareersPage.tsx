import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Send, Briefcase, TrendingUp, Users, CheckCircle2 } from 'lucide-react'
import MeridianLogo, { MeridianEmblem } from '@/components/MeridianLogo'
import GrainOverlay from '@/components/landing/GrainOverlay'
import MagneticButton from '@/components/landing/MagneticButton'

const EASE = [0.16, 1, 0.3, 1] as const

const positions = [
  {
    title: 'Sales Representative',
    type: 'Commission-Based',
    location: 'Remote',
    icon: TrendingUp,
    description:
      'Help local businesses unlock the power of their POS data. Sell Meridian to restaurants, cafes, and retail shops — earn 30-60% commission on every deal you close.',
    perks: [
      '30-60% commission per account',
      'Flexible schedule — work your own hours',
      'Full sales training & onboarding provided',
      'Real-time portal to manage your pipeline',
    ],
  },
  {
    title: 'Sales Team Lead',
    type: 'Commission + Override',
    location: 'Remote',
    icon: Users,
    description:
      'Build and manage a team of sales reps. Recruit, train, and scale our field sales operation while earning overrides on your team\'s production.',
    perks: [
      'Override commission on team sales',
      'Recruit and build your own team',
      'Leadership training & support',
      'Performance bonuses',
    ],
  },
]

export default function CareersPage() {
  const navigate = useNavigate()
  const [submitted, setSubmitted] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    position: '',
    experience: '',
    message: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // In the future this would hit an API — for now just show confirmation
    setSubmitted(true)
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B] overflow-x-hidden">
      <GrainOverlay />

      {/* NAV */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-[#1F1F23]/60 bg-[#0A0A0B]/70 backdrop-blur-[20px]">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <MeridianLogo size={28} showWordmark showTagline={false} />
          </div>
          <MagneticButton
            onClick={() => navigate('/landing')}
            className="px-4 py-1.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors duration-200 flex items-center gap-1.5"
          >
            <ArrowLeft size={14} />
            Back to Home
          </MagneticButton>
        </div>
      </header>

      {/* HERO */}
      <section className="pt-32 pb-16 relative">
        <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full bg-[#1A8FD6]/8 blur-[120px]" />
        <div className="max-w-5xl mx-auto px-6 text-center relative">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: EASE }}
            className="flex justify-center mb-6"
          >
            <MeridianEmblem size={56} />
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.1 }}
            className="text-4xl md:text-6xl font-bold text-[#F5F5F7] tracking-tight"
          >
            Join the{' '}
            <em className="font-serif italic font-normal bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">
              Meridian
            </em>{' '}
            team
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.2 }}
            className="mt-4 text-[#A1A1A8] text-[16px] max-w-lg mx-auto leading-relaxed"
          >
            We're building the future of small business intelligence. Help local businesses thrive and earn great money doing it.
          </motion.p>
        </div>
      </section>

      {/* OPEN POSITIONS */}
      <section className="pb-16">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-xl font-semibold text-[#F5F5F7] mb-6 flex items-center gap-2">
            <Briefcase size={20} className="text-[#1A8FD6]" />
            Open Positions
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {positions.map((pos) => (
              <motion.div
                key={pos.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: EASE }}
                className="rounded-xl border border-[#1F1F23] bg-[#111113]/80 p-6 hover:border-[#1A8FD6]/30 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-[#F5F5F7] font-semibold text-lg">{pos.title}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[11px] px-2 py-0.5 rounded-full border border-[#1A8FD6]/30 text-[#1A8FD6] bg-[#1A8FD6]/10 font-medium">
                        {pos.type}
                      </span>
                      <span className="text-[11px] px-2 py-0.5 rounded-full border border-[#17C5B0]/30 text-[#17C5B0] bg-[#17C5B0]/10 font-medium">
                        {pos.location}
                      </span>
                    </div>
                  </div>
                  <pos.icon size={24} className="text-[#1A8FD6]/60" />
                </div>
                <p className="text-[#A1A1A8] text-[13px] leading-relaxed mb-4">{pos.description}</p>
                <ul className="space-y-1.5">
                  {pos.perks.map((perk) => (
                    <li key={perk} className="flex items-center gap-2 text-[12px] text-[#A1A1A8]/80">
                      <CheckCircle2 size={12} className="text-[#17C5B0] shrink-0" />
                      {perk}
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* APPLICATION FORM */}
      <section className="pb-24">
        <div className="max-w-2xl mx-auto px-6">
          <h2 className="text-xl font-semibold text-[#F5F5F7] mb-6 flex items-center gap-2">
            <Send size={20} className="text-[#1A8FD6]" />
            Apply Now
          </h2>

          {submitted ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="rounded-xl border border-[#17C5B0]/30 bg-[#17C5B0]/5 p-8 text-center"
            >
              <CheckCircle2 size={40} className="text-[#17C5B0] mx-auto mb-4" />
              <h3 className="text-[#F5F5F7] text-lg font-semibold">Application Received!</h3>
              <p className="text-[#A1A1A8] text-[14px] mt-2">
                Thanks {formData.name}! We'll review your application and get back to you soon.
              </p>
            </motion.div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[12px] text-[#A1A1A8] font-medium mb-1.5">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-2.5 text-[#F5F5F7] text-[14px] focus:outline-none focus:border-[#1A8FD6]/50 transition-colors"
                    placeholder="John Smith"
                  />
                </div>
                <div>
                  <label className="block text-[12px] text-[#A1A1A8] font-medium mb-1.5">Email *</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-2.5 text-[#F5F5F7] text-[14px] focus:outline-none focus:border-[#1A8FD6]/50 transition-colors"
                    placeholder="you@example.com"
                  />
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[12px] text-[#A1A1A8] font-medium mb-1.5">Phone</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-2.5 text-[#F5F5F7] text-[14px] focus:outline-none focus:border-[#1A8FD6]/50 transition-colors"
                    placeholder="(555) 123-4567"
                  />
                </div>
                <div>
                  <label className="block text-[12px] text-[#A1A1A8] font-medium mb-1.5">Position *</label>
                  <select
                    required
                    value={formData.position}
                    onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                    className="w-full bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-2.5 text-[#F5F5F7] text-[14px] focus:outline-none focus:border-[#1A8FD6]/50 transition-colors"
                  >
                    <option value="">Select a position</option>
                    <option value="sales_rep">Sales Representative</option>
                    <option value="team_lead">Sales Team Lead</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-[12px] text-[#A1A1A8] font-medium mb-1.5">Sales Experience</label>
                <input
                  type="text"
                  value={formData.experience}
                  onChange={(e) => setFormData({ ...formData, experience: e.target.value })}
                  className="w-full bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-2.5 text-[#F5F5F7] text-[14px] focus:outline-none focus:border-[#1A8FD6]/50 transition-colors"
                  placeholder="e.g. 2 years B2B, door-to-door, etc."
                />
              </div>
              <div>
                <label className="block text-[12px] text-[#A1A1A8] font-medium mb-1.5">Why do you want to join Meridian?</label>
                <textarea
                  rows={4}
                  value={formData.message}
                  onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                  className="w-full bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-2.5 text-[#F5F5F7] text-[14px] focus:outline-none focus:border-[#1A8FD6]/50 transition-colors resize-none"
                  placeholder="Tell us a bit about yourself..."
                />
              </div>
              <button
                type="submit"
                className="w-full py-3 bg-[#1A8FD6] text-white font-medium rounded-lg hover:bg-[#1574B8] transition-colors duration-200 flex items-center justify-center gap-2"
              >
                <Send size={16} />
                Submit Application
              </button>
            </form>
          )}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[#1F1F23]/40 py-8">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <p className="text-[11px] text-[#A1A1A8]/30">© 2026 <span className="font-semibold bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">Meridian</span></p>
        </div>
      </footer>
    </div>
  )
}
