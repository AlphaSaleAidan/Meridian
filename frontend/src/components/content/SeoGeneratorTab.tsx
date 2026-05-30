import { useState } from 'react'
import { motion } from 'framer-motion'
import DOMPurify from 'dompurify'
import {
  Search,
  Globe,
  FileText,
  Loader2,
  Check,
  Copy,
  ExternalLink,
  Zap,
  Lock,
  Coins,
  Image as ImageIcon,
  AlertCircle,
} from 'lucide-react'
import { contentApi } from '@/lib/content-api'

interface BrandData {
  business_name: string
  business_type: string
  voice_profile?: {
    tone?: string
    top_products?: string[]
    keywords?: string[]
  }
}

interface Props {
  isDemo: boolean
  creditBalance: number
  merchantId: string
  brand?: BrandData | null
}

interface WebsiteData {
  domain: string
  title: string
  meta_description: string
  logos: string[]
  headings: { level: string; text: string }[]
  social_links: Record<string, string>
  brand_colors: string[]
  content_preview: string
  word_count: number
}

interface SeoResult {
  meta_title: string
  meta_description: string
  content_html: string
  word_count: number
  headers: string[]
  schema_suggestion: string
}

const CONTENT_TYPES = [
  { id: 'blog_post', label: 'Blog Post', desc: 'SEO article with headers and links' },
  { id: 'landing_page', label: 'Landing Page', desc: 'Conversion-focused copy' },
  { id: 'product_page', label: 'Product Page', desc: 'Product/service page' },
  { id: 'faq', label: 'FAQ Page', desc: 'Targets featured snippets' },
]

export default function SeoGeneratorTab({ isDemo, creditBalance, merchantId, brand }: Props) {
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [websiteData, setWebsiteData] = useState<WebsiteData | null>(null)
  const [scraping, setScraping] = useState(false)
  const [scrapeError, setScrapeError] = useState<string | null>(null)

  const [keyword, setKeyword] = useState('')
  const [contentType, setContentType] = useState('blog_post')
  const [wordCount, setWordCount] = useState(800)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<SeoResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleScrape = async () => {
    if (!websiteUrl.trim()) return
    setScraping(true)
    setScrapeError(null)

    try {
      const data = await contentApi.scrapeWebsite(merchantId, websiteUrl)
      setWebsiteData(data)
    } catch (err) {
      setScrapeError(err instanceof Error ? err.message : 'Failed to scrape website')
    } finally {
      setScraping(false)
    }
  }

  const handleGenerate = async () => {
    if (isDemo || !keyword.trim()) return
    setGenerating(true)
    setError(null)
    setResult(null)

    try {
      const res = await contentApi.generateSeo(merchantId, {
        targetKeyword: keyword,
        websiteUrl: websiteUrl || undefined,
        contentType,
        wordCount,
        websiteContext: websiteData?.content_preview || undefined,
      })
      setResult(res.seo_content)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate SEO content')
    } finally {
      setGenerating(false)
    }
  }

  const handleCopy = () => {
    if (!result) return
    navigator.clipboard.writeText(result.content_html)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Search size={18} className="text-[#17C5B0]" />
          <h2 className="text-sm font-semibold text-[#F5F5F7]">SEO Content Generator</h2>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[#A1A1A8]">
          <Coins size={12} className="text-amber-400" />
          250 credits/article
        </div>
      </div>

      {/* Website Scanner */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Globe size={14} className="text-[#1A8FD6]" />
          <span className="text-[11px] font-medium text-[#F5F5F7]">Connect Your Website</span>
          <span className="text-[9px] text-[#A1A1A8]">We'll read your site for brand info, logos, and current content</span>
        </div>

        <div className="flex gap-2">
          <input
            value={websiteUrl}
            onChange={e => setWebsiteUrl(e.target.value)}
            placeholder="yourbusiness.com"
            className="flex-1 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-4 py-2.5 text-sm text-[#F5F5F7] placeholder:text-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40"
          />
          <button
            onClick={handleScrape}
            disabled={scraping || !websiteUrl.trim()}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-[#1A8FD6] text-white text-[11px] font-semibold hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-colors"
          >
            {scraping ? <Loader2 size={12} className="animate-spin" /> : <Globe size={12} />}
            {scraping ? 'Scanning...' : 'Scan Site'}
          </button>
        </div>

        {scrapeError && (
          <div className="flex items-center gap-2 text-[11px] text-red-400">
            <AlertCircle size={12} /> {scrapeError}
          </div>
        )}

        {/* Scraped Website Data */}
        {websiteData && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="space-y-3 pt-3 border-t border-[#1F1F23]"
          >
            <div className="flex items-center gap-2">
              <Check size={12} className="text-green-400" />
              <span className="text-[11px] font-medium text-[#F5F5F7]">{websiteData.title || websiteData.domain}</span>
              <span className="text-[9px] text-[#A1A1A8]">{websiteData.word_count} words found</span>
            </div>

            {/* Logos */}
            {websiteData.logos.length > 0 && (
              <div>
                <span className="text-[9px] text-[#A1A1A8] uppercase tracking-wider">Logos found</span>
                <div className="flex gap-2 mt-1">
                  {websiteData.logos.slice(0, 4).map((url, i) => (
                    <img
                      key={i}
                      src={url}
                      alt="Logo"
                      className="w-10 h-10 rounded border border-[#1F1F23] object-contain bg-white/5"
                      onError={e => (e.currentTarget.style.display = 'none')}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Brand Colors */}
            {websiteData.brand_colors.length > 0 && (
              <div>
                <span className="text-[9px] text-[#A1A1A8] uppercase tracking-wider">Brand colors</span>
                <div className="flex gap-1 mt-1">
                  {websiteData.brand_colors.map((color, i) => (
                    <div
                      key={i}
                      className="w-6 h-6 rounded border border-[#1F1F23]"
                      style={{ backgroundColor: color }}
                      title={color}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Meta */}
            {websiteData.meta_description && (
              <div>
                <span className="text-[9px] text-[#A1A1A8] uppercase tracking-wider">Current meta description</span>
                <p className="text-[10px] text-[#A1A1A8] mt-0.5">{websiteData.meta_description}</p>
              </div>
            )}

            <p className="text-[9px] text-green-400/60">
              Site data loaded — SEO content will be tailored to your business
            </p>
          </motion.div>
        )}
      </div>

      {/* SEO Generator */}
      <div className="card p-5 space-y-4">
        <div>
          <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
            Target Keyword
          </label>
          <input
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            placeholder="e.g. best brunch downtown portland"
            className="w-full bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-4 py-3 text-sm text-[#F5F5F7] placeholder:text-[#A1A1A8]/30 focus:outline-none focus:border-[#17C5B0]/40"
          />
          {brand?.voice_profile?.keywords && (
            <div className="flex flex-wrap gap-1 mt-2">
              {brand.voice_profile.keywords.map((kw, i) => (
                <button
                  key={i}
                  onClick={() => setKeyword(kw)}
                  className="text-[9px] text-[#17C5B0]/70 bg-[#17C5B0]/10 px-1.5 py-0.5 rounded hover:bg-[#17C5B0]/20 transition-colors"
                >
                  {kw}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Content Type */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
              Content Type
            </label>
            <div className="space-y-1">
              {CONTENT_TYPES.map(ct => (
                <button
                  key={ct.id}
                  onClick={() => setContentType(ct.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border text-left transition-all ${
                    contentType === ct.id
                      ? 'border-[#17C5B0]/40 bg-[#17C5B0]/10'
                      : 'border-[#1F1F23] hover:border-[#1F1F23]/80'
                  }`}
                >
                  <span className="text-[11px] font-medium text-[#F5F5F7]">{ct.label}</span>
                  <span className="text-[9px] text-[#A1A1A8]">{ct.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Word Count */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
              Target Word Count: {wordCount}
            </label>
            <input
              type="range"
              min={300}
              max={3000}
              step={100}
              value={wordCount}
              onChange={e => setWordCount(Number(e.target.value))}
              className="w-full accent-[#17C5B0]"
            />
            <div className="flex justify-between text-[9px] text-[#A1A1A8] mt-1">
              <span>300 (short)</span>
              <span>3000 (comprehensive)</span>
            </div>

            <div className="mt-4 p-3 bg-[#0A0A0B] rounded-lg border border-[#1F1F23] space-y-2">
              <span className="text-[10px] font-medium text-[#A1A1A8]">What you get:</span>
              <ul className="text-[9px] text-[#A1A1A8]/70 space-y-1">
                <li>- SEO-optimized {CONTENT_TYPES.find(c => c.id === contentType)?.label}</li>
                <li>- Meta title & description</li>
                <li>- Header structure (H2, H3)</li>
                <li>- Internal link suggestions</li>
                <li>- Schema markup recommendation</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Generate */}
        <div className="flex items-center justify-between pt-3 border-t border-[#1F1F23]">
          <span className="text-[10px] text-[#A1A1A8]">
            {websiteData ? `Using data from ${websiteData.domain}` : 'Scan your website for better results'}
          </span>
          {isDemo ? (
            <button disabled className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F1F23] text-[#A1A1A8]/50 text-sm font-medium cursor-not-allowed">
              <Lock size={14} /> Sign up to generate
            </button>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={generating || !keyword.trim() || creditBalance < 250}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold hover:bg-[#17C5B0]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generating ? (
                <><Loader2 size={14} className="animate-spin" /> Generating...</>
              ) : (
                <><Zap size={14} /> Generate SEO Content</>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card p-4 border-red-500/20 bg-red-500/5">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm text-red-400">{error}</p>
            <button onClick={() => setError(null)} className="text-[10px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7]">Dismiss</button>
          </div>
        </div>
      )}

      {/* Generated SEO Result */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-5 space-y-4 border-[#17C5B0]/20 bg-gradient-to-br from-[#17C5B0]/5 to-transparent"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-2">
              <Check size={14} className="text-green-400" />
              SEO Content Ready
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-[#A1A1A8]">{result.word_count} words</span>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#1F1F23] text-[10px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
              >
                {copied ? <><Check size={10} className="text-green-400" /> Copied</> : <><Copy size={10} /> Copy HTML</>}
              </button>
            </div>
          </div>

          {/* Meta Preview */}
          <div className="bg-[#0A0A0B] rounded-lg border border-[#1F1F23] p-4 space-y-2">
            <div className="space-y-1">
              <p className="text-[#1A8FD6] text-sm font-medium">{result.meta_title}</p>
              <p className="text-[11px] text-[#17C5B0]">{websiteUrl || 'yourbusiness.com'}</p>
              <p className="text-[11px] text-[#A1A1A8]">{result.meta_description}</p>
            </div>
            <p className="text-[8px] text-[#A1A1A8]/30 uppercase tracking-wider mt-2">Google preview</p>
          </div>

          {/* Content Preview */}
          <div className="bg-[#0A0A0B] rounded-lg border border-[#1F1F23] p-4 max-h-[400px] overflow-y-auto">
            <div
              className="prose prose-sm prose-invert max-w-none text-[11px] text-[#A1A1A8] [&_h2]:text-[#F5F5F7] [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mt-4 [&_h3]:text-[#F5F5F7] [&_h3]:text-xs [&_h3]:font-medium [&_h3]:mt-3 [&_p]:mt-2 [&_li]:mt-1"
              dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(result.content_html) }}
            />
          </div>

          {/* Headers & Schema */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#0A0A0B] rounded-lg border border-[#1F1F23] p-3">
              <span className="text-[9px] text-[#A1A1A8] uppercase tracking-wider">Structure</span>
              <div className="mt-1 space-y-0.5">
                {result.headers.map((h, i) => (
                  <p key={i} className="text-[10px] text-[#F5F5F7]">{h}</p>
                ))}
              </div>
            </div>
            <div className="bg-[#0A0A0B] rounded-lg border border-[#1F1F23] p-3">
              <span className="text-[9px] text-[#A1A1A8] uppercase tracking-wider">Schema</span>
              <p className="text-[10px] text-[#F5F5F7] mt-1">{result.schema_suggestion}</p>
              <p className="text-[8px] text-[#17C5B0]/60 mt-2">
                Add to your website's &lt;head&gt; for rich search results
              </p>
            </div>
          </div>

          {/* Deploy CTA */}
          <div className="flex items-center gap-3 p-3 bg-[#17C5B0]/5 rounded-lg border border-[#17C5B0]/20">
            <ExternalLink size={14} className="text-[#17C5B0]" />
            <div className="flex-1">
              <p className="text-[11px] font-medium text-[#F5F5F7]">Deploy to My Website</p>
              <p className="text-[9px] text-[#A1A1A8]">Push this content to your website from the My Website page</p>
            </div>
            <button className="px-3 py-1.5 rounded-md bg-[#17C5B0]/20 text-[10px] font-medium text-[#17C5B0] hover:bg-[#17C5B0]/30 transition-colors">
              Go to My Website
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
