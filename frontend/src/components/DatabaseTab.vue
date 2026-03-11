<template>
  <div>
    <!-- Databases list -->
    <div class="card mb-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <h3 class="text-sm font-semibold text-slate-300">Databases</h3>
        <button class="btn btn-ghost btn-sm w-full sm:w-auto inline-flex items-center gap-1.5" @click="loadDbs">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          Refresh
        </button>
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

    <!-- Modal -->
    <div v-if="modal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" @click.self="modal = null">
      <div class="bg-[#1a1d27] border border-[#2d3148] rounded-xl p-6 w-[calc(100vw-2rem)] max-w-md">
        <h4 class="font-semibold text-white mb-2">{{ modal.title }}</h4>
        <p class="text-sm text-slate-400 mb-4" v-html="modal.body" />
        <input v-model="modalInput" class="input w-full mb-4" :placeholder="modal.placeholder || ''" />
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost" @click="modal = null">Cancel</button>
          <button class="btn btn-primary" @click="modal.confirm()">Confirm</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

const props = defineProps<{ projectName: string; active: boolean }>()
const notify = useNotificationsStore()

interface DB { name: string; size: string; size_bytes: number }
interface Backup { filename: string; size: string; modified: string }

const dbs = ref<DB[]>([])
const backups = ref<Backup[]>([])
const loading = ref(false)
const error = ref('')
const modal = ref<{ title: string; body: string; placeholder?: string; confirm: () => void } | null>(null)
const modalInput = ref('')

watch(() => props.active, (v) => { if (v) { loadDbs(); loadBackups() } })

async function loadDbs() {
  loading.value = true; error.value = ''
  const res = await fetch(`/api/db/${props.projectName}/list`)
  const data = await res.json()
  loading.value = false
  if (data.error) { error.value = data.error; return }
  dbs.value = data.databases
}

async function loadBackups() {
  const res = await fetch(`/api/db/${props.projectName}/backups`)
  const data = await res.json()
  backups.value = data.backups || []
}

async function backup(dbname: string) {
  notify.add('info', `Backing up ${dbname}…`)
  const res = await fetch(`/api/db/${props.projectName}/backup/${dbname}`, { method: 'POST' })
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
      const res = await fetch(`/api/db/${props.projectName}/duplicate/${dbname}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
      })
      const data = await res.json()
      modal.value = null
      if (data.ok) { notify.add('success', 'Duplicated'); loadDbs() }
      else notify.add('error', data.error || 'Failed')
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
      const res = await fetch(`/api/db/${props.projectName}/drop/${dbname}`, {
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
  const res = await fetch(`/api/db/${props.projectName}/restore/${dbname}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  })
  const data = await res.json()
  notify.add(data.ok ? 'success' : 'error', data.ok ? 'Restored successfully' : data.error)
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
  const res = await fetch(`/api/db/${props.projectName}/restore/${dbname}`, { method: 'POST', body: form })
  const data = await res.json()
  notify.add(data.ok ? 'success' : 'error', data.ok ? 'Restored successfully' : data.error)
  if (data.ok) loadDbs()
}
</script>
