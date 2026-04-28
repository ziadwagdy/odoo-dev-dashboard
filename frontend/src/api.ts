/**
 * Thin fetch wrapper that injects the auth token from localStorage.
 * Use this for all authenticated API calls instead of raw fetch().
 */
export async function api(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('auth_token')
  const headers: Record<string, string> = { ...(options.headers as Record<string, string> || {}) }

  if (token) {
    headers['Authorization'] = `Token ${token}`
  }
  // Set Content-Type for JSON bodies unless FormData
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(url, { ...options, headers })

  // Token expired or revoked — force logout
  if (response.status === 401) {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_role')
    window.location.href = '/login'
  }

  return response
}
