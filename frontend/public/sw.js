// Service worker: shows security alerts pushed by the dashboard, opens /security on click.
self.addEventListener('push', (event) => {
  let data = {}
  try { data = event.data ? event.data.json() : {} } catch (e) { data = { title: 'Dashboard alert', body: event.data && event.data.text() } }
  const severity = data.severity || 'info'
  event.waitUntil(self.registration.showNotification(data.title || 'Dashboard alert', {
    body: data.body || '',
    tag: data.tag || 'dashboard-alert',
    renotify: true,
    requireInteraction: severity === 'critical' || severity === 'high',
    icon: '/favicon.svg',
    badge: '/favicon.svg',
    data: { url: data.url || '/security' },
  }))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/security'
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
    for (const c of clients) {
      if ('focus' in c) { c.navigate(url); return c.focus() }
    }
    return self.clients.openWindow(url)
  }))
})
