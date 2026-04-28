<template>
  <SidebarLayout>
    <template #breadcrumb>
      <Breadcrumb :crumbs="[{ label: 'Health Monitor' }]" />
    </template>
    <div class="max-w-4xl">

    <!-- Host System -->
    <div class="card mb-6">
      <div class="flex items-center gap-3 mb-6">
        <h2 class="text-xs font-bold uppercase tracking-widest text-slate-400">Host System</h2>
        <div class="h-px flex-1 bg-gradient-to-r from-border to-transparent"></div>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-6 md:gap-8">
        <!-- CPU -->
        <div class="flex flex-col items-center">
          <CpuGauge :value="hostStats?.cpu_pct ?? null" />
        </div>

        <!-- Memory -->
        <div class="flex flex-col gap-2 justify-center">
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm font-semibold text-slate-300">Memory</span>
            <span class="text-xs font-mono text-slate-400">
              {{ hostStats ? `${hostStats.mem_used_mb.toFixed(0)} / ${hostStats.mem_total_mb.toFixed(0)} MB` : '-- / -- MB' }}
            </span>
          </div>
          <div class="h-3 rounded-full bg-surface-hover overflow-hidden border border-border/50 shadow-inner">
            <div class="h-full rounded-full transition-all duration-500"
              :style="{ width: (hostStats?.mem_pct ?? 0) + '%' }"
              :class="memBarClass(hostStats?.mem_pct ?? 0)"
            />
          </div>
          <span class="text-xs text-slate-400 mt-1 font-semibold">{{ hostStats ? hostStats.mem_pct.toFixed(1) + '%' : '--' }}</span>
        </div>

        <!-- Disk -->
        <div class="flex flex-col gap-2 justify-center">
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm font-semibold text-slate-300">Disk</span>
            <span class="text-xs font-mono text-slate-400">
              {{ hostStats ? `${hostStats.disk_used_gb.toFixed(1)} / ${hostStats.disk_total_gb.toFixed(1)} GB` : '-- / -- GB' }}
            </span>
          </div>
          <div class="h-3 rounded-full bg-surface-hover overflow-hidden border border-border/50 shadow-inner">
            <div class="h-full rounded-full transition-all duration-500"
              :style="{ width: (hostStats?.disk_pct ?? 0) + '%' }"
              :class="memBarClass(hostStats?.disk_pct ?? 0)"
            />
          </div>
          <span class="text-xs text-slate-400 mt-1 font-semibold">{{ hostStats ? hostStats.disk_pct.toFixed(1) + '%' : '--' }}</span>
        </div>
      </div>
    </div>

    <!-- Containers -->
    <div class="card">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
          <h2 class="text-xs font-bold uppercase tracking-widest text-slate-400">Containers</h2>
          <div class="h-px w-20 bg-gradient-to-r from-border to-transparent"></div>
        </div>
        <span class="px-3 py-1.5 bg-surface-hover rounded-full text-xs font-semibold text-slate-300 border border-border">
          {{ runningCount }} / {{ containerStats.length }} running
        </span>
      </div>

      <div v-if="containerStats.length === 0" class="text-center py-12 text-slate-400">
        <div class="inline-block w-10 h-10 border-3 border-accent/30 border-t-accent rounded-full animate-spin mb-3"></div>
        <p class="text-sm font-medium">Loading containers…</p>
      </div>

      <template v-else>
        <!-- Mobile: Card Layout -->
        <div class="md:hidden space-y-3">
        <div
          v-for="c in sortedContainers"
          :key="c.name"
          class="bg-surface-hover/50 rounded-lg p-4 border border-border/30"
          :class="c.status !== 'running' ? 'opacity-40' : ''"
        >
          <!-- Header -->
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold text-white capitalize">{{ c.name }}</h3>
            <span class="badge text-xs" :class="{
              'badge-running': c.status === 'running',
              'badge-exited': c.status === 'exited' || c.status === 'not_found',
              'badge-restarting': c.status === 'restarting',
            }">{{ c.status }}</span>
          </div>

          <!-- Stats -->
          <div class="space-y-3">
            <!-- CPU -->
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-xs text-slate-400 font-medium">CPU</span>
                <span class="text-xs text-slate-300 font-semibold">
                  {{ c.cpu_pct !== null ? c.cpu_pct.toFixed(1) + '%' : '—' }}
                </span>
              </div>
              <template v-if="c.cpu_pct !== null">
                <div class="h-2 rounded-full bg-surface overflow-hidden border border-border/50">
                  <div class="h-full rounded transition-all duration-500"
                    :style="{ width: Math.min(c.cpu_pct, 100) + '%' }"
                    :class="barClass(c.cpu_pct)"
                  />
                </div>
              </template>
            </div>

            <!-- Memory -->
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-xs text-slate-400 font-medium">Memory</span>
                <span class="text-xs text-slate-300 font-mono">
                  {{ c.mem_used_mb !== null ? `${c.mem_used_mb.toFixed(0)} / ${c.mem_limit_mb?.toFixed(0)} MB` : '—' }}
                </span>
              </div>
              <template v-if="c.mem_pct !== null">
                <div class="h-2 rounded-full bg-surface overflow-hidden border border-border/50">
                  <div class="h-full rounded transition-all duration-500"
                    :style="{ width: Math.min(c.mem_pct, 100) + '%' }"
                    :class="barClass(c.mem_pct)"
                  />
                </div>
                <div class="text-xs text-slate-400 mt-1">{{ c.mem_pct.toFixed(1) }}%</div>
              </template>
            </div>
          </div>
        </div>
      </div>

        <!-- Desktop: Table Layout -->
        <div class="hidden md:block overflow-x-auto">
        <table class="table-base w-full">
          <thead>
            <tr>
              <th class="text-left">Project</th>
              <th class="text-left">Status</th>
              <th class="text-left">CPU</th>
              <th class="text-left">Memory</th>
              <th class="text-left">Mem %</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in sortedContainers"
              :key="c.name"
              :class="c.status !== 'running' ? 'opacity-40' : ''"
            >
              <td class="font-semibold text-white capitalize">{{ c.name }}</td>
              <td>
                <span class="badge text-xs" :class="{
                  'badge-running': c.status === 'running',
                  'badge-exited': c.status === 'exited' || c.status === 'not_found',
                  'badge-restarting': c.status === 'restarting',
                }">{{ c.status }}</span>
              </td>
              <td>
                <template v-if="c.cpu_pct !== null">
                  <div class="flex items-center gap-2">
                    <div class="w-24 h-2 rounded-full bg-surface-hover overflow-hidden border border-border/50">
                      <div class="h-full rounded transition-all duration-500"
                        :style="{ width: Math.min(c.cpu_pct, 100) + '%' }"
                        :class="barClass(c.cpu_pct)"
                      />
                    </div>
                    <span class="text-xs text-slate-300 w-12">{{ c.cpu_pct.toFixed(1) }}%</span>
                  </div>
                </template>
                <span v-else class="text-slate-600">—</span>
              </td>
              <td class="text-xs font-mono text-slate-300">
                <template v-if="c.mem_used_mb !== null">
                  {{ c.mem_used_mb.toFixed(0) }} / {{ c.mem_limit_mb?.toFixed(0) }} MB
                </template>
                <span v-else class="text-slate-600">—</span>
              </td>
              <td>
                <template v-if="c.mem_pct !== null">
                  <div class="flex items-center gap-2">
                    <div class="w-20 h-1.5 rounded bg-[#2d3148] overflow-hidden">
                      <div class="h-full rounded transition-all duration-500"
                        :style="{ width: Math.min(c.mem_pct, 100) + '%' }"
                        :class="barClass(c.mem_pct)"
                      />
                    </div>
                    <span class="text-xs text-slate-300 w-12">{{ c.mem_pct.toFixed(1) }}%</span>
                  </div>
                </template>
                <span v-else class="text-slate-600">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      </template>
    </div>
      <!-- Storage Breakdown -->
      <div class="card !p-0 mt-6 overflow-hidden">
        <div class="flex items-center justify-between px-5 py-4 border-b border-border/40">
          <div class="flex items-center gap-3">
            <h2 class="text-xs font-bold uppercase tracking-widest text-slate-400">Disk — Project Breakdown</h2>
          </div>
          <div class="flex items-center gap-3">
            <!-- Legend -->
            <div class="hidden sm:flex items-center gap-3 text-[11px]" style="color:rgb(var(--t-muted))">
              <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-blue-500/80 inline-block"></span>Database</span>
              <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-accent/80 inline-block"></span>Filestore</span>
              <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-emerald-500/80 inline-block"></span>Code</span>
            </div>
            <button
              class="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-border/60 hover:border-accent/40 hover:bg-accent/10 transition-all"
              style="color:rgb(var(--t-sec))"
              :disabled="storageLoading"
              @click="fetchStorage"
            >
              <svg class="w-3.5 h-3.5" :class="storageLoading ? 'animate-spin' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              {{ storageLoading ? 'Scanning…' : 'Refresh' }}
            </button>
          </div>
        </div>

        <div v-if="!storageData && !storageLoading" class="flex flex-col items-center justify-center py-12 gap-3">
          <svg class="w-8 h-8 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"/></svg>
          <p class="text-sm" style="color:rgb(var(--t-muted))">Click Refresh to scan project disk usage</p>
        </div>

        <div v-else-if="storageLoading && !storageData" class="flex items-center justify-center py-12 gap-2 text-sm" style="color:rgb(var(--t-muted))">
          <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
          Scanning all projects…
        </div>

        <div v-else-if="storageData">
          <!-- Host disk summary bar -->
          <div class="px-5 py-3 border-b border-border/20 flex items-center gap-4">
            <span class="text-xs font-medium w-20 shrink-0" style="color:rgb(var(--t-muted))">Host disk</span>
            <div class="flex-1 h-2.5 rounded-full overflow-hidden bg-surface-hover border border-border/40">
              <div
                class="h-full rounded-full transition-all duration-700"
                :class="storageData.disk_pct > 90 ? 'bg-red-500' : storageData.disk_pct > 75 ? 'bg-amber-500' : 'bg-indigo-500'"
                :style="{ width: storageData.disk_pct + '%' }"
              />
            </div>
            <span class="text-xs font-mono shrink-0 text-slate-400">{{ storageData.disk_used_gb }} / {{ storageData.disk_total_gb }} GB</span>
            <span class="text-xs font-semibold shrink-0 w-10 text-right"
              :class="storageData.disk_pct > 90 ? 'text-red-400' : storageData.disk_pct > 75 ? 'text-amber-400' : 'text-slate-300'">
              {{ storageData.disk_pct }}%
            </span>
          </div>

          <!-- Per-project rows -->
          <div class="divide-y divide-border/20">
            <div
              v-for="p in storageData.projects"
              :key="p.name"
              class="flex items-center gap-4 px-5 py-3 hover:bg-surface-hover/30 transition-colors"
            >
              <!-- Name -->
              <span class="text-sm font-medium text-slate-300 w-32 shrink-0 truncate" :title="p.name">{{ p.name }}</span>

              <!-- Stacked bar -->
              <div class="flex-1 h-5 rounded-lg overflow-hidden bg-surface-hover border border-border/30 flex min-w-0">
                <div
                  v-if="p.db_bytes"
                  class="h-full bg-blue-500/70 transition-all duration-700 hover:bg-blue-500"
                  :style="{ width: pct(p.db_bytes, maxTotal) + '%' }"
                  :title="`Database: ${fmt(p.db_bytes)}`"
                />
                <div
                  v-if="p.filestore_bytes"
                  class="h-full bg-accent/70 transition-all duration-700 hover:bg-accent"
                  :style="{ width: pct(p.filestore_bytes, maxTotal) + '%' }"
                  :title="`Filestore: ${fmt(p.filestore_bytes)}`"
                />
                <div
                  v-if="p.code_bytes"
                  class="h-full bg-emerald-500/70 transition-all duration-700 hover:bg-emerald-500"
                  :style="{ width: pct(p.code_bytes, maxTotal) + '%' }"
                  :title="`Code: ${fmt(p.code_bytes)}`"
                />
              </div>

              <!-- Breakdown numbers -->
              <div class="hidden lg:flex items-center gap-3 text-[11px] shrink-0" style="color:rgb(var(--t-muted))">
                <span v-if="p.db_bytes" class="text-blue-400/80">DB {{ fmt(p.db_bytes) }}</span>
                <span v-if="p.filestore_bytes" class="text-accent/80">FS {{ fmt(p.filestore_bytes) }}</span>
                <span v-if="p.code_bytes" class="text-emerald-400/80">Code {{ fmt(p.code_bytes) }}</span>
              </div>

              <!-- Total -->
              <span class="text-sm font-mono font-semibold text-slate-300 w-16 text-right shrink-0">{{ fmt(p.total_bytes) }}</span>
            </div>

            <div v-if="storageData.projects.length === 0" class="px-5 py-8 text-center text-sm" style="color:rgb(var(--t-muted))">
              No projects found
            </div>
          </div>
        </div>
      </div>

    </div>
  </SidebarLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/api'
import SidebarLayout from '@/layouts/SidebarLayout.vue'
import Breadcrumb from '@/components/Breadcrumb.vue'
import CpuGauge from '@/components/CpuGauge.vue'

interface HostStats {
  cpu_pct: number
  mem_used_mb: number
  mem_total_mb: number
  mem_pct: number
  disk_used_gb: number
  disk_total_gb: number
  disk_pct: number
}

interface ContainerStat {
  name: string
  container: string
  status: string
  cpu_pct: number | null
  mem_used_mb: number | null
  mem_limit_mb: number | null
  mem_pct: number | null
}

interface ProjectStorage {
  name: string
  filestore_bytes: number
  code_bytes: number
  db_bytes: number
  total_bytes: number
}

interface StorageData {
  projects: ProjectStorage[]
  disk_used_gb: number
  disk_total_gb: number
  disk_pct: number
}

const hostStats = ref<HostStats | null>(null)
const containerStats = ref<ContainerStat[]>([])
const storageData = ref<StorageData | null>(null)
const storageLoading = ref(false)

let hostSrc: EventSource | null = null
let containerSrc: EventSource | null = null

const runningCount = computed(() => containerStats.value.filter(c => c.status === 'running').length)

const sortedContainers = computed(() =>
  [...containerStats.value].sort((a, b) => {
    if (a.status === 'running' && b.status !== 'running') return -1
    if (a.status !== 'running' && b.status === 'running') return 1
    return a.name.localeCompare(b.name)
  })
)

const maxTotal = computed(() =>
  Math.max(...(storageData.value?.projects.map(p => p.total_bytes) ?? [1]), 1)
)

function fmt(bytes: number): string {
  if (bytes >= 1024 ** 3) return (bytes / 1024 ** 3).toFixed(1) + ' GB'
  if (bytes >= 1024 ** 2) return (bytes / 1024 ** 2).toFixed(0) + ' MB'
  if (bytes >= 1024)      return (bytes / 1024).toFixed(0) + ' KB'
  return bytes + ' B'
}

function pct(part: number, total: number): number {
  return total > 0 ? Math.round((part / total) * 100) : 0
}

async function fetchStorage() {
  storageLoading.value = true
  try {
    const res = await api('/api/storage')
    storageData.value = await res.json()
  } finally {
    storageLoading.value = false
  }
}

function barClass(pct: number) {
  if (pct > 90) return 'bg-red-400'
  if (pct > 75) return 'bg-amber-400'
  return 'bg-indigo-500'
}

function memBarClass(pct: number) {
  if (pct > 90) return 'bg-red-500'
  if (pct > 75) return 'bg-amber-500'
  return 'bg-[#6366f1]'
}

onMounted(() => {
  hostSrc = new EventSource('/stream/health/host')
  hostSrc.onmessage = (e) => { hostStats.value = JSON.parse(e.data) }

  containerSrc = new EventSource('/stream/health/containers')
  containerSrc.onmessage = (e) => { containerStats.value = JSON.parse(e.data) }
})

onUnmounted(() => {
  hostSrc?.close()
  containerSrc?.close()
})
</script>
