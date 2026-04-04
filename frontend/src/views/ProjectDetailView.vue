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
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          Logs
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
        <div class="card grid grid-cols-2 sm:flex sm:flex-col gap-2 md:gap-3 min-h-[44px] sm:min-h-0">
          <button class="btn btn-ghost min-h-[44px]" @click="restart">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            Restart
          </button>
          <button class="btn btn-danger min-h-[44px]" @click="stop">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd"></path>
            </svg>
            Stop
          </button>
          <button class="btn btn-primary min-h-[44px]" @click="deploy">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
            </svg>
            Deploy
          </button>
          <a v-if="project.url" :href="'https://' + project.url" target="_blank" class="btn btn-ghost min-h-[44px]">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
            </svg>
            Open
          </a>
          <button class="btn btn-danger min-h-[44px]" @click="showDeleteModal = true">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>
            Delete
          </button>
        </div>
      </div>

      <!-- Delete confirmation modal -->
      <Teleport to="body">
        <div v-if="showDeleteModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="closeDeleteModal" />
          <div class="relative bg-[#12151f] border border-red-500/30 rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-5">
            <!-- Header -->
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-full bg-red-500/15 border border-red-500/30 flex items-center justify-center shrink-0">
                <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                </svg>
              </div>
              <div>
                <h2 class="text-lg font-bold text-white">Delete project</h2>
                <p class="text-sm text-slate-400 mt-0.5">This action is permanent and cannot be undone.</p>
              </div>
            </div>

            <!-- What will be deleted -->
            <div class="bg-red-950/30 border border-red-500/20 rounded-lg p-3 space-y-1 text-xs text-red-300/80">
              <div class="flex items-center gap-2"><span class="text-red-400">✕</span> Docker containers stopped and removed</div>
              <div class="flex items-center gap-2"><span class="text-red-400">✕</span> All volumes deleted (databases + filestore)</div>
              <div class="flex items-center gap-2"><span class="text-red-400">✕</span> Project directory removed from disk</div>
              <div class="flex items-center gap-2"><span class="text-red-400">✕</span> Removed from port registry</div>
            </div>

            <!-- Confirmation input -->
            <div>
              <label class="block text-sm text-slate-300 mb-1.5">
                Type <code class="bg-slate-800 text-red-300 px-1.5 py-0.5 rounded text-xs">{{ name }}</code> to confirm
              </label>
              <input
                v-model="deleteConfirmText"
                class="input w-full"
                :class="{ 'border-red-500/60': deleteConfirmText && deleteConfirmText !== name }"
                placeholder="project name"
                @keyup.enter="confirmDelete"
                autofocus
              />
            </div>

            <!-- Actions -->
            <div class="flex gap-3 justify-end">
              <button class="btn btn-ghost" @click="closeDeleteModal" :disabled="deleting">Cancel</button>
              <button
                class="btn btn-danger inline-flex items-center gap-2"
                :disabled="deleteConfirmText !== name || deleting"
                @click="confirmDelete">
                <svg v-if="deleting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
                {{ deleting ? 'Deleting…' : 'Delete project' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>

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
            <div v-for="ap in project.addons_paths as AddonPath[]" :key="ap.path" class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 text-xs min-w-0">
              <span class="px-2.5 py-1 rounded-lg text-xs font-mono font-semibold shrink-0"
                :class="{
                  'bg-gradient-to-r from-blue-500/20 to-blue-600/20 text-blue-300 border border-blue-500/40': ap.kind === 'core',
                  'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-300 border border-amber-500/40': ap.kind === 'enterprise',
                  'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border border-green-500/40': ap.kind === 'extra',
                  'bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-300 border border-purple-500/40': ap.kind === 'project' || ap.kind === 'project-sub',
                  'bg-slate-800/50 text-slate-400 border border-slate-700/50': ap.kind === 'other',
                }">{{ ap.label }}</span>
              <code class="text-slate-500 break-all">{{ ap.path }}</code>
            </div>
          </div>
        </div>
        <!-- Recent commits -->
        <div class="card mb-4 min-w-0" v-if="(project.commits as unknown[])?.length">
          <h3 class="text-sm font-semibold mb-3 text-slate-300">Recent Commits</h3>
          <div class="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
            <table class="table-base min-w-[480px]">
              <thead><tr><th>Hash</th><th>Message</th><th>Author</th><th>Date</th></tr></thead>
              <tbody>
                <tr v-for="c in project.commits as Commit[]" :key="c.hash">
                  <td><code class="text-slate-400 text-xs">{{ c.hash }}</code></td>
                  <td class="text-slate-300 max-w-[120px] sm:max-w-none truncate" :title="c.subject">{{ c.subject }}</td>
                  <td class="text-slate-500 truncate max-w-[80px] sm:max-w-none" :title="c.author">{{ c.author }}</td>
                  <td class="text-slate-500 text-xs whitespace-nowrap">{{ c.date }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <!-- Audit log -->
        <div class="card mb-4 min-w-0">
          <h3 class="text-sm font-semibold mb-3 text-slate-300">Audit Log</h3>
          <div v-if="auditLog.length === 0" class="text-sm text-slate-500">No audit events yet.</div>
          <div v-else class="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
            <table class="table-base min-w-[480px]">
              <thead><tr><th>Time</th><th>Action</th><th>Detail</th><th>Outcome</th></tr></thead>
              <tbody>
                <tr v-for="a in auditLog as AuditEntry[]" :key="a.id">
                  <td class="text-slate-400 text-xs whitespace-nowrap">{{ new Date(a.triggered_at).toLocaleString() }}</td>
                  <td>
                    <span class="px-2 py-0.5 rounded text-xs font-mono"
                      :class="{
                        'bg-blue-500/15 text-blue-300': a.action === 'deploy',
                        'bg-amber-500/15 text-amber-300': a.action === 'backup',
                        'bg-purple-500/15 text-purple-300': a.action === 'restore',
                        'bg-red-500/15 text-red-300': a.action === 'db_drop',
                        'bg-cyan-500/15 text-cyan-300': a.action === 'branch_switch',
                        'bg-slate-500/15 text-slate-300': !['deploy','backup','restore','db_drop','branch_switch'].includes(a.action),
                      }">{{ a.action }}</span>
                  </td>
                  <td class="text-slate-400 text-xs max-w-[160px] truncate" :title="a.detail">{{ a.detail || '—' }}</td>
                  <td>
                    <span :class="a.outcome === 'success' ? 'text-green-400' : 'text-red-400'" class="text-xs">
                      {{ a.outcome === 'success' ? '✓' : '✗' }} {{ a.outcome }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Deploy history -->
        <div class="card min-w-0">
          <h3 class="text-sm font-semibold mb-3 text-slate-300">Deploy History</h3>
          <div v-if="history.length === 0" class="text-sm text-slate-500">No deploys yet.</div>
          <div v-else class="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
            <table class="table-base min-w-[560px]">
              <thead><tr><th>Time</th><th>Type</th><th>From</th><th>To</th><th>Outcome</th><th>Duration</th></tr></thead>
              <tbody>
                <tr v-for="h in history as DeployRecord[]" :key="h.id">
                  <td class="text-slate-400 text-xs whitespace-nowrap">{{ new Date(h.triggered_at).toLocaleString() }}</td>
                  <td>{{ h.trigger_type }}</td>
                  <td class="max-w-[70px] sm:max-w-[90px]"><code class="text-slate-500 text-xs truncate inline-block max-w-full align-bottom" :title="h.prev_commit || '—'">{{ h.prev_commit || '—' }}</code></td>
                  <td class="max-w-[70px] sm:max-w-[90px]"><code class="text-slate-500 text-xs truncate inline-block max-w-full align-bottom" :title="h.new_commit || '—'">{{ h.new_commit || '—' }}</code></td>
                  <td>
                    <span :class="h.outcome === 'success' ? 'text-green-400' : 'text-red-400'">
                      {{ h.outcome === 'success' ? '✓' : '✗' }} {{ h.outcome }}
                    </span>
                  </td>
                  <td class="text-slate-500 text-xs">{{ h.duration_seconds != null ? h.duration_seconds + 's' : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <EnvironmentsTab
        v-show="activeTab === 'environments'"
        :project-name="name"
        :project-url="(project.url as string) || ''"
        :current-branch="(project.branch as string) || undefined"
        :running="project.running as boolean"
        :active="activeTab === 'environments'"
      />
      <LogViewer v-show="activeTab === 'logs'" :container="project.container as string" :container-id="(project.container_id as string) || ''" :logs-url="config.logsUrl" :active="activeTab === 'logs'" />
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
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
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
import EnvironmentsTab from '@/components/EnvironmentsTab.vue'

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

interface AuditEntry {
  id: number
  triggered_at: string
  action: string
  detail: string
  outcome: string
}

const route    = useRoute()
const router   = useRouter()
const notify   = useNotificationsStore()
const config   = useConfigStore()
const projects = useProjectsStore()

const name    = route.params.name as string
const project = ref<Record<string, unknown> | null>(null)
const history = ref<unknown[]>([])
const auditLog = ref<unknown[]>([])
const activeTab   = ref('overview')
const deployPanel = ref<InstanceType<typeof DeployPanel> | null>(null)

const showDeleteModal   = ref(false)
const deleteConfirmText = ref('')
const deleting          = ref(false)

function closeDeleteModal() {
  showDeleteModal.value   = false
  deleteConfirmText.value = ''
}

async function confirmDelete() {
  if (deleteConfirmText.value !== name || deleting.value) return
  deleting.value = true
  const res = await fetch(`/api/project/${name}/delete`, { method: 'DELETE' })
  const d   = await res.json()
  deleting.value = false
  if (!d.ok) {
    notify.add('error', d.error || 'Delete failed')
    return
  }
  notify.add('success', `Project "${name}" deleted`)
  await projects.fetchProjects()
  router.push('/')
}

const tabs = [
  { id: 'overview',      label: 'Overview' },
  { id: 'environments',  label: 'Environments' },
  { id: 'logs',          label: 'Logs' },
  { id: 'database',      label: 'Database' },
  { id: 'modules',       label: 'Modules' },
  { id: 'branches',      label: 'Branches' },
  { id: 'settings',      label: 'Settings' },
  { id: 'notebook',      label: 'Notebook' },
]

onMounted(async () => {
  const [projRes, histRes, auditRes] = await Promise.all([
    fetch(`/api/project/${name}`),
    fetch(`/api/project/${name}/history`),
    fetch(`/api/project/${name}/audit`),
  ])
  project.value = await projRes.json()
  history.value = await histRes.json()
  auditLog.value = await auditRes.json()
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
