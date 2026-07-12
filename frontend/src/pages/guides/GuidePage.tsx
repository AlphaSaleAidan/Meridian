import { useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ArrowRight, ChevronDown, ChevronRight, Lightbulb, BookOpen } from 'lucide-react'
import SEO from '@/components/SEO'
import { getGuideBySlug, guides, isGuidePublished } from '@/data/seo-guides'
import type { GuideData } from '@/data/seo-guides'

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="w-full flex items-center justify-between p-5 text-left hover:bg-[#111113] transition-colors"
      >
        <span className="text-[#F5F5F7] font-medium text-[15px] pr-4">{q}</span>
        <ChevronDown size={18} className={`text-[#6B7280] flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {/* Answer stays in the DOM at all times (collapsed via CSS grid, not unmounted)
          so crawlers and AI engines can read the Q&A text even when visually closed. */}
      <div className={`grid transition-all duration-200 ease-out ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
        <div className="overflow-hidden">
          <div className="px-5 pb-5 text-[#A1A1A8] text-[14px] leading-relaxed border-t border-[#1F1F23] pt-4">
            {a}
          </div>
        </div>
      </div>
    </div>
  )
}

function buildJsonLd(guide: GuideData) {
  return [
    {
      '@type': 'Article',
      headline: guide.seoTitle.replace(' | Meridian', ''),
      description: guide.description,
      image: 'https://meridian.tips/og-image.png',
      inLanguage: guide.slug.includes('canada') || guide.slug.includes('pipeda') || guide.slug.includes('quebec') ? 'en-CA' : 'en-US',
      author: { '@type': 'Person', name: 'Aidan Pierce', jobTitle: 'Founder & CEO', url: 'https://meridian.tips/about' },
      publisher: {
        '@type': 'Organization',
        name: 'Meridian',
        url: 'https://meridian.tips/',
        logo: { '@type': 'ImageObject', url: 'https://meridian.tips/meridian-icon.svg' },
      },
      datePublished: guide.datePublished,
      dateModified: guide.datePublished,
      isAccessibleForFree: true,
      mainEntityOfPage: { '@type': 'WebPage', '@id': `https://meridian.tips/guides/${guide.slug}` },
      // Voice/assistant + AI-answer signal: the headline and self-contained summary.
      speakable: { '@type': 'SpeakableSpecification', cssSelector: ['h1', '.guide-summary'] },
    },
    {
      '@type': 'FAQPage',
      mainEntity: guide.faqs.map(item => ({
        '@type': 'Question',
        name: item.q,
        acceptedAnswer: { '@type': 'Answer', text: item.a },
      })),
    },
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://meridian.tips/' },
        { '@type': 'ListItem', position: 2, name: 'Guides', item: 'https://meridian.tips/guides' },
        { '@type': 'ListItem', position: 3, name: guide.heroTitle + ' ' + guide.heroAccent, item: `https://meridian.tips/guides/${guide.slug}` },
      ],
    },
  ]
}

export default function GuidePage() {
  const { slug } = useParams<{ slug: string }>()
  const guide = slug ? getGuideBySlug(slug) : undefined

  // Scheduled-but-unreleased guides behave as if they don't exist yet.
  if (!guide || !isGuidePublished(guide)) return <Navigate to="/guides" replace />

  const jsonLd = buildJsonLd(guide)

  const visibleRelatedLinks = guide.relatedLinks.filter(link => {
    const m = link.to.match(/^\/guides\/(.+)$/)
    if (!m) return true
    const target = getGuideBySlug(m[1])
    return !!target && isGuidePublished(target)
  })

  return (
    <>
      <SEO title={guide.seoTitle} description={guide.description} path={`/guides/${guide.slug}`} jsonLd={jsonLd} />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        {/* Breadcrumbs */}
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-4">
          <nav className="flex items-center gap-1.5 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8] transition-colors">Home</Link>
            <ChevronRight size={12} />
            <Link to="/guides" className="hover:text-[#A1A1A8] transition-colors">Guides</Link>
            <ChevronRight size={12} />
            <span className="text-[#A1A1A8] truncate">{guide.heroTitle} {guide.heroAccent}</span>
          </nav>
        </div>

        {/* Hero */}
        <header className="max-w-3xl mx-auto px-4 sm:px-6 pb-12">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight leading-[1.1]">
            {guide.heroTitle}{' '}
            <span className="bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] bg-clip-text text-transparent">
              {guide.heroAccent}
            </span>
          </h1>
          <p className="guide-summary mt-5 text-lg text-[#A1A1A8] leading-relaxed max-w-2xl">{guide.heroDescription}</p>
          <div className="mt-6 flex items-center gap-3 text-[12px] text-[#6B7280]">
            <span>By <Link to="/about" className="text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">Aidan Pierce</Link>, Founder</span>
            <span className="w-1 h-1 rounded-full bg-[#6B7280]" />
            <BookOpen size={14} />
            <span>{Math.ceil(guide.sections.length * 1.5)} min read</span>
            <span className="w-1 h-1 rounded-full bg-[#6B7280]" />
            <span>Updated {new Date(guide.datePublished).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</span>
          </div>
        </header>

        {/* Content */}
        <article className="max-w-3xl mx-auto px-4 sm:px-6 pb-16 space-y-12">
          {guide.sections.map((section, i) => (
            <section key={i}>
              <h2 className="text-xl sm:text-2xl font-bold text-[#F5F5F7] mb-4">{section.title}</h2>
              {section.stat && (
                <div className="mb-5 inline-flex items-baseline gap-2 px-4 py-2.5 rounded-lg bg-[#111113] border border-[#1F1F23]">
                  <span className="text-2xl font-bold text-[#17C5B0] font-mono">{section.stat.value}</span>
                  <span className="text-[13px] text-[#A1A1A8]">{section.stat.label}</span>
                </div>
              )}
              {section.paragraphs.map((p, j) => (
                <p key={j} className="text-[#D1D1D6] text-[15px] leading-[1.75] mb-4">{p}</p>
              ))}
              {section.tip && (
                <div className="mt-4 flex gap-3 p-4 rounded-lg bg-[#17C5B0]/5 border border-[#17C5B0]/20">
                  <Lightbulb size={18} className="text-[#17C5B0] flex-shrink-0 mt-0.5" />
                  <p className="text-[14px] text-[#D1D1D6] leading-relaxed"><span className="font-semibold text-[#17C5B0]">Pro tip:</span> {section.tip}</p>
                </div>
              )}
            </section>
          ))}
        </article>

        {/* FAQ */}
        <section className="max-w-3xl mx-auto px-4 sm:px-6 pb-16">
          <h2 className="text-2xl font-bold text-[#F5F5F7] mb-6">Frequently Asked Questions</h2>
          <div className="space-y-3">
            {guide.faqs.map((faq, i) => <FAQItem key={i} q={faq.q} a={faq.a} />)}
          </div>
        </section>

        {/* Related Links */}
        {visibleRelatedLinks.length > 0 && (
        <section className="max-w-3xl mx-auto px-4 sm:px-6 pb-16">
          <h3 className="text-lg font-semibold text-[#F5F5F7] mb-4">Related Guides</h3>
          <div className="flex flex-wrap gap-2">
            {visibleRelatedLinks.map(link => (
              <Link
                key={link.to}
                to={link.to}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors"
              >
                {link.label}
                <ChevronRight size={12} />
              </Link>
            ))}
          </div>
        </section>
        )}

        {/* CTA */}
        <section className="py-20 border-t border-[#1F1F23]/40 relative">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-[0.06]" style={{ background: 'radial-gradient(circle, #1A8FD6 0%, transparent 70%)' }} />
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center relative">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#F5F5F7] tracking-tight">{guide.ctaHeadline}</h2>
            <p className="mt-4 text-[#A1A1A8] text-[15px] leading-relaxed max-w-lg mx-auto">{guide.ctaDescription}</p>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                to="/onboard"
                className="group px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-all duration-200 inline-flex items-center gap-2"
              >
                Get Started Free <ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link
                to="/demo"
                className="px-6 py-3 text-[14px] font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:border-[#2A2A30] hover:text-[#F5F5F7] transition-all duration-200"
              >
                See Live Demo
              </Link>
            </div>
            <p className="mt-4 text-[11px] text-[#6B7280]">No credit card required · 45-second setup · Cancel anytime</p>
          </div>
        </section>

        {/* Footer nav */}
        <footer className="border-t border-[#1F1F23]/40 py-8">
          <div className="max-w-3xl mx-auto px-4 sm:px-6">
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#6B7280]">
              <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
              <Link to="/guides" className="hover:text-[#A1A1A8]">All Guides</Link>
              <Link to="/about" className="hover:text-[#A1A1A8]">About</Link>
              <Link to="/blog" className="hover:text-[#A1A1A8]">Blog</Link>
              <Link to="/for/restaurants" className="hover:text-[#A1A1A8]">For Restaurants</Link>
              <Link to="/for/coffee-shops" className="hover:text-[#A1A1A8]">For Coffee Shops</Link>
              <Link to="/onboard" className="hover:text-[#A1A1A8]">Get Started</Link>
            </div>
            <p className="mt-4 text-[11px] text-[#6B7280]/50">© 2026 Meridian. AI-powered POS analytics.</p>
          </div>
        </footer>
      </div>
    </>
  )
}
