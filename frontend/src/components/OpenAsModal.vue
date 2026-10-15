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
          <label class="text-xs text-slate-500">Sign in as</label>
          <div v-if="loadingUsers" class="text-sm text-slate-500 mb-4">Loading users…</div>
          <select v-else v-model="login" class="input w-full mb-4">
            <option v-for="u in users" :key="u.login" :value="u.login">{{ u.name }} ({{ u.login }}){{ u.admin ? ' — admin' : '' }}</option>
          </select>
        </template>
      </template>
      <p v-if="error" class="text-sm text-red-400 mb-3">{{ error }}</p>
      <div class="flex gap-2 justify-end">
        <button class="btn btn-ghost" @click="$emit('close')">Cancel</button>
        <button class="btn btn-primary" :disabled="busy || loadingUsers || !db || !login" @click="open">Open</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api'

const props = defineProps<{ projectName: string; presetDb?: string }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const dbs = ref<string[]>([])
const users = ref<{ login: string; name: string; admin: boolean }[]>([])
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
      login.value = (data.users.find((u: any) => u.login === 'admin') || data.users[0] || {}).login || ''
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
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ login: login.value }),
    })
    const data = await res.json()
    if (data.ok && win) { win.location.href = data.url; emit('close') }
    else { win?.close(); error.value = data.error || 'Failed' }
  } catch (e: any) { win?.close(); error.value = String(e) }
  busy.value = false
}
</script>
