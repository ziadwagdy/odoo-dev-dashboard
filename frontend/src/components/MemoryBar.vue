<template>
  <div class="flex flex-col gap-2">
    <div class="flex justify-between items-center">
      <span class="text-sm font-semibold text-slate-300">Memory</span>
      <span class="text-xs font-mono text-slate-400">{{ memText }}</span>
    </div>
    <div class="h-3 rounded-full bg-surface-hover overflow-hidden border border-border/50 shadow-inner">
      <div class="h-full rounded-full transition-all duration-500"
        :style="{ width: pct + '%' }"
        :class="barColorClass"
      />
    </div>
    <span class="text-xs text-slate-400 font-semibold">{{ pct.toFixed(1) }}%</span>
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

const barColorClass = computed(() => {
  const p = pct.value
  if (p > 90) return 'bg-gradient-to-r from-red-500 to-rose-400'
  if (p > 75) return 'bg-gradient-to-r from-amber-500 to-orange-400'
  return 'bg-gradient-to-r from-primary to-accent'
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
