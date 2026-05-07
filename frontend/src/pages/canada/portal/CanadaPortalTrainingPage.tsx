import { useState } from 'react'
import {
  GraduationCap, Play, CheckCircle2, Clock, ChevronRight,
  BookOpen, Target, Users, Zap, Shield, BarChart3,
  Camera, Lightbulb, Plug,
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
  {
    id: 'camera',
    title: 'Camera Intelligence Setup',
    description: 'How to sell and configure Meridian Vision for foot traffic and queue analytics.',
    icon: Camera,
    duration: '30 min',
    category: 'Product Knowledge',
    lessons: [
      { id: '26', title: 'What is Camera Intelligence?', completed: false },
      { id: '27', title: 'Hardware Requirements & Placement', completed: false },
      { id: '28', title: 'PIPEDA Compliance & Privacy Signage', completed: false },
      { id: '29', title: 'Configuring Zones & Alerts', completed: false },
      { id: '30', title: 'Selling the ROI to Prospects', completed: false },
    ],
  },
  {
    id: 'quicktips',
    title: 'Quick Tips',
    description: 'Bite-sized tips for everyday selling in the Canadian market.',
    icon: Lightbulb,
    duration: '15 min',
    category: 'Quick Reference',
    lessons: [
      { id: '31', title: 'Pricing in CAD — Handling Currency Questions', completed: false },
      { id: '32', title: 'Canadian Payment Processing Landscape', completed: false },
      { id: '33', title: 'Provincial Tax Differences (GST/HST/PST)', completed: false },
      { id: '34', title: 'Seasonal Sales Patterns in Canada', completed: false },
    ],
  },
  {
    id: 'pos-guides',
    title: 'POS Connection Guides',
    description: 'Step-by-step guides for connecting major Canadian POS systems.',
    icon: Plug,
    duration: '25 min',
    category: 'Technical',
    lessons: [
      { id: '35', title: 'Moneris Integration Walkthrough', completed: false },
      { id: '36', title: 'Square Canada Setup', completed: false },
      { id: '37', title: 'Clover Canada Configuration', completed: false },
      { id: '38', title: 'Troubleshooting POS Connections', completed: false },
    ],
  },
]

// Section groupings
const SECTIONS = [
  {
    title: 'How to Sell a Deal (5-Step SOP)',
    description: 'Follow these steps from first contact to closed deal.',
    moduleIds: ['onboarding', 'pitch', 'demo'],
  },
  {
    title: 'Sales Knowledge',
    description: 'Deepen your expertise across verticals and techniques.',
    moduleIds: ['verticals', 'advanced'],
  },
  {
    title: 'Compliance & Ethics',
    description: 'Required training for all sales representatives.',
    moduleIds: ['compliance'],
  },
  {
    title: 'Product Deep Dives',
    description: 'Technical knowledge for Camera Intelligence and POS integrations.',
    moduleIds: ['camera', 'pos-guides'],
  },
  {
    title: 'Quick Reference',
    description: 'Handy tips for the Canadian market.',
    moduleIds: ['quicktips'],
  },
]

export default function CanadaPortalTrainingPage() {
  const [expandedId, setExpandedId] = useState<string | null>('onboarding')
  const [completedLessons, setCompletedLessons] = useState<Set<string>>(() => {
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
      return next
    })
  }

  function getDurationMinutes(duration: string): number {
    const match = duration.match(/(\d+)/)
    return match ? parseInt(match[1]) : 0
  }

  function getLessonTime(mod: Module): string {
    const totalMin = getDurationMinutes(mod.duration)
    const perLesson = Math.round(totalMin / mod.lessons.length)
    return `${perLesson} min`
  }

  // Track step numbers across sections
  let globalStep = 0

  return (
    <div className="min-h-screen bg-[#0a0f0d] space-y-6 p-1">
      <div>
        <h1 className="text-xl font-bold text-white">Training</h1>
        <p className="text-sm text-[#6b7a74] mt-0.5">Level up your sales skills with guided modules.</p>
      </div>

      {/* Progress Section */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart3 size={16} className="text-[#00d4aa]" />
            <span className="text-sm font-semibold text-white">Your Progress</span>
          </div>
          <span className="text-sm font-bold text-[#00d4aa]">{progressPct}%</span>
        </div>
        <div className="w-full h-2 bg-[#1a2420] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#00d4aa] rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <p className="text-[10px] text-[#4a5550] mt-2">
          {completedCount} of {totalLessons} lessons completed
        </p>
      </div>

      {/* Sections */}
      {SECTIONS.map((section) => {
        const sectionModules = section.moduleIds.map(id => MODULES.find(m => m.id === id)!).filter(Boolean)

        return (
          <div key={section.title} className="space-y-3">
            <div className="mb-2">
              <h2 className="text-[14px] font-semibold text-white">{section.title}</h2>
              <p className="text-[11px] text-[#6b7a74] mt-0.5">{section.description}</p>
            </div>

            {sectionModules.map(mod => {
              globalStep++
              const stepNum = globalStep
              const modCompleted = mod.lessons.filter(l => completedLessons.has(l.id)).length
              const isExpanded = expandedId === mod.id
              const Icon = mod.icon

              return (
                <div key={mod.id} className="bg-[#0f1512] border border-[#1a2420] rounded-xl overflow-hidden">
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : mod.id)}
                    className="w-full px-4 sm:px-5 py-4 flex items-center gap-3 text-left hover:bg-[#0f1512]/80 transition-colors"
                  >
                    {/* Step number badge */}
                    <div className="w-7 h-7 rounded-full bg-[#00d4aa]/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-[11px] font-bold text-[#00d4aa]">{stepNum}</span>
                    </div>

                    {/* Module icon */}
                    <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center flex-shrink-0">
                      <Icon size={16} className="text-[#00d4aa]" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] font-semibold text-white">{mod.title}</p>
                      <p className="text-[10px] text-[#6b7a74] truncate mt-0.5">{mod.description}</p>
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      <div className="text-right">
                        <p className="text-[10px] font-medium text-[#6b7a74]">
                          {modCompleted}/{mod.lessons.length} lessons
                        </p>
                        <p className="text-[9px] text-[#4a5550]">{mod.duration}</p>
                      </div>
                      <ChevronRight
                        size={14}
                        className={clsx(
                          'text-[#4a5550] transition-transform',
                          isExpanded && 'rotate-90'
                        )}
                      />
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="border-t border-[#1a2420]">
                      {mod.lessons.map((lesson, i) => {
                        const lessonTime = getLessonTime(mod)
                        return (
                          <button
                            key={lesson.id}
                            onClick={() => toggleLesson(lesson.id)}
                            className={clsx(
                              'w-full px-5 py-3 flex items-center gap-3 text-left transition-colors',
                              i < mod.lessons.length - 1 && 'border-b border-[#1a2420]/50',
                              'hover:bg-[#1a2420]/30',
                            )}
                          >
                            {completedLessons.has(lesson.id) ? (
                              <CheckCircle2 size={16} className="text-[#00d4aa] flex-shrink-0" />
                            ) : (
                              <div className="w-4 h-4 rounded-full border border-[#1a2420] flex-shrink-0" />
                            )}
                            <span
                              className={clsx(
                                'text-[11px] font-medium flex-1',
                                completedLessons.has(lesson.id) ? 'text-[#6b7a74]' : 'text-white'
                              )}
                            >
                              {lesson.title}
                            </span>
                            <span className="text-[9px] text-[#4a5550]">{lessonTime}</span>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}
