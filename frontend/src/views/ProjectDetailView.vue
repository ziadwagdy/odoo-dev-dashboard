<template>
  <div class="max-w-7xl mx-auto px-4 md:px-6 py-6 md:py-10">
    <!-- Back + header -->
    <div class="flex flex-col sm:flex-row sm:items-center gap-3 md:gap-4 mb-6 md:mb-8">
      <RouterLink to="/" class="btn btn-ghost btn-sm">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
        </svg>
        Back
      </RouterLink>
      <div class="hidden sm:block h-6 w-px bg-border"></div>
      <div class="flex flex-wrap items-center gap-2 md:gap-4 flex-1">
        <h1 class="text-2xl md:text-3xl font-bold bg-gradient-to-r from-white to-accent-light bg-clip-text text-transparent capitalize">{{ name }}</h1>
        <StatusBadge v-if="project" :status="project.status as string" />
        <a
          v-if="project && project.container_id && config.logsUrl"
          :href="config.logsUrl + '/container/' + project.container_id"
          target="_blank"
          rel="noopener"
          class="btn btn-ghost btn-sm sm:ml-auto"
        >
          📜 Logs
        </a>
      </div>
    </div>

    <div v-if="!project" class="text-center py-20 md:py-32 text-slate-400">
      <div class="inline-block w-10 h-10 md:w-12 md:h-12 border-4 border-accent/30 border-t-accent rounded-full animate-spin mb-4"></div>
      <p class="text-base md:text-lg font-medium">Loading project…</p>
    </div>

    <template v-else>
      <!-- Gauges row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-5 mb-6 md:mb-8">
        <div class="card flex items-center justify-center py-4">
          <CpuGauge :container="project.container as string" />
        </div>
        <div class="card">
          <MemoryBar :container="project.container as string" />
        </div>
        <div class="card flex flex-col gap-2 md:gap-3">
          <button class="btn btn-ghost" @click="restart">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            Restart
          </button>
          <button class="btn btn-danger" @click="stop">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd"></path>
            </svg>
            Stop
          </button>
          <button class="btn btn-primary" @click="deploy">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
            </svg>
            Deploy
          </button>
          <a v-if="project.url" :href="'https://' + project.url" target="_blank" class="btn btn-ghost">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
            </svg>
            Open
          </a>
        </div>
      </div>

      <!-- Deploy panel -->
      <DeployPanel :project-name="name" ref="deployPanel" />

      <!-- Tabs -->
      <div class="border-b border-border mb-6 flex gap-0.5 md:gap-1 overflow-x-auto">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn text-xs md:text-sm whitespace-nowrap"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>

      <!-- Tab content -->
      <div v-show="activeTab === 'overview'">
        <!-- Stack info -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-5 mb-6">
          <div class="card">
            <div class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Container</div>
            <div class="font-mono text-sm text-white">{{ project.container }}</div>
          </div>
          <div class="card">
            <div class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Branch</div>
            <div class="font-mono text-sm text-white">{{ project.branch || '—' }}</div>
          </div>
          <div class="card">
            <div class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Odoo Port</div>
            <div class="font-mono text-sm text-white">{{ project.odoo_port }}</div>
          </div>
          <div class="card">
            <div class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">DB Port</div>
            <div class="font-mono text-sm text-white">{{ project.db_port }}</div>
          </div>
        </div>
        <!-- Addons paths -->
        <div class="card mb-4" v-if="(project.addons_paths as unknown[])?.length">
          <h3 class="text-sm font-bold mb-4 text-slate-200 uppercase tracking-wider">Addons Paths</h3>
          <div class="space-y-2">
            <div v-for="ap in project.addons_paths as AddonPath[]" :key="ap.path" class="flex items-center gap-3 text-xs">
              <span class="px-2.5 py-1 rounded-lg text-xs font-mono font-semibold"
                :class="{
                  'bg-gradient-to-r from-blue-500/20 to-blue-600/20 text-blue-300 border border-blue-500/40': ap.kind === 'core',
                  'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-300 border border-amber-500/40': ap.kind === 'enterprise',
                  'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border border-green-500/40': ap.kind === 'extra',
                  'bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-300 border border-purple-500/40': ap.kind === 'project' || ap.kind === 'project-sub',
                  'bg-slate-800/50 text-slate-400 border border-slate-700/50': ap.kind === 'other',
                }">{{ ap.label }}</span>
              <code class="text-slate-500">{{ ap.path }}</code>
            </div>
          </div>
        </div>
        <!-- Recent commits -->
        <div class="card mb-4" v-if="(project.commits as unknown[])?.length">
          <h3 class="text-sm font-semibold mb-3 text-slate-300">Recent Commits</h3>
          <table class="table-base">
            <thead><tr><th>Hash</th><th>Message</th><th>Author</th><th>Date</th></tr></thead>
            <tbody>
              <tr v-for="c in project.commits as Commit[]" :key="c.hash">
                <td><code class="text-slate-400">{{ c.hash }}</code></td>
                <td class="text-slate-300">{{ c.subject }}</td>
                <td class="text-slate-500">{{ c.author }}</td>
                <td class="text-slate-500">{{ c.date }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Deploy history -->
        <div class="card">
          <h3 class="text-sm font-semibold mb-3 text-slate-300">Deploy History</h3>
          <div v-if="history.length === 0" class="text-sm text-slate-500">No deploys yet.</div>
          <table v-else class="table-base">
            <thead><tr><th>Time</th><th>Type</th><th>From</th><th>To</th><th>Outcome</th><th>Duration</th></tr></thead>
            <tbody>
              <tr v-for="h in history as DeployRecord[]" :key="h.id">
                <td class="text-slate-400">{{ new Date(h.triggered_at).toLocaleString() }}</td>
                <td>{{ h.trigger_type }}</td>
                <td><code class="text-slate-500">{{ h.prev_commit || '—' }}</code></td>
                <td><code class="text-slate-500">{{ h.new_commit || '—' }}</code></td>
                <td>
                  <span :class="h.outcome === 'success' ? 'text-green-400' : 'text-red-400'">
                    {{ h.outcome === 'success' ? '✓' : '✗' }} {{ h.outcome }}
                  </span>
                </td>
                <td class="text-slate-500">{{ h.duration_seconds != null ? h.duration_seconds + 's' : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <LogViewer v-show="activeTab === 'logs'" :container="project.container as string" :active="activeTab === 'logs'" />
      <DatabaseTab v-show="activeTab === 'database'" :project-name="name" :active="activeTab === 'database'" />
      <ModulesTab v-show="activeTab === 'modules'" :project-name="name" :active="activeTab === 'modules'" />
      <BranchTab v-show="activeTab === 'branches'" :project-name="name" :folder="(project.folder as string | null)" :container="(project.container as string)" :active="activeTab === 'branches'" />
      <SettingsTab v-show="activeTab === 'settings'" :project-name="name" :active="activeTab === 'settings'" />
      <NotebookTab v-show="activeTab === 'notebook'" :project-name="name" :active="activeTab === 'notebook'" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import { useConfigStore } from '@/stores/config'
import StatusBadge from '@/components/StatusBadge.vue'
import CpuGauge from '@/components/CpuGauge.vue'
import MemoryBar from '@/components/MemoryBar.vue'
import LogViewer from '@/components/LogViewer.vue'
import DeployPanel from '@/components/DeployPanel.vue'
import DatabaseTab from '@/components/DatabaseTab.vue'
import ModulesTab from '@/components/ModulesTab.vue'
import BranchTab from '@/components/BranchTab.vue'
import SettingsTab from '@/components/SettingsTab.vue'
import NotebookTab from '@/components/NotebookTab.vue'

interface AddonPath { path: string; kind: string; label: string }
interface Commit { hash: string; subject: string; author: string; date: string }
interface DeployRecord {
  id: number
  triggered_at: string
  trigger_type: string
  prev_commit: string | null
  new_commit: string | null
  outcome: string
  duration_seconds: number | null
}

const route = useRoute()
const notify = useNotificationsStore()
const config = useConfigStore()

const name = route.params.name as string
const project = ref<Record<string, unknown> | null>(null)
const history = ref<unknown[]>([])
const activeTab = ref('overview')
const deployPanel = ref<InstanceType<typeof DeployPanel> | null>(null)

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'logs', label: 'Logs' },
  { id: 'database', label: 'Database' },
  { id: 'modules', label: 'Modules' },
  { id: 'branches', label: 'Branches' },
  { id: 'settings', label: 'Settings' },
  { id: 'notebook', label: 'Notebook' },
]

onMounted(async () => {
  const [projRes, histRes] = await Promise.all([
    fetch(`/api/project/${name}`),
    fetch(`/api/project/${name}/history`),
  ])
  project.value = await projRes.json()
  history.value = await histRes.json()
})

async function restart() {
  const res = await fetch(`/api/restart/${project.value?.container}`, { method: 'POST' })
  const d = await res.json()
  notify.add(d.ok ? 'success' : 'error', d.ok ? 'Restarted' : d.error)
}

async function stop() {
  if (!confirm('Stop this container?')) return
  const res = await fetch(`/api/stop/${project.value?.container}`, { method: 'POST' })
  const d = await res.json()
  notify.add(d.ok ? 'success' : 'error', d.ok ? 'Stopped' : d.error)
}

async function deploy() {
  deployPanel.value?.trigger()
}
</script>
