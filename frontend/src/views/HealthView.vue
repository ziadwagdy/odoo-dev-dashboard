<template>
  <div class="max-w-7xl mx-auto px-4 md:px-6 py-6 md:py-10">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center gap-3 md:gap-4 mb-6 md:mb-10">
      <RouterLink to="/" class="btn btn-ghost btn-sm">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
        </svg>
        Dashboard
      </RouterLink>
      <div class="hidden sm:block h-6 w-px bg-border"></div>
      <h1 class="text-2xl md:text-3xl font-bold bg-gradient-to-r from-white to-accent-light bg-clip-text text-transparent">Health Monitor</h1>
      <span class="hidden md:flex items-center gap-2 ml-auto text-xs text-slate-400">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span class="font-medium text-emerald-400">Live</span>
        <span class="text-slate-500">· updates every 3s</span>
      </span>
    </div>

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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
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

const hostStats = ref<HostStats | null>(null)
const containerStats = ref<ContainerStat[]>([])

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
