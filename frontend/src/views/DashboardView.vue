<template>
  <div class="max-w-7xl mx-auto px-4 md:px-6 py-6 md:py-10">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 md:gap-0 mb-6 md:mb-10">
      <div class="flex items-center gap-3 md:gap-6">
        <Logo />
        <div class="hidden md:block h-12 w-px bg-border"></div>
        <div class="hidden md:block">
          <p class="text-sm text-slate-400 flex items-center gap-2">
            <span v-if="store.lastUpdated" class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span class="font-medium text-emerald-400">Live</span>
              <span class="text-slate-500">·</span>
              <span>{{ store.lastUpdated.toLocaleTimeString() }}</span>
            </span>
            <span v-else class="text-slate-500">Connecting…</span>
          </p>
        </div>
      </div>
      <!-- Infra shortcuts -->
      <div class="flex gap-2 md:gap-3 overflow-x-auto">
        <RouterLink to="/health" class="btn btn-ghost text-xs md:text-sm whitespace-nowrap">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
          </svg>
          <span class="hidden sm:inline">Health</span>
        </RouterLink>
        <a v-if="config.logsUrl" :href="config.logsUrl" target="_blank" rel="noopener" class="btn btn-ghost text-xs md:text-sm whitespace-nowrap">
          📋 <span class="hidden sm:inline">Logs</span>
        </a>
        <a v-if="config.filesUrl" :href="config.filesUrl" target="_blank" rel="noopener" class="btn btn-ghost text-xs md:text-sm whitespace-nowrap">
          📁 <span class="hidden sm:inline">Files</span>
        </a>
        <a v-if="config.terminalUrl" :href="config.terminalUrl" target="_blank" rel="noopener" class="btn btn-ghost text-xs md:text-sm whitespace-nowrap">
          ⌨ <span class="hidden sm:inline">Terminal</span>
        </a>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading && !store.projects.length" class="text-center py-20 md:py-32 text-slate-400">
      <div class="inline-block w-10 h-10 md:w-12 md:h-12 border-4 border-accent/30 border-t-accent rounded-full animate-spin mb-4"></div>
      <p class="text-base md:text-lg font-medium">Loading projects…</p>
    </div>

    <!-- Project groups -->
    <div v-for="(projects, version) in store.grouped" :key="version" class="mb-8 md:mb-10">
      <div class="flex items-center gap-2 md:gap-3 mb-4 md:mb-5">
        <h2 class="text-xs font-bold uppercase tracking-widest text-slate-400">
          Odoo {{ version }}
        </h2>
        <div class="h-px flex-1 bg-gradient-to-r from-border to-transparent"></div>
        <span class="text-xs text-slate-500 font-medium whitespace-nowrap">{{ projects.length }} {{ projects.length === 1 ? 'project' : 'projects' }}</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
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
import Logo from '@/components/Logo.vue'

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
