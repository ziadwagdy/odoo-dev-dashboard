<template>
  <div>
    <!-- Databases list -->
    <div class="card mb-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-slate-300">Databases</h3>
        <button class="btn btn-ghost btn-sm" @click="loadDbs">↺ Refresh</button>
      </div>
      <div v-if="loading" class="text-sm text-slate-500">Loading…</div>
      <div v-else-if="error" class="text-sm text-red-400">{{ error }}</div>
      <table v-else-if="dbs.length" class="table-base">
        <thead><tr><th>Database</th><th>Size</th><th>Actions</th></tr></thead>
        <tbody>
          <tr v-for="db in dbs" :key="db.name">
            <td class="font-mono text-sm">{{ db.name }}</td>
            <td class="text-slate-400">{{ db.size }}</td>
            <td>
              <div class="flex gap-2">
                <button class="btn btn-ghost btn-sm" @click="backup(db.name)">⬇ Backup</button>
                <button class="btn btn-ghost btn-sm" @click="duplicate(db.name)">⧉ Duplicate</button>
                <button class="btn btn-danger btn-sm" @click="drop(db.name)">✕ Drop</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="text-sm text-slate-500">No databases found.</div>
    </div>

    <!-- Backups on disk -->
    <div class="card mb-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-slate-300">Backups on Disk</h3>
        <label class="btn btn-ghost btn-sm cursor-pointer">
          ⬆ Upload &amp; Restore
          <input type="file" accept=".dump,.zip" class="hidden" @change="uploadRestore" />
        </label>
      </div>
      <div v-if="!backups.length" class="text-sm text-slate-500">No backup files.</div>
      <table v-else class="table-base">
        <thead><tr><th>File</th><th>Size</th><th>Date</th><th>Actions</th></tr></thead>
        <tbody>
          <tr v-for="b in backups" :key="b.filename">
            <td class="font-mono text-xs">{{ b.filename }}</td>
            <td class="text-slate-400">{{ b.size }}</td>
            <td class="text-slate-400">{{ new Date(b.modified).toLocaleString() }}</td>
            <td>
              <div class="flex gap-2">
                <a :href="`/api/db/${projectName}/download/${b.filename}`" class="btn btn-ghost btn-sm">⬇</a>
                <button class="btn btn-ghost btn-sm" @click="restoreFrom(b.filename)">Restore</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal -->
    <div v-if="modal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50" @click.self="modal = null">
      <div class="bg-[#1a1d27] border border-[#2d3148] rounded-xl p-6 w-96">
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
