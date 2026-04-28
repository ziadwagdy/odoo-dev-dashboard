<template>
  <SidebarLayout>
    <template #breadcrumb>
      <Breadcrumb :crumbs="[{ label: 'Users & Roles' }]" />
    </template>

    <div class="max-w-5xl">

      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-lg font-bold text-slate-100">Users & Roles</h1>
          <p class="text-xs mt-0.5" style="color:rgb(var(--t-muted))">{{ users.length }} member{{ users.length !== 1 ? 's' : '' }}</p>
        </div>
        <button class="btn btn-primary" @click="showCreate = true">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Add User
        </button>
      </div>

      <!-- Users table -->
      <div class="card !p-0 overflow-hidden">
        <table class="table-base w-full">
          <thead>
            <tr>
              <th class="pl-5">User</th>
              <th>Role</th>
              <th>Projects</th>
              <th>Last Login</th>
              <th class="text-right pr-5">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="text-center py-10" style="color:rgb(var(--t-muted))">
                <div class="flex items-center justify-center gap-2 text-sm">
                  <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
                  Loading…
                </div>
              </td>
            </tr>
            <tr v-else-if="!users.length">
              <td colspan="5" class="text-center py-10 text-sm" style="color:rgb(var(--t-muted))">No users found</td>
            </tr>
            <tr v-for="u in users" :key="u.id">
              <!-- User -->
              <td class="pl-5">
                <div class="flex items-center gap-3">
                  <div
                    class="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold text-white uppercase shrink-0"
                    :class="{
                      'bg-gradient-to-br from-accent to-primary': u.role === 'admin',
                      'bg-gradient-to-br from-blue-500 to-indigo-600': u.role === 'manager',
                      'bg-gradient-to-br from-emerald-500 to-teal-600': u.role === 'developer',
                    }"
                  >{{ u.username.charAt(0) }}</div>
                  <div>
                    <div class="flex items-center gap-1.5">
                      <span class="text-sm font-semibold text-slate-200">{{ u.username }}</span>
                      <span v-if="u.username === auth.username" class="px-1.5 py-px rounded-md text-[10px] font-medium bg-accent/15 text-accent-lt border border-accent/20">you</span>
                    </div>
                  </div>
                </div>
              </td>

              <!-- Role -->
              <td>
                <select
                  :value="u.role"
                  :disabled="u.username === auth.username"
                  class="text-xs font-semibold rounded-lg px-2.5 py-1.5 border cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent/30 transition-all disabled:opacity-60 disabled:cursor-default"
                  :class="{
                    'bg-accent/10 text-accent-lt border-accent/30 hover:bg-accent/20': u.role === 'admin',
                    'bg-blue-500/10 text-blue-300 border-blue-500/30 hover:bg-blue-500/20': u.role === 'manager',
                    'bg-emerald-500/10 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/20': u.role === 'developer',
                  }"
                  style="background-image: none;"
                  @change="updateRole(u.id, ($event.target as HTMLSelectElement).value)"
                >
                  <option value="admin">admin</option>
                  <option value="manager">manager</option>
                  <option value="developer">developer</option>
                </select>
              </td>

              <!-- Projects -->
              <td>
                <button
                  v-if="u.role !== 'admin'"
                  class="flex items-center gap-1.5 text-xs rounded-lg px-2.5 py-1.5 border border-border/60 hover:border-accent/40 hover:bg-accent/10 transition-all"
                  style="color:rgb(var(--t-sec))"
                  :title="`Manage project access for ${u.username}`"
                  @click="openAssign(u)"
                >
                  <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                  </svg>
                  <span class="font-mono font-semibold text-slate-300">{{ u.assigned_projects.length }}</span>
                  <span>project{{ u.assigned_projects.length !== 1 ? 's' : '' }}</span>
                </button>
                <span v-else class="text-xs px-2.5 py-1.5 rounded-lg border border-accent/20 bg-accent/5 text-accent-lt/70 font-medium">all</span>
              </td>

              <!-- Last Login -->
              <td>
                <span v-if="u.last_login" class="text-xs" style="color:rgb(var(--t-sec))">{{ new Date(u.last_login).toLocaleDateString(undefined, { month:'short', day:'numeric', year:'numeric' }) }}</span>
                <span v-else class="text-xs" style="color:rgb(var(--t-dim))">Never</span>
              </td>

              <!-- Actions -->
              <td class="pr-5">
                <div class="flex items-center justify-end gap-1">
                  <!-- Change password -->
                  <button
                    class="w-8 h-8 rounded-lg flex items-center justify-center border border-transparent hover:border-border hover:bg-surface-hover/50 transition-all"
                    style="color:rgb(var(--t-muted))"
                    title="Change password"
                    @click="openChangePassword(u)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>
                    </svg>
                  </button>
                  <!-- Delete -->
                  <button
                    v-if="u.username !== auth.username"
                    class="w-8 h-8 rounded-lg flex items-center justify-center border border-transparent hover:border-red-800/60 hover:bg-red-900/20 text-red-500/50 hover:text-red-400 transition-all"
                    title="Delete user"
                    @click="removeUser(u)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                  </button>
                  <div v-else class="w-8 h-8" />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- System audit log -->
      <div class="card !p-0 mt-6 overflow-hidden">
        <div class="px-5 py-4 border-b border-border/40">
          <h2 class="text-sm font-semibold text-slate-300">System Audit Log</h2>
        </div>
        <div v-if="systemAudit.length === 0" class="text-sm py-8 text-center" style="color:rgb(var(--t-muted))">No system audit events yet.</div>
        <div v-else class="overflow-x-auto">
          <table class="table-base w-full min-w-[520px]">
            <thead>
              <tr>
                <th class="pl-5">Time</th>
                <th>By</th>
                <th>Action</th>
                <th>Detail</th>
                <th class="pr-5">Outcome</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in systemAudit" :key="a.id">
                <td class="pl-5 text-xs whitespace-nowrap" style="color:rgb(var(--t-muted))">{{ new Date(a.triggered_at).toLocaleString() }}</td>
                <td class="text-xs font-medium text-slate-400">{{ a.user || '—' }}</td>
                <td>
                  <span class="px-2 py-0.5 rounded-md text-[11px] font-mono font-medium"
                    :class="{
                      'bg-blue-500/15 text-blue-300 border border-blue-500/20': a.action === 'user_create',
                      'bg-red-500/15 text-red-300 border border-red-500/20': a.action === 'user_delete',
                      'bg-amber-500/15 text-amber-300 border border-amber-500/20': a.action === 'password_change',
                      'bg-purple-500/15 text-purple-300 border border-purple-500/20': a.action === 'user_role_change',
                      'bg-accent/10 text-accent-lt border border-accent/20': a.action === 'user_projects_assign',
                      'bg-slate-500/10 text-slate-400 border border-slate-600/30': !['user_create','user_delete','password_change','user_role_change','user_projects_assign'].includes(a.action),
                    }">{{ a.action }}</span>
                </td>
                <td class="text-xs max-w-[200px] truncate" style="color:rgb(var(--t-sec))" :title="a.detail">{{ a.detail || '—' }}</td>
                <td class="pr-5">
                  <div class="flex items-center gap-1.5 text-xs">
                    <span :class="a.outcome === 'success' ? 'text-emerald-400' : 'text-red-400'">
                      <svg v-if="a.outcome === 'success'" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
                      <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/></svg>
                    </span>
                    <span :class="a.outcome === 'success' ? 'text-emerald-400' : 'text-red-400'">{{ a.outcome }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Create user modal -->
      <Teleport to="body">
        <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div class="card w-full max-w-sm p-6">
            <h2 class="text-base font-bold text-slate-100 mb-4">Add User</h2>
            <form @submit.prevent="createUser" class="space-y-3">
              <div>
                <label class="block text-xs font-medium text-slate-400 mb-1">Username</label>
                <input v-model="newUser.username" class="input w-full" placeholder="username" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-400 mb-1">Password</label>
                <input v-model="newUser.password" type="password" class="input w-full" placeholder="password" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-400 mb-1">Role</label>
                <select v-model="newUser.role" class="input w-full">
                  <option value="developer">developer</option>
                  <option value="manager">manager</option>
                  <option value="admin">admin</option>
                </select>
              </div>
              <div v-if="createError" class="text-xs text-red-400 px-2">{{ createError }}</div>
              <div class="flex gap-2 pt-1">
                <button type="submit" class="btn btn-primary flex-1 justify-center">Create</button>
                <button type="button" class="btn btn-ghost flex-1 justify-center" @click="showCreate = false">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      </Teleport>

      <!-- Assign projects modal -->
      <Teleport to="body">
        <div v-if="assignTarget" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div class="card w-full max-w-sm p-6">
            <div class="flex items-center gap-3 mb-4">
              <div
                class="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold text-white uppercase"
                :class="{
                  'bg-gradient-to-br from-blue-500 to-indigo-600': assignTarget.role === 'manager',
                  'bg-gradient-to-br from-emerald-500 to-teal-600': assignTarget.role === 'developer',
                }"
              >{{ assignTarget.username.charAt(0) }}</div>
              <div>
                <h2 class="text-base font-bold text-slate-100">Project Access</h2>
                <p class="text-xs" style="color:rgb(var(--t-muted))">{{ assignTarget.username }}</p>
              </div>
            </div>
            <div class="space-y-0.5 max-h-64 overflow-y-auto -mx-1 mb-4">
              <label
                v-for="name in allProjectNames"
                :key="name"
                class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface-hover/50 cursor-pointer transition-colors"
              >
                <input
                  type="checkbox"
                  :checked="selectedProjects.has(name)"
                  class="accent-primary w-3.5 h-3.5 shrink-0"
                  @change="toggleProject(name)"
                />
                <span class="text-sm font-mono text-slate-300">{{ name }}</span>
              </label>
              <p v-if="!allProjectNames.length" class="text-xs py-4 text-center" style="color:rgb(var(--t-muted))">Loading projects…</p>
            </div>
            <div class="flex gap-2 pt-1 border-t border-border/40">
              <button class="btn btn-primary flex-1 justify-center mt-3" :disabled="assignSaving" @click="saveAssign">
                {{ assignSaving ? 'Saving…' : 'Save' }}
              </button>
              <button class="btn btn-ghost flex-1 justify-center mt-3" @click="assignTarget = null">Cancel</button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Change password modal -->
      <Teleport to="body">
        <div v-if="changePwUser" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div class="card w-full max-w-sm p-6">
            <div class="flex items-center gap-3 mb-4">
              <div
                class="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold text-white uppercase"
                :class="{
                  'bg-gradient-to-br from-accent to-primary': changePwUser.role === 'admin',
                  'bg-gradient-to-br from-blue-500 to-indigo-600': changePwUser.role === 'manager',
                  'bg-gradient-to-br from-emerald-500 to-teal-600': changePwUser.role === 'developer',
                }"
              >{{ changePwUser.username.charAt(0) }}</div>
              <div>
                <h2 class="text-base font-bold text-slate-100">Change Password</h2>
                <p class="text-xs" style="color:rgb(var(--t-muted))">{{ changePwUser.username }}</p>
              </div>
            </div>
            <form @submit.prevent="submitChangePassword" class="space-y-3">
              <div>
                <label class="block text-xs font-medium text-slate-400 mb-1">New Password</label>
                <input v-model="newPassword" type="password" class="input w-full" placeholder="min 6 characters" />
              </div>
              <div v-if="changePwError" class="text-xs text-red-400 px-2">{{ changePwError }}</div>
              <div class="flex gap-2 pt-1">
                <button type="submit" class="btn btn-primary flex-1 justify-center">Update</button>
                <button type="button" class="btn btn-ghost flex-1 justify-center" @click="changePwUser = null">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      </Teleport>

    </div>
  </SidebarLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { api } from '@/api'
import SidebarLayout from '@/layouts/SidebarLayout.vue'
import Breadcrumb from '@/components/Breadcrumb.vue'

const auth = useAuthStore()
const notify = useNotificationsStore()

interface UserEntry { id: number; username: string; role: string; last_login: string | null; assigned_projects: string[] }
interface AuditEntry { id: number; triggered_at: string; action: string; detail: string; outcome: string; user: string }

const users = ref<UserEntry[]>([])
const systemAudit = ref<AuditEntry[]>([])
const loading = ref(false)
const showCreate = ref(false)
const createError = ref('')
const newUser = ref({ username: '', password: '', role: 'developer' })

const changePwUser = ref<UserEntry | null>(null)
const newPassword = ref('')
const changePwError = ref('')

const assignTarget = ref<UserEntry | null>(null)
const allProjectNames = ref<string[]>([])
const selectedProjects = ref<Set<string>>(new Set())
const assignSaving = ref(false)

function openChangePassword(u: UserEntry) {
  changePwUser.value = u
  newPassword.value = ''
  changePwError.value = ''
}

async function openAssign(u: UserEntry) {
  assignTarget.value = u
  selectedProjects.value = new Set(u.assigned_projects)
  if (!allProjectNames.value.length) {
    const res = await api('/api/status')
    const data = await res.json()
    allProjectNames.value = (data.projects || []).map((p: { name: string }) => p.name)
  }
}

async function saveAssign() {
  if (!assignTarget.value) return
  assignSaving.value = true
  const res = await api(`/api/auth/users/${assignTarget.value.id}/projects`, {
    method: 'POST',
    body: JSON.stringify({ projects: [...selectedProjects.value] }),
  })
  assignSaving.value = false
  if (res.ok) {
    assignTarget.value.assigned_projects = [...selectedProjects.value]
    assignTarget.value = null
    notify.add('success', 'Project access updated')
  } else {
    notify.add('error', 'Failed to update project access')
  }
}

function toggleProject(name: string) {
  if (selectedProjects.value.has(name)) {
    selectedProjects.value.delete(name)
  } else {
    selectedProjects.value.add(name)
  }
}

async function submitChangePassword() {
  changePwError.value = ''
  if (!changePwUser.value) return
  const res = await api(`/api/auth/users/${changePwUser.value.id}/password`, {
    method: 'POST',
    body: JSON.stringify({ password: newPassword.value }),
  })
  const data = await res.json()
  if (res.ok) {
    changePwUser.value = null
    notify.add('success', 'Password updated')
  } else {
    changePwError.value = data.error || 'Failed to update password'
  }
}

async function fetchUsers() {
  loading.value = true
  try {
    const [usersRes, auditRes] = await Promise.all([
      api('/api/auth/users'),
      api('/api/auth/audit'),
    ])
    const data = await usersRes.json()
    users.value = data.users || []
    systemAudit.value = await auditRes.json()
  } finally {
    loading.value = false
  }
}

async function updateRole(id: number, role: string) {
  const res = await api(`/api/auth/users/${id}/role`, { method: 'POST', body: JSON.stringify({ role }) })
  if (res.ok) {
    const u = users.value.find(u => u.id === id)
    if (u) u.role = role
    notify.add('success', 'Role updated')
  } else {
    notify.add('error', 'Failed to update role')
  }
}

async function removeUser(u: UserEntry) {
  if (!confirm(`Delete user "${u.username}"?`)) return
  const res = await api(`/api/auth/users/${u.id}/delete`, { method: 'DELETE' })
  if (res.ok) {
    users.value = users.value.filter(x => x.id !== u.id)
    notify.add('success', `User ${u.username} deleted`)
  } else {
    notify.add('error', 'Failed to delete user')
  }
}

async function createUser() {
  createError.value = ''
  const res = await api('/api/auth/users/create', {
    method: 'POST',
    body: JSON.stringify(newUser.value),
  })
  const data = await res.json()
  if (res.ok) {
    showCreate.value = false
    newUser.value = { username: '', password: '', role: 'developer' }
    notify.add('success', `User ${data.username} created`)
    fetchUsers()
  } else {
    createError.value = data.error || 'Failed to create user'
  }
}

onMounted(fetchUsers)
</script>
