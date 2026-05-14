import { useState, useEffect, useCallback, useRef } from 'react'
import { clsx } from 'clsx'
import {
  Globe, Palette, BarChart3, ShoppingBag, ExternalLink, Copy, Check,
  Loader2, ArrowRight, Trash2, Eye, EyeOff, RefreshCw, Star,
  Phone, Mail, MapPin, Clock, ChevronRight, Sparkles, Link2, X,
} from 'lucide-react'
import { useOrgId } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import ScrollReveal from '@/components/ScrollReveal'
import { WEBSITE_TEMPLATES, getTemplateById, type WebsiteTemplate } from '@/data/websiteTemplates'
import SceneRenderer from '@/components/website/SceneRenderer'

const API_BASE = import.meta.env.VITE_API_URL || ''

type SubTab = 'setup' | 'website' | 'analytics' | 'orders'

interface WebsiteConfig {
  id?: string
  slug?: string
  business_name?: string
  business_type?: string
  tagline?: string
  template_id: string
  logo_url?: string
  hero_headline?: string
  hero_subheadline?: string
  about_text?: string
  services: Array<{ name: string; description: string; price: string }>
  hours: Record<string, string>
  phone?: string
  email?: string
  address?: string
  source_url?: string
  published?: boolean
  published_at?: string
  ordering_enabled?: boolean
  social_links?: Record<string, string>
  google_rating?: number
  google_review_count?: number
}

interface AnalyticsSummary {
  visitors_today: number
  visitors_this_week: number
  total_events_30d: number
  top_referrers: Array<{ referrer: string; count: number }>
  device_split: Record<string, number>
  utm_sources: Record<string, number>
}

interface Order {
  id: string
  customer_name: string
  customer_phone: string
  items: Array<{ name: string; qty: number; price: number }>
  subtotal: number
  fee_amount: number
  total: number
  status: string
  order_type: string
  created_at: string
}

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
const DAY_LABELS: Record<string, string> = {
  monday: 'Mon', tuesday: 'Tue', wednesday: 'Wed', thursday: 'Thu',
  friday: 'Fri', saturday: 'Sat', sunday: 'Sun',
}

const BUSINESS_TYPES = [
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'coffee_shop', label: 'Coffee Shop' },
  { value: 'fast_food', label: 'Fast Food' },
  { value: 'smoke_shop', label: 'Smoke Shop' },
  { value: 'auto_shop', label: 'Auto Shop' },
  { value: 'retail', label: 'Retail Store' },
  { value: 'salon', label: 'Salon / Spa' },
  { value: 'other', label: 'Other' },
]

function StatCard({ label, value, icon: Icon, accent }: { label: string; value: string | number; icon: typeof Globe; accent?: boolean }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={14} className={accent ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/50'} />
        <span className="text-[11px] text-[#A1A1A8] uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-xl font-bold text-[#F5F5F7] font-mono">{value}</p>
    </div>
  )
}

export default function MyWebsitePage() {
  const orgId = useOrgId()
  const { org } = useAuth()
  const [tab, setTab] = useState<SubTab>('setup')
  const [config, setConfig] = useState<WebsiteConfig>({
    template_id: 'aurora',
    services: [],
    hours: {},
  })
  const [hasWebsite, setHasWebsite] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [scraping, setScraping] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [scrapeUrl, setScrapeUrl] = useState('')
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<WebsiteTemplate | null>(null)
  const [previewTemplate, setPreviewTemplate] = useState<WebsiteTemplate | null>(null)
  const dirty = useRef(false)
  const autosaveTimer = useRef<ReturnType<typeof setTimeout>>()
  const DRAFT_KEY = `meridian_website_draft_${orgId}`

  const siteUrl = config.slug ? `${window.location.origin}/sites/${config.slug}` : ''

  // Mark dirty on config changes (skip initial load)
  const initialLoad = useRef(true)
  useEffect(() => {
    if (initialLoad.current) { initialLoad.current = false; return }
    dirty.current = true

    // Autosave to localStorage after 2s of inactivity
    clearTimeout(autosaveTimer.current)
    autosaveTimer.current = setTimeout(() => {
      try { localStorage.setItem(DRAFT_KEY, JSON.stringify(config)) } catch {}
    }, 2000)
  }, [config, DRAFT_KEY])

  // Navigation guard — warn on unsaved changes
  useEffect(() => {
    function onBeforeUnload(e: BeforeUnloadEvent) {
      if (dirty.current) { e.preventDefault(); e.returnValue = '' }
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [])

  // Restore draft on mount (only if no saved website exists yet)
  useEffect(() => {
    if (hasWebsite) return
    try {
      const raw = localStorage.getItem(DRAFT_KEY)
      if (raw) {
        const draft = JSON.parse(raw)
        if (draft.business_name || draft.hero_headline) {
          setConfig(prev => ({ ...prev, ...draft }))
          setSuccess('Draft restored from your last session.')
        }
      }
    } catch {}
  }, [hasWebsite, DRAFT_KEY])

  // Clear draft after successful save
  function clearDraft() {
    dirty.current = false
    try { localStorage.removeItem(DRAFT_KEY) } catch {}
  }

  const loadConfig = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/website/config?merchant_id=${orgId}`)
      if (res.ok) {
        const data = await res.json()
        if (data && data.id) {
          setConfig({ ...config, ...data })
          setHasWebsite(true)
          setTab(data.published ? 'website' : 'setup')
        }
      }
    } catch {
      // No website yet — stay on setup
    } finally {
      setLoading(false)
    }
  }, [orgId])

  useEffect(() => { loadConfig() }, [loadConfig])

  useEffect(() => {
    if (hasWebsite && tab === 'analytics') loadAnalytics()
    if (hasWebsite && tab === 'orders') loadOrders()
  }, [tab, hasWebsite])

  async function loadAnalytics() {
    try {
      const res = await fetch(`${API_BASE}/api/website/analytics/${orgId}`)
      if (res.ok) setAnalytics(await res.json())
    } catch {
      setError('Failed to load analytics')
    }
  }

  async function loadOrders() {
    try {
      const res = await fetch(`${API_BASE}/api/website/orders/${orgId}`)
      if (res.ok) {
        const data = await res.json()
        setOrders(data.orders || [])
      }
    } catch {
      setError('Failed to load orders')
    }
  }

  async function handleScrape() {
    if (!scrapeUrl) return
    setScraping(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/api/website/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: scrapeUrl, merchant_id: orgId }),
      })
      const json = await res.json()
      if (json.error) { setError(json.error); return }
      const scraped = json.data || json
      setConfig(prev => ({
        ...prev,
        business_name: scraped.business_name || prev.business_name,
        phone: scraped.phone || prev.phone,
        email: scraped.email || prev.email,
        address: scraped.address || prev.address,
        about_text: scraped.about || prev.about_text,
        logo_url: scraped.logo_url || prev.logo_url,
        social_links: scraped.social_links || prev.social_links,
        hours: scraped.hours || prev.hours,
        google_rating: scraped.google_rating ?? prev.google_rating,
        google_review_count: scraped.google_review_count ?? prev.google_review_count,
        source_url: scrapeUrl,
      }))
      const reviewCount = scraped.google_review_count || 0
      const ratingStr = scraped.google_rating ? ` (${scraped.google_rating} stars, ${reviewCount} reviews)` : ''
      setSuccess(`Site scraped!${ratingStr} Review the info below and adjust as needed.`)
    } catch (e: any) {
      setError(e.message || 'Scrape failed')
    } finally {
      setScraping(false)
    }
  }

  async function handleGenerate() {
    setGenerating(true)
    setError('')
    try {
      await handleSave(false)
      const res = await fetch(`${API_BASE}/api/website/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ merchant_id: orgId }),
      })
      const json = await res.json()
      const copy = json.copy || json
      setConfig(prev => ({
        ...prev,
        hero_headline: copy.headline || prev.hero_headline,
        hero_subheadline: copy.subheadline || prev.hero_subheadline,
        about_text: copy.about || prev.about_text,
      }))
      setSuccess('Copy generated by AI! Review and publish when ready.')
    } catch (e: any) {
      setError(e.message || 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  async function handleSave(showSuccess = true) {
    setSaving(true)
    setError('')
    try {
      const body = { ...config, merchant_id: orgId }
      const res = await fetch(`${API_BASE}/api/website/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (data.id) {
        setConfig(prev => ({ ...prev, id: data.id, slug: data.slug }))
        setHasWebsite(true)
        clearDraft()
      }
      if (showSuccess) setSuccess('Saved!')
    } catch (e: any) {
      setError(e.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function handlePublish() {
    setPublishing(true)
    setError('')
    try {
      await handleSave(false)
      const res = await fetch(`${API_BASE}/api/website/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ merchant_id: orgId }),
      })
      const data = await res.json()
      if (data.ok) {
        setConfig(prev => ({ ...prev, published: true, slug: data.slug }))
        setSuccess('Your website is live!')
        setTab('website')
      } else {
        setError(data.detail || 'Publish failed — check required fields')
      }
    } catch (e: any) {
      setError(e.message || 'Publish failed')
    } finally {
      setPublishing(false)
    }
  }

  async function handleUnpublish() {
    try {
      await fetch(`${API_BASE}/api/website/unpublish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ merchant_id: orgId }),
      })
      setConfig(prev => ({ ...prev, published: false }))
      setSuccess('Website taken offline.')
    } catch {
      setError('Failed to unpublish. Try again.')
    }
  }

  function copyUrl() {
    navigator.clipboard.writeText(siteUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function addService() {
    setConfig(prev => ({
      ...prev,
      services: [...prev.services, { name: '', description: '', price: '' }],
    }))
  }

  function updateService(i: number, field: string, value: string) {
    setConfig(prev => {
      const services = [...prev.services]
      services[i] = { ...services[i], [field]: value }
      return { ...prev, services }
    })
  }

  function removeService(i: number) {
    setConfig(prev => ({
      ...prev,
      services: prev.services.filter((_, idx) => idx !== i),
    }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={24} className="animate-spin text-[#1A8FD6]" />
      </div>
    )
  }

  const tabs: { key: SubTab; label: string; icon: typeof Globe; show: boolean }[] = [
    { key: 'setup', label: 'Setup', icon: Palette, show: true },
    { key: 'website', label: 'My Website', icon: Globe, show: hasWebsite },
    { key: 'analytics', label: 'Analytics', icon: BarChart3, show: hasWebsite && !!config.published },
    { key: 'orders', label: 'Orders', icon: ShoppingBag, show: hasWebsite && !!config.ordering_enabled },
  ]

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">My Website</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              {hasWebsite && config.published
                ? <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Live</span>
                : 'Build your professional 3D website in minutes'}
            </p>
          </div>
          {hasWebsite && config.published && siteUrl && (
            <a href={siteUrl} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1A8FD6]/10 text-[#1A8FD6] text-sm font-medium border border-[#1A8FD6]/20 hover:bg-[#1A8FD6]/20 transition-colors">
              <ExternalLink size={14} /> Visit Site
            </a>
          )}
        </div>
      </ScrollReveal>

      {/* Sub-tabs */}
      <ScrollReveal variant="fadeUp" delay={0.03}>
        <div className="flex gap-1 border-b border-[#1F1F23] pb-0">
          {tabs.filter(t => t.show).map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-[1px]',
                tab === t.key
                  ? 'text-[#1A8FD6] border-[#1A8FD6]'
                  : 'text-[#A1A1A8] border-transparent hover:text-[#F5F5F7]'
              )}>
              <t.icon size={15} /> {t.label}
            </button>
          ))}
        </div>
      </ScrollReveal>

      {/* Status messages */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400">{error}
          <button onClick={() => setError('')} className="ml-2 underline">dismiss</button>
        </div>
      )}
      {success && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-sm text-emerald-400">{success}
          <button onClick={() => setSuccess('')} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* ═══ SETUP TAB ═══ */}
      {tab === 'setup' && (
        <div className="space-y-6">
          {/* Scrape section */}
          <ScrollReveal variant="fadeUp" delay={0.05}>
            <div className="card p-5 space-y-4">
              <h3 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-2">
                <Link2 size={16} className="text-[#1A8FD6]" /> Import from existing website
              </h3>
              <div className="flex gap-2">
                <input type="url" value={scrapeUrl} onChange={e => setScrapeUrl(e.target.value)}
                  placeholder="https://yourbusiness.com"
                  className="flex-1 px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] placeholder:text-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50" />
                <button onClick={handleScrape} disabled={scraping || !scrapeUrl}
                  className="px-4 py-2 rounded-lg bg-[#1A8FD6] text-white text-sm font-medium hover:bg-[#1A8FD6]/90 disabled:opacity-40 flex items-center gap-2">
                  {scraping ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                  {scraping ? 'Scraping...' : 'Scrape'}
                </button>
              </div>
              <p className="text-xs text-[#A1A1A8]/60">We'll extract your branding, hours, contact info, and services automatically.</p>
            </div>
          </ScrollReveal>

          {/* Business info form */}
          <ScrollReveal variant="fadeUp" delay={0.08}>
            <div className="card p-5 space-y-4">
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Business Info</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#A1A1A8] mb-1 block">Business Name *</label>
                  <input value={config.business_name || ''} onChange={e => setConfig(p => ({ ...p, business_name: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                </div>
                <div>
                  <label className="text-xs text-[#A1A1A8] mb-1 block">Business Type</label>
                  <select value={config.business_type || ''} onChange={e => setConfig(p => ({ ...p, business_type: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50">
                    <option value="">Select...</option>
                    {BUSINESS_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#A1A1A8] mb-1 block">Phone</label>
                  <input value={config.phone || ''} onChange={e => setConfig(p => ({ ...p, phone: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                </div>
                <div>
                  <label className="text-xs text-[#A1A1A8] mb-1 block">Email</label>
                  <input value={config.email || ''} onChange={e => setConfig(p => ({ ...p, email: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-xs text-[#A1A1A8] mb-1 block">Address</label>
                  <input value={config.address || ''} onChange={e => setConfig(p => ({ ...p, address: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                </div>
              </div>

              {/* Hours */}
              <div>
                <label className="text-xs text-[#A1A1A8] mb-2 block">Hours</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {DAYS.map(day => (
                    <div key={day} className="flex items-center gap-2">
                      <span className="w-10 text-xs text-[#A1A1A8] font-medium">{DAY_LABELS[day]}</span>
                      <input value={config.hours[day] || ''} placeholder="9am - 5pm"
                        onChange={e => setConfig(p => ({ ...p, hours: { ...p.hours, [day]: e.target.value } }))}
                        className="flex-1 px-2 py-1.5 rounded bg-[#1F1F23] border border-[#2A2A30] text-xs text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                    </div>
                  ))}
                </div>
              </div>

              {/* Services */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs text-[#A1A1A8]">Services / Menu</label>
                  <button onClick={addService} className="text-xs text-[#1A8FD6] hover:underline">+ Add item</button>
                </div>
                <div className="space-y-2">
                  {config.services.map((svc, i) => (
                    <div key={i} className="flex gap-2 items-start">
                      <input value={svc.name} placeholder="Service name"
                        onChange={e => updateService(i, 'name', e.target.value)}
                        className="flex-1 px-2 py-1.5 rounded bg-[#1F1F23] border border-[#2A2A30] text-xs text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                      <input value={svc.description} placeholder="Description"
                        onChange={e => updateService(i, 'description', e.target.value)}
                        className="flex-1 px-2 py-1.5 rounded bg-[#1F1F23] border border-[#2A2A30] text-xs text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                      <input value={svc.price} placeholder="$0.00"
                        onChange={e => updateService(i, 'price', e.target.value)}
                        className="w-20 px-2 py-1.5 rounded bg-[#1F1F23] border border-[#2A2A30] text-xs text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                      <button onClick={() => removeService(i)} className="text-red-400/60 hover:text-red-400 p-1">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </ScrollReveal>

          {/* Copy fields */}
          <ScrollReveal variant="fadeUp" delay={0.1}>
            <div className="card p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[#F5F5F7]">Website Copy</h3>
                <button onClick={handleGenerate} disabled={generating}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#7C5CFF]/10 text-[#7C5CFF] text-xs font-medium border border-[#7C5CFF]/20 hover:bg-[#7C5CFF]/20 disabled:opacity-40">
                  {generating ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                  {generating ? 'Generating...' : 'AI Generate'}
                </button>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-[#A1A1A8] mb-1 block">Hero Headline</label>
                  <input value={config.hero_headline || ''} placeholder="Your Business, Elevated"
                    onChange={e => setConfig(p => ({ ...p, hero_headline: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                </div>
                <div>
                  <label className="text-xs text-[#A1A1A8] mb-1 block">Sub-headline</label>
                  <input value={config.hero_subheadline || ''} placeholder="Discover what makes us special"
                    onChange={e => setConfig(p => ({ ...p, hero_subheadline: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
                </div>
                <div>
                  <label className="text-xs text-[#A1A1A8] mb-1 block">About</label>
                  <textarea rows={3} value={config.about_text || ''} placeholder="Tell your story..."
                    onChange={e => setConfig(p => ({ ...p, about_text: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50 resize-none" />
                </div>
              </div>
            </div>
          </ScrollReveal>

          {/* Template picker */}
          <ScrollReveal variant="fadeUp" delay={0.12}>
            <div className="card p-5 space-y-4">
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Choose a Template</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {WEBSITE_TEMPLATES.map(tmpl => {
                  const isSelected = config.template_id === tmpl.id
                  return (
                    <div key={tmpl.id}
                      className={clsx(
                        'relative rounded-xl overflow-hidden border-2 transition-all text-left group',
                        isSelected ? 'border-[#1A8FD6] ring-2 ring-[#1A8FD6]/20' : 'border-[#1F1F23] hover:border-[#2A2A30]'
                      )}>
                      <button onClick={() => { setConfig(p => ({ ...p, template_id: tmpl.id })); setSelectedTemplate(tmpl) }}
                        className="w-full text-left">
                        <div className="aspect-[4/3] relative" style={{ background: `linear-gradient(135deg, ${tmpl.primaryColor}, ${tmpl.accentColor}20)` }}>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-8 h-8 rounded-full" style={{ background: tmpl.accentColor, opacity: 0.6 }} />
                          </div>
                          {isSelected && (
                            <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-[#1A8FD6] flex items-center justify-center">
                              <Check size={12} className="text-white" />
                            </div>
                          )}
                          {/* Preview button — appears on hover */}
                          <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <span
                              onClick={(e) => { e.stopPropagation(); setPreviewTemplate(tmpl) }}
                              className="px-3 py-1.5 rounded-full bg-white/15 backdrop-blur-sm text-white text-[11px] font-medium border border-white/20 hover:bg-white/25 transition-colors cursor-pointer flex items-center gap-1.5">
                              <Eye size={12} /> Preview
                            </span>
                          </div>
                        </div>
                        <div className="p-2.5">
                          <p className="text-xs font-semibold text-[#F5F5F7]">{tmpl.name}</p>
                          <p className="text-[10px] text-[#A1A1A8] mt-0.5 line-clamp-1">{tmpl.description}</p>
                        </div>
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>
          </ScrollReveal>

          {/* Action buttons */}
          <ScrollReveal variant="fadeUp" delay={0.15}>
            <div className="flex gap-3">
              <button onClick={() => handleSave(true)} disabled={saving}
                className="px-5 py-2.5 rounded-lg border border-[#2A2A30] text-sm font-medium text-[#F5F5F7] hover:bg-[#1F1F23] disabled:opacity-40 flex items-center gap-2">
                {saving ? <Loader2 size={14} className="animate-spin" /> : null}
                Save Draft
              </button>
              <button onClick={handlePublish} disabled={publishing || !config.business_name || !config.hero_headline}
                className="px-6 py-2.5 rounded-lg bg-[#1A8FD6] text-white text-sm font-semibold hover:bg-[#1A8FD6]/90 disabled:opacity-40 flex items-center gap-2 shadow-lg shadow-[#1A8FD6]/20">
                {publishing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                {publishing ? 'Publishing...' : 'Publish Website'}
              </button>
            </div>
          </ScrollReveal>
        </div>
      )}

      {/* ═══ MY WEBSITE TAB ═══ */}
      {tab === 'website' && hasWebsite && (
        <div className="space-y-6">
          {/* Live URL bar */}
          <div className="card p-4 flex items-center gap-3 flex-wrap">
            <span className="flex items-center gap-1.5">
              <span className={clsx('w-2 h-2 rounded-full', config.published ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400')} />
              <span className="text-xs font-medium text-[#A1A1A8]">{config.published ? 'Live' : 'Draft'}</span>
            </span>
            {siteUrl && (
              <>
                <code className="text-xs text-[#1A8FD6] bg-[#1A8FD6]/5 px-2 py-1 rounded font-mono flex-1 truncate">{siteUrl}</code>
                <button onClick={copyUrl} className="text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
                  {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                </button>
                <a href={siteUrl} target="_blank" rel="noopener noreferrer" className="text-[#A1A1A8] hover:text-[#F5F5F7]">
                  <ExternalLink size={14} />
                </a>
              </>
            )}
            <button onClick={config.published ? handleUnpublish : handlePublish}
              className={clsx('text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors',
                config.published
                  ? 'text-amber-400 border-amber-400/20 hover:bg-amber-400/10'
                  : 'text-emerald-400 border-emerald-400/20 hover:bg-emerald-400/10')}>
              {config.published ? <><EyeOff size={12} className="inline mr-1" />Unpublish</> : <><Eye size={12} className="inline mr-1" />Publish</>}
            </button>
          </div>

          {/* Preview */}
          {config.published && siteUrl && (
            <div className="card overflow-hidden rounded-xl border border-[#1F1F23]">
              <div className="h-8 bg-[#1F1F23] flex items-center gap-1.5 px-3">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
                <code className="ml-2 text-[10px] text-[#A1A1A8] font-mono">{siteUrl}</code>
              </div>
              <iframe src={siteUrl} className="w-full h-[500px] border-0" title="Website preview" />
            </div>
          )}

          {/* Quick edit */}
          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Quick Edit</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[#A1A1A8] mb-1 block">Headline</label>
                <input value={config.hero_headline || ''} onChange={e => setConfig(p => ({ ...p, hero_headline: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
              </div>
              <div>
                <label className="text-xs text-[#A1A1A8] mb-1 block">Sub-headline</label>
                <input value={config.hero_subheadline || ''} onChange={e => setConfig(p => ({ ...p, hero_subheadline: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
              </div>
              <div>
                <label className="text-xs text-[#A1A1A8] mb-1 block">Phone</label>
                <input value={config.phone || ''} onChange={e => setConfig(p => ({ ...p, phone: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
              </div>
              <div>
                <label className="text-xs text-[#A1A1A8] mb-1 block">Template</label>
                <select value={config.template_id} onChange={e => setConfig(p => ({ ...p, template_id: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50">
                  {WEBSITE_TEMPLATES.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            </div>
            <button onClick={() => handleSave(true)} disabled={saving}
              className="px-4 py-2 rounded-lg bg-[#1A8FD6] text-white text-sm font-medium hover:bg-[#1A8FD6]/90 disabled:opacity-40 flex items-center gap-2">
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              Save Changes
            </button>
          </div>

          {/* Danger zone */}
          <details className="card">
            <summary className="p-4 text-sm text-red-400/60 cursor-pointer hover:text-red-400">Danger Zone</summary>
            <div className="px-4 pb-4">
              <button onClick={async () => {
                if (!confirm('Delete your website? This cannot be undone.')) return
                await fetch(`${API_BASE}/api/website/${orgId}`, { method: 'DELETE' })
                setHasWebsite(false); setConfig({ template_id: 'aurora', services: [], hours: {} }); setTab('setup')
              }}
                className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 text-sm hover:bg-red-500/10">
                <Trash2 size={14} className="inline mr-1.5" />Delete Website
              </button>
            </div>
          </details>
        </div>
      )}

      {/* ═══ ANALYTICS TAB ═══ */}
      {tab === 'analytics' && (
        <div className="space-y-6">
          {analytics ? (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatCard label="Today" value={analytics.visitors_today} icon={BarChart3} accent />
                <StatCard label="This Week" value={analytics.visitors_this_week} icon={BarChart3} />
                <StatCard label="Last 30 Days" value={analytics.total_events_30d} icon={Globe} />
                <StatCard label="Top Source" value={analytics.top_referrers?.[0]?.referrer || 'Direct'} icon={ShoppingBag} />
              </div>

              {/* Referrers */}
              {analytics.top_referrers && analytics.top_referrers.length > 0 && (
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Traffic Sources</h3>
                <div className="space-y-2">
                  {analytics.top_referrers.map((ref, i) => {
                    const max = Math.max(...analytics.top_referrers.map(r => r.count), 1)
                    return (
                      <div key={i} className="flex items-center gap-3">
                        <span className="text-xs text-[#A1A1A8] w-24 truncate">{ref.referrer}</span>
                        <div className="flex-1 h-5 bg-[#1F1F23] rounded-full overflow-hidden">
                          <div className="h-full bg-[#1A8FD6]/40 rounded-full" style={{ width: `${(ref.count / max) * 100}%` }} />
                        </div>
                        <span className="text-xs font-mono text-[#F5F5F7] w-10 text-right">{ref.count}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
              )}

              {/* Devices */}
              {analytics.device_split && Object.keys(analytics.device_split).length > 0 && (
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Devices</h3>
                <div className="flex gap-4">
                  {(() => {
                    const total = Object.values(analytics.device_split).reduce((a, b) => a + b, 0) || 1
                    return Object.entries(analytics.device_split).map(([device, count]) => (
                      <div key={device} className="flex-1 text-center">
                        <p className="text-2xl font-bold text-[#F5F5F7] font-mono">{Math.round((count / total) * 100)}%</p>
                        <p className="text-xs text-[#A1A1A8] capitalize mt-1">{device}</p>
                      </div>
                    ))
                  })()}
                </div>
              </div>
              )}
            </>
          ) : (
            <div className="card p-8 text-center">
              <BarChart3 size={32} className="mx-auto text-[#A1A1A8]/30 mb-3" />
              <p className="text-sm text-[#A1A1A8]">Analytics will appear after your website gets traffic.</p>
              <p className="text-xs text-[#A1A1A8]/50 mt-1">Data refreshes every 5 minutes.</p>
            </div>
          )}
        </div>
      )}

      {/* ═══ ORDERS TAB ═══ */}
      {tab === 'orders' && (
        <div className="space-y-6">
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Online Orders</h3>
              <span className="text-xs text-[#A1A1A8]">{orders.length} orders</span>
            </div>
            {orders.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-[#A1A1A8] border-b border-[#1F1F23]">
                      <th className="text-left py-2 font-medium">Time</th>
                      <th className="text-left py-2 font-medium">Customer</th>
                      <th className="text-left py-2 font-medium">Items</th>
                      <th className="text-right py-2 font-medium">Total</th>
                      <th className="text-right py-2 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map(order => (
                      <tr key={order.id} className="border-b border-[#1F1F23]/50">
                        <td className="py-2.5 text-[#A1A1A8] text-xs">{new Date(order.created_at).toLocaleTimeString()}</td>
                        <td className="py-2.5 text-[#F5F5F7]">{order.customer_name}</td>
                        <td className="py-2.5 text-[#A1A1A8]">{order.items?.length || 0} items</td>
                        <td className="py-2.5 text-right text-[#F5F5F7] font-mono">${order.total?.toFixed(2)}</td>
                        <td className="py-2.5 text-right">
                          <span className={clsx('text-[10px] font-medium px-2 py-0.5 rounded-full border',
                            order.status === 'paid' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            order.status === 'pending' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                            'bg-[#1F1F23] text-[#A1A1A8] border-[#2A2A30]')}>
                            {order.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8">
                <ShoppingBag size={32} className="mx-auto text-[#A1A1A8]/30 mb-3" />
                <p className="text-sm text-[#A1A1A8]">No orders yet.</p>
                <p className="text-xs text-[#A1A1A8]/50 mt-1">Orders from your website will appear here.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══ TEMPLATE PREVIEW MODAL ═══ */}
      {previewTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={() => setPreviewTemplate(null)}>
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
          <div className="relative w-full max-w-4xl mx-4 rounded-2xl overflow-hidden border border-[#1F1F23] shadow-2xl"
            onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="relative z-10 flex items-center justify-between px-5 py-3 bg-[#0A0A0B]/90 backdrop-blur-sm border-b border-[#1F1F23]">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full" style={{ background: previewTemplate.accentColor }} />
                <div>
                  <h3 className="text-sm font-semibold text-[#F5F5F7]">{previewTemplate.name}</h3>
                  <p className="text-[11px] text-[#A1A1A8]">{previewTemplate.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  {previewTemplate.tags.map(tag => (
                    <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full bg-[#1F1F23] text-[#A1A1A8] border border-[#2A2A30]">{tag}</span>
                  ))}
                </div>
                <button onClick={() => setPreviewTemplate(null)}
                  className="ml-3 w-8 h-8 rounded-lg flex items-center justify-center text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors">
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Live 3D scene */}
            <div className="relative aspect-video" style={{ background: previewTemplate.primaryColor }}>
              <SceneRenderer
                sceneId={previewTemplate.scene}
                primaryColor={previewTemplate.primaryColor}
                accentColor={previewTemplate.accentColor}
              />
              {/* Simulated hero content overlay */}
              <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
                <div className="text-center px-8">
                  <h2 className="text-3xl md:text-4xl font-bold text-white mb-3 tracking-tight drop-shadow-lg">
                    {config.hero_headline || config.business_name || 'Your Business Name'}
                  </h2>
                  <p className="text-base text-white/60 drop-shadow-md">
                    {config.hero_subheadline || 'Your tagline will appear here'}
                  </p>
                </div>
              </div>
              <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/40 pointer-events-none" />
            </div>

            {/* Footer actions */}
            <div className="relative z-10 flex items-center justify-between px-5 py-3 bg-[#0A0A0B]/90 backdrop-blur-sm border-t border-[#1F1F23]">
              <p className="text-xs text-[#A1A1A8]">
                Best for: {previewTemplate.businessTypes.map(t => t.replace(/_/g, ' ')).join(', ')}
              </p>
              <div className="flex gap-2">
                <button onClick={() => setPreviewTemplate(null)}
                  className="px-4 py-2 rounded-lg text-sm text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors">
                  Close
                </button>
                <button onClick={() => {
                  setConfig(p => ({ ...p, template_id: previewTemplate.id }))
                  setSelectedTemplate(previewTemplate)
                  setPreviewTemplate(null)
                }}
                  className="px-4 py-2 rounded-lg bg-[#1A8FD6] text-white text-sm font-medium hover:bg-[#1A8FD6]/90 transition-colors flex items-center gap-2">
                  <Check size={14} /> Use This Template
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
