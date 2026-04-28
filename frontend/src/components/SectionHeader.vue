<template>
  <div class="flex items-center gap-3 mb-4">
    <span class="w-2.5 h-2.5 rounded-sm bg-gradient-to-br from-primary to-accent shrink-0" />
    <h2 class="text-sm font-bold uppercase tracking-widest text-slate-200">{{ title }}</h2>
    <div class="h-px flex-1 bg-gradient-to-r from-accent/30 to-transparent" />
    <span v-if="count !== undefined"
      class="text-[11px] px-2 py-0.5 rounded-full bg-surface-hover border border-border text-slate-400 font-semibold tabular-nums"
    >{{ count }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; count?: number }>()
</script>
