/**
 * Meridian Content Worker — Express server entry point.
 *
 * Mounts content router at /api/content.
 * Starts BullMQ worker and cron schedules.
 * Graceful shutdown on SIGINT/SIGTERM.
 */

import express from 'express'
import cors from 'cors'
import { contentRouter } from './api/routes/content.js'
import { contentWorker } from './queues/workers/contentWorker.js'
import { startCronSchedules, stopCronSchedules } from './queues/contentCron.js'
import { redisConnection } from './queues/contentQueue.js'

const app = express()
const PORT = parseInt(process.env.PORT ?? '3001', 10)

// Middleware
app.use(cors())
app.use(express.json({ limit: '10mb' }))

// Health check
app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    service: 'meridian-content-worker',
    timestamp: new Date().toISOString(),
  })
})

// Mount routes
app.use('/api/content', contentRouter)

// Start server
const server = app.listen(PORT, () => {
  console.log(`[server] Meridian Content Worker listening on :${PORT}`)
  console.log(`[server] API routes mounted at /api/content`)
})

// Start cron schedules
startCronSchedules()

// Graceful shutdown
async function shutdown(signal: string): Promise<void> {
  console.log(`[server] ${signal} received, shutting down gracefully...`)

  // Stop accepting new connections
  server.close()

  // Stop cron schedules
  stopCronSchedules()

  // Close the BullMQ worker (waits for active jobs to finish)
  try {
    await contentWorker.close()
    console.log('[server] Worker closed')
  } catch (err) {
    console.error('[server] Error closing worker:', err)
  }

  // Disconnect Redis
  try {
    await redisConnection.quit()
    console.log('[server] Redis disconnected')
  } catch (err) {
    console.error('[server] Error disconnecting Redis:', err)
  }

  process.exit(0)
}

process.on('SIGINT', () => shutdown('SIGINT'))
process.on('SIGTERM', () => shutdown('SIGTERM'))
