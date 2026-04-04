<template>
  <div class="card relative overflow-hidden group cursor-pointer" @click="$router.push(`/project/${project.name}`)">
    <!-- Status glow strip -->
    <div class="absolute top-0 left-0 right-0 h-0.5 rounded-t-2xl"
      :class="{
        'bg-gradient-to-r from-emerald-500 to-green-400': project.status === 'running',
        'bg-gradient-to-r from-amber-500 to-orange-400': project.status === 'restarting',
        'bg-gradient-to-r from-red-500 to-rose-400': !['running','restarting'].includes(project.status),
      }"
    />
    <div class="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

    <div class="relative pt-1">
      <!-- Header -->
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2 min-w-0">
          <h3 class="text-base font-bold text-white capitalize truncate group-hover:text-accent-light transition-colors">
            {{ project.name }}
          </h3>
          <span class="px-1.5 py-0.5 bg-surface-hover rounded text-[10px] font-mono font-semibold text-slate-400 flex-shrink-0">
            v{{ project.version }}
          </span>
        </div>
        <StatusBadge :status="project.status" />
      </div>

      <!-- Environment rows (read-only) -->
      <div class="mb-4 rounded-xl border border-border/50 overflow-hidden" @click.stop>
        <div
          v-for="env in ENV_DEFS"
          :key="env.type"
          class="grid grid-cols-[80px_1fr_auto] gap-x-2 items-center px-3 py-2 border-b border-border/40 last:border-b-0"
          :class="isActive(env.type) ? env.activeBg : ''"
        >
          <!-- Label -->
          <div class="flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
              :class="isActive(env.type) ? env.dotActive : 'bg-slate-700'" />
            <span class="text-[10px] font-bold uppercase tracking-widest"
              :class="isActive(env.type) ? env.labelColor : 'text-slate-600'">
              {{ env.label }}
            </span>
          </div>

          <!-- Info -->
          <div class="min-w-0 space-y-0.5">
            <div v-if="getSlot(env.type).branch || getSlot(env.type).db" class="flex items-center gap-1.5 flex-wrap">
              <span v-if="getSlot(env.type).branch" class="font-mono text-[11px] text-slate-400 truncate max-w-[100px]">
                {{ getSlot(env.type).branch }}
              </span>
              <span v-if="getSlot(env.type).branch && getSlot(env.type).db" class="text-slate-700 text-[10px]">·</span>
              <span v-if="getSlot(env.type).db" class="font-mono text-[11px] text-slate-500 truncate max-w-[100px]">
                {{ getSlot(env.type).db }}
              </span>
            </div>
            <div v-else class="text-[11px] text-slate-700 italic">not configured</div>
          </div>

          <!-- Active pill -->
          <span v-if="isActive(env.type)" class="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full flex-shrink-0"
            :class="env.activePill">active</span>
          <!-- Open link if running and has db -->
          <a
            v-else-if="getSlot(env.type).db && project.running"
            :href="`https://${project.url}/web?db=${getSlot(env.type).db}`"
            target="_blank"
            class="p-1 rounded text-slate-700 hover:text-sky-400 transition-colors"
            title="Open database"
            @click.stop
          >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
          </a>
          <span v-else />
        </div>

        <!-- Not configured hint -->
        <div
          v-if="!hasAnyEnv"
          class="flex items-center justify-center gap-1.5 px-3 py-2 text-[11px] text-slate-600"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          Configure in Manage → Environments
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-2" @click.stop>
        <a
          v-if="project.url"
          :href="'https://' + project.url"
          target="_blank"
          class="btn btn-primary btn-sm flex-1"
          :class="{ 'opacity-40 pointer-events-none': !project.running }"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
          </svg>
          Open
        </a>
        <a
          v-if="project.container_id && config.logsUrl"
          :href="config.logsUrl + '/container/' + project.container_id"
          target="_blank"
          rel="noopener"
          class="btn btn-ghost btn-sm p-2"
          title="Container logs"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        </a>
        <RouterLink :to="`/project/${project.name}`" class="btn btn-ghost btn-sm flex-1">Manage</RouterLink>
        <button
          class="btn btn-ghost btn-sm hover:border-accent hover:text-accent"
          title="Restart"
          @click.stop="$emit('restart', project.container)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { Project, EnvSlot } from '@/stores/projects'
import { useConfigStore } from '@/stores/config'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{ project: Project }>()
defineEmits<{ restart: [container: string] }>()

const config = useConfigStore()

const ENV_DEFS = [
  {
    type: 'production' as const, label: 'Prod',
    dotActive: 'bg-emerald-500', labelColor: 'text-emerald-400',
    activeBg: 'bg-emerald-500/5', activePill: 'bg-emerald-500/20 text-emerald-400',
  },
  {
    type: 'staging' as const, label: 'Stage',
    dotActive: 'bg-amber-500', labelColor: 'text-amber-400',
    activeBg: 'bg-amber-500/5', activePill: 'bg-amber-500/20 text-amber-400',
  },
  {
    type: 'dev' as const, label: 'Dev',
    dotActive: 'bg-sky-500', labelColor: 'text-sky-400',
    activeBg: 'bg-sky-500/5', activePill: 'bg-sky-500/20 text-sky-400',
  },
] as const

function getSlot(type: 'production' | 'staging' | 'dev'): EnvSlot {
  return props.project.environments?.[type] ?? { branch: '', db: '' }
}

function isActive(type: 'production' | 'staging' | 'dev'): boolean {
  const b = getSlot(type).branch
  return !!b && b === props.project.branch
}

const hasAnyEnv = computed(() =>
  (['production', 'staging', 'dev'] as const).some(t => getSlot(t).branch || getSlot(t).db)
)
</script>
