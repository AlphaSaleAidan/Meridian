import { Link } from 'react-router-dom'
import { ArrowRight, ChevronRight, ShieldCheck, MapPin, Cpu } from 'lucide-react'
import SEO from '@/components/SEO'

/**
 * Owned founder / about page — the primary entity property for the query
 * "Aidan Pierce" and "Meridian founder". Person + Organization(founder) schema
 * builds the knowledge-graph entity.
 *
 * COPY IS EDITABLE: everything user-facing is in FOUNDER below. Keep claims
 * strictly true — do not add credentials, history, or metrics that aren't verifiable.
 * TODO(aidan): add a real headshot at /public/team/aidan-pierce.jpg and fill `sameAs`
 * with your LinkedIn / X profile URLs (left empty rather than guessed).
 */
const FOUNDER = {
  name: 'Aidan Pierce',
  title: 'Founder & CEO',
  org: 'Meridian Intelligence',
  // Verifiable, minimal bio — describes what Meridian is and the build choices.
  bio: [
    'Aidan Pierce is the founder and CEO of Meridian Intelligence. He started Meridian to give independent restaurants, cafés, auto shops, and retailers the kind of analytics that large chains take for granted — connected directly to the point-of-sale systems they already run, with plain-English insights instead of dashboards nobody reads.',
    'He built Meridian compliance-first for the Canadian market: CAD pricing, Canadian POS integrations like Moneris, and PIPEDA and Quebec Law 25 alignment designed into the product from the start rather than bolted on later. The goal is simple — let an owner connect their POS in a few minutes and start seeing where revenue is leaking, where it can grow, and what to do next.',
  ],
  // sameAs intentionally left for Aidan to fill with profiles he wants public.
  sameAs: [] as string[],
  photo: '/team/aidan-pierce.jpg', // optional; page degrades gracefully if absent
}

const PRINCIPLES = [
  {
    icon: ShieldCheck,
    title: 'Compliance-first, not compliance-later',
    body: 'PIPEDA and Quebec Law 25 alignment and Canadian data residency are part of the product design, not an afterthought — because trust is the foundation of handing over your transaction data.',
  },
  {
    icon: MapPin,
    title: 'Built for the Canadian market',
    body: 'CAD pricing, Canadian POS systems like Moneris and Alice POS, and a dedicated Canadian portal — one of the earliest analytics platforms adapted for Canada from the ground up.',
  },
  {
    icon: Cpu,
    title: 'Insights an owner can act on',
    body: 'Connect your POS and Meridian turns raw transactions into plain-English revenue insights, anomaly alerts, and forecasts — the kind of intelligence that used to require a data team.',
  },
]

function buildJsonLd() {
  // @id matches the global Organization graph in index.html so Google resolves the
  // founder/CEO relationship into a single entity across the whole site.
  const person = {
    '@type': 'Person',
    '@id': 'https://meridian.tips/#aidan-pierce',
    name: FOUNDER.name,
    jobTitle: FOUNDER.title,
    url: 'https://meridian.tips/about',
    description: `${FOUNDER.name} is the founder and CEO of ${FOUNDER.org}, a compliance-first POS analytics platform for Canadian businesses.`,
    // disambiguatingDescription separates this Aidan Pierce from same-name entities Google
    // already resolves (notably Brett Pierce / "Meridian Stories", and 100+ unrelated "Aidan
    // Pierce" profiles). schema.org's purpose-built property for name-collision disambiguation.
    disambiguatingDescription:
      `Founder and CEO of Meridian Intelligence (meridian.tips), the POS analytics company — ` +
      `not affiliated with Meridian Stories or any other Meridian-named organization.`,
    knowsAbout: ['POS analytics', 'restaurant revenue intelligence', 'PIPEDA compliance', 'small business analytics'],
    worksFor: { '@id': 'https://meridian.tips/#organization' },
    ...(FOUNDER.sameAs.length ? { sameAs: FOUNDER.sameAs } : {}),
  }
  return [
    {
      '@type': 'AboutPage',
      name: `About ${FOUNDER.org}`,
      url: 'https://meridian.tips/about',
      mainEntity: { '@id': 'https://meridian.tips/#aidan-pierce' },
    },
    person,
    {
      '@type': 'Organization',
      '@id': 'https://meridian.tips/#organization',
      name: FOUNDER.org,
      alternateName: ['Meridian AI Business Solutions', 'Meridian AI'],
      url: 'https://meridian.tips/',
      logo: { '@type': 'ImageObject', url: 'https://meridian.tips/meridian-icon.svg' },
      founder: { '@id': 'https://meridian.tips/#aidan-pierce' },
      areaServed: ['CA', 'US'],
    },
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://meridian.tips/' },
        { '@type': 'ListItem', position: 2, name: 'About', item: 'https://meridian.tips/about' },
      ],
    },
  ]
}

export default function FounderPage() {
  return (
    <>
      <SEO
        title={`About Meridian — Founded by ${FOUNDER.name}, ${FOUNDER.title} | Meridian`}
        description={`Meet ${FOUNDER.name}, founder and CEO of Meridian Intelligence — the compliance-first POS analytics platform built for Canadian restaurants, cafés, and retailers. Learn why Meridian was built Canada-first.`}
        path="/about"
        type="website"
        jsonLd={buildJsonLd()}
      />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        {/* Breadcrumbs */}
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-4">
          <nav className="flex items-center gap-1.5 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8] transition-colors">Home</Link>
            <ChevronRight size={12} />
            <span className="text-[#A1A1A8]">About</span>
          </nav>
        </div>

        {/* Hero */}
        <header className="max-w-3xl mx-auto px-4 sm:px-6 pb-12">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight leading-[1.1]">
            About{' '}
            <span className="bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] bg-clip-text text-transparent">
              Meridian Intelligence
            </span>
          </h1>
          <p className="guide-summary mt-5 text-lg text-[#A1A1A8] leading-relaxed max-w-2xl">
            Meridian Intelligence is a compliance-first POS analytics platform that connects to the
            point-of-sale systems Canadian businesses already use and turns their transactions into
            revenue insights, anomaly alerts, and forecasts — in plain English.
          </p>
        </header>

        {/* Founder */}
        <section className="max-w-3xl mx-auto px-4 sm:px-6 pb-16">
          <div className="rounded-2xl border border-[#1F1F23] bg-[#0E0E10] p-6 sm:p-8">
            <div className="flex items-start gap-5">
              <div className="hidden sm:flex w-16 h-16 rounded-full bg-gradient-to-br from-[#17C5B0]/20 to-[#1A8FD6]/20 border border-[#1F1F23] items-center justify-center text-xl font-bold text-[#17C5B0] flex-shrink-0">
                AP
              </div>
              <div>
                <h2 className="text-xl sm:text-2xl font-bold text-[#F5F5F7]">
                  {FOUNDER.name} — {FOUNDER.title}
                </h2>
                <p className="text-[13px] text-[#6B7280] mt-1">{FOUNDER.org}</p>
              </div>
            </div>
            <div className="mt-6 space-y-4">
              {FOUNDER.bio.map((p, i) => (
                <p key={i} className="text-[#D1D1D6] text-[15px] leading-[1.75]">{p}</p>
              ))}
            </div>
          </div>
        </section>

        {/* Principles */}
        <section className="max-w-3xl mx-auto px-4 sm:px-6 pb-16">
          <h2 className="text-2xl font-bold text-[#F5F5F7] mb-6">What Meridian is built on</h2>
          <div className="grid sm:grid-cols-3 gap-4">
            {PRINCIPLES.map(({ icon: Icon, title, body }) => (
              <div key={title} className="rounded-xl border border-[#1F1F23] bg-[#0E0E10] p-5">
                <Icon size={20} className="text-[#17C5B0]" />
                <h3 className="mt-3 text-[15px] font-semibold text-[#F5F5F7]">{title}</h3>
                <p className="mt-2 text-[13px] text-[#A1A1A8] leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 border-t border-[#1F1F23]/40 relative">
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center relative">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#F5F5F7] tracking-tight">
              See what Meridian finds in your numbers
            </h2>
            <p className="mt-4 text-[#A1A1A8] text-[15px] leading-relaxed max-w-lg mx-auto">
              Connect your POS in a few minutes and get your first insights free. No credit card required.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                to="/onboard"
                className="group px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-all duration-200 inline-flex items-center gap-2"
              >
                Get Started Free <ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link
                to="/canada"
                className="px-6 py-3 text-[14px] font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:border-[#2A2A30] hover:text-[#F5F5F7] transition-all duration-200"
              >
                Meridian for Canada
              </Link>
            </div>
          </div>
        </section>

        {/* Footer nav */}
        <footer className="border-t border-[#1F1F23]/40 py-8">
          <div className="max-w-3xl mx-auto px-4 sm:px-6">
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#6B7280]">
              <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
              <Link to="/about" className="hover:text-[#A1A1A8]">About</Link>
              <Link to="/guides" className="hover:text-[#A1A1A8]">Guides</Link>
              <Link to="/canada" className="hover:text-[#A1A1A8]">For Canada</Link>
              <Link to="/onboard" className="hover:text-[#A1A1A8]">Get Started</Link>
            </div>
            <p className="mt-4 text-[11px] text-[#6B7280]/50">© 2026 Meridian Intelligence. AI-powered POS analytics.</p>
          </div>
        </footer>
      </div>
    </>
  )
}
