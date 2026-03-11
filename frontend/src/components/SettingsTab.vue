<template>
  <div class="space-y-4">
    <!-- odoo.conf -->
    <div class="card">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <h3 class="text-sm font-semibold text-slate-300">odoo.conf</h3>
        <button class="btn btn-primary btn-sm w-full sm:w-auto" @click="saveConf">Save</button>
      </div>
      <div v-if="confError" class="text-sm text-red-400 mb-2">{{ confError }}</div>
      <div v-for="(kv, section) in conf" :key="section" class="mb-4">
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">[{{ section }}]</div>
        <div v-for="(val, key) in kv" :key="key" class="flex flex-col sm:flex-row sm:items-center gap-2 mb-3">
          <span class="font-mono text-xs text-slate-400 sm:w-48 sm:shrink-0 font-semibold">{{ key }}</span>
          <input class="input flex-1 text-xs font-mono w-full" :value="val" @input="updateConf(section as string, key as string, ($event.target as HTMLInputElement).value)" />
        </div>
      </div>
    </div>

    <!-- .env -->
    <div class="card">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <h3 class="text-sm font-semibold text-slate-300">.env</h3>
        <button class="btn btn-primary btn-sm w-full sm:w-auto" @click="saveEnv">Save</button>
      </div>
      <div v-for="(val, key) in env" :key="key" class="flex flex-col sm:flex-row sm:items-center gap-2 mb-3">
        <span class="font-mono text-xs text-slate-400 sm:w-48 sm:shrink-0 font-semibold">{{ key }}</span>
        <input class="input flex-1 text-xs font-mono w-full" :value="val" @input="updateEnv(key as string, ($event.target as HTMLInputElement).value)" />
      </div>
      <div v-if="!Object.keys(env).length" class="text-sm text-slate-500">No .env file found.</div>
    </div>

    <!-- Cron -->
    <div class="card">
      <h3 class="text-sm font-semibold text-slate-300 mb-3">Auto-Deploy Cron</h3>
      <div class="flex flex-col gap-3 mb-3">
        <label class="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" v-model="cron.enabled" class="accent-indigo-500" />
          <span class="text-slate-300">Enabled</span>
        </label>
        <div class="flex flex-col sm:flex-row gap-3">
          <input v-model="cron.schedule" class="input font-mono text-xs sm:w-40" placeholder="0 * * * *" />
          <span class="text-xs text-slate-500 self-center">{{ cronHumanReadable }}</span>
        </div>
      </div>
      <div v-if="cron.last_run" class="text-xs text-slate-500 mb-3">
        Last run: {{ new Date(cron.last_run).toLocaleString() }} — {{ cron.last_result || 'unknown' }}
      </div>
      <button class="btn btn-primary btn-sm w-full sm:w-auto" @click="saveCron">Save Cron</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

const props = defineProps<{ projectName: string; active: boolean }>()
const notify = useNotificationsStore()

const conf = ref<Record<string, Record<string, string>>>({})
const env = ref<Record<string, string>>({})
const cron = ref({ enabled: false, schedule: '0 * * * *', last_run: null as string | null, last_result: null as string | null })
const confError = ref('')

watch(() => props.active, (v) => { if (v) loadAll() })

async function loadAll() {
  const [confRes, envRes, cronRes] = await Promise.all([
    fetch(`/api/settings/${props.projectName}/odoo-conf`),
    fetch(`/api/settings/${props.projectName}/env`),
    fetch(`/api/settings/${props.projectName}/cron`),
  ])
  const confData = await confRes.json()
  if (confData.error) confError.value = confData.error
  else conf.value = confData

  env.value = await envRes.json()
  const cronData = await cronRes.json()
  cron.value = { enabled: cronData.enabled, schedule: cronData.schedule, last_run: cronData.last_run, last_result: cronData.last_result }
}

function updateConf(section: string, key: string, val: string) {
  conf.value[section][key] = val
}

function updateEnv(key: string, val: string) {
  env.value[key] = val
}

async function saveConf() {
  const res = await fetch(`/api/settings/${props.projectName}/odoo-conf/write`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(conf.value),
  })
  const d = await res.json()
  notify.add(d.ok ? 'success' : 'error', d.ok ? 'odoo.conf saved' : d.error)
}

async function saveEnv() {
  const res = await fetch(`/api/settings/${props.projectName}/env/write`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(env.value),
  })
  const d = await res.json()
  notify.add(d.ok ? 'success' : 'error', d.ok ? '.env saved' : d.error)
}

async function saveCron() {
  const res = await fetch(`/api/settings/${props.projectName}/cron/save`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled: cron.value.enabled, schedule: cron.value.schedule }),
  })
  const d = await res.json()
  notify.add(d.ok !== false ? 'success' : 'error', d.project ? 'Cron saved' : d.error)
}

const cronHumanReadable = computed(() => {
  const parts = cron.value.schedule.split(' ')
  if (parts.length !== 5) return 'invalid cron'
  const [min, hour] = parts
  if (min === '0' && hour === '*') return 'every hour'
  if (min === '0' && hour === '0') return 'daily at midnight'
  if (min === '*' && hour === '*') return 'every minute'
  return cron.value.schedule
})
</script>
