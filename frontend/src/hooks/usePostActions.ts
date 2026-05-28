import { useState, useCallback } from 'react'
import { contentApi } from '@/lib/content-api'
import { useAuth } from '@/lib/auth'

export function usePostActions(onSuccess?: () => void) {
  const { org } = useAuth()
  const merchantId = org?.org_id || 'demo'
  const [isPending, setIsPending] = useState(false)

  const approvePost = useCallback(
    async (postId: string, scheduledAt?: string) => {
      if (merchantId === 'demo') {
        onSuccess?.()
        return
      }
      setIsPending(true)
      try {
        await contentApi.approvePost(postId, merchantId, scheduledAt)
        onSuccess?.()
      } finally {
        setIsPending(false)
      }
    },
    [merchantId, onSuccess],
  )

  const rejectPost = useCallback(
    async (postId: string) => {
      if (merchantId === 'demo') {
        onSuccess?.()
        return
      }
      setIsPending(true)
      try {
        await contentApi.rejectPost(postId)
        onSuccess?.()
      } finally {
        setIsPending(false)
      }
    },
    [merchantId, onSuccess],
  )

  const regeneratePost = useCallback(
    async (postId: string, field: string) => {
      if (merchantId === 'demo') {
        onSuccess?.()
        return
      }
      setIsPending(true)
      try {
        await contentApi.regeneratePost(postId, field, merchantId)
        onSuccess?.()
      } finally {
        setIsPending(false)
      }
    },
    [merchantId, onSuccess],
  )

  return { approvePost, rejectPost, regeneratePost, isPending }
}
