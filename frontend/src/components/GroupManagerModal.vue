<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />

        <!-- Panel -->
        <div class="relative bg-surface border border-border rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-border flex-shrink-0">
            <h2 class="text-base font-bold text-white">Manage Project Groups</h2>
            <button class="btn btn-ghost btn-sm p-1.5" @click="$emit('close')">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-y-auto px-6 py-4 space-y-4">

            <!-- Existing groups -->
            <div v-if="rawGroups.length" class="space-y-3">
              <h3 class="text-xs font-bold uppercase tracking-widest text-slate-400">Existing Groups</h3>
              <div
                v-for="g in rawGroups"
                :key="g.name"
                class="rounded-xl border border-border/60 bg-surface-hover px-4 py-3 space-y-2"
              >
                <div class="flex items-center justify-between">
                  <span class="font-semibold text-white text-sm">{{ g.name }}</span>
                  <div class="flex gap-2">
                    <button class="btn btn-ghost btn-sm text-xs" @click="startEdit(g)">Edit</button>
                    <button class="btn btn-ghost btn-sm text-xs text-red-400 hover:text-red-300" @click="deleteGroup(g.name)">Delete</button>
                  </div>
                </div>
                <div class="grid grid-cols-3 gap-2 text-[11px]">
                  <div>
                    <span class="text-emerald-400 font-bold uppercase">Prod:</span>
                    <span class="text-slate-400 ml-1 font-mono">{{ g.production_instance || '—' }}</span>
                  </div>
                  <div>
                    <span class="text-amber-400 font-bold uppercase">Stage:</span>
                    <span class="text-slate-400 ml-1 font-mono">{{ g.staging_instance || '—' }}</span>
                  </div>
                  <div>
                    <span class="text-sky-400 font-bold uppercase">Dev:</span>
                    <span class="text-slate-400 ml-1 font-mono">{{ g.dev_instance || '—' }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-else-if="!loadingGroups" class="text-sm text-slate-500 italic">No groups configured yet.</div>

            <!-- Divider -->
            <div class="h-px bg-border" />

            <!-- New / edit group form -->
            <div class="space-y-3">
              <h3 class="text-xs font-bold uppercase tracking-widest text-slate-400">
                {{ editingGroup ? `Edit "${editingGroup}"` : 'New Group' }}
              </h3>

              <!-- Group name -->
              <div>
                <label class="block text-xs text-slate-400 mb-1">Group Name</label>
                <input
                  v-model="form.name"
                  :disabled="!!editingGroup"
                  type="text"
                  placeholder="e.g. lexus-tailors"
                  class="input w-full text-sm"
                  :class="{ 'opacity-60 cursor-not-allowed': !!editingGroup }"
                />
              </div>

              <!-- Instance selectors -->
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div v-for="env in ENV_DEFS" :key="env.type">
                  <label class="block text-xs mb-1" :class="env.labelColor">
                    {{ env.label }} Instance
                  </label>
                  <select v-model="form[env.field]" class="input w-full text-sm">
                    <option value="">— none —</option>
                    <option
                      v-for="inst in availableInstances"
                      :key="inst.name"
                      :value="inst.name"
                    >
                      {{ inst.name }} (v{{ inst.version }}) {{ inst.running ? '●' : '○' }}
                    </option>
                  </select>
                </div>
              </div>

              <!-- Error -->
              <p v-if="error" class="text-xs text-red-400">{{ error }}</p>

              <!-- Buttons -->
              <div class="flex gap-2 pt-1">
                <button
                  class="btn btn-primary btn-sm flex-1"
                  :disabled="saving"
                  @click="saveGroup"
                >
                  <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                  {{ saving ? 'Saving…' : (editingGroup ? 'Update Group' : 'Create Group') }}
                </button>
                <button v-if="editingGroup" class="btn btn-ghost btn-sm" @click="cancelEdit">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import type { Project } from '@/stores/projects'

interface RawGroup {
  id: number
  name: string
  production_instance: string
  staging_instance: string
  dev_instance: string
}

const props = defineProps<{
  show: boolean
  availableInstances: Project[]
}>()

const emit = defineEmits<{
  close: []
  saved: []
}>()

const ENV_DEFS = [
  { type: 'production' as const, label: 'Production', labelColor: 'text-emerald-400', field: 'production_instance' as const },
  { type: 'staging'    as const, label: 'Staging',    labelColor: 'text-amber-400',   field: 'staging_instance'    as const },
  { type: 'dev'        as const, label: 'Dev',        labelColor: 'text-sky-400',      field: 'dev_instance'        as const },
]

const rawGroups = ref<RawGroup[]>([])
const loadingGroups = ref(false)

const form = reactive({
  name: '',
  production_instance: '',
  staging_instance: '',
  dev_instance: '',
})

const editingGroup = ref<string | null>(null)
const saving = ref(false)
const error = ref('')

async function fetchRawGroups() {
  loadingGroups.value = true
  try {
    const res = await fetch('/api/groups')
    rawGroups.value = await res.json()
  } finally {
    loadingGroups.value = false
  }
}

// Fetch raw groups when modal opens; reset when it closes
watch(() => props.show, (v) => {
  if (v) {
    fetchRawGroups()
  } else {
    cancelEdit()
  }
})

function startEdit(g: RawGroup) {
  editingGroup.value = g.name
  form.name = g.name
  form.production_instance = g.production_instance
  form.staging_instance = g.staging_instance
  form.dev_instance = g.dev_instance
  error.value = ''
}

function cancelEdit() {
  editingGroup.value = null
  form.name = ''
  form.production_instance = ''
  form.staging_instance = ''
  form.dev_instance = ''
  error.value = ''
}

async function saveGroup() {
  error.value = ''
  if (!form.name.trim()) {
    error.value = 'Group name is required'
    return
  }
  saving.value = true
  try {
    const res = await fetch('/api/groups/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: form.name.trim(),
        production_instance: form.production_instance,
        staging_instance: form.staging_instance,
        dev_instance: form.dev_instance,
      }),
    })
    if (!res.ok) {
      const data = await res.json()
      error.value = data.error || 'Save failed'
      return
    }
    cancelEdit()
    await fetchRawGroups()
    emit('saved')
  } catch {
    error.value = 'Network error'
  } finally {
    saving.value = false
  }
}

async function deleteGroup(name: string) {
  if (!confirm(`Delete group "${name}"? The instances themselves will not be affected.`)) return
  try {
    await fetch(`/api/groups/${encodeURIComponent(name)}`, { method: 'DELETE' })
    await fetchRawGroups()
    emit('saved')
  } catch {
    // ignore
  }
}
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
