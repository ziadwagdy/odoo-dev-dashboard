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
        How to Use
      </h1>
    </div>

    <!-- Hero -->
    <div class="card mb-8 border-accent/30">
      <h2 class="text-xl font-bold text-white mb-2">Odoo Dev Dashboard</h2>
      <p class="text-slate-400">
        Manage multiple Odoo projects across versions. Deploy, switch branches, manage databases, edit settings, and run Odoo shell — all from one place.
      </p>
    </div>

    <!-- Quick Start -->
    <div class="card mb-8">
      <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
        <svg class="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
        </svg>
        Quick Start
      </h3>
      <ol class="list-decimal list-inside space-y-2 text-slate-300">
        <li>Run <code class="px-2 py-0.5 bg-surface rounded font-mono text-sm">docker compose up -d</code> from the dashboard directory</li>
        <li>Open <code class="px-2 py-0.5 bg-surface rounded font-mono text-sm">http://localhost:8892</code> (or your configured port)</li>
        <li>Projects appear grouped by Odoo version</li>
        <li>Click a project to manage it, or use <RouterLink to="/onboard" class="text-accent hover:text-accent-light underline">New Project</RouterLink> to onboard one</li>
      </ol>
    </div>

    <!-- Key Features -->
    <h3 class="text-lg font-bold text-white mb-4">Key Features</h3>
    <div class="grid gap-4 md:gap-5 mb-10">
      <div class="card">
        <h4 class="font-semibold text-slate-200 mb-2">Dashboard</h4>
        <p class="text-sm text-slate-400">Project list with status (running/stopped), CPU/memory gauges, and quick actions. Use <strong>New Project</strong> for the onboard wizard, <strong>Health</strong> for system and container stats.</p>
      </div>
      <div class="card">
        <h4 class="font-semibold text-slate-200 mb-2">Project Tabs</h4>
        <ul class="text-sm text-slate-400 space-y-1 list-disc list-inside">
          <li><strong class="text-slate-300">Overview</strong> — container info, addons paths, recent commits, deploy history</li>
          <li><strong class="text-slate-300">Logs</strong> — live container logs, filter, follow, lock scroll</li>
          <li><strong class="text-slate-300">Database</strong> — backup, duplicate, drop, restore from disk</li>
          <li><strong class="text-slate-300">Modules</strong> — list/update modules by addons path</li>
          <li><strong class="text-slate-300">Branches</strong> — switch branch, pull, update submodules</li>
          <li><strong class="text-slate-300">Settings</strong> — odoo.conf, .env, auto-deploy cron</li>
          <li><strong class="text-slate-300">Notebook</strong> — Odoo shell with full ORM (env, self, env['model'].search([]))</li>
        </ul>
      </div>
      <div class="card">
        <h4 class="font-semibold text-slate-200 mb-2">Deploy</h4>
        <p class="text-sm text-slate-400">Triggers a container rebuild. Output streams in the Deploy Panel above the tabs. Use after switching branches or changing addons.</p>
      </div>
      <div class="card">
        <h4 class="font-semibold text-slate-200 mb-2">Onboard</h4>
        <p class="text-sm text-slate-400">Add a new project via the wizard: clone repo, configure addons paths, pick Odoo version, assign port and subdomain. Produces a running instance.</p>
      </div>
    </div>

    <!-- FAQ -->
    <h3 class="text-lg font-bold text-white mb-4">FAQ</h3>
    <div class="space-y-2 mb-10">
      <details
        v-for="faq in faqs"
        :key="faq.q"
        class="card group cursor-pointer"
        :open="faq.open"
      >
        <summary class="font-semibold text-slate-200 list-none flex items-center justify-between gap-2">
          <span>{{ faq.q }}</span>
          <svg class="w-5 h-5 text-slate-500 shrink-0 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
          </svg>
        </summary>
        <p class="mt-3 text-sm text-slate-400">{{ faq.a }}</p>
      </details>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'

const faqs = [
  {
    q: 'How do I add a project?',
    a: 'Use the New Project button on the dashboard, or go to /onboard. The wizard will clone your repo, configure addons paths, pick Odoo/Enterprise version, and assign a port.',
    open: false,
  },
  {
    q: 'Where are ports defined?',
    a: 'Ports are stored in the .port-registry file (pipe-delimited: name|version|odoo_port|db_port|url|folder). The onboard wizard assigns them automatically.',
    open: false,
  },
  {
    q: 'How does deploy work?',
    a: 'Deploy triggers a Docker container rebuild. It pulls latest code (if configured), installs dependencies, and restarts the Odoo process. The output streams in real time.',
    open: false,
  },
  {
    q: 'How do I use the Notebook?',
    a: 'Select a database and click Start Odoo Shell. Then add cells and run Python with full Odoo env: env, self, env["res.partner"].search([]), etc. Use Ctrl+Enter to execute.',
    open: false,
  },
]
</script>
