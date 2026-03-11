import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Project {
  name: string
  version: string
  odoo_port: string
  db_port: string
  url: string
  container: string
  container_id?: string
  folder: string | null
  status: string
  running: boolean
  branch?: string
  pending_count?: number
}

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const loading = ref(false)
  const lastUpdated = ref<Date | null>(null)
  let sseSource: EventSource | null = null

  async function fetchProjects() {
    loading.value = true
    try {
      const res = await fetch('/api/status')
      const data = await res.json()
      projects.value = data.projects || []
    } finally {
      loading.value = false
    }
  }

  function startSSE() {
    if (sseSource) return
    sseSource = new EventSource('/stream/status')
    sseSource.onmessage = (evt) => {
      const updates: Array<{ name: string; status: string; running: boolean }> = JSON.parse(evt.data)
      for (const u of updates) {
        const p = projects.value.find(p => p.name === u.name)
        if (p) {
          p.status = u.status
          p.running = u.running
        }
      }
      lastUpdated.value = new Date()
    }
    sseSource.onerror = () => {
      // auto-reconnects
    }
  }

  function stopSSE() {
    sseSource?.close()
    sseSource = null
  }

  const grouped = computed(() => {
    const g: Record<string, Project[]> = {}
    for (const p of projects.value) {
      ;(g[p.version] ??= []).push(p)
    }
    return Object.fromEntries(Object.entries(g).sort())
  })

  return { projects, loading, lastUpdated, fetchProjects, startSSE, stopSSE, grouped }
})
