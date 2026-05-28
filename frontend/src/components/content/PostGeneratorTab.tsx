import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Wand2,
  Upload,
  Instagram,
  Facebook,
  Music2,
  Linkedin,
  MapPin,
  Globe,
  Loader2,
  Copy,
  Check,
  X,
  Coins,
  Lock,
  Hash,
  MessageSquare,
  Image as ImageIcon,
} from 'lucide-react'
import { contentApi } from '@/lib/content-api'

interface BrandData {
  business_name: string
  business_type: string
  voice_profile?: {
    tone?: string
    emoji_usage?: string
    top_products?: string[]
    keywords?: string[]
  }
}

interface Props {
  isDemo: boolean
  creditBalance: number
  merchantId: string
  brand?: BrandData | null
  websiteContext?: string | null
}

const PLATFORMS = [
  { id: 'instagram', label: 'Instagram', icon: Instagram, color: 'text-purple-400' },
  { id: 'facebook', label: 'Facebook', icon: Facebook, color: 'text-blue-400' },
  { id: 'tiktok', label: 'TikTok', icon: Music2, color: 'text-[#F5F5F7]' },
  { id: 'google_business', label: 'Google Biz', icon: MapPin, color: 'text-green-400' },
  { id: 'linkedin', label: 'LinkedIn', icon: Linkedin, color: 'text-blue-500' },
]

interface GeneratedPost {
  hook: string
  body: string
  hashtags: string[]
  call_to_action: string
  suggested_image_prompt?: string
  platform: string
}

export default function PostGeneratorTab({ isDemo, creditBalance, merchantId, brand, websiteContext }: Props) {
  const [prompt, setPrompt] = useState('')
  const [platform, setPlatform] = useState('instagram')
  const [referenceImage, setReferenceImage] = useState<{ file: File; preview: string } | null>(null)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<GeneratedPost | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setReferenceImage({ file, preview: URL.createObjectURL(file) })
    }
    e.target.value = ''
  }

  const handleGenerate = async () => {
    if (isDemo || !prompt.trim()) return
    setGenerating(true)
    setError(null)
    setResult(null)

    try {
      const brandPayload = brand ? {
        business_name: brand.business_name,
        business_type: brand.business_type,
        voice_profile: brand.voice_profile ?? {},
      } : undefined

      const res = await contentApi.generatePost(merchantId, {
        prompt,
        platform,
        brand: brandPayload,
        websiteContext: websiteContext ?? undefined,
        referenceImageUrl: referenceImage ? referenceImage.preview : undefined,
      })

      setResult({ ...res.post, platform: res.platform })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate post')
    } finally {
      setGenerating(false)
    }
  }

  const handleCopy = () => {
    if (!result) return
    const text = `${result.hook}\n\n${result.body}\n\n${result.call_to_action}\n\n${result.hashtags.join(' ')}`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare size={18} className="text-[#1A8FD6]" />
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Generate Post</h2>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[#A1A1A8]">
          <Coins size={12} className="text-amber-400" />
          100 credits/post
        </div>
      </div>

      {/* Generator Card */}
      <div className="card p-5 space-y-4">
        {/* Prompt */}
        <div>
          <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
            What should this post be about?
          </label>
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="e.g. Promote our new summer menu, highlight the grilled peach salad..."
            rows={3}
            className="w-full bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-4 py-3 text-sm text-[#F5F5F7] placeholder:text-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40 resize-none"
          />
        </div>

        {/* Platform + Reference Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Platform */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
              Platform
            </label>
            <div className="flex flex-wrap gap-1.5">
              {PLATFORMS.map(p => {
                const Icon = p.icon
                return (
                  <button
                    key={p.id}
                    onClick={() => setPlatform(p.id)}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-[11px] font-medium transition-all ${
                      platform === p.id
                        ? 'border-[#1A8FD6]/40 bg-[#1A8FD6]/10 text-[#1A8FD6]'
                        : 'border-[#1F1F23] text-[#A1A1A8] hover:border-[#1F1F23]/80'
                    }`}
                  >
                    <Icon size={12} />
                    {p.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Reference Image Upload */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
              Reference Image (optional)
            </label>
            {referenceImage ? (
              <div className="flex items-center gap-3 p-2 rounded-lg border border-[#1F1F23] bg-[#0A0A0B]">
                <img src={referenceImage.preview} alt="" className="w-12 h-12 rounded-md object-cover" />
                <span className="text-[11px] text-[#F5F5F7] truncate flex-1">{referenceImage.file.name}</span>
                <button
                  onClick={() => setReferenceImage(null)}
                  className="p-1 rounded hover:bg-[#1F1F23] transition-colors"
                >
                  <X size={12} className="text-[#A1A1A8]" />
                </button>
              </div>
            ) : (
              <label className="flex items-center gap-2 p-3 rounded-lg border-2 border-dashed border-[#1F1F23] hover:border-[#1A8FD6]/30 cursor-pointer transition-colors">
                <Upload size={14} className="text-[#A1A1A8]/40" />
                <span className="text-[11px] text-[#A1A1A8]/40">Upload a photo to reference in the post</span>
                <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
              </label>
            )}
          </div>
        </div>

        {/* Generate */}
        <div className="flex items-center justify-between pt-3 border-t border-[#1F1F23]">
          <span className="text-[10px] text-[#A1A1A8]">
            {brand ? `Using ${brand.business_name} brand voice` : 'Connect POS for brand voice'}
          </span>
          {isDemo ? (
            <button disabled className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F1F23] text-[#A1A1A8]/50 text-sm font-medium cursor-not-allowed">
              <Lock size={14} /> Sign up to generate
            </button>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={generating || !prompt.trim() || creditBalance < 100}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1A8FD6] text-white text-sm font-semibold hover:bg-[#1A8FD6]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generating ? (
                <><Loader2 size={14} className="animate-spin" /> Generating...</>
              ) : (
                <><Wand2 size={14} /> Generate Post</>
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

      {/* Generated Result */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-5 space-y-4 border-[#1A8FD6]/20 bg-gradient-to-br from-[#1A8FD6]/5 to-transparent"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-2">
              <Check size={14} className="text-green-400" />
              Post Generated
            </h3>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#1F1F23] text-[10px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
            >
              {copied ? <><Check size={10} className="text-green-400" /> Copied</> : <><Copy size={10} /> Copy All</>}
            </button>
          </div>

          {/* Preview */}
          <div className="bg-[#0A0A0B] rounded-lg border border-[#1F1F23] p-4 space-y-3">
            <p className="text-sm font-semibold text-[#F5F5F7]">{result.hook}</p>
            <p className="text-sm text-[#A1A1A8] whitespace-pre-wrap">{result.body}</p>
            <p className="text-sm text-[#1A8FD6]">{result.call_to_action}</p>
            <div className="flex flex-wrap gap-1.5">
              {result.hashtags.map((tag, i) => (
                <span key={i} className="text-[10px] text-[#1A8FD6]/70 bg-[#1A8FD6]/10 px-1.5 py-0.5 rounded">
                  <Hash size={8} className="inline mr-0.5" />{tag.replace('#', '')}
                </span>
              ))}
            </div>
          </div>

          {result.suggested_image_prompt && (
            <div className="flex items-start gap-2 p-3 bg-purple-500/5 rounded-lg border border-purple-500/20">
              <ImageIcon size={12} className="text-purple-400 mt-0.5" />
              <div>
                <p className="text-[10px] font-medium text-purple-400">Suggested image</p>
                <p className="text-[10px] text-[#A1A1A8]">{result.suggested_image_prompt}</p>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  )
}
