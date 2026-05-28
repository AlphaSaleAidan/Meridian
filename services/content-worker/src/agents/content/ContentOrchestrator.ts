/**
 * ContentOrchestrator
 *
 * Master coordinator for the content system. Handles:
 * - onboardMerchant(): Create Ayrshare profile, upsert content_brands,
 *   queue brand extraction + calendar generation
 * - generateWeeklyCalendar(): Pull POS snapshot + foot traffic,
 *   plan calendar via Claude Sonnet, create content_posts rows,
 *   queue individual generation jobs
 */

import Anthropic from '@anthropic-ai/sdk'
import { supabase } from '../../lib/supabase.js'
import { createAyrshareProfile } from '../../lib/ayrshare.js'
import { contentQueue, JOBS } from '../../queues/contentQueue.js'

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY ?? '' })

// ── Types ───────────────────────────────────────────────────────────────────

interface CalendarSlot {
  day: string
  time: string
  postType: 'social' | 'article' | 'video_brief' | 'gmb_post'
  platform: string
  topic: string
  targetKeyword?: string
  imagePrompt?: string
}

interface POSSnapshot {
  topProducts: Array<{ name: string; category: string; revenue: number }>
  totalRevenue: number
  transactionCount: number
  avgTicket: number
}

// ── Onboarding ──────────────────────────────────────────────────────────────

export async function onboardMerchant(params: {
  merchantId: string
  businessName: string
  businessType: string
  websiteUrl?: string
  contentTier: 'starter' | 'growth' | 'command'
  approvalEmail?: string
  autoPublish?: boolean
}): Promise<{ brandId: string; ayrshareProfileKey: string }> {
  if (!supabase) throw new Error('Supabase client not initialized')

  // Create Ayrshare sub-profile for this merchant
  let profileKey = ''
  try {
    const profile = await createAyrshareProfile({
      title: `Meridian - ${params.businessName}`,
    })
    profileKey = profile.profileKey
  } catch (err) {
    console.warn('[orchestrator] Ayrshare profile creation failed:', err)
  }

  // Upsert content_brands row
  const { data: brand, error: brandErr } = await supabase
    .from('content_brands')
    .upsert(
      {
        merchant_id: params.merchantId,
        business_name: params.businessName,
        business_type: params.businessType,
        website_url: params.websiteUrl ?? null,
        content_tier: params.contentTier,
        tier_activated_at: new Date().toISOString(),
        ayrshare_profile_key: profileKey || null,
        approval_email: params.approvalEmail ?? null,
        auto_publish: params.autoPublish ?? false,
        voice_profile: {},
      },
      { onConflict: 'merchant_id' }
    )
    .select('id')
    .single()

  if (brandErr || !brand) {
    throw new Error(`Failed to upsert brand: ${brandErr?.message}`)
  }

  const brandId = brand.id as string

  // Queue brand extraction job
  await contentQueue.add(
    JOBS.BRAND_EXTRACTION,
    { merchantId: params.merchantId },
    { jobId: `brand-${params.merchantId}-${Date.now()}` }
  )

  await logJob(params.merchantId, 'brand_extraction', {
    merchantId: params.merchantId,
  })

  // Queue initial calendar generation
  await contentQueue.add(
    JOBS.CALENDAR_GENERATION,
    {
      merchantId: params.merchantId,
      contentTier: params.contentTier,
    },
    {
      jobId: `cal-${params.merchantId}-${Date.now()}`,
      delay: 30_000, // Wait 30s for brand extraction to finish
    }
  )

  await logJob(params.merchantId, 'calendar_generation', {
    merchantId: params.merchantId,
    contentTier: params.contentTier,
  })

  return { brandId, ayrshareProfileKey: profileKey }
}

// ── Weekly Calendar Generation ──────────────────────────────────────────────

export async function generateWeeklyCalendar(params: {
  merchantId: string
  contentTier: 'starter' | 'growth' | 'command'
  weekStart?: string
}): Promise<{ calendarId: string; postCount: number }> {
  if (!supabase) throw new Error('Supabase client not initialized')

  const weekStart = params.weekStart ?? getThisMonday()

  // Pull data for planning
  const [posSnapshot, footTrafficPeak, brand] = await Promise.all([
    getPOSSnapshot(params.merchantId),
    getFootTrafficPeak(params.merchantId),
    supabase
      .from('content_brands')
      .select('business_name, business_type, voice_profile')
      .eq('merchant_id', params.merchantId)
      .single()
      .then((r) => r.data),
  ])

  if (!brand) {
    throw new Error(`No brand found for merchant ${params.merchantId}`)
  }

  // Plan calendar via Claude Sonnet
  const slots = await planCalendar({
    merchantId: params.merchantId,
    businessName: brand.business_name as string,
    businessType: brand.business_type as string,
    contentTier: params.contentTier,
    posSnapshot,
    footTrafficPeak,
    weekStart,
  })

  // Create content_calendars row
  const { data: calendar, error: calErr } = await supabase
    .from('content_calendars')
    .upsert(
      {
        merchant_id: params.merchantId,
        week_start: weekStart,
        status: 'active',
        plan: slots,
        pos_snapshot: posSnapshot,
        foot_traffic_peak: footTrafficPeak,
      },
      { onConflict: 'merchant_id,week_start' }
    )
    .select('id')
    .single()

  if (calErr || !calendar) {
    throw new Error(`Failed to create calendar: ${calErr?.message}`)
  }

  const calendarId = calendar.id as string

  // Create content_posts rows and queue generation jobs
  let postCount = 0

  for (const slot of slots) {
    const scheduledAt = slotToDateTime(weekStart, slot.day, slot.time)

    // Insert content_posts row
    const { data: post, error: postErr } = await supabase
      .from('content_posts')
      .insert({
        merchant_id: params.merchantId,
        calendar_id: calendarId,
        post_type: slot.postType,
        platform: slot.platform,
        title: slot.topic,
        target_keyword: slot.targetKeyword ?? null,
        image_prompt: slot.imagePrompt ?? null,
        status: 'generating',
        scheduled_at: scheduledAt,
        pos_data_reference: posSnapshot,
      })
      .select('id')
      .single()

    if (postErr || !post) {
      console.error(`[orchestrator] Failed to create post:`, postErr)
      continue
    }

    const postId = post.id as string

    // Queue the appropriate generation job
    if (slot.postType === 'social' || slot.postType === 'gmb_post') {
      await contentQueue.add(JOBS.GENERATE_SOCIAL_POST, {
        postId,
        merchantId: params.merchantId,
        platform: slot.platform,
        topic: slot.topic,
        posDataReference: posSnapshot,
      })

      // Also queue image generation if there's a prompt
      if (slot.imagePrompt) {
        await contentQueue.add(
          JOBS.GENERATE_IMAGE,
          {
            postId,
            merchantId: params.merchantId,
            prompt: slot.imagePrompt,
            platform: slot.platform,
          },
          { delay: 5_000 }
        )
      }
    } else if (slot.postType === 'article') {
      await contentQueue.add(JOBS.GENERATE_ARTICLE, {
        postId,
        merchantId: params.merchantId,
        title: slot.topic,
        targetKeyword: slot.targetKeyword ?? slot.topic,
        wordCount: targetWordCount(params.contentTier),
        contentTier: params.contentTier,
        posDataReference: posSnapshot,
      })
    } else if (slot.postType === 'video_brief') {
      await contentQueue.add(JOBS.GENERATE_VIDEO, {
        postId,
        merchantId: params.merchantId,
        prompt: slot.imagePrompt ?? slot.topic,
        platform: slot.platform,
      })
    }

    postCount++
  }

  return { calendarId, postCount }
}

// ── Internal Helpers ────────────────────────────────────────────────────────

async function planCalendar(params: {
  merchantId: string
  businessName: string
  businessType: string
  contentTier: 'starter' | 'growth' | 'command'
  posSnapshot: POSSnapshot | null
  footTrafficPeak: string | null
  weekStart: string
}): Promise<CalendarSlot[]> {
  const postsPerWeek =
    params.contentTier === 'command'
      ? 14
      : params.contentTier === 'growth'
        ? 7
        : 3

  const systemPrompt = `You are a content strategist for local businesses. Plan a weekly content calendar. Return valid JSON only — an array of content slot objects.`

  const userPrompt = `Plan a ${postsPerWeek}-post content calendar for this week (starting ${params.weekStart}):

Business: ${params.businessName} (${params.businessType})
Content tier: ${params.contentTier}
${params.footTrafficPeak ? `Peak foot traffic: ${params.footTrafficPeak}` : ''}
${params.posSnapshot ? `Top products: ${params.posSnapshot.topProducts.slice(0, 5).map((p) => p.name).join(', ')}. Avg ticket: $${(params.posSnapshot.avgTicket / 100).toFixed(2)}` : ''}

Rules:
- Mix social posts, articles, and occasional video briefs
- Starter tier: social only, Growth: social + 1 article, Command: social + 2 articles + 1 video
- Post times should match peak traffic when possible
- Each post needs a specific topic tied to products or seasonal trends
- Include image generation prompts for visual posts
- Distribute across platforms: instagram, facebook, twitter, google_my_business

Return a JSON array:
[
  {
    "day": "monday|tuesday|...|sunday",
    "time": "HH:MM",
    "postType": "social|article|video_brief|gmb_post",
    "platform": "instagram|facebook|twitter|linkedin|tiktok|google_my_business",
    "topic": "specific post topic",
    "targetKeyword": "optional SEO keyword for articles",
    "imagePrompt": "optional image generation prompt"
  }
]`

  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 2048,
    messages: [{ role: 'user', content: userPrompt }],
    system: systemPrompt,
  })

  const textBlock = response.content.find((b) => b.type === 'text')
  if (!textBlock || textBlock.type !== 'text') {
    throw new Error('Claude returned no calendar plan')
  }

  let jsonStr = textBlock.text
  const match = jsonStr.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (match) jsonStr = match[1]

  const slots = JSON.parse(jsonStr.trim()) as CalendarSlot[]

  // Validate and cap at expected count
  return slots.slice(0, postsPerWeek).map((slot) => ({
    day: slot.day ?? 'monday',
    time: slot.time ?? '10:00',
    postType: slot.postType ?? 'social',
    platform: slot.platform ?? 'instagram',
    topic: slot.topic ?? 'Weekly update',
    targetKeyword: slot.targetKeyword,
    imagePrompt: slot.imagePrompt,
  }))
}

async function getPOSSnapshot(merchantId: string): Promise<POSSnapshot | null> {
  if (!supabase) return null

  try {
    // Get top products from recent POS data
    const { data: items } = await supabase
      .from('pos_items')
      .select('name, category, total_revenue')
      .eq('org_id', merchantId)
      .order('total_revenue', { ascending: false })
      .limit(10)

    if (!items || items.length === 0) return null

    const topProducts = items.map(
      (i: { name: string; category: string; total_revenue: number }) => ({
        name: i.name,
        category: i.category,
        revenue: i.total_revenue,
      })
    )

    const totalRevenue = topProducts.reduce((sum, p) => sum + p.revenue, 0)

    // Get recent transaction stats
    const { data: stats } = await supabase
      .from('pos_transactions')
      .select('id, total_amount')
      .eq('org_id', merchantId)
      .gte(
        'created_at',
        new Date(Date.now() - 7 * 24 * 3600_000).toISOString()
      )
      .limit(1000)

    const transactions = stats ?? []
    const transactionCount = transactions.length
    const sumAmount = transactions.reduce(
      (sum, t: { total_amount: number }) => sum + (t.total_amount ?? 0),
      0
    )
    const avgTicket = transactionCount > 0 ? Math.round(sumAmount / transactionCount) : 0

    return { topProducts, totalRevenue, transactionCount, avgTicket }
  } catch {
    return null
  }
}

async function getFootTrafficPeak(merchantId: string): Promise<string | null> {
  if (!supabase) return null

  try {
    const { data } = await supabase
      .from('foot_traffic_patterns')
      .select('peak_hour, peak_day')
      .eq('org_id', merchantId)
      .order('created_at', { ascending: false })
      .limit(1)
      .single()

    if (!data) return null

    return `${data.peak_day ?? 'Saturday'} at ${data.peak_hour ?? '12:00'}`
  } catch {
    return null
  }
}

function targetWordCount(tier: 'starter' | 'growth' | 'command'): number {
  switch (tier) {
    case 'command':
      return 2000
    case 'growth':
      return 1200
    case 'starter':
    default:
      return 800
  }
}

function getThisMonday(): string {
  const now = new Date()
  const day = now.getDay()
  const diff = day === 0 ? -6 : 1 - day
  const monday = new Date(now)
  monday.setDate(now.getDate() + diff)
  return monday.toISOString().split('T')[0]
}

function slotToDateTime(
  weekStart: string,
  dayName: string,
  time: string
): string {
  const dayOffsets: Record<string, number> = {
    monday: 0,
    tuesday: 1,
    wednesday: 2,
    thursday: 3,
    friday: 4,
    saturday: 5,
    sunday: 6,
  }

  const offset = dayOffsets[dayName.toLowerCase()] ?? 0
  const baseDate = new Date(weekStart)
  baseDate.setDate(baseDate.getDate() + offset)

  const [hours, minutes] = (time ?? '10:00').split(':').map(Number)
  baseDate.setHours(hours ?? 10, minutes ?? 0, 0, 0)

  return baseDate.toISOString()
}

async function logJob(
  merchantId: string,
  jobType: string,
  payload: Record<string, unknown>
): Promise<void> {
  if (!supabase) return

  try {
    await supabase.from('content_jobs').insert({
      merchant_id: merchantId,
      job_type: jobType,
      status: 'pending',
      payload,
    })
  } catch (err) {
    console.error(`[orchestrator] Failed to log job:`, err)
  }
}
