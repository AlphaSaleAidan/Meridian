/**
 * Standalone worker entry point.
 *
 * Starts only the BullMQ worker and cron schedules,
 * without the Express HTTP server. Use this when running
 * the worker as a separate process from the API server.
 *
 * Usage: tsx src/worker-entry.ts
 */

import { contentWorker } from './queues/workers/contentWorker.js'
import { startCronSchedules, stopCronSchedules } from './queues/contentCron.js'
import { redisConnection } from './queues/contentQueue.js'

console.log('[worker-entry] Starting content worker (no HTTP server)')

// Start cron schedules
startCronSchedules()

// Graceful shutdown
async function shutdown(signal: string): Promise<void> {
  console.log(`[worker-entry] ${signal} received, shutting down...`)

  stopCronSchedules()

  try {
    await contentWorker.close()
    console.log('[worker-entry] Worker closed')
  } catch (err) {
    console.error('[worker-entry] Error closing worker:', err)
  }

  try {
    await redisConnection.quit()
    console.log('[worker-entry] Redis disconnected')
  } catch (err) {
    console.error('[worker-entry] Error disconnecting Redis:', err)
  }

  process.exit(0)
}

process.on('SIGINT', () => shutdown('SIGINT'))
process.on('SIGTERM', () => shutdown('SIGTERM'))
