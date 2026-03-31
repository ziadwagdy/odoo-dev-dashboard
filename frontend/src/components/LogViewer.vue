<template>
  <div class="card">
    <!-- Toolbar -->
    <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 mb-3">
      <template v-if="!dozzleMode">
        <input v-model="filter" class="input flex-1 w-full sm:min-w-0" placeholder="Filter logs…" />
      </template>
      <template v-else>
        <span class="text-sm text-slate-400 flex-1">Dozzle live view</span>
      </template>

      <div class="flex flex-wrap items-center gap-2">
        <!-- Dozzle toggle -->
        <template v-if="dozzleUrl">
          <button
            class="btn btn-sm min-h-[44px] sm:min-h-0 inline-flex items-center gap-1.5"
            :class="dozzleMode ? 'btn-primary' : 'btn-ghost'"
            @click="dozzleMode = !dozzleMode"
            title="Toggle Dozzle view"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            Dozzle
          </button>
          <a :href="dozzleUrl" target="_blank" rel="noopener" class="btn btn-ghost btn-sm min-h-[44px] sm:min-h-0 inline-flex items-center gap-1.5" title="Open in new tab">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
            New tab
          </a>
        </template>

        <template v-if="!dozzleMode">
          <label class="flex items-center gap-1.5 text-sm text-slate-400 cursor-pointer min-h-[44px] sm:min-h-0">
            <input type="checkbox" v-model="follow" class="accent-indigo-500" /> Follow
          </label>
          <button class="btn btn-ghost btn-sm min-h-[44px] sm:min-h-0" @click="toggleScrollLock" :title="scrollLocked ? 'Unlock scroll' : 'Lock scroll'">
            <template v-if="scrollLocked">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"></path></svg>
              Unlock
            </template>
            <template v-else>
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
              Lock
            </template>
          </button>
          <a :href="`/api/logs/${container}/download`" class="btn btn-ghost btn-sm min-h-[44px] sm:min-h-0 inline-flex items-center gap-1.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            Download
          </a>
        </template>
      </div>
    </div>

    <!-- Dozzle iframe -->
    <div v-if="dozzleMode && dozzleUrl" class="rounded-lg overflow-hidden border border-border/40">
      <iframe
        :src="dozzleUrl"
        class="w-full"
        style="height: 70vh; min-height: 400px; border: none; background: #0d0f17;"
        allow="fullscreen"
      />
    </div>

    <!-- Custom SSE log viewer -->
    <div v-else ref="outputEl" class="log-output min-h-[240px] sm:min-h-[320px] max-h-[60vh] md:max-h-[500px]">
      <span
        v-for="(line, i) in filteredLines"
        :key="i"
        :class="line.cls"
        v-html="line.html + '\n'"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import { ansiToHtml, odooLogClass } from '@/utils/ansi'

const props = defineProps<{
  container: string
  active: boolean
  containerId?: string
  logsUrl?: string
}>()

const dozzleMode = ref(false)
const dozzleUrl = computed(() => {
  if (!props.logsUrl || !props.containerId) return ''
  return `${props.logsUrl}/container/${props.containerId}`
})

interface LogLine { raw: string; html: string; cls: string }

const lines = ref<LogLine[]>([])
const filter = ref('')
const follow = ref(true)
const scrollLocked = ref(false)
const outputEl = ref<HTMLDivElement | null>(null)
let source: EventSource | null = null

const filteredLines = computed(() => {
  if (!filter.value) return lines.value
  const f = filter.value.toLowerCase()
  return lines.value.filter(l => l.raw.toLowerCase().includes(f))
})

watch(() => props.active, (active) => {
  if (active) start()
  else stop()
}, { immediate: true })

function start() {
  if (source) return
  source = new EventSource(`/stream/logs/${props.container}?tail=500&follow=true`)
  source.onmessage = (evt) => {
    const d = JSON.parse(evt.data)
    const raw = d.line || ''
    lines.value.push({ raw, html: ansiToHtml(raw), cls: odooLogClass(raw) })
    if (lines.value.length > 2000) lines.value.shift()
    if (!scrollLocked.value) {
      nextTick(() => {
        if (outputEl.value) outputEl.value.scrollTop = outputEl.value.scrollHeight
      })
    }
  }
}

function stop() {
  source?.close()
  source = null
}

function toggleScrollLock() {
  scrollLocked.value = !scrollLocked.value
}

onUnmounted(() => stop())
</script>
