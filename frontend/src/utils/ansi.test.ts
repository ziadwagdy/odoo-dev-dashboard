import { describe, it, expect } from 'vitest'
import { ansiToHtml } from './ansi'

describe('ansiToHtml', () => {
  it('escapes HTML coming from container logs (no script injection)', () => {
    const html = ansiToHtml('<img src=x onerror=alert(1)> & <script>evil()</script>')
    expect(html).not.toContain('<img')
    expect(html).not.toContain('<script')
    expect(html).toContain('&lt;img')
    expect(html).toContain('&amp;')
  })

  it('still renders colours as spans', () => {
    expect(ansiToHtml('\x1b[31merror\x1b[0m')).toContain('<span style="color:#f87171">error</span>')
  })

  it('returns plain text unchanged', () => {
    expect(ansiToHtml('hello world')).toBe('hello world')
  })
})
