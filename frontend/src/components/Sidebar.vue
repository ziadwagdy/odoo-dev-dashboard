<template>
  <aside class="w-56 h-full shrink-0 flex flex-col border-r border-border bg-surface/80 backdrop-blur-sm">
    <!-- Logo / brand -->
    <div class="px-4 py-4 border-b border-border">
      <RouterLink to="/" class="flex items-center gap-2.5 group">
        <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center shrink-0">
          <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M8 9l-4 3 4 3M16 9l4 3-4 3M12 6l-2 12"/>
          </svg>
        </div>
        <span class="text-sm font-bold text-slate-100 group-hover:text-accent transition-colors truncate">
          {{ config.dashboardTitle || 'Dev Dashboard' }}
        </span>
      </RouterLink>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
      <!-- Core links -->
      <RouterLink to="/" exact-active-class="nav-active" class="nav-item">
        <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
        Dashboard
      </RouterLink>
      <RouterLink to="/health" active-class="nav-active" class="nav-item">
        <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
        Health
      </RouterLink>

      <!-- Projects by version -->
      <div v-if="store.projects.length" class="pt-3">
        <p class="px-2 text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Projects</p>
        <template v-for="(vProjects, version) in store.ungroupedByVersion" :key="version">
          <button
            class="w-full flex items-center gap-1.5 px-2 py-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
            @click="toggle(String(version))"
          >
            <svg class="w-3 h-3 transition-transform shrink-0" :class="{ 'rotate-90': open[String(version)] }"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
            <span>v{{ version }}</span>
            <span class="ml-auto text-[10px] text-slate-600">{{ vProjects.length }}</span>
          </button>
          <div v-if="open[String(version)]" class="ml-3 space-y-0.5 mb-1">
            <RouterLink
              v-for="p in vProjects"
              :key="p.name"
              :to="`/project/${p.name}`"
              class="flex items-center gap-2 px-2 py-1 rounded text-xs text-slate-400 hover:text-slate-100 hover:bg-surface-hover transition-colors"
              active-class="!text-slate-100 bg-surface-hover"
            >
              <span class="w-1.5 h-1.5 rounded-full shrink-0"
                :class="p.running ? 'bg-emerald-400' : 'bg-slate-600'"></span>
              <span class="truncate">{{ p.name }}</span>
            </RouterLink>
          </div>
        </template>
      </div>

      <!-- Manager/Admin section -->
      <template v-if="auth.canOnboard">
        <div class="pt-3">
          <p class="px-2 text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Admin</p>
          <RouterLink to="/onboard" active-class="nav-active" class="nav-item">
            <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            New Project
          </RouterLink>
          <RouterLink v-if="auth.canManageUsers" to="/users" active-class="nav-active" class="nav-item">
            <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/>
            </svg>
            Users & Roles
          </RouterLink>
        </div>
      </template>

      <!-- External tools -->
      <div class="pt-3">
        <p class="px-2 text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Tools</p>
        <RouterLink to="/help" active-class="nav-active" class="nav-item">
          <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          Help
        </RouterLink>
        <a v-if="config.logsUrl" :href="config.logsUrl" target="_blank" rel="noopener" class="nav-item">
          <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <span>Logs</span>
          <svg class="w-3 h-3 ml-auto text-slate-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
          </svg>
        </a>
      </div>
    </nav>

    <!-- Version footer -->
    <div class="px-4 py-2.5 border-t border-border shrink-0">
      <span class="text-[10px] text-slate-600 font-mono">v{{ APP_VERSION }}</span>
    </div>

  </aside>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import { APP_VERSION } from '@/version'
const store = useProjectsStore()
const config = useConfigStore()
const auth = useAuthStore()
const route = useRoute()

const open = reactive<Record<string, boolean>>({})
function toggle(version: string) {
  open[version] = !open[version]
}

// Auto-open the accordion containing the currently active project.
// Runs on mount and whenever the route or the project list changes.
function openCurrentVersion() {
  const name = route.params.name as string | undefined
  if (!name) return
  const proj = store.projects.find(p => p.name === name)
  if (proj) open[proj.version] = true
}
watch(() => route.params.name, openCurrentVersion, { immediate: true })
watch(() => store.projects, openCurrentVersion)
</script>

<style scoped>
.nav-item {
  @apply flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-sm hover:bg-white/5 transition-colors w-full relative;
  color: rgb(var(--t-sec));
}
.nav-item:hover { color: rgb(var(--t-base)); }
.nav-active {
  @apply !text-accent bg-accent/10 font-medium;
}
.nav-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 3px;
  bottom: 3px;
  width: 2px;
  background: linear-gradient(to bottom, #714b67, #a24689);
  border-radius: 0 2px 2px 0;
}
.nav-icon {
  @apply w-4 h-4 shrink-0;
}

</style>
