/**
 * PublishAgent
 *
 * - publishToSocial(): via Ayrshare with per-merchant profileKey
 * - publishToWordPress(): via WP REST API Basic auth
 *
 * Updates content_posts status in Supabase after each publish.
 */

import { publishPost as ayrsharePublish } from '../../lib/ayrshare.js'
import { supabase } from '../../lib/supabase.js'

// ── Social Publishing ───────────────────────────────────────────────────────

export interface SocialPublishInput {
  postId: string
  merchantId: string
  platforms: string[]
  body: string
  mediaUrls?: string[]
  scheduledDate?: string
}

export interface SocialPublishOutput {
  ayrsharePostId: string
  publishedPlatforms: string[]
  publishUrl: string | null
}

export async function publishToSocial(
  input: SocialPublishInput
): Promise<SocialPublishOutput> {
  if (!supabase) throw new Error('Supabase client not initialized')

  // Get merchant's Ayrshare profile key
  const { data: brand, error: brandErr } = await supabase
    .from('content_brands')
    .select('ayrshare_profile_key, ayrshare_connected_platforms')
    .eq('merchant_id', input.merchantId)
    .single()

  if (brandErr || !brand?.ayrshare_profile_key) {
    throw new Error(
      `No Ayrshare profile for merchant ${input.merchantId}: ${brandErr?.message ?? 'profile_key missing'}`
    )
  }

  // Filter to only connected platforms
  const connectedPlatforms = (brand.ayrshare_connected_platforms as string[]) ?? []
  const activePlatforms = input.platforms.filter((p) =>
    connectedPlatforms.includes(p)
  )

  if (activePlatforms.length === 0) {
    throw new Error(
      `No connected platforms match requested: ${input.platforms.join(', ')}`
    )
  }

  // Publish via Ayrshare
  const result = await ayrsharePublish({
    profileKey: brand.ayrshare_profile_key,
    post: input.body,
    platforms: activePlatforms,
    mediaUrls: input.mediaUrls,
    scheduledDate: input.scheduledDate,
  })

  // Update post status in Supabase
  const now = new Date().toISOString()
  await supabase
    .from('content_posts')
    .update({
      status: input.scheduledDate ? 'scheduled' : 'published',
      ayrshare_post_id: result.id,
      published_at: input.scheduledDate ? null : now,
      publish_url: Object.values(result.postIds)[0] ?? null,
      updated_at: now,
    })
    .eq('id', input.postId)

  return {
    ayrsharePostId: result.id,
    publishedPlatforms: activePlatforms,
    publishUrl: Object.values(result.postIds)[0] ?? null,
  }
}

// ── WordPress Publishing ────────────────────────────────────────────────────

export interface WPPublishInput {
  postId: string
  merchantId: string
  title: string
  body: string
  slug?: string
  metaDescription?: string
  featuredImageUrl?: string
}

export interface WPPublishOutput {
  wpPostId: number
  publishUrl: string
}

export async function publishToWordPress(
  input: WPPublishInput
): Promise<WPPublishOutput> {
  if (!supabase) throw new Error('Supabase client not initialized')

  // Get merchant's WP credentials from content_brands
  const { data: brand, error: brandErr } = await supabase
    .from('content_brands')
    .select('wp_site_url, wp_app_password, wp_author_id')
    .eq('merchant_id', input.merchantId)
    .single()

  if (brandErr || !brand?.wp_site_url || !brand?.wp_app_password) {
    throw new Error(
      `No WordPress config for merchant ${input.merchantId}: ${brandErr?.message ?? 'wp credentials missing'}`
    )
  }

  const wpBaseUrl = (brand.wp_site_url as string).replace(/\/+$/, '')
  const authHeader =
    'Basic ' +
    Buffer.from(`admin:${brand.wp_app_password}`).toString('base64')

  // Build WP post payload
  const wpPayload: Record<string, unknown> = {
    title: input.title,
    content: input.body,
    status: 'publish',
    author: brand.wp_author_id ?? 1,
  }

  if (input.slug) wpPayload.slug = input.slug
  if (input.metaDescription) {
    wpPayload.excerpt = input.metaDescription
  }

  // Upload featured image if provided
  let featuredMediaId: number | undefined
  if (input.featuredImageUrl) {
    try {
      featuredMediaId = await uploadWPMedia(
        wpBaseUrl,
        authHeader,
        input.featuredImageUrl,
        input.title
      )
      wpPayload.featured_media = featuredMediaId
    } catch (err) {
      console.warn('[publish-agent] WP media upload failed:', err)
    }
  }

  // Create the WP post
  const response = await fetch(`${wpBaseUrl}/wp-json/wp/v2/posts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': authHeader,
    },
    body: JSON.stringify(wpPayload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`WP post creation failed (${response.status}): ${text}`)
  }

  const wpPost = (await response.json()) as { id: number; link: string }

  // Update content_posts in Supabase
  const now = new Date().toISOString()
  await supabase
    .from('content_posts')
    .update({
      status: 'published',
      wp_post_id: wpPost.id,
      publish_url: wpPost.link,
      published_at: now,
      updated_at: now,
    })
    .eq('id', input.postId)

  return {
    wpPostId: wpPost.id,
    publishUrl: wpPost.link,
  }
}

/**
 * Upload an image to WP media library from a URL.
 */
async function uploadWPMedia(
  wpBaseUrl: string,
  authHeader: string,
  imageUrl: string,
  altText: string
): Promise<number> {
  const imgResponse = await fetch(imageUrl)
  if (!imgResponse.ok) {
    throw new Error(`Failed to download image: ${imgResponse.status}`)
  }

  const contentType = imgResponse.headers.get('content-type') ?? 'image/webp'
  const ext = contentType.includes('png')
    ? 'png'
    : contentType.includes('jpeg') || contentType.includes('jpg')
      ? 'jpg'
      : 'webp'

  const buffer = Buffer.from(await imgResponse.arrayBuffer())
  const filename = `meridian-${Date.now()}.${ext}`

  const response = await fetch(`${wpBaseUrl}/wp-json/wp/v2/media`, {
    method: 'POST',
    headers: {
      'Authorization': authHeader,
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Type': contentType,
    },
    body: buffer,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`WP media upload failed (${response.status}): ${text}`)
  }

  const media = (await response.json()) as { id: number }

  // Set alt text
  await fetch(`${wpBaseUrl}/wp-json/wp/v2/media/${media.id}`, {
    method: 'POST',
    headers: {
      'Authorization': authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ alt_text: altText }),
  })

  return media.id
}
