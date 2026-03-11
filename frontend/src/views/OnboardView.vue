<template>
  <div class="max-w-4xl mx-auto px-4 md:px-6 py-6 md:py-10">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center gap-3 md:gap-4 mb-6 md:mb-10">
      <RouterLink to="/" class="btn btn-ghost btn-sm">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
        </svg>
        Dashboard
      </RouterLink>
      <div class="hidden sm:block h-6 w-px bg-border"></div>
      <h1 class="text-2xl md:text-3xl font-bold bg-gradient-to-r from-white to-accent-light bg-clip-text text-transparent">
        Onboard New Project
      </h1>
    </div>

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
          <label class="block text-sm font-semibold text-slate-300 mb-2">GitHub Repository URL</label>
          <input
            v-model="form.repoUrl"
            type="text"
            placeholder="git@github.com:ORG/REPO.git"
            class="w-full px-4 py-3 rounded-lg bg-surface border border-border text-white placeholder-slate-500 focus:outline-none focus:border-accent transition-colors font-mono text-sm"
            :class="errors.repoUrl ? 'border-red-500' : ''"
          />
          <p v-if="errors.repoUrl" class="mt-1 text-sm text-red-400">{{ errors.repoUrl }}</p>
          <p class="mt-1 text-xs text-slate-500">SSH format required (git@github.com:...)</p>
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
            <label class="flex items-start gap-3 p-3 rounded-lg bg-surface-hover border border-border cursor-pointer hover:border-accent/50 transition-colors">
              <input type="radio" v-model="form.hrBaseMode" value="yes-mount" class="mt-1" />
              <div>
                <div class="font-medium text-white">Yes - Mount worktree</div>
                <div class="text-xs text-slate-400">Project uses hr-base modules from hr-base repository</div>
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
    <div v-if="currentStep === 3" class="card">
      <h2 class="text-xl font-bold mb-6 text-white">Onboarding in Progress</h2>
      
      <div class="space-y-3 mb-6">
        <div v-for="(line, idx) in progressLines" :key="idx"
          class="p-3 rounded-lg text-sm font-mono"
          :class="line.error ? 'bg-red-500/10 text-red-400 border border-red-500/30' :
                  line.success ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' :
                  line.warning ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
                  'bg-surface-hover text-slate-300'"
        >
          {{ line.text }}
        </div>
      </div>

      <div v-if="!onboardingComplete" class="text-center py-4">
        <div class="inline-block w-8 h-8 border-3 border-accent/30 border-t-accent rounded-full animate-spin"></div>
        <p class="text-sm text-slate-400 mt-3">Please wait...</p>
      </div>

      <div v-if="onboardingComplete && !onboardingError" class="text-center py-6">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-500/20 border-2 border-emerald-500 flex items-center justify-center">
          <svg class="w-8 h-8 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
          </svg>
        </div>
        <h3 class="text-xl font-bold text-emerald-400 mb-2">Onboarding Complete!</h3>
        <p class="text-slate-400 mb-6">
          Your project is now accessible at 
          <a :href="`https://${form.subdomain}.zedev.org`" target="_blank" class="text-accent hover:underline">
            https://{{ form.subdomain }}.zedev.org
          </a>
        </p>
        <div class="flex justify-center gap-3">
          <RouterLink to="/" class="btn btn-primary">View Dashboard</RouterLink>
          <RouterLink :to="`/project/${form.projectName}`" class="btn btn-ghost">View Project</RouterLink>
        </div>
      </div>

      <div v-if="onboardingError" class="text-center py-6">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 border-2 border-red-500 flex items-center justify-center">
          <svg class="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </div>
        <h3 class="text-xl font-bold text-red-400 mb-2">Onboarding Failed</h3>
        <p class="text-slate-400 mb-6">An error occurred during onboarding. Please check the logs above.</p>
        <button @click="resetForm" class="btn btn-primary">Start Over</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { RouterLink } from 'vue-router'

const currentStep = ref(1)
const validating = ref(false)
const onboarding = ref(false)
const onboardingComplete = ref(false)
const onboardingError = ref(false)
const assignedPorts = ref<{odoo_port: number, db_port: number} | null>(null)
const progressLines = ref<Array<{text: string, error?: boolean, success?: boolean, warning?: boolean}>>([])

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

async function validateAndProceed() {
  // Clear errors
  Object.keys(errors).forEach(k => (errors as any)[k] = '')
  
  // Basic client validation
  if (!form.projectName) {
    errors.projectName = 'Project name is required'
    return
  }
  if (!form.repoUrl) {
    errors.repoUrl = 'Repository URL is required'
    return
  }
  if (!form.version) {
    errors.version = 'Odoo version is required'
    return
  }
  if (!form.subdomain) {
    errors.subdomain = 'Subdomain is required'
    return
  }
  
  // Server validation
  validating.value = true
  try {
    const response = await fetch('/api/onboard/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_name: form.projectName,
        subdomain: form.subdomain,
        version: form.version,
      }),
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
  progressLines.value = []
  
  try {
    const response = await fetch('/api/onboard/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_name: form.projectName,
        repo_url: form.repoUrl,
        version: form.version,
        subdomain: form.subdomain,
        hr_base_mode: form.hrBaseMode,
      }),
    })
    
    const data = await response.json()
    
    if (!data.success) {
      progressLines.value.push({ text: `ERROR: ${data.error}`, error: true })
      onboardingError.value = true
      onboarding.value = false
      return
    }
    
    // Start SSE stream
    const eventSource = new EventSource(`/stream/onboard/${form.projectName}`)
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.line) {
        progressLines.value.push({
          text: data.line,
          error: data.error,
          success: data.success,
          warning: data.warning,
        })
      }
      
      if (data.done) {
        eventSource.close()
        onboarding.value = false
        
        if (data.error || progressLines.value.some(l => l.error)) {
          onboardingError.value = true
        } else {
          onboardingComplete.value = true
        }
      }
    }
    
    eventSource.onerror = () => {
      eventSource.close()
      progressLines.value.push({ text: 'ERROR: Connection lost', error: true })
      onboardingError.value = true
      onboarding.value = false
    }
  } catch (error: any) {
    progressLines.value.push({ text: `ERROR: ${error.message}`, error: true })
    onboardingError.value = true
    onboarding.value = false
  }
}

function resetForm() {
  currentStep.value = 1
  onboardingComplete.value = false
  onboardingError.value = false
  progressLines.value = []
  Object.keys(form).forEach(k => (form as any)[k] = k === 'hrBaseMode' ? 'no' : '')
  Object.keys(errors).forEach(k => (errors as any)[k] = '')
}
</script>
