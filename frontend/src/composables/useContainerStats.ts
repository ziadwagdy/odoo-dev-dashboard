/**
 * Shared per-container stats SSE.
 * Multiple components (CpuGauge, MemoryBar) subscribe to the same stream.
 * The SSE is opened once per container and closed when all subscribers unmount.
 */
import { ref, onUnmounted } from 'vue'

interface StatsEntry {
  cpu:      number | null
  memUsed:  number | null
  memLimit: number | null
  source:   EventSource
  refCount: number
  listeners: Set<(e: StatsEntry) => void>
}

const cache = new Map<string, StatsEntry>()

export function useContainerStats(container: string) {
  const cpu      = ref<number | null>(null)
  const memUsed  = ref<number | null>(null)
  const memLimit = ref<number | null>(null)

  if (!cache.has(container)) {
    const entry: StatsEntry = {
      cpu: null, memUsed: null, memLimit: null,
      source: new EventSource(`/stream/stats/${container}`),
      refCount: 0,
      listeners: new Set(),
    }
    entry.source.onmessage = (evt) => {
      const d = JSON.parse(evt.data)
      if (d.cpu_pct      != null) entry.cpu      = d.cpu_pct
      if (d.mem_used_mb  != null) entry.memUsed  = d.mem_used_mb
      if (d.mem_limit_mb != null) entry.memLimit = d.mem_limit_mb
      entry.listeners.forEach(fn => fn(entry))
    }
    cache.set(container, entry)
  }

  const entry = cache.get(container)!
  entry.refCount++

  // Seed with cached values so second subscriber doesn't show -- briefly
  cpu.value      = entry.cpu
  memUsed.value  = entry.memUsed
  memLimit.value = entry.memLimit

  const listener = (e: StatsEntry) => {
    cpu.value      = e.cpu
    memUsed.value  = e.memUsed
    memLimit.value = e.memLimit
  }
  entry.listeners.add(listener)

  onUnmounted(() => {
    entry.listeners.delete(listener)
    entry.refCount--
    if (entry.refCount <= 0) {
      entry.source.close()
      cache.delete(container)
    }
  })

  return { cpu, memUsed, memLimit }
}
