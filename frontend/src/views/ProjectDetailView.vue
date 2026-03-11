<template>
  <div class="max-w-7xl mx-auto px-6 py-8">
    <!-- Back + header -->
    <div class="flex items-center gap-4 mb-6">
      <RouterLink to="/" class="text-slate-500 hover:text-white transition-colors">← Back</RouterLink>
      <div class="flex items-center gap-3">
        <h1 class="text-xl font-bold text-white capitalize">{{ name }}</h1>
        <StatusBadge v-if="project" :status="project.status as string" />
        <a
          v-if="project && project.container_id && config.logsUrl"
          :href="config.logsUrl + '/container/' + project.container_id"
          target="_blank"
          rel="noopener"
          class="btn btn-ghost btn-sm text-xs"
        >📜 Logs</a>
      </div>
    </div>

    <div v-if="!project" class="text-center py-20 text-slate-500">Loading…</div>

    <template v-else>
      <!-- Gauges row -->
      <div class="flex gap-4 mb-6">
        <CpuGauge :container="project.container as string" />
        <MemoryBar :container="project.container as string" />
        <div class="flex-1 card flex items-center gap-3 flex-wrap">
          <button class="btn btn-ghost btn-sm" @click="restart">↺ Restart</button>
          <button class="btn btn-danger btn-sm" @click="stop">⏹ Stop</button>
          <button class="btn btn-primary btn-sm" @click="deploy">⬆ Deploy</button>
          <a v-if="project.url" :href="'https://' + project.url" target="_blank" class="btn btn-ghost btn-sm">↗ Open</a>
        </div>
      </div>

      <!-- Deploy panel -->
      <DeployPanel :project-name="name" ref="deployPanel" />

      <!-- Tabs -->
      <div class="border-b border-[#2d3148] mb-6 flex gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>

      <!-- Tab content -->
      <div v-show="activeTab === 'overview'">
        <!-- Stack info -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div class="card">
            <div class="text-xs text-slate-500 mb-1">Container</div>
            <div class="font-mono text-sm">{{ project.container }}</div>
          </div>
          <div class="card">
            <div class="text-xs text-slate-500 mb-1">Branch</div>
            <div class="font-mono text-sm">{{ project.branch || '—' }}</div>
          </div>
          <div class="card">
            <div class="text-xs text-slate-500 mb-1">Odoo Port</div>
            <div class="font-mono text-sm">{{ project.odoo_port }}</div>
          </div>
          <div class="card">
            <div class="text-xs text-slate-500 mb-1">DB Port</div>
            <div class="font-mono text-sm">{{ project.db_port }}</div>
          </div>
        </div>
        <!-- Addons paths -->
        <div class="card mb-4" v-if="(project.addons_paths as unknown[])?.length">
          <h3 class="text-sm font-semibold mb-3 text-slate-300">Addons Paths</h3>
          <div class="space-y-1">
            <div v-for="ap in project.addons_paths as AddonPath[]" :key="ap.path" class="flex items-center gap-2 text-xs">
              <span class="px-1.5 py-0.5 rounded text-xs font-mono"
                :class="{
                  'bg-blue-900/40 text-blue-300': ap.kind === 'core',
                  'bg-amber-900/40 text-amber-300': ap.kind === 'enterprise',
                  'bg-green-900/40 text-green-300': ap.kind === 'extra',
                  'bg-purple-900/40 text-purple-300': ap.kind === 'project' || ap.kind === 'project-sub',
                  'bg-slate-800 text-slate-400': ap.kind === 'other',
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
      <BranchTab v-show="activeTab === 'branches'" :project-name="name" :folder="(project.folder as string | null)" :active="activeTab === 'branches'" />
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
