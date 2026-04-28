<template>
  <div class="min-h-screen bg-bg flex items-center justify-center px-4">
    <!-- Background gradient -->
    <div class="fixed inset-0 pointer-events-none">
      <div class="absolute inset-0" style="background: radial-gradient(ellipse at 20% 50%, rgba(113,75,103,0.15) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(162,70,137,0.1) 0%, transparent 50%)"></div>
    </div>

    <div class="w-full max-w-sm relative">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="w-12 h-12 mx-auto rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center mb-4 shadow-lg" style="box-shadow: 0 0 30px rgba(162,70,137,0.4)">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </div>
        <h1 class="text-xl font-bold text-slate-100">{{ config.dashboardTitle || 'Dev Dashboard' }}</h1>
        <p class="text-sm text-slate-500 mt-1">Sign in to continue</p>
      </div>

      <!-- Login card -->
      <div class="card p-6">
        <form @submit.prevent="submit" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Username</label>
            <input
              v-model="username"
              type="text"
              autocomplete="username"
              class="input w-full"
              placeholder="Enter username"
              :disabled="loading"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Password</label>
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              class="input w-full"
              placeholder="Enter password"
              :disabled="loading"
            />
          </div>

          <div v-if="error" class="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
            {{ error }}
          </div>

          <button
            type="submit"
            class="btn btn-primary w-full justify-center"
            :disabled="loading"
          >
            <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <span>{{ loading ? 'Signing in…' : 'Sign in' }}</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'

const auth = useAuthStore()
const config = useConfigStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const err = await auth.login(username.value, password.value)
    if (err) {
      error.value = err
    } else {
      const redirect = (route.query.redirect as string) || '/'
      router.push(redirect)
    }
  } finally {
    loading.value = false
  }
}
</script>
