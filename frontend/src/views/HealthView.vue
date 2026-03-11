<template>
  <div class="max-w-7xl mx-auto px-6 py-8">
    <!-- Header -->
    <div class="flex items-center gap-4 mb-8">
      <RouterLink to="/" class="text-slate-400 hover:text-white transition-colors text-sm">← Dashboard</RouterLink>
      <h1 class="text-2xl font-bold text-white">Health Monitor</h1>
      <span class="text-xs text-slate-500 ml-auto">Live · every 3s</span>
    </div>

    <!-- Host System -->
    <div class="card mb-6">
      <h2 class="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">Host System</h2>
      <div class="grid grid-cols-3 gap-6">
        <!-- CPU -->
        <div class="flex flex-col items-center">
          <CpuGauge :value="hostStats?.cpu_pct ?? null" />
        </div>

        <!-- Memory -->
        <div class="flex flex-col gap-1 justify-center">
          <div class="flex justify-between items-center mb-1">
            <span class="text-xs text-slate-500">Memory</span>
            <span class="text-xs font-mono text-slate-300">
              {{ hostStats ? `${hostStats.mem_used_mb.toFixed(0)} / ${hostStats.mem_total_mb.toFixed(0)} MB` : '-- / -- MB' }}
            </span>
          </div>
          <div class="h-2 rounded-full bg-[#2d3148] overflow-hidden">
            <div class="h-full rounded-full transition-all duration-500"
              :style="{ width: (hostStats?.mem_pct ?? 0) + '%' }"
              :class="memBarClass(hostStats?.mem_pct ?? 0)"
            />
          </div>
          <span class="text-xs text-slate-500 mt-1">{{ hostStats ? hostStats.mem_pct.toFixed(1) + '%' : '--' }}</span>
        </div>

        <!-- Disk -->
        <div class="flex flex-col gap-1 justify-center">
          <div class="flex justify-between items-center mb-1">
            <span class="text-xs text-slate-500">Disk</span>
            <span class="text-xs font-mono text-slate-300">
              {{ hostStats ? `${hostStats.disk_used_gb.toFixed(1)} / ${hostStats.disk_total_gb.toFixed(1)} GB` : '-- / -- GB' }}
            </span>
          </div>
          <div class="h-2 rounded-full bg-[#2d3148] overflow-hidden">
            <div class="h-full rounded-full transition-all duration-500"
              :style="{ width: (hostStats?.disk_pct ?? 0) + '%' }"
              :class="memBarClass(hostStats?.disk_pct ?? 0)"
            />
          </div>
          <span class="text-xs text-slate-500 mt-1">{{ hostStats ? hostStats.disk_pct.toFixed(1) + '%' : '--' }}</span>
        </div>
      </div>
    </div>

    <!-- Containers -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-slate-500">Containers</h2>
        <span class="badge bg-[#2d3148] text-slate-400 text-xs">
          {{ runningCount }} / {{ containerStats.length }} running
        </span>
      </div>

      <div v-if="containerStats.length === 0" class="text-center py-8 text-slate-500 text-sm">
        Loading…
      </div>

      <table v-else class="table-base w-full">
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
            <td class="font-medium text-white capitalize">{{ c.name }}</td>
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
                  <div class="w-20 h-1.5 rounded bg-[#2d3148] overflow-hidden">
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
