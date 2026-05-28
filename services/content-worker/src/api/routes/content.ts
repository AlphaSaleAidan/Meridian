/**
 * Express routes for content system API.
 *
 * POST /webhooks/content-purchase   — Webhook from billing (validates WEBHOOK_SECRET)
 * GET  /dashboard/:merchantId       — Dashboard data (brand, posts, rankings, jobs)
 * POST /calendar/generate/:merchantId — Trigger calendar generation
 * PATCH /posts/:postId/approve      — Approve a post and queue publish
 * PATCH /posts/:postId/reject       — Reject a post
 * POST /posts/:postId/regenerate    — Regenerate a post
 */

import { Router, type Request, type Response } from 'express'
import { z } from 'zod'
import { supabase } from '../../lib/supabase.js'
import { contentQueue, JOBS } from '../../queues/contentQueue.js'
import { onboardMerchant } from '../../agents/content/ContentOrchestrator.js'

export const contentRouter = Router()

// ── Webhook: Content Purchase ───────────────────────────────────────────────

const webhookSchema = z.object({
  merchantId: z.string().uuid(),
  businessName: z.string(),
  businessType: z.string(),
  contentTier: z.enum(['starter', 'growth', 'command']),
  websiteUrl: z.string().url().optional(),
  approvalEmail: z.string().email().optional(),
  autoPublish: z.boolean().optional(),
})

contentRouter.post(
  '/webhooks/content-purchase',
  async (req: Request, res: Response): Promise<void> => {
    // Validate webhook secret
    const secret = req.headers['x-webhook-secret'] as string | undefined
    if (!secret || secret !== process.env.WEBHOOK_SECRET) {
      res.status(401).json({ error: 'Invalid webhook secret' })
      return
    }

    const parsed = webhookSchema.safeParse(req.body)
    if (!parsed.success) {
      res.status(400).json({ error: 'Invalid payload', details: parsed.error.issues })
      return
    }

    try {
      const result = await onboardMerchant({
        merchantId: parsed.data.merchantId,
        businessName: parsed.data.businessName,
        businessType: parsed.data.businessType,
        contentTier: parsed.data.contentTier,
        websiteUrl: parsed.data.websiteUrl,
        approvalEmail: parsed.data.approvalEmail,
        autoPublish: parsed.data.autoPublish,
      })

      res.status(200).json({
        success: true,
        brandId: result.brandId,
        ayrshareProfileKey: result.ayrshareProfileKey,
      })
    } catch (err) {
      console.error('[api] Webhook content-purchase error:', err)
      res.status(500).json({
        error: 'Onboarding failed',
        message: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }
)

// ── Dashboard ───────────────────────────────────────────────────────────────

contentRouter.get(
  '/dashboard/:merchantId',
  async (req: Request, res: Response): Promise<void> => {
    const { merchantId } = req.params

    if (!supabase) {
      res.status(503).json({ error: 'Database not available' })
      return
    }

    try {
      // Run all queries in parallel
      const [brandResult, postsResult, rankingsResult, jobsResult] =
        await Promise.all([
          supabase
            .from('content_brands')
            .select('*')
            .eq('merchant_id', merchantId)
            .single(),
          supabase
            .from('content_posts')
            .select('*')
            .eq('merchant_id', merchantId)
            .order('scheduled_at', { ascending: false })
            .limit(50),
          supabase
            .from('content_rankings')
            .select('*')
            .eq('merchant_id', merchantId)
            .order('checked_at', { ascending: false })
            .limit(30),
          supabase
            .from('content_jobs')
            .select('*')
            .eq('merchant_id', merchantId)
            .order('created_at', { ascending: false })
            .limit(20),
        ])

      res.json({
        brand: brandResult.data,
        posts: postsResult.data ?? [],
        rankings: rankingsResult.data ?? [],
        jobs: jobsResult.data ?? [],
      })
    } catch (err) {
      console.error('[api] Dashboard error:', err)
      res.status(500).json({
        error: 'Dashboard fetch failed',
        message: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }
)

// ── Calendar Generation ─────────────────────────────────────────────────────

const calendarGenerateSchema = z.object({
  contentTier: z.enum(['starter', 'growth', 'command']).optional(),
  weekStart: z.string().optional(),
})

contentRouter.post(
  '/calendar/generate/:merchantId',
  async (req: Request, res: Response): Promise<void> => {
    const { merchantId } = req.params
    const parsed = calendarGenerateSchema.safeParse(req.body)

    if (!parsed.success) {
      res.status(400).json({ error: 'Invalid payload', details: parsed.error.issues })
      return
    }

    try {
      // Get content tier from brand if not provided
      let contentTier = parsed.data.contentTier

      if (!contentTier && supabase) {
        const { data: brand } = await supabase
          .from('content_brands')
          .select('content_tier')
          .eq('merchant_id', merchantId)
          .single()

        contentTier = (brand?.content_tier as 'starter' | 'growth' | 'command') ?? 'starter'
      }

      await contentQueue.add(
        JOBS.CALENDAR_GENERATION,
        {
          merchantId,
          contentTier: contentTier ?? 'starter',
          weekStart: parsed.data.weekStart,
        },
        { jobId: `api-cal-${merchantId}-${Date.now()}` }
      )

      res.json({ success: true, message: 'Calendar generation queued' })
    } catch (err) {
      console.error('[api] Calendar generation error:', err)
      res.status(500).json({
        error: 'Calendar generation failed',
        message: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }
)

// ── Approve Post ────────────────────────────────────────────────────────────

contentRouter.patch(
  '/posts/:postId/approve',
  async (req: Request, res: Response): Promise<void> => {
    const { postId } = req.params

    if (!supabase) {
      res.status(503).json({ error: 'Database not available' })
      return
    }

    try {
      // Get the post
      const { data: post, error: postErr } = await supabase
        .from('content_posts')
        .select('id, merchant_id, post_type, platform, status')
        .eq('id', postId)
        .single()

      if (postErr || !post) {
        res.status(404).json({ error: 'Post not found' })
        return
      }

      if (post.status !== 'needs_review' && post.status !== 'draft') {
        res.status(400).json({
          error: `Cannot approve post in '${post.status}' status`,
        })
        return
      }

      // Update to approved
      await supabase
        .from('content_posts')
        .update({ status: 'approved', updated_at: new Date().toISOString() })
        .eq('id', postId)

      // Queue publish job
      const jobType =
        post.post_type === 'article' ? JOBS.PUBLISH_ARTICLE : JOBS.PUBLISH_POST

      await contentQueue.add(
        jobType,
        {
          postId,
          merchantId: post.merchant_id,
          platforms: [post.platform],
        },
        { jobId: `pub-${postId}-${Date.now()}` }
      )

      res.json({ success: true, message: 'Post approved and publish queued' })
    } catch (err) {
      console.error('[api] Approve error:', err)
      res.status(500).json({
        error: 'Approval failed',
        message: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }
)

// ── Reject Post ─────────────────────────────────────────────────────────────

contentRouter.patch(
  '/posts/:postId/reject',
  async (req: Request, res: Response): Promise<void> => {
    const { postId } = req.params

    if (!supabase) {
      res.status(503).json({ error: 'Database not available' })
      return
    }

    try {
      const { error } = await supabase
        .from('content_posts')
        .update({
          status: 'rejected',
          updated_at: new Date().toISOString(),
        })
        .eq('id', postId)

      if (error) {
        res.status(500).json({ error: 'Failed to reject post' })
        return
      }

      res.json({ success: true, message: 'Post rejected' })
    } catch (err) {
      console.error('[api] Reject error:', err)
      res.status(500).json({
        error: 'Rejection failed',
        message: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }
)

// ── Regenerate Post ─────────────────────────────────────────────────────────

contentRouter.post(
  '/posts/:postId/regenerate',
  async (req: Request, res: Response): Promise<void> => {
    const { postId } = req.params

    if (!supabase) {
      res.status(503).json({ error: 'Database not available' })
      return
    }

    try {
      // Get the post
      const { data: post, error: postErr } = await supabase
        .from('content_posts')
        .select('*')
        .eq('id', postId)
        .single()

      if (postErr || !post) {
        res.status(404).json({ error: 'Post not found' })
        return
      }

      // Reset status to generating
      await supabase
        .from('content_posts')
        .update({
          status: 'generating',
          updated_at: new Date().toISOString(),
        })
        .eq('id', postId)

      // Queue regeneration based on post type
      const merchantId = post.merchant_id as string

      if (post.post_type === 'article') {
        // Get brand for content tier
        const { data: brand } = await supabase
          .from('content_brands')
          .select('content_tier')
          .eq('merchant_id', merchantId)
          .single()

        await contentQueue.add(JOBS.GENERATE_ARTICLE, {
          postId,
          merchantId,
          title: post.title ?? '',
          targetKeyword: post.target_keyword ?? post.title ?? '',
          wordCount: post.word_count ?? 1200,
          contentTier: brand?.content_tier ?? 'growth',
          posDataReference: post.pos_data_reference,
        })
      } else {
        await contentQueue.add(JOBS.GENERATE_SOCIAL_POST, {
          postId,
          merchantId,
          platform: post.platform ?? 'instagram',
          topic: post.title ?? '',
          posDataReference: post.pos_data_reference,
        })

        // Also regenerate image if there was an image prompt
        if (post.image_prompt) {
          await contentQueue.add(
            JOBS.GENERATE_IMAGE,
            {
              postId,
              merchantId,
              prompt: post.image_prompt,
              platform: post.platform ?? 'instagram_feed',
            },
            { delay: 5_000 }
          )
        }
      }

      res.json({ success: true, message: 'Post regeneration queued' })
    } catch (err) {
      console.error('[api] Regenerate error:', err)
      res.status(500).json({
        error: 'Regeneration failed',
        message: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }
)
