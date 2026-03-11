<template>
  <div class="card">
    <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 mb-3">
      <input v-model="filter" class="input flex-1 w-full sm:min-w-0" placeholder="Filter logs…" />
      <div class="flex flex-wrap items-center gap-2">
        <label class="flex items-center gap-1.5 text-sm text-slate-400 cursor-pointer min-h-[44px] sm:min-h-0 items-center">
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
        <a :href="`/api/logs/${container}/download`" class="btn btn-ghost btn-sm min-h-[44px] sm:min-h-0 inline-flex">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
          Download
        </a>
      </div>
    </div>
    <div ref="outputEl" class="log-output min-h-[240px] sm:min-h-[320px] max-h-[60vh] md:max-h-[500px]">
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

const props = defineProps<{ container: string; active: boolean }>()

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
