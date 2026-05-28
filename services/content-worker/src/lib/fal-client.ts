/**
 * fal.ai client for image and video generation.
 * Uses FLUX.2 Pro for images, Kling for video.
 */

import { fal } from '@fal-ai/client'

// Configure fal.ai credentials
fal.config({
  credentials: process.env.FAL_KEY ?? '',
})

export const PLATFORM_DIMS: Record<string, { width: number; height: number }> = {
  instagram_feed: { width: 1080, height: 1080 },
  instagram_story: { width: 1080, height: 1920 },
  instagram_reel: { width: 1080, height: 1920 },
  facebook: { width: 1200, height: 630 },
  twitter: { width: 1200, height: 675 },
  linkedin: { width: 1200, height: 627 },
  tiktok: { width: 1080, height: 1920 },
  youtube_thumbnail: { width: 1280, height: 720 },
  google_my_business: { width: 1200, height: 900 },
  blog_hero: { width: 1200, height: 630 },
}

interface GenerateImageParams {
  prompt: string
  platform: string
  businessType?: string
}

interface GenerateImageResult {
  imageUrl: string
  seed: number
}

const AD_IMAGE_STYLE = `Professional product photography, studio-quality lighting, shallow depth of field, appetizing and vibrant colors, clean composition suitable for social media advertising, no text overlays, no watermarks, photorealistic`

const BUSINESS_STYLE: Record<string, string> = {
  restaurant: 'warm golden-hour lighting, rustic wood surfaces, fresh ingredients visible, steam rising from hot food, overhead flat-lay or 45-degree angle',
  coffee_shop: 'soft natural light, latte art detail, cozy cafe atmosphere, warm earth tones, close-up macro detail on the drink',
  fast_food: 'bold dramatic lighting, dynamic angle, melting cheese pull, fresh toppings in motion, vibrant saturated colors, dark moody background',
  auto_shop: 'clean professional garage, chrome and metal textures, mechanic working with precision tools, blue and grey tones, industrial aesthetic',
  smoke_shop: 'artistic product showcase, premium materials and textures, dramatic side lighting, dark elegant background, glass reflections and refractions',
}

function enhanceAdPrompt(prompt: string, platform: string, businessType?: string): string {
  const styleHints = businessType ? BUSINESS_STYLE[businessType] ?? '' : ''
  const platformHint = platform.includes('story') || platform.includes('reel') || platform === 'tiktok'
    ? 'vertical composition, subject centered'
    : platform === 'instagram_feed'
      ? 'square composition, subject centered with breathing room'
      : 'wide horizontal composition, rule of thirds'

  return `${prompt}. ${AD_IMAGE_STYLE}. ${styleHints}. ${platformHint}`.replace(/\.\s*\./g, '.')
}

export async function generateImage(
  params: GenerateImageParams
): Promise<GenerateImageResult> {
  const dims = PLATFORM_DIMS[params.platform] ?? PLATFORM_DIMS.facebook
  const enhancedPrompt = enhanceAdPrompt(params.prompt, params.platform, params.businessType)

  const result = await fal.subscribe('fal-ai/flux-2-pro', {
    input: {
      prompt: enhancedPrompt,
      image_size: {
        width: dims.width,
        height: dims.height,
      },
      safety_tolerance: '2',
    },
  })

  const data = result.data as Record<string, unknown>
  const images = data.images as Array<{ url: string }> | undefined
  const seed = (data.seed as number) ?? 0

  if (!images || images.length === 0) {
    throw new Error('fal.ai returned no images')
  }

  return {
    imageUrl: images[0].url,
    seed,
  }
}

export type VideoModel =
  | 'kling-v2'
  | 'kling-v2-master'
  | 'minimax-video'
  | 'ltx-video'
  | 'wan-v2'
  | 'hunyuan'

interface VideoModelConfig {
  falEndpoint: string
  maxDuration: number
  defaultDuration: number
  supportsAspectRatio: boolean
  costTier: 'low' | 'mid' | 'high'
}

export const VIDEO_MODELS: Record<VideoModel, VideoModelConfig> = {
  'kling-v2':        { falEndpoint: 'fal-ai/kling-video/v2/standard', maxDuration: 10, defaultDuration: 5,  supportsAspectRatio: true,  costTier: 'mid' },
  'kling-v2-master': { falEndpoint: 'fal-ai/kling-video/v2/master',   maxDuration: 10, defaultDuration: 5,  supportsAspectRatio: true,  costTier: 'high' },
  'minimax-video':   { falEndpoint: 'fal-ai/minimax-video',           maxDuration: 6,  defaultDuration: 5,  supportsAspectRatio: true,  costTier: 'mid' },
  'ltx-video':       { falEndpoint: 'fal-ai/ltx-video-v2',            maxDuration: 10, defaultDuration: 5,  supportsAspectRatio: true,  costTier: 'low' },
  'wan-v2':          { falEndpoint: 'fal-ai/wan/v2.1/1.3b',           maxDuration: 5,  defaultDuration: 5,  supportsAspectRatio: true,  costTier: 'low' },
  'hunyuan':         { falEndpoint: 'fal-ai/hunyuan-video',           maxDuration: 5,  defaultDuration: 5,  supportsAspectRatio: true,  costTier: 'mid' },
}

export interface GenerateVideoParams {
  prompt: string
  platform: string
  durationSeconds?: number
  model?: VideoModel
}

export interface GenerateVideoResult {
  videoUrl: string
  model: VideoModel
  durationSeconds: number
}

export async function generateVideo(
  params: GenerateVideoParams
): Promise<GenerateVideoResult> {
  const dims = PLATFORM_DIMS[params.platform] ?? PLATFORM_DIMS.instagram_reel
  const model = params.model ?? 'kling-v2'
  const config = VIDEO_MODELS[model]
  const duration = Math.min(params.durationSeconds ?? config.defaultDuration, config.maxDuration)

  const aspectRatio =
    dims.width > dims.height
      ? '16:9'
      : dims.width < dims.height
        ? '9:16'
        : '1:1'

  const input: Record<string, unknown> = {
    prompt: params.prompt,
    duration,
  }
  if (config.supportsAspectRatio) {
    input.aspect_ratio = aspectRatio
  }

  const result = await fal.subscribe(config.falEndpoint, { input })

  const data = result.data as Record<string, unknown>

  const videoUrl =
    (data.video as { url: string } | undefined)?.url ??
    (data.video_url as string | undefined) ??
    ((data.videos as Array<{ url: string }> | undefined)?.[0]?.url) ??
    null

  if (!videoUrl) {
    throw new Error(`fal.ai ${model} returned no video`)
  }

  return { videoUrl, model, durationSeconds: duration }
}
