import { useState, useEffect, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import { api } from '@/lib/api'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'

interface UseUnreadNotifications {
  unreadCount: number
  markAllRead: () => void
}

// Routes that mount the customer Layout but are NOT scoped to a single
// business org — admin dashboards in particular. The notifications poller
// keyed on org_id is meaningless on these surfaces; firing it with the
// admin's own business org_id was producing /api/dashboard/notifications
// 500s on every admin page mount.
function isAdminRoute(pathname: string): boolean {
  return pathname.startsWith('/admin/') || pathname === '/customer/admin'
}

export function useUnreadNotifications(): UseUnreadNotifications {
  const [unreadCount, setUnreadCount] = useState(0)
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const location = useLocation()
  const skipForAdmin = isAdminRoute(location.pathname)

  // Fetch initial unread count from the notifications API
  useEffect(() => {
    if (!orgId || skipForAdmin) return

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
  }, [orgId, skipForAdmin])

  // Subscribe to Supabase Realtime for new notification inserts
  useEffect(() => {
    if (!supabase || isDemo || !orgId || skipForAdmin) return

    const client = supabase
    const topic = `notifications-badge-${orgId}`

    // The Supabase client caches channels by topic on a module-level singleton.
    // A stale channel for this topic (left by a fast remount, StrictMode double-
    // mount, or HMR) is still subscribed, so client.channel(topic) would return
    // it and the chained .on() throws "cannot add callbacks after subscribe()".
    // Remove any existing one first, and never let a realtime hiccup crash the
    // dashboard — the badge degrades to its polled count.
    let channel: ReturnType<typeof client.channel> | null = null
    try {
      client
        .getChannels()
        .filter((ch) => ch.topic === `realtime:${topic}`)
        .forEach((ch) => client.removeChannel(ch))

      channel = client
        .channel(topic)
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
    } catch {
      channel = null
    }

    return () => {
      if (channel) client.removeChannel(channel)
    }
  }, [orgId, isDemo, skipForAdmin])

  const markAllRead = useCallback(() => {
    setUnreadCount(0)
  }, [])

  return { unreadCount, markAllRead }
}
