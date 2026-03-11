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
    <div v-if="switchOutput" class="card mb-4 border-accent/30">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm font-semibold text-slate-300">Git Output</div>
        <button @click="switchOutput = ''" class="btn btn-ghost btn-sm">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
          Clear
        </button>
      </div>
      <pre class="log-output h-48 whitespace-pre-wrap text-xs">{{ switchOutput }}</pre>
    </div>

    <div class="card mb-4">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-slate-300">Branches</h3>
        <div class="flex gap-2">
          <button class="btn btn-ghost btn-sm" @click="gitPull">↓ Pull</button>
          <button class="btn btn-ghost btn-sm" @click="load">↺ Refresh</button>
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
              class="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover/50 transition-colors">
              <div class="flex items-center gap-2">
                <span v-if="b === data.current" class="w-1.5 h-1.5 rounded-full bg-green-400" />
                <span v-else class="w-1.5 h-1.5 rounded-full bg-slate-600" />
                <span class="font-mono text-sm" :class="b === data.current ? 'text-white' : 'text-slate-400'">{{ b }}</span>
                <span v-if="b === data.current" class="text-xs text-green-400">(current)</span>
              </div>
              <button v-if="b !== data.current" class="btn btn-ghost btn-sm" @click="showConfirmModal = true; pendingBranch = b">Switch</button>
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
              class="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover/50 transition-colors">
              <span class="font-mono text-sm text-slate-500">{{ b }}</span>
              <button class="btn btn-ghost btn-sm" @click="showConfirmModal = true; pendingBranch = b.replace('origin/', '')">Checkout</button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Submodules -->
    <div class="card mb-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-slate-300">Submodules</h3>
        <button class="btn btn-ghost btn-sm" @click="updateSubmodules">⬆ Update All</button>
      </div>
      <div v-if="!submodules.length" class="text-sm text-slate-500">No submodules.</div>
      <table v-else class="table-base">
        <thead><tr><th>Path</th><th>Commit</th><th>Status</th></tr></thead>
        <tbody>
          <tr v-for="s in submodules" :key="s.path">
            <td class="font-mono text-xs">{{ s.path }}</td>
            <td class="font-mono text-xs text-slate-500">{{ s.commit }}</td>
            <td>
              <span class="text-xs px-1.5 py-0.5 rounded"
                :class="{
                  'bg-green-900/40 text-green-400': s.status === 'clean',
                  'bg-amber-900/40 text-amber-400': s.status === 'modified',
                  'bg-red-900/40 text-red-400': s.status === 'behind',
                }">{{ s.status }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

const props = defineProps<{ projectName: string; folder: string | null; active: boolean; container: string }>()
const notify = useNotificationsStore()

interface BranchData { local: string[]; remote: string[]; current: string | null; error?: string }
interface Submodule { path: string; commit: string; status: string }

const data = ref<BranchData>({ local: [], remote: [], current: null })
const submodules = ref<Submodule[]>([])
const loading = ref(false)
const switchOutput = ref('')
const searchQuery = ref('')
const showConfirmModal = ref(false)
const showRestartModal = ref(false)
const pendingBranch = ref('')

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

watch(() => props.active, (v) => { if (v) load() }, { immediate: true })

async function load() {
  loading.value = true
  const [branchRes, subRes] = await Promise.all([
    fetch(`/api/git/${props.projectName}/branches`),
    fetch(`/api/git/${props.projectName}/submodules`),
  ])
  data.value = await branchRes.json()
  const subData = await subRes.json()
  submodules.value = subData.submodules || []
  loading.value = false
}

async function confirmSwitch() {
  showConfirmModal.value = false
  await switchBranch(pendingBranch.value)
}

async function switchBranch(branch: string) {
  switchOutput.value = ''
  const res = await fetch(`/api/git/${props.projectName}/switch`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ branch }),
  })
  const d = await res.json()
  if (!d.ok) { notify.add('error', d.error); return }

  let switchComplete = false
  const source = new EventSource(d.stream_url)
  source.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)
    switchOutput.value += msg.line + '\n'
    if (msg.done) {
      source.close()
      load()
      switchComplete = true
      // Show restart prompt after successful switch
      showRestartModal.value = true
    }
  }
  source.onerror = () => source.close()
}

async function restartContainer() {
  showRestartModal.value = false
  try {
    const res = await fetch(`/api/restart/${props.container}`, { method: 'POST' })
    const data = await res.json()
    notify.add(data.ok ? 'success' : 'error', data.ok ? 'Container restarting...' : data.error)
  } catch (err) {
    notify.add('error', 'Failed to restart container')
  }
}

async function updateSubmodules() {
  switchOutput.value = ''
  const res = await fetch(`/api/git/${props.projectName}/submodule-update`, { method: 'POST' })
  const d = await res.json()
  if (!d.ok) { notify.add('error', d.error); return }

  const source = new EventSource(d.stream_url)
  source.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)
    switchOutput.value += msg.line + '\n'
    if (msg.done) { source.close(); load() }
  }
  source.onerror = () => source.close()
}

async function gitPull() {
  switchOutput.value = ''
  const res = await fetch(`/api/git/${props.projectName}/pull`, { method: 'POST' })
  const d = await res.json()
  if (!d.ok) { notify.add('error', d.error); return }

  const source = new EventSource(d.stream_url)
  source.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)
    switchOutput.value += msg.line + '\n'
    if (msg.done) { source.close(); load() }
  }
  source.onerror = () => source.close()
}
</script>
