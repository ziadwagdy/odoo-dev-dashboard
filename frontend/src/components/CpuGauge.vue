<template>
  <div class="flex flex-col items-center gap-1.5">
    <svg viewBox="0 0 120 72" class="w-36 overflow-visible">
      <defs>
        <filter id="gaugeGlow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="2.5" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      <!-- Zone background bands -->
      <path :d="zonePath(0,  60)" fill="none" stroke="#10b981" stroke-opacity="0.18" stroke-width="9" stroke-linecap="butt"/>
      <path :d="zonePath(60, 80)" fill="none" stroke="#f59e0b" stroke-opacity="0.20" stroke-width="9" stroke-linecap="butt"/>
      <path :d="zonePath(80,100)" fill="none" stroke="#ef4444" stroke-opacity="0.20" stroke-width="9" stroke-linecap="butt"/>

      <!-- Regular tick marks at 0, 25, 50, 75, 100 -->
      <line v-for="t in regularTicks" :key="t.pct"
        :x1="t.x1" :y1="t.y1" :x2="t.x2" :y2="t.y2"
        :stroke="tickColor" stroke-width="1.5" stroke-linecap="round"/>

      <!-- Threshold markers at 60%, 80% — cross the arc track -->
      <line v-for="t in threshTicks" :key="t.pct"
        :x1="t.x1" :y1="t.y1" :x2="t.x2" :y2="t.y2"
        :stroke="threshColor" stroke-width="2" stroke-linecap="round"/>

      <!-- Active fill arc -->
      <path v-if="activePct > 0"
        :d="zonePath(0, activePct)"
        fill="none" :stroke="arcColor"
        stroke-width="9" stroke-linecap="round"
        filter="url(#gaugeGlow)"
      />

      <!-- Tip glow dot -->
      <circle
        :cx="tipPos.x" :cy="tipPos.y" r="4.5"
        :fill="arcColor" filter="url(#gaugeGlow)"
        :opacity="cpuPct !== null ? 1 : 0"
      />

      <!-- Value text -->
      <text x="60" y="51"
        text-anchor="middle"
        font-family="'JetBrains Mono', 'Fira Code', monospace"
        font-size="20" font-weight="700"
        :fill="textFill">{{ displayVal }}</text>

      <!-- Sub-label -->
      <text x="60" y="63"
        text-anchor="middle"
        font-family="'JetBrains Mono', 'Fira Code', monospace"
        font-size="7" letter-spacing="1.5"
        :fill="textFill" opacity="0.4">USAGE</text>
    </svg>

    <!-- Footer: label + status badge -->
    <div class="flex items-center justify-between w-36 px-1">
      <span class="text-[9px] font-bold uppercase tracking-[0.2em]"
        :style="{ color: labelColor }">CPU</span>
      <span
        class="text-[8px] font-bold uppercase tracking-wide font-mono px-1.5 py-0.5 rounded-sm border transition-colors duration-300"
        :style="{
          color:            statusColor,
          background:       statusBg,
          borderColor:      statusBorder,
        }">{{ statusText }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useContainerStats } from '@/composables/useContainerStats'
import { useThemeStore } from '@/stores/theme'

const props = defineProps<{ container?: string; value?: number | null }>()

const themeStore = useThemeStore()
const cpuPct = ref<number | null>(null)

watch(() => props.value, (v) => { if (v !== undefined) cpuPct.value = v ?? null }, { immediate: true })

if (props.value === undefined && props.container) {
  const { cpu } = useContainerStats(props.container)
  watch(cpu, (v) => { cpuPct.value = v }, { immediate: true })
}

// ── Arc geometry ──────────────────────────────────────────────────────
const CX = 60, CY = 68, R = 50

function arcPos(pct: number, r = R) {
  const a = Math.PI * (1 - pct / 100)
  return { x: CX + r * Math.cos(a), y: CY - r * Math.sin(a) }
}

// Always use short arc (large=0) — safe for 0-99.99% range
function zonePath(pct1: number, pct2: number, r = R): string {
  const p1 = arcPos(pct1, r), p2 = arcPos(pct2, r)
  return `M ${p1.x.toFixed(2)} ${p1.y.toFixed(2)} A ${r} ${r} 0 0 1 ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`
}

// Regular ticks outside the arc: R+1 → R+7
const regularTicks = [0, 25, 50, 75, 100].map(pct => {
  const i = arcPos(pct, R + 1), o = arcPos(pct, R + 8)
  return { pct, x1: i.x, y1: i.y, x2: o.x, y2: o.y }
})

// Threshold ticks crossing the arc: R-5 → R+9
const threshTicks = [60, 80].map(pct => {
  const i = arcPos(pct, R - 5), o = arcPos(pct, R + 9)
  return { pct, x1: i.x, y1: i.y, x2: o.x, y2: o.y }
})

// Clamp to 99.99 so the 0% / 100% degenerate arc case never occurs
const activePct = computed(() => {
  if (cpuPct.value === null) return 0
  return Math.min(Math.max(cpuPct.value, 0.01), 99.99)
})

const tipPos = computed(() => arcPos(activePct.value))

const displayVal = computed(() =>
  cpuPct.value === null ? '--' : cpuPct.value.toFixed(1) + '%'
)

// ── Color logic ───────────────────────────────────────────────────────
const zone = computed(() => {
  const v = cpuPct.value ?? 0
  if (v >= 85) return 'crit'
  if (v >= 70) return 'high'
  if (v >= 40) return 'ok'
  return 'idle'
})

const arcColor = computed(() => {
  const v = cpuPct.value ?? 0
  if (v >= 85) return '#ef4444'
  if (v >= 70) return '#f59e0b'
  return '#a24689'
})

const textFill    = computed(() => themeStore.isDark ? '#f1f5f9' : '#1a0f2e')
const labelColor  = computed(() => themeStore.isDark ? '#64748b' : '#8b7899')
const tickColor   = computed(() => themeStore.isDark ? 'rgba(148,163,184,0.35)' : 'rgba(90,69,112,0.30)')
const threshColor = computed(() => themeStore.isDark ? 'rgba(148,163,184,0.65)' : 'rgba(90,69,112,0.55)')

const statusText = computed(() =>
  ({ idle: 'IDLE', ok: 'OK', high: 'HIGH', crit: 'CRIT' }[zone.value])
)
const statusColor = computed(() =>
  ({ idle: '#10b981', ok: '#a24689', high: '#d97706', crit: '#ef4444' }[zone.value])
)
const statusBg = computed(() =>
  ({ idle: 'rgba(16,185,129,0.10)', ok: 'rgba(162,70,137,0.10)', high: 'rgba(245,158,11,0.10)', crit: 'rgba(239,68,68,0.10)' }[zone.value])
)
const statusBorder = computed(() =>
  ({ idle: 'rgba(16,185,129,0.30)', ok: 'rgba(162,70,137,0.30)', high: 'rgba(245,158,11,0.30)', crit: 'rgba(239,68,68,0.30)' }[zone.value])
)
</script>
