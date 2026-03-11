<template>
  <div class="card flex-1">
    <div class="flex justify-between items-center mb-2">
      <span class="text-xs text-slate-500">Memory</span>
      <span class="text-xs font-mono text-slate-300">{{ memText }}</span>
    </div>
    <div class="h-2 rounded-full bg-[#2d3148] overflow-hidden">
      <div class="h-full rounded-full transition-all duration-500"
        :style="{ width: pct + '%' }"
        :class="{
          'bg-red-500': pct > 90,
          'bg-amber-500': pct > 75 && pct <= 90,
          'bg-[#6366f1]': pct <= 75,
        }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps<{
  container?: string
  memUsedMb?: number | null
  memLimitMb?: number | null
}>()

const memUsed = ref<number | null>(null)
const memLimit = ref<number | null>(null)
let source: EventSource | null = null

const pct = computed(() => {
  if (!memUsed.value || !memLimit.value) return 0
  return Math.min((memUsed.value / memLimit.value) * 100, 100)
})
const memText = computed(() => {
  if (!memUsed.value || !memLimit.value) return '-- / -- MB'
  return `${memUsed.value.toFixed(0)} / ${memLimit.value.toFixed(0)} MB`
})

// If direct values are provided, use them and skip SSE
watch(() => [props.memUsedMb, props.memLimitMb] as const, ([u, l]) => {
  if (props.memUsedMb !== undefined || props.memLimitMb !== undefined) {
    memUsed.value = u ?? null
    memLimit.value = l ?? null
  }
}, { immediate: true })

onMounted(() => {
  if (props.memUsedMb !== undefined || props.memLimitMb !== undefined) return  // direct value mode
  if (!props.container) return
  source = new EventSource(`/stream/stats/${props.container}`)
  source.onmessage = (evt) => {
    const d = JSON.parse(evt.data)
    if (d.mem_used_mb !== null) memUsed.value = d.mem_used_mb
    if (d.mem_limit_mb !== null) memLimit.value = d.mem_limit_mb
  }
})
onUnmounted(() => source?.close())
</script>
