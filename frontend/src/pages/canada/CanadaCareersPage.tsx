import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Send, Briefcase, TrendingUp, Users, CheckCircle2, AlertCircle, Linkedin, UserCircle } from 'lucide-react'
import MeridianLogo, { MeridianEmblem } from '@/components/MeridianLogo'
import GrainOverlay from '@/components/landing/GrainOverlay'
import MagneticButton from '@/components/landing/MagneticButton'
import { supabase } from '@/lib/supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''
const EASE = [0.16, 1, 0.3, 1] as const
const PROVINCES = ['ON','BC','AB','QC','MB','SK','NS','NB','NL','PE','NT','YT','NU'] as const
const HEAR_OPTIONS = ['LinkedIn','Referral','Job Board','Social Media','Other'] as const
const AVAILABILITY = ['Immediately','2 weeks','1 month','Other'] as const

const INPUT = 'w-full bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-2.5 text-[#F5F5F7] text-[14px] focus:outline-none focus:border-[#1A8FD6]/50 transition-colors'
const LABEL = 'block text-[12px] text-[#A1A1A8] font-medium mb-1.5'

const positions = [
  {
    title: 'Sales Representative',
    type: 'Commission-Based',
    location: 'Remote — Canada',
    icon: TrendingUp,
    description:
      'Help Canadian small businesses unlock the power of their POS data. Sell Meridian to restaurants, cafes, and retail shops across Canada — earn 30-60% commission on every deal you close.',
    perks: ['30-60% commission per account', 'Flexible schedule — work your own hours', 'Full sales training & onboarding provided', 'Real-time portal to manage your pipeline'],
  },
  {
    title: 'Sales Team Lead',
    type: 'Commission + Override',
    location: 'Remote — Canada',
    icon: Users,
    description:
      "Build and manage a Canadian team of sales reps. Recruit, train, and scale our field sales operation across provinces while earning overrides on your team's production.",
    perks: ['Override commission on team sales', 'Recruit and build your own team', 'Leadership training & support', 'Performance bonuses'],
  },
]

interface Recruiter {
  id: string
  name: string
  title: string
  company: string
  bio: string
  linkedin_url: string
  email: string
  photo_url: string | null
  region: string
  active: boolean
  display_order: number
}

const FALLBACK_RECRUITERS: Recruiter[] = [
  {
    id: '1',
    name: 'Enoch Cheung',
    title: 'Canadian Regional Director, Meridian',
    company: 'Nexus Consulting',
    bio: "Leading Meridian's expansion across Canadian markets.",
    linkedin_url: '', // TODO: replace with real contact URL
    email: '',
    photo_url: null,
    region: 'canada',
    active: true,
    display_order: 1,
  },
]

const empty = { name: '', email: '', phone: '', position: '', city: '', province: '', experience: '', employer: '', linkedin: '', heardFrom: '', availability: '', message: '' }

export default function CanadaCareersPage() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState(empty)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [recruiters, setRecruiters] = useState<Recruiter[]>(FALLBACK_RECRUITERS)

  useEffect(() => {
    async function loadRecruiters() {
      if (!supabase) return
      try {
        const { data } = await supabase
          .from('recruiters')
          .select('*')
          .eq('region', 'canada')
          .eq('active', true)
          .order('display_order', { ascending: true })
        if (data && data.length > 0) setRecruiters(data as Recruiter[])
      } catch { /* use fallback */ }
    }
    loadRecruiters()
  }, [])

  const set = (key: keyof typeof empty) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setFormData((d) => ({ ...d, [key]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/canada/careers/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })
      if (res.ok) { setSubmitted(true); return }
      const errData = await res.json().catch(() => null)
      throw new Error(errData?.detail || `Server responded with ${res.status}`)
    } catch (err: any) {
      setError(err?.message || 'Something went wrong. Please try again.')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B] overflow-x-hidden">
      <GrainOverlay />

      {/* NAV */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-[#1F1F23]/60 bg-[#0A0A0B]/70 backdrop-blur-[20px]">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MeridianLogo size={28} showWordmark showTagline={false} />
            <span className="text-[11px] px-2 py-0.5 rounded-full border border-red-500/30 text-red-400 bg-red-500/10 font-medium flex items-center gap-1">
              <span aria-label="CN Tower">&#128508;</span> Canada
            </span>
          </div>
          <MagneticButton onClick={() => navigate('/canada')} className="px-4 py-1.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors duration-200 flex items-center gap-1.5">
            <ArrowLeft size={14} />
            Back to Home
          </MagneticButton>
        </div>
      </header>

      {/* HERO */}
      <section className="pt-32 pb-16 relative">
        <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full bg-[#1A8FD6]/8 blur-[120px]" />
        <div className="max-w-5xl mx-auto px-6 text-center relative">
          <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, ease: EASE }} className="flex justify-center mb-6">
            <MeridianEmblem size={56} />
          </motion.div>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE, delay: 0.05 }} className="text-4xl md:text-6xl font-bold text-[#F5F5F7] tracking-tight">
            Join{' '}<em className="font-serif italic font-normal bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">Meridian Canada</em>
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE, delay: 0.1 }} className="mt-4 text-[#A1A1A8] text-[16px] max-w-lg mx-auto leading-relaxed">
            We're expanding across Canada. Help local businesses thrive from coast to coast and earn great money doing it.
          </motion.p>
        </div>
      </section>

      {/* OPEN POSITIONS */}
      <section className="pb-16">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-xl font-semibold text-[#F5F5F7] mb-6 flex items-center gap-2">
            <Briefcase size={20} className="text-[#1A8FD6]" /> Open Positions
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {positions.map((pos) => (
              <motion.div key={pos.title} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE }} className="rounded-xl border border-[#1F1F23] bg-[#111113]/80 p-6 hover:border-[#1A8FD6]/30 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-[#F5F5F7] font-semibold text-lg">{pos.title}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[11px] px-2 py-0.5 rounded-full border border-[#1A8FD6]/30 text-[#1A8FD6] bg-[#1A8FD6]/10 font-medium">{pos.type}</span>
                      <span className="text-[11px] px-2 py-0.5 rounded-full border border-[#17C5B0]/30 text-[#17C5B0] bg-[#17C5B0]/10 font-medium">{pos.location}</span>
                    </div>
                  </div>
                  <pos.icon size={24} className="text-[#1A8FD6]/60" />
                </div>
                <p className="text-[#A1A1A8] text-[13px] leading-relaxed mb-4">{pos.description}</p>
                <ul className="space-y-1.5">
                  {pos.perks.map((perk) => (
                    <li key={perk} className="flex items-center gap-2 text-[12px] text-[#A1A1A8]/80">
                      <CheckCircle2 size={12} className="text-[#17C5B0] shrink-0" /> {perk}
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* YOUR RECRUITER */}
      {recruiters.length > 0 && (
        <section className="pb-16">
          <div className="max-w-5xl mx-auto px-6">
            <h2 className="text-xl font-semibold text-[#F5F5F7] mb-2 flex items-center gap-2">
              <UserCircle size={20} className="text-[#1A8FD6]" /> Your Recruiter
            </h2>
            <p className="text-[13px] text-[#A1A1A8] mb-6">Questions about the role? Reach out directly.</p>
            <div className={`grid gap-4 ${recruiters.length > 1 ? 'md:grid-cols-2' : 'max-w-md'}`}>
              {recruiters.map(rec => (
                <motion.div
                  key={rec.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: EASE }}
                  className="rounded-xl border border-[#1F1F23] bg-[#111113]/80 p-6 hover:border-[#1A8FD6]/30 transition-colors"
                >
                  <div className="flex items-center gap-4 mb-4">
                    <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[#1A8FD6]/20 to-[#17C5B0]/20 border border-[#1F1F23] flex items-center justify-center flex-shrink-0 overflow-hidden">
                      {rec.photo_url ? (
                        <img src={rec.photo_url} alt={rec.name} className="w-full h-full object-cover rounded-full" />
                      ) : (
                        <span className="text-xl font-bold bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">
                          {rec.name.split(' ').map(n => n[0]).join('')}
                        </span>
                      )}
                    </div>
                    <div>
                      <h3 className="text-[#F5F5F7] font-semibold text-[15px]">{rec.name}</h3>
                      <p className="text-[12px] text-[#A1A1A8]">{rec.title}</p>
                      <p className="text-[11px] text-[#1A8FD6] mt-0.5">{rec.company}</p>
                    </div>
                  </div>
                  {rec.bio && (
                    <p className="text-[13px] text-[#A1A1A8]/80 leading-relaxed mb-4">{rec.bio}</p>
                  )}
                  <a
                    href={rec.linkedin_url || rec.email ? `mailto:${rec.email}` : '#'}
                    target={rec.linkedin_url ? '_blank' : undefined}
                    rel={rec.linkedin_url ? 'noopener noreferrer' : undefined}
                    className="inline-flex items-center gap-2 px-4 py-2 text-[13px] font-medium text-[#1A8FD6] border border-[#1A8FD6]/30 rounded-lg bg-[#1A8FD6]/5 hover:bg-[#1A8FD6]/10 hover:border-[#1A8FD6]/50 transition-all"
                  >
                    <Linkedin size={14} /> Connect with {rec.name.split(' ')[0]}
                  </a>
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* APPLICATION FORM */}
      <section className="pb-24">
        <div className="max-w-2xl mx-auto px-6">
          <h2 className="text-xl font-semibold text-[#F5F5F7] mb-6 flex items-center gap-2">
            <Send size={20} className="text-[#1A8FD6]" /> Apply Now
          </h2>

          {submitted ? (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="rounded-xl border border-[#17C5B0]/30 bg-[#17C5B0]/5 p-8 text-center">
              <CheckCircle2 size={40} className="text-[#17C5B0] mx-auto mb-4" />
              <h3 className="text-[#F5F5F7] text-lg font-semibold">Application Received!</h3>
              <p className="text-[#A1A1A8] text-[14px] mt-2">Thanks {formData.name}! We'll review your application and get back to you soon.</p>
            </motion.div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="flex items-center gap-2 text-red-400 text-[13px] bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2.5">
                  <AlertCircle size={16} /> {error}
                </div>
              )}
              {/* Row 1: Name + Email */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div><label className={LABEL}>Full Name *</label><input type="text" required value={formData.name} onChange={set('name')} className={INPUT} placeholder="Jane Doe" /></div>
                <div><label className={LABEL}>Email *</label><input type="email" required value={formData.email} onChange={set('email')} className={INPUT} placeholder="you@example.com" /></div>
              </div>
              {/* Row 2: Phone + Position */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div><label className={LABEL}>Phone *</label><input type="tel" required value={formData.phone} onChange={set('phone')} className={INPUT} placeholder="(416) 555-0199" /></div>
                <div>
                  <label className={LABEL}>Position *</label>
                  <select required value={formData.position} onChange={set('position')} className={INPUT}>
                    <option value="">Select a position</option>
                    <option value="sales_rep">Sales Representative</option>
                    <option value="team_lead">Sales Team Lead</option>
                  </select>
                </div>
              </div>
              {/* Row 3: City + Province */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div><label className={LABEL}>City *</label><input type="text" required value={formData.city} onChange={set('city')} className={INPUT} placeholder="Toronto, Vancouver, etc." /></div>
                <div>
                  <label className={LABEL}>Province *</label>
                  <select required value={formData.province} onChange={set('province')} className={INPUT}>
                    <option value="">Select province</option>
                    {PROVINCES.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
              </div>
              {/* Row 4: Experience + Employer */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div><label className={LABEL}>Sales Experience</label><input type="text" value={formData.experience} onChange={set('experience')} className={INPUT} placeholder="e.g. 2 years B2B, door-to-door" /></div>
                <div><label className={LABEL}>Current Employer</label><input type="text" value={formData.employer} onChange={set('employer')} className={INPUT} placeholder="Optional" /></div>
              </div>
              {/* Row 5: LinkedIn + Heard From */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div><label className={LABEL}>LinkedIn URL</label><input type="url" value={formData.linkedin} onChange={set('linkedin')} className={INPUT} placeholder="https://linkedin.com/in/..." /></div>
                <div>
                  <label className={LABEL}>How did you hear about us?</label>
                  <select value={formData.heardFrom} onChange={set('heardFrom')} className={INPUT}>
                    <option value="">Select one</option>
                    {HEAR_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
              </div>
              {/* Row 6: Availability */}
              <div>
                <label className={LABEL}>Availability</label>
                <select value={formData.availability} onChange={set('availability')} className={INPUT}>
                  <option value="">Select availability</option>
                  {AVAILABILITY.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              {/* Row 7: Message */}
              <div>
                <label className={LABEL}>Why do you want to join Meridian Canada?</label>
                <textarea rows={4} value={formData.message} onChange={set('message')} className={`${INPUT} resize-none`} placeholder="Tell us a bit about yourself..." />
              </div>
              <button type="submit" disabled={loading} className="w-full py-3 bg-[#1A8FD6] text-white font-medium rounded-lg hover:bg-[#1574B8] transition-colors duration-200 flex items-center justify-center gap-2 disabled:opacity-50">
                <Send size={16} /> {loading ? 'Submitting...' : 'Submit Application'}
              </button>
            </form>
          )}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[#1F1F23]/40 py-8">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <p className="text-[11px] text-[#A1A1A8]/30">&copy; 2026 <span className="font-semibold bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">Meridian Canada</span></p>
        </div>
      </footer>
    </div>
  )
}
