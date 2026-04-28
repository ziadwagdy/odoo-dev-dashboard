<template>
  <div>
    <div class="space-y-3 mb-6 max-h-96 overflow-y-auto">
      <div
        v-for="(line, idx) in lines"
        :key="idx"
        class="p-3 rounded-lg text-sm font-mono"
        :class="line.error   ? 'bg-red-500/10 text-red-400 border border-red-500/30' :
                line.success ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' :
                line.warning ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
                'bg-surface-hover text-slate-300'"
      >{{ line.text }}</div>
    </div>
    <div v-if="!complete" class="text-center py-4">
      <div class="inline-block w-8 h-8 border-3 border-accent/30 border-t-accent rounded-full animate-spin"></div>
      <p class="text-sm text-slate-400 mt-3">Please wait...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  lines:    Array<{ text: string; error?: boolean; success?: boolean; warning?: boolean }>
  complete: boolean
  hasError: boolean
}>()
</script>
