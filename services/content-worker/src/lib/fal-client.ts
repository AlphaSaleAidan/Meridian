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
}

interface GenerateImageResult {
  imageUrl: string
  seed: number
}

export async function generateImage(
  params: GenerateImageParams
): Promise<GenerateImageResult> {
  const dims = PLATFORM_DIMS[params.platform] ?? PLATFORM_DIMS.facebook

  const result = await fal.subscribe('fal-ai/flux-2-pro', {
    input: {
      prompt: params.prompt,
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

interface GenerateVideoParams {
  prompt: string
  platform: string
  durationSeconds?: number
}

interface GenerateVideoResult {
  videoUrl: string
}

export async function generateVideo(
  params: GenerateVideoParams
): Promise<GenerateVideoResult> {
  const dims = PLATFORM_DIMS[params.platform] ?? PLATFORM_DIMS.instagram_reel

  const result = await fal.subscribe('fal-ai/kling-video', {
    input: {
      prompt: params.prompt,
      duration: params.durationSeconds ?? 5,
      aspect_ratio:
        dims.width > dims.height
          ? '16:9'
          : dims.width < dims.height
            ? '9:16'
            : '1:1',
    },
  })

  const data = result.data as Record<string, unknown>
  const video = data.video as { url: string } | undefined

  if (!video?.url) {
    throw new Error('fal.ai returned no video')
  }

  return { videoUrl: video.url }
}
