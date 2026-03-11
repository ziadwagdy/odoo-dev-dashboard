import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConfigStore = defineStore('config', () => {
  const logsUrl = ref('')
  const filesUrl = ref('')
  const terminalUrl = ref('')
  const dashboardTitle = ref('Odoo Dev Dashboard')

  async function init() {
    try {
      const res = await fetch('/api/config')
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
