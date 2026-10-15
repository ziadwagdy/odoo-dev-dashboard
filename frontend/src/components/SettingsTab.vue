<template>
  <div class="space-y-4">
    <!-- Runtime settings (curated; odoo.conf itself is never shown or edited) -->
    <div class="card">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-1">
        <h3 class="text-sm font-semibold text-slate-300">Runtime settings</h3>
        <span class="text-xs text-slate-500">Server: {{ host.cpu_count }} vCPU · {{ host.ram_total_mb }} MB RAM (shared by all projects)</span>
      </div>
      <p class="text-xs text-slate-500 mb-4">
        Changes are validated, then reviewed and applied by an admin; the application restarts when needed
        and is rolled back automatically if it does not come back healthy.
      </p>
      <div v-if="loadError" class="text-sm text-red-400 mb-2">{{ loadError }}</div>
      <div v-for="g in groups" :key="g.name" class="mb-4">
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-2">{{ g.name }}</div>
        <div v-for="f in g.fields" :key="f.key" class="flex flex-col sm:flex-row sm:items-start gap-2 mb-3">
          <div class="sm:w-64 sm:shrink-0">
            <div class="text-xs text-slate-300 font-semibold">{{ f.label }}</div>
            <div class="text-[11px] text-slate-500">{{ f.help }}</div>
          </div>
          <div class="flex-1">
            <select v-if="f.type === 'enum'" v-model="draft[f.key]" class="input w-full sm:w-56 text-xs font-mono">
              <option v-for="c in f.choices" :key="c" :value="c">{{ c }}</option>
            </select>
            <input v-else v-model="draft[f.key]" type="number" :min="f.min ?? undefined" :max="f.max ?? undefined" class="input w-full sm:w-56 text-xs font-mono" />
            <div class="text-[11px] text-slate-500 mt-1">
              current {{ f.value }}<span v-if="f.source === 'default'"> (default)</span>
              <span v-if="f.min !== null"> · allowed {{ f.min }}–{{ f.max }}</span>
              <span v-if="String(draft[f.key]) !== String(f.value)" class="text-amber-400"> · modified</span>
            </div>
          </div>
        </div>
      </div>
      <button class="btn btn-primary btn-sm w-full sm:w-auto" :disabled="!dirty || busy" @click="review">Review changes…</button>
    </div>

    <!-- Pending requests -->
    <div class="card" v-if="pending.length">
      <h3 class="text-sm font-semibold text-slate-300 mb-3">Pending change requests</h3>
      <div v-for="r in pending" :key="r.id" class="border border-border/50 rounded-xl p-3 mb-3 bg-surface/30">
        <div class="text-xs text-slate-400 mb-1">#{{ r.id }} · {{ r.requested_by }} · {{ new Date(r.requested_at).toLocaleString() }}</div>
        <ul class="text-sm text-white mb-1">
          <li v-for="(v, k) in r.changes" :key="k" class="font-mono text-xs">{{ labelOf(String(k)) }}: {{ r.previous[k] }} → <b>{{ v }}</b></li>
        </ul>
        <div v-if="r.reason" class="text-xs text-slate-400 mb-1">“{{ r.reason }}”</div>
        <div v-for="w in r.warnings" :key="w" class="text-xs text-amber-400">⚠ {{ w }}</div>
        <div class="flex gap-2 mt-2">
          <button v-if="r.can_approve" class="btn btn-primary btn-sm" @click="startApprove(r)">Review &amp; apply…</button>
          <button v-else-if="canApprove && r.self_request" class="btn btn-ghost btn-sm" title="Another admin should approve this. Use only if you are the sole admin."
                  @click="startApprove(r, true)">Approve my own request (override)…</button>
          <span v-if="canApprove && r.self_request" class="text-xs text-slate-500 self-center">needs a second admin</span>
          <button v-if="canApprove" class="btn btn-ghost btn-sm" @click="reject(r)">Reject</button>
          <button v-if="!canApprove || r.requested_by" class="btn btn-ghost btn-sm" @click="cancel(r)">Cancel</button>
        </div>
      </div>
    </div>

    <!-- History -->
    <div class="card" v-if="history.length">
      <h3 class="text-sm font-semibold text-slate-300 mb-3">Recent changes</h3>
      <div v-for="r in history" :key="r.id" class="text-xs text-slate-400 mb-2">
        <span class="font-mono text-slate-300">#{{ r.id }}</span> · {{ r.status }} · {{ r.requested_by }}
        <span v-if="r.decided_by"> → {{ r.decided_by }}</span>
        · {{ Object.entries(r.changes).map(([k, v]) => k + '=' + v).join(', ') }}
        <span v-if="r.result" class="text-slate-500"> — {{ r.result }}</span>
      </div>
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

    <!-- Review / apply modal -->
    <div v-if="modal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" @click.self="modal = null">
      <div class="bg-[#1a1d27] border border-[#2d3148] rounded-xl p-6 w-[calc(100vw-2rem)] max-w-lg max-h-[90vh] overflow-y-auto">
        <h4 class="font-semibold text-white mb-3">{{ modal.title }}</h4>
        <div v-for="e in modal.errors" :key="e" class="text-sm text-red-400 mb-2">✖ {{ e }}</div>
        <ul v-if="modal.diff.length" class="mb-3">
          <li v-for="d in modal.diff" :key="d.key" class="text-sm text-slate-200 font-mono">{{ d.label }}: {{ d.from }} → <b>{{ d.to }}</b></li>
        </ul>
        <div v-for="w in modal.warnings" :key="w" class="text-sm text-amber-400 mb-2">⚠ {{ w }}</div>
        <p v-if="modal.restart && !modal.errors.length" class="text-xs text-slate-400 mb-3">Applying restarts this project's Odoo (about a minute of downtime). If it does not become healthy the previous configuration is restored automatically.</p>
        <textarea v-if="!modal.errors.length || modal.mode === 'apply'" v-model="modal.reason" class="input w-full mb-3 text-sm" rows="2" :placeholder="modal.selfApprove ? 'Why are you approving your own request? (required, audited)' : (modal.mode === 'request' ? 'Why is this change needed? (shown to the approver)' : 'Note (optional)')" />
        <label v-if="modal.mode === 'apply' && modal.warnings.length" class="flex items-center gap-2 text-sm text-slate-300 mb-3">
          <input type="checkbox" v-model="modal.ack" class="accent-indigo-500" /> I have read the warnings and want to apply anyway
        </label>
        <label v-if="modal.mode === 'apply'" class="flex items-center gap-2 text-sm text-slate-300 mb-3">
          <input type="checkbox" v-model="modal.restartNow" class="accent-indigo-500" /> Restart now
        </label>
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost" @click="modal = null">Close</button>
          <button v-if="modal.mode === 'request' && !modal.errors.length && modal.diff.length" class="btn btn-primary" :disabled="modal.busy" @click="submitRequest">Submit request for approval</button>
          <button v-if="modal.mode === 'apply'" class="btn btn-primary" :disabled="modal.busy || (modal.warnings.length > 0 && !modal.ack)" @click="approve">Apply</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { api } from '@/api'
import { ref, computed, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

interface Field { key: string; label: string; type: string; group: string; help: string; min: number | null; max: number | null; choices: string[] | null; default: number | string; value: number | string; source: string; restart: boolean }
interface Req { self_request?: boolean; can_approve?: boolean; id: number; status: string; requested_by: string; requested_at: string; changes: Record<string, any>; previous: Record<string, any>; warnings: string[]; reason: string; decided_by: string; result: string }

const props = defineProps<{ projectName: string; active: boolean }>()
const notify = useNotificationsStore()

const loaded = ref(false)
const loadError = ref('')
const fields = ref<Field[]>([])
const host = ref({ cpu_count: 0, ram_total_mb: 0, ram_available_mb: 0 })
const pending = ref<Req[]>([])
const history = ref<Req[]>([])
const canApprove = ref(false)
const draft = ref<Record<string, any>>({})
const busy = ref(false)
const cron = ref({ enabled: false, schedule: '0 * * * *', last_run: null as string | null, last_result: null as string | null })

const groups = computed(() => {
  const map: Record<string, Field[]> = {}
  for (const f of fields.value) (map[f.group] ||= []).push(f)
  return Object.entries(map).map(([name, fs]) => ({ name, fields: fs }))
})
const dirty = computed(() => fields.value.some(f => String(draft.value[f.key]) !== String(f.value)))
const labelOf = (k: string) => fields.value.find(f => f.key === k)?.label || k

watch(() => props.active, (v) => { if (v && !loaded.value) loadAll() })

async function loadRuntime() {
  const res = await api(`/api/settings/${props.projectName}/runtime`)
  const d = await res.json()
  if (!res.ok) { loadError.value = d.error || 'Could not load settings'; return }
  fields.value = d.fields; host.value = d.host; pending.value = d.pending; history.value = d.history
  canApprove.value = d.can_approve
  draft.value = Object.fromEntries(d.fields.map((f: Field) => [f.key, f.value]))
}

async function loadAll() {
  await loadRuntime()
  const cronRes = await api(`/api/settings/${props.projectName}/cron`)
  const cronData = await cronRes.json()
  cron.value = { enabled: cronData.enabled, schedule: cronData.schedule, last_run: cronData.last_run, last_result: cronData.last_result }
  loaded.value = true
}

function changedOnly() {
  const out: Record<string, any> = {}
  for (const f of fields.value) if (String(draft.value[f.key]) !== String(f.value)) out[f.key] = draft.value[f.key]
  return out
}

const modal = ref<null | { selfApprove?: boolean; title: string; diff: { key: string; label: string; from: any; to: any }[]; errors: string[]; warnings: string[]; restart: boolean; mode: 'request' | 'apply'; reqId?: number; reason: string; ack: boolean; restartNow: boolean; busy: boolean }>(null)

async function review() {
  busy.value = true
  const res = await api(`/api/settings/${props.projectName}/changes/validate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ changes: changedOnly() }) })
  const d = await res.json()
  busy.value = false
  modal.value = { title: 'Review changes', diff: d.diff || [], errors: d.errors || [], warnings: d.warnings || [], restart: !!d.restart_required, mode: 'request', reason: '', ack: false, restartNow: true, busy: false }
}

async function submitRequest() {
  const m = modal.value; if (!m) return
  m.busy = true
  const res = await api(`/api/settings/${props.projectName}/changes`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ changes: changedOnly(), reason: m.reason }) })
  const d = await res.json()
  m.busy = false
  if (d.ok) { notify.add('success', 'Change request submitted for approval'); modal.value = null; await loadRuntime() }
  else m.errors = d.errors || ['Failed']
}

function startApprove(r: Req, selfApprove = false) {
  modal.value = { selfApprove, title: selfApprove ? `Approve your own request #${r.id} (override)` : `Apply request #${r.id}`, diff: Object.entries(r.changes).map(([k, v]) => ({ key: k, label: labelOf(k), from: r.previous[k], to: v })),
    errors: [], warnings: r.warnings, restart: true, mode: 'apply', reqId: r.id, reason: '', ack: false, restartNow: true, busy: false }
}

async function approve() {
  const m = modal.value; if (!m || m.reqId === undefined) return
  m.busy = true
  const res = await api(`/api/settings/${props.projectName}/changes/${m.reqId}/approve`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm: true, accept_warnings: m.ack, restart: m.restartNow, note: m.reason, self_approve: !!m.selfApprove }) })
  const d = await res.json()
  m.busy = false
  if (d.ok) { notify.add('success', d.restarted ? 'Applied and restarted' : 'Applied (restart pending)'); modal.value = null; await loadRuntime() }
  else { m.errors = d.errors || ['Failed']; if (d.warnings) m.warnings = d.warnings }
}

async function reject(r: Req) {
  const res = await api(`/api/settings/${props.projectName}/changes/${r.id}/reject`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
  if (res.ok) { notify.add('info', 'Request rejected'); await loadRuntime() }
}
async function cancel(r: Req) {
  const res = await api(`/api/settings/${props.projectName}/changes/${r.id}/cancel`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
  if (res.ok) { notify.add('info', 'Request cancelled'); await loadRuntime() }
}

async function saveCron() {
  const res = await api(`/api/settings/${props.projectName}/cron/save`, {
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
