<template>
  <div class="flex flex-col items-center justify-center p-4">
    <div class="relative">
      <svg viewBox="0 0 100 60" class="w-32">
        <!-- Background arc -->
        <path d="M 10 55 A 40 40 0 0 1 90 55" fill="none" stroke="rgba(42, 49, 80, 0.5)" stroke-width="10" stroke-linecap="round"/>
        <!-- Fill arc with glow -->
        <defs>
          <linearGradient id="cpuGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" :stop-color="gradientStart" />
            <stop offset="100%" :stop-color="gradientEnd" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <path d="M 10 55 A 40 40 0 0 1 90 55" fill="none"
          stroke="url(#cpuGradient)"
          stroke-width="10" stroke-linecap="round"
          :stroke-dasharray="`${arcLength} 126`"
          :stroke-dashoffset="0"
          filter="url(#glow)"
        />
        <text x="50" y="50" text-anchor="middle" class="fill-white text-lg font-bold" font-size="16">
          {{ cpuText }}
        </text>
      </svg>
    </div>
    <div class="text-xs font-semibold text-slate-400 mt-1 uppercase tracking-wider">CPU</div>
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

const gradientStart = computed(() => {
  const v = cpuPct.value ?? 0
  if (v > 80) return '#ef4444'
  if (v > 60) return '#f59e0b'
  return '#714b67'
})

const gradientEnd = computed(() => {
  const v = cpuPct.value ?? 0
  if (v > 80) return '#dc2626'
  if (v > 60) return '#d97706'
  return '#a24689'
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
