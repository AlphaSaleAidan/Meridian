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
  }, [orgId, isDemo, skipForAdmin])

  const markAllRead = useCallback(() => {
    setUnreadCount(0)
  }, [])

  return { unreadCount, markAllRead }
}
