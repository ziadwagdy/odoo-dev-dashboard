import { describe, it, expect, beforeEach, vi } from 'vitest'

// capture what the native constructors receive
const seen: { es: string[]; ws: string[] } = { es: [], ws: [] }

class FakeEventSource {
  constructor(public url: string | URL) { seen.es.push(String(url)) }
}
class FakeWebSocket {
  constructor(public url: string | URL) { seen.ws.push(String(url)) }
}

beforeEach(async () => {
  seen.es.length = 0
  seen.ws.length = 0
  ;(window as any).EventSource = FakeEventSource
  ;(window as any).WebSocket = FakeWebSocket
  localStorage.clear()
  vi.resetModules()
  await import('./authedStreams')
})

describe('authedStreams', () => {
  it('adds the token to same-origin stream URLs', () => {
    localStorage.setItem('auth_token', 'tok123')
    new EventSource('/stream/status')
    expect(seen.es[0]).toBe('/stream/status?token=tok123')
  })

  it('keeps existing query parameters', () => {
    localStorage.setItem('auth_token', 'tok123')
    new EventSource('/stream/logs/odoo17-app?tail=500&follow=true')
    expect(seen.es[0]).toContain('tail=500')
    expect(seen.es[0]).toContain('token=tok123')
  })

  it('covers the onboarding stream and websockets', () => {
    localStorage.setItem('auth_token', 'tok123')
    new EventSource('/api/onboard/stream/acme')
    new WebSocket(`ws://${location.host}/ws/notebook/odoo17`)
    expect(seen.es[0]).toContain('token=tok123')
    expect(seen.ws[0]).toContain('token=tok123')
  })

  it('never leaks the token to other paths or other origins', () => {
    localStorage.setItem('auth_token', 'tok123')
    new EventSource('/api/projects')
    new EventSource('https://evil.example/stream/status')
    expect(seen.es[0]).toBe('/api/projects')
    expect(seen.es[1]).toBe('https://evil.example/stream/status')
  })

  it('does nothing when there is no token', () => {
    new EventSource('/stream/status')
    expect(seen.es[0]).toBe('/stream/status')
  })
})
