<template>
  <div class="max-w-7xl mx-auto px-6 py-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-bold text-white">{{ config.dashboardTitle }}</h1>
        <p class="text-sm text-slate-500 mt-1">
          {{ store.lastUpdated ? 'Live · ' + store.lastUpdated.toLocaleTimeString() : 'Connecting…' }}
        </p>
      </div>
      <!-- Infra shortcuts -->
      <div class="flex gap-2">
        <RouterLink to="/health" class="btn btn-ghost text-xs">Health</RouterLink>
        <a v-if="config.logsUrl" :href="config.logsUrl" target="_blank" rel="noopener" class="btn btn-ghost text-xs">📋 Logs</a>
        <a v-if="config.filesUrl" :href="config.filesUrl" target="_blank" rel="noopener" class="btn btn-ghost text-xs">📁 Files</a>
        <a v-if="config.terminalUrl" :href="config.terminalUrl" target="_blank" rel="noopener" class="btn btn-ghost text-xs">⌨ Terminal</a>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading && !store.projects.length" class="text-center py-20 text-slate-500">
      Loading projects…
    </div>

    <!-- Project groups -->
    <div v-for="(projects, version) in store.grouped" :key="version" class="mb-8">
      <h2 class="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
        Odoo {{ version }}
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <ProjectCard
          v-for="p in projects"
          :key="p.name"
          :project="p"
          @restart="restartProject"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useNotificationsStore } from '@/stores/notifications'
import { useConfigStore } from '@/stores/config'
import ProjectCard from '@/components/ProjectCard.vue'

const store = useProjectsStore()
const notify = useNotificationsStore()
const config = useConfigStore()

onMounted(async () => {
  await store.fetchProjects()
  store.startSSE()
})

onUnmounted(() => {
  store.stopSSE()
})

async function restartProject(containerName: string) {
  try {
    const res = await fetch(`/api/restart/${containerName}`, { method: 'POST' })
    const data = await res.json()
    notify.add(data.ok ? 'success' : 'error', data.ok ? 'Container restarted' : data.error)
  } catch {
    notify.add('error', 'Restart failed')
  }
}
</script>
