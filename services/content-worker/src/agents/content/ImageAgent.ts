/**
 * ImageAgent
 *
 * - generateAdImage(): FLUX.2 Pro via fal.ai, optional logo overlay via sharp, upload to R2
 * - generateVideoClip(): Kling via fal.ai, download + upload to R2
 */

import sharp from 'sharp'
import { generateImage, generateVideo } from '../../lib/fal-client.js'
import { uploadToR2, downloadUrl } from '../../lib/r2-upload.js'
import { supabase } from '../../lib/supabase.js'

// ── Image Generation ────────────────────────────────────────────────────────

export interface AdImageInput {
  merchantId: string
  prompt: string
  platform: string
  businessType?: string
  postId?: string
  logoOverlay?: boolean
}

export interface AdImageOutput {
  imageUrl: string
  r2Key: string
  seed: number
}

export async function generateAdImage(
  input: AdImageInput
): Promise<AdImageOutput> {
  // Generate via fal.ai FLUX.2 Pro with style enhancement
  const { imageUrl: falUrl, seed } = await generateImage({
    prompt: input.prompt,
    businessType: input.businessType,
    platform: input.platform,
  })

  // Download the generated image from fal CDN
  const response = await fetch(falUrl)
  if (!response.ok) {
    throw new Error(`Failed to download from fal CDN: ${response.status}`)
  }
  const arrayBuf = await response.arrayBuffer()
  let imageBuffer: Buffer = Buffer.from(new Uint8Array(arrayBuf))

  // Optional brand logo overlay
  if (input.logoOverlay) {
    imageBuffer = await overlayLogo(imageBuffer, input.merchantId)
  }

  // Upload to R2
  const timestamp = Date.now()
  const r2Key = `content/${input.merchantId}/images/${timestamp}-${input.platform}.webp`

  // Convert to WebP for optimal size
  const webpBuffer = await sharp(imageBuffer).webp({ quality: 90 }).toBuffer()

  await uploadToR2({
    key: r2Key,
    body: webpBuffer,
    contentType: 'image/webp',
  })

  const publicUrl = downloadUrl(r2Key)

  // Update content_posts if postId provided
  if (input.postId && supabase) {
    await supabase
      .from('content_posts')
      .update({
        image_url: publicUrl,
        image_prompt: input.prompt,
        updated_at: new Date().toISOString(),
      })
      .eq('id', input.postId)
  }

  return {
    imageUrl: publicUrl,
    r2Key,
    seed,
  }
}

/**
 * Overlay the merchant's brand logo onto the generated image.
 * Looks for logo_url in content_brands, composites in bottom-right corner.
 */
async function overlayLogo(
  imageBuffer: Buffer,
  merchantId: string
): Promise<Buffer> {
  if (!supabase) return imageBuffer

  // Check if brand has a logo URL in voice_profile
  const { data: brand } = await supabase
    .from('content_brands')
    .select('voice_profile')
    .eq('merchant_id', merchantId)
    .single()

  const profile = brand?.voice_profile as Record<string, unknown> | null
  const logoUrl = profile?.logoUrl as string | undefined

  if (!logoUrl) return imageBuffer

  try {
    const logoResp = await fetch(logoUrl)
    if (!logoResp.ok) return imageBuffer

    const logoBuffer: Buffer = Buffer.from(new Uint8Array(await logoResp.arrayBuffer()))
    const metadata = await sharp(imageBuffer).metadata()
    const imgWidth = metadata.width ?? 1200
    const imgHeight = metadata.height ?? 630

    // Resize logo to 15% of image width, maintain aspect ratio
    const logoMaxWidth = Math.round(imgWidth * 0.15)
    const resizedLogo = await sharp(logoBuffer)
      .resize({ width: logoMaxWidth, withoutEnlargement: true })
      .ensureAlpha()
      .toBuffer()

    const logoMeta = await sharp(resizedLogo).metadata()
    const logoW = logoMeta.width ?? logoMaxWidth
    const logoH = logoMeta.height ?? logoMaxWidth

    // Position: bottom-right with padding
    const padding = Math.round(imgWidth * 0.03)
    const left = imgWidth - logoW - padding
    const top = imgHeight - logoH - padding

    return await sharp(imageBuffer)
      .composite([{ input: resizedLogo, left, top }])
      .toBuffer()
  } catch (err) {
    console.warn('[image-agent] Logo overlay failed, returning original:', err)
    return imageBuffer
  }
}

// ── Video Generation ────────────────────────────────────────────────────────

export interface VideoClipInput {
  merchantId: string
  prompt: string
  platform: string
  durationSeconds?: number
  postId?: string
}

export interface VideoClipOutput {
  videoUrl: string
  r2Key: string
}

export async function generateVideoClip(
  input: VideoClipInput
): Promise<VideoClipOutput> {
  // Generate via fal.ai Kling
  const { videoUrl: falUrl } = await generateVideo({
    prompt: input.prompt,
    platform: input.platform,
    durationSeconds: input.durationSeconds,
  })

  // Download from fal CDN
  const response = await fetch(falUrl)
  if (!response.ok) {
    throw new Error(`Failed to download video from fal CDN: ${response.status}`)
  }
  const videoBuffer: Buffer = Buffer.from(new Uint8Array(await response.arrayBuffer()))

  // Upload to R2
  const timestamp = Date.now()
  const r2Key = `content/${input.merchantId}/videos/${timestamp}-${input.platform}.mp4`

  await uploadToR2({
    key: r2Key,
    body: videoBuffer,
    contentType: 'video/mp4',
  })

  const publicUrl = downloadUrl(r2Key)

  // Update content_posts if postId provided
  if (input.postId && supabase) {
    await supabase
      .from('content_posts')
      .update({
        video_url: publicUrl,
        updated_at: new Date().toISOString(),
      })
      .eq('id', input.postId)
  }

  return {
    videoUrl: publicUrl,
    r2Key,
  }
}
