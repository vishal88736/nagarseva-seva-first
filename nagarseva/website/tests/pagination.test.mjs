import assert from 'node:assert/strict'
import { test } from 'node:test'
import { collectPages } from '../src/urban/pagination.ts'

test('All records load beyond the first1000 without truncating or duplicating', async () => {
  const source = Array.from({ length: 2597 }, (_, i) => ({ id: String(i) }))
  const calls = []
  const rows = await collectPages(async (page, size) => { calls.push(page); return { items: source.slice((page - 1) * size, page * size), total: source.length } })
  assert.equal(rows.length, 2597); assert.deepEqual(calls, [1, 2, 3])
})
test('Changing counts, early empty pages, duplicate IDs and download limits are explicit errors', async () => {
  await assert.rejects(collectPages(async page => ({ items: [{ id: String(page) }], total: page === 1 ? 2 : 3 }), 1), /changed/)
  await assert.rejects(collectPages(async () => ({ items: [], total: 2 })), /incomplete/)
  await assert.rejects(collectPages(async () => ({ items: [{ id: 'same' }], total: 2 }), 1), /Duplicate/)
  await assert.rejects(collectPages(async () => ({ items: [], total: 20001 })), /limit/)
  assert.deepEqual(await collectPages(async () => ({ items: [], total: 0 })), [])
})
