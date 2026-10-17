import { describe, it, expect } from 'vitest'
import { databaseNames } from './databases'

describe('databaseNames', () => {
  it('reads the API shape { databases: [...] }', () => {
    expect(databaseNames({ databases: [{ name: 'sivas', size: '1 MB' }, { name: 'sivas-2' }] })).toEqual(['sivas', 'sivas-2'])
  })

  it('still accepts a bare array', () => {
    expect(databaseNames([{ name: 'a' }])).toEqual(['a'])
  })

  it('returns an empty list for errors and garbage instead of throwing', () => {
    expect(databaseNames({ error: 'boom' })).toEqual([])
    expect(databaseNames(null)).toEqual([])
    expect(databaseNames(undefined)).toEqual([])
    expect(databaseNames('x')).toEqual([])
  })

  it('skips entries without a name', () => {
    expect(databaseNames({ databases: [{ name: 'ok' }, {}, { name: '' }, null] })).toEqual(['ok'])
  })
})
