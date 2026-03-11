<template>
  <div class="card cursor-pointer relative overflow-hidden" @click="$router.push(`/project/${project.name}`)">
    <!-- Status strip at bottom -->
    <div class="absolute bottom-0 left-0 right-0 h-0.5"
      :class="{
        'bg-green-500': project.status === 'running',
        'bg-amber-500': project.status === 'restarting',
        'bg-red-500': !['running', 'restarting'].includes(project.status),
      }"
    />
    <div class="flex items-start justify-between mb-3">
      <div>
        <h3 class="font-semibold text-white capitalize">{{ project.name }}</h3>
        <p class="text-xs text-slate-500 mt-0.5">v{{ project.version }} · :{{ project.odoo_port }}</p>
      </div>
      <StatusBadge :status="project.status" />
    </div>
    <div class="text-xs text-slate-500 mb-3 font-mono">
      {{ project.branch || 'no branch' }}
      <span v-if="project.pending_count" class="text-amber-400 ml-2">↯ {{ project.pending_count }} pending</span>
    </div>
    <div class="flex gap-2" @click.stop>
      <a
        v-if="project.url"
        :href="'https://' + project.url"
        target="_blank"
        class="btn btn-primary btn-sm flex-1 justify-center"
        :class="{ 'opacity-50 pointer-events-none': !project.running }"
      >↗ Open</a>
      <a
        v-if="project.container_id && config.logsUrl"
        :href="config.logsUrl + '/container/' + project.container_id"
        target="_blank"
        rel="noopener"
        class="btn btn-ghost btn-sm"
        title="Dozzle logs"
      >📜</a>
      <RouterLink :to="`/project/${project.name}`" class="btn btn-ghost btn-sm flex-1 justify-center">Manage</RouterLink>
      <button class="btn btn-ghost btn-sm" @click.stop="$emit('restart', project.container)">↺</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Project } from '@/stores/projects'
import { useConfigStore } from '@/stores/config'
import StatusBadge from './StatusBadge.vue'

defineProps<{ project: Project }>()
defineEmits<{ restart: [container: string] }>()

const config = useConfigStore()
</script>
