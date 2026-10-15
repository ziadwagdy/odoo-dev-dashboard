<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" @click.self="$emit('close')">
    <div class="bg-[#1a1d27] border border-[#2d3148] rounded-xl p-6 w-[calc(100vw-2rem)] max-w-md">
      <h4 class="font-semibold text-white mb-1">Open {{ projectName }} as…</h4>
      <p class="text-sm text-slate-400 mb-4">
        Signs you in directly. No password is created or shared; the link works once, for 60 seconds,
        and is recorded in the audit log with your name.
      </p>
      <div v-if="loadingDbs" class="text-sm text-slate-500 mb-4">Loading databases…</div>
      <template v-else>
        <div v-if="!dbs.length" class="text-sm text-slate-400 mb-4">This project has no databases yet. Create one in the Database tab.</div>
        <template v-else>
          <label class="text-xs text-slate-500">Database</label>
          <select v-model="db" class="input w-full mb-3" @change="loadUsers">
            <option v-for="d in dbs" :key="d" :value="d">{{ d }}</option>
          </select>
          <div v-if="!loadingUsers" class="text-xs mb-3">
            <span v-if="neutralized" class="text-emerald-400">● neutralized — no outgoing mail, crons or payments</span>
            <span v-else class="text-amber-400">● NOT neutralized — may hold live data and integrations</span>
          </div>
          <label class="text-xs text-slate-500">Sign in as</label>
          <div v-if="loadingUsers" class="text-sm text-slate-500 mb-4">Loading users…</div>
          <select v-else v-model="login" class="input w-full mb-2">
            <option v-for="u in users" :key="u.login" :value="u.login" :disabled="!u.allowed">
              {{ u.name }} ({{ u.login }}){{ u.admin ? ' — admin' : '' }}{{ u.allowed ? '' : ' — not allowed for your role' }}
            </option>
          </select>
          <p v-if="selected && !selected.allowed" class="text-xs text-red-400 mb-3">{{ selected.why }}</p>
          <div v-if="selected && selected.allowed && selected.reason_required" class="mb-3">
            <label class="text-xs text-slate-500">Reason (recorded in the audit log)</label>
            <textarea v-model="reason" rows="2" class="input w-full text-sm" placeholder="e.g. verify access rights for ticket #4521" />
          </div>
        </template>
      </template>
      <p v-if="error" class="text-sm text-red-400 mb-3">{{ error }}</p>
      <div class="flex gap-2 justify-end">
        <button class="btn btn-ghost" @click="$emit('close')">Cancel</button>
        <button class="btn btn-primary" :disabled="busy || loadingUsers || !db || !login || !canOpen" @click="open">Open</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api'

const props = defineProps<{ projectName: string; presetDb?: string }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const dbs = ref<string[]>([])
interface LoginUser { login: string; name: string; admin: boolean; allowed: boolean; reason_required: boolean; why: string }
const users = ref<LoginUser[]>([])
const neutralized = ref(true)
const reason = ref('')
const selected = computed(() => users.value.find(u => u.login === login.value))
const canOpen = computed(() => {
  const u = selected.value
  if (!u || !u.allowed) return false
  return !u.reason_required || reason.value.trim().length >= 8
})
const db = ref('')
const login = ref('')
const loadingDbs = ref(true)
const loadingUsers = ref(false)
const busy = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    const res = await api(`/api/db/${props.projectName}/list`)
    const data = await res.json()
    dbs.value = Array.isArray(data) ? data.map((d: any) => d.name) : []
    db.value = props.presetDb && dbs.value.includes(props.presetDb) ? props.presetDb : (dbs.value[0] || '')
  } catch (e: any) { error.value = String(e) }
  loadingDbs.value = false
  if (db.value) await loadUsers()
})

async function loadUsers() {
  loadingUsers.value = true; error.value = ''; users.value = []; login.value = ''
  try {
    const res = await api(`/api/db/${props.projectName}/login-users/${db.value}`)
    const data = await res.json()
    if (!res.ok) { error.value = data.error || 'Could not load users' }
    else {
      users.value = data.users
      neutralized.value = !!data.neutralized
      const allowed = (data.users as LoginUser[]).filter(u => u.allowed)
      login.value = (allowed.find(u => u.login === 'admin') || allowed[0] || data.users[0] || {}).login || ''
    }
  } catch (e: any) { error.value = String(e) }
  loadingUsers.value = false
}

async function open() {
  // open the tab inside the click so the popup blocker allows it
  const win = window.open('about:blank', '_blank')
  busy.value = true; error.value = ''
  try {
    const res = await api(`/api/db/${props.projectName}/login-link/${db.value}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ login: login.value, reason: reason.value.trim() }),
    })
    const data = await res.json()
    if (data.ok && win) { win.location.href = data.url; emit('close') }
    else { win?.close(); error.value = data.error || 'Failed' }
  } catch (e: any) { win?.close(); error.value = String(e) }
  busy.value = false
}
</script>
