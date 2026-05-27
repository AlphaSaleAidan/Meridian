import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, ChevronDown, ChevronRight, Phone, Globe, Mic, Monitor, MessageSquare, Clock, Sparkles } from 'lucide-react'
import SEO from '@/components/SEO'

const ACCENT = '#17C5B0'

const faqItems = [
  {
    q: 'How does the AI phone agent work?',
    a: 'When a customer calls your restaurant, the AI agent answers instantly and takes their order through natural conversation. It understands your full menu including modifications, sizes, combos, and special requests. Once the order is confirmed, it routes directly to your POS system and sends the customer an SMS payment link. The entire process takes under 2 minutes and requires zero staff involvement.',
  },
  {
    q: 'What languages does it support?',
    a: 'The AI phone agent supports 600+ languages and dialects with natural-sounding voice output. It automatically detects the caller\'s language and responds accordingly — no configuration needed. This means every customer who calls your restaurant is served in their native language, eliminating language barriers that cause lost orders.',
  },
  {
    q: 'Does it work with my POS system?',
    a: 'Yes. Meridian integrates with 80+ POS systems including Square, Toast, Clover, Lightspeed, TouchBistro, Aloha, Revel, and SpotOn. Orders placed through the phone agent appear in your POS exactly like any other order — no re-entry, no extra tablets, no workflow changes for your kitchen staff.',
  },
  {
    q: 'Can I customize the voice?',
    a: 'Absolutely. Meridian offers voice cloning so the AI agent can sound like your brand. You can choose from preset voices or clone a specific voice to match your restaurant\'s personality. The result is a consistent, professional phone experience that feels like a real member of your team.',
  },
  {
    q: 'What happens if the AI can\'t understand the caller?',
    a: 'The AI agent is trained to handle ambiguity gracefully. If it can\'t understand a request, it asks clarifying questions naturally — just like a human would. If the caller needs to speak with a person, the agent seamlessly transfers the call to your staff. You can also set up fallback rules for specific scenarios like catering orders or complaints.',
  },
]

const jsonLd = [
  {
    '@type': 'SoftwareApplication',
    name: 'Meridian AI Phone Agent',
    applicationCategory: 'BusinessApplication',
    description: 'AI-powered phone ordering agent for restaurants. Answers calls in 600+ languages, takes orders conversationally, routes to 80+ POS systems, and sends SMS payment links.',
    url: 'https://meridian.tips/features/phone-agent',
    offers: { '@type': 'Offer', price: '250', priceCurrency: 'USD' },
    provider: { '@type': 'Organization', name: 'Meridian Intelligence', url: 'https://meridian.tips' },
    operatingSystem: 'Cloud-based',
  },
  {
    '@type': 'FAQPage',
    mainEntity: faqItems.map(item => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  },
  {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://meridian.tips' },
      { '@type': 'ListItem', position: 2, name: 'Features', item: 'https://meridian.tips/features' },
      { '@type': 'ListItem', position: 3, name: 'AI Phone Agent', item: 'https://meridian.tips/features/phone-agent' },
    ],
  },
]

const transcript = [
  { from: 'ai', text: 'Thank you for calling Sunrise Coffee! What can I get started for you today?' },
  { from: 'customer', text: 'Hi, can I get a large cold brew and a blueberry muffin?' },
  { from: 'ai', text: 'Absolutely! One large cold brew and a blueberry muffin. Anything else?' },
  { from: 'customer', text: "That's it." },
  { from: 'ai', text: "Great — your total is $9.48. Would you like to pick up or have it delivered?" },
  { from: 'customer', text: 'Pickup please.' },
  { from: 'ai', text: "Perfect! I'm sending a payment link to your phone now. Your order will be ready in 10 minutes." },
]

const features = [
  { icon: Globe, title: '600+ Languages', desc: 'Serves any customer in their native language with natural voice. Auto-detects the caller\'s language — no configuration needed.' },
  { icon: Mic, title: 'Voice Cloning', desc: 'Clone your brand\'s voice so the AI sounds like your team. Choose presets or create a custom voice that matches your restaurant.' },
  { icon: Monitor, title: 'POS Integration', desc: 'Orders route directly to Square, Toast, Clover, and 77+ other POS systems. No re-entry, no extra tablets.' },
  { icon: MessageSquare, title: 'SMS Checkout', desc: 'Customer gets a payment link via text — no card over the phone needed. Faster, safer, and fewer order errors.' },
  { icon: Clock, title: '24/7 Coverage', desc: 'Never miss a call — even during rush hour, after hours, or holidays. Every ring is answered in under 2 seconds.' },
  { icon: Sparkles, title: 'Smart Menu Matching', desc: 'AI understands modifications, sizes, combos, and special requests. Handles complex orders as naturally as your best employee.' },
]

const posIntegrations = ['Square', 'Toast', 'Clover', 'Lightspeed', 'TouchBistro', 'Aloha', 'Revel', 'SpotOn']

function FAQ({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-5 text-left hover:bg-[#111113] transition-colors">
        <span className="text-[#F5F5F7] font-medium text-[15px] pr-4">{q}</span>
        <ChevronDown size={18} className={`text-[#6B7280] flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="px-5 pb-5 text-[#A1A1A8] text-[14px] leading-relaxed border-t border-[#1F1F23] pt-4">{a}</div>}
    </div>
  )
}

export default function PhoneAgentPage() {
  return (
    <>
      <SEO
        title="AI Phone Ordering Agent for Restaurants — Never Miss a Call | Meridian"
        description="AI-powered phone ordering that takes orders in 600+ languages, routes to your POS, and sends SMS payment links. 24/7 coverage, no staff needed. Included in all Meridian plans."
        path="/features/phone-agent"
        jsonLd={jsonLd}
      />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        {/* Breadcrumb */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-24 pb-4">
          <nav className="flex items-center gap-1.5 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <ChevronRight size={12} />
            <span className="text-[#6B7280]">Features</span>
            <ChevronRight size={12} />
            <span className="text-[#A1A1A8]">AI Phone Agent</span>
          </nav>
        </div>

        {/* Hero */}
        <header className="max-w-4xl mx-auto px-4 sm:px-6 pb-12 text-center">
          <div className="flex justify-center mb-5">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${ACCENT}15` }}>
              <Phone size={28} style={{ color: ACCENT }} />
            </div>
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold tracking-tight mb-3">
            AI Phone Agent
          </h1>
          <p className="text-xl sm:text-2xl font-semibold mb-4" style={{ color: ACCENT }}>
            Never Miss Another Order
          </p>
          <p className="text-[#A1A1A8] text-[16px] sm:text-[17px] leading-relaxed max-w-2xl mx-auto mb-8">
            Your AI assistant answers every call, takes orders in 600+ languages, and routes them directly to your POS — 24/7, no staff needed.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/onboard" className="inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors">
              Get Started Free <ArrowRight size={15} />
            </Link>
            <Link to="/demo" className="inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors">
              Watch Demo
            </Link>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 sm:px-6 pb-16">
          {/* How It Works */}
          <section className="mb-16">
            <h2 className="text-xl font-bold mb-8 text-center">How It Works</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { step: '1', title: 'Customer Calls', desc: 'A customer dials your restaurant phone number — same number you already use.' },
                { step: '2', title: 'AI Takes the Order', desc: 'The AI agent answers instantly and takes their order through natural conversation.' },
                { step: '3', title: 'Order + Payment', desc: 'Order appears in your POS and the customer gets an SMS payment link.' },
              ].map(item => (
                <div key={item.step} className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 text-center">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center mx-auto mb-3 text-[13px] font-bold" style={{ backgroundColor: `${ACCENT}15`, color: ACCENT }}>
                    {item.step}
                  </div>
                  <h3 className="text-[#F5F5F7] font-semibold text-[15px] mb-2">{item.title}</h3>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Key Features Grid */}
          <section className="mb-16">
            <h2 className="text-xl font-bold mb-8 text-center">Key Features</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {features.map(f => (
                <div key={f.title} className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 hover:border-[#2A2A30] transition-colors">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${ACCENT}15` }}>
                      <f.icon size={18} style={{ color: ACCENT }} />
                    </div>
                    <h3 className="text-[#F5F5F7] font-semibold text-[15px]">{f.title}</h3>
                  </div>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{f.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Revenue Impact */}
          <section className="mb-16">
            <h2 className="text-xl font-bold mb-4 text-center">The Revenue You're Losing</h2>
            <p className="text-[#A1A1A8] text-[15px] text-center max-w-xl mx-auto mb-8">
              Every missed call is a missed order. Here is what the data says.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { stat: '$3,240/mo', desc: '6 missed calls/day at $18 avg ticket = $3,240/mo in lost revenue' },
                { stat: '93%', desc: 'of customers who call prefer not to wait on hold' },
                { stat: '+22%', desc: 'more phone orders for restaurants using an AI phone agent' },
              ].map(item => (
                <div key={item.stat} className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 text-center">
                  <p className="text-2xl font-bold font-mono mb-2" style={{ color: ACCENT }}>{item.stat}</p>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Call Transcript */}
          <section className="mb-16">
            <h2 className="text-xl font-bold mb-4 text-center">How the Call Sounds</h2>
            <p className="text-[#A1A1A8] text-[15px] text-center max-w-xl mx-auto mb-8">
              A real example of the AI phone agent taking a coffee order.
            </p>
            <div className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 sm:p-8 max-w-2xl mx-auto">
              <div className="space-y-3">
                {transcript.map((msg, i) => (
                  <div key={i} className={`flex ${msg.from === 'ai' ? 'justify-start' : 'justify-end'}`}>
                    <div className="flex items-start gap-2 max-w-[85%]">
                      {msg.from === 'ai' && (
                        <span className="text-[11px] mt-1.5 flex-shrink-0" style={{ color: ACCENT }}>AI</span>
                      )}
                      <div
                        className="rounded-lg px-3.5 py-2 text-[13px] leading-relaxed"
                        style={{
                          backgroundColor: msg.from === 'ai' ? `${ACCENT}15` : '#1F1F23',
                          color: msg.from === 'ai' ? ACCENT : '#A1A1A8',
                        }}
                      >
                        {msg.text}
                      </div>
                      {msg.from === 'customer' && (
                        <span className="text-[11px] text-[#6B7280] mt-1.5 flex-shrink-0">You</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-4 border-t border-[#1F1F23] flex items-center gap-2 justify-center">
                <MessageSquare size={14} style={{ color: ACCENT }} />
                <span className="text-[12px] text-[#6B7280]">SMS payment link sent to customer's phone</span>
              </div>
            </div>
          </section>

          {/* POS Integration */}
          <section className="mb-16">
            <h2 className="text-xl font-bold mb-4 text-center">Works With Your POS</h2>
            <p className="text-[#A1A1A8] text-[15px] text-center max-w-xl mx-auto mb-8">
              Works with 80+ POS systems. Orders flow directly into your kitchen — no re-entry needed.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto">
              {posIntegrations.map(name => (
                <div key={name} className="rounded-lg border border-[#1F1F23] bg-[#111113] p-4 text-center hover:border-[#2A2A30] transition-colors">
                  <p className="text-[#F5F5F7] font-medium text-[14px]">{name}</p>
                </div>
              ))}
            </div>
            <p className="text-[12px] text-[#6B7280] text-center mt-4">
              + Lightspeed, Shopify POS, Moneris, Alice POS, and 70+ more
            </p>
          </section>

          {/* Pricing Callout */}
          <section className="mb-16">
            <div className="rounded-xl border border-[#1F1F23] bg-[#111113] p-6 sm:p-8 text-center">
              <h2 className="text-xl font-bold mb-2">Included in All Meridian Plans</h2>
              <p className="text-[#A1A1A8] text-[15px] mb-1">Starting at <span className="text-[#F5F5F7] font-semibold">$250/mo</span></p>
              <p className="text-[#6B7280] text-[13px] mb-6">First month free. No contracts.</p>
              <Link to="/onboard" className="inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors">
                Start Your Free Month <ArrowRight size={15} />
              </Link>
            </div>
          </section>

          {/* FAQ */}
          <section className="mb-16">
            <h2 className="text-xl font-bold mb-6">Frequently Asked Questions</h2>
            <div className="space-y-3">
              {faqItems.map((faq, i) => <FAQ key={i} q={faq.q} a={faq.a} />)}
            </div>
          </section>

          {/* Related */}
          <section className="mb-10">
            <h3 className="text-lg font-semibold mb-4">Related Resources</h3>
            <div className="flex flex-wrap gap-2">
              {[
                { to: '/tools/food-cost-calculator', label: 'Food Cost Calculator' },
                { to: '/tools/prime-cost-calculator', label: 'Prime Cost Calculator' },
                { to: '/for/restaurants', label: 'Restaurant Analytics' },
              ].map(link => (
                <Link key={link.to} to={link.to} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors">
                  {link.label} <ChevronRight size={12} />
                </Link>
              ))}
            </div>
          </section>
        </main>

        {/* CTA */}
        <section className="py-16 border-t border-[#1F1F23]/40 relative">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-[0.06]" style={{ background: 'radial-gradient(circle, #1A8FD6 0%, transparent 70%)' }} />
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center relative">
            <h2 className="text-2xl font-bold">Stop Losing Phone Orders</h2>
            <p className="mt-3 text-[#A1A1A8] text-[15px] max-w-lg mx-auto">Every missed call is lost revenue. Let the AI phone agent answer every ring, take every order, and send every payment link — while your team focuses on the kitchen.</p>
            <Link to="/onboard" className="mt-6 inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors">
              Get Started Free <ArrowRight size={15} />
            </Link>
          </div>
        </section>

        <footer className="border-t border-[#1F1F23]/40 py-6">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <Link to="/guides" className="hover:text-[#A1A1A8]">Guides</Link>
            <Link to="/faq" className="hover:text-[#A1A1A8]">FAQ</Link>
            <Link to="/blog" className="hover:text-[#A1A1A8]">Blog</Link>
          </div>
        </footer>
      </div>
    </>
  )
}
