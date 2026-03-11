<template>
  <div v-if="visible" class="card mb-6 border-[#6366f1]/30">
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm font-medium text-slate-300">Deploy Output</span>
      <button class="btn btn-ghost btn-sm" @click="visible = false">✕</button>
    </div>
    <pre class="log-output h-48 whitespace-pre-wrap text-xs">{{ output }}</pre>
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
