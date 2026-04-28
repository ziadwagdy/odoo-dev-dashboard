import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('auth_token') || '')
  const username = ref<string>(localStorage.getItem('auth_user') || '')
  const role = ref<string>(localStorage.getItem('auth_role') || '')

  const isAuthenticated  = computed(() => !!token.value)
  const isAdmin          = computed(() => role.value === 'admin')
  const isManager        = computed(() => role.value === 'manager')
  // Capabilities derived from role
  const canSwitchBranch  = computed(() => role.value === 'admin' || role.value === 'manager')
  const canDelete        = computed(() => role.value === 'admin')
  const canManageUsers   = computed(() => role.value === 'admin')
  const canOnboard       = computed(() => role.value === 'admin' || role.value === 'manager')

  async function login(usernameInput: string, password: string): Promise<string | null> {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: usernameInput, password }),
    })
    const data = await res.json()
    if (!res.ok) return data.error || 'Login failed'

    token.value = data.token
    username.value = data.username
    role.value = data.role
    localStorage.setItem('auth_token', data.token)
    localStorage.setItem('auth_user', data.username)
    localStorage.setItem('auth_role', data.role)
    return null
  }

  async function logout() {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { Authorization: `Token ${token.value}` },
      })
    } catch { /* ignore */ }
    token.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_role')
  }

  return { token, username, role, isAuthenticated, isAdmin, isManager, canSwitchBranch, canDelete, canManageUsers, canOnboard, login, logout }
})
