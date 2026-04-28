<template>
  <div v-if="visible" class="card mb-6 border-[#6366f1]/30">
    <div class="flex items-center justify-between mb-3">
      <span class="text-sm font-medium text-slate-300">Deploy Output</span>
      <button class="btn btn-ghost btn-sm p-1.5" @click="visible = false" title="Close">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
      </button>
    </div>
    <div ref="outputEl" class="log-output min-h-[8rem] max-h-[40vh] md:max-h-[12rem]">
      <div v-for="(line, i) in lines" :key="i" :class="line.cls" v-html="line.html" />
      <div v-if="!lines.length" class="log-dim">Waiting for output…</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { api } from '@/api'
import { ref, nextTick } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'
import { parseLine, type LogLine } from '@/utils/ansi'

const props = defineProps<{ projectName: string }>()
const notify = useNotificationsStore()

const visible = ref(false)
const lines = ref<LogLine[]>([])
const outputEl = ref<HTMLElement | null>(null)

function scrollBottom() {
  nextTick(() => { if (outputEl.value) outputEl.value.scrollTop = outputEl.value.scrollHeight })
}

async function trigger() {
  visible.value = true
  lines.value = []

  const res = await api(`/api/project/${props.projectName}/deploy`, { method: 'POST' })
  const data = await res.json()
  if (!data.ok) {
    lines.value.push(parseLine('Error: ' + (data.error || 'unknown')))
    notify.add('error', data.error || 'Deploy failed')
    return
  }

  const source = new EventSource(`/stream/deploy/${props.projectName}`)
  source.onmessage = (evt) => {
    const d = JSON.parse(evt.data)
    lines.value.push(parseLine(d.line ?? ''))
    scrollBottom()
    if (d.done) {
      source.close()
      notify.add('success', 'Deploy complete')
    }
  }
  source.onerror = () => source.close()
}

defineExpose({ trigger })
</script>
