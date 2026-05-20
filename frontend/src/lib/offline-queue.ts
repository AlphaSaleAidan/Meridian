import { canadaLeadsService, LeadsServiceError } from './canada-leads-service'
import type { Deal, DealStage } from './canada-sales-demo-data'

const QUEUE_KEY = 'meridian_offline_queue'

interface QueuedMutation {
  id: string
  type: 'create' | 'update' | 'updateStage' | 'delete'
  payload: Record<string, unknown>
  timestamp: number
  retries: number
}

function loadQueue(): QueuedMutation[] {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]')
  } catch {
    return []
  }
}

function saveQueue(queue: QueuedMutation[]): void {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
}

function enqueue(mutation: Omit<QueuedMutation, 'id' | 'timestamp' | 'retries'>): void {
  const queue = loadQueue()
  queue.push({
    ...mutation,
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
    timestamp: Date.now(),
    retries: 0,
  })
  saveQueue(queue)
}

async function processMutation(m: QueuedMutation): Promise<void> {
  switch (m.type) {
    case 'create':
      await canadaLeadsService.create(m.payload.deal as Deal, m.payload.repId as string | undefined)
      break
    case 'update':
      await canadaLeadsService.update(m.payload.id as string, m.payload.updates as Partial<Deal>)
      break
    case 'updateStage':
      await canadaLeadsService.updateStage(m.payload.id as string, m.payload.stage as DealStage)
      break
    case 'delete':
      await canadaLeadsService.delete(m.payload.id as string)
      break
  }
}

export async function flushQueue(onFlushed?: (count: number) => void): Promise<void> {
  const queue = loadQueue()
  if (queue.length === 0) return

  const failed: QueuedMutation[] = []
  let flushed = 0

  for (const m of queue) {
    try {
      await processMutation(m)
      flushed++
    } catch {
      if (m.retries < 3) {
        failed.push({ ...m, retries: m.retries + 1 })
      }
    }
  }

  saveQueue(failed)
  if (flushed > 0 && onFlushed) onFlushed(flushed)
}

export function queueIfOffline(
  type: QueuedMutation['type'],
  payload: Record<string, unknown>,
): boolean {
  if (navigator.onLine) return false
  enqueue({ type, payload })
  return true
}

export function getPendingCount(): number {
  return loadQueue().length
}

export function setupOfflineSync(onFlushed?: (count: number) => void): () => void {
  const handler = () => {
    if (navigator.onLine) flushQueue(onFlushed)
  }
  window.addEventListener('online', handler)
  handler()
  return () => window.removeEventListener('online', handler)
}
