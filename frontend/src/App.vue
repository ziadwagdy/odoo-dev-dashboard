<template>
  <div class="min-h-screen bg-bg">
    <!-- Notifications -->
    <div class="fixed top-6 right-6 z-50 flex flex-col gap-3 max-w-md">
      <TransitionGroup name="notif">
        <div
          v-for="n in notifications.items"
          :key="n.id"
          class="px-5 py-4 rounded-2xl text-sm font-semibold shadow-2xl backdrop-blur-xl"
          :class="{
            'bg-gradient-to-r from-emerald-500/20 to-green-500/20 text-emerald-100 border-2 border-emerald-500/50': n.type === 'success',
            'bg-gradient-to-r from-red-500/20 to-rose-500/20 text-red-100 border-2 border-red-500/50': n.type === 'error',
            'bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-100 border-2 border-purple-500/50': n.type === 'info',
          }"
          :style="{
            boxShadow: n.type === 'success' ? '0 10px 40px rgba(16, 185, 129, 0.3)' :
                       n.type === 'error' ? '0 10px 40px rgba(239, 68, 68, 0.3)' :
                       '0 10px 40px rgba(162, 70, 137, 0.3)'
          }"
        >
          <div class="flex items-center gap-3">
            <span class="text-lg">
              {{ n.type === 'success' ? '✓' : n.type === 'error' ? '✕' : 'ℹ' }}
            </span>
            <span>{{ n.message }}</span>
          </div>
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
.notif-enter-active, .notif-leave-active { 
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.notif-enter-from { 
  opacity: 0; 
  transform: translateX(30px) scale(0.9);
}
.notif-leave-to { 
  opacity: 0; 
  transform: translateX(30px) scale(0.9);
}
</style>
