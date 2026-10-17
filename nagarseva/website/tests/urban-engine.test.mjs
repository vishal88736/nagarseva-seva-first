import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { score, prioritize, DEFAULT_WEIGHTS, compareScenarios, defaultAssumptions, networkAccess, emptyState, planWork, actOnWork, reportIssue, resolveIssue, verifiedCount, overdue } from '../src/urban/engine.ts'

const data = JSON.parse(readFileSync(new URL('../../shared/urban-demo.json', import.meta.url)))
const cases = JSON.parse(readFileSync(new URL('../../shared/urban-validation-cases.json', import.meta.url)))
for (const fixture of cases) test(`Shared Python/browser fixture: ${fixture.id}`, () => {
  const result = score(fixture.indicators, fixture.weights)
  for (const field of ['score', 'lower', 'upper', 'coverage_pct']) assert.equal(result[field], fixture[field], field)
})
test('Rankings and equal-weight comparison change as expected', () => {
  const report = prioritize(data.clusters)
  assert.deepEqual(report.items.map(row => row.id), ['US-A', 'US-C', 'US-B', 'US-D', 'US-E'])
  assert.equal(report.items[4].rank, null)
  assert.equal(report.rank_correlation, .8)
  const equal = prioritize(data.clusters, { water: 1, sanitation: 1, housing: 1, access: 1, risk: 1 })
  assert.equal(equal.items[0].id, 'US-C')
  assert.equal(equal.rank_correlation, 1)
})
test('Zero totals, negative weights, missing keys and non-finite values are rejected', () => {
  for (const weights of [{ water: 0, sanitation: 0, housing: 0, access: 0, risk: 0 }, { ...DEFAULT_WEIGHTS, water: -1 }, { water: 1 }, { ...DEFAULT_WEIGHTS, risk: NaN }]) assert.throws(() => prioritize(data.clusters, weights))
  assert.throws(() => score({ ...data.clusters[0].indicators, water: true }))
})
test('Shared-rank ties do not fabricate a correlation', () => {
  const clusters = data.clusters.slice(0, 2).map(cluster => ({ ...cluster, indicators: { water: 50, sanitation: 50, housing: 50, access: 50, risk: 50 } }))
  const result = prioritize(clusters)
  assert.deepEqual(result.items.map(row => row.rank), [1, 1])
  assert.equal(result.rank_correlation, null)
})
test('Scenario cost matches the hand-worked 1,199 INR example', () => {
  const assumptions = { households: 10, contingency_pct: 10, temporary_rent_per_month: 20, annual_maintenance_per_household: 12, include_relocation: false, relocation_reason: '', options: ['upgrade', 'redevelop'].map(kind => ({ kind, unit_cost_inr: 100, shared_works_inr: 50, months: 6, temporary_months: 1, disrupted_share: .2, assumed_service_coverage_pct: 80 })) }
  const result = compareScenarios(data, 'US-A', assumptions).options[0]
  assert.equal(result.total_cost_inr, 1199); assert.equal(result.temporary_support_inr, 40); assert.equal(result.annual_maintenance_inr, 120)
  assert.equal(result.disrupted_households, 2); assert.ok(result.access.every(row => row.change_m === 0))
})
test('Unavailable household count blocks the scenario', () => assert.throws(() => compareScenarios(data, 'US-E', defaultAssumptions(data.clusters[4]))))
test('Disconnected facilities stay unavailable instead of receiving zero distance', () => {
  const result = networkAccess({ ...data, network: { ...data.network, edges: [] } }, 'n00')
  assert.ok(result.slice(0, 3).every(row => row.distance_m === null)); assert.equal(result[3].distance_m, 0)
})
test('Relocation is opt-in and needs a reason', () => {
  const input = defaultAssumptions(data.clusters[0])
  input.options.push({ ...input.options[1], kind: 'relocate' })
  assert.throws(() => compareScenarios(data, 'US-A', input))
  input.include_relocation = true
  assert.throws(() => compareScenarios(data, 'US-A', input))
  input.relocation_reason = 'Explicit demonstration hazard-avoidance assumption.'
  assert.equal(compareScenarios(data, 'US-A', input).options.length, 3)
})
const at = '2026-10-18T10:00:00.000Z'
const later = '2026-10-18T11:00:00.000Z'
function planned() { return planWork(emptyState(), { cluster_id: 'US-A', title: 'Water improvement demo', service: 'water', target: 6, due_date: '2026-10-17', actor: 'Contractor' }, at) }
function completed() { let state = planned(); const id = state.works[0].id; state = actOnWork(state, id, { action: 'start', actor: 'Contractor', notes: 'Started the demo work' }, at); return actOnWork(state, id, { action: 'complete', actor: 'Contractor', notes: 'Physical completion claimed' }, at) }
function withEvidence() { const state = completed(); state.evidence.push({ id: 'EVI-A', work_id: state.works[0].id, cluster_id: 'US-A', filename: 'inspection.txt', actor: 'Inspector', notes: 'Demo inspection', uploaded_at: at, bytes: 10, sha256: 'demo-only', content_type: 'text/plain', synthetic: true }); return state }
const review = { action: 'verify', actor: 'Reviewer', notes: 'Independent demo inspection', evidence_id: 'EVI-A', measured_value: 6, observed_at: at, functioning_confirmed: true }
test('Physical completion never increments verified services', () => { const state = completed(); assert.equal(state.works[0].verification, 'unverified'); assert.equal(verifiedCount(state), 0); assert.equal(overdue(planned().works[0], '2026-10-18'), true) })
test('Verification needs matching evidence, a different reviewer and a passing measurement', () => {
  const state = withEvidence(), id = state.works[0].id
  assert.throws(() => actOnWork(state, id, { ...review, actor: 'Inspector' }, at))
  assert.throws(() => actOnWork(state, id, { ...review, measured_value: 5 }, at))
  assert.throws(() => actOnWork(state, id, { ...review, evidence_id: 'unknown' }, at))
  assert.equal(state.works[0].verification, 'unverified')
  assert.equal(verifiedCount(actOnWork(state, id, review, at)), 1)
})
test('Complaint disputes verification; response needs fresh evidence before a new review', () => {
  let state = withEvidence(); const id = state.works[0].id
  state = actOnWork(state, id, review, at)
  state = reportIssue(state, id, 'Water stopped in the demo again', later)
  assert.equal(verifiedCount(state), 0); assert.equal(state.works[0].verification, 'disputed')
  assert.throws(() => actOnWork(state, id, { ...review, observed_at: later }, later))
  state = resolveIssue(state, state.complaints[0].id, 'Officer', 'Demo repair response recorded', later)
  assert.equal(state.works[0].verification, 'disputed')
  assert.throws(() => actOnWork(state, id, { ...review, observed_at: later }, later))
  state.evidence.push({ ...state.evidence[0], id: 'EVI-B', uploaded_at: later })
  state = actOnWork(state, id, { ...review, evidence_id: 'EVI-B', observed_at: later }, later)
  assert.equal(verifiedCount(state), 1)
})
test('An at-most drainage target uses the correct inequality', () => {
  const state = withEvidence(); state.works[0].service = 'drainage'; state.works[0].direction = 'at_most'; state.works[0].target = 0
  assert.throws(() => actOnWork(state, state.works[0].id, { ...review, measured_value: 1 }, at))
  assert.equal(verifiedCount(actOnWork(state, state.works[0].id, { ...review, measured_value: 0 }, at)), 1)
})
