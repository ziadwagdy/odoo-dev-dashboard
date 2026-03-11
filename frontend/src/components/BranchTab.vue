<template>
  <div>
    <div class="card mb-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-slate-300">Branches</h3>
        <div class="flex gap-2">
          <button class="btn btn-ghost btn-sm" @click="gitPull">↓ Pull</button>
          <button class="btn btn-ghost btn-sm" @click="load">↺ Refresh</button>
        </div>
      </div>
      <div v-if="loading" class="text-sm text-slate-500">Loading…</div>
      <div v-else-if="data.error" class="text-sm text-red-400">{{ data.error }}</div>
      <template v-else>
        <div class="mb-4">
          <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">Local Branches</div>
          <div class="space-y-1">
            <div v-for="b in data.local" :key="b"
              class="flex items-center justify-between p-2 rounded-lg hover:bg-[#2d3148]/30">
              <div class="flex items-center gap-2">
                <span v-if="b === data.current" class="w-1.5 h-1.5 rounded-full bg-green-400" />
                <span v-else class="w-1.5 h-1.5 rounded-full bg-slate-600" />
                <span class="font-mono text-sm" :class="b === data.current ? 'text-white' : 'text-slate-400'">{{ b }}</span>
                <span v-if="b === data.current" class="text-xs text-green-400">(current)</span>
              </div>
              <button v-if="b !== data.current" class="btn btn-ghost btn-sm" @click="switchBranch(b)">Switch</button>
            </div>
          </div>
        </div>
        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">Remote Branches</div>
          <div class="space-y-1">
            <div v-for="b in data.remote" :key="b"
              class="flex items-center justify-between p-2 rounded-lg hover:bg-[#2d3148]/30">
              <span class="font-mono text-sm text-slate-500">{{ b }}</span>
              <button class="btn btn-ghost btn-sm" @click="switchBranch(b.replace('origin/', ''))">Checkout</button>
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

    <!-- Branch switch / pull output -->
    <div v-if="switchOutput" class="card border-[#6366f1]/30">
      <div class="text-xs font-medium text-slate-400 mb-2">Git output</div>
      <pre class="log-output h-32 whitespace-pre-wrap text-xs">{{ switchOutput }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

const props = defineProps<{ projectName: string; folder: string | null; active: boolean }>()
const notify = useNotificationsStore()

interface BranchData { local: string[]; remote: string[]; current: string | null; error?: string }
interface Submodule { path: string; commit: string; status: string }

const data = ref<BranchData>({ local: [], remote: [], current: null })
const submodules = ref<Submodule[]>([])
const loading = ref(false)
const switchOutput = ref('')

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

async function switchBranch(branch: string) {
  switchOutput.value = ''
  const res = await fetch(`/api/git/${props.projectName}/switch`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ branch }),
  })
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
