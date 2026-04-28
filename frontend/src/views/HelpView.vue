<template>
  <SidebarLayout>
    <template #breadcrumb>
      <Breadcrumb :crumbs="[{ label: 'Docs' }]" />
    </template>

    <div class="max-w-4xl mx-auto space-y-10 pb-16">

      <!-- Header -->
      <div class="flex items-center gap-4">
        <div>
          <h1 class="text-2xl font-bold text-slate-100">Documentation</h1>
          <p class="text-sm text-slate-400 mt-1">Odoo Dev Dashboard — v{{ version }}</p>
        </div>
      </div>

      <!-- What is this -->
      <section>
        <SectionHeader title="Overview" />
        <div class="card">
          <p class="text-slate-300 leading-relaxed">
            The Odoo Dev Dashboard is an internal tool for the CNC team to manage multiple Odoo projects across versions from a single browser UI.
            It replaces manual Docker and SSH workflows with a live dashboard, log streaming, branch switching, database management, and an Odoo shell (Notebook).
          </p>
          <div class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
            <div class="bg-bg-secondary rounded-xl p-3 border border-border">
              <div class="text-lg font-bold text-accent">Projects</div>
              <div class="text-xs text-slate-500 mt-0.5">Any number of Odoo instances</div>
            </div>
            <div class="bg-bg-secondary rounded-xl p-3 border border-border">
              <div class="text-lg font-bold text-accent">Versions</div>
              <div class="text-xs text-slate-500 mt-0.5">v15, v16, v17, v18, v19…</div>
            </div>
            <div class="bg-bg-secondary rounded-xl p-3 border border-border">
              <div class="text-lg font-bold text-accent">Live</div>
              <div class="text-xs text-slate-500 mt-0.5">Container status via SSE</div>
            </div>
            <div class="bg-bg-secondary rounded-xl p-3 border border-border">
              <div class="text-lg font-bold text-accent">Shell</div>
              <div class="text-xs text-slate-500 mt-0.5">Full Odoo ORM in browser</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Architecture -->
      <section>
        <SectionHeader title="Architecture" />
        <div class="card space-y-4">
          <p class="text-sm text-slate-400">The dashboard runs as a Docker Compose stack alongside the Odoo containers.</p>
          <div class="font-mono text-xs bg-bg-secondary rounded-xl p-4 border border-border text-slate-300 leading-relaxed">
            <div class="text-slate-500">nginx (:8892)</div>
            <div class="ml-4">├── <span class="text-accent">/api/*</span>   → Django/Daphne backend (:8000)</div>
            <div class="ml-4">├── <span class="text-accent">/stream/*</span> → Django SSE endpoints</div>
            <div class="ml-4">├── <span class="text-accent">/ws/*</span>    → Django Channels WebSocket</div>
            <div class="ml-4">└── <span class="text-accent">/*</span>       → Vue 3 SPA (Vite build)</div>
            <div class="mt-3 text-slate-500">backend reads:</div>
            <div class="ml-4">├── <span class="text-accent">.port-registry</span>  — project list (pipe-delimited)</div>
            <div class="ml-4">├── <span class="text-accent">Docker socket</span>   — container control + stats</div>
            <div class="ml-4">└── <span class="text-accent">odoo.conf / .env</span> — per-project config files</div>
          </div>
          <div class="grid md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 class="font-semibold text-slate-200 mb-2">Backend stack</h4>
              <ul class="space-y-1 text-slate-400">
                <li>• <strong class="text-slate-300">Django 5</strong> + DRF — REST API</li>
                <li>• <strong class="text-slate-300">Django Channels</strong> + Daphne — WebSocket / ASGI</li>
                <li>• <strong class="text-slate-300">Redis</strong> — Channels layer</li>
                <li>• <strong class="text-slate-300">APScheduler</strong> — cron jobs</li>
                <li>• <strong class="text-slate-300">jupyter_client</strong> — Notebook kernel (ZMQ)</li>
                <li>• <strong class="text-slate-300">SQLite</strong> — deploy history, cron state</li>
              </ul>
            </div>
            <div>
              <h4 class="font-semibold text-slate-200 mb-2">Frontend stack</h4>
              <ul class="space-y-1 text-slate-400">
                <li>• <strong class="text-slate-300">Vue 3</strong> + TypeScript + Vite</li>
                <li>• <strong class="text-slate-300">Pinia</strong> — state management</li>
                <li>• <strong class="text-slate-300">TailwindCSS</strong> — styling</li>
                <li>• <strong class="text-slate-300">IBM Plex Sans</strong> + JetBrains Mono</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <!-- Quick Start -->
      <section>
        <SectionHeader title="Quick Start" />
        <div class="card space-y-4">
          <ol class="space-y-3">
            <li v-for="(step, i) in quickStart" :key="i" class="flex gap-3">
              <span class="w-6 h-6 rounded-full bg-accent/20 border border-accent/40 text-accent text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">{{ i + 1 }}</span>
              <div class="flex-1 text-sm text-slate-300" v-html="step" />
            </li>
          </ol>
        </div>
      </section>

      <!-- Feature reference -->
      <section>
        <SectionHeader title="Feature Reference" />
        <div class="space-y-4">
          <div v-for="feat in features" :key="feat.title" class="card">
            <h4 class="font-semibold text-slate-100 mb-2 flex items-center gap-2">
              <span class="text-accent">{{ feat.icon }}</span>
              {{ feat.title }}
              <span v-if="feat.tab" class="ml-auto text-[10px] font-mono text-slate-500 bg-bg-secondary px-2 py-0.5 rounded border border-border">tab: {{ feat.tab }}</span>
            </h4>
            <p class="text-sm text-slate-400 leading-relaxed">{{ feat.desc }}</p>
            <div v-if="feat.code" class="mt-3 font-mono text-xs bg-[#0a0c12] rounded-lg p-3 border border-border text-slate-300">{{ feat.code }}</div>
          </div>
        </div>
      </section>

      <!-- Onboard wizard -->
      <section>
        <SectionHeader title="Onboarding a New Project" />
        <div class="card space-y-4">
          <p class="text-sm text-slate-400">The onboard wizard (<RouterLink to="/onboard" class="text-accent hover:underline">New Project</RouterLink>) automates the full setup sequence.</p>
          <ol class="space-y-2">
            <li v-for="(s, i) in onboardSteps" :key="i" class="flex gap-3 text-sm">
              <span class="w-5 h-5 rounded bg-surface-hover border border-border text-slate-400 text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">{{ i + 1 }}</span>
              <span class="text-slate-300">{{ s }}</span>
            </li>
          </ol>
          <div class="bg-amber-900/20 border border-amber-500/30 rounded-xl p-3 text-xs text-amber-300">
            <strong>Manual steps still required after onboard:</strong> copy Nginx config (<code class="bg-black/20 px-1 rounded">sudo cp ... /etc/nginx/conf.d/</code>),
            add Cloudflare tunnel DNS record, and restart cloudflared. The wizard displays exact copy-paste commands on the final screen.
          </div>
        </div>
      </section>

      <!-- Notebook -->
      <section>
        <SectionHeader title="Notebook (Odoo Shell)" />
        <div class="card space-y-4">
          <p class="text-sm text-slate-400">The Notebook tab gives you a full Jupyter-style Python REPL wired into a live Odoo database. Useful for data investigation, one-off migrations, and debugging model logic.</p>
          <div class="space-y-2">
            <h4 class="text-sm font-semibold text-slate-200">How it works</h4>
            <ol class="space-y-1 text-sm text-slate-400 list-decimal list-inside">
              <li>Select a database and click <strong class="text-slate-300">▶ Start Odoo Shell</strong></li>
              <li>The backend spawns an ipykernel process inside the project's Docker container</li>
              <li>A WebSocket connection is established to the kernel via ZMQ</li>
              <li>Add cells, write Python, press <kbd class="bg-bg-secondary border border-border px-1.5 py-0.5 rounded text-xs font-mono">Ctrl+Enter</kbd> to execute</li>
              <li>Output (stdout, stderr, HTML tables, images) streams back to the cell</li>
            </ol>
          </div>
          <div class="space-y-2">
            <h4 class="text-sm font-semibold text-slate-200">Available globals</h4>
            <div class="font-mono text-xs bg-[#0a0c12] rounded-lg p-3 border border-border text-slate-300 leading-relaxed">
              <div><span class="text-purple-400">env</span>        <span class="text-slate-500"># Odoo Environment (sudo)</span></div>
              <div><span class="text-purple-400">self</span>       <span class="text-slate-500"># res.users singleton for the admin user</span></div>
              <div class="mt-2 text-slate-400"># Examples:</div>
              <div>env[<span class="text-green-400">'res.partner'</span>].search([(
                <span class="text-green-400">'is_company'</span>, <span class="text-blue-400">'='</span>, <span class="text-orange-400">True</span>)])</div>
              <div>env[<span class="text-green-400">'hr.employee'</span>].browse(<span class="text-orange-400">42</span>).name</div>
            </div>
          </div>
          <div class="bg-blue-900/20 border border-blue-500/30 rounded-xl p-3 text-xs text-blue-300">
            The kernel runs inside the project container — it has the same Python environment as Odoo itself and can import any installed module.
          </div>
        </div>
      </section>

      <!-- Port registry -->
      <section>
        <SectionHeader title="Port Registry" />
        <div class="card space-y-3">
          <p class="text-sm text-slate-400">
            All projects are tracked in <code class="text-slate-300 bg-bg-secondary px-1.5 py-0.5 rounded font-mono text-xs">$ODOO_DEV_BASE/projects/.port-registry</code> (pipe-delimited, one project per line).
          </p>
          <div class="font-mono text-xs bg-[#0a0c12] rounded-lg p-3 border border-border text-slate-300">
            <div class="text-slate-500"># format: name|version|odoo_port|db_port|url|folder</div>
            <div>alif-stores<span class="text-slate-600">|</span>17<span class="text-slate-600">|</span>18171<span class="text-slate-600">|</span>15432<span class="text-slate-600">|</span>alifstoresdev.zedev.org<span class="text-slate-600">|</span>alif-stores</div>
          </div>
          <p class="text-xs text-slate-500">Port convention: <code class="font-mono">181[version][client_index]</code> — e.g. first v17 client: 18171, second v17 client: 18173.</p>
        </div>
      </section>

      <!-- FAQ -->
      <section>
        <SectionHeader title="FAQ" />
        <div class="space-y-2">
          <details
            v-for="faq in faqs"
            :key="faq.q"
            class="card group cursor-pointer"
          >
            <summary class="font-semibold text-slate-200 list-none flex items-center justify-between gap-2">
              <span>{{ faq.q }}</span>
              <svg class="w-4 h-4 text-slate-500 shrink-0 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </summary>
            <p class="mt-3 text-sm text-slate-400 leading-relaxed">{{ faq.a }}</p>
          </details>
        </div>
      </section>

      <!-- Changelog -->
      <section>
        <SectionHeader title="Changelog" />
        <div class="space-y-3">
          <div v-for="release in changelog" :key="release.version" class="card">
            <div class="flex items-center gap-3 mb-3">
              <span class="font-mono text-sm font-bold text-accent">v{{ release.version }}</span>
              <span class="text-xs text-slate-500">{{ release.date }}</span>
            </div>
            <ul class="space-y-1">
              <li v-for="item in release.items" :key="item" class="text-sm text-slate-400 flex gap-2">
                <span :class="item.startsWith('fix') ? 'text-amber-400' : item.startsWith('break') ? 'text-red-400' : 'text-emerald-400'" class="shrink-0">•</span>
                {{ item }}
              </li>
            </ul>
          </div>
        </div>
      </section>

    </div>
  </SidebarLayout>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import SidebarLayout from '@/layouts/SidebarLayout.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import Breadcrumb from '@/components/Breadcrumb.vue'
import { APP_VERSION } from '@/version'

const version = APP_VERSION

const quickStart = [
  'Run <code class="px-1.5 py-0.5 bg-surface rounded font-mono text-xs">docker compose up -d</code> from the dashboard directory.',
  'Open the dashboard URL (default <code class="px-1.5 py-0.5 bg-surface rounded font-mono text-xs">http://localhost:8892</code> or your configured subdomain).',
  'Log in with your account. Admins see the full sidebar including <em>New Project</em> and <em>Users &amp; Roles</em>.',
  'Projects are grouped by Odoo version in the sidebar and the main table. Click any project to open its detail page.',
  'To add a new project use <strong>New Project</strong> in the sidebar. The wizard handles cloning, Docker build, and port assignment.',
]

const features = [
  {
    icon: '📋',
    title: 'Dashboard',
    desc: 'Main project list grouped by Odoo version. Shows container status (running/stopped/restarting), current branch, database count, and URL. Supports quick restart from the table.',
  },
  {
    icon: '📊',
    title: 'Health',
    desc: 'System-level view: host CPU, RAM, and disk usage with live gauges, plus per-container CPU and memory stats updated every few seconds via Server-Sent Events.',
  },
  {
    icon: '🚀',
    title: 'Deploy',
    tab: 'Overview',
    desc: 'Triggers a Docker container rebuild for the project. Streams stdout/stderr in real time. Use after switching branches or modifying addons. The Deploy Panel appears above the tabs on any project page.',
  },
  {
    icon: '🌿',
    title: 'Branch',
    tab: 'Branch',
    desc: 'View the current branch, switch to any local or remote branch, pull latest, and sync Git submodules. All operations stream output so you can see exactly what Git is doing.',
  },
  {
    icon: '🗄️',
    title: 'Database',
    tab: 'Database',
    desc: 'List all databases in the project\'s PostgreSQL container with sizes. Backup (pg_dump), duplicate, drop, or restore from a backup file on disk. Large restores use direct DB access — no Nginx timeout risk.',
  },
  {
    icon: '🧩',
    title: 'Modules',
    tab: 'Modules',
    desc: 'Browse all installed Odoo modules grouped by addons path. See version, state, and author. Trigger a module update from the UI.',
  },
  {
    icon: '⚙️',
    title: 'Settings',
    tab: 'Settings',
    desc: 'Edit odoo.conf and .env directly in the browser with syntax highlighting. Save and restart the container to apply changes. Also manage auto-deploy cron jobs.',
  },
  {
    icon: '📓',
    title: 'Notebook',
    tab: 'Notebook',
    desc: 'Full Jupyter-style Python shell with a live Odoo ORM environment. Start a kernel against any database, add cells, run code with Ctrl+Enter. Supports stdout, stderr, HTML tables (DataFrames), and image output.',
    code: "env['res.partner'].search([('customer_rank', '>', 0)], limit=5).mapped('name')",
  },
]

const onboardSteps = [
  'Enter the project name, Git repo URL, and select the Odoo version.',
  'The wizard clones the repo with --recurse-submodules.',
  'Requirements files are found across the entire repo tree and merged (including hr-base if applicable).',
  'Addons paths are auto-detected by finding all directories containing __manifest__.py files.',
  'Ports are assigned automatically from the port convention (181[version][index]).',
  'A Dockerfile, odoo.conf, and docker-compose.yml are generated and the container is built.',
  'Dozzle filter is updated so the new container\'s logs are visible in the log viewer.',
  'The wizard shows copy-paste commands for the remaining manual steps: Nginx config and Cloudflare DNS.',
]

const faqs = [
  {
    q: 'I navigated to a project and the sidebar collapsed — is that a bug?',
    a: 'No. The sidebar automatically re-opens the accordion for the version of whichever project page you\'re on. If it appears collapsed, the project\'s version might not match any accordion group yet.',
  },
  {
    q: 'The notebook says "kernel stopped" immediately after starting.',
    a: 'This usually means ipykernel is not installed in the project\'s Docker container. The kernel manager tries to install it automatically, but if the container has a read-only filesystem or pip is not available, this can fail. Check the container logs for details.',
  },
  {
    q: 'Database restore times out.',
    a: 'For large databases (>1 GB), use the SSH tunnel method: ssh -L <local_port>:127.0.0.1:<container_port> zeyad@68.183.74.39, then restore via http://localhost:<local_port>/web/database/manager. This bypasses Nginx entirely.',
  },
  {
    q: 'I added a module but it doesn\'t appear in the Modules tab.',
    a: 'Check that the module\'s parent directory is listed in addons_path in odoo.conf. You can verify under the Settings tab. Also ensure the directory actually contains __manifest__.py — the dashboard scans for that file.',
  },
  {
    q: 'How do I update the dashboard itself?',
    a: 'Pull the latest code into the dashboard directory, then run: docker compose build && docker compose up -d. The frontend will be rebuilt and the backend restarted.',
  },
  {
    q: 'How is authentication handled?',
    a: 'The dashboard has its own user table (SQLite). Admins can create and manage users via the Users & Roles page. There is no Odoo authentication integration — dashboard users are separate from Odoo users.',
  },
]

const changelog = [
  {
    version: '1.4.0',
    date: '2026-04-14',
    items: [
      'fix: light theme — notebook cells now render with correct colors (dark code areas stay dark, text contrast fixed)',
      'fix: sidebar project links auto-open the correct version accordion after navigation',
      'feat: version number displayed in sidebar footer',
      'feat: comprehensive documentation page (this page)',
    ],
  },
  {
    version: '1.3.0',
    date: '2026-04-11',
    items: [
      'feat: project environments grouping (production / staging / dev)',
    ],
  },
  {
    version: '1.2.0',
    date: '2026-04-09',
    items: [
      'feat: audit log for project actions',
      'feat: scheduled database backups via APScheduler cron',
      'feat: GitHub webhook endpoint for auto-deploy on push',
      'feat: Dozzle log viewer embed in project detail',
      'feat: FileBrowser integration for writable file access',
    ],
  },
  {
    version: '1.1.0',
    date: '2026-04-07',
    items: [
      'feat: mobile-friendly project page layout',
      'feat: Help / docs view',
      'fix: Settings tab config save',
      'feat: UX improvements across all tabs',
    ],
  },
  {
    version: '1.0.0',
    date: '2026-04-05',
    items: [
      'feat: full rewrite — Django + Vue 3 replacing original Flask dashboard',
      'feat: Notebook tab (Jupyter kernel over WebSocket)',
      'feat: real-time SSE log streaming and health gauges',
      'feat: branch management, database operations, module list',
      'feat: onboard wizard with full automation',
    ],
  },
]
</script>
