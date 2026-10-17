<template>
  <div class="flex h-screen overflow-hidden bg-bg">

    <!-- ── Mobile backdrop ───────────────────────────────────────── -->
    <Transition name="backdrop">
      <div
        v-if="mobileOpen"
        class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
        @click="mobileOpen = false"
      />
    </Transition>

    <!-- ── Sidebar ───────────────────────────────────────────────── -->
    <!-- On desktop: static column. On mobile: fixed overlay from left. -->
    <div
      class="fixed inset-y-0 left-0 z-50 lg:static lg:z-auto
             w-64 lg:w-56 shrink-0
             transform transition-transform duration-300 ease-in-out
             lg:transform-none"
      :class="mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'"
    >
      <Sidebar />
    </div>

    <!-- ── Main area ─────────────────────────────────────────────── -->
    <div class="flex flex-col flex-1 min-w-0 overflow-hidden">

      <!-- Top header bar -->
      <header class="relative z-30 flex items-center gap-3 px-4 md:px-6 py-3 border-b border-border bg-surface/60 backdrop-blur-sm shrink-0">

        <!-- Hamburger — mobile only -->
        <button
          class="lg:hidden flex items-center justify-center w-9 h-9 rounded-xl hover:bg-white/5 transition-colors shrink-0"
          :style="{ color: 'rgb(var(--t-sec))' }"
          @click="mobileOpen = !mobileOpen"
          aria-label="Toggle sidebar"
        >
          <svg v-if="!mobileOpen" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>

        <!-- Breadcrumb -->
        <div class="flex-1 min-w-0">
          <slot name="breadcrumb" />
        </div>

        <!-- Right controls -->
        <div class="flex items-center gap-2 md:gap-4 shrink-0">
          <!-- Live indicator -->
          <span v-if="store.lastUpdated" class="hidden md:flex items-center gap-1.5 text-xs text-emerald-400">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span class="hidden lg:inline">Live ·</span> {{ store.lastUpdated.toLocaleTimeString() }}
          </span>

          <!-- Theme toggle -->
          <button
            class="flex items-center gap-1.5 px-2 h-8 rounded-lg hover:bg-white/5 transition-colors text-xs font-medium shrink-0"
            :style="{ color: themeStore.theme === 'system' ? 'rgb(var(--t-sec))' : themeStore.theme === 'light' ? '#d97706' : '#94a3b8' }"
            :title="`Theme: ${themeStore.theme} — click to cycle`"
            @click="themeStore.toggle()"
          >
            <!-- System: monitor -->
            <svg v-if="themeStore.theme === 'system'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
            <!-- Light: sun -->
            <svg v-else-if="themeStore.theme === 'light'" class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"/>
            </svg>
            <!-- Dark: moon -->
            <svg v-else class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"/>
            </svg>
            <span class="capitalize hidden md:inline">{{ themeStore.theme }}</span>
          </button>

          <UserBadge />
        </div>
      </header>

      <!-- Main content -->
      <main class="flex-1 overflow-y-auto px-4 md:px-6 py-4 md:py-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import UserBadge from '@/components/UserBadge.vue'
import { useProjectsStore } from '@/stores/projects'
import { useThemeStore } from '@/stores/theme'

const store = useProjectsStore()
const themeStore = useThemeStore()
const route = useRoute()

const mobileOpen = ref(false)

// Close mobile sidebar on navigation
watch(() => route.fullPath, () => { mobileOpen.value = false })
</script>

<style scoped>
.backdrop-enter-active,
.backdrop-leave-active { transition: opacity 0.25s ease; }
.backdrop-enter-from,
.backdrop-leave-to    { opacity: 0; }
</style>
