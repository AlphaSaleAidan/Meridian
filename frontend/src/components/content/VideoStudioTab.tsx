import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Video,
  Play,
  Clock,
  Sparkles,
  Instagram,
  Facebook,
  Music2,
  ChevronDown,
  Wand2,
  Zap,
  Film,
  Loader2,
  Check,
  Download,
  Eye,
  Coins,
  Lock,
} from 'lucide-react'
import { isCanadaPath } from '@/lib/demo-context'
import { contentApi } from '@/lib/content-api'

// ── Types ──────────────────────────────────────────────────────────────────

type VideoModel = 'kling-v3' | 'kling-v2.5-turbo' | 'seedance-2' | 'seedance-2-fast' | 'minimax-video' | 'ltx-video' | 'wan-2.5' | 'hunyuan' | 'veo-3.1' | 'mochi'
type VideoStyle = 'product_spotlight' | 'behind_the_scenes' | 'appetizing_food' | 'before_after' | 'testimonial_scene' | 'seasonal_promo' | 'atmosphere'

interface ModelInfo {
  name: string
  desc: string
  maxDuration: number
  costCredits: number
  badge?: string
}

const MODELS: Record<VideoModel, ModelInfo> = {
  'ltx-video':         { name: 'LTX Video 13B',    desc: 'Fast, affordable',        maxDuration: 10, costCredits: 200 },
  'wan-2.5':           { name: 'Wan 2.5',           desc: 'Alibaba, great quality',  maxDuration: 5,  costCredits: 200 },
  'mochi':             { name: 'Mochi v1',          desc: 'Best motion realism',     maxDuration: 5,  costCredits: 300 },
  'hunyuan':           { name: 'HunyuanVideo',      desc: 'Tencent, cinematic',      maxDuration: 5,  costCredits: 300 },
  'minimax-video':     { name: 'MiniMax Hailuo',    desc: 'Smooth, reliable',        maxDuration: 6,  costCredits: 300 },
  'seedance-2-fast':   { name: 'Seedance 2 Fast',   desc: 'ByteDance, quick',        maxDuration: 10, costCredits: 300, badge: 'NEW' },
  'kling-v2.5-turbo':  { name: 'Kling 2.5 Turbo',   desc: 'Fast cinematic',          maxDuration: 10, costCredits: 400 },
  'seedance-2':        { name: 'Seedance 2.0',      desc: 'ByteDance, cinematic+audio', maxDuration: 10, costCredits: 500, badge: 'CINEMATIC' },
  'kling-v3':          { name: 'Kling v3 Pro',      desc: 'Top-tier commercial',     maxDuration: 10, costCredits: 600, badge: 'PRO' },
  'veo-3.1':           { name: 'Veo 3.1',           desc: 'Google, highest quality',  maxDuration: 8,  costCredits: 800, badge: 'BEST' },
}

const STYLES: { id: VideoStyle; label: string; emoji: string; desc: string }[] = [
  { id: 'product_spotlight', label: 'Product Spotlight', emoji: '🎯', desc: 'Cinematic hero product reveal' },
  { id: 'appetizing_food',   label: 'Food Close-Up',     emoji: '🍔', desc: 'Slow-mo food porn' },
  { id: 'behind_the_scenes', label: 'Behind the Scenes', emoji: '🎬', desc: 'Authentic preparation footage' },
  { id: 'atmosphere',        label: 'Vibe / Atmosphere',  emoji: '✨', desc: 'Immersive establishing shot' },
  { id: 'before_after',      label: 'Before & After',    emoji: '🔄', desc: 'Satisfying transformation' },
  { id: 'seasonal_promo',    label: 'Seasonal Promo',    emoji: '🎉', desc: 'Timely festive energy' },
  { id: 'testimonial_scene', label: 'Happy Customer',    emoji: '😊', desc: 'Lifestyle scene with customer' },
]

const PLATFORMS = [
  { id: 'instagram_reel', label: 'IG Reels',    icon: Instagram, aspect: '9:16' },
  { id: 'tiktok',         label: 'TikTok',      icon: Music2,    aspect: '9:16' },
  { id: 'facebook',       label: 'Facebook',     icon: Facebook,  aspect: '16:9' },
  { id: 'instagram_feed', label: 'IG Feed',      icon: Instagram, aspect: '1:1' },
]

// ── Demo Videos ────────────────────────────────────────────────────────────

const DEMO_VIDEOS = [
  {
    id: 'dv-1',
    platform: 'instagram_reel',
    style: 'appetizing_food' as VideoStyle,
    model: 'kling-v3' as VideoModel,
    prompt: 'Slow-motion cheese pull on a gourmet burger, warm kitchen lighting, steam rising',
    duration: 5,
    status: 'completed' as const,
    thumbnailUrl: 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=300&h=534&fit=crop&q=80',
    createdAt: '2 hours ago',
  },
  {
    id: 'dv-2',
    platform: 'tiktok',
    style: 'behind_the_scenes' as VideoStyle,
    model: 'seedance-2' as VideoModel,
    prompt: 'Barista pouring latte art in slow motion, morning light through cafe windows',
    duration: 6,
    status: 'completed' as const,
    thumbnailUrl: 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=300&h=534&fit=crop&q=80',
    createdAt: '5 hours ago',
  },
  {
    id: 'dv-3',
    platform: 'facebook',
    style: 'atmosphere' as VideoStyle,
    model: 'veo-3.1' as VideoModel,
    prompt: 'Slow dolly through cozy restaurant interior, candlelit tables, warm ambiance',
    duration: 10,
    status: 'completed' as const,
    thumbnailUrl: 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=300&h=169&fit=crop&q=80',
    createdAt: '1 day ago',
  },
]

// ── Component ──────────────────────────────────────────────────────────────

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
}

interface DirectorNotes {
  style_notes: string
  model_recommendation: string
  original_prompt: string
}

interface GeneratedResult {
  videoUrl: string
  model: string
  durationSeconds?: number
  director?: DirectorNotes
  enhanced_prompt?: string
}

export default function VideoStudioTab({ isDemo, creditBalance, merchantId, brand }: Props) {
  const [prompt, setPrompt] = useState('')
  const [selectedModel, setSelectedModel] = useState<VideoModel>('seedance-2-fast')
  const [selectedStyle, setSelectedStyle] = useState<VideoStyle>('product_spotlight')
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['instagram_reel'])
  const [duration, setDuration] = useState(5)
  const [showModelPicker, setShowModelPicker] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [previewVideo, setPreviewVideo] = useState<string | null>(null)
  const [generatedResult, setGeneratedResult] = useState<GeneratedResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const modelInfo = MODELS[selectedModel]
  const totalCost = modelInfo.costCredits * selectedPlatforms.length

  const togglePlatform = (id: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    )
  }

  const [genStatus, setGenStatus] = useState('')

  const handleGenerate = async () => {
    if (isDemo || !prompt.trim() || selectedPlatforms.length === 0) return
    setGenerating(true)
    setError(null)
    setGeneratedResult(null)
    setGenStatus('Submitting to AI...')

    try {
      const platform = selectedPlatforms[0]
      const brandPayload = brand ? {
        business_name: brand.business_name,
        business_type: brand.business_type,
        voice_profile: brand.voice_profile ?? {},
      } : undefined

      setGenStatus(brand ? 'Director enhancing prompt...' : 'Submitting to AI...')

      const res = await contentApi.generateVideo(merchantId, {
        prompt,
        platform,
        model: selectedModel,
        style: selectedStyle,
        durationSeconds: duration,
        brand: brandPayload,
        enhance: !!brand,
      })

      if (res.videoUrl) {
        setGeneratedResult({
          videoUrl: res.videoUrl,
          model: MODELS[selectedModel].name,
          durationSeconds: duration,
          director: res.director,
        })
        setGenerating(false)
        return
      }

      if (!res.jobId) {
        throw new Error('No job ID returned')
      }

      setGenStatus(res.director ? 'Director enhanced — generating video...' : 'Generating video...')
      const jobId = res.jobId
      let directorInfo = res.director
      for (let i = 0; i < 180; i++) {
        await new Promise(r => setTimeout(r, 3000))
        const status = await contentApi.videoStatus(jobId)
        const elapsed = Math.round(status.elapsed ?? i * 3)
        setGenStatus(`Generating video... ${elapsed}s (${status.fal_status ?? 'processing'})`)
        if (status.director && !directorInfo) directorInfo = status.director

        if (status.status === 'completed' && status.videoUrl) {
          setGeneratedResult({
            videoUrl: status.videoUrl,
            model: MODELS[selectedModel].name,
            durationSeconds: duration,
            director: directorInfo,
            enhanced_prompt: status.enhanced_prompt,
          })
          setGenerating(false)
          return
        }

        if (status.status === 'failed') {
          throw new Error(status.error ?? 'Generation failed')
        }
      }

      throw new Error('Generation timed out — try a faster model like Seedance 2 Fast')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate video. Please try again.')
      setGenerating(false)
    }
  }

  const resetResult = () => {
    setGeneratedResult(null)
    setError(null)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Film size={18} className="text-purple-400" />
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Video Studio</h2>
          <span className="text-[10px] font-medium text-purple-400 bg-purple-500/10 border border-purple-500/20 px-1.5 py-0.5 rounded">
            BETA
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[#A1A1A8]">
          <Coins size={12} className="text-amber-400" />
          {creditBalance} credits
        </div>
      </div>

      {/* Creator Panel */}
      <div className="card p-5 space-y-5">
        {/* Prompt Input */}
        <div>
          <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
            Describe your video ad
          </label>
          <div className="relative">
            <textarea
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder="e.g. Close-up of our signature burger being assembled, cheese melting over the patty, warm kitchen lighting..."
              rows={3}
              className="w-full bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-4 py-3 text-sm text-[#F5F5F7] placeholder:text-[#A1A1A8]/30 focus:outline-none focus:border-purple-500/40 resize-none"
            />
            <button
              className="absolute right-2 bottom-2 flex items-center gap-1 text-[10px] font-medium text-purple-400 hover:text-purple-300 bg-purple-500/10 px-2 py-1 rounded transition-colors"
              title="AI-generate a prompt based on your business"
            >
              <Wand2 size={10} /> Auto-write
            </button>
          </div>
        </div>

        {/* Style Picker */}
        <div>
          <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
            Video Style
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {STYLES.map(s => (
              <button
                key={s.id}
                onClick={() => setSelectedStyle(s.id)}
                className={`p-2.5 rounded-lg border text-left transition-all ${
                  selectedStyle === s.id
                    ? 'border-purple-500/40 bg-purple-500/10'
                    : 'border-[#1F1F23] hover:border-[#1F1F23]/80 bg-[#0A0A0B]'
                }`}
              >
                <span className="text-base">{s.emoji}</span>
                <p className="text-[11px] font-medium text-[#F5F5F7] mt-1">{s.label}</p>
                <p className="text-[9px] text-[#A1A1A8]">{s.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Platform + Duration Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Platforms */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
              Platforms
            </label>
            <div className="flex flex-wrap gap-2">
              {PLATFORMS.map(p => {
                const Icon = p.icon
                const active = selectedPlatforms.includes(p.id)
                return (
                  <button
                    key={p.id}
                    onClick={() => togglePlatform(p.id)}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-[11px] font-medium transition-all ${
                      active
                        ? 'border-purple-500/40 bg-purple-500/10 text-purple-300'
                        : 'border-[#1F1F23] text-[#A1A1A8] hover:border-[#1F1F23]/80'
                    }`}
                  >
                    <Icon size={12} />
                    {p.label}
                    <span className="text-[9px] text-[#A1A1A8]">{p.aspect}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Duration */}
          <div>
            <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
              Duration: {duration}s
            </label>
            <input
              type="range"
              min={3}
              max={modelInfo.maxDuration}
              value={duration}
              onChange={e => setDuration(Number(e.target.value))}
              className="w-full accent-purple-500"
            />
            <div className="flex justify-between text-[9px] text-[#A1A1A8] mt-1">
              <span>3s</span>
              <span>{modelInfo.maxDuration}s max</span>
            </div>
          </div>
        </div>

        {/* Model Picker */}
        <div>
          <label className="text-[11px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
            AI Model
          </label>
          <button
            onClick={() => setShowModelPicker(!showModelPicker)}
            className="w-full flex items-center justify-between px-4 py-3 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] hover:border-[#1F1F23]/80 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-purple-400" />
              <span className="text-sm text-[#F5F5F7]">{modelInfo.name}</span>
              <span className="text-[10px] text-[#A1A1A8]">{modelInfo.desc}</span>
              {modelInfo.badge && (
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                  modelInfo.badge === 'PRO' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                }`}>
                  {modelInfo.badge}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-amber-400">{modelInfo.costCredits} credits/video</span>
              <ChevronDown size={14} className={`text-[#A1A1A8] transition-transform ${showModelPicker ? 'rotate-180' : ''}`} />
            </div>
          </button>

          <AnimatePresence>
            {showModelPicker && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="mt-2 space-y-1">
                  {(Object.entries(MODELS) as [VideoModel, ModelInfo][]).map(([id, m]) => (
                    <button
                      key={id}
                      onClick={() => { setSelectedModel(id); setShowModelPicker(false); setDuration(d => Math.min(d, m.maxDuration)) }}
                      className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg transition-colors ${
                        selectedModel === id
                          ? 'bg-purple-500/10 border border-purple-500/30'
                          : 'hover:bg-[#1F1F23]/50 border border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-[#F5F5F7]">{m.name}</span>
                        <span className="text-[10px] text-[#A1A1A8]">{m.desc}</span>
                        {m.badge && (
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                            m.badge === 'PRO' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                          }`}>
                            {m.badge}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] text-[#A1A1A8]">up to {m.maxDuration}s</span>
                        <span className="text-[10px] text-amber-400">{m.costCredits} credits</span>
                        {selectedModel === id && <Check size={12} className="text-purple-400" />}
                      </div>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Generate Button */}
        <div className="flex items-center justify-between pt-2 border-t border-[#1F1F23]">
          <div className="text-xs text-[#A1A1A8]">
            {selectedPlatforms.length} platform{selectedPlatforms.length !== 1 ? 's' : ''} × {modelInfo.costCredits} credits = <span className="text-amber-400 font-medium">{totalCost} credits total</span>
          </div>
          {isDemo ? (
            <button
              disabled
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F1F23] text-[#A1A1A8]/50 text-sm font-medium cursor-not-allowed"
            >
              <Lock size={14} /> Sign up to generate
            </button>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={generating || !prompt.trim() || selectedPlatforms.length === 0 || creditBalance < totalCost}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-purple-600 text-white text-sm font-semibold hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generating ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> {genStatus || 'Generating...'}
                </>
              ) : (
                <>
                  <Zap size={14} /> Generate Video{selectedPlatforms.length > 1 ? 's' : ''}
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-4 border-red-500/20 bg-red-500/5"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm text-red-400">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-[10px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] flex-shrink-0"
            >
              Dismiss
            </button>
          </div>
        </motion.div>
      )}

      {/* Generated Result Card */}
      {generatedResult && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="card overflow-hidden border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-transparent"
        >
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-2">
                <Check size={14} className="text-green-400" />
                Video Generated
              </h3>
              <div className="flex items-center gap-2 text-[10px] text-[#A1A1A8]">
                <span className="bg-purple-500/10 text-purple-400 px-1.5 py-0.5 rounded font-medium">
                  {generatedResult.model}
                </span>
                {generatedResult.durationSeconds && (
                  <span className="flex items-center gap-1">
                    <Clock size={10} /> {generatedResult.durationSeconds}s
                  </span>
                )}
              </div>
            </div>

            {/* Director Enhancement Notes */}
            {generatedResult.director && (
              <div className="rounded-lg bg-[#0A0A0B] border border-purple-500/20 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5 text-[10px] font-medium text-purple-400">
                  <Wand2 size={10} />
                  Director Enhanced
                </div>
                <p className="text-[11px] text-[#A1A1A8]">{generatedResult.director.style_notes}</p>
                {generatedResult.enhanced_prompt && (
                  <details className="text-[10px] text-[#A1A1A8]/60">
                    <summary className="cursor-pointer hover:text-[#A1A1A8]">View enhanced prompt</summary>
                    <p className="mt-1 pl-2 border-l border-purple-500/20">{generatedResult.enhanced_prompt}</p>
                  </details>
                )}
              </div>
            )}

            {/* Video Player */}
            <div className="rounded-lg overflow-hidden bg-[#0A0A0B] border border-[#1F1F23]">
              <video
                src={generatedResult.videoUrl}
                controls
                className="w-full max-h-[400px]"
                preload="metadata"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              <a
                href={generatedResult.videoUrl}
                download
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-purple-600 text-white text-sm font-semibold hover:bg-purple-500 transition-colors"
              >
                <Download size={14} /> Download
              </a>
              <button
                onClick={resetResult}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-[#1F1F23] text-[#A1A1A8] text-sm font-medium hover:text-[#F5F5F7] hover:border-purple-500/30 transition-colors"
              >
                <Zap size={14} /> Generate Another
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* How Video Ads Work — demo showcase */}
      {isDemo && (
        <div className="card p-5 border-purple-500/10 bg-gradient-to-br from-purple-500/5 to-transparent">
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-3 flex items-center gap-2">
            <Video size={14} className="text-purple-400" />
            How Video Ads Work
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            {[
              { step: '1', title: 'Describe It', desc: 'Write a prompt or let AI auto-write one from your POS data', icon: Wand2 },
              { step: '2', title: 'Pick Style & Model', desc: 'Choose from 6 AI models and 7 ad styles', icon: Film },
              { step: '3', title: 'Generate', desc: '5-10 second clips in under 2 minutes', icon: Sparkles },
              { step: '4', title: 'Publish', desc: 'Auto-post to Reels, TikTok, or download', icon: Play },
            ].map(({ step, title, desc, icon: Icon }) => (
              <div key={step} className="flex gap-2.5">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-[10px] font-bold text-purple-400">
                  {step}
                </div>
                <div>
                  <p className="text-[11px] font-medium text-[#F5F5F7] flex items-center gap-1">
                    <Icon size={10} className="text-purple-400" /> {title}
                  </p>
                  <p className="text-[10px] text-[#A1A1A8] mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Videos / Demo Gallery */}
      <div>
        <h3 className="text-sm font-semibold text-[#F5F5F7] mb-3 flex items-center gap-2">
          <Clock size={14} className="text-[#A1A1A8]" />
          {isDemo ? 'Example Video Ads' : 'Recent Videos'}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {DEMO_VIDEOS.map(v => {
            const platform = PLATFORMS.find(p => p.id === v.platform)
            const PlatformIcon = platform?.icon ?? Instagram
            return (
              <div key={v.id} className="card overflow-hidden group">
                <div className="relative aspect-[9/16] sm:aspect-video bg-[#0A0A0B]">
                  <img
                    src={v.thumbnailUrl}
                    alt={v.prompt}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => setPreviewVideo(v.id)}
                      className="p-3 rounded-full bg-white/20 backdrop-blur-sm border border-white/20 hover:bg-white/30 transition-colors"
                    >
                      <Play size={20} className="text-white" fill="white" />
                    </button>
                  </div>
                  <div className="absolute top-2 left-2 flex items-center gap-1">
                    <span className="text-[9px] font-medium bg-black/60 backdrop-blur-sm text-white px-1.5 py-0.5 rounded flex items-center gap-1">
                      <PlatformIcon size={9} /> {platform?.label}
                    </span>
                  </div>
                  <div className="absolute top-2 right-2">
                    <span className="text-[9px] font-medium bg-black/60 backdrop-blur-sm text-white px-1.5 py-0.5 rounded flex items-center gap-1">
                      <Clock size={9} /> {v.duration}s
                    </span>
                  </div>
                  <div className="absolute bottom-2 left-2 right-2">
                    <span className="text-[9px] font-medium bg-purple-600/80 backdrop-blur-sm text-white px-1.5 py-0.5 rounded">
                      {MODELS[v.model].name}
                    </span>
                  </div>
                </div>
                <div className="p-3">
                  <p className="text-[11px] text-[#A1A1A8] line-clamp-2">{v.prompt}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-[10px] text-[#A1A1A8]/60">{v.createdAt}</span>
                    <div className="flex items-center gap-1">
                      <button className="p-1 rounded hover:bg-[#1F1F23] transition-colors" title="Preview">
                        <Eye size={12} className="text-[#A1A1A8]" />
                      </button>
                      <button className="p-1 rounded hover:bg-[#1F1F23] transition-colors" title="Download">
                        <Download size={12} className="text-[#A1A1A8]" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Model Comparison */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-[#F5F5F7] mb-3">Model Comparison</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-[#A1A1A8] border-b border-[#1F1F23]">
                <th className="text-left py-2 pr-4 font-medium">Model</th>
                <th className="text-left py-2 pr-4 font-medium">Max Duration</th>
                <th className="text-left py-2 pr-4 font-medium">Quality</th>
                <th className="text-left py-2 pr-4 font-medium">Speed</th>
                <th className="text-right py-2 font-medium">Credits</th>
              </tr>
            </thead>
            <tbody>
              {([
                ['LTX Video 13B', '10s', '★★★☆☆', '~20s', '200'],
                ['Wan 2.5', '5s', '★★★★☆', '~40s', '200'],
                ['Mochi v1', '5s', '★★★★☆', '~60s', '300'],
                ['HunyuanVideo', '5s', '★★★★☆', '~60s', '300'],
                ['MiniMax Hailuo', '6s', '★★★★☆', '~45s', '300'],
                ['Seedance 2 Fast', '10s', '★★★★☆', '~30s', '300'],
                ['Kling 2.5 Turbo', '10s', '★★★★☆', '~45s', '400'],
                ['Seedance 2.0', '10s', '★★★★★', '~90s', '500'],
                ['Kling v3 Pro', '10s', '★★★★★', '~90s', '600'],
                ['Veo 3.1', '8s', '★★★★★', '~120s', '800'],
              ] as const).map(([name, dur, quality, speed, cost]) => (
                <tr key={name} className="border-b border-[#1F1F23]/50 text-[#F5F5F7]">
                  <td className="py-2 pr-4 font-medium">{name}</td>
                  <td className="py-2 pr-4 text-[#A1A1A8]">{dur}</td>
                  <td className="py-2 pr-4">{quality}</td>
                  <td className="py-2 pr-4 text-[#A1A1A8]">{speed}</td>
                  <td className="py-2 text-right text-amber-400">{cost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pricing note */}
      {isDemo && (
        <div className="text-center space-y-2 py-2">
          <p className="text-xs text-[#A1A1A8]">
            Video credits start at <span className="text-amber-400 font-medium">{isCanadaPath() ? 'CA$2.75' : '$2'} for 2,000 credits</span> — enough for 10 videos with LTX or 5 with Kling.
          </p>
          <p className="text-[10px] text-[#A1A1A8]/40">
            All videos are generated via fal.ai API. No watermarks. Full commercial rights.
          </p>
        </div>
      )}
    </div>
  )
}
