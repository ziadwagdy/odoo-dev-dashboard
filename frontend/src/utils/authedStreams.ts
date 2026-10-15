// EventSource and WebSocket cannot set an Authorization header, but the
// backend now requires authentication on /stream/*, /api/onboard/stream/* and
// /ws/*. Append the session token as a query parameter for same-origin
// requests to those paths (nginx logs the path only, never the query string).
const TOKEN_KEY = 'auth_token'
const PATHS = /^\/(stream|ws|api\/onboard\/stream)\//

function withToken(raw: string): string {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return raw
    const u = new URL(raw, location.href)
    if (u.host !== location.host || !PATHS.test(u.pathname)) return raw
    u.searchParams.set('token', token)
    const isWs = u.protocol === 'ws:' || u.protocol === 'wss:'
    return isWs ? u.toString() : u.pathname + u.search
  } catch {
    return raw
  }
}

const NativeEventSource = window.EventSource
window.EventSource = class extends NativeEventSource {
  constructor(url: string | URL, init?: EventSourceInit) {
    super(withToken(String(url)), init)
  }
} as typeof EventSource

const NativeWebSocket = window.WebSocket
window.WebSocket = class extends NativeWebSocket {
  constructor(url: string | URL, protocols?: string | string[]) {
    super(withToken(String(url)), protocols)
  }
} as typeof WebSocket
export {}
