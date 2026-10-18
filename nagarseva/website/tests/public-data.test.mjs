import assert from 'node:assert/strict'
import { test } from 'node:test'
import { encodeCsv } from '../src/urban/csv.ts'
import { DEFAULT_WEIGHTS, score, compareScenarios } from '../src/urban/engine.ts'

test('CSV preserves missing cells and protects spreadsheet formulas', () => {
  const csv = encodeCsv([{ name: '=danger()', score: null, source: 'quoted "title"' }])
  assert.ok(csv.includes('"\'=danger()"'))
  assert.ok(csv.includes(',"",'))
  assert.ok(csv.includes('"quoted ""title"""'))
})
test('Acquired records without observations remain completely unranked', () => {
  const result = score(Object.fromEntries(Object.keys(DEFAULT_WEIGHTS).map(key => [key, null])))
  assert.equal(result.score, null); assert.equal(result.coverage_pct, 0); assert.equal(result.upper, 100)
})
test('No settlement origin or network never yields an invented zero distance', () => {
  const cluster = { id: 'fixture', node_id: '', indicators: Object.fromEntries(Object.keys(DEFAULT_WEIGHTS).map(key => [key,null])) }
  const data = { clusters: [cluster], network: { nodes: [], edges: [] }, amenities: [], relocation_node_id: '' }
  const option = { unit_cost_inr: 100, shared_works_inr: 50, months: 6, temporary_months: 1, disrupted_share: .2, assumed_service_coverage_pct: 80 }
  const result = compareScenarios(data, 'fixture', { households: 10, contingency_pct: 10, temporary_rent_per_month: 20, annual_maintenance_per_household: 12, include_relocation: false, options: ['upgrade','redevelop'].map(kind => ({ ...option, kind })) })
  assert.deepEqual(result.options[0].access, [])
  assert.equal(result.options[0].total_cost_inr, 1199)
})
