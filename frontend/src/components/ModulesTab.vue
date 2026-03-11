<template>
  <div class="card">
    <div class="flex items-center gap-3 mb-4">
      <select v-model="selectedDb" class="input" @change="loadModules">
        <option value="">Select database…</option>
        <option v-for="db in dbs" :key="db" :value="db">{{ db }}</option>
      </select>
      <input v-model="filter" class="input flex-1" placeholder="Filter modules…" />
      <button v-if="pendingCount > 0" class="btn btn-primary btn-sm" @click="updatePending">
        ⬆ Update {{ pendingCount }} pending
      </button>
    </div>

    <div v-if="loading" class="text-sm text-slate-500">Loading…</div>
    <div v-else-if="error" class="text-sm text-red-400">{{ error }}</div>

    <div v-for="group in filteredGroups" :key="group.label" class="mb-4">
      <div class="flex items-center gap-2 py-2 border-b border-[#2d3148] cursor-pointer"
        @click="toggleGroup(group.label)">
        <span class="text-slate-500 text-xs">{{ collapsed.has(group.label) ? '▸' : '▾' }}</span>
        <span class="text-sm font-medium text-slate-300">{{ group.label }}</span>
        <code class="text-xs text-slate-600">{{ group.path }}</code>
        <span class="ml-auto text-xs text-slate-500">{{ group.modules.length }} modules</span>
        <span v-if="pendingInGroup(group) > 0" class="text-xs text-amber-400">↯ {{ pendingInGroup(group) }} pending</span>
      </div>
      <div v-if="!collapsed.has(group.label)">
        <table class="table-base">
          <thead><tr><th>Module</th><th>State</th><th>Version</th><th>Action</th></tr></thead>
          <tbody>
            <tr v-for="mod in group.modules" :key="mod.name"
              v-show="!filter || mod.name.toLowerCase().includes(filter.toLowerCase())">
              <td class="font-mono text-xs">{{ mod.name }}</td>
              <td>
                <span class="text-xs px-1.5 py-0.5 rounded"
                  :class="{
                    'bg-green-900/40 text-green-400': mod.state === 'installed',
                    'bg-amber-900/40 text-amber-400': mod.state === 'to upgrade',
                    'bg-red-900/40 text-red-400': mod.state === 'to remove',
                    'bg-slate-800 text-slate-500': mod.state === 'uninstalled',
                  }">{{ mod.state }}</span>
              </td>
              <td class="text-slate-500 text-xs">{{ mod.version || '—' }}</td>
              <td>
                <button v-if="['installed', 'to upgrade'].includes(mod.state)"
                  class="btn btn-ghost btn-sm"
                  @click="updateModule(mod.name)">⬆ Update</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Module update output -->
    <div v-if="updateOutput" class="mt-4 card border-[#6366f1]/30">
      <div class="text-xs font-medium text-slate-400 mb-2">Updating: {{ updatingModule }}</div>
      <pre class="log-output h-48 whitespace-pre-wrap text-xs">{{ updateOutput }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = defineProps<{ projectName: string; active: boolean }>()

interface Module { name: string; state: string; version: string; author: string }
interface Group { label: string; kind: string; path: string; modules: Module[] }

const dbs = ref<string[]>([])
const selectedDb = ref('')
const groups = ref<Group[]>([])
const filter = ref('')
const loading = ref(false)
const error = ref('')
const collapsed = ref<Set<string>>(new Set(['Odoo Core']))
const updateOutput = ref('')
const updatingModule = ref('')

const pendingCount = computed(() =>
  groups.value.flatMap(g => g.modules).filter(m => m.state === 'to upgrade').length
)

const filteredGroups = computed(() => {
  if (!filter.value) return groups.value
  const f = filter.value.toLowerCase()
  return groups.value.map(g => ({
    ...g,
    modules: g.modules.filter(m => m.name.toLowerCase().includes(f))
  })).filter(g => g.modules.length > 0)
})

function pendingInGroup(g: Group) {
  return g.modules.filter(m => m.state === 'to upgrade').length
}

watch(() => props.active, async (v) => {
  if (v && !dbs.value.length) {
    const res = await fetch(`/api/db/${props.projectName}/list`)
    const data = await res.json()
    dbs.value = (data.databases || []).map((d: { name: string }) => d.name)
  }
})

async function loadModules() {
  if (!selectedDb.value) return
  loading.value = true; error.value = ''
  const res = await fetch(`/api/modules/${props.projectName}/${selectedDb.value}`)
  const data = await res.json()
  loading.value = false
  if (data.error) { error.value = data.error; return }
  groups.value = data.groups || []
}

function toggleGroup(label: string) {
  if (collapsed.value.has(label)) collapsed.value.delete(label)
  else collapsed.value.add(label)
}

async function updateModule(modname: string) {
  updatingModule.value = modname
  updateOutput.value = ''
  const res = await fetch(`/api/modules/${props.projectName}/${selectedDb.value}/update/${modname}`, { method: 'POST' })
  const data = await res.json()
  if (!data.ok) { updateOutput.value = data.error; return }
  const source = new EventSource(data.stream_url)
  source.onmessage = (evt) => {
    const d = JSON.parse(evt.data)
    updateOutput.value += d.line + '\n'
    if (d.done) source.close()
  }
  source.onerror = () => source.close()
}

async function updatePending() {
  const pending = groups.value.flatMap(g => g.modules).filter(m => m.state === 'to upgrade')
  for (const mod of pending) {
    await updateModule(mod.name)
  }
}
</script>
