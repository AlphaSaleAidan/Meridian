let swRegistration: ServiceWorkerRegistration | null = null

export async function initServiceWorker(): Promise<void> {
  if (!('serviceWorker' in navigator)) return
  try {
    swRegistration = await navigator.serviceWorker.register('/sw.js')
  } catch {
    // SW registration failed — not critical
  }
}

export async function requestNotificationPermission(): Promise<boolean> {
  if (!('Notification' in window)) return false
  if (Notification.permission === 'granted') return true
  if (Notification.permission === 'denied') return false
  const result = await Notification.requestPermission()
  return result === 'granted'
}

export function showLocalNotification(title: string, body: string, url?: string): void {
  if (Notification.permission !== 'granted') return

  if (swRegistration) {
    swRegistration.showNotification(title, {
      body,
      icon: '/meridian-icon.svg',
      tag: 'meridian-' + Date.now(),
      data: { url: url || '/canada/portal/leads' },
    })
  } else {
    new Notification(title, { body, icon: '/meridian-icon.svg' })
  }
}

export function notifyStageChange(businessName: string, newStage: string): void {
  const stageLabels: Record<string, string> = {
    proposal_shown: 'Proposal Shown',
    customer_checkout: 'Customer Checkout',
    pos_connected: 'POS Connected',
    customer_walkthrough: 'Active Deal',
    closed_lost: 'Closed Lost',
  }
  const label = stageLabels[newStage] || newStage
  showLocalNotification(
    'Deal Updated',
    `${businessName} moved to ${label}`,
    '/canada/portal/leads',
  )
}
