import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import { useNotificationsStore } from '@/stores/notifications'

export interface Alert {
  id: number; rule: string; severity: 'info' | 'warning' | 'high' | 'critical'; source: string
  summary: string; sample: string; count: number; first_seen: string; last_seen: string
  status: 'open' | 'acknowledged'; acknowledged_by: string; note: string
}

function urlBase64ToUint8Array(b64: string) {
  const padding = '='.repeat((4 - (b64.length % 4)) % 4)
  const raw = atob((b64 + padding).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)))
}

export const useSecurityStore = defineStore('security', () => {
  const summary = ref({ open: 0, critical: 0, high: 0, worst: null as string | null })
  const alerts = ref<Alert[]>([])
  const pushState = ref<'unsupported' | 'blocked' | 'off' | 'on'>('off')
  let timer: number | undefined
  let lastWorstRank = 0
  const rank: Record<string, number> = { info: 1, warning: 2, high: 3, critical: 4 }

  const badgeClass = computed(() => ({
    critical: 'bg-red-600', high: 'bg-orange-500', warning: 'bg-amber-500', info: 'bg-slate-500',
  } as Record<string, string>)[summary.value.worst || 'info'])

  async function fetchSummary(announce = true) {
    try {
      const res = await api('/api/security/summary')
      if (!res.ok) return
      const s = await res.json()
      const r = rank[s.worst || ''] || 0
      if (announce && r >= 3 && (r > lastWorstRank || s.open > summary.value.open)) {
        useNotificationsStore().add('error', `Security: ${s.critical} critical, ${s.high} high alert(s) open`)
      }
      lastWorstRank = r
      summary.value = s
    } catch { /* ignore a failed poll */ }
  }

  async function fetchAlerts() {
    const res = await api('/api/security/alerts')
    if (res.ok) alerts.value = (await res.json()).alerts
  }

  async function acknowledge(id: number, note = '') {
    await api(`/api/security/alerts/${id}/ack`, { method: 'POST', body: JSON.stringify({ note }) })
    await Promise.all([fetchAlerts(), fetchSummary(false)])
  }

  function startPolling() {
    if (timer) return
    fetchSummary(false)
    timer = window.setInterval(() => fetchSummary(true), 20000)
  }
  function stopPolling() { if (timer) { clearInterval(timer); timer = undefined } }

  // ── Web Push ──────────────────────────────────────────────────────────────
  async function refreshPushState() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
      pushState.value = 'unsupported'; return
    }
    if (Notification.permission === 'denied') { pushState.value = 'blocked'; return }
    const reg = await navigator.serviceWorker.getRegistration('/sw.js')
    const sub = reg ? await reg.pushManager.getSubscription() : null
    pushState.value = sub && Notification.permission === 'granted' ? 'on' : 'off'
  }

  async function enablePush() {
    const notify = useNotificationsStore()
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) { pushState.value = 'unsupported'; return }
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') { pushState.value = permission === 'denied' ? 'blocked' : 'off'; return }
    const reg = await navigator.serviceWorker.register('/sw.js')
    await navigator.serviceWorker.ready
    const keyRes = await api('/api/push/public-key')
    const { key } = await keyRes.json()
    const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(key) })
    const res = await api('/api/push/subscribe', { method: 'POST', body: JSON.stringify(sub.toJSON()) })
    if (res.ok) { pushState.value = 'on'; notify.add('success', 'Push notifications enabled on this device') }
    else notify.add('error', 'Could not register this device for push notifications')
  }

  async function disablePush() {
    const reg = await navigator.serviceWorker.getRegistration('/sw.js')
    const sub = reg ? await reg.pushManager.getSubscription() : null
    if (sub) {
      await api('/api/push/unsubscribe', { method: 'POST', body: JSON.stringify({ endpoint: sub.endpoint }) })
      await sub.unsubscribe()
    }
    pushState.value = 'off'
  }

  async function testPush() {
    const res = await api('/api/push/test', { method: 'POST', body: '{}' })
    const d = await res.json()
    useNotificationsStore().add(d.delivered ? 'success' : 'error',
      d.delivered ? 'Test notification sent' : 'No device received it. Enable notifications first.')
  }

  return { summary, alerts, pushState, badgeClass, fetchSummary, fetchAlerts, acknowledge, startPolling, stopPolling,
           refreshPushState, enablePush, disablePush, testPush }
})
