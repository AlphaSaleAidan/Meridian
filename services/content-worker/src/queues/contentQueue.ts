/**
 * BullMQ queue for content generation jobs.
 * Connects to Upstash Redis with TLS.
 */

import { Queue } from 'bullmq'
import IORedis from 'ioredis'

const redisUrl = process.env.UPSTASH_REDIS_URL ?? ''
const redisToken = process.env.UPSTASH_REDIS_TOKEN ?? ''

/**
 * Shared Redis connection for BullMQ.
 * Upstash requires TLS and token-based auth.
 * Cast to `any` to bridge ioredis version mismatch with BullMQ's bundled copy.
 */
export const redisConnection = new IORedis(redisUrl, {
  password: redisToken,
  tls: redisUrl.startsWith('rediss://') ? {} : undefined,
  maxRetriesPerRequest: null,
  enableReadyCheck: false,
  lazyConnect: true,
})

export const JOBS = {
  BRAND_EXTRACTION: 'brand_extraction',
  CALENDAR_GENERATION: 'calendar_generation',
  GENERATE_SOCIAL_POST: 'generate_social_post',
  GENERATE_ARTICLE: 'generate_article',
  GENERATE_IMAGE: 'generate_image',
  GENERATE_VIDEO: 'generate_video',
  PUBLISH_POST: 'publish_post',
  PUBLISH_ARTICLE: 'publish_article',
  RANK_CHECK: 'rank_check',
} as const

export type JobName = (typeof JOBS)[keyof typeof JOBS]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const connection = redisConnection as any

export const contentQueue = new Queue('meridian-content', {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 5000,
    },
    removeOnComplete: { age: 7 * 24 * 3600 },
    removeOnFail: { age: 30 * 24 * 3600 },
  },
})
