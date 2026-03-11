<template>
  <div class="card cursor-pointer relative overflow-hidden group" @click="$router.push(`/project/${project.name}`)">
    <!-- Gradient overlay on hover -->
    <div class="absolute inset-0 bg-gradient-to-br from-accent/5 to-primary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
    
    <!-- Status strip at top with glow -->
    <div class="absolute top-0 left-0 right-0 h-1 rounded-t-2xl"
      :class="{
        'bg-gradient-to-r from-emerald-500 to-green-400': project.status === 'running',
        'bg-gradient-to-r from-amber-500 to-orange-400': project.status === 'restarting',
        'bg-gradient-to-r from-red-500 to-rose-400': !['running', 'restarting'].includes(project.status),
      }"
      :style="{
        boxShadow: project.status === 'running' ? '0 0 15px rgba(16, 185, 129, 0.5)' : 
                   project.status === 'restarting' ? '0 0 15px rgba(245, 158, 11, 0.5)' : 
                   '0 0 15px rgba(239, 68, 68, 0.5)'
      }"
    />
    
    <div class="relative pt-2">
      <div class="flex items-start justify-between mb-4">
        <div class="flex-1">
          <h3 class="text-lg font-bold text-white capitalize mb-1 group-hover:text-accent-light transition-colors">
            {{ project.name }}
          </h3>
          <div class="flex items-center gap-2 text-xs text-slate-400">
            <span class="px-2 py-0.5 bg-surface-hover rounded-md font-mono font-semibold">v{{ project.version }}</span>
            <span class="text-slate-600">·</span>
            <span class="font-mono">:{{ project.odoo_port }}</span>
          </div>
        </div>
        <StatusBadge :status="project.status" />
      </div>
      
      <!-- Branch info -->
      <div class="mb-4 px-3 py-2 bg-bg-secondary/50 rounded-lg border border-border/50">
        <div class="flex items-center gap-2 text-xs">
          <svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"></path>
          </svg>
          <span class="font-mono text-slate-300 flex-1">{{ project.branch || 'no branch' }}</span>
          <span v-if="project.pending_count" class="flex items-center gap-1 text-amber-400 font-semibold">
            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"></path>
            </svg>
            {{ project.pending_count }}
          </span>
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
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
          </svg>
          Open
        </a>
        <a
          v-if="project.container_id && config.logsUrl"
          :href="config.logsUrl + '/container/' + project.container_id"
          target="_blank"
          rel="noopener"
          class="btn btn-ghost btn-sm"
          title="View logs"
        >
          📜
        </a>
        <RouterLink :to="`/project/${project.name}`" class="btn btn-ghost btn-sm flex-1">
          Manage
        </RouterLink>
        <button class="btn btn-ghost btn-sm hover:border-accent hover:text-accent" @click.stop="$emit('restart', project.container)" title="Restart container">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
          </svg>
        </button>
      </div>
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
