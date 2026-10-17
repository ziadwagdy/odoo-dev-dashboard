import { describe, it, expect } from 'vitest'

const files = import.meta.glob('./BranchTab.vue', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const branchTab = Object.values(files)[0]

describe('Branches tab labels', () => {
  it('the submodule action is a git pull, so it is called "Pull" (not "Update All")', () => {
    const block = branchTab.slice(branchTab.indexOf('<!-- Submodules -->'))
    const button = block.slice(block.indexOf('@click="updateSubmodules"'), block.indexOf('</button>', block.indexOf('@click="updateSubmodules"')))
    expect(button).toMatch(/>\s*Pull\s*$/m)
    expect(button).not.toContain('Update All')
  })
})
