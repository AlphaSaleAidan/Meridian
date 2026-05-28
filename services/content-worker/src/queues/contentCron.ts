/**
 * Cron schedules for automated content operations.
 *
 * - Monday 6AM UTC: weekly calendar generation for all active merchants
 * - Sunday 2AM UTC: rank checks for all merchants with tracked keywords
 */

import cron from 'node-cron'
import { supabase } from '../lib/supabase.js'
import { contentQueue, JOBS } from './contentQueue.js'

// ── Monday 6AM UTC: Weekly Calendar Generation ──────────────────────────────

const calendarCron = cron.schedule(
  '0 6 * * 1',
  async () => {
    console.log('[cron] Starting weekly calendar generation for all active merchants')

    if (!supabase) {
      console.error('[cron] Supabase not initialized, skipping calendar cron')
      return
    }

    try {
      // Get all active content_brands (merchants with a content tier)
      const { data: brands, error } = await supabase
        .from('content_brands')
        .select('merchant_id, content_tier')
        .not('content_tier', 'is', null)

      if (error) {
        console.error('[cron] Failed to fetch brands:', error)
        return
      }

      if (!brands || brands.length === 0) {
        console.log('[cron] No active content merchants found')
        return
      }

      console.log(`[cron] Queuing calendar generation for ${brands.length} merchants`)

      for (const brand of brands) {
        const merchantId = brand.merchant_id as string
        const contentTier = (brand.content_tier as string) ?? 'starter'

        await contentQueue.add(
          JOBS.CALENDAR_GENERATION,
          {
            merchantId,
            contentTier,
          },
          {
            jobId: `cron-cal-${merchantId}-${Date.now()}`,
          }
        )

        // Log the job
        await supabase.from('content_jobs').insert({
          merchant_id: merchantId,
          job_type: 'calendar_generation',
          status: 'pending',
          payload: { source: 'cron', contentTier },
        })
      }

      console.log(`[cron] Calendar generation queued for ${brands.length} merchants`)
    } catch (err) {
      console.error('[cron] Calendar cron error:', err)
    }
  },
  {
    timezone: 'UTC',
  }
)

// ── Sunday 2AM UTC: Rank Checks ─────────────────────────────────────────────

const rankCheckCron = cron.schedule(
  '0 2 * * 0',
  async () => {
    console.log('[cron] Starting weekly rank checks for all merchants')

    if (!supabase) {
      console.error('[cron] Supabase not initialized, skipping rank check cron')
      return
    }

    try {
      // Get merchants with tracked keywords (those who have existing rankings)
      const { data: merchants, error } = await supabase
        .from('content_brands')
        .select('merchant_id, website_url, gsc_site_url')
        .not('content_tier', 'is', null)

      if (error) {
        console.error('[cron] Failed to fetch merchants for rank check:', error)
        return
      }

      if (!merchants || merchants.length === 0) {
        console.log('[cron] No merchants to check rankings for')
        return
      }

      for (const merchant of merchants) {
        const merchantId = merchant.merchant_id as string
        const targetDomain =
          (merchant.gsc_site_url as string) ??
          (merchant.website_url as string) ??
          null

        if (!targetDomain) continue

        // Get tracked keywords for this merchant (from previous rank checks)
        const { data: prevRankings } = await supabase
          .from('content_rankings')
          .select('keyword')
          .eq('merchant_id', merchantId)
          .order('checked_at', { ascending: false })
          .limit(50)

        const uniqueKeywords = [
          ...new Set(
            (prevRankings ?? []).map(
              (r: { keyword: string }) => r.keyword
            )
          ),
        ]

        if (uniqueKeywords.length === 0) continue

        await contentQueue.add(
          JOBS.RANK_CHECK,
          {
            merchantId,
            keywords: uniqueKeywords,
            targetDomain,
          },
          {
            jobId: `cron-rank-${merchantId}-${Date.now()}`,
          }
        )

        // Log the job
        await supabase.from('content_jobs').insert({
          merchant_id: merchantId,
          job_type: 'rank_check',
          status: 'pending',
          payload: {
            source: 'cron',
            keywordCount: uniqueKeywords.length,
            targetDomain,
          },
        })
      }

      console.log(`[cron] Rank checks queued for merchants`)
    } catch (err) {
      console.error('[cron] Rank check cron error:', err)
    }
  },
  {
    timezone: 'UTC',
  }
)

export function startCronSchedules(): void {
  calendarCron.start()
  rankCheckCron.start()
  console.log('[cron] Content cron schedules registered')
  console.log('[cron]   - Calendar generation: Monday 6AM UTC')
  console.log('[cron]   - Rank checks: Sunday 2AM UTC')
}

export function stopCronSchedules(): void {
  calendarCron.stop()
  rankCheckCron.stop()
  console.log('[cron] Content cron schedules stopped')
}
