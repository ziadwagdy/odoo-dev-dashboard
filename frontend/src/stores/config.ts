import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConfigStore = defineStore('config', () => {
  const logsUrl = ref('')
  const filesUrl = ref('')
  const terminalUrl = ref('')
  const dashboardTitle = ref('Odoo Dev Dashboard')

  // The title is public. Links to the internal tools are only sent to admins, so the request
  // carries the session token when there is one. A stale token must not break the login page:
  // on any error fall back to the anonymous request.
  async function init() {
    const token = localStorage.getItem('auth_token')
    try {
      let res = await fetch('/api/config', token ? { headers: { Authorization: `Token ${token}` } } : undefined)
      if (res.status === 401) res = await fetch('/api/config')
      const d = await res.json()
      logsUrl.value = d.logs_url || ''
      filesUrl.value = d.files_url || ''
      terminalUrl.value = d.terminal_url || ''
      dashboardTitle.value = d.dashboard_title || 'Odoo Dev Dashboard'
    } catch {
      // silently ignore — defaults remain
    }
  }

  return { logsUrl, filesUrl, terminalUrl, dashboardTitle, init }
})
