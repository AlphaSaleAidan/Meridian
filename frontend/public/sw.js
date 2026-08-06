// Bump on every deploy — activate purges caches with any other name, so a stale
// name leaves old shells stranded in browsers (root cause of "portal reverted"
// reports surviving server-side fixes).
const CACHE_NAME = 'meridian-v40-20260806'
const SHELL_URLS = ['/', '/index.html']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(SHELL_URLS))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

function isStaticAsset(pathname) {
  return /\.(js|css|png|jpg|jpeg|svg|gif|webp|woff2|ttf|ico)$/.test(pathname)
}

async function networkFirst(request) {
  try {
    const res = await fetch(request)
    if (res.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, res.clone())
    }
    return res
  } catch {
    const cached = await caches.match(request)
    return cached || new Response(JSON.stringify({ error: 'offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request)
  if (cached) return cached
  try {
    const res = await fetch(request)
    if (res.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, res.clone())
    }
    return res
  } catch {
    return new Response('', { status: 503 })
  }
}

async function navigationFallback(request) {
  try {
    return await fetch(request)
  } catch {
    const cached = await caches.match('/index.html')
    return cached || new Response('Offline', { status: 503 })
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)
  if (request.method !== 'GET' || !url.protocol.startsWith('http')) return
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request))
    return
  }
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request))
    return
  }
  if (request.mode === 'navigate') {
    event.respondWith(navigationFallback(request))
    return
  }
})

self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {}
  const title = data.title || 'Meridian'
  const options = {
    body: data.body || 'You have a new update',
    icon: '/meridian-icon.svg',
    badge: '/meridian-icon.svg',
    tag: data.tag || 'meridian-notification',
    data: { url: data.url || '/canada/portal/leads' },
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes(url) && 'focus' in client) return client.focus()
      }
      return self.clients.openWindow(url)
    })
  )
})
