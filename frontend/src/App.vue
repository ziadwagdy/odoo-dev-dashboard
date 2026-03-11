<template>
  <div class="min-h-screen bg-[#0f1117]">
    <!-- Notifications -->
    <div class="fixed top-4 right-4 z-50 flex flex-col gap-2">
      <TransitionGroup name="notif">
        <div
          v-for="n in notifications.items"
          :key="n.id"
          class="px-4 py-3 rounded-lg text-sm font-medium shadow-lg"
          :class="{
            'bg-green-900/80 text-green-200 border border-green-700': n.type === 'success',
            'bg-red-900/80 text-red-200 border border-red-700': n.type === 'error',
            'bg-slate-800 text-slate-200 border border-slate-700': n.type === 'info',
          }"
        >
          {{ n.message }}
        </div>
      </TransitionGroup>
    </div>
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import { useConfigStore } from '@/stores/config'

const notifications = useNotificationsStore()
const config = useConfigStore()
onMounted(() => config.init())
</script>

<style>
.notif-enter-active, .notif-leave-active { transition: all 0.3s ease; }
.notif-enter-from { opacity: 0; transform: translateX(20px); }
.notif-leave-to   { opacity: 0; transform: translateX(20px); }
</style>
