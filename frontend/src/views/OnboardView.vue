<template>
  <SidebarLayout>
    <template #breadcrumb>
      <Breadcrumb :crumbs="[{ label: 'New Project' }]" />
    </template>
    <div class="max-w-4xl">

    <!-- Step Indicator -->
    <div class="flex items-center justify-center mb-8 gap-2 md:gap-4">
      <div v-for="s in steps" :key="s.id" class="flex items-center">
        <div class="flex items-center gap-2 md:gap-3">
          <div
            class="flex items-center justify-center w-8 h-8 md:w-10 md:h-10 rounded-full border-2 text-sm md:text-base font-bold transition-all"
            :class="currentStep === s.id ? 'border-accent bg-accent/20 text-accent' :
                    currentStep > s.id ? 'border-emerald-500 bg-emerald-500/20 text-emerald-400' :
                    'border-slate-600 bg-slate-800/50 text-slate-500'"
          >
            <span v-if="currentStep > s.id">✓</span>
            <span v-else>{{ s.id }}</span>
          </div>
          <span class="hidden sm:inline text-sm text-slate-400">{{ s.label }}</span>
        </div>
        <div v-if="s.id < steps.length" class="w-8 md:w-16 h-0.5 mx-2 md:mx-4"
          :class="currentStep > s.id ? 'bg-emerald-500' : 'bg-slate-700'">
        </div>
      </div>
    </div>

    <!-- Step 1: Project Details -->
    <div v-if="currentStep === 1" class="card">
      <h2 class="text-xl font-bold mb-6 text-white">Project Details</h2>

      <div class="space-y-4">
        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">Project Name</label>
          <input
            v-model="form.projectName"
            type="text"
            placeholder="e.g. lexus-tailors, medtech"
            class="w-full px-4 py-3 rounded-lg bg-surface border border-border text-white placeholder-slate-500 focus:outline-none focus:border-accent transition-colors"
            :class="errors.projectName ? 'border-red-500' : ''"
          />
          <p v-if="errors.projectName" class="mt-1 text-sm text-red-400">{{ errors.projectName }}</p>
          <p class="mt-1 text-xs text-slate-500">Short slug, no spaces (alphanumeric, hyphens, underscores)</p>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Repository URL
            <span class="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide bg-slate-500/15 text-slate-400 border border-slate-500/30">
              optional
            </span>
            <span class="ml-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide bg-amber-500/15 text-amber-400 border border-amber-500/30">
              SSH only
            </span>
          </label>
          <input
            v-model="form.repoUrl"
            type="text"
            placeholder="git@github.com:ORG/REPO.git"
            class="w-full px-4 py-3 rounded-lg bg-surface border border-border text-white placeholder-slate-500 focus:outline-none focus:border-accent transition-colors font-mono text-sm"
            :class="errors.repoUrl ? 'border-red-500' : (repoUrlValid ? 'border-emerald-500/60' : '')"
          />
          <p v-if="errors.repoUrl" class="mt-1 text-sm text-red-400">{{ errors.repoUrl }}</p>
          <div v-else class="mt-1.5 flex items-center gap-1.5">
            <template v-if="form.repoUrl && !repoUrlValid">
              <svg class="w-3.5 h-3.5 text-red-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
              <span class="text-xs text-red-400">Must be SSH format — <code class="font-mono">git@github.com:ORG/REPO.git</code></span>
            </template>
            <template v-else-if="form.repoUrl && repoUrlValid">
              <svg class="w-3.5 h-3.5 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-xs text-emerald-400">Valid SSH URL</span>
            </template>
            <template v-else>
              <svg class="w-3.5 h-3.5 text-slate-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span class="text-xs text-slate-500">Leave blank for a plain Odoo install with no custom modules</span>
            </template>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">Odoo Version</label>
            <select
              v-model="form.version"
              class="w-full px-4 py-3 rounded-lg bg-surface border border-border text-white focus:outline-none focus:border-accent transition-colors"
              :class="errors.version ? 'border-red-500' : ''"
            >
              <option value="">Select version...</option>
              <option value="15">Odoo 15</option>
              <option value="17">Odoo 17</option>
              <option value="18">Odoo 18</option>
              <option value="19">Odoo 19</option>
            </select>
            <p v-if="errors.version" class="mt-1 text-sm text-red-400">{{ errors.version }}</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">Subdomain</label>
            <div class="flex items-center gap-2">
              <input
                v-model="form.subdomain"
                type="text"
                placeholder="e.g. lexus"
                class="flex-1 px-4 py-3 rounded-lg bg-surface border border-border text-white placeholder-slate-500 focus:outline-none focus:border-accent transition-colors"
                :class="errors.subdomain ? 'border-red-500' : ''"
              />
              <span class="text-sm text-slate-400">.zedev.org</span>
            </div>
            <p v-if="errors.subdomain" class="mt-1 text-sm text-red-400">{{ errors.subdomain }}</p>
          </div>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">HR Base Dependency</label>
          <div class="space-y-2">
            <label class="flex items-start gap-3 p-3 rounded-lg bg-surface-hover border border-border cursor-pointer hover:border-accent/50 transition-colors">
              <input type="radio" v-model="form.hrBaseMode" value="no" class="mt-1" />
              <div>
                <div class="font-medium text-white">No dependency</div>
                <div class="text-xs text-slate-400">Project does not use hr-base modules</div>
              </div>
            </label>
            <label
              class="flex items-start gap-3 p-3 rounded-lg bg-surface-hover border border-border transition-colors"
              :class="form.version === '15' ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer hover:border-accent/50'"
            >
              <input type="radio" v-model="form.hrBaseMode" value="yes-mount" class="mt-1" :disabled="form.version === '15'" />
              <div>
                <div class="font-medium text-white">Yes - Mount worktree</div>
                <div class="text-xs text-slate-400">
                  <span v-if="form.version === '15'">Not available for Odoo 15 — no hr-base v15 branch</span>
                  <span v-else>Project uses hr-base modules from hr-base repository</span>
                </div>
              </div>
            </label>
            <label class="flex items-start gap-3 p-3 rounded-lg bg-surface-hover border border-border cursor-pointer hover:border-accent/50 transition-colors">
              <input type="radio" v-model="form.hrBaseMode" value="yes-included" class="mt-1" />
              <div>
                <div class="font-medium text-white">Yes - Included in repo</div>
                <div class="text-xs text-slate-400">Project repo itself contains hr-base modules</div>
              </div>
            </label>
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-3 mt-6">
        <button @click="validateAndProceed" :disabled="validating" class="btn btn-primary">
          <span v-if="validating">Validating...</span>
          <span v-else>Next →</span>
        </button>
      </div>
    </div>

    <!-- Step 2: Confirmation -->
    <div v-if="currentStep === 2" class="card">
      <h2 class="text-xl font-bold mb-6 text-white">Confirm Configuration</h2>

      <div class="space-y-4 mb-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="p-4 rounded-lg bg-surface-hover border border-border">
            <div class="text-xs text-slate-400 mb-1">Project Name</div>
            <div class="text-white font-semibold">{{ form.projectName }}</div>
          </div>
          <div class="p-4 rounded-lg bg-surface-hover border border-border">
            <div class="text-xs text-slate-400 mb-1">Odoo Version</div>
            <div class="text-white font-semibold">Odoo {{ form.version }}</div>
          </div>
          <div class="p-4 rounded-lg bg-surface-hover border border-border">
            <div class="text-xs text-slate-400 mb-1">URL</div>
            <div class="text-accent font-mono text-sm">https://{{ form.subdomain }}.zedev.org</div>
          </div>
          <div class="p-4 rounded-lg bg-surface-hover border border-border">
            <div class="text-xs text-slate-400 mb-1">HR Base</div>
            <div class="text-white font-semibold">
              {{ form.hrBaseMode === 'no' ? 'Not used' :
                 form.hrBaseMode === 'yes-mount' ? 'Mounted' : 'Included' }}
            </div>
          </div>
        </div>

        <div class="p-4 rounded-lg bg-surface-hover border border-border">
          <div class="text-xs text-slate-400 mb-1">Repository</div>
          <div class="text-white font-mono text-sm break-all">{{ form.repoUrl }}</div>
        </div>

        <div v-if="assignedPorts" class="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
          <div class="text-xs text-emerald-400 mb-2">Assigned Ports</div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <span class="text-slate-400 text-sm">Odoo:</span>
              <span class="text-white font-semibold ml-2">{{ assignedPorts.odoo_port }}</span>
            </div>
            <div>
              <span class="text-slate-400 text-sm">Database:</span>
              <span class="text-white font-semibold ml-2">{{ assignedPorts.db_port }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-between gap-3">
        <button @click="currentStep = 1" class="btn btn-ghost">← Back</button>
        <button @click="startOnboarding" :disabled="onboarding" class="btn btn-primary">
          <span v-if="onboarding">Starting...</span>
          <span v-else>Start Onboarding</span>
        </button>
      </div>
    </div>

    <!-- Step 3: Progress -->
    <div v-if="currentStep === 3">
      <div class="flex items-center justify-between mb-5">
        <h2 class="text-xl font-bold text-white">
          {{ onboardingComplete ? 'Onboarding Complete' : onboardingError ? 'Onboarding Failed' : 'Onboarding…' }}
        </h2>
        <button v-if="onboardingComplete || onboardingError" @click="resetForm" class="btn btn-ghost btn-sm text-xs">
          Start Over
        </button>
      </div>

      <OnboardProgress :events="events" :project-name="form.projectName" />

      <!-- waiting indicator (while in progress) -->
      <div v-if="!onboardingComplete && !onboardingError" class="flex items-center justify-center gap-3 mt-5 text-slate-500 text-sm">
        <div class="w-4 h-4 rounded-full border-2 border-accent/30 border-t-accent animate-spin shrink-0"/>
        Please wait — this can take a few minutes for the Docker build…
      </div>
    </div>

    </div>
  </SidebarLayout>
</template>

<script setup lang="ts">
import { api } from '@/api'
import { ref, reactive, computed, watch } from 'vue'
import SidebarLayout from '@/layouts/SidebarLayout.vue'
import Breadcrumb from '@/components/Breadcrumb.vue'
import OnboardProgress from '@/components/OnboardProgress.vue'
import type { OnboardEvent } from '@/types/onboard'

// ──────────────────────────────────────────────────────────────────
// SINGLE-INSTANCE state
// ──────────────────────────────────────────────────────────────────
const currentStep = ref(1)
const validating = ref(false)
const onboarding = ref(false)
const onboardingComplete = ref(false)
const onboardingError = ref(false)
const assignedPorts = ref<{odoo_port: number, db_port: number} | null>(null)
const events = ref<OnboardEvent[]>([])

const steps = [
  { id: 1, label: 'Details' },
  { id: 2, label: 'Confirm' },
  { id: 3, label: 'Progress' },
]

const form = reactive({
  projectName: '',
  repoUrl: '',
  version: '',
  subdomain: '',
  hrBaseMode: 'no',
})

const errors = reactive({
  projectName: '',
  repoUrl: '',
  version: '',
  subdomain: '',
})

const SSH_RE = /^git@[a-zA-Z0-9._-]+:[a-zA-Z0-9._/-]+\/[a-zA-Z0-9._-]+\.git$/
const repoUrlValid = computed(() => SSH_RE.test(form.repoUrl.trim()))

watch(() => form.version, (v) => {
  if (v === '15' && form.hrBaseMode === 'yes-mount') form.hrBaseMode = 'no'
})

async function validateAndProceed() {
  Object.keys(errors).forEach(k => (errors as any)[k] = '')
  if (!form.projectName) { errors.projectName = 'Project name is required'; return }
  if (form.repoUrl && !repoUrlValid.value) { errors.repoUrl = 'Must be SSH format: git@github.com:ORG/REPO.git'; return }
  if (!form.version)     { errors.version = 'Odoo version is required'; return }
  if (!form.subdomain)   { errors.subdomain = 'Subdomain is required'; return }

  validating.value = true
  try {
    const response = await api('/api/onboard/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_name: form.projectName, subdomain: form.subdomain, version: form.version }),
    })
    const data = await response.json()
    if (!data.valid) {
      Object.keys(data.errors).forEach(key => {
        if (key === 'project_name') errors.projectName = data.errors[key]
        else if (key === 'subdomain') errors.subdomain = data.errors[key]
        else if (key === 'version') errors.version = data.errors[key]
      })
      return
    }
    assignedPorts.value = data.assigned_ports
    currentStep.value = 2
  } catch (error: any) {
    errors.projectName = 'Validation failed: ' + error.message
  } finally {
    validating.value = false
  }
}

async function startOnboarding() {
  onboarding.value = true
  currentStep.value = 3
  events.value = []
  try {
    const response = await api('/api/onboard/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_name: form.projectName,
        repo_url: form.repoUrl,
        version: form.version,
        subdomain: form.subdomain,
        hr_base_mode: form.hrBaseMode,
        odoo_port: assignedPorts.value?.odoo_port,
        db_port: assignedPorts.value?.db_port,
      }),
    })
    const data = await response.json()
    if (!data.success) {
      events.value.push({ type: 'log', text: `Error: ${data.error}`, error: true })
      events.value.push({ type: 'done', success: false })
      onboardingError.value = true
      onboarding.value = false
      return
    }
    const eventSource = new EventSource(`/api/onboard/stream/${form.projectName}`)
    eventSource.onmessage = (ev) => {
      const e: OnboardEvent = JSON.parse(ev.data)
      events.value.push(e)
      if (e.type === 'done') {
        eventSource.close()
        onboarding.value = false
        if (e.success) onboardingComplete.value = true
        else           onboardingError.value = true
      }
    }
    eventSource.onerror = () => {
      eventSource.close()
      events.value.push({ type: 'log', text: 'Connection lost', error: true })
      events.value.push({ type: 'done', success: false })
      onboardingError.value = true
      onboarding.value = false
    }
  } catch (error: any) {
    events.value.push({ type: 'log', text: error.message, error: true })
    events.value.push({ type: 'done', success: false })
    onboardingError.value = true
    onboarding.value = false
  }
}

function resetForm() {
  currentStep.value = 1
  onboardingComplete.value = false
  onboardingError.value = false
  events.value = []
  Object.keys(form).forEach(k => (form as any)[k] = k === 'hrBaseMode' ? 'no' : '')
  Object.keys(errors).forEach(k => (errors as any)[k] = '')
}


</script>
