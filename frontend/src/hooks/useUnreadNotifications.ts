import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import { api } from '@/lib/api'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'

interface UseUnreadNotifications {
  unreadCount: number
  markAllRead: () => void
}

export function useUnreadNotifications(): UseUnreadNotifications {
  const [unreadCount, setUnreadCount] = useState(0)
  const orgId = useOrgId()
  const isDemo = useIsDemo()

  // Fetch initial unread count from the notifications API
  useEffect(() => {
    if (!orgId) return

    let cancelled = false

    api.notifications(orgId, 50)
      .then((data) => {
        if (cancelled) return
        const unread = data.notifications.filter(
          (n) => !n.acknowledged_at,
        ).length
        setUnreadCount(unread)
      })
      .catch(() => {
        // Silently ignore — badge just stays at 0
      })

    return () => {
      cancelled = true
    }
  }, [orgId])

  // Subscribe to Supabase Realtime for new notification inserts
  useEffect(() => {
    if (!supabase || isDemo || !orgId) return

    const client = supabase

    const channel = client
      .channel(`notifications-badge-${orgId}`)
      .on(
        'postgres_changes' as any,
        {
          event: 'INSERT',
          schema: 'public',
          table: 'notifications',
          filter: `org_id=eq.${orgId}`,
        },
        (_payload: any) => {
          setUnreadCount((c) => c + 1)
        },
      )
      .subscribe()

    return () => {
      client.removeChannel(channel)
    }
  }, [orgId, isDemo])

  const markAllRead = useCallback(() => {
    setUnreadCount(0)
  }, [])

  return { unreadCount, markAllRead }
}
