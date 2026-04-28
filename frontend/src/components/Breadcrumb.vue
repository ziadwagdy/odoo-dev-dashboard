<template>
  <nav class="flex items-center gap-1.5 text-xs text-slate-500">
    <RouterLink to="/" class="hover:text-slate-300 transition-colors">Dashboard</RouterLink>
    <template v-for="(crumb, i) in crumbs" :key="i">
      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
      </svg>
      <RouterLink v-if="crumb.to" :to="crumb.to" class="hover:text-slate-300 transition-colors">
        {{ crumb.label }}
      </RouterLink>
      <span v-else class="text-slate-300 font-medium">{{ crumb.label }}</span>
    </template>
  </nav>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{
  crumbs?: Array<{ label: string; to?: string }>
}>()
</script>
