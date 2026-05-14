import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import {
  Phone,
  Mail,
  MapPin,
  Clock,
  ChevronDown,
  Star,
  ExternalLink,
  ShoppingBag,
  Navigation,
} from 'lucide-react'
import SceneRenderer from '@/components/website/SceneRenderer'
import WebsiteTracker from '@/components/website/WebsiteTracker'
import { getTemplateById } from '@/data/websiteTemplates'

const API_BASE = import.meta.env.VITE_API_URL || ''
const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY || 'AIzaSyBFw0Qbyq9zTFTd-tUY6dZWTgaQzuU17R8'

/* ── Types ──────────────────────────────────────────────────── */

interface WebsiteData {
  active: boolean
  business_name: string
  business_type: string
  tagline?: string
  template_id: string
  template_config: Record<string, unknown>
  logo_url?: string
  hero_headline: string
  hero_subheadline: string
  about_text: string
  services: Array<{ name: string; description: string; price?: string }>
  hours: Record<string, string>
  phone: string
  email: string
  address: string
  google_rating?: number
  google_review_count?: number
  google_reviews: Array<{ author: string; rating: number; text: string; date: string }>
  social_links: Record<string, string>
  ordering_enabled: boolean
  slug: string
  id?: string
  merchant_id?: string
}

/* ── Helpers ────────────────────────────────────────────────── */

function StarRating({ rating, color }: { rating: number; color: string }) {
  return (
    <span className="inline-flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(i => {
        const fill = rating >= i ? 1 : rating >= i - 0.5 ? 0.5 : 0
        return (
          <span key={i} className="relative inline-block w-5 h-5">
            <Star className="absolute inset-0 w-5 h-5 text-white/20" />
            {fill > 0 && (
              <span
                className="absolute inset-0 overflow-hidden"
                style={{ width: fill === 1 ? '100%' : '50%' }}
              >
                <Star className="w-5 h-5 fill-current" style={{ color }} />
              </span>
            )}
          </span>
        )
      })}
    </span>
  )
}

function SocialIcon({ platform, url, color }: { platform: string; url: string; color: string }) {
  const label = platform.charAt(0).toUpperCase() + platform.slice(1)
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm text-sm text-white/80 hover:bg-white/10 transition-all duration-300"
      style={{ borderColor: `${color}30` }}
    >
      <ExternalLink className="w-3.5 h-3.5" />
      {label}
    </a>
  )
}

function formatHourLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

const DAYS_ORDER = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

function sortedHours(hours: Record<string, string>): [string, string][] {
  const entries = Object.entries(hours)
  entries.sort((a, b) => {
    const ai = DAYS_ORDER.indexOf(a[0].toLowerCase())
    const bi = DAYS_ORDER.indexOf(b[0].toLowerCase())
    if (ai === -1 && bi === -1) return 0
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  })
  return entries
}

/* ── Scroll indicator (animated chevron) ────────────────────── */

function ScrollIndicator() {
  return (
    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 animate-bounce opacity-60">
      <span className="text-xs uppercase tracking-[0.25em] text-white/50 font-medium">Scroll</span>
      <ChevronDown className="w-5 h-5 text-white/50" />
    </div>
  )
}

/* ── Glass card wrapper ─────────────────────────────────────── */

function GlassCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-white/[0.04] backdrop-blur-xl border border-white/[0.08] rounded-2xl shadow-[0_8px_32px_rgba(0,0,0,0.4)] ${className}`}
    >
      {children}
    </div>
  )
}

/* ── Section wrapper with fade-in on scroll ─────────────────── */

function Section({
  children,
  className = '',
  id,
}: {
  children: React.ReactNode
  className?: string
  id?: string
}) {
  const ref = useRef<HTMLElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          obs.disconnect()
        }
      },
      { threshold: 0.1 },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <section
      ref={ref}
      id={id}
      className={`transition-all duration-1000 ease-out ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      } ${className}`}
    >
      {children}
    </section>
  )
}

/* ── Coming Soon page ───────────────────────────────────────── */

function ComingSoon({
  businessName,
  accentColor,
}: {
  businessName: string
  accentColor: string
}) {
  return (
    <div className="relative z-10 flex items-center justify-center min-h-screen px-6">
      <div className="text-center max-w-lg">
        <div
          className="inline-block px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-[0.2em] mb-8 border"
          style={{
            color: accentColor,
            borderColor: `${accentColor}40`,
            background: `${accentColor}10`,
          }}
        >
          Coming Soon
        </div>
        <h1 className="text-4xl md:text-6xl font-bold text-white mb-4 tracking-tight">
          {businessName}
        </h1>
        <p className="text-lg text-white/50 leading-relaxed">
          We are putting the finishing touches on something special. Check back soon.
        </p>
        <div
          className="mt-10 h-px w-24 mx-auto opacity-30"
          style={{ background: accentColor }}
        />
      </div>
    </div>
  )
}

/* ── Loading skeleton ───────────────────────────────────────── */

function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 rounded-xl border border-white/10 flex items-center justify-center">
          <div className="w-4 h-4 rounded-full border-2 border-white/20 border-t-white/60 animate-spin" />
        </div>
        <p className="text-white/30 text-sm tracking-wide">Loading</p>
      </div>
    </div>
  )
}

/* ── Error state ────────────────────────────────────────────── */

function NotFound() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center px-6">
      <div className="text-center max-w-md">
        <h1 className="text-5xl font-bold text-white mb-3">404</h1>
        <p className="text-white/50 text-lg mb-6">This site could not be found.</p>
        <a
          href="https://meridian.tips"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-white/10 text-white text-sm font-medium hover:bg-white/15 transition-colors"
        >
          Go to Meridian
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   MAIN PAGE COMPONENT
   ═══════════════════════════════════════════════════════════════ */

export default function MerchantSitePage() {
  const { slug } = useParams<{ slug: string }>()
  const [data, setData] = useState<WebsiteData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const reviewsRef = useRef<HTMLDivElement>(null)

  /* ── Fetch website data ─────────────────────────────────────── */

  useEffect(() => {
    if (!slug) return
    setLoading(true)
    setError(false)

    fetch(`${API_BASE}/api/website/public/${slug}`, {
      headers: { Accept: 'application/json' },
    })
      .then(res => {
        if (!res.ok) throw new Error('Not found')
        return res.json()
      })
      .then((d: WebsiteData) => {
        setData(d)
        document.title = `${d.business_name} — ${d.tagline || d.hero_subheadline || ''}`
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [slug])

  /* ── Resolve template ───────────────────────────────────────── */

  const template = data ? getTemplateById(data.template_id) : null
  const accent = template?.accentColor || '#1A8FD6'
  const primary = template?.primaryColor || '#0A0A0B'
  const sceneId = template?.scene || '3d_particles'

  /* ── Loading / error ────────────────────────────────────────── */

  if (loading) return <LoadingSkeleton />
  if (error || !data) return <NotFound />

  /* ── Coming soon (inactive) ─────────────────────────────────── */

  if (!data.active) {
    return (
      <div className="min-h-screen overflow-hidden" style={{ background: primary }}>
        <div className="fixed inset-0 z-0">
          <SceneRenderer sceneId={sceneId} primaryColor={primary} accentColor={accent} />
        </div>
        <div className="fixed inset-0 z-[1] bg-black/30" />
        <ComingSoon businessName={data.business_name} accentColor={accent} />
        {data.id && data.merchant_id && (
          <WebsiteTracker websiteId={data.id} merchantId={data.merchant_id} />
        )}
      </div>
    )
  }

  /* ── Helpers for this render ────────────────────────────────── */

  const hasReviews = data.google_reviews && data.google_reviews.length > 0
  const hasServices = data.services && data.services.length > 0
  const hasHours = data.hours && Object.keys(data.hours).length > 0
  const hasSocials = data.social_links && Object.keys(data.social_links).length > 0
  const mapsQuery = encodeURIComponent(data.address)

  /* ── Full active site ───────────────────────────────────────── */

  return (
    <div className="min-h-screen text-white scroll-smooth" style={{ background: primary }}>
      {/* Smooth scroll CSS */}
      <style>{`html { scroll-behavior: smooth; }`}</style>

      {/* 3D Background — fixed so it scrolls with page */}
      <div className="fixed inset-0 z-0">
        <SceneRenderer sceneId={sceneId} primaryColor={primary} accentColor={accent} />
      </div>

      {/* Analytics */}
      {data.id && data.merchant_id && (
        <WebsiteTracker websiteId={data.id} merchantId={data.merchant_id} />
      )}

      {/* ────────────────────────────────────────────────────────
          SECTION 1 — HERO (full viewport)
          ──────────────────────────────────────────────────────── */}
      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Dark overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/20 to-black/60 pointer-events-none" />

        {/* Top bar — logo + business name */}
        <header className="relative z-20 flex items-center justify-between px-6 md:px-12 pt-6 md:pt-8">
          <div className="flex items-center gap-3">
            {data.logo_url && (
              <img
                src={data.logo_url}
                alt={data.business_name}
                className="max-h-12 md:max-h-16 w-auto object-contain drop-shadow-lg"
              />
            )}
            {!data.logo_url && (
              <span className="text-lg font-semibold tracking-tight text-white/90">
                {data.business_name}
              </span>
            )}
          </div>

          {/* Minimal nav */}
          <nav className="hidden md:flex items-center gap-6 text-sm text-white/60">
            {hasServices && (
              <a href="#services" className="hover:text-white transition-colors duration-300">
                {data.business_type === 'restaurant' || data.business_type === 'coffee_shop' ? 'Menu' : 'Services'}
              </a>
            )}
            {hasReviews && (
              <a href="#reviews" className="hover:text-white transition-colors duration-300">
                Reviews
              </a>
            )}
            <a href="#contact" className="hover:text-white transition-colors duration-300">
              Contact
            </a>
          </nav>
        </header>

        {/* Hero content — centered */}
        <div className="relative z-20 flex-1 flex items-center justify-center px-6 md:px-12">
          <div className="max-w-3xl text-center">
            {data.tagline && (
              <div
                className="inline-block px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-[0.2em] mb-6 border"
                style={{
                  color: accent,
                  borderColor: `${accent}30`,
                  background: `${accent}08`,
                }}
              >
                {data.tagline}
              </div>
            )}

            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.05] mb-6">
              {data.hero_headline}
            </h1>

            <p className="text-lg md:text-xl text-white/60 leading-relaxed max-w-xl mx-auto mb-10">
              {data.hero_subheadline}
            </p>

            {/* CTA buttons */}
            <div className="flex flex-wrap items-center justify-center gap-4">
              {data.ordering_enabled && (
                <a
                  href="#order"
                  className="group inline-flex items-center gap-2.5 px-7 py-3.5 rounded-full text-sm font-semibold transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-[1.03]"
                  style={{
                    background: accent,
                    color: '#000',
                    boxShadow: `0 4px 24px ${accent}40`,
                  }}
                >
                  <ShoppingBag className="w-4 h-4" />
                  Order Online
                </a>
              )}

              {data.phone && (
                <a
                  href={`tel:${data.phone}`}
                  className="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-full text-sm font-semibold border border-white/15 bg-white/[0.06] backdrop-blur-sm text-white hover:bg-white/10 hover:border-white/25 transition-all duration-300"
                >
                  <Phone className="w-4 h-4" />
                  Call Now
                </a>
              )}

              {data.address && (
                <a
                  href={`https://maps.google.com/?q=${mapsQuery}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-full text-sm font-semibold border border-white/15 bg-white/[0.06] backdrop-blur-sm text-white hover:bg-white/10 hover:border-white/25 transition-all duration-300"
                >
                  <Navigation className="w-4 h-4" />
                  Get Directions
                </a>
              )}
            </div>

            {/* Google rating badge */}
            {data.google_rating != null && data.google_rating > 0 && (
              <div className="mt-10 inline-flex items-center gap-3 px-5 py-2.5 rounded-full bg-white/[0.06] backdrop-blur-sm border border-white/10">
                <StarRating rating={data.google_rating} color={accent} />
                <span className="text-sm font-semibold text-white/90">
                  {data.google_rating.toFixed(1)}
                </span>
                {data.google_review_count != null && (
                  <span className="text-xs text-white/40">
                    ({data.google_review_count} reviews)
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        <ScrollIndicator />
      </div>

      {/* ────────────────────────────────────────────────────────
          SECTION 2 — ABOUT + HOURS
          ──────────────────────────────────────────────────────── */}
      <div className="relative z-10">
        {/* Gradient divider into darker overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-black/70 to-black/80 pointer-events-none" />

        <div className="relative z-10 max-w-5xl mx-auto px-6 md:px-12 py-24 md:py-32">
          <Section>
            <div className="grid md:grid-cols-2 gap-16">
              {/* About */}
              <div>
                <h2
                  className="text-xs font-semibold uppercase tracking-[0.25em] mb-6"
                  style={{ color: accent }}
                >
                  About
                </h2>
                <p className="text-white/70 text-lg leading-relaxed whitespace-pre-line">
                  {data.about_text}
                </p>

                {/* Rating block */}
                {data.google_rating != null && data.google_rating > 0 && (
                  <div className="mt-8 flex items-center gap-3">
                    <StarRating rating={data.google_rating} color={accent} />
                    <span className="text-sm text-white/60">
                      {data.google_rating.toFixed(1)} on Google
                      {data.google_review_count ? ` (${data.google_review_count})` : ''}
                    </span>
                  </div>
                )}
              </div>

              {/* Hours */}
              {hasHours && (
                <div>
                  <h2
                    className="text-xs font-semibold uppercase tracking-[0.25em] mb-6"
                    style={{ color: accent }}
                  >
                    Hours
                  </h2>
                  <GlassCard className="p-6">
                    <div className="space-y-3">
                      {sortedHours(data.hours).map(([day, time]) => (
                        <div key={day} className="flex items-center justify-between text-sm">
                          <span className="text-white/60">{formatHourLabel(day)}</span>
                          <span className="text-white/90 font-medium">{time}</span>
                        </div>
                      ))}
                    </div>
                  </GlassCard>
                </div>
              )}
            </div>
          </Section>
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────
          SECTION 3 — SERVICES / MENU
          ──────────────────────────────────────────────────────── */}
      {hasServices && (
        <div className="relative z-10" id="services">
          <div className="absolute inset-0 bg-black/75 pointer-events-none" />

          <div className="relative z-10 max-w-5xl mx-auto px-6 md:px-12 py-24 md:py-32">
            <Section>
              <h2
                className="text-xs font-semibold uppercase tracking-[0.25em] mb-2"
                style={{ color: accent }}
              >
                {data.business_type === 'restaurant' || data.business_type === 'coffee_shop'
                  ? 'Menu'
                  : 'Services'}
              </h2>
              <p className="text-white/40 text-sm mb-10">
                {data.business_type === 'restaurant' || data.business_type === 'coffee_shop'
                  ? 'What we serve'
                  : 'What we offer'}
              </p>

              <div className="grid sm:grid-cols-2 gap-4">
                {data.services.map((svc, i) => (
                  <GlassCard key={i} className="p-6 hover:bg-white/[0.07] transition-colors duration-500">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-semibold text-white/95 mb-1.5">{svc.name}</h3>
                        <p className="text-sm text-white/50 leading-relaxed">{svc.description}</p>
                      </div>
                      {svc.price && (
                        <span
                          className="text-sm font-bold whitespace-nowrap mt-0.5"
                          style={{ color: accent }}
                        >
                          {svc.price}
                        </span>
                      )}
                    </div>
                  </GlassCard>
                ))}
              </div>
            </Section>
          </div>
        </div>
      )}

      {/* ────────────────────────────────────────────────────────
          SECTION 4 — REVIEWS
          ──────────────────────────────────────────────────────── */}
      {hasReviews && (
        <div className="relative z-10" id="reviews">
          <div className="absolute inset-0 bg-black/70 pointer-events-none" />

          <div className="relative z-10 max-w-6xl mx-auto px-6 md:px-12 py-24 md:py-32">
            <Section>
              <h2
                className="text-xs font-semibold uppercase tracking-[0.25em] mb-2"
                style={{ color: accent }}
              >
                Reviews
              </h2>
              <p className="text-white/40 text-sm mb-10">What our customers say</p>

              {/* Horizontal scroll carousel */}
              <div
                ref={reviewsRef}
                className="flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory no-scrollbar -mx-6 px-6"
              >
                {data.google_reviews.map((review, i) => (
                  <GlassCard
                    key={i}
                    className="flex-shrink-0 w-[320px] md:w-[380px] p-6 snap-start"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <StarRating rating={review.rating} color={accent} />
                      <span className="text-xs text-white/30">{review.rating}.0</span>
                    </div>
                    <p className="text-sm text-white/60 leading-relaxed line-clamp-5 mb-4">
                      &ldquo;{review.text}&rdquo;
                    </p>
                    <div className="flex items-center justify-between mt-auto">
                      <span className="text-sm font-medium text-white/80">{review.author}</span>
                      <span className="text-xs text-white/30">{review.date}</span>
                    </div>
                  </GlassCard>
                ))}
              </div>
            </Section>
          </div>
        </div>
      )}

      {/* ────────────────────────────────────────────────────────
          SECTION 5 — CONTACT
          ──────────────────────────────────────────────────────── */}
      <div className="relative z-10" id="contact">
        <div className="absolute inset-0 bg-black/80 pointer-events-none" />

        <div className="relative z-10 max-w-5xl mx-auto px-6 md:px-12 py-24 md:py-32">
          <Section>
            <h2
              className="text-xs font-semibold uppercase tracking-[0.25em] mb-10"
              style={{ color: accent }}
            >
              Contact
            </h2>

            <div className="grid md:grid-cols-2 gap-12">
              {/* Contact details */}
              <div className="space-y-6">
                {data.phone && (
                  <a
                    href={`tel:${data.phone}`}
                    className="flex items-center gap-4 group"
                  >
                    <div
                      className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                      style={{ background: `${accent}15`, border: `1px solid ${accent}25` }}
                    >
                      <Phone className="w-4.5 h-4.5" style={{ color: accent }} />
                    </div>
                    <div>
                      <p className="text-xs text-white/40 uppercase tracking-wider">Phone</p>
                      <p className="text-white/90 font-medium group-hover:text-white transition-colors">
                        {data.phone}
                      </p>
                    </div>
                  </a>
                )}

                {data.email && (
                  <a
                    href={`mailto:${data.email}`}
                    className="flex items-center gap-4 group"
                  >
                    <div
                      className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                      style={{ background: `${accent}15`, border: `1px solid ${accent}25` }}
                    >
                      <Mail className="w-4.5 h-4.5" style={{ color: accent }} />
                    </div>
                    <div>
                      <p className="text-xs text-white/40 uppercase tracking-wider">Email</p>
                      <p className="text-white/90 font-medium group-hover:text-white transition-colors">
                        {data.email}
                      </p>
                    </div>
                  </a>
                )}

                {data.address && (
                  <a
                    href={`https://maps.google.com/?q=${mapsQuery}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-4 group"
                  >
                    <div
                      className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                      style={{ background: `${accent}15`, border: `1px solid ${accent}25` }}
                    >
                      <MapPin className="w-4.5 h-4.5" style={{ color: accent }} />
                    </div>
                    <div>
                      <p className="text-xs text-white/40 uppercase tracking-wider">Address</p>
                      <p className="text-white/90 font-medium group-hover:text-white transition-colors">
                        {data.address}
                      </p>
                    </div>
                  </a>
                )}

                {/* Social links */}
                {hasSocials && (
                  <div className="pt-4">
                    <p className="text-xs text-white/40 uppercase tracking-wider mb-3">Follow Us</p>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(data.social_links).map(([platform, url]) => (
                        <SocialIcon key={platform} platform={platform} url={url} color={accent} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Hours repeated (compact) */}
                {hasHours && (
                  <div className="pt-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Clock className="w-4 h-4" style={{ color: accent }} />
                      <p className="text-xs text-white/40 uppercase tracking-wider">Hours</p>
                    </div>
                    <div className="space-y-1.5">
                      {sortedHours(data.hours).map(([day, time]) => (
                        <div key={day} className="flex items-center justify-between text-xs">
                          <span className="text-white/40">{formatHourLabel(day)}</span>
                          <span className="text-white/70">{time}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Map embed */}
              {data.address && (
                <GlassCard className="overflow-hidden min-h-[300px]">
                  <iframe
                    title="Location"
                    src={`https://www.google.com/maps/embed/v1/place?key=${MAPS_KEY}&q=${mapsQuery}`}
                    className="w-full h-full min-h-[300px] border-0 rounded-2xl"
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                    style={{ filter: 'invert(0.9) hue-rotate(180deg) saturate(0.3) brightness(0.7)' }}
                  />
                </GlassCard>
              )}
            </div>
          </Section>
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────
          FOOTER
          ──────────────────────────────────────────────────────── */}
      <footer className="relative z-10">
        <div className="absolute inset-0 bg-black/90 pointer-events-none" />
        <div className="relative z-10 max-w-5xl mx-auto px-6 md:px-12 py-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-white/20">
              &copy; {new Date().getFullYear()} {data.business_name}. All rights reserved.
            </p>
            <a
              href="https://meridian.tips"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-xs text-white/15 hover:text-white/30 transition-colors duration-300"
            >
              Powered by
              <span className="font-semibold tracking-tight">Meridian</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
