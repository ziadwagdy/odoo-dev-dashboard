<template>
  <div>
    <!-- Confirmation Modal -->
    <div v-if="showConfirmModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" @click.self="showConfirmModal = false">
      <div class="card max-w-md w-full border-accent/30">
        <div class="mb-4">
          <h3 class="text-lg font-bold text-white mb-2">Switch Branch?</h3>
          <p class="text-sm text-slate-400">
            Are you sure you want to switch to branch <span class="font-mono text-accent">{{ pendingBranch }}</span>?
          </p>
        </div>
        <div class="flex gap-3 justify-end">
          <button @click="showConfirmModal = false" class="btn btn-ghost">Cancel</button>
          <button @click="confirmSwitch" class="btn btn-primary">Switch Branch</button>
        </div>
      </div>
    </div>

    <!-- Restart Container Modal -->
    <div v-if="showRestartModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" @click.self="showRestartModal = false">
      <div class="card max-w-md w-full border-accent/30">
        <div class="mb-4">
          <h3 class="text-lg font-bold text-white mb-2">Restart Container?</h3>
          <p class="text-sm text-slate-400 mb-3">
            Branch switched successfully. Would you like to restart the container to apply the changes?
          </p>
          <div class="bg-warning/10 border border-warning/30 rounded-lg p-3">
            <p class="text-xs text-warning flex items-start gap-2">
              <svg class="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
              </svg>
              <span>This will restart the Odoo container and may cause brief downtime.</span>
            </p>
          </div>
        </div>
        <div class="flex gap-3 justify-end">
          <button @click="showRestartModal = false" class="btn btn-ghost">Skip</button>
          <button @click="restartContainer" class="btn btn-warning">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            Restart Now
          </button>
        </div>
      </div>
    </div>

    <!-- Branch switch / pull output -->
    <div v-if="switchLines.length" class="card mb-4 border-accent/30">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm font-semibold text-slate-300">Git Output</div>
        <button @click="switchLines = []" class="btn btn-ghost btn-sm">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
          Clear
        </button>
      </div>
      <div class="log-output min-h-[8rem] max-h-[40vh] md:max-h-[12rem]">
        <div v-for="(line, i) in switchLines" :key="i" :class="line.cls" v-html="line.html" />
      </div>
    </div>

    <div :class="isHrBase ? 'lg:grid lg:grid-cols-2 lg:gap-4 lg:items-start' : ''">
    <div class="card mb-4">
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mb-4">
        <h3 class="text-sm font-semibold text-slate-300">Branches</h3>
        <div class="flex gap-2">
          <button class="btn btn-ghost btn-sm flex-1 sm:flex-none inline-flex items-center gap-1.5" @click="gitPull">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
            Pull
          </button>
          <button class="btn btn-ghost btn-sm flex-1 sm:flex-none inline-flex items-center gap-1.5" @click="load">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
            Refresh
          </button>
        </div>
      </div>
      
      <!-- Search Input -->
      <div class="mb-4">
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search branches..."
            class="input pl-10 w-full"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      </div>

      <div v-if="loading" class="text-sm text-slate-500">Loading…</div>
      <div v-else-if="data.error" class="text-sm text-red-400">{{ data.error }}</div>
      <template v-else>
        <div class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <div class="text-xs text-slate-500 uppercase tracking-wide">Local Branches</div>
            <span class="text-xs text-slate-600">{{ filteredLocal.length }} / {{ data.local.length }}</span>
          </div>
          <div v-if="filteredLocal.length === 0" class="text-sm text-slate-500 py-4 text-center">
            No matching branches
          </div>
          <div v-else class="space-y-1">
            <div v-for="b in filteredLocal" :key="b"
              class="flex items-center justify-between gap-2 p-2 rounded-lg hover:bg-surface-hover/50 transition-colors min-w-0">
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <span v-if="b === data.current" class="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0" />
                <span v-else class="w-1.5 h-1.5 rounded-full bg-slate-600 shrink-0" />
                <span class="font-mono text-sm truncate" :class="b === data.current ? 'text-white' : 'text-slate-400'" :title="b">{{ b }}</span>
                <span v-if="b === data.current" class="text-xs text-green-400 shrink-0">(current)</span>
              </div>
              <button v-if="b !== data.current && props.canSwitch !== false" class="btn btn-ghost btn-sm shrink-0" @click="showConfirmModal = true; pendingBranch = b">Switch</button>
            </div>
          </div>
        </div>
        <div>
          <div class="flex items-center justify-between mb-2">
            <div class="text-xs text-slate-500 uppercase tracking-wide">Remote Branches</div>
            <span class="text-xs text-slate-600">{{ filteredRemote.length }} / {{ data.remote.length }}</span>
          </div>
          <div v-if="filteredRemote.length === 0" class="text-sm text-slate-500 py-4 text-center">
            No matching branches
          </div>
          <div v-else class="space-y-1">
            <div v-for="b in filteredRemote" :key="b"
              class="flex items-center justify-between gap-2 p-2 rounded-lg hover:bg-surface-hover/50 transition-colors min-w-0">
              <span class="font-mono text-sm text-slate-500 truncate min-w-0" :title="b">{{ b }}</span>
              <button v-if="props.canSwitch !== false" class="btn btn-ghost btn-sm shrink-0" @click="showConfirmModal = true; pendingBranch = b.replace('origin/', '')">Checkout</button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Submodules -->
    <div class="card mb-4">
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mb-3">
        <h3 class="text-sm font-semibold text-slate-300">Submodules</h3>
        <button class="btn btn-ghost btn-sm w-full sm:w-auto inline-flex items-center gap-1.5 justify-center" title="Pull the latest commit of every submodule" @click="updateSubmodules">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          Pull
        </button>
      </div>
      <div v-if="!submodules.length" class="text-sm text-slate-500">No submodules.</div>
      <div v-else class="space-y-2">
        <div v-for="s in submodules" :key="s.path" class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg bg-surface-hover/30">
          <div class="flex flex-col gap-1 min-w-0 flex-1">
            <span class="font-mono text-xs text-slate-300 truncate">{{ s.path }}</span>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono text-[10px] text-slate-500">{{ s.commit }}</span>
              <span v-if="s.branch" class="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent font-mono">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path></svg>
                {{ s.branch }}
              </span>
              <span v-else class="text-[10px] text-slate-600 italic">detached HEAD</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded"
                :class="{
                  'bg-green-900/40 text-green-400': s.status === 'clean',
                  'bg-amber-900/40 text-amber-400': s.status === 'modified',
                  'bg-red-900/40 text-red-400': s.status === 'behind',
                }">{{ s.status }}</span>
            </div>
          </div>
          <button v-if="props.canSwitch !== false" class="btn btn-ghost btn-sm shrink-0 self-start sm:self-center" @click="openSubmoduleBranchModal(s.path)">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
            Switch Branch
          </button>
        </div>
      </div>
    </div>
    </div>

    <!-- Submodule branch switch modal -->
    <div v-if="showSubmoduleBranchModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" @click.self="closeSubmoduleModal">
      <div class="card max-w-lg w-full border-accent/30">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-bold text-white">Switch Submodule Branch</h3>
          <button @click="closeSubmoduleModal" class="text-slate-500 hover:text-white">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
        <p class="text-xs text-slate-500 font-mono mb-4">{{ pendingSubmodulePath }}</p>
        <div v-if="submoduleBranchLoading" class="text-sm text-slate-500 py-4 text-center">Loading branches…</div>
        <div v-else-if="submoduleBranchData.error" class="text-sm text-red-400">{{ submoduleBranchData.error }}</div>
        <template v-else>
          <div class="mb-3">
            <div class="relative">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
              <input v-model="submoduleBranchSearch" type="text" placeholder="Search branches…" class="input pl-10 w-full" />
            </div>
          </div>
          <div class="max-h-72 overflow-y-auto space-y-1 mb-4">
            <div v-for="b in filteredSubmoduleLocal" :key="'l:' + b"
              class="flex items-center justify-between gap-2 p-2 rounded-lg hover:bg-surface-hover/50 transition-colors">
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <span :class="b === submoduleBranchData.current ? 'bg-green-400' : 'bg-slate-600'" class="w-1.5 h-1.5 rounded-full shrink-0" />
                <span class="font-mono text-sm truncate" :class="b === submoduleBranchData.current ? 'text-white' : 'text-slate-400'">{{ b }}</span>
                <span v-if="b === submoduleBranchData.current" class="text-xs text-green-400 shrink-0">(current)</span>
              </div>
              <button v-if="b !== submoduleBranchData.current" class="btn btn-ghost btn-sm shrink-0" @click="confirmSubmoduleSwitch(b)">Switch</button>
            </div>
            <div v-if="filteredSubmoduleRemote.length" class="pt-2 border-t border-white/5">
              <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 px-2">Remote</div>
              <div v-for="b in filteredSubmoduleRemote" :key="'r:' + b"
                class="flex items-center justify-between gap-2 p-2 rounded-lg hover:bg-surface-hover/50 transition-colors">
                <span class="font-mono text-sm text-slate-500 truncate min-w-0">{{ b }}</span>
                <button class="btn btn-ghost btn-sm shrink-0" @click="confirmSubmoduleSwitch(b.replace('origin/', ''))">Checkout</button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Submodule switch confirm modal -->
    <div v-if="showSubmoduleConfirmModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" @click.self="showSubmoduleConfirmModal = false">
      <div class="card max-w-md w-full border-accent/30">
        <h3 class="text-lg font-bold text-white mb-2">Switch Submodule Branch?</h3>
        <p class="text-sm text-slate-400 mb-1">Submodule: <span class="font-mono text-xs text-slate-300">{{ pendingSubmodulePath }}</span></p>
        <p class="text-sm text-slate-400">Branch: <span class="font-mono text-accent">{{ pendingSubmoduleBranch }}</span></p>
        <div class="flex gap-3 justify-end mt-4">
          <button @click="showSubmoduleConfirmModal = false" class="btn btn-ghost">Cancel</button>
          <button @click="doSubmoduleSwitch" class="btn btn-primary">Switch Branch</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { api } from '@/api'
import { ref, computed, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'
import { parseLine, type LogLine } from '@/utils/ansi'

const props = defineProps<{ projectName: string; usesHrBase?: boolean; active: boolean; container: string; canSwitch?: boolean }>()
const emit = defineEmits<{
  'branch-changed': [branch: string]
  'container-restarted': []
}>()
const notify = useNotificationsStore()

interface BranchData { local: string[]; remote: string[]; current: string | null; error?: string }
interface Submodule { path: string; commit: string; status: string; branch: string | null }

const data = ref<BranchData>({ local: [], remote: [], current: null })
const submodules = ref<Submodule[]>([])
const loading = ref(false)
const loaded = ref(false)
const switchLines = ref<LogLine[]>([])
const searchQuery = ref('')
const showConfirmModal = ref(false)
const showRestartModal = ref(false)
const pendingBranch = ref('')

const showSubmoduleBranchModal = ref(false)
const showSubmoduleConfirmModal = ref(false)
const pendingSubmodulePath = ref('')
const pendingSubmoduleBranch = ref('')
const submoduleBranchLoading = ref(false)
const submoduleBranchData = ref<BranchData>({ local: [], remote: [], current: null })
const submoduleBranchSearch = ref('')

const isHrBase = computed(() =>
  props.usesHrBase ||
  submodules.value.some(s => /hr[-_]base/i.test(s.path))
)

const filteredLocal = computed(() => {
  if (!searchQuery.value) return data.value.local
  const query = searchQuery.value.toLowerCase()
  return data.value.local.filter(b => b.toLowerCase().includes(query))
})

const filteredRemote = computed(() => {
  if (!searchQuery.value) return data.value.remote
  const query = searchQuery.value.toLowerCase()
  return data.value.remote.filter(b => b.toLowerCase().includes(query))
})

const filteredSubmoduleLocal = computed(() => {
  if (!submoduleBranchSearch.value) return submoduleBranchData.value.local
  const q = submoduleBranchSearch.value.toLowerCase()
  return submoduleBranchData.value.local.filter(b => b.toLowerCase().includes(q))
})

const filteredSubmoduleRemote = computed(() => {
  if (!submoduleBranchSearch.value) return submoduleBranchData.value.remote
  const q = submoduleBranchSearch.value.toLowerCase()
  return submoduleBranchData.value.remote.filter(b => b.toLowerCase().includes(q))
})

watch(() => props.active, (v) => { if (v && !loaded.value) load() }, { immediate: true })

async function load() {
  loading.value = true
  const [branchRes, subRes] = await Promise.all([
    api(`/api/git/${props.projectName}/branches`),
    api(`/api/git/${props.projectName}/submodules`),
  ])
  data.value = await branchRes.json()
  const subData = await subRes.json()
  submodules.value = subData.submodules || []
  loading.value = false
  loaded.value = true
}

async function confirmSwitch() {
  showConfirmModal.value = false
  await switchBranch(pendingBranch.value)
}

async function switchBranch(branch: string) {
  switchLines.value = []
  const res = await api(`/api/git/${props.projectName}/switch`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ branch }),
  })
  const d = await res.json()
  if (!d.ok) { notify.add('error', d.error); return }

  let switchComplete = false
  const source = new EventSource(d.stream_url)
  source.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)
    switchLines.value.push(parseLine(msg.line ?? ''))
    if (msg.done) {
      source.close()
      loaded.value = false  // invalidate so next activate or manual refresh re-fetches
      load()
      switchComplete = true
      emit('branch-changed', branch)
      showRestartModal.value = true
    }
  }
  source.onerror = () => source.close()
}

async function restartContainer() {
  showRestartModal.value = false
  try {
    const res = await api(`/api/restart/${props.container}`, { method: 'POST' })
    const data = await res.json()
    if (data.ok) emit('container-restarted')
    notify.add(data.ok ? 'success' : 'error', data.ok ? 'Container restarting...' : data.error)
  } catch (err) {
    notify.add('error', 'Failed to restart container')
  }
}

async function updateSubmodules() {
  switchLines.value = []
  const res = await api(`/api/git/${props.projectName}/submodule-update`, { method: 'POST' })
  const d = await res.json()
  if (!d.ok) { notify.add('error', d.error); return }

  const source = new EventSource(d.stream_url)
  source.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)
    switchLines.value.push(parseLine(msg.line ?? ''))
    if (msg.done) { source.close(); loaded.value = false; load() }
  }
  source.onerror = () => source.close()
}

async function openSubmoduleBranchModal(subPath: string) {
  pendingSubmodulePath.value = subPath
  submoduleBranchSearch.value = ''
  submoduleBranchData.value = { local: [], remote: [], current: null }
  showSubmoduleBranchModal.value = true
  submoduleBranchLoading.value = true
  const res = await api(`/api/git/${props.projectName}/submodule-branches?path=${encodeURIComponent(subPath)}`)
  submoduleBranchData.value = await res.json()
  submoduleBranchLoading.value = false
}

function closeSubmoduleModal() {
  showSubmoduleBranchModal.value = false
}

function confirmSubmoduleSwitch(branch: string) {
  pendingSubmoduleBranch.value = branch
  showSubmoduleBranchModal.value = false
  showSubmoduleConfirmModal.value = true
}

async function doSubmoduleSwitch() {
  showSubmoduleConfirmModal.value = false
  switchLines.value = []
  const res = await api(`/api/git/${props.projectName}/submodule-switch`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sub_path: pendingSubmodulePath.value, branch: pendingSubmoduleBranch.value }),
  })
  const d = await res.json()
  if (!d.ok) { notify.add('error', d.error); return }

  const source = new EventSource(d.stream_url)
  source.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)
    switchLines.value.push(parseLine(msg.line ?? ''))
    if (msg.done) {
      source.close()
      loaded.value = false
      load()
      emit('branch-changed', pendingSubmoduleBranch.value)
      showRestartModal.value = true
    }
  }
  source.onerror = () => source.close()
}

async function gitPull() {
  switchLines.value = []
  const res = await api(`/api/git/${props.projectName}/pull`, { method: 'POST' })
  const d = await res.json()
  if (!d.ok) { notify.add('error', d.error); return }

  const source = new EventSource(d.stream_url)
  source.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)
    switchLines.value.push(parseLine(msg.line ?? ''))
    // Pull doesn't change current branch — no need to re-fetch branch list
    if (msg.done) { source.close(); notify.add('success', 'Pull complete') }
  }
  source.onerror = () => source.close()
}
</script>
