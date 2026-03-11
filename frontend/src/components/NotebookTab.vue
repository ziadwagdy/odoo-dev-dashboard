<template>
  <div class="space-y-3">
    <!-- Kernel control bar -->
    <div class="card flex flex-col sm:flex-row sm:items-center gap-3">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full transition-colors"
          :class="kernelStatus.running ? 'bg-green-400' : 'bg-slate-600'" />
        <span class="text-sm text-slate-300">
          Kernel:
          <span :class="kernelStatus.running ? 'text-green-400' : 'text-slate-500'">
            {{ kernelStatus.running ? `Running (${kernelStatus.db})` : 'Stopped' }}
          </span>
        </span>
      </div>

      <template v-if="!kernelStatus.running">
        <select v-model="selectedDb" class="input text-sm flex-1 sm:flex-none">
          <option value="">Select database…</option>
          <option v-for="db in databases" :key="db" :value="db">{{ db }}</option>
        </select>
        <button class="btn btn-primary btn-sm w-full sm:w-auto" :disabled="!selectedDb || connecting" @click="startKernel">
          {{ connecting ? '⟳ Starting…' : '▶ Start Odoo Shell' }}
        </button>
      </template>
      <template v-else>
        <span class="text-xs text-slate-500 font-mono hidden md:block flex-1">
          env, self, env['model.name'].search([]) available
        </span>
        <div class="flex gap-2 w-full sm:w-auto">
          <button class="btn btn-warning btn-sm flex-1 sm:flex-none" :disabled="!anyRunning" @click="interruptKernel">⏸ Interrupt</button>
          <button class="btn btn-danger btn-sm flex-1 sm:flex-none" @click="stopKernel">⏹ Stop</button>
        </div>
      </template>

      <button class="btn btn-ghost btn-sm w-full sm:w-auto sm:ml-auto" @click="addCell">+ Cell</button>
    </div>

    <!-- Kernel progress messages -->
    <div v-if="statusMessage" class="flex items-center gap-2 px-4 py-2 text-xs text-slate-400">
      <span class="inline-block w-2 h-2 bg-amber-400 rounded-full pulse" />
      {{ statusMessage }}
    </div>

    <!-- Startup error -->
    <div v-if="startError" class="card border-red-800/50 text-sm text-red-400">
      {{ startError }}
    </div>

    <!-- Cells -->
    <div v-for="(cell, idx) in cells" :key="cell.id"
      class="card border-[#2d3148] overflow-hidden p-0">
      <!-- Cell header -->
      <div class="flex items-center justify-between px-3 py-1.5 bg-[#0f1117]/60 border-b border-[#2d3148]">
        <span class="text-xs text-slate-500 font-mono select-none">In [{{ idx + 1 }}]</span>
        <div class="flex gap-1">
          <button class="btn btn-primary btn-sm py-0.5 px-2 text-xs"
            :disabled="!kernelStatus.running || cell.status === 'running'"
            @click="runCell(cell)">
            {{ cell.status === 'running' ? '⟳' : '▶' }}
            <span class="hidden sm:inline ml-1">Run</span>
            <kbd class="ml-1 text-[10px] opacity-60 hidden md:inline">⌃↵</kbd>
          </button>
          <button class="btn btn-ghost btn-sm py-0.5 px-2 text-xs hidden sm:inline-block" @click="clearOutput(cell)">Clear</button>
          <button class="btn btn-ghost btn-sm py-0.5 px-2 text-slate-600 hover:text-red-400" @click="removeCell(cell.id)">✕</button>
        </div>
      </div>

      <!-- Code textarea -->
      <textarea
        v-model="cell.code"
        class="w-full bg-[#0a0c12] text-slate-200 font-mono text-[13px] leading-relaxed p-3
               focus:outline-none focus:ring-1 focus:ring-[#6366f1]/40 resize-y min-h-[80px]"
        :placeholder="idx === 0 ? '# Full Odoo shell environment available\n# env, self, env[\'res.partner\'].search([]) ...' : '# Python code'"
        spellcheck="false"
        @keydown.ctrl.enter.prevent="runCell(cell)"
        @keydown.meta.enter.prevent="runCell(cell)"
      />

      <!-- Output -->
      <div v-if="cell.outputs.length || cell.status === 'running'" class="border-t border-[#2d3148]">
        <div v-if="cell.status === 'running'" class="px-3 py-2 text-xs text-slate-500 flex items-center gap-2">
          <span class="inline-block w-2 h-2 bg-amber-400 rounded-full pulse" />
          Executing…
        </div>
        <template v-for="(out, oi) in cell.outputs" :key="oi">
          <div v-if="out.type === 'html'"
            class="notebook-output-html px-3 py-2 overflow-x-auto border-t border-[#2d3148]/50 first:border-t-0"
            v-html="out.data" />
          <img v-else-if="out.type === 'image'"
            :src="'data:image/png;base64,' + out.data"
            class="max-w-full h-auto rounded px-3 py-2 border-t border-[#2d3148]/50 first:border-t-0" />
          <div v-else
            class="font-mono text-[12px] leading-relaxed px-3 py-2 whitespace-pre-wrap border-t border-[#2d3148]/50 first:border-t-0"
            :class="{
              'text-slate-300 bg-[#0a0c12]': out.type === 'stdout' || out.type === 'text',
              'text-red-400 bg-red-950/20': out.type === 'stderr' || out.type === 'error',
            }"
            v-html="renderOutput(out.data)"
          />
        </template>
      </div>
    </div>

    <div v-if="!cells.length" class="text-center py-12 text-slate-600 text-sm">
      Start a kernel, then click "+ Cell" to write Python with full Odoo env access.
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'
import { ansiToHtml } from '@/utils/ansi'

const props = defineProps<{ projectName: string; active: boolean }>()
const notify = useNotificationsStore()

interface CellOutput { type: string; data: string }
interface Cell { id: string; code: string; outputs: CellOutput[]; status: 'idle' | 'running' }
interface KernelStatus { running: boolean; status?: string; db?: string }

const cells = ref<Cell[]>([])
const databases = ref<string[]>([])
const selectedDb = ref('')
const kernelStatus = ref<KernelStatus>({ running: false })
const connecting = ref(false)
const startError = ref('')
const statusMessage = ref('')
let ws: WebSocket | null = null
let cellCounter = 0

const anyRunning = computed(() => cells.value.some(c => c.status === 'running'))

watch(() => props.active, (v) => { if (v) init() }, { immediate: true })

async function init() {
  // Load databases
  if (!databases.value.length) {
    const res = await fetch(`/api/db/${props.projectName}/list`)
    const data = await res.json()
    databases.value = (data.databases || []).map((d: { name: string }) => d.name)
  }
  // Get kernel status
  const res = await fetch(`/api/notebooks/${props.projectName}/status`)
  kernelStatus.value = await res.json()
  if (kernelStatus.value.running) connectWS()
}

function connectWS() {
  if (ws && ws.readyState === WebSocket.OPEN) return
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${location.host}/ws/notebook/${props.projectName}`)

  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)

    if (msg.type === 'status') {
      kernelStatus.value = msg.data
    } else if (msg.type === 'status_message') {
      statusMessage.value = msg.text
    } else if (msg.type === 'kernel_started') {
      connecting.value = false
      statusMessage.value = ''
      if (!msg.data.ok) startError.value = msg.data.error || 'Failed to start kernel'
      // kernelStatus updated by the 'status' message sent immediately after
    } else if (msg.type === 'output') {
      const cell = cells.value.find(c => c.id === msg.cell_id)
      if (cell) cell.outputs.push({ type: msg.output_type, data: msg.data })
    } else if (msg.type === 'done') {
      const cell = cells.value.find(c => c.id === msg.cell_id)
      if (cell) cell.status = 'idle'
    } else if (msg.type === 'error') {
      connecting.value = false
      startError.value = msg.error
    }
  }

  ws.onclose = () => {
    ws = null
  }
  ws.onerror = () => {
    connecting.value = false
    notify.add('error', 'Kernel WebSocket error')
  }
}

async function startKernel() {
  if (!selectedDb.value) return
  startError.value = ''
  connecting.value = true
  connectWS()
  // Wait for WS open then send start
  await waitForOpen()
  ws?.send(JSON.stringify({ type: 'start', db: selectedDb.value }))
}

function waitForOpen(): Promise<void> {
  return new Promise((resolve) => {
    if (ws?.readyState === WebSocket.OPEN) { resolve(); return }
    const check = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) { clearInterval(check); resolve() }
    }, 50)
    setTimeout(() => { clearInterval(check); resolve() }, 5000)
  })
}

async function stopKernel() {
  ws?.send(JSON.stringify({ type: 'stop' }))
  await fetch(`/api/notebooks/${props.projectName}/stop`, { method: 'POST' })
  kernelStatus.value = { running: false }
  ws?.close()
  ws = null
}

function interruptKernel() {
  ws?.send(JSON.stringify({ type: 'interrupt' }))
}

function addCell() {
  cells.value.push({ id: String(++cellCounter), code: '', outputs: [], status: 'idle' })
}

function removeCell(id: string) {
  cells.value = cells.value.filter(c => c.id !== id)
}

function clearOutput(cell: Cell) {
  cell.outputs = []
}

function runCell(cell: Cell) {
  if (!kernelStatus.value.running) {
    notify.add('error', 'Start a kernel first')
    return
  }
  if (cell.status === 'running') return
  cell.outputs = []
  cell.status = 'running'
  ws?.send(JSON.stringify({ type: 'execute', code: cell.code, cell_id: cell.id }))
}

function renderOutput(data: string): string {
  return ansiToHtml(data)
    .replace(/\n/g, '<br>')
}

onUnmounted(() => ws?.close())
</script>

<style scoped>
.notebook-output-html :deep(table) {
  border-collapse: collapse;
  font-size: 12px;
  color: #e2e8f0;
}
.notebook-output-html :deep(th) {
  background: #1e2130;
  padding: 4px 8px;
  border: 1px solid #2d3148;
}
.notebook-output-html :deep(td) {
  padding: 3px 8px;
  border: 1px solid #2d3148;
}
.notebook-output-html :deep(tr:nth-child(even)) {
  background: #0f1117;
}
</style>
