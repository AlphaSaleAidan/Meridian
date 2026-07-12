import { useParams, Link } from 'react-router-dom'
import { ChevronRight, ArrowRight } from 'lucide-react'
import SEO from '@/components/SEO'
import { findCity, findIndustry, ALL_CITIES, INDUSTRIES } from '@/data/seo-cities'

export default function CityIndustryPage() {
  const { industry: industrySlug, citySlug } = useParams<{ industry: string; citySlug: string }>()
  const city = findCity(citySlug || '')
  const industry = findIndustry(industrySlug || '')

  if (!city || !industry) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-[#F5F5F7] mb-2">Page Not Found</h1>
          <Link to="/" className="text-[#1A8FD6] hover:underline">Back to Home</Link>
        </div>
      </div>
    )
  }

  const pricing = city.country === 'CA' ? 'CA$339' : '$250'

  const faqItems = [
    {
      q: `Is Meridian available for ${industry.plural.toLowerCase()} in ${city.city}?`,
      a: `Yes, Meridian is available to all ${industry.plural.toLowerCase()} in ${city.city}, ${city.region}. Connect your POS system and get AI-powered analytics within minutes. Meridian supports Square, Toast, Clover, and 75+ other POS systems used by ${city.city} businesses.`,
    },
    {
      q: `How much does ${industry.label.toLowerCase()} analytics cost in ${city.city}?`,
      a: `Meridian starts at ${pricing}/month for the Standard plan, with a free first month and no contracts. The Premium plan (${city.country === 'CA' ? 'CA$675' : '$490'}/mo) adds camera intelligence and customer segmentation.`,
    },
    {
      q: `What POS systems do ${industry.plural.toLowerCase()} in ${city.city} use?`,
      a: `${industry.plural} in ${city.city} commonly use Square, ${city.country === 'CA' ? 'Moneris, ' : ''}Toast, and Clover. Meridian works with all of these plus 75+ other POS systems, connecting via OAuth in under 5 minutes.`,
    },
    {
      q: `How long does it take to set up Meridian for my ${industry.label.toLowerCase()} in ${city.city}?`,
      a: `Most ${industry.plural.toLowerCase()} in ${city.city} are connected in under 10 minutes. Authorize your POS via OAuth, and Meridian immediately starts importing your transaction history. First AI insights appear within 24 hours.`,
    },
    {
      q: `Does Meridian comply with ${city.country === 'CA' ? 'Canadian privacy laws' : `${city.region} data regulations`}?`,
      a: city.country === 'CA'
        ? `Yes. Meridian is fully compliant with PIPEDA and ${city.region === 'QC' ? 'Quebec Law 25' : 'all provincial privacy regulations'}. Customer data is processed securely and never shared with third parties.`
        : `Yes. Meridian follows all applicable US data protection standards. Customer data is encrypted, processed securely, and never shared with third parties.`,
    },
  ]

  const faqJsonLd = {
    '@type': 'FAQPage' as const,
    mainEntity: faqItems.map(f => ({
      '@type': 'Question' as const,
      name: f.q,
      acceptedAnswer: { '@type': 'Answer' as const, text: f.a },
    })),
  }

  const nearbyCities = city.nearby
    .map(slug => ALL_CITIES.find(c => c.slug === slug))
    .filter((c): c is NonNullable<typeof c> => c != null)

  return (
    <div className="min-h-screen bg-[#0A0A0B]">
      <SEO
        title={`${industry.label} Analytics Software in ${city.city}, ${city.region} | Meridian`}
        description={`AI-powered POS analytics for ${industry.plural.toLowerCase()} in ${city.city}, ${city.region}. Revenue forecasts, anomaly detection, and customer insights. Starting at ${pricing}/mo. First month free.`}
        path={`/analytics/${industry.slug}/${city.slug}`}
        jsonLd={[faqJsonLd]}
      />

      {/* Breadcrumb */}
      <nav className="border-b border-[#1F1F23] px-6 py-3">
        <div className="max-w-5xl mx-auto flex items-center gap-2 text-xs text-[#A1A1A8]">
          <Link to="/" className="hover:text-[#F5F5F7]">Meridian</Link>
          <ChevronRight size={12} />
          <Link to={`/for/${industry.slug}`} className="hover:text-[#F5F5F7]">{industry.plural}</Link>
          <ChevronRight size={12} />
          <span className="text-[#F5F5F7]">{city.city}, {city.region}</span>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-16 pb-12 text-center">
        <h1 className="text-3xl sm:text-4xl font-bold text-[#F5F5F7] mb-4">
          {industry.label} Analytics Software in {city.city}, {city.region}
        </h1>
        <p className="text-lg text-[#A1A1A8] max-w-2xl mx-auto mb-8">
          {industry.label} owners in {city.city} are using Meridian's AI to uncover hidden revenue,
          optimize staffing, and make smarter decisions — all from their existing POS data.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 px-6 py-3 bg-[#17C5B0] text-[#0A0A0B] font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all"
        >
          See a Live Demo <ArrowRight size={16} />
        </Link>
      </section>

      {/* Pain Points */}
      <section className="max-w-4xl mx-auto px-6 py-12">
        <h2 className="text-xl font-bold text-[#F5F5F7] mb-6">
          What {industry.label} Owners in {city.city} Struggle With
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {industry.painPoints.map((point, i) => (
            <div key={i} className="p-4 rounded-xl bg-[#111113] border border-[#1F1F23]">
              <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center mb-3">
                <span className="text-red-400 text-sm font-bold">{i + 1}</span>
              </div>
              <p className="text-sm text-[#A1A1A8]">{point}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-4xl mx-auto px-6 py-12">
        <h2 className="text-xl font-bold text-[#F5F5F7] mb-6">
          What Meridian Does for {industry.plural} in {city.city}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {industry.features.map((feature, i) => (
            <div key={i} className="p-4 rounded-xl bg-[#111113] border border-[#1F1F23] flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-[#17C5B0] text-xs font-bold">{'✓'}</span>
              </div>
              <p className="text-sm text-[#F5F5F7]">{feature}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="max-w-4xl mx-auto px-6 py-12">
        <h2 className="text-xl font-bold text-[#F5F5F7] mb-6">Get Started in 3 Steps</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            { step: '1', title: 'Connect Your POS', desc: 'Authorize your Square, Toast, Clover, or any of 80+ POS systems. Takes under 5 minutes.' },
            { step: '2', title: 'AI Analyzes Your Data', desc: "Meridian's 41-agent AI swarm processes your transaction history and starts generating insights." },
            { step: '3', title: 'Get Actionable Insights', desc: 'See revenue forecasts, anomaly alerts, and recommendations in plain English within 24 hours.' },
          ].map(s => (
            <div key={s.step} className="text-center">
              <div className="w-10 h-10 rounded-full bg-[#1A8FD6]/10 text-[#1A8FD6] font-bold text-lg flex items-center justify-center mx-auto mb-3">
                {s.step}
              </div>
              <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">{s.title}</h3>
              <p className="text-xs text-[#A1A1A8]">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <h2 className="text-xl font-bold text-[#F5F5F7] mb-6">
          Frequently Asked Questions — {industry.plural} in {city.city}
        </h2>
        <div className="space-y-4">
          {faqItems.map(({ q, a }) => (
            <details key={q} className="group">
              <summary className="cursor-pointer text-sm font-semibold text-[#F5F5F7] flex items-center justify-between py-3 border-b border-[#1F1F23]">
                {q}
                <ChevronRight size={16} className="text-[#A1A1A8] transition-transform group-open:rotate-90 flex-shrink-0 ml-2" />
              </summary>
              <p className="text-sm text-[#A1A1A8] leading-relaxed pt-3 pb-4">{a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-6 py-16 text-center">
        <h2 className="text-2xl font-bold text-[#F5F5F7] mb-3">
          Ready to Transform Your {industry.label} in {city.city}?
        </h2>
        <p className="text-[#A1A1A8] mb-6">First month free. No contracts. Cancel anytime.</p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 px-8 py-3 bg-[#17C5B0] text-[#0A0A0B] font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all text-lg"
        >
          Start Your Free Month <ArrowRight size={18} />
        </Link>
      </section>

      {/* Nearby Cities */}
      {nearbyCities.length > 0 && (
        <section className="max-w-4xl mx-auto px-6 pb-12">
          <h2 className="text-sm font-semibold text-[#A1A1A8] mb-3">
            {industry.label} Analytics in Nearby Cities
          </h2>
          <div className="flex flex-wrap gap-2">
            {nearbyCities.map(nc => (
              <Link
                key={nc.slug}
                to={`/analytics/${industry.slug}/${nc.slug}`}
                className="px-3 py-1.5 text-xs text-[#1A8FD6] bg-[#1A8FD6]/10 rounded-lg hover:bg-[#1A8FD6]/20 transition-colors"
              >
                {nc.city}, {nc.region}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Other Industries */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <h2 className="text-sm font-semibold text-[#A1A1A8] mb-3">
          Other Industries in {city.city}
        </h2>
        <div className="flex flex-wrap gap-2">
          {INDUSTRIES.filter(i => i.slug !== industry.slug).map(i => (
            <Link
              key={i.slug}
              to={`/analytics/${i.slug}/${city.slug}`}
              className="px-3 py-1.5 text-xs text-[#A1A1A8] bg-[#111113] border border-[#1F1F23] rounded-lg hover:text-[#F5F5F7] transition-colors"
            >
              {i.plural} in {city.city}
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
