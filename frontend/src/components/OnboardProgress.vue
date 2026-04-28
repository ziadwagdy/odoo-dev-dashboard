<template>
  <div class="space-y-5">

    <!-- ── Phase tracker ──────────────────────────────────────────── -->
    <div class="card p-0 overflow-hidden">
      <div class="px-5 py-3 border-b border-border/60">
        <span class="text-xs font-bold uppercase tracking-widest text-slate-500">Steps</span>
      </div>

      <div class="divide-y divide-border/40">
        <div
          v-for="phase in phases"
          :key="phase.id"
          class="flex items-center gap-3 px-5 py-3 transition-colors"
          :class="phase.status === 'running' ? 'bg-accent/5' : ''"
        >
          <!-- status icon -->
          <div class="w-5 h-5 flex items-center justify-center shrink-0">
            <div v-if="phase.status === 'running'"
              class="w-4 h-4 rounded-full border-2 border-accent border-t-transparent animate-spin"/>
            <svg v-else-if="phase.status === 'done'"
              class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
            </svg>
            <svg v-else-if="phase.status === 'error'"
              class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
            </svg>
            <div v-else class="w-2 h-2 rounded-full bg-slate-700"/>
          </div>

          <!-- label -->
          <span class="text-sm flex-1 transition-colors" :class="{
            'text-white font-medium': phase.status === 'running',
            'text-emerald-400':       phase.status === 'done',
            'text-red-400':           phase.status === 'error',
            'text-slate-500':         phase.status === 'pending',
          }">{{ phase.label }}</span>

          <!-- error message inline -->
          <span v-if="phase.status === 'error' && phase.message"
            class="text-xs text-red-400/80 truncate max-w-[240px]" :title="phase.message">
            {{ phase.message }}
          </span>

          <!-- build log toggle -->
          <button
            v-if="phase.id === 'build' && buildLogs.length"
            @click="showBuildLog = !showBuildLog"
            class="text-xs text-slate-500 hover:text-slate-300 transition-colors shrink-0">
            {{ showBuildLog ? 'Hide log ↑' : 'Show log ↓' }}
          </button>
        </div>
      </div>

      <!-- build log (collapsible) -->
      <Transition name="slide">
        <div v-if="showBuildLog && buildLogs.length" class="border-t border-border/60 bg-black/20">
          <div ref="buildLogEl" class="px-4 py-3 font-mono text-xs max-h-52 overflow-y-auto">
            <div v-for="(line, i) in buildLogs" :key="i"
              :class="line.error ? 'log-error' : classifyLine(line.text)"
              v-html="ansiToHtml(line.text)" />
          </div>
        </div>
      </Transition>

      <!-- general logs (non-build, non-phase) -->
      <div v-if="generalLogs.length" class="border-t border-border/60 bg-black/10">
        <div class="px-4 py-3 font-mono text-xs max-h-32 overflow-y-auto">
          <div v-for="(line, i) in generalLogs" :key="i"
            :class="line.error ? 'log-error' : classifyLine(line.text)"
            v-html="ansiToHtml(line.text)" />
        </div>
      </div>
    </div>

    <!-- ── Credential box ─────────────────────────────────────────── -->
    <Transition name="fade">
      <div v-if="credential"
        class="rounded-xl border-2 border-amber-500/40 bg-amber-500/5 px-5 py-4">
        <div class="flex items-center gap-2 mb-3">
          <svg class="w-4 h-4 text-amber-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>
          </svg>
          <span class="text-sm font-semibold text-amber-400">{{ credential.label }}</span>
          <span class="text-xs text-slate-500 ml-auto">Save this — shown once</span>
        </div>
        <div class="flex items-center gap-2">
          <code class="flex-1 px-3 py-2 rounded-lg bg-slate-900 text-amber-300 font-mono text-sm select-all">
            {{ credential.value }}
          </code>
          <button @click="copy(credential.value)"
            class="btn btn-ghost btn-sm shrink-0 min-w-[64px] transition-colors"
            :class="recentCopy === credential.value ? 'text-emerald-400 border-emerald-500/40' : ''">
            {{ recentCopy === credential.value ? '✓ Copied' : 'Copy' }}
          </button>
        </div>
      </div>
    </Transition>

    <!-- ── Error terminal ─────────────────────────────────────────── -->
    <div v-if="isDone && !isSuccess" class="text-center py-8">
      <div class="w-14 h-14 mx-auto mb-4 rounded-full bg-red-500/10 border-2 border-red-500/60 flex items-center justify-center">
        <svg class="w-7 h-7 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </div>
      <h3 class="text-lg font-bold text-red-400 mb-1">Onboarding Failed</h3>
      <p class="text-sm text-slate-400">Check the log above for details.</p>
    </div>

    <!-- ── Success + manual steps ────────────────────────────────── -->
    <template v-if="isDone && isSuccess">

      <!-- success banner -->
      <div class="rounded-xl border border-emerald-500/30 bg-emerald-500/5 px-5 py-4 flex flex-wrap items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/60 flex items-center justify-center shrink-0">
          <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold text-emerald-400">Project is running</p>
          <a v-if="doneUrl" :href="doneUrl" target="_blank"
            class="text-xs text-slate-400 hover:text-accent transition-colors truncate block">
            {{ doneUrl }}
          </a>
        </div>
        <div class="flex gap-2 shrink-0">
          <RouterLink :to="`/project/${projectName}`" class="btn btn-primary btn-sm">View Project</RouterLink>
          <RouterLink to="/" class="btn btn-ghost btn-sm">Dashboard</RouterLink>
        </div>
      </div>

      <!-- manual steps -->
      <div v-if="manualSteps.length">
        <div class="flex items-center gap-3 my-2">
          <div class="flex-1 h-px bg-border/60"/>
          <span class="text-[10px] font-bold uppercase tracking-widest text-slate-500 px-1">
            Complete manually to go public
          </span>
          <div class="flex-1 h-px bg-border/60"/>
        </div>

        <p class="text-xs text-slate-500 mb-4 text-center">
          Run these over SSH. The project is already running internally — these make it reachable at its public URL.
        </p>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div v-for="step in manualSteps" :key="step.id"
            class="card transition-colors"
            :class="completedSteps.has(step.id) ? 'border-emerald-500/20 bg-emerald-500/3' : ''">

            <!-- step header -->
            <div class="flex items-center gap-2 mb-4">
              <button
                @click="toggleStep(step.id)"
                class="w-5 h-5 rounded-full border flex items-center justify-center shrink-0 transition-all"
                :class="completedSteps.has(step.id)
                  ? 'border-emerald-500 bg-emerald-500/20 hover:bg-emerald-500/10'
                  : 'border-amber-500/40 bg-amber-500/10 hover:border-amber-500/70'"
                :title="completedSteps.has(step.id) ? 'Mark undone' : 'Mark done'">
                <svg v-if="completedSteps.has(step.id)"
                  class="w-3 h-3 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                </svg>
                <div v-else class="w-1.5 h-1.5 rounded-full bg-amber-400"/>
              </button>
              <h4 class="text-sm font-bold text-white flex-1">{{ step.label }}</h4>
              <span v-if="completedSteps.has(step.id)" class="text-xs text-emerald-400">Done</span>
            </div>

            <!-- step items -->
            <div class="space-y-2">
              <template v-for="(item, i) in step.items" :key="i">
                <p v-if="item.kind === 'note'"
                  class="text-xs text-slate-400 leading-relaxed">{{ item.text }}</p>

                <div v-else class="relative group">
                  <pre class="text-xs rounded-lg px-3 py-2.5 overflow-x-auto leading-relaxed whitespace-pre-wrap break-all"
                    :class="item.kind === 'command'
                      ? 'bg-slate-900 text-slate-200 pr-14'
                      : 'bg-surface-hover text-slate-400 border border-border/60'">{{ item.text }}</pre>
                  <button
                    v-if="item.kind === 'command'"
                    @click="copy(item.text)"
                    class="absolute top-1.5 right-1.5 px-2 py-1 rounded text-[10px] font-medium transition-all"
                    :class="recentCopy === item.text
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-slate-700 text-slate-400 opacity-0 group-hover:opacity-100 hover:bg-slate-600 hover:text-white'">
                    {{ recentCopy === item.text ? '✓' : 'Copy' }}
                  </button>
                </div>
              </template>
            </div>
          </div>
        </div>

        <!-- completion tracker -->
        <div v-if="manualSteps.length" class="mt-4 flex items-center justify-center gap-2">
          <div v-for="step in manualSteps" :key="step.id"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-colors"
            :class="completedSteps.has(step.id)
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
              : 'bg-surface-hover text-slate-500 border border-border/60'">
            <svg v-if="completedSteps.has(step.id)"
              class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
            </svg>
            <div v-else class="w-1.5 h-1.5 rounded-full bg-current"/>
            {{ step.label }}
          </div>
        </div>
      </div>

    </template>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { RouterLink } from 'vue-router'
import { ansiToHtml, classifyLine } from '@/utils/ansi'

// ── types ─────────────────────────────────────────────────────────

import type { OnboardEvent } from '@/types/onboard'

interface PhasesDef { id: string; label: string }
interface PhaseState { id: string; label: string; status: 'pending' | 'running' | 'done' | 'error'; message?: string }
interface LogLine   { text: string; error?: boolean }
interface Credential { label: string; value: string }
interface ManualStepItem { kind: 'note' | 'command' | 'code'; text: string }
interface ManualStep { id: string; label: string; items: ManualStepItem[] }

// ── props ─────────────────────────────────────────────────────────

const props = defineProps<{
  events: OnboardEvent[]
  projectName: string
}>()

// ── local state ───────────────────────────────────────────────────

const showBuildLog    = ref(false)
const recentCopy      = ref<string | null>(null)
const completedSteps  = ref<Set<string>>(new Set())
const buildLogEl      = ref<HTMLElement | null>(null)

// ── derived from events ───────────────────────────────────────────

const phases = computed<PhaseState[]>(() => {
  // Collect phase definitions from the `phases` event (sent first)
  const defs: PhasesDef[] = []
  for (const e of props.events) {
    if (e.type === 'phases') { defs.push(...(e.phases as PhasesDef[])); break }
  }
  if (!defs.length) return []

  // Build status map
  const status: Record<string, { status: PhaseState['status']; message?: string }> = {}
  for (const d of defs) status[d.id] = { status: 'pending' }

  for (const e of props.events) {
    if (e.type === 'phase_start') status[e.phase as string] = { status: 'running' }
    if (e.type === 'phase_done')  status[e.phase as string] = { status: 'done' }
    if (e.type === 'phase_error') status[e.phase as string] = { status: 'error', message: e.message as string }
  }

  return defs.map(d => ({ id: d.id, label: d.label, ...status[d.id] }))
})

const buildLogs = computed<LogLine[]>(() =>
  props.events
    .filter(e => e.type === 'log' && (e.phase === 'build' || currentPhase.value === 'build'))
    .map(e => ({ text: e.text as string, error: !!e.error }))
)

const currentPhase = computed(() => {
  let cur = ''
  for (const e of props.events) {
    if (e.type === 'phase_start') cur = e.phase as string
    if (e.type === 'phase_done' || e.type === 'phase_error') cur = ''
  }
  return cur
})

const generalLogs = computed<LogLine[]>(() =>
  props.events
    .filter(e => e.type === 'log' && e.phase !== 'build' && currentPhase.value !== 'build')
    .map(e => ({ text: e.text as string, error: !!e.error }))
)

const credential = computed<Credential | null>(() => {
  for (const e of props.events) {
    if (e.type === 'credential') return { label: e.label as string, value: e.value as string }
  }
  return null
})

const manualSteps = computed<ManualStep[]>(() =>
  props.events
    .filter(e => e.type === 'manual_step')
    .map(e => ({ id: e.id as string, label: e.label as string, items: e.items as ManualStepItem[] }))
)

const isDone    = computed(() => props.events.some(e => e.type === 'done'))
const isSuccess = computed(() => props.events.some(e => e.type === 'done' && e.success))
const doneUrl   = computed(() => {
  const done = props.events.find(e => e.type === 'done')
  return done?.url as string | undefined
})

// ── auto-scroll build log ─────────────────────────────────────────

watch(buildLogs, async () => {
  if (showBuildLog.value && buildLogEl.value) {
    await nextTick()
    buildLogEl.value.scrollTop = buildLogEl.value.scrollHeight
  }
})

// ── actions ───────────────────────────────────────────────────────

function copy(text: string) {
  navigator.clipboard.writeText(text).catch(() => {})
  recentCopy.value = text
  setTimeout(() => { if (recentCopy.value === text) recentCopy.value = null }, 2000)
}

function toggleStep(id: string) {
  const next = new Set(completedSteps.value)
  if (next.has(id)) next.delete(id); else next.add(id)
  completedSteps.value = next
}
</script>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: max-height 0.25s ease, opacity 0.2s ease; }
.slide-enter-from, .slide-leave-to       { max-height: 0; opacity: 0; overflow: hidden; }
.slide-enter-to, .slide-leave-from       { max-height: 500px; opacity: 1; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; transform: translateY(-6px); }
</style>
