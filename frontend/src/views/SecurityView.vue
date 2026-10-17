<template>
  <SidebarLayout>
    <template #breadcrumb>
      <Breadcrumb :crumbs="[{ label: 'Security' }]" />
    </template>

    <div class="max-w-5xl">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
      <div>
        <h1 class="text-xl font-bold text-white">Security alerts</h1>
        <p class="text-xs text-slate-500">Real-time detections from the project databases. Repeats are grouped into one alert.</p>
      </div>
      <div class="flex flex-wrap gap-2 items-center">
        <span v-if="sec.pushState === 'unsupported'" class="text-xs text-slate-500">This browser cannot receive push notifications.</span>
        <span v-else-if="sec.pushState === 'blocked'" class="text-xs text-amber-400">Notifications are blocked in this browser's site settings.</span>
        <template v-else>
          <button v-if="sec.pushState !== 'on'" class="btn btn-primary btn-sm" @click="sec.enablePush()">Enable push notifications</button>
          <template v-else>
            <span class="text-xs text-emerald-400">● push enabled on this device</span>
            <button class="btn btn-ghost btn-sm" @click="sec.testPush()">Send test</button>
            <button class="btn btn-ghost btn-sm" @click="sec.disablePush()">Turn off</button>
          </template>
        </template>
      </div>
    </div>

    <div v-if="!sec.alerts.length" class="card text-sm text-slate-400">No alerts. Nothing suspicious has been detected.</div>
    <div v-for="a in sec.alerts" :key="a.id" class="card mb-3" :class="a.status === 'acknowledged' ? 'opacity-60' : ''">
      <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded text-white" :class="sevClass(a.severity)">{{ a.severity }}</span>
            <span class="text-sm font-semibold text-white">{{ a.summary }}</span>
          </div>
          <div class="text-xs text-slate-400">
            {{ a.count }} event(s) · first {{ new Date(a.first_seen).toLocaleString() }} · last {{ new Date(a.last_seen).toLocaleString() }}
          </div>
          <div v-if="a.sample" class="font-mono text-[11px] text-slate-500 mt-1 break-all">{{ a.sample }}</div>
          <div v-if="a.status === 'acknowledged'" class="text-xs text-slate-500 mt-1">
            acknowledged by {{ a.acknowledged_by }}<span v-if="a.note"> — “{{ a.note }}”</span>
          </div>
        </div>
        <button v-if="a.status === 'open'" class="btn btn-ghost btn-sm shrink-0" @click="ack(a.id)">Acknowledge…</button>
      </div>
    </div>
    </div>
  </SidebarLayout>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import SidebarLayout from '@/layouts/SidebarLayout.vue'
import Breadcrumb from '@/components/Breadcrumb.vue'
import { useSecurityStore } from '@/stores/security'

const sec = useSecurityStore()
let timer: number | undefined

const sevClass = (s: string) => ({ critical: 'bg-red-600', high: 'bg-orange-500', warning: 'bg-amber-600', info: 'bg-slate-600' } as Record<string, string>)[s]

function ack(id: number) {
  const note = window.prompt('Note for the audit log (what was it / what did you do?)', '')
  if (note === null) return
  sec.acknowledge(id, note)
}

onMounted(() => { sec.fetchAlerts(); sec.refreshPushState(); timer = window.setInterval(() => sec.fetchAlerts(), 15000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>
