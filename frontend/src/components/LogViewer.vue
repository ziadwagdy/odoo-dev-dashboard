<template>
  <div class="card">
    <div class="flex items-center gap-3 mb-3">
      <input v-model="filter" class="input flex-1" placeholder="Filter logs…" />
      <label class="flex items-center gap-1.5 text-sm text-slate-400 cursor-pointer">
        <input type="checkbox" v-model="follow" class="accent-indigo-500" /> Follow
      </label>
      <button class="btn btn-ghost btn-sm" @click="toggleScrollLock">
        {{ scrollLocked ? '🔓 Unlock' : '🔒 Lock' }}
      </button>
      <a :href="`/api/logs/${container}/download`" class="btn btn-ghost btn-sm">⬇ Download</a>
    </div>
    <div ref="outputEl" class="log-output h-[480px]">
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
