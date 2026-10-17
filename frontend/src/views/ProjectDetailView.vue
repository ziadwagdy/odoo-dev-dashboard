<template>
  <SidebarLayout>
    <template #breadcrumb>
      <Breadcrumb :crumbs="[{ label: name }]" />
    </template>
    <div class="max-w-7xl">
    <!-- Project title row -->
    <div class="flex items-center gap-3 mb-6">
      <h1 class="text-xl font-bold text-slate-100 capitalize">{{ name }}</h1>
      <StatusBadge v-if="project" :status="project.status as string" />
      <a
        v-if="project && project.container_id && config.logsUrl"
        :href="config.logsUrl + '/container/' + project.container_id"
        target="_blank" rel="noopener"
        class="btn btn-ghost btn-sm ml-auto"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        Logs
      </a>
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
          <button v-if="project.status === 'running'" class="btn btn-ghost min-h-[44px]" @click="restart">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            Restart
          </button>
          <button v-if="project.status === 'running'" class="btn btn-danger min-h-[44px]" @click="stop">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd"></path>
            </svg>
            Stop
          </button>
          <button v-else class="btn btn-primary min-h-[44px]" @click="start">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Start
          </button>
          <button class="btn btn-primary min-h-[44px]" @click="showOpenAs = true" title="Sign in to a database of this project without a password">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
            </svg>
            Open as…
          </button>
        </div>
      </div>

      <OpenAsModal v-if="showOpenAs" :project-name="name" @close="showOpenAs = false" />

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
      <!-- Manage (admins only): deploy and delete -->
      <div v-if="auth.isAdmin" v-show="activeTab === 'manage'" class="space-y-4">
        <div class="card">
          <h3 class="text-sm font-semibold text-slate-300 mb-1">Deploy</h3>
          <p class="text-xs text-slate-500 mb-3">Pull the latest code for this project and restart it. Output appears below.</p>
          <button class="btn btn-primary min-h-[44px]" @click="deploy">Deploy now</button>
        </div>
        <DeployPanel :project-name="name" ref="deployPanel" />
        <div class="card border border-red-900/40">
          <h3 class="text-sm font-semibold text-red-400 mb-1">Danger zone</h3>
          <p class="text-xs text-slate-500 mb-3">Deleting a project stops its containers and removes its data. This cannot be undone.</p>
          <button v-if="auth.canDelete" class="btn btn-danger min-h-[44px]" @click="showDeleteModal = true">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>
            Delete
          </button>
        </div>
      </div>

      <div v-show="activeTab === 'overview'">
        <!-- Stack info -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-5 mb-6">
          <div class="card">
            <div class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Odoo version</div>
            <div class="font-mono text-sm text-white">{{ project.version }}</div>
          </div>
          <div class="card">
            <div class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Branch</div>
            <div class="font-mono text-sm text-white">{{ project.branch || '—' }}</div>
          </div>
          <div class="card">
            <div class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Updates to pull</div>
            <div class="font-mono text-sm text-white">{{ project.pending_count ?? 0 }}</div>
          </div>
          <div class="card">
            <div class="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Address</div>
            <div class="font-mono text-sm text-white break-all">{{ project.url }}</div>
          </div>
        </div>
        <!-- Recent commits -->
        <div class="card mb-4 min-w-0" v-if="(project.commits as unknown[])?.length">
          <h3 class="text-sm font-semibold mb-3 text-slate-300">Recent Commits</h3>
          <div class="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
            <table class="table-base min-w-[480px]">
              <thead><tr><th>Hash</th><th>Message</th><th>Author</th><th class="text-right">Date</th></tr></thead>
              <tbody>
                <tr v-for="c in project.commits as Commit[]" :key="c.hash">
                  <td><code class="text-slate-400 text-xs">{{ c.hash }}</code></td>
                  <td class="text-slate-300 max-w-[120px] sm:max-w-none truncate" :title="c.subject">{{ c.subject }}</td>
                  <td class="text-slate-500 truncate max-w-[80px] sm:max-w-none" :title="c.author">{{ c.author }}</td>
                  <td class="text-slate-500 text-xs whitespace-nowrap text-right">{{ c.date }}</td>
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
              <thead><tr><th>Time</th><th>User</th><th class="text-center">Action</th><th>Detail</th><th class="text-center">Outcome</th></tr></thead>
              <tbody>
                <tr v-for="a in auditLog as AuditEntry[]" :key="a.id">
                  <td class="text-slate-400 text-xs whitespace-nowrap">{{ new Date(a.triggered_at).toLocaleString() }}</td>
                  <td class="text-slate-400 text-xs">{{ a.user || '—' }}</td>
                  <td class="text-center">
                    <span class="px-2 py-0.5 rounded text-xs font-mono"
                      :class="{
                        'bg-blue-500/15 text-blue-300': a.action === 'deploy',
                        'bg-amber-500/15 text-amber-300': a.action === 'backup' || a.action === 'backup_schedule',
                        'bg-purple-500/15 text-purple-300': a.action === 'restore',
                        'bg-red-500/15 text-red-300': a.action === 'db_drop' || a.action === 'container_stop' || a.action === 'project_delete',
                        'bg-cyan-500/15 text-cyan-300': a.action === 'branch_switch' || a.action === 'git_pull' || a.action === 'submodule_update',
                        'bg-green-500/15 text-green-300': a.action === 'container_restart',
                        'bg-slate-500/15 text-slate-300': !['deploy','backup','backup_schedule','restore','db_drop','branch_switch','git_pull','submodule_update','container_stop','container_restart','project_delete'].includes(a.action),
                      }">{{ a.action }}</span>
                  </td>
                  <td class="text-slate-400 text-xs max-w-[160px] truncate" :title="a.detail">{{ a.detail || '—' }}</td>
                  <td class="text-center">
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
              <thead><tr><th>Time</th><th>Type</th><th>From</th><th>To</th><th class="text-center">Outcome</th><th class="text-right">Duration</th></tr></thead>
              <tbody>
                <tr v-for="h in history as DeployRecord[]" :key="h.id">
                  <td class="text-slate-400 text-xs whitespace-nowrap">{{ new Date(h.triggered_at).toLocaleString() }}</td>
                  <td>{{ h.trigger_type }}</td>
                  <td class="max-w-[70px] sm:max-w-[90px]"><code class="text-slate-500 text-xs truncate inline-block max-w-full align-bottom" :title="h.prev_commit || '—'">{{ h.prev_commit || '—' }}</code></td>
                  <td class="max-w-[70px] sm:max-w-[90px]"><code class="text-slate-500 text-xs truncate inline-block max-w-full align-bottom" :title="h.new_commit || '—'">{{ h.new_commit || '—' }}</code></td>
                  <td class="text-center">
                    <span :class="h.outcome === 'success' ? 'text-green-400' : 'text-red-400'">
                      {{ h.outcome === 'success' ? '✓' : '✗' }} {{ h.outcome }}
                    </span>
                  </td>
                  <td class="text-slate-500 text-xs text-right">{{ h.duration_seconds != null ? h.duration_seconds + 's' : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <LogViewer v-show="activeTab === 'logs'" :container="project.container as string" :container-id="(project.container_id as string) || ''" :logs-url="config.logsUrl" :active="activeTab === 'logs'" />
      <DatabaseTab v-show="activeTab === 'database'" :project-name="name" :active="activeTab === 'database'" />
      <ModulesTab v-show="activeTab === 'modules'" :project-name="name" :active="activeTab === 'modules'" />
      <BranchTab v-show="activeTab === 'branches'" :project-name="name" :uses-hr-base="!!project.uses_hr_base" :container="(project.container as string)" :active="activeTab === 'branches'" :can-switch="auth.canSwitchBranch" @branch-changed="onBranchChanged" @container-restarted="refreshStatus" />
      <SettingsTab v-show="activeTab === 'settings'" :project-name="name" :active="activeTab === 'settings'" />
      <NotebookTab v-show="activeTab === 'notebook'" :project-name="name" :active="activeTab === 'notebook'" />
    </template>
    </div>
  </SidebarLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useNotificationsStore } from '@/stores/notifications'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api'
import SidebarLayout from '@/layouts/SidebarLayout.vue'
import Breadcrumb from '@/components/Breadcrumb.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import CpuGauge from '@/components/CpuGauge.vue'
import MemoryBar from '@/components/MemoryBar.vue'
import LogViewer from '@/components/LogViewer.vue'
import DeployPanel from '@/components/DeployPanel.vue'
import OpenAsModal from '@/components/OpenAsModal.vue'
import DatabaseTab from '@/components/DatabaseTab.vue'
import ModulesTab from '@/components/ModulesTab.vue'
import BranchTab from '@/components/BranchTab.vue'
import SettingsTab from '@/components/SettingsTab.vue'
import NotebookTab from '@/components/NotebookTab.vue'

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
  user: string
}

const route    = useRoute()
const router   = useRouter()
const notify   = useNotificationsStore()
const config   = useConfigStore()
const projects = useProjectsStore()
const auth     = useAuthStore()

const name    = route.params.name as string
const project = ref<Record<string, unknown> | null>(null)
const history = ref<unknown[]>([])
const auditLog = ref<unknown[]>([])
const activeTab   = ref((route.query.tab as string) || 'overview')
const deployPanel = ref<InstanceType<typeof DeployPanel> | null>(null)

const showDeleteModal   = ref(false)
const showOpenAs        = ref(false)
const deleteConfirmText = ref('')
const deleting          = ref(false)

function closeDeleteModal() {
  showDeleteModal.value   = false
  deleteConfirmText.value = ''
}

async function confirmDelete() {
  if (deleteConfirmText.value !== name || deleting.value) return
  deleting.value = true
  const res = await api(`/api/project/${name}/delete`, { method: 'DELETE' })
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

const allTabs = [
  { id: 'overview',      label: 'Overview',      adminOnly: false },
  { id: 'logs',          label: 'Logs',          adminOnly: false },
  { id: 'database',      label: 'Database',      adminOnly: false },
  { id: 'modules',       label: 'Modules',       adminOnly: false },
  { id: 'branches',      label: 'Branches',      adminOnly: false },
  { id: 'settings',      label: 'Settings',      adminOnly: false },
  { id: 'notebook',      label: 'Notebook',      adminOnly: false },
  { id: 'manage',        label: 'Manage',        adminOnly: true  },
]
const tabs = computed(() => allTabs.filter(t => !t.adminOnly || auth.isAdmin))

onMounted(async () => {
  const [projRes, histRes, auditRes] = await Promise.all([
    api(`/api/project/${name}`),
    api(`/api/project/${name}/history`),
    api(`/api/project/${name}/audit`),
  ])
  project.value = await projRes.json()
  history.value = await histRes.json()
  auditLog.value = await auditRes.json()
})

async function refreshStatus() {
  const res = await api(`/api/project/${name}`)
  if (res.ok) {
    const fresh = await res.json()
    if (project.value) {
      project.value.status  = fresh.status
      project.value.running = fresh.running
    }
  }
}

async function onBranchChanged(branch: string) {
  // Optimistically update the branch card immediately
  if (project.value) project.value.branch = branch

  // Then refresh commits + audit log from the server (they change after branch switch)
  const [projRes, auditRes] = await Promise.all([
    api(`/api/project/${name}`),
    api(`/api/project/${name}/audit`),
  ])
  if (projRes.ok) {
    const fresh = await projRes.json()
    if (project.value) {
      project.value.branch  = fresh.branch  ?? branch
      project.value.commits = fresh.commits ?? []
      project.value.status  = fresh.status
      project.value.running = fresh.running
    }
  }
  if (auditRes.ok) auditLog.value = await auditRes.json()
}

async function restart() {
  const res = await api(`/api/restart/${project.value?.container}`, { method: 'POST' })
  const d = await res.json()
  notify.add(d.ok ? 'success' : 'error', d.ok ? 'Restarted' : d.error)
  if (d.ok) refreshStatus()
}

async function stop() {
  if (!confirm('Stop this container?')) return
  const res = await api(`/api/stop/${project.value?.container}`, { method: 'POST' })
  const d = await res.json()
  notify.add(d.ok ? 'success' : 'error', d.ok ? 'Stopped' : d.error)
  if (d.ok) refreshStatus()
}

async function start() {
  const res = await api(`/api/start/${project.value?.container}`, { method: 'POST' })
  const d = await res.json()
  notify.add(d.ok ? 'success' : 'error', d.ok ? 'Started' : d.error)
  if (d.ok) refreshStatus()
}

async function deploy() {
  deployPanel.value?.trigger()
}
</script>
