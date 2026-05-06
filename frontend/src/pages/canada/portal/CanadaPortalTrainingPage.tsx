import { useState } from 'react'
import {
  GraduationCap, Play, CheckCircle2, Clock, ChevronRight,
  BookOpen, Target, Users, Zap, Shield, BarChart3,
} from 'lucide-react'
import { clsx } from 'clsx'

interface Module {
  id: string
  title: string
  description: string
  icon: typeof GraduationCap
  duration: string
  lessons: { id: string; title: string; completed: boolean }[]
  category: string
}

const MODULES: Module[] = [
  {
    id: 'onboarding',
    title: 'New Rep Onboarding',
    description: 'Everything you need to know to start selling Meridian POS Intelligence.',
    icon: BookOpen,
    duration: '45 min',
    category: 'Getting Started',
    lessons: [
      { id: '1', title: 'Welcome to Meridian Sales', completed: true },
      { id: '2', title: 'Understanding the Product', completed: true },
      { id: '3', title: 'Pricing & Plans Overview', completed: true },
      { id: '4', title: 'Setting Up Your Pipeline', completed: false },
      { id: '5', title: 'First Week Checklist', completed: false },
    ],
  },
  {
    id: 'pitch',
    title: 'Perfecting Your Pitch',
    description: 'Master the Meridian value proposition and overcome common objections.',
    icon: Target,
    duration: '30 min',
    category: 'Sales Skills',
    lessons: [
      { id: '6', title: 'The 60-Second Elevator Pitch', completed: true },
      { id: '7', title: 'Pain Points by Vertical', completed: false },
      { id: '8', title: 'Handling Price Objections', completed: false },
      { id: '9', title: 'Competitive Positioning', completed: false },
    ],
  },
  {
    id: 'demo',
    title: 'Running a Great Demo',
    description: 'How to conduct product demos that convert prospects into clients.',
    icon: Play,
    duration: '25 min',
    category: 'Sales Skills',
    lessons: [
      { id: '10', title: 'Demo Environment Setup', completed: false },
      { id: '11', title: 'The Discovery Call Framework', completed: false },
      { id: '12', title: 'Feature Walkthrough Script', completed: false },
      { id: '13', title: 'Closing After the Demo', completed: false },
    ],
  },
  {
    id: 'verticals',
    title: 'Selling by Vertical',
    description: 'Tailored strategies for restaurants, smoke shops, salons, and retail.',
    icon: Users,
    duration: '40 min',
    category: 'Industry Knowledge',
    lessons: [
      { id: '14', title: 'Restaurants & Cafes', completed: false },
      { id: '15', title: 'Smoke Shops & Vape', completed: false },
      { id: '16', title: 'Salons & Spas', completed: false },
      { id: '17', title: 'Retail & Boutiques', completed: false },
      { id: '18', title: 'Food Trucks & QSR', completed: false },
    ],
  },
  {
    id: 'advanced',
    title: 'Advanced Closing Techniques',
    description: 'Negotiation tactics, urgency creation, and multi-location selling.',
    icon: Zap,
    duration: '35 min',
    category: 'Advanced',
    lessons: [
      { id: '19', title: 'Creating Urgency Without Pressure', completed: false },
      { id: '20', title: 'Multi-Location Upsell', completed: false },
      { id: '21', title: 'Referral Programs', completed: false },
      { id: '22', title: 'Commission Optimization', completed: false },
    ],
  },
  {
    id: 'compliance',
    title: 'Compliance & Ethics',
    description: 'Guidelines for responsible selling and regulatory compliance.',
    icon: Shield,
    duration: '20 min',
    category: 'Required',
    lessons: [
      { id: '23', title: 'Sales Ethics Policy', completed: false },
      { id: '24', title: 'Data Privacy & Security', completed: false },
      { id: '25', title: 'Accurate Representations', completed: false },
    ],
  },
]

export default function CanadaPortalTrainingPage() {
  const [expandedId, setExpandedId] = useState<string | null>('onboarding')
  const [completedLessons, setCompletedLessons] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem('meridian_ca_training_progress')
      if (stored) return new Set(JSON.parse(stored) as string[])
    } catch { /* fall through to defaults */ }
    const initial = new Set<string>()
    MODULES.forEach(m => m.lessons.forEach(l => { if (l.completed) initial.add(l.id) }))
    return initial
  })

  const totalLessons = MODULES.reduce((s, m) => s + m.lessons.length, 0)
  const completedCount = completedLessons.size
  const progressPct = Math.round((completedCount / totalLessons) * 100)

  function toggleLesson(lessonId: string) {
    setCompletedLessons(prev => {
      const next = new Set(prev)
      if (next.has(lessonId)) next.delete(lessonId)
      else next.add(lessonId)
      try { localStorage.setItem('meridian_ca_training_progress', JSON.stringify([...next])) } catch { /* quota */ }
      return next
    })
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[#F5F5F7]">Training</h1>
        <p className="text-sm text-[#A1A1A8] mt-0.5">Level up your sales skills with guided modules.</p>
      </div>

      <div className="card border border-[#1F1F23] p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart3 size={16} className="text-[#17C5B0]" />
            <span className="text-sm font-semibold text-[#F5F5F7]">Your Progress</span>
          </div>
          <span className="text-sm font-bold text-[#17C5B0]">{progressPct}%</span>
        </div>
        <div className="w-full h-2 bg-[#1F1F23] rounded-full overflow-hidden">
          <div className="h-full bg-[#17C5B0] rounded-full transition-all duration-500" style={{ width: `${progressPct}%` }} />
        </div>
        <p className="text-[10px] text-[#A1A1A8]/40 mt-2">{completedCount} of {totalLessons} lessons completed</p>
      </div>

      <div className="space-y-3">
        {MODULES.map(mod => {
          const modCompleted = mod.lessons.filter(l => completedLessons.has(l.id)).length
          const isExpanded = expandedId === mod.id
          const Icon = mod.icon

          return (
            <div key={mod.id} className="card border border-[#1F1F23] overflow-hidden">
              <button
                onClick={() => setExpandedId(isExpanded ? null : mod.id)}
                className="w-full px-4 sm:px-5 py-4 flex items-center gap-3 text-left hover:bg-[#111113] transition-colors"
              >
                <div className="w-9 h-9 rounded-lg bg-[#7C5CFF]/10 border border-[#7C5CFF]/20 flex items-center justify-center flex-shrink-0">
                  <Icon size={16} className="text-[#7C5CFF]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-[11px] font-semibold text-[#F5F5F7]">{mod.title}</p>
                    <span className="text-[9px] text-[#A1A1A8]/30 bg-[#1F1F23] px-1.5 py-0.5 rounded">{mod.category}</span>
                  </div>
                  <p className="text-[10px] text-[#A1A1A8]/50 truncate mt-0.5">{mod.description}</p>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <p className="text-[10px] font-medium text-[#A1A1A8]">{modCompleted}/{mod.lessons.length}</p>
                    <p className="text-[9px] text-[#A1A1A8]/30">{mod.duration}</p>
                  </div>
                  <ChevronRight size={14} className={clsx('text-[#A1A1A8]/30 transition-transform', isExpanded && 'rotate-90')} />
                </div>
              </button>

              {isExpanded && (
                <div className="border-t border-[#1F1F23]">
                  {mod.lessons.map((lesson, i) => (
                    <button
                      key={lesson.id}
                      onClick={() => toggleLesson(lesson.id)}
                      className={clsx(
                        'w-full px-5 py-3 flex items-center gap-3 text-left transition-colors',
                        i < mod.lessons.length - 1 && 'border-b border-[#1F1F23]/50',
                        'hover:bg-[#111113]',
                      )}
                    >
                      {completedLessons.has(lesson.id) ? (
                        <CheckCircle2 size={16} className="text-[#17C5B0] flex-shrink-0" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-[#1F1F23] flex-shrink-0" />
                      )}
                      <span className={clsx(
                        'text-[11px] font-medium',
                        completedLessons.has(lesson.id) ? 'text-[#A1A1A8]/50 line-through' : 'text-[#F5F5F7]'
                      )}>
                        {lesson.title}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
