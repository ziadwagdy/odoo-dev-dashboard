<template>
  <div class="card flex flex-col items-center justify-center w-32">
    <svg viewBox="0 0 100 60" class="w-24">
      <!-- Background arc -->
      <path d="M 10 55 A 40 40 0 0 1 90 55" fill="none" stroke="#2d3148" stroke-width="8" stroke-linecap="round"/>
      <!-- Fill arc -->
      <path d="M 10 55 A 40 40 0 0 1 90 55" fill="none"
        :stroke="arcColor"
        stroke-width="8" stroke-linecap="round"
        :stroke-dasharray="`${arcLength} 126`"
        :stroke-dashoffset="0"
      />
      <text x="50" y="52" text-anchor="middle" class="fill-white text-sm" font-size="14" font-weight="600">
        {{ cpuText }}
      </text>
    </svg>
    <div class="text-xs text-slate-500 -mt-1">CPU</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps<{
  container?: string
  value?: number | null
}>()

const cpuPct = ref<number | null>(null)
let source: EventSource | null = null

const ARC_MAX = 126
const arcLength = computed(() => cpuPct.value === null ? 0 : (Math.min(cpuPct.value, 100) / 100) * ARC_MAX)
const cpuText = computed(() => cpuPct.value === null ? '--' : cpuPct.value.toFixed(1) + '%')
const arcColor = computed(() => {
  const v = cpuPct.value ?? 0
  if (v > 80) return '#f87171'
  if (v > 60) return '#fbbf24'
  return '#6366f1'
})

// If a direct value is provided, use it and skip SSE
watch(() => props.value, (v) => {
  if (v !== undefined) cpuPct.value = v ?? null
}, { immediate: true })

onMounted(() => {
  if (props.value !== undefined) return  // direct value mode — no SSE
  if (!props.container) return
  source = new EventSource(`/stream/stats/${props.container}`)
  source.onmessage = (evt) => {
    const d = JSON.parse(evt.data)
    if (d.cpu_pct !== null && d.cpu_pct !== undefined) cpuPct.value = d.cpu_pct
  }
})
onUnmounted(() => source?.close())
</script>
