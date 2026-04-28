<template>
  <div class="relative" ref="dropdown">
    <button
      @click="open = !open"
      class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-surface-hover transition-colors"
    >
      <!-- Avatar initials -->
      <div class="w-6 h-6 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-[10px] font-bold text-white uppercase">
        {{ auth.username.charAt(0) }}
      </div>
      <div class="hidden md:block text-left">
        <p class="text-xs font-medium text-slate-200 leading-none">{{ auth.username }}</p>
        <p class="text-[10px] text-slate-500 leading-none mt-0.5 capitalize">{{ auth.role }}</p>
      </div>
      <svg class="w-3 h-3 text-slate-500 hidden md:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
      </svg>
    </button>

    <!-- Dropdown -->
    <Transition name="dropdown">
      <div v-if="open"
        class="absolute right-0 top-full mt-1 w-44 bg-surface border border-border rounded-xl shadow-2xl z-50 overflow-hidden">
        <div class="px-3 py-2.5 border-b border-border">
          <p class="text-xs font-semibold text-slate-200">{{ auth.username }}</p>
          <p class="text-[10px] text-slate-500 capitalize">{{ auth.role }}</p>
        </div>
        <button
          @click="doLogout"
          class="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
          </svg>
          Sign out
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const open = ref(false)
const dropdown = ref<HTMLElement | null>(null)

async function doLogout() {
  await auth.logout()
  router.push('/login')
}

function onClickOutside(e: MouseEvent) {
  if (dropdown.value && !dropdown.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside, true))
onUnmounted(() => document.removeEventListener('click', onClickOutside, true))
</script>

<style scoped>
.dropdown-enter-active, .dropdown-leave-active { transition: all 0.15s ease; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
