/**
 * VideoAgent — Social media video ad generation.
 *
 * Generates 5–15 second video clips for Instagram Reels, TikTok, YouTube Shorts.
 * Supports multiple fal.ai video models with ad-specific prompt enhancement.
 */

import Anthropic from '@anthropic-ai/sdk'
import { generateVideo, VIDEO_MODELS, type VideoModel, type GenerateVideoResult } from '../../lib/fal-client.js'
import { uploadToR2, downloadUrl } from '../../lib/r2-upload.js'
import { supabase } from '../../lib/supabase.js'

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY ?? '' })

// ── Types ──────────────────────────────────────────────────────────────────

export type VideoAdStyle =
  | 'product_spotlight'
  | 'behind_the_scenes'
  | 'appetizing_food'
  | 'before_after'
  | 'testimonial_scene'
  | 'seasonal_promo'
  | 'atmosphere'

export interface VideoAdInput {
  merchantId: string
  prompt: string
  platform: string
  style?: VideoAdStyle
  businessType?: string
  model?: VideoModel
  durationSeconds?: number
  postId?: string
}

export interface VideoAdOutput {
  videoUrl: string
  r2Key: string
  model: VideoModel
  durationSeconds: number
  enhancedPrompt: string
}

// ── Style Templates ────────────────────────────────────────────────────────

const STYLE_TEMPLATES: Record<VideoAdStyle, string> = {
  product_spotlight:
    'Cinematic product reveal with smooth camera push-in, professional studio lighting, shallow depth of field transitioning from blur to sharp focus on the hero product, subtle particle effects, premium feel',
  behind_the_scenes:
    'Authentic handheld-style footage of preparation and craftsmanship, warm ambient lighting, close-up of hands working, real textures and materials, documentary feel with natural movement',
  appetizing_food:
    'Slow-motion food cinematography, steam rising, cheese pull, sauce drizzle, ingredients falling in slow motion, warm golden lighting, extreme close-up macro details, appetite appeal',
  before_after:
    'Split-screen or smooth transition from before state to after state, satisfying transformation, clean wipe transition, dramatic improvement reveal',
  testimonial_scene:
    'Happy customer in a natural setting enjoying the product or service, genuine smile, warm natural lighting, lifestyle photography feel, relatable and authentic',
  seasonal_promo:
    'Festive and timely atmosphere, seasonal decorations and colors, celebration mood, eye-catching and vibrant, urgency-inducing energy',
  atmosphere:
    'Immersive establishing shot of the business environment, smooth slow dolly movement, ambient lighting, inviting atmosphere, the kind of place you want to visit',
}

const BUSINESS_VIDEO_STYLE: Record<string, string> = {
  restaurant: 'warm kitchen lighting, sizzling sounds implied by steam and bubbling, chef hands plating, rustic wood and ceramic textures',
  coffee_shop: 'morning light through windows, latte art pour in slow motion, cozy interior, books and warm tones, steam from fresh cup',
  fast_food: 'dynamic quick cuts, bold colors, cheese pull close-up, crispy textures, fast-paced energy, neon reflections',
  auto_shop: 'polished chrome, hydraulic lift movement, precision tool work, clean professional garage, blue-toned lighting',
  smoke_shop: 'premium glass display, artistic vapor, dramatic backlighting, sleek dark aesthetic, luxury product showcase',
  salon: 'elegant transformation, mirror reflections, soft diffused lighting, before-and-after styling, confident result reveal',
  retail: 'product unboxing feel, clean white background to lifestyle setting transition, handling the product, texture close-ups',
}

// ── Prompt Enhancement ─────────────────────────────────────────────────────

function enhanceVideoPrompt(
  prompt: string,
  platform: string,
  style?: VideoAdStyle,
  businessType?: string
): string {
  const styleTpl = style ? STYLE_TEMPLATES[style] : STYLE_TEMPLATES.product_spotlight
  const bizStyle = businessType ? BUSINESS_VIDEO_STYLE[businessType] ?? '' : ''

  const orientation =
    platform.includes('story') || platform.includes('reel') || platform === 'tiktok'
      ? 'vertical 9:16 framing, subject centered for mobile viewing'
      : platform === 'instagram_feed'
        ? 'square 1:1 framing, subject centered'
        : 'cinematic horizontal 16:9 framing, rule of thirds'

  const base = `${prompt}. ${styleTpl}. ${bizStyle}. ${orientation}. No text overlays, no watermarks, no logos, photorealistic quality, smooth camera movement, professional color grading.`

  return base.replace(/\.\s*\./g, '.').replace(/\s+/g, ' ').trim()
}

// ── AI-Powered Prompt Generation ───────────────────────────────────────────

export async function generateVideoPrompt(params: {
  businessName: string
  businessType: string
  productName?: string
  style: VideoAdStyle
  platform: string
}): Promise<string> {
  const response = await anthropic.messages.create({
    model: 'claude-haiku-4-5-20251001',
    max_tokens: 300,
    system: 'You write video generation prompts for AI models. Output ONLY the prompt text, no explanation. Prompts should describe a 5-10 second video scene with specific camera movements, lighting, and visual details. Never include text overlays or logos in the description.',
    messages: [{
      role: 'user',
      content: `Write a ${params.style.replace(/_/g, ' ')} video ad prompt for ${params.businessName} (${params.businessType}).${params.productName ? ` Featured product: ${params.productName}.` : ''} Platform: ${params.platform}. The video should be scroll-stopping and make viewers want to visit the business.`,
    }],
  })

  const text = response.content.find(b => b.type === 'text')
  return text && text.type === 'text' ? text.text.trim() : params.productName ?? params.businessName
}

// ── Main Generation ────────────────────────────────────────────────────────

export async function generateVideoAd(input: VideoAdInput): Promise<VideoAdOutput> {
  const model = input.model ?? pickBestModel(input.durationSeconds ?? 5)
  const enhancedPrompt = enhanceVideoPrompt(
    input.prompt,
    input.platform,
    input.style,
    input.businessType
  )

  const result: GenerateVideoResult = await generateVideo({
    prompt: enhancedPrompt,
    platform: input.platform,
    durationSeconds: input.durationSeconds,
    model,
  })

  const response = await fetch(result.videoUrl)
  if (!response.ok) {
    throw new Error(`Failed to download video from fal CDN: ${response.status}`)
  }
  const videoBuffer: Buffer = Buffer.from(new Uint8Array(await response.arrayBuffer()))

  const timestamp = Date.now()
  const r2Key = `content/${input.merchantId}/videos/${timestamp}-${input.platform}-${model}.mp4`

  await uploadToR2({
    key: r2Key,
    body: videoBuffer,
    contentType: 'video/mp4',
  })

  const publicUrl = downloadUrl(r2Key)

  if (input.postId && supabase) {
    await supabase
      .from('content_posts')
      .update({
        video_url: publicUrl,
        video_model: result.model,
        video_duration: result.durationSeconds,
        updated_at: new Date().toISOString(),
      })
      .eq('id', input.postId)
  }

  return {
    videoUrl: publicUrl,
    r2Key,
    model: result.model,
    durationSeconds: result.durationSeconds,
    enhancedPrompt,
  }
}

function pickBestModel(durationSeconds: number): VideoModel {
  if (durationSeconds <= 5) return 'seedance-2-fast'
  return 'kling-v3'
}

// ── Batch Generation ───────────────────────────────────────────────────────

export async function generateVideoAdBatch(params: {
  merchantId: string
  businessName: string
  businessType: string
  platforms: string[]
  styles: VideoAdStyle[]
  productName?: string
  durationSeconds?: number
  model?: VideoModel
}): Promise<VideoAdOutput[]> {
  const results: VideoAdOutput[] = []

  for (const platform of params.platforms) {
    for (const style of params.styles) {
      const prompt = await generateVideoPrompt({
        businessName: params.businessName,
        businessType: params.businessType,
        productName: params.productName,
        style,
        platform,
      })

      const output = await generateVideoAd({
        merchantId: params.merchantId,
        prompt,
        platform,
        style,
        businessType: params.businessType,
        model: params.model,
        durationSeconds: params.durationSeconds,
      })

      results.push(output)
    }
  }

  return results
}
