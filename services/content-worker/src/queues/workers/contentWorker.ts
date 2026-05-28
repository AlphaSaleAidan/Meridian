/**
 * BullMQ Worker for 'meridian-content' queue.
 *
 * Handles all content generation job types.
 * Concurrency: 5. Updates content_jobs status at each step.
 */

import { Worker, type Job } from 'bullmq'
import { redisConnection, JOBS, type JobName } from '../contentQueue.js'
import { supabase } from '../../lib/supabase.js'

// Agent imports
import { extractBrandVoice } from '../../agents/content/BrandExtractionAgent.js'
import { generateSocialPost, generateSEOArticle } from '../../agents/content/CopyAgent.js'
import { generateAdImage } from '../../agents/content/ImageAgent.js'
import { generateVideoAd } from '../../agents/content/VideoAgent.js'
import { publishToSocial, publishToWordPress } from '../../agents/content/PublishAgent.js'
import { checkRankings } from '../../agents/content/SEOAgent.js'
import { generateWeeklyCalendar } from '../../agents/content/ContentOrchestrator.js'

// ── Job Handler ─────────────────────────────────────────────────────────────

async function processJob(job: Job): Promise<unknown> {
  const jobName = job.name as JobName
  const data = job.data as Record<string, unknown>
  const merchantId = data.merchantId as string

  console.log(`[worker] Processing ${jobName} for merchant ${merchantId}`)

  await updateJobStatus(merchantId, jobName, job.id ?? '', 'running')

  try {
    let result: unknown

    switch (jobName) {
      case JOBS.BRAND_EXTRACTION: {
        result = await extractBrandVoice(merchantId)
        break
      }

      case JOBS.CALENDAR_GENERATION: {
        result = await generateWeeklyCalendar({
          merchantId,
          contentTier: (data.contentTier as 'starter' | 'growth' | 'command') ?? 'starter',
          weekStart: data.weekStart as string | undefined,
        })
        break
      }

      case JOBS.GENERATE_SOCIAL_POST: {
        const postResult = await generateSocialPost({
          merchantId,
          platform: (data.platform as string) ?? 'instagram',
          topic: (data.topic as string) ?? '',
          posDataReference: data.posDataReference as Record<string, unknown> | undefined,
        })

        // Update the content_posts row
        if (supabase && data.postId) {
          await supabase
            .from('content_posts')
            .update({
              hook: postResult.hook,
              body: `${postResult.hook}\n\n${postResult.body}`,
              hashtags: postResult.hashtags,
              call_to_action: postResult.callToAction,
              model_used: postResult.modelUsed,
              status: 'needs_review',
              updated_at: new Date().toISOString(),
            })
            .eq('id', data.postId)
        }

        result = postResult
        break
      }

      case JOBS.GENERATE_ARTICLE: {
        const articleResult = await generateSEOArticle({
          merchantId,
          title: (data.title as string) ?? '',
          targetKeyword: (data.targetKeyword as string) ?? '',
          secondaryKeywords: data.secondaryKeywords as string[] | undefined,
          wordCount: (data.wordCount as number) ?? 1200,
          contentTier:
            (data.contentTier as 'starter' | 'growth' | 'command') ?? 'growth',
          posDataReference: data.posDataReference as Record<string, unknown> | undefined,
        })

        // Update content_posts
        if (supabase && data.postId) {
          await supabase
            .from('content_posts')
            .update({
              title: articleResult.title,
              body: articleResult.body,
              slug: articleResult.slug,
              meta_description: articleResult.metaDescription,
              word_count: articleResult.wordCount,
              model_used: articleResult.modelUsed,
              status: 'needs_review',
              updated_at: new Date().toISOString(),
            })
            .eq('id', data.postId)
        }

        result = articleResult
        break
      }

      case JOBS.GENERATE_IMAGE: {
        result = await generateAdImage({
          merchantId,
          prompt: (data.prompt as string) ?? '',
          platform: (data.platform as string) ?? 'instagram_feed',
          postId: data.postId as string | undefined,
          logoOverlay: (data.logoOverlay as boolean) ?? false,
        })
        break
      }

      case JOBS.GENERATE_VIDEO: {
        result = await generateVideoAd({
          merchantId,
          prompt: (data.prompt as string) ?? '',
          platform: (data.platform as string) ?? 'instagram_reel',
          style: data.style as 'product_spotlight' | 'behind_the_scenes' | 'appetizing_food' | 'before_after' | 'testimonial_scene' | 'seasonal_promo' | 'atmosphere' | undefined,
          businessType: data.businessType as string | undefined,
          model: data.model as 'kling-v2' | 'kling-v2-master' | 'minimax-video' | 'ltx-video' | 'wan-v2' | 'hunyuan' | undefined,
          durationSeconds: data.durationSeconds as number | undefined,
          postId: data.postId as string | undefined,
        })
        break
      }

      case JOBS.PUBLISH_POST: {
        const postId = data.postId as string
        if (!supabase) throw new Error('Supabase not initialized')

        const { data: post } = await supabase
          .from('content_posts')
          .select('*')
          .eq('id', postId)
          .single()

        if (!post) throw new Error(`Post ${postId} not found`)

        const platforms = (data.platforms as string[]) ?? [post.platform]
        const mediaUrls: string[] = []
        if (post.image_url) mediaUrls.push(post.image_url as string)

        result = await publishToSocial({
          postId,
          merchantId,
          platforms,
          body: (post.body as string) ?? '',
          mediaUrls: mediaUrls.length > 0 ? mediaUrls : undefined,
          scheduledDate: post.scheduled_at as string | undefined,
        })
        break
      }

      case JOBS.PUBLISH_ARTICLE: {
        const artPostId = data.postId as string
        if (!supabase) throw new Error('Supabase not initialized')

        const { data: artPost } = await supabase
          .from('content_posts')
          .select('*')
          .eq('id', artPostId)
          .single()

        if (!artPost) throw new Error(`Article post ${artPostId} not found`)

        result = await publishToWordPress({
          postId: artPostId,
          merchantId,
          title: (artPost.title as string) ?? '',
          body: (artPost.body as string) ?? '',
          slug: artPost.slug as string | undefined,
          metaDescription: artPost.meta_description as string | undefined,
          featuredImageUrl: artPost.image_url as string | undefined,
        })
        break
      }

      case JOBS.RANK_CHECK: {
        const keywords = (data.keywords as string[]) ?? []
        const targetDomain = (data.targetDomain as string) ?? ''

        if (keywords.length === 0 || !targetDomain) {
          throw new Error('rank_check requires keywords and targetDomain')
        }

        result = await checkRankings({
          merchantId,
          keywords,
          targetDomain,
          locationCode: data.locationCode as number | undefined,
        })
        break
      }

      default:
        throw new Error(`Unknown job type: ${jobName}`)
    }

    await updateJobStatus(merchantId, jobName, job.id ?? '', 'completed', result)

    console.log(`[worker] Completed ${jobName} for merchant ${merchantId}`)
    return result
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err)
    console.error(`[worker] Failed ${jobName} for merchant ${merchantId}:`, errorMsg)

    await updateJobStatus(
      merchantId,
      jobName,
      job.id ?? '',
      'failed',
      undefined,
      errorMsg
    )

    throw err
  }
}

// ── Job Status Tracking ─────────────────────────────────────────────────────

async function updateJobStatus(
  merchantId: string,
  jobType: string,
  bullmqJobId: string,
  status: 'running' | 'completed' | 'failed',
  result?: unknown,
  errorMessage?: string
): Promise<void> {
  if (!supabase) return

  try {
    // Find the matching content_jobs row
    const { data: existingJob } = await supabase
      .from('content_jobs')
      .select('id')
      .eq('merchant_id', merchantId)
      .eq('job_type', mapJobType(jobType))
      .eq('status', status === 'running' ? 'pending' : 'running')
      .order('created_at', { ascending: false })
      .limit(1)
      .single()

    if (existingJob) {
      const update: Record<string, unknown> = {
        status,
        bullmq_job_id: bullmqJobId,
      }

      if (status === 'running') {
        update.started_at = new Date().toISOString()
      }
      if (status === 'completed') {
        update.completed_at = new Date().toISOString()
        update.result = result ?? {}
      }
      if (status === 'failed') {
        update.error_message = errorMessage
      }

      await supabase.from('content_jobs').update(update).eq('id', existingJob.id)
    } else if (status === 'running') {
      // Create a job record if none exists
      await supabase.from('content_jobs').insert({
        merchant_id: merchantId,
        job_type: mapJobType(jobType),
        status: 'running',
        bullmq_job_id: bullmqJobId,
        started_at: new Date().toISOString(),
      })
    }
  } catch (err) {
    console.error('[worker] Failed to update job status:', err)
  }
}

/**
 * Map BullMQ job names to content_jobs.job_type enum values.
 */
function mapJobType(jobName: string): string {
  const mapping: Record<string, string> = {
    brand_extraction: 'brand_extraction',
    calendar_generation: 'calendar_generation',
    generate_social_post: 'content_generation',
    generate_article: 'content_generation',
    generate_image: 'image_generation',
    generate_video: 'video_generation',
    publish_post: 'publish_post',
    publish_article: 'publish_post',
    rank_check: 'rank_check',
  }
  return mapping[jobName] ?? jobName
}

// ── Worker Instance ─────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const connection = redisConnection as any

export const contentWorker = new Worker('meridian-content', processJob, {
  connection,
  concurrency: 5,
  removeOnComplete: { count: 1000 },
  removeOnFail: { count: 5000 },
})

contentWorker.on('failed', (job, err) => {
  console.error(
    `[worker] Job ${job?.name}:${job?.id} failed:`,
    err.message
  )
})

contentWorker.on('completed', (job) => {
  console.log(`[worker] Job ${job.name}:${job.id} completed`)
})

contentWorker.on('error', (err) => {
  console.error('[worker] Worker error:', err)
})

console.log('[worker] Content worker started (concurrency: 5)')
