<template>
  <span class="badge" :class="`badge-${status}`">
    <span class="dot" :class="dotClass" />
    {{ status }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const dotClass = computed(() => {
  if (props.status === 'running') return 'dot-green'
  if (props.status === 'restarting') return 'dot-amber pulse'
  return 'dot-red'
})
</script>
