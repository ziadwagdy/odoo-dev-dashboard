<template>
  <div class="space-y-4">

    <!-- Toolbar -->
    <div class="card flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
      <select v-model="selectedDb" class="input flex-1 sm:flex-none sm:w-52" @change="loadModules">
        <option value="">Select database…</option>
        <option v-for="db in dbs" :key="db" :value="db">{{ db }}</option>
      </select>
      <input v-model="filter" class="input flex-1" placeholder="Filter modules…" />
      <div class="flex gap-2 shrink-0">
        <button
          v-if="selectedModules.size > 0"
          class="btn btn-primary btn-sm inline-flex items-center gap-1.5"
          :disabled="updating"
          @click="updateSelected">
          <svg v-if="updating" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
          </svg>
          <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          {{ updating ? 'Updating…' : `Update ${selectedModules.size} selected` }}
        </button>
        <button
          v-if="pendingCount > 0 && selectedModules.size === 0"
          class="btn btn-sm inline-flex items-center gap-1.5 bg-amber-500/10 text-amber-300 border border-amber-500/30 hover:bg-amber-500/20"
          :disabled="updating"
          @click="selectPending">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          </svg>
          Select {{ pendingCount }} pending
        </button>
        <button
          v-if="selectedDb && selectedModules.size === 0"
          class="btn btn-sm inline-flex items-center gap-1.5 bg-slate-700/60 text-slate-300 border border-slate-600/40 hover:bg-slate-700"
          :disabled="updating"
          @click="confirmUpdateAll = true">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          Update All
        </button>
        <button v-if="selectedModules.size > 0" class="btn btn-ghost btn-sm" @click="selectedModules.clear()">
          Clear
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-sm text-slate-500 px-1">Loading modules…</div>
    <div v-else-if="error" class="text-sm text-red-400 px-1">{{ error }}</div>

    <!-- Module groups -->
    <div v-for="group in filteredGroups" :key="group.label" class="card p-0 overflow-hidden">
      <!-- Group header -->
      <div class="flex items-center gap-2 px-4 py-2.5 border-b border-[#2d3148] cursor-pointer select-none hover:bg-white/[0.02]"
        @click="toggleGroup(group.label)">
        <input type="checkbox"
          class="accent-indigo-500 shrink-0"
          :checked="isGroupSelected(group)"
          :indeterminate="isGroupIndeterminate(group)"
          @click.stop
          @change="toggleGroupSelect(group)" />
        <span class="text-slate-500 text-xs shrink-0">{{ collapsed.has(group.label) ? '▸' : '▾' }}</span>
        <span class="text-sm font-medium text-slate-300 shrink-0">{{ group.label }}</span>
        <code class="text-xs text-slate-600 truncate min-w-0 flex-1" :title="group.path">{{ group.path }}</code>
        <span class="text-xs text-slate-500 shrink-0">{{ group.modules.length }}</span>
        <span v-if="pendingInGroup(group) > 0" class="text-xs text-amber-400 shrink-0 ml-1">
          {{ pendingInGroup(group) }} pending
        </span>
      </div>

      <!-- Module rows -->
      <div v-if="!collapsed.has(group.label)">
        <div v-for="mod in visibleModules(group)" :key="mod.name"
          class="flex items-center gap-3 px-4 py-2 border-b border-[#1e2235] last:border-0 hover:bg-white/[0.02] cursor-pointer"
          :class="{ 'bg-indigo-500/5': selectedModules.has(mod.name) }"
          @click="toggleModule(mod.name)">
          <input type="checkbox"
            class="accent-indigo-500 shrink-0"
            :checked="selectedModules.has(mod.name)"
            @click.stop
            @change="toggleModule(mod.name)" />

          <!-- Status indicator -->
          <div class="w-5 h-5 shrink-0 flex items-center justify-center">
            <svg v-if="updating && updatingModules.has(mod.name)" class="w-4 h-4 animate-spin text-indigo-400" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <svg v-else-if="doneModules.has(mod.name)" class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            <svg v-else-if="failedModules.has(mod.name)" class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </div>

          <span class="font-mono text-[11px] text-slate-200 flex-1 truncate" :title="mod.name">{{ mod.name }}</span>

          <span class="text-[10px] px-1.5 py-0.5 rounded shrink-0"
            :class="{
              'bg-green-900/40 text-green-400': mod.state === 'installed',
              'bg-amber-900/40 text-amber-400': mod.state === 'to upgrade',
              'bg-red-900/40 text-red-400': mod.state === 'to remove',
              'bg-slate-800 text-slate-500': mod.state === 'uninstalled',
            }">{{ mod.state }}</span>

          <span class="text-[10px] text-slate-600 shrink-0 hidden sm:block w-16 text-right">{{ mod.version || '' }}</span>
        </div>

        <div v-if="hiddenCount(group) > 0" class="px-4 py-2 text-xs text-slate-600 italic">
          {{ hiddenCount(group) }} modules hidden by filter
        </div>
      </div>
    </div>

    <!-- Update All confirmation modal -->
    <Teleport to="body">
      <div v-if="confirmUpdateAll" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="confirmUpdateAll = false">
        <div class="bg-[#1a1d2e] border border-[#2d3148] rounded-xl shadow-2xl p-6 w-full max-w-sm mx-4">
          <div class="flex items-center gap-3 mb-4">
            <svg class="w-5 h-5 text-amber-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            </svg>
            <h3 class="text-sm font-semibold text-slate-200">Update All Modules?</h3>
          </div>
          <p class="text-xs text-slate-400 mb-5">
            This runs <code class="text-slate-300 bg-slate-800 px-1 rounded">-u all</code> on <span class="text-slate-300 font-medium">{{ selectedDb }}</span>.
            It may take several minutes and will briefly interrupt the server.
          </p>
          <div class="flex gap-2 justify-end">
            <button class="btn btn-ghost btn-sm" @click="confirmUpdateAll = false">Cancel</button>
            <button class="btn btn-sm bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30 inline-flex items-center gap-1.5"
              @click="confirmUpdateAll = false; updateAll()">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              Yes, update all
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Update log -->
    <div v-if="logLines.length > 0" class="card p-0 overflow-hidden">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-[#2d3148]">
        <div class="flex items-center gap-2">
          <svg v-if="updating" class="w-3.5 h-3.5 animate-spin text-indigo-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
          </svg>
          <svg v-else-if="updateFailed" class="w-3.5 h-3.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          </svg>
          <svg v-else class="w-3.5 h-3.5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
          <span class="text-xs font-mono text-slate-400">
            {{ updating ? (updatingModules.has('all') ? 'Updating all modules…' : `Updating: ${[...updatingModules].join(', ')}`) : (updateFailed ? 'Update failed' : 'Update complete') }}
          </span>
        </div>
        <button class="text-slate-600 hover:text-slate-400 text-xs" @click="logLines = []">✕</button>
      </div>
      <pre ref="logEl" class="log-output max-h-72 overflow-y-auto p-4 text-[11px] leading-relaxed">
        <span v-for="(l, i) in logLines" :key="i"
          :class="{
            'text-red-400':    l.includes(' ERROR '),
            'text-amber-400':  l.includes(' WARNING '),
            'text-green-400':  l.includes(' INFO ') && l.includes('modules'),
            'text-slate-400':  !l.includes(' ERROR ') && !l.includes(' WARNING ') && !(l.includes(' INFO ') && l.includes('modules')),
          }">{{ l }}
</span>
      </pre>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps<{ projectName: string; active: boolean }>()

interface Module { name: string; state: string; version: string; author: string }
interface Group  { label: string; kind: string; path: string; modules: Module[] }

const dbs            = ref<string[]>([])
const selectedDb     = ref('')
const groups         = ref<Group[]>([])
const filter         = ref('')
const loading        = ref(false)
const error          = ref('')
const collapsed      = ref<Set<string>>(new Set(['Odoo Core']))

const selectedModules  = ref<Set<string>>(new Set())
const updatingModules  = ref<Set<string>>(new Set())
const doneModules      = ref<Set<string>>(new Set())
const failedModules    = ref<Set<string>>(new Set())
const updating         = ref(false)
const updateFailed     = ref(false)
const logLines         = ref<string[]>([])
const logEl            = ref<HTMLPreElement | null>(null)
const confirmUpdateAll = ref(false)

const pendingCount = computed(() =>
  groups.value.flatMap(g => g.modules).filter(m => m.state === 'to upgrade').length
)

const filteredGroups = computed(() => {
  if (!filter.value) return groups.value
  const f = filter.value.toLowerCase()
  return groups.value
    .map(g => ({ ...g, modules: g.modules.filter(m => m.name.toLowerCase().includes(f)) }))
    .filter(g => g.modules.length > 0)
})

function visibleModules(g: Group) {
  if (!filter.value) return g.modules
  const f = filter.value.toLowerCase()
  return g.modules.filter(m => m.name.toLowerCase().includes(f))
}

function hiddenCount(g: Group) {
  if (!filter.value) return 0
  const f = filter.value.toLowerCase()
  return g.modules.filter(m => !m.name.toLowerCase().includes(f)).length
}

function pendingInGroup(g: Group) {
  return g.modules.filter(m => m.state === 'to upgrade').length
}

function isGroupSelected(g: Group) {
  return g.modules.length > 0 && g.modules.every(m => selectedModules.value.has(m.name))
}
function isGroupIndeterminate(g: Group) {
  const sel = g.modules.filter(m => selectedModules.value.has(m.name)).length
  return sel > 0 && sel < g.modules.length
}
function toggleGroupSelect(g: Group) {
  if (isGroupSelected(g)) g.modules.forEach(m => selectedModules.value.delete(m.name))
  else                    g.modules.forEach(m => selectedModules.value.add(m.name))
}
function toggleGroup(label: string) {
  if (collapsed.value.has(label)) collapsed.value.delete(label)
  else                            collapsed.value.add(label)
}
function toggleModule(name: string) {
  if (selectedModules.value.has(name)) selectedModules.value.delete(name)
  else                                 selectedModules.value.add(name)
}
function selectPending() {
  groups.value.flatMap(g => g.modules)
    .filter(m => m.state === 'to upgrade')
    .forEach(m => selectedModules.value.add(m.name))
}

watch(() => props.active, async (v) => {
  if (v && !dbs.value.length) {
    const res  = await fetch(`/api/db/${props.projectName}/list`)
    const data = await res.json()
    dbs.value  = (data.databases || []).map((d: { name: string }) => d.name)
  }
})

async function loadModules() {
  if (!selectedDb.value) return
  loading.value = true; error.value = ''
  selectedModules.value.clear()
  doneModules.value.clear()
  failedModules.value.clear()
  const res  = await fetch(`/api/modules/${props.projectName}/${selectedDb.value}`)
  const data = await res.json()
  loading.value = false
  if (data.error) { error.value = data.error; return }
  groups.value = data.groups || []
}

async function updateSelected() {
  if (!selectedDb.value || selectedModules.value.size === 0 || updating.value) return

  const mods = [...selectedModules.value]
  updating.value   = true
  updateFailed.value = false
  logLines.value   = []
  doneModules.value.clear()
  failedModules.value.clear()
  updatingModules.value = new Set(mods)

  // Update all selected modules in one call (comma-joined)
  const modList = mods.join(',')
  const res  = await fetch(`/api/modules/${props.projectName}/${selectedDb.value}/update/${modList}`, { method: 'POST' })
  const data = await res.json()

  if (!data.ok) {
    logLines.value  = [data.error || 'Failed to start update']
    updating.value  = false
    updateFailed.value = true
    mods.forEach(m => { updatingModules.value.delete(m); failedModules.value.add(m) })
    return
  }

  const source = new EventSource(data.stream_url)
  source.onmessage = async (evt) => {
    const d = JSON.parse(evt.data)
    if (d.line) {
      logLines.value.push(d.line)
      await nextTick()
      if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
    }
    if (d.done) {
      source.close()
      const failed = logLines.value.some(l => l.includes(' ERROR '))
      mods.forEach(m => {
        updatingModules.value.delete(m)
        if (failed) failedModules.value.add(m)
        else        doneModules.value.add(m)
      })
      updating.value     = false
      updateFailed.value = failed
      if (!failed) selectedModules.value.clear()
    }
  }
  source.onerror = () => {
    source.close()
    mods.forEach(m => { updatingModules.value.delete(m); failedModules.value.add(m) })
    updating.value     = false
    updateFailed.value = true
  }
}

async function updateAll() {
  if (!selectedDb.value || updating.value) return

  updating.value     = true
  updateFailed.value = false
  logLines.value     = []
  doneModules.value.clear()
  failedModules.value.clear()
  updatingModules.value = new Set(['all'])

  const res  = await fetch(`/api/modules/${props.projectName}/${selectedDb.value}/update/all`, { method: 'POST' })
  const data = await res.json()

  if (!data.ok) {
    logLines.value  = [data.error || 'Failed to start update']
    updating.value  = false
    updateFailed.value = true
    updatingModules.value.clear()
    return
  }

  const source = new EventSource(data.stream_url)
  source.onmessage = async (evt) => {
    const d = JSON.parse(evt.data)
    if (d.line) {
      logLines.value.push(d.line)
      await nextTick()
      if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
    }
    if (d.done) {
      source.close()
      const failed = logLines.value.some(l => l.includes(' ERROR '))
      updatingModules.value.clear()
      updating.value     = false
      updateFailed.value = failed
    }
  }
  source.onerror = () => {
    source.close()
    updatingModules.value.clear()
    updating.value     = false
    updateFailed.value = true
  }
}
</script>
