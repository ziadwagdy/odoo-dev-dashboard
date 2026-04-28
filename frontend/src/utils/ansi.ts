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

/** Classify a generic output line (deploy/git/docker) into a CSS class. */
export function classifyLine(line: string): string {
  const t = line.trim()

  // Odoo structured log levels take priority
  if (/ CRITICAL /.test(line)) return 'log-critical'
  if (/ ERROR /.test(line))    return 'log-error'
  if (/ WARNING /.test(line))  return 'log-warning'
  if (/ DEBUG /.test(line))    return 'log-debug'

  // Docker build steps: #1 [internal] ..., #2 FROM ..., STEP 1/N etc.
  if (/^#\d+\s/.test(t) || /^Step\s+\d+\/\d+/i.test(t)) return 'log-step'

  // Errors (case-insensitive keywords)
  if (/\berror\b|\bfailed\b|\bfailure\b|\bexception\b|\btraceback\b/i.test(t)) return 'log-error'

  // Warnings
  if (/\bwarn(ing)?\b/i.test(t)) return 'log-warning'

  // Success / completion signals
  if (/\b(success(fully)?|complete[d]?|done|built|pushed|pulled|cloned|started|healthy)\b/i.test(t)) return 'log-success'

  // Git output highlights
  if (/^(From |Branch |Updating |Fast-forward|Already up to date|HEAD is now)/i.test(t)) return 'log-success'
  if (/^\s*[\+\-]{3}\s/.test(t) || /^@@/.test(t)) return 'log-warning'   // diff hunks
  if (/^\s*remote:/i.test(t)) return 'log-dim'

  // Separator / divider lines
  if (/^[-=]{3,}/.test(t) || /^---/.test(t)) return 'log-separator'

  // Exit code lines
  if (/exit code: 0/.test(t)) return 'log-success'
  if (/exit code: [^0]/.test(t)) return 'log-error'

  return 'log-info'
}

export interface LogLine { raw: string; html: string; cls: string }

export function parseLine(raw: string): LogLine {
  return { raw, html: ansiToHtml(raw), cls: classifyLine(raw) }
}
