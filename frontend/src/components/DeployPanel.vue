<template>
  <div v-if="visible" class="card mb-6 border-[#6366f1]/30">
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm font-medium text-slate-300">Deploy Output</span>
      <button class="btn btn-ghost btn-sm p-1.5" @click="visible = false" title="Close">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
      </button>
    </div>
    <pre class="log-output min-h-[8rem] max-h-[40vh] md:max-h-[12rem] whitespace-pre-wrap text-xs">{{ output }}</pre>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

const props = defineProps<{ projectName: string }>()
const notify = useNotificationsStore()

const visible = ref(false)
const output = ref('')

async function trigger() {
  visible.value = true
  output.value = ''

  const res = await fetch(`/api/project/${props.projectName}/deploy`, { method: 'POST' })
  const data = await res.json()
  if (!data.ok) {
    output.value = 'Error: ' + (data.error || 'unknown')
    notify.add('error', data.error || 'Deploy failed')
    return
  }

  const source = new EventSource(`/stream/deploy/${props.projectName}`)
  source.onmessage = (evt) => {
    const d = JSON.parse(evt.data)
    output.value += d.line + '\n'
    if (d.done) {
      source.close()
      notify.add('success', 'Deploy complete')
    }
  }
  source.onerror = () => source.close()
}

defineExpose({ trigger })
</script>
