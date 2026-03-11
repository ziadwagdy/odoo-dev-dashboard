<template>
  <div v-if="lines.length" class="card border-[#6366f1]/30 mt-4">
    <div class="flex items-center justify-between mb-2">
      <slot name="title"><span class="text-xs text-slate-400">Output</span></slot>
      <button class="btn btn-ghost btn-sm" @click="lines = []">Clear</button>
    </div>
    <pre class="log-output h-48 whitespace-pre-wrap text-xs">{{ lines.join('\n') }}</pre>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const lines = ref<string[]>([])
function append(line: string) { lines.value.push(line) }
defineExpose({ append, clear: () => (lines.value = []) })
</script>
