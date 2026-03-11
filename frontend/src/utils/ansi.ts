const ANSI_COLORS: Record<number, string> = {
  30: '#374151', 31: '#f87171', 32: '#4ade80', 33: '#fbbf24',
  34: '#818cf8', 35: '#c084fc', 36: '#67e8f9', 37: '#e2e8f0',
  90: '#6b7280', 91: '#fca5a5', 92: '#86efac', 93: '#fde68a',
  94: '#a5b4fc', 95: '#d8b4fe', 96: '#a5f3fc', 97: '#f8fafc',
}

export function ansiToHtml(text: string): string {
  let html = ''
  let currentStyle = ''
  const parts = text.split(/(\x1b\[[0-9;]*m)/)
  for (const part of parts) {
    if (part.startsWith('\x1b[')) {
      const codes = part.slice(2, -1).split(';').map(Number)
      const styles: string[] = []
      for (const code of codes) {
        if (code === 0) { currentStyle = ''; styles.length = 0 }
        else if (code === 1) styles.push('font-weight:bold')
        else if (ANSI_COLORS[code]) styles.push(`color:${ANSI_COLORS[code]}`)
      }
      currentStyle = styles.join(';')
    } else if (part) {
      const escaped = part.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      html += currentStyle ? `<span style="${currentStyle}">${escaped}</span>` : escaped
    }
  }
  return html
}

export function odooLogClass(line: string): string {
  if (/ CRITICAL /.test(line)) return 'log-critical'
  if (/ ERROR /.test(line)) return 'log-error'
  if (/ WARNING /.test(line)) return 'log-warning'
  if (/ DEBUG /.test(line)) return 'log-debug'
  return 'log-info'
}
