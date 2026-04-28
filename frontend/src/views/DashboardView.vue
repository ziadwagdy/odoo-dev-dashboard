<template>
  <SidebarLayout>
    <template #breadcrumb>
      <Breadcrumb />
    </template>

    <div class="max-w-6xl mx-auto w-full space-y-8">

      <!-- Loading state -->
      <div v-if="store.loading && !store.projects.length"
           class="flex items-center justify-center py-32 text-slate-400">
        <div class="text-center">
          <div class="inline-block w-10 h-10 border-4 border-accent/30 border-t-accent rounded-full animate-spin mb-4"></div>
          <p class="text-sm font-medium">Loading projects…</p>
        </div>
      </div>

      <template v-else>

        <!-- Summary strip -->
        <div v-if="store.projects.length" class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="card !p-3 md:!p-4 text-center">
            <div class="text-2xl font-bold text-slate-100 tabular-nums">{{ store.projects.length }}</div>
            <div class="text-[11px] text-slate-500 uppercase tracking-wide mt-0.5">Projects</div>
          </div>
          <div class="card !p-3 md:!p-4 text-center">
            <div class="text-2xl font-bold text-emerald-400 tabular-nums">{{ runningCount }}</div>
            <div class="text-[11px] text-slate-500 uppercase tracking-wide mt-0.5">Running</div>
          </div>
          <div class="card !p-3 md:!p-4 text-center">
            <div class="text-2xl font-bold text-red-400 tabular-nums">{{ stoppedCount }}</div>
            <div class="text-[11px] text-slate-500 uppercase tracking-wide mt-0.5">Stopped</div>
          </div>
          <div class="card !p-3 md:!p-4 text-center">
            <div class="text-2xl font-bold text-slate-300 tabular-nums">{{ Object.keys(store.ungroupedByVersion).length }}</div>
            <div class="text-[11px] text-slate-500 uppercase tracking-wide mt-0.5">Versions</div>
          </div>
        </div>

        <!-- Projects by version -->
        <div
          v-for="(versionProjects, version, vIdx) in store.ungroupedByVersion"
          :key="version"
          class="fade-in-up"
          :style="{ animationDelay: `${vIdx * 60}ms` }"
        >
          <SectionHeader :title="`Odoo ${version}`" :count="versionProjects.length" />

          <!-- ── Desktop: table (md+) ─────────────────────────── -->
          <div class="card overflow-hidden hidden md:block">
            <table class="table-base w-full">
              <thead>
                <tr>
                  <th>Project</th>
                  <th class="text-center">Status</th>
                  <th>Branch</th>
                  <th>Databases</th>
                  <th class="hidden lg:table-cell">URL</th>
                  <th class="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(p, rowIdx) in versionProjects"
                  :key="p.name"
                  class="fade-in-row"
                  :style="{ animationDelay: `${rowIdx * 25}ms` }"
                  :class="p.status === 'running'
                    ? 'table-row-running'
                    : p.status === 'restarting'
                      ? 'table-row-restarting'
                      : 'table-row-stopped'"
                >
                  <td>
                    <RouterLink
                      :to="`/project/${p.name}`"
                      class="font-semibold hover:text-accent transition-colors"
                      :class="p.status === 'running' ? 'text-slate-200' : 'text-slate-400'"
                    >{{ p.name }}</RouterLink>
                    <span v-if="p.pending_count" class="ml-2 text-[10px] text-amber-400 font-medium">
                      {{ p.pending_count }} pending
                    </span>
                  </td>
                  <td class="text-center"><StatusBadge :status="p.status" /></td>
                  <td class="text-slate-400 text-xs font-mono">{{ p.branch || '—' }}</td>
                  <td>
                    <div v-if="databases[p.name] === undefined" class="text-slate-600 text-xs">…</div>
                    <div v-else-if="!databases[p.name].length" class="text-slate-600 text-xs">none</div>
                    <div v-else class="flex flex-wrap gap-1">
                      <RouterLink
                        v-for="db in databases[p.name]"
                        :key="db.name"
                        :to="`/project/${p.name}?tab=database`"
                        class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-secondary border border-border/60 text-slate-400 hover:border-accent/50 hover:text-accent transition-colors truncate max-w-[100px]"
                        :title="db.name"
                      >{{ db.name }}</RouterLink>
                    </div>
                  </td>
                  <td class="hidden lg:table-cell">
                    <a v-if="p.url" :href="`https://${p.url}`" target="_blank" rel="noopener"
                       class="text-xs text-slate-500 hover:text-accent transition-colors flex items-center gap-1">
                      <span class="truncate max-w-[140px]">{{ p.url }}</span>
                      <svg class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                      </svg>
                    </a>
                    <span v-else class="text-slate-600 text-xs">—</span>
                  </td>
                  <td class="text-right">
                    <div class="flex items-center justify-end gap-1.5">
                      <RouterLink :to="`/project/${p.name}`" class="btn btn-ghost btn-sm text-xs">Open</RouterLink>
                      <button
                        class="btn btn-ghost btn-sm text-xs"
                        :disabled="!p.running"
                        @click="restartProject(p.container)"
                      >Restart</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ── Mobile: cards (< md) ─────────────────────────── -->
          <div class="grid gap-3 md:hidden">
            <div
              v-for="(p, rowIdx) in versionProjects"
              :key="p.name"
              class="card !p-4 fade-in-row"
              :style="{ animationDelay: `${rowIdx * 25}ms` }"
            >
              <!-- Card top: name + status -->
              <div class="flex items-start justify-between gap-2 mb-3">
                <div class="min-w-0">
                  <RouterLink
                    :to="`/project/${p.name}`"
                    class="font-semibold hover:text-accent transition-colors text-sm truncate block"
                    :class="p.status === 'running' ? 'text-slate-100' : 'text-slate-400'"
                  >{{ p.name }}</RouterLink>
                  <div class="flex items-center gap-2 mt-1">
                    <span v-if="p.branch" class="text-[11px] font-mono text-slate-500 truncate max-w-[140px]">{{ p.branch }}</span>
                    <span v-if="p.pending_count" class="text-[10px] text-amber-400 font-medium">{{ p.pending_count }} pending</span>
                  </div>
                </div>
                <StatusBadge :status="p.status" class="shrink-0" />
              </div>

              <!-- Card meta row -->
              <div class="flex items-center gap-3 mb-3 flex-wrap">
                <!-- Databases -->
                <div class="flex flex-wrap gap-1">
                  <span v-if="databases[p.name] === undefined" class="text-[11px] text-slate-600">Loading…</span>
                  <span v-else-if="!databases[p.name].length" class="text-[11px] text-slate-600">No databases</span>
                  <RouterLink
                    v-else
                    v-for="db in databases[p.name].slice(0, 3)"
                    :key="db.name"
                    :to="`/project/${p.name}?tab=database`"
                    class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-secondary border border-border/60 text-slate-400 hover:text-accent transition-colors truncate max-w-[100px]"
                  >{{ db.name }}</RouterLink>
                  <span v-if="databases[p.name] && databases[p.name].length > 3" class="text-[10px] text-slate-500">
                    +{{ databases[p.name].length - 3 }}
                  </span>
                </div>
              </div>

              <!-- Card actions -->
              <div class="flex gap-2 pt-2 border-t border-border/40">
                <RouterLink :to="`/project/${p.name}`" class="btn btn-primary btn-sm flex-1 text-xs justify-center">Open</RouterLink>
                <a v-if="p.url" :href="`https://${p.url}`" target="_blank" rel="noopener" class="btn btn-ghost btn-sm px-2.5" title="Open site">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                  </svg>
                </a>
                <button
                  class="btn btn-ghost btn-sm px-2.5"
                  :disabled="!p.running"
                  title="Restart"
                  @click="restartProject(p.container)"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="!store.projects.length" class="text-center py-20 text-slate-500">
          <div class="w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
            </svg>
          </div>
          <p class="text-sm font-medium text-slate-400">No projects found</p>
          <p class="text-xs text-slate-600 mt-1">Check the port registry or use New Project to add one.</p>
        </div>

      </template>
    </div>
  </SidebarLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useNotificationsStore } from '@/stores/notifications'
import { api } from '@/api'
import SidebarLayout from '@/layouts/SidebarLayout.vue'
import Breadcrumb from '@/components/Breadcrumb.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import SectionHeader from '@/components/SectionHeader.vue'

const store = useProjectsStore()
const notify = useNotificationsStore()

const databases = ref<Record<string, Array<{ name: string; size: string }>>>({})

const runningCount = computed(() => store.projects.filter(p => p.running).length)
const stoppedCount = computed(() => store.projects.filter(p => !p.running).length)

async function fetchDatabases(projects: typeof store.projects) {
  await Promise.allSettled(
    projects.map(async (p) => {
      if (databases.value[p.name] !== undefined) return
      try {
        const res = await api(`/api/db/${p.name}/list`)
        const data = await res.json()
        databases.value[p.name] = data.databases || []
      } catch {
        databases.value[p.name] = []
      }
    })
  )
}

onMounted(async () => {
  await store.fetchProjects()
  store.startSSE()
  fetchDatabases(store.projects)
})

watch(() => store.projects, (projects) => {
  fetchDatabases(projects)
}, { deep: false })

onUnmounted(() => store.stopSSE())

async function restartProject(containerName: string) {
  try {
    const res = await api(`/api/restart/${containerName}`, { method: 'POST' })
    const data = await res.json()
    notify.add(data.ok ? 'success' : 'error', data.ok ? 'Container restarted' : data.error)
  } catch {
    notify.add('error', 'Restart failed')
  }
}
</script>
