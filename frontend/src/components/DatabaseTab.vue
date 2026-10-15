<template>
  <div>
    <!-- Databases list -->
    <div class="card mb-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <h3 class="text-sm font-semibold text-slate-300">Databases</h3>
        <div class="flex gap-2">
        <button class="btn btn-primary btn-sm w-full sm:w-auto inline-flex items-center gap-1.5" @click="createDb">
          + New database
        </button>
        <button class="btn btn-ghost btn-sm w-full sm:w-auto inline-flex items-center gap-1.5" @click="loadDbs">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          Refresh
        </button>
        </div>
      </div>
      <div v-if="loading" class="text-sm text-slate-500">Loading…</div>
      <div v-else-if="error" class="text-sm text-red-400">{{ error }}</div>
      <template v-else-if="dbs.length">
        <!-- Mobile: vertical card layout -->
        <div class="space-y-3 sm:hidden">
          <div v-for="db in dbs" :key="db.name" class="border border-border/50 rounded-xl p-3 bg-surface/30">
            <div class="font-mono text-sm font-medium text-white mb-1 break-all">{{ db.name }}</div>
            <div class="text-slate-400 text-xs mb-2">{{ db.size }}</div>
            <div class="flex gap-2">
              <button class="btn btn-ghost btn-sm p-2 min-h-[44px] min-w-[44px]" @click="backup(db.name)" title="Backup">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
              </button>
              <button class="btn btn-ghost btn-sm p-2 min-h-[44px] min-w-[44px]" @click="duplicate(db.name)" title="Duplicate">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
              </button>
              <button class="btn btn-primary btn-sm p-2 min-h-[44px] min-w-[44px] text-xs" @click="openAs(db.name)" title="Open this database signed in as a user — no password needed">
                Open as…
              </button>
              <button class="btn btn-ghost btn-sm p-2 min-h-[44px] min-w-[44px] text-xs" @click="issueAdminLogin(db.name)" title="Issue a one-time admin password">
                Password
              </button>
              <button class="btn btn-ghost btn-sm p-2 min-h-[44px] min-w-[44px]" @click="neutralize(db.name)" title="Neutralize">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
              </button>
              <button class="btn btn-danger btn-sm p-2 min-h-[44px] min-w-[44px]" @click="drop(db.name)" title="Drop">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>
          </div>
        </div>
        <!-- Desktop: table layout -->
        <div class="hidden sm:block overflow-x-auto -mx-4 md:mx-0">
        <div class="inline-block min-w-full align-middle px-4 md:px-0">
          <table class="table-base w-full">
            <thead><tr><th>Database</th><th>Size</th><th>Actions</th></tr></thead>
            <tbody>
              <tr v-for="db in dbs" :key="db.name">
                <td class="font-mono text-sm whitespace-nowrap">{{ db.name }}</td>
                <td class="text-slate-400 text-sm">{{ db.size }}</td>
                <td>
                  <div class="flex gap-2">
                    <button class="btn btn-ghost btn-sm text-xs inline-flex items-center gap-1" @click="backup(db.name)">
                      <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                      Backup
                    </button>
                    <button class="btn btn-ghost btn-sm text-xs inline-flex items-center gap-1" @click="duplicate(db.name)">
                      <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                      Duplicate
                    </button>
                    <button class="btn btn-primary btn-sm text-xs inline-flex items-center gap-1" @click="openAs(db.name)">
                      Open as…
                    </button>
                    <button class="btn btn-ghost btn-sm text-xs inline-flex items-center gap-1" @click="issueAdminLogin(db.name)">
                      Admin password
                    </button>
                    <button class="btn btn-ghost btn-sm text-xs inline-flex items-center gap-1" @click="neutralize(db.name)">
                      <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                      Neutralize
                    </button>
                    <button class="btn btn-danger btn-sm text-xs inline-flex items-center gap-1" @click="drop(db.name)">
                      <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                      Drop
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        </div>
      </template>
      <div v-else class="text-sm text-slate-500">No databases found.</div>
    </div>

    <!-- Backups on disk -->
    <div class="card mb-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <h3 class="text-sm font-semibold text-slate-300">Backups on Disk</h3>
        <label class="btn btn-ghost btn-sm cursor-pointer text-center sm:text-left inline-flex items-center justify-center gap-1.5">
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
          Upload &amp; Restore
          <input type="file" accept=".dump,.zip" class="hidden" @change="uploadRestore" />
        </label>
      </div>
      <p class="text-xs text-slate-500 mb-3">Restored and duplicated databases are automatically neutralized (no outgoing emails, crons, or payment calls).</p>
      <div v-if="!backups.length" class="text-sm text-slate-500">No backup files.</div>
      <template v-else>
        <!-- Mobile: vertical card layout -->
        <div class="space-y-3 sm:hidden">
          <div v-for="b in backups" :key="b.filename" class="border border-border/50 rounded-xl p-3 bg-surface/30">
            <div class="font-mono text-xs font-medium text-white mb-1 break-all">{{ b.filename }}</div>
            <div class="text-slate-400 text-xs mb-2">{{ b.size }} · {{ new Date(b.modified).toLocaleDateString() }}</div>
            <div class="flex gap-2">
              <a :href="`/api/db/${projectName}/download/${b.filename}`" class="btn btn-ghost btn-sm p-2 min-h-[44px] min-w-[44px] inline-flex items-center justify-center" title="Download">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
              </a>
              <button class="btn btn-ghost btn-sm p-2 min-h-[44px] min-w-[44px]" @click="restoreFrom(b.filename)" title="Restore">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
              </button>
            </div>
          </div>
        </div>
        <!-- Desktop: table layout -->
        <div class="hidden sm:block overflow-x-auto -mx-4 md:mx-0">
          <div class="inline-block min-w-full align-middle px-4 md:px-0">
            <table class="table-base w-full">
              <thead><tr><th>File</th><th>Size</th><th class="hidden sm:table-cell">Date</th><th>Actions</th></tr></thead>
              <tbody>
                <tr v-for="b in backups" :key="b.filename">
                  <td class="font-mono text-xs break-all">{{ b.filename }}</td>
                  <td class="text-slate-400 text-xs whitespace-nowrap">{{ b.size }}</td>
                  <td class="text-slate-400 text-xs hidden sm:table-cell whitespace-nowrap">{{ new Date(b.modified).toLocaleString() }}</td>
                  <td>
                    <div class="flex gap-2">
                      <a :href="`/api/db/${projectName}/download/${b.filename}`" class="btn btn-ghost btn-sm text-xs inline-flex items-center p-2" title="Download">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                      </a>
                      <button class="btn btn-ghost btn-sm text-xs" @click="restoreFrom(b.filename)">Restore</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>

    <!-- Backup Schedules -->
    <div class="card mb-4">
      <h3 class="text-sm font-semibold text-slate-300 mb-3">Backup Schedules</h3>
      <div v-if="!dbs.length" class="text-sm text-slate-500">Load databases first.</div>
      <div v-else class="space-y-3">
        <div v-for="db in dbs" :key="'sched-' + db.name" class="border border-border/50 rounded-xl p-4 bg-surface/20">
          <div class="flex flex-col sm:flex-row sm:items-center gap-3">
            <span class="font-mono text-sm text-white shrink-0">{{ db.name }}</span>
            <div class="flex flex-wrap items-center gap-2 flex-1">
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" class="sr-only peer"
                  :checked="schedules[db.name]?.enabled ?? false"
                  @change="toggleSchedule(db.name, ($event.target as HTMLInputElement).checked)" />
                <div class="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent"></div>
              </label>
              <input
                v-if="schedules[db.name]?.enabled"
                type="text"
                class="input input-sm font-mono w-36 text-xs"
                placeholder="0 2 * * *"
                :value="schedules[db.name]?.schedule ?? '0 2 * * *'"
                @change="updateScheduleField(db.name, 'schedule', ($event.target as HTMLInputElement).value)"
              />
              <span v-if="schedules[db.name]?.enabled" class="text-xs text-slate-400">keep last</span>
              <input
                v-if="schedules[db.name]?.enabled"
                type="number"
                class="input input-sm w-16 text-xs"
                min="1" max="99"
                :value="schedules[db.name]?.retention ?? 7"
                @change="updateScheduleField(db.name, 'retention', Number(($event.target as HTMLInputElement).value))"
              />
              <button
                v-if="schedules[db.name]"
                class="btn btn-primary btn-sm text-xs"
                @click="saveSchedule(db.name)">Save</button>
            </div>
          </div>
          <div v-if="schedules[db.name]?.last_run" class="mt-2 text-xs text-slate-500">
            Last run: {{ new Date(schedules[db.name].last_run!).toLocaleString() }}
            <span :class="schedules[db.name].last_result === 'success' ? 'text-green-400' : 'text-red-400'">
              · {{ schedules[db.name].last_result }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Open as… picker -->
    <div v-if="picker" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" @click.self="picker = null">
      <div class="bg-[#1a1d27] border border-[#2d3148] rounded-xl p-6 w-[calc(100vw-2rem)] max-w-md">
        <h4 class="font-semibold text-white mb-1">Open "{{ picker.db }}"</h4>
        <p class="text-sm text-slate-400 mb-3">Signs you in directly — no password is created or shared. The link works once, for 60 seconds, and is recorded in the audit log with your name.</p>
        <div v-if="picker.loading" class="text-sm text-slate-500 mb-4">Loading users…</div>
        <select v-else v-model="picker.login" class="input w-full mb-4">
          <option v-for="u in picker.users" :key="u.login" :value="u.login">{{ u.name }} ({{ u.login }}){{ u.admin ? ' — admin' : '' }}</option>
        </select>
        <p v-if="picker.error" class="text-sm text-red-400 mb-3">{{ picker.error }}</p>
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost" @click="picker = null">Cancel</button>
          <button class="btn btn-primary" :disabled="picker.loading || picker.busy || !picker.login" @click="confirmOpenAs">Open</button>
        </div>
      </div>
    </div>

    <!-- One-time credential -->
    <div v-if="credential" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-[#1a1d27] border border-[#2d3148] rounded-xl p-6 w-[calc(100vw-2rem)] max-w-md">
        <h4 class="font-semibold text-white mb-2">{{ credential.title }}</h4>
        <p class="text-sm text-slate-400 mb-3">Shown once. It is not stored anywhere — copy it now. Issuing a new one replaces it.</p>
        <div class="text-xs text-slate-500">Login</div>
        <div class="font-mono text-sm text-white mb-2 break-all">{{ credential.login }}</div>
        <div class="text-xs text-slate-500">Password</div>
        <div class="font-mono text-sm text-white mb-4 break-all select-all">{{ credential.password }}</div>
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost" @click="copyCredential">Copy password</button>
          <button class="btn btn-primary" @click="credential = null">Done</button>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <div v-if="modal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" @click.self="modal = null">
      <div class="bg-[#1a1d27] border border-[#2d3148] rounded-xl p-6 w-[calc(100vw-2rem)] max-w-md">
        <h4 class="font-semibold text-white mb-2">{{ modal.title }}</h4>
        <p class="text-sm text-slate-400 mb-4" v-html="modal.body" />
        <input v-if="modal.placeholder !== undefined" v-model="modalInput" class="input w-full mb-4" :placeholder="modal.placeholder" />
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost" @click="modal = null">Cancel</button>
          <button class="btn btn-primary" @click="modal.confirm()">Confirm</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { api } from '@/api'
import { ref, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

const props = defineProps<{ projectName: string; active: boolean }>()
const notify = useNotificationsStore()

interface DB { name: string; size: string; size_bytes: number }
interface Backup { filename: string; size: string; modified: string }
interface Schedule {
  enabled: boolean; schedule: string; retention: number;
  last_run: string | null; last_result: string | null
}

const dbs = ref<DB[]>([])
const backups = ref<Backup[]>([])
const schedules = ref<Record<string, Schedule>>({})
const loading = ref(false)
const error = ref('')
const modal = ref<{ title: string; body: string; placeholder?: string; confirm: () => void } | null>(null)
const modalInput = ref('')
const credential = ref<{ title: string; login: string; password: string } | null>(null)
const picker = ref<{ db: string; users: { login: string; name: string; admin: boolean }[]; login: string; loading: boolean; busy: boolean; error: string } | null>(null)

async function openAs(dbname: string) {
  picker.value = { db: dbname, users: [], login: '', loading: true, busy: false, error: '' }
  try {
    const res = await api(`/api/db/${props.projectName}/login-users/${dbname}`)
    const data = await res.json()
    if (!picker.value) return
    if (!res.ok) { picker.value.error = data.error || 'Could not load users'; picker.value.loading = false; return }
    picker.value.users = data.users
    picker.value.login = (data.users.find((u: any) => u.login === 'admin') || data.users[0] || {}).login || ''
  } catch (e: any) {
    if (picker.value) picker.value.error = String(e)
  }
  if (picker.value) picker.value.loading = false
}

async function confirmOpenAs() {
  const p = picker.value
  if (!p) return
  // open the tab synchronously (inside the click) so the popup blocker allows it
  const win = window.open('about:blank', '_blank')
  p.busy = true; p.error = ''
  try {
    const res = await api(`/api/db/${props.projectName}/login-link/${p.db}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login: p.login }),
    })
    const data = await res.json()
    if (data.ok && win) { win.location.href = data.url; picker.value = null }
    else { win?.close(); p.error = data.error || 'Failed'; p.busy = false }
  } catch (e: any) {
    win?.close(); p.error = String(e); p.busy = false
  }
}

async function copyCredential() {
  if (!credential.value) return
  try { await navigator.clipboard.writeText(credential.value.password); notify.add('success', 'Copied') }
  catch { notify.add('error', 'Copy failed — select the password and copy it manually') }
}

function createDb() {
  modalInput.value = ''
  modal.value = {
    title: 'New database',
    body: 'Enter a name for the new empty database (letters, digits, <code>_ . -</code>). An individual admin password is generated for you.',
    placeholder: 'database name',
    confirm: async () => {
      const name = modalInput.value.trim()
      modal.value = null
      if (!name) return
      notify.add('info', `Creating ${name}… this takes a minute`)
      const res = await api(`/api/db/${props.projectName}/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, demo: false }),
      })
      const data = await res.json()
      if (data.ok) {
        credential.value = { title: `Database "${data.name}" created`, login: data.login, password: data.password }
        loadDbs()
      } else {
        notify.add('error', data.error || 'Failed')
      }
    },
  }
}

function issueAdminLogin(dbname: string) {
  modalInput.value = ''
  modal.value = {
    title: `Admin login for "${dbname}"`,
    body: 'Sets a new random password for the <code>admin</code> user of this database and shows it to you once. The previous admin password stops working. This action is recorded in the audit log with your name.',
    confirm: async () => {
      modal.value = null
      const res = await api(`/api/db/${props.projectName}/admin-password/${dbname}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
      })
      const data = await res.json()
      if (data.ok) credential.value = { title: `Admin login for "${dbname}"`, login: data.login, password: data.password }
      else notify.add('error', data.error || 'Failed')
    },
  }
}

const loaded = ref(false)
watch(() => props.active, (v) => { if (v && !loaded.value) { loadDbs(); loadBackups() } })

async function loadDbs() {
  loading.value = true; error.value = ''
  const res = await api(`/api/db/${props.projectName}/list`)
  const data = await res.json()
  loading.value = false
  if (data.error) { error.value = data.error; return }
  dbs.value = data.databases
  loaded.value = true
  loadAllSchedules()
}

async function loadAllSchedules() {
  for (const db of dbs.value) {
    const res = await api(`/api/db/${props.projectName}/backup-schedule/${db.name}`)
    const data = await res.json()
    schedules.value[db.name] = {
      enabled: data.enabled, schedule: data.schedule,
      retention: data.retention, last_run: data.last_run, last_result: data.last_result,
    }
  }
}

function toggleSchedule(dbname: string, enabled: boolean) {
  if (!schedules.value[dbname]) {
    schedules.value[dbname] = { enabled, schedule: '0 2 * * *', retention: 7, last_run: null, last_result: null }
  } else {
    schedules.value[dbname].enabled = enabled
  }
}

function updateScheduleField(dbname: string, field: 'schedule' | 'retention', value: string | number) {
  if (!schedules.value[dbname]) return
  if (field === 'schedule') schedules.value[dbname].schedule = value as string
  else schedules.value[dbname].retention = value as number
}

async function saveSchedule(dbname: string) {
  const s = schedules.value[dbname]
  if (!s) return
  const res = await api(`/api/db/${props.projectName}/backup-schedule/${dbname}/save`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled: s.enabled, schedule: s.schedule, retention: s.retention }),
  })
  const data = await res.json()
  if (data.enabled !== undefined) {
    schedules.value[dbname] = { enabled: data.enabled, schedule: data.schedule, retention: data.retention, last_run: data.last_run, last_result: data.last_result }
    notify.add('success', `Schedule saved for ${dbname}`)
  } else {
    notify.add('error', data.error || 'Failed to save schedule')
  }
}

async function loadBackups() {
  const res = await api(`/api/db/${props.projectName}/backups`)
  const data = await res.json()
  backups.value = data.backups || []
}

async function backup(dbname: string) {
  notify.add('info', `Backing up ${dbname}…`)
  const res = await api(`/api/db/${props.projectName}/backup/${dbname}`, { method: 'POST' })
  const data = await res.json()
  if (data.ok) {
    window.location.href = data.download_url
    loadBackups()
  } else {
    notify.add('error', data.error || 'Backup failed')
  }
}

function duplicate(dbname: string) {
  modalInput.value = ''
  modal.value = {
    title: `Duplicate "${dbname}"`,
    body: 'Enter a name for the new database:',
    placeholder: 'new_database_name',
    confirm: async () => {
      const newName = modalInput.value.trim()
      if (!newName) return
      const res = await api(`/api/db/${props.projectName}/duplicate/${dbname}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
      })
      const data = await res.json()
      modal.value = null
      if (data.ok) { notify.add('success', 'Duplicated and neutralized'); loadDbs() }
      else notify.add('error', data.error || 'Failed')
    }
  }
}

function neutralize(dbname: string) {
  modalInput.value = ''
  modal.value = {
    title: `Neutralize "${dbname}"`,
    body: 'Disables outgoing mail servers, cron jobs, and payment providers on this database so it can\'t act on the outside world. Safe to run again on an already-neutralized DB.',
    confirm: async () => {
      modal.value = null
      notify.add('info', `Neutralizing ${dbname}…`)
      const res = await api(`/api/db/${props.projectName}/neutralize/${dbname}`, { method: 'POST' })
      const data = await res.json()
      notify.add(data.ok ? 'success' : 'error', data.ok ? 'Neutralized' : (data.error || 'Failed'))
    }
  }
}

function drop(dbname: string) {
  modalInput.value = ''
  modal.value = {
    title: `Drop "${dbname}"`,
    body: `<span class="text-red-400">This permanently deletes the database.</span><br>Type the database name to confirm:`,
    placeholder: dbname,
    confirm: async () => {
      if (modalInput.value !== dbname) { notify.add('error', 'Name does not match'); return }
      const res = await api(`/api/db/${props.projectName}/drop/${dbname}`, {
        method: 'DELETE', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: dbname }),
      })
      const data = await res.json()
      modal.value = null
      if (data.ok) { notify.add('success', 'Dropped'); loadDbs() }
      else notify.add('error', data.error || 'Failed')
    }
  }
}

async function restoreFrom(filename: string) {
  const dbname = prompt('Restore into which database name?')
  if (!dbname) return
  notify.add('info', `Restoring into ${dbname}…`)
  const res = await api(`/api/db/${props.projectName}/restore/${dbname}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  })
  const data = await res.json()
  notify.add(data.ok ? 'success' : 'error', data.ok ? 'Restored and neutralized' : data.error)
  if (data.ok) loadDbs()
}

async function uploadRestore(evt: Event) {
  const file = (evt.target as HTMLInputElement).files?.[0]
  if (!file) return
  const dbname = prompt('Restore into which database name?')
  if (!dbname) return
  const form = new FormData()
  form.append('file', file)
  notify.add('info', 'Uploading and restoring…')
  const res = await api(`/api/db/${props.projectName}/restore/${dbname}`, { method: 'POST', body: form })
  const data = await res.json()
  notify.add(data.ok ? 'success' : 'error', data.ok ? 'Restored and neutralized' : data.error)
  if (data.ok) loadDbs()
}
</script>
