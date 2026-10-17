import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// Every hard-coded hex colour in a component must either have a light-theme override in
// style.css or be an intentionally dark surface (code/terminal blocks) or the brand accent.
const vues = import.meta.glob(['./**/*.vue'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const css = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf8')
const INTENTIONALLY_FIXED = new Set(['0a0c12', '0f1117', '6366f1'])   // code blocks, notebook, accent

describe('theme compliance', () => {
  const used = new Map<string, Set<string>>()
  for (const [file, src] of Object.entries(vues)) {
    for (const m of src.matchAll(/\b(?:bg|border|text|ring|from|to|via)-\[#([0-9a-fA-F]{6})\]/g)) {
      const hex = m[1].toLowerCase()
      if (!used.has(hex)) used.set(hex, new Set())
      used.get(hex)!.add(file)
    }
  }

  it('finds the hard-coded colours at all (guards the test itself)', () => {
    expect(used.size).toBeGreaterThan(2)
  })

  for (const [hex, files] of used) {
    if (INTENTIONALLY_FIXED.has(hex)) continue
    it(`#${hex} has a light-theme override (used in ${[...files].join(', ')})`, () => {
      expect(css.toLowerCase(), `add an override for #${hex} in style.css or use a theme token`)
        .toContain(`\\[\\#${hex}\\]`)
    })
  }
})
