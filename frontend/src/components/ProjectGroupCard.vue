<template>
  <div class="card overflow-hidden">
    <!-- Card top: group name + version badge -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <h3 class="text-base font-bold text-white capitalize">{{ group.name }}</h3>
        <span v-if="versionBadge" class="px-1.5 py-0.5 bg-surface-hover rounded text-[10px] font-mono font-semibold text-slate-400">
          v{{ versionBadge }}
        </span>
      </div>
      <span class="text-[10px] font-bold uppercase tracking-widest text-slate-500 px-2 py-1 rounded border border-border/50">
        Group
      </span>
    </div>

    <!-- 3-column environment grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-border/50 rounded-xl border border-border/50 overflow-hidden">
      <div v-for="env in ENV_DEFS" :key="env.type" class="flex flex-col">
        <!-- Colored top strip -->
        <div class="h-0.5" :class="env.strip" />

        <!-- Column header -->
        <div class="flex items-center justify-between px-3 pt-2 pb-1.5">
          <div class="flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :class="env.dot" />
            <span class="text-[10px] font-bold uppercase tracking-widest" :class="env.label">
              {{ env.type }}
            </span>
          </div>
          <StatusBadge v-if="group.instances[env.type]" :status="group.instances[env.type]!.status" />
          <span v-else class="text-[10px] text-slate-600 italic">—</span>
        </div>

        <!-- Body: instance configured -->
        <div v-if="group.instances[env.type]" class="px-3 pb-2 flex-1 flex flex-col gap-1.5">
          <!-- Instance name -->
          <div class="font-mono text-[11px] text-slate-500 truncate">
            {{ group.instances[env.type]!.name }}
          </div>

          <!-- Branch -->
          <div v-if="group.instances[env.type]!.branch" class="flex items-center gap-1 text-[11px] text-slate-400">
            <svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M8 7h.01M8 12h.01M8 17h.01M16 7a4 4 0 010 8v2a2 2 0 01-2 2H6a2 2 0 01-2-2V5a2 2 0 012-2h8a4 4 0 010 8z"/>
            </svg>
            <span class="truncate font-mono">{{ group.instances[env.type]!.branch }}</span>
          </div>

          <!-- Port -->
          <div class="flex items-center gap-2 text-[11px] text-slate-500">
            <span class="font-mono">:{{ group.instances[env.type]!.odoo_port }}</span>
            <span v-if="group.instances[env.type]!.db_port !== group.instances[env.type]!.odoo_port"
              class="font-mono text-slate-600">db:{{ group.instances[env.type]!.db_port }}</span>
          </div>

          <!-- Action buttons -->
          <div class="flex flex-wrap gap-1 mt-auto pt-1">
            <a
              v-if="group.instances[env.type]!.url"
              :href="'https://' + group.instances[env.type]!.url"
              target="_blank"
              rel="noopener"
              class="btn btn-primary btn-sm flex-1 text-[11px]"
              :class="{ 'opacity-40 pointer-events-none': !group.instances[env.type]!.running }"
            >
              Open ↗
            </a>
            <a
              v-if="group.instances[env.type]!.container_id && config.logsUrl"
              :href="config.logsUrl + '/container/' + group.instances[env.type]!.container_id"
              target="_blank"
              rel="noopener"
              class="btn btn-ghost btn-sm p-1.5"
              title="Logs"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
            </a>
            <RouterLink
              :to="`/project/${group.instances[env.type]!.name}`"
              class="btn btn-ghost btn-sm flex-1 text-[11px]"
            >
              Manage →
            </RouterLink>
            <button
              class="btn btn-ghost btn-sm p-1.5"
              title="Deploy"
              :disabled="deploying[env.type]"
              @click="deployInstance(env.type)"
            >
              <svg v-if="deploying[env.type]" class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
              </svg>
            </button>
            <button
              class="btn btn-ghost btn-sm p-1.5"
              title="Restart"
              @click="$emit('restart', group.instances[env.type]!.container)"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Body: instance not configured -->
        <div v-else class="px-3 pb-3 flex-1 flex flex-col justify-center gap-1">
          <p class="text-[12px] text-slate-600 italic">— no instance —</p>
          <p class="text-[10px] text-slate-700">Add an instance in registry then configure below</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { RouterLink } from 'vue-router'
import type { ProjectGroup } from '@/stores/projects'
import { useConfigStore } from '@/stores/config'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{ group: ProjectGroup }>()
const emit = defineEmits<{ restart: [container: string] }>()

const config = useConfigStore()

const ENV_DEFS = [
  {
    type: 'production' as const,
    strip: 'bg-gradient-to-r from-emerald-500 to-green-400',
    dot: 'bg-emerald-500',
    label: 'text-emerald-400',
  },
  {
    type: 'staging' as const,
    strip: 'bg-gradient-to-r from-amber-500 to-orange-400',
    dot: 'bg-amber-500',
    label: 'text-amber-400',
  },
  {
    type: 'dev' as const,
    strip: 'bg-gradient-to-r from-sky-500 to-blue-400',
    dot: 'bg-sky-500',
    label: 'text-sky-400',
  },
] as const

const deploying = reactive<Record<string, boolean>>({
  production: false,
  staging: false,
  dev: false,
})

const versionBadge = computed(() => {
  for (const env of ['production', 'staging', 'dev'] as const) {
    const inst = props.group.instances[env]
    if (inst) return inst.version
  }
  return null
})

async function deployInstance(envType: 'production' | 'staging' | 'dev') {
  const inst = props.group.instances[envType]
  if (!inst) return
  deploying[envType] = true
  try {
    await fetch(`/api/project/${inst.name}/deploy`, { method: 'POST' })
  } finally {
    deploying[envType] = false
  }
}
</script>
