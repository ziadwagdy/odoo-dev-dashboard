<template>
  <div class="space-y-6">

    <!-- ── Environment Cards ─────────────────────────────────────── -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div
        v-for="env in ENV_DEFS"
        :key="env.type"
        class="rounded-xl border border-border/50 bg-surface/40 overflow-hidden flex flex-col"
      >
        <!-- Colored top strip -->
        <div class="h-0.5 w-full" :class="env.stripClass" />

        <!-- Card header -->
        <div class="flex items-center justify-between px-4 pt-4 pb-3">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full" :class="isActive(env.type) ? env.dotActive : 'bg-slate-600'" />
            <span class="text-xs font-bold uppercase tracking-widest" :class="isActive(env.type) ? env.labelColor : 'text-slate-500'">
              {{ env.label }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span
              v-if="isActive(env.type)"
              class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
              :class="env.pillClass"
            >● active</span>
            <button
              class="p-1 rounded text-slate-600 hover:text-slate-300 transition-colors"
              :class="{ 'text-accent': editMode[env.type] }"
              title="Edit"
              @click="toggleEdit(env.type)"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- View mode -->
        <div v-if="!editMode[env.type]" class="px-4 pb-3 space-y-2 flex-1">
          <!-- Branch -->
          <div class="flex items-start gap-2.5">
            <svg class="w-3.5 h-3.5 mt-0.5 text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
            </svg>
            <div class="min-w-0">
              <div class="text-[10px] uppercase tracking-wide text-slate-600 mb-0.5">Branch</div>
              <span
                class="text-sm font-mono"
                :class="envConfig[env.type].branch ? 'text-slate-200' : 'text-slate-600 italic'"
              >{{ envConfig[env.type].branch || '— not set —' }}</span>
            </div>
          </div>
          <!-- Database -->
          <div class="flex items-start gap-2.5">
            <svg class="w-3.5 h-3.5 mt-0.5 text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/>
            </svg>
            <div class="min-w-0">
              <div class="text-[10px] uppercase tracking-wide text-slate-600 mb-0.5">Database</div>
              <span
                class="text-sm font-mono"
                :class="envConfig[env.type].db ? 'text-slate-200' : 'text-slate-600 italic'"
              >{{ envConfig[env.type].db || '— not set —' }}</span>
            </div>
          </div>
        </div>

        <!-- Edit mode -->
        <div v-else class="px-4 pb-3 space-y-3 flex-1">
          <div>
            <label class="block text-[10px] uppercase tracking-wide text-slate-500 mb-1">Branch</label>
            <input
              v-model="editValues[env.type].branch"
              :list="`branches-${env.type}`"
              class="input text-sm w-full"
              placeholder="e.g. main"
              autocomplete="off"
            />
            <datalist :id="`branches-${env.type}`">
              <option v-for="b in availableBranches" :key="b" :value="b" />
            </datalist>
          </div>
          <div>
            <label class="block text-[10px] uppercase tracking-wide text-slate-500 mb-1">Database</label>
            <input
              v-model="editValues[env.type].db"
              :list="`dbs-${env.type}`"
              class="input text-sm w-full"
              placeholder="e.g. myproject_prod"
              autocomplete="off"
            />
            <datalist :id="`dbs-${env.type}`">
              <option v-for="d in availableDatabases" :key="d.name" :value="d.name">{{ d.name }} ({{ d.size }})</option>
            </datalist>
          </div>
          <div class="flex gap-2 pt-1">
            <button class="btn btn-ghost btn-sm flex-1" @click="cancelEdit(env.type)">Cancel</button>
            <button
              class="btn btn-primary btn-sm flex-1"
              :disabled="saving[env.type]"
              @click="saveEnv(env.type)"
            >{{ saving[env.type] ? 'Saving…' : 'Save' }}</button>
          </div>
        </div>

        <!-- Divider -->
        <div class="mx-4 border-t border-border/40" />

        <!-- Actions -->
        <div class="px-4 py-3 grid grid-cols-2 gap-2">
          <!-- Deploy -->
          <button
            class="btn btn-sm col-span-2 inline-flex items-center justify-center gap-1.5"
            :class="isActive(env.type) ? env.deployActiveClass : 'btn-ghost'"
            :disabled="!envConfig[env.type].branch || deploying === env.type"
            @click="deployEnv(env.type)"
            :title="envConfig[env.type].branch ? `Switch to ${envConfig[env.type].branch} and pull` : 'Set a branch first'"
          >
            <svg v-if="deploying === env.type" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
            </svg>
            {{ deploying === env.type ? 'Deploying…' : 'Deploy' }}
          </button>

          <!-- Run -->
          <a
            :href="envConfig[env.type].db && running ? `https://${projectUrl}/web?db=${envConfig[env.type].db}` : '#'"
            target="_blank"
            class="btn btn-ghost btn-sm inline-flex items-center justify-center gap-1.5"
            :class="{ 'opacity-40 pointer-events-none': !envConfig[env.type].db || !running }"
            title="Open this environment's database in Odoo"
            @click.prevent="openEnv(env.type)"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Run
          </a>

          <!-- Backup -->
          <button
            class="btn btn-ghost btn-sm inline-flex items-center justify-center gap-1.5"
            :disabled="!envConfig[env.type].db || backingUp === envConfig[env.type].db"
            @click="backupDb(envConfig[env.type].db)"
            title="Backup this environment's database"
          >
            <svg v-if="backingUp === envConfig[env.type].db" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            Backup
          </button>

          <!-- Restore -->
          <button
            class="btn btn-ghost btn-sm inline-flex items-center justify-center gap-1.5"
            :disabled="!envConfig[env.type].db"
            @click="openRestoreModal(envConfig[env.type].db)"
            title="Restore a backup to this environment's database"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            Restore
          </button>
        </div>
      </div>
    </div>

    <!-- ── All Databases ─────────────────────────────────────────── -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-slate-300">All Databases</h3>
        <div class="flex items-center gap-2">
          <label
            class="btn btn-ghost btn-sm cursor-pointer inline-flex items-center gap-1.5"
            title="Upload a .dump or .zip file and restore it"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
            </svg>
            Upload &amp; Restore
            <input type="file" accept=".dump,.zip" class="hidden" @change="uploadRestore" />
          </label>
          <button class="btn btn-ghost btn-sm p-2" title="Refresh" @click="loadData">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>
        </div>
      </div>

      <div v-if="loadingData" class="text-sm text-slate-500 text-center py-6">Loading…</div>
      <div v-else-if="!availableDatabases.length" class="text-sm text-slate-500 py-4 text-center">No databases found.</div>
      <div v-else class="overflow-x-auto -mx-5">
        <table class="table-base w-full min-w-[480px] px-5">
          <thead>
            <tr>
              <th class="pl-5">Database</th>
              <th>Size</th>
              <th>Environment</th>
              <th class="pr-5">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="db in availableDatabases" :key="db.name">
              <td class="pl-5">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm text-slate-200">{{ db.name }}</span>
                  <!-- Show which env uses this DB -->
                  <span
                    v-for="env in dbEnvTags(db.name)"
                    :key="env.type"
                    class="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded"
                    :class="env.pillClass"
                  >{{ env.label }}</span>
                </div>
              </td>
              <td class="text-slate-400 text-sm">{{ db.size }}</td>
              <td class="text-slate-500 text-xs">
                <span v-if="!dbEnvTags(db.name).length" class="text-slate-700">—</span>
              </td>
              <td class="pr-5">
                <div class="flex items-center gap-1.5">
                  <a
                    :href="running ? `https://${projectUrl}/web?db=${db.name}` : '#'"
                    target="_blank"
                    class="btn btn-ghost btn-sm text-xs inline-flex items-center gap-1 py-1 px-2"
                    :class="{ 'opacity-40 pointer-events-none': !running }"
                    title="Open in Odoo"
                    @click.prevent="() => running && window.open(`https://${projectUrl}/web?db=${db.name}`, '_blank')"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                    </svg>
                    Open
                  </a>
                  <button
                    class="btn btn-ghost btn-sm text-xs inline-flex items-center gap-1 py-1 px-2"
                    :disabled="backingUp === db.name"
                    @click="backupDb(db.name)"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                    </svg>
                    {{ backingUp === db.name ? '…' : 'Backup' }}
                  </button>
                  <button
                    class="btn btn-ghost btn-sm text-xs inline-flex items-center gap-1 py-1 px-2"
                    @click="openRestoreModal(db.name)"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    Restore
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Backup Files ──────────────────────────────────────────── -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-slate-300">Backup Files on Disk</h3>
        <button class="btn btn-ghost btn-sm p-2" title="Refresh" @click="loadBackupFiles">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>
      </div>
      <div v-if="!backupFiles.length" class="text-sm text-slate-500 text-center py-4">No backup files found.</div>
      <div v-else class="overflow-x-auto -mx-5">
        <table class="table-base w-full min-w-[540px]">
          <thead>
            <tr>
              <th class="pl-5">File</th>
              <th>Size</th>
              <th>Date</th>
              <th class="pr-5">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in backupFiles" :key="b.filename">
              <td class="pl-5 font-mono text-xs text-slate-300 max-w-[200px] truncate" :title="b.filename">
                {{ b.filename }}
              </td>
              <td class="text-slate-400 text-sm whitespace-nowrap">{{ b.size }}</td>
              <td class="text-slate-500 text-xs whitespace-nowrap">
                {{ new Date(b.modified).toLocaleString() }}
              </td>
              <td class="pr-5">
                <div class="flex items-center gap-1.5">
                  <a
                    :href="`/api/db/${projectName}/download/${b.filename}`"
                    class="btn btn-ghost btn-sm text-xs inline-flex items-center gap-1 py-1 px-2"
                    title="Download"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                    </svg>
                    Download
                  </a>
                  <button
                    class="btn btn-ghost btn-sm text-xs inline-flex items-center gap-1 py-1 px-2"
                    @click="openRestoreModalWithFile(b.filename)"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    Restore to…
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>

  <!-- ── Restore Modal ─────────────────────────────────────────── -->
  <Teleport to="body">
    <div
      v-if="restoreModal.open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="closeRestoreModal" />
      <div class="relative bg-[#0d1117] border border-border rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">

        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-border/50">
          <div>
            <h3 class="text-base font-bold text-white">Restore Database</h3>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="text-xs text-slate-500">Target:</span>
              <code class="text-xs bg-surface-hover px-2 py-0.5 rounded font-mono text-amber-300">
                {{ restoreModal.targetDb }}
              </code>
            </div>
          </div>
          <button class="text-slate-500 hover:text-white transition-colors" @click="closeRestoreModal">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Warning -->
        <div class="mx-6 mt-4 flex items-start gap-2.5 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2.5">
          <svg class="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          </svg>
          <p class="text-xs text-amber-300/80">
            This will <strong class="text-amber-300">overwrite all data</strong> in
            <code class="font-mono">{{ restoreModal.targetDb }}</code>.
            This action cannot be undone.
          </p>
        </div>

        <!-- Mode toggle -->
        <div class="flex mx-6 mt-4 border border-border/50 rounded-lg overflow-hidden">
          <button
            class="flex-1 py-2 text-xs font-semibold transition-colors"
            :class="restoreModal.mode === 'upload' ? 'bg-accent text-white' : 'text-slate-400 hover:text-white'"
            @click="restoreModal.mode = 'upload'"
          >Upload File</button>
          <button
            class="flex-1 py-2 text-xs font-semibold transition-colors border-l border-border/50"
            :class="restoreModal.mode === 'file' ? 'bg-accent text-white' : 'text-slate-400 hover:text-white'"
            @click="restoreModal.mode = 'file'"
          >From Backup</button>
        </div>

        <!-- Upload mode -->
        <div v-if="restoreModal.mode === 'upload'" class="px-6 py-4">
          <label
            class="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-border/50 rounded-xl p-6 cursor-pointer hover:border-accent/50 transition-colors"
            :class="{ 'border-accent/50 bg-accent/5': restoreModal.selectedFile }"
          >
            <svg class="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
            </svg>
            <span v-if="restoreModal.selectedFile" class="text-sm text-accent font-medium text-center">
              {{ restoreModal.selectedFile.name }}
            </span>
            <span v-else class="text-sm text-slate-500 text-center">
              Click to select a .dump or .zip file
            </span>
            <input
              type="file"
              accept=".dump,.zip"
              class="hidden"
              @change="(e) => restoreModal.selectedFile = (e.target as HTMLInputElement).files?.[0] ?? null"
            />
          </label>
        </div>

        <!-- From backup mode -->
        <div v-else class="px-6 py-4">
          <div v-if="!backupFiles.length" class="text-sm text-slate-500 text-center py-4">No backup files found.</div>
          <div v-else class="space-y-1.5 max-h-48 overflow-y-auto">
            <label
              v-for="b in backupFiles"
              :key="b.filename"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors"
              :class="restoreModal.selectedBackup === b.filename
                ? 'border-accent/50 bg-accent/10'
                : 'border-border/40 hover:border-border'"
            >
              <input
                type="radio"
                :value="b.filename"
                v-model="restoreModal.selectedBackup"
                class="accent-accent"
              />
              <div class="flex-1 min-w-0">
                <div class="font-mono text-xs text-slate-200 truncate">{{ b.filename }}</div>
                <div class="text-[11px] text-slate-500 mt-0.5">{{ b.size }} · {{ new Date(b.modified).toLocaleString() }}</div>
              </div>
            </label>
          </div>
        </div>

        <!-- Modal target DB override (for "Restore to…" from backup list) -->
        <div v-if="restoreModal.showTargetInput" class="px-6 pb-2">
          <label class="block text-xs text-slate-400 mb-1.5">Restore into database:</label>
          <input
            v-model="restoreModal.targetDb"
            :list="`restore-target-dbs`"
            class="input w-full text-sm"
            placeholder="database name"
          />
          <datalist id="restore-target-dbs">
            <option v-for="d in availableDatabases" :key="d.name" :value="d.name" />
          </datalist>
        </div>

        <!-- Footer -->
        <div class="flex gap-3 justify-end px-6 py-4 border-t border-border/50">
          <button class="btn btn-ghost" @click="closeRestoreModal" :disabled="restoring">Cancel</button>
          <button
            class="btn btn-primary inline-flex items-center gap-2"
            :disabled="restoring || !canRestore"
            @click="confirmRestore"
          >
            <svg v-if="restoring" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            {{ restoring ? 'Restoring…' : 'Restore' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

const props = defineProps<{
  projectName: string
  projectUrl:  string
  currentBranch: string | undefined
  running: boolean
  active: boolean
}>()

const notify = useNotificationsStore()

// ── Env definitions ──────────────────────────────────────────────
const ENV_DEFS = [
  {
    type:             'production' as const,
    label:            'Production',
    stripClass:       'bg-gradient-to-r from-emerald-500 to-green-400',
    dotActive:        'bg-emerald-500',
    labelColor:       'text-emerald-400',
    pillClass:        'bg-emerald-500/20 text-emerald-400',
    deployActiveClass: 'bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25',
  },
  {
    type:             'staging' as const,
    label:            'Staging',
    stripClass:       'bg-gradient-to-r from-amber-500 to-orange-400',
    dotActive:        'bg-amber-500',
    labelColor:       'text-amber-400',
    pillClass:        'bg-amber-500/20 text-amber-400',
    deployActiveClass: 'bg-amber-500/15 border border-amber-500/40 text-amber-300 hover:bg-amber-500/25',
  },
  {
    type:             'dev' as const,
    label:            'Dev',
    stripClass:       'bg-gradient-to-r from-sky-500 to-blue-400',
    dotActive:        'bg-sky-500',
    labelColor:       'text-sky-400',
    pillClass:        'bg-sky-500/20 text-sky-400',
    deployActiveClass: 'bg-sky-500/15 border border-sky-500/40 text-sky-300 hover:bg-sky-500/25',
  },
] as const

type EnvType = 'production' | 'staging' | 'dev'

// ── State ────────────────────────────────────────────────────────
const loadingData = ref(false)

const envConfig = reactive<Record<EnvType, { branch: string; db: string }>>({
  production: { branch: '', db: '' },
  staging:    { branch: '', db: '' },
  dev:        { branch: '', db: '' },
})

const editMode   = reactive<Record<EnvType, boolean>>({ production: false, staging: false, dev: false })
const saving     = reactive<Record<EnvType, boolean>>({ production: false, staging: false, dev: false })
const editValues = reactive<Record<EnvType, { branch: string; db: string }>>({
  production: { branch: '', db: '' },
  staging:    { branch: '', db: '' },
  dev:        { branch: '', db: '' },
})

const availableBranches  = ref<string[]>([])
const availableDatabases = ref<Array<{ name: string; size: string }>>([])
const backupFiles        = ref<Array<{ filename: string; size: string; modified: string }>>([])

const deploying  = ref<string | null>(null)
const backingUp  = ref<string | null>(null)
const restoring  = ref(false)

const restoreModal = reactive({
  open:            false,
  targetDb:        '',
  mode:            'upload' as 'upload' | 'file',
  selectedFile:    null as File | null,
  selectedBackup:  '',
  showTargetInput: false,
})

const canRestore = computed(() =>
  restoreModal.targetDb.trim() &&
  (restoreModal.mode === 'upload' ? !!restoreModal.selectedFile : !!restoreModal.selectedBackup)
)

// ── Helpers ──────────────────────────────────────────────────────
function isActive(type: EnvType): boolean {
  const b = envConfig[type].branch
  return !!b && b === props.currentBranch
}

function dbEnvTags(dbName: string) {
  return ENV_DEFS.filter(e => envConfig[e.type].db === dbName)
}

function openEnv(type: EnvType) {
  const db = envConfig[type].db
  if (!db || !props.running) return
  window.open(`https://${props.projectUrl}/web?db=${db}`, '_blank')
}

// ── Data loading ─────────────────────────────────────────────────
async function loadData() {
  loadingData.value = true
  try {
    const [envRes, dbRes] = await Promise.all([
      fetch(`/api/project/${props.projectName}/environments`),
      fetch(`/api/db/${props.projectName}/list`),
    ])
    const envData = await envRes.json()
    const dbData  = await dbRes.json()

    envConfig.production = { branch: envData.production_branch || '', db: envData.production_db || '' }
    envConfig.staging    = { branch: envData.staging_branch    || '', db: envData.staging_db    || '' }
    envConfig.dev        = { branch: envData.dev_branch        || '', db: envData.dev_db        || '' }

    availableBranches.value  = (envData.branches  as string[]) || []
    availableDatabases.value = (dbData.databases  as Array<{ name: string; size: string }>) || []
  } catch {
    notify.add('error', 'Failed to load environments')
  } finally {
    loadingData.value = false
  }
  loadBackupFiles()
}

async function loadBackupFiles() {
  const res  = await fetch(`/api/db/${props.projectName}/backups`)
  const data = await res.json()
  backupFiles.value = data.backups || []
}

const loaded = ref(false)
watch(() => props.active, (v) => { if (v && !loaded.value) { loaded.value = true; loadData() } }, { immediate: true })

// ── Edit ─────────────────────────────────────────────────────────
function toggleEdit(type: EnvType) {
  if (editMode[type]) {
    cancelEdit(type)
  } else {
    editValues[type] = { ...envConfig[type] }
    editMode[type]   = true
  }
}

function cancelEdit(type: EnvType) {
  editMode[type] = false
}

async function saveEnv(type: EnvType) {
  saving[type] = true
  try {
    const body: Record<string, string> = {}
    body[`${type}_branch`] = editValues[type].branch
    body[`${type}_db`]     = editValues[type].db
    const res = await fetch(`/api/project/${props.projectName}/environments`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    })
    if (res.ok) {
      envConfig[type] = { ...editValues[type] }
      editMode[type]  = false
      notify.add('success', `${type.charAt(0).toUpperCase() + type.slice(1)} environment saved`)
    } else {
      notify.add('error', 'Failed to save environment')
    }
  } catch {
    notify.add('error', 'Failed to save environment')
  } finally {
    saving[type] = false
  }
}

// ── Deploy ───────────────────────────────────────────────────────
async function deployEnv(type: EnvType) {
  deploying.value = type
  try {
    const res  = await fetch(`/api/project/${props.projectName}/environments/${type}/deploy`, { method: 'POST' })
    const data = await res.json()
    if (data.ok) {
      notify.add('success', `Deploying ${type} → ${data.branch}. Check the Logs tab to follow progress.`)
    } else {
      notify.add('error', data.error || 'Deploy failed')
    }
  } catch {
    notify.add('error', 'Deploy failed')
  } finally {
    deploying.value = null
  }
}

// ── Backup ───────────────────────────────────────────────────────
async function backupDb(dbname: string) {
  if (!dbname) return
  backingUp.value = dbname
  notify.add('info', `Backing up ${dbname}…`)
  try {
    const res  = await fetch(`/api/db/${props.projectName}/backup/${dbname}`, { method: 'POST' })
    const data = await res.json()
    if (data.ok) {
      notify.add('success', `Backup ready: ${data.filename}`)
      window.location.href = data.download_url
      loadBackupFiles()
    } else {
      notify.add('error', data.error || 'Backup failed')
    }
  } catch {
    notify.add('error', 'Backup failed')
  } finally {
    backingUp.value = null
  }
}

// ── Restore ──────────────────────────────────────────────────────
function openRestoreModal(targetDb: string) {
  Object.assign(restoreModal, {
    open:            true,
    targetDb,
    mode:            'upload',
    selectedFile:    null,
    selectedBackup:  '',
    showTargetInput: false,
  })
}

function openRestoreModalWithFile(filename: string) {
  Object.assign(restoreModal, {
    open:            true,
    targetDb:        '',
    mode:            'file',
    selectedFile:    null,
    selectedBackup:  filename,
    showTargetInput: true,
  })
}

function closeRestoreModal() {
  if (restoring.value) return
  restoreModal.open = false
}

async function confirmRestore() {
  if (!canRestore.value) return
  restoring.value = true
  try {
    let res: Response
    if (restoreModal.mode === 'upload' && restoreModal.selectedFile) {
      const form = new FormData()
      form.append('file', restoreModal.selectedFile)
      res = await fetch(`/api/db/${props.projectName}/restore/${restoreModal.targetDb}`, { method: 'POST', body: form })
    } else {
      res = await fetch(`/api/db/${props.projectName}/restore/${restoreModal.targetDb}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ filename: restoreModal.selectedBackup }),
      })
    }
    const data = await res.json()
    if (data.ok) {
      notify.add('success', `Restored into ${restoreModal.targetDb}`)
      restoreModal.open = false
      loadData()
    } else {
      notify.add('error', data.error || 'Restore failed')
    }
  } catch {
    notify.add('error', 'Restore failed')
  } finally {
    restoring.value = false
  }
}

async function uploadRestore(evt: Event) {
  const file = (evt.target as HTMLInputElement).files?.[0]
  if (!file) return
  Object.assign(restoreModal, {
    open:            true,
    targetDb:        '',
    mode:            'upload',
    selectedFile:    file,
    selectedBackup:  '',
    showTargetInput: true,
  })
}

// expose for parent to call window — needed for table open buttons
const window = globalThis.window
</script>
