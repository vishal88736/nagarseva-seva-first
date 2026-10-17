export const KEYS = ['water', 'sanitation', 'housing', 'access', 'risk'] as const
export type Key = typeof KEYS[number]
export type Weights = Record<Key, number>
export const DEFAULT_WEIGHTS: Weights = { water: .30, sanitation: .25, housing: .20, access: .15, risk: .10 }
export const INDICATORS: Record<Key, { label: string; short: string; color: string; description: string }> = {
  water: { label: 'Water deficit', short: 'W', color: '#267e9c', description: 'Normalized water-service deficit; higher means greater need.' },
  sanitation: { label: 'Sanitation & drainage', short: 'S', color: '#4c8870', description: 'Normalized sanitation and drainage deficit.' },
  housing: { label: 'Housing conditions', short: 'H', color: '#c78c41', description: 'Housing-condition deficit; not a structural-safety or legal-eligibility assessment.' },
  access: { label: 'Essential-amenity access', short: 'A', color: '#8b76a4', description: 'Normalized amenity-access deficit; not evidence that a mapped facility is usable.' },
  risk: { label: 'Environmental risk', short: 'R', color: '#c36e59', description: 'Relevant environmental/infrastructure risk index; not a satellite-derived household label.' },
}
export type Cluster = {
  id: string; name: string; node_id: string; households: number | null; households_source: string; synthetic: boolean
  geometry: { type: string; coordinates: number[][][] }
  indicators: Record<Key, number | null>
  provenance: Record<Key, { kind: string; source_label: string; reference_date: string | null; unit: string }>
}
export type Node = { id: string; lon: number; lat: number }
export type Dataset = {
  schema_version: string; metadata: { title: string; geographic_scope: string; synthetic: boolean; real_pilot_approved: boolean; reference_date: string; source_label: string; limitations: string[] }
  default_weights: Weights; clusters: Cluster[]
  network: { nodes: Node[]; edges: { from: string; to: string; walkable: boolean }[] }
  amenities: { id: string; name: string; category: string; node_id: string }[]; relocation_node_id: string
}
export function finite(value: unknown, name: string, low = 0, high = Infinity): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < low || value > high) throw new Error(`${name} must be finite and between ${low} and ${high}.`)
  return value
}
const rounded = (value: number, digits = 6) => Math.round((value + Number.EPSILON) * 10 ** digits) / 10 ** digits
export function normalizeWeights(weights: Weights): Weights {
  if (Object.keys(weights).length !== 5 || !KEYS.every(key => key in weights)) throw new Error('Supply exactly the five indicator weights.')
  const total = KEYS.reduce((n, key) => n + finite(weights[key], key, 0, 100), 0)
  if (total <= 0) throw new Error('At least one indicator must have a positive weight.')
  return Object.fromEntries(KEYS.map(key => [key, weights[key] / total])) as Weights
}
export function score(indicators: Cluster['indicators'], weights = DEFAULT_WEIGHTS) {
  if (Object.keys(indicators).length !== 5 || !KEYS.every(key => key in indicators)) throw new Error('Supply all five indicators; use null for unavailable values.')
  const normalized = normalizeWeights(weights)
  const missing = KEYS.filter(key => indicators[key] === null)
  const raw = Object.fromEntries(KEYS.map(key => [key, indicators[key] === null ? null : finite(indicators[key], key, 0, 100) * normalized[key]])) as Record<Key, number | null>
  const contributions = Object.fromEntries(KEYS.map(key => [key, raw[key] === null ? null : rounded(raw[key]!)])) as Record<Key, number | null>
  const lower = KEYS.reduce((n, key) => n + (raw[key] ?? 0), 0)
  const missingWeight = missing.reduce((n, key) => n + normalized[key], 0)
  const rankable = missingWeight <= 1e-12
  return { score: rankable ? rounded(lower) : null, lower: rounded(lower), upper: rounded(lower + missingWeight * 100), coverage_pct: rounded((1 - missingWeight) * 100), rankable, missing, weights: normalized, contributions }
}
export type Score = ReturnType<typeof score>
export type Ranked = Score & { id: string; name: string; rank: number | null; baseline_score: number | null; baseline_rank: number | null }
export function prioritize(clusters: Cluster[], weights = DEFAULT_WEIGHTS) {
  const normalized = normalizeWeights(weights)
  const baseline = new Map(clusters.map(cluster => [cluster.id, score(cluster.indicators, { water: 1, sanitation: 1, housing: 1, access: 1, risk: 1 }).score]))
  const scores = clusters.map(cluster => ({ id: cluster.id, name: cluster.name, ...score(cluster.indicators, normalized) }))
  const items: Ranked[] = scores.map(row => {
    const base = baseline.get(row.id) ?? null
    return { ...row, rank: row.rankable ? 1 + scores.filter(other => other.score !== null && other.score > row.score!).length : null,
      baseline_score: base, baseline_rank: base === null ? null : 1 + [...baseline.values()].filter(value => value !== null && value > base).length }
  }).sort((a, b) => a.score === null ? b.score === null ? a.id.localeCompare(b.id) : 1 : b.score === null ? -1 : b.score - a.score || a.id.localeCompare(b.id))
  const comparable = items.filter(row => row.score !== null && row.baseline_score !== null)
  const averageRanks = (field: 'score' | 'baseline_score') => comparable.map(row => 1 + comparable.filter(other => other[field]! > row[field]!).length + (comparable.filter(other => other[field] === row[field]).length - 1) / 2)
  const a = averageRanks('score'), b = averageRanks('baseline_score'), ma = a.reduce((n, x) => n + x, 0) / (a.length || 1), mb = b.reduce((n, x) => n + x, 0) / (b.length || 1)
  const denominator = Math.sqrt(a.reduce((n, x) => n + (x - ma) ** 2, 0) * b.reduce((n, x) => n + (x - mb) ** 2, 0))
  return { weights: normalized, items, rank_correlation: denominator ? rounded(a.reduce((n, x, i) => n + (x - ma) * (b[i] - mb), 0) / denominator) : null, comparable_clusters: comparable.length,
    baseline: 'Equal weights on the same supplied indicators; not an independent field baseline', synthetic: clusters.every(cluster => cluster.synthetic) }
}
export function distanceM(a: Node, b: Node) {
  const radians = (n: number) => n * Math.PI / 180, lat1 = radians(a.lat), lat2 = radians(b.lat)
  const hav = Math.sin((lat2 - lat1) / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(radians(b.lon - a.lon) / 2) ** 2
  return 6371000 * 2 * Math.asin(Math.min(1, Math.sqrt(hav)))
}
export function networkAccess(data: Dataset, start: string) {
  const nodes = new Map(data.network.nodes.map(node => [node.id, node]))
  const graph = new Map(data.network.nodes.map(node => [node.id, [] as { to: string; length: number }[]]))
  for (const edge of data.network.edges) {
    if (!edge.walkable) continue
    const a = nodes.get(edge.from), b = nodes.get(edge.to)
    if (!a || !b) throw new Error('Network edge references an unknown node.')
    const length = distanceM(a, b)
    graph.get(a.id)!.push({ to: b.id, length }); graph.get(b.id)!.push({ to: a.id, length })
  }
  const distances = new Map<string, number>(nodes.has(start) ? [[start, 0]] : [])
  const queue = nodes.has(start) ? [{ id: start, distance: 0 }] : []
  while (queue.length) {
    queue.sort((a, b) => a.distance - b.distance)
    const current = queue.shift()!
    if (current.distance > distances.get(current.id)!) continue
    for (const edge of graph.get(current.id)!) {
      const candidate = current.distance + edge.length
      if (candidate < (distances.get(edge.to) ?? Infinity)) { distances.set(edge.to, candidate); queue.push({ id: edge.to, distance: candidate }) }
    }
  }
  return data.amenities.map(amenity => ({ ...amenity, distance_m: distances.has(amenity.node_id) ? rounded(distances.get(amenity.node_id)!, 1) : null }))
}
export type OptionKind = 'upgrade' | 'redevelop' | 'relocate'
export type ScenarioOption = { kind: OptionKind; unit_cost_inr: number; shared_works_inr: number; months: number; temporary_months: number; disrupted_share: number; assumed_service_coverage_pct: number }
export type Assumptions = { households: number | null; contingency_pct: number; temporary_rent_per_month: number; annual_maintenance_per_household: number; include_relocation: boolean; relocation_reason: string; options: ScenarioOption[] }
export const OPTION_NAMES: Record<OptionKind, string> = { upgrade: 'Improve in place', redevelop: 'Redevelop in place', relocate: 'Relocation thought experiment' }
export function defaultAssumptions(cluster: Cluster): Assumptions {
  return { households: cluster.households, contingency_pct: 10, temporary_rent_per_month: 5000, annual_maintenance_per_household: 1200, include_relocation: false, relocation_reason: '', options: [
    { kind: 'upgrade', unit_cost_inr: 90000, shared_works_inr: 400000, months: 6, temporary_months: 1, disrupted_share: .15, assumed_service_coverage_pct: 80 },
    { kind: 'redevelop', unit_cost_inr: 1000000, shared_works_inr: 1000000, months: 24, temporary_months: 18, disrupted_share: 1, assumed_service_coverage_pct: 95 },
  ] }
}
export function compareScenarios(data: Dataset, clusterId: string, assumptions: Assumptions) {
  const cluster = data.clusters.find(cluster => cluster.id === clusterId)
  if (!cluster) throw new Error('Unknown cluster.')
  const households = finite(assumptions.households, 'Scenario households', 1, 100000)
  if (!Number.isInteger(households)) throw new Error('Scenario households must be a whole number, not an eligibility count.')
  const contingency = finite(assumptions.contingency_pct, 'Contingency', 0, 100)
  const rent = finite(assumptions.temporary_rent_per_month, 'Temporary rent', 0, 1000000)
  const maintenance = finite(assumptions.annual_maintenance_per_household, 'Maintenance', 0, 1000000)
  const kinds = assumptions.options.map(option => option.kind)
  if (new Set(kinds).size !== kinds.length || !kinds.includes('upgrade') || !kinds.includes('redevelop') || kinds.some(kind => !['upgrade', 'redevelop', 'relocate'].includes(kind))) throw new Error('Compare upgrading and redevelopment once each; relocation is optional.')
  if (kinds.includes('relocate') !== assumptions.include_relocation) throw new Error('Relocation must be explicitly enabled and supplied as an option.')
  if (assumptions.include_relocation && assumptions.relocation_reason.trim().length < 10) throw new Error('Explain the assumptions for the relocation thought experiment (at least 10 characters).')
  const before = networkAccess(data, cluster.node_id)
  const options = assumptions.options.map(option => {
    const unit = finite(option.unit_cost_inr, 'Unit cost', 0, 100000000), shared = finite(option.shared_works_inr, 'Shared works', 0, 100000000000)
    finite(option.months, 'Implementation months', 1, 120); finite(option.temporary_months, 'Temporary-support months', 0, option.months)
    finite(option.disrupted_share, 'Disrupted share', 0, 1); finite(option.assumed_service_coverage_pct, 'Assumed coverage', 0, 100)
    const disrupted = Math.ceil(households * option.disrupted_share), support = disrupted * option.temporary_months * rent, base = households * unit + shared
    const after = networkAccess(data, option.kind === 'relocate' ? data.relocation_node_id : cluster.node_id)
    return { ...option, households_assumed: households, construction_and_shared_inr: rounded(base, 2), temporary_support_inr: rounded(support, 2), total_cost_inr: rounded((base + support) * (1 + contingency / 100), 2), annual_maintenance_inr: rounded(households * maintenance, 2), disrupted_households: disrupted,
      access: after.map((amenity, i) => ({ ...amenity, baseline_distance_m: before[i].distance_m, change_m: amenity.distance_m !== null && before[i].distance_m !== null ? rounded(amenity.distance_m - before[i].distance_m!, 1) : null })) }
  })
  return { cluster_id: clusterId, options, assumptions: structuredClone(assumptions), synthetic: true, limits: 'Hypothetical costs and coverage assumptions, not quotations. Distances use a synthetic graph. No engineering, financial, tenure or relocation approval is established.' }
}
export type ScenarioResult = ReturnType<typeof compareScenarios>
export const SERVICES = {
  water: { label: 'Water supply', unit: 'hours/day', direction: 'at_least', ceiling: 24 },
  sanitation: { label: 'Sanitation', unit: 'functional toilets', direction: 'at_least', ceiling: 10000 },
  drainage: { label: 'Drainage', unit: 'blocked segments', direction: 'at_most', ceiling: 10000 },
  waste: { label: 'Waste collection', unit: 'collections/week', direction: 'at_least', ceiling: 21 },
} as const
export type Service = keyof typeof SERVICES
export type AuditEvent = { at: string; action: string; actor: string; notes: string }
export type ActionInput = { action: 'start' | 'complete' | 'verify' | 'reopen'; actor: string; notes: string; evidence_id?: string; measured_value?: number | null; observed_at?: string; functioning_confirmed?: boolean }
export type WorkInput = { cluster_id: string; title: string; service: Service; target: number; due_date: string; actor: string; scenario_snapshot?: Record<string, unknown> | null }
export type Work = WorkInput & { id: string; unit: string; direction: string; created_at: string; status: 'planned' | 'in_progress' | 'completed'; verification: 'unverified' | 'verified' | 'disputed'; completed_at: string | null; completed_by: string | null; verification_record: (ActionInput & { verified_at: string; scope?: string }) | null; synthetic: boolean; history: AuditEvent[] }
export type Evidence = { id: string; work_id: string; cluster_id: string; filename: string; content_type: string; actor: string; notes: string; uploaded_at: string; bytes: number; sha256: string; synthetic: boolean; content_base64?: string }
export type Issue = { id: string; work_id: string; cluster_id: string; text: string; status: 'open' | 'resolved'; created_at: string; resolved_at: string | null; resolution_notes: string | null; history: AuditEvent[]; synthetic: boolean }
export type State = { works: Work[]; evidence: Evidence[]; complaints: Issue[]; synthetic: boolean }
export const emptyState = (): State => ({ works: [], evidence: [], complaints: [], synthetic: true })
const id = (prefix: string) => `${prefix}-${globalThis.crypto.randomUUID().slice(0, 10).toUpperCase()}`
function text(value: string, label: string, min = 2) { if (value.trim().length < min) throw new Error(`${label} needs at least ${min} characters.`); return value.trim() }
function addHistory(record: { history: AuditEvent[] }, action: string, actor: string, notes: string, at: string) { record.history.push({ at, action, actor, notes }) }
export function planWork(state: State, input: WorkInput, at: string): State {
  text(input.title, 'Work title', 5); text(input.actor, 'Actor'); finite(input.target, 'Service target', 0, SERVICES[input.service].ceiling)
  if (SERVICES[input.service].direction === 'at_least' && input.target <= 0) throw new Error('An at-least service commitment needs a positive target.')
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.due_date) || !Number.isFinite(Date.parse(input.due_date))) throw new Error('Supply a valid due date.')
  const result: State = structuredClone(state), definition = SERVICES[input.service]
  result.works.unshift({ ...input, id: id('WORK'), unit: definition.unit, direction: definition.direction, created_at: at, status: 'planned', verification: 'unverified', completed_at: null, completed_by: null, verification_record: null, synthetic: true, history: [{ at, action: 'planned', actor: input.actor.trim(), notes: 'User-entered demonstration plan; no government approval implied.' }] })
  return result
}
export function actOnWork(state: State, workId: string, input: ActionInput, at: string): State {
  const result: State = structuredClone(state), work = result.works.find(work => work.id === workId)
  if (!work) throw new Error('Work not found.')
  const actor = text(input.actor, 'Actor'), notes = text(input.notes, 'Review note', 5)
  if (input.action === 'start') { if (work.status !== 'planned') throw new Error('Only planned work can be started.'); work.status = 'in_progress' }
  else if (input.action === 'complete') { if (work.status !== 'in_progress') throw new Error('Start the work before marking physical completion.'); Object.assign(work, { status: 'completed', verification: 'unverified', completed_at: at, completed_by: actor }) }
  else if (input.action === 'reopen') { if (work.status !== 'completed') throw new Error('Only completed work can be reopened.'); Object.assign(work, { status: 'in_progress', verification: 'unverified', verification_record: null }) }
  else {
    if (work.status !== 'completed') throw new Error('Physical work must be completed before service verification.')
    const evidence = result.evidence.find(item => item.id === input.evidence_id && item.work_id === workId)
    if (!evidence) throw new Error('Attach evidence belonging to this work.')
    if ([work.completed_by?.toLowerCase(), evidence.actor.toLowerCase()].includes(actor.toLowerCase())) throw new Error('Use a reviewer different from the completion actor and evidence submitter.')
    const issues = result.complaints.filter(issue => issue.work_id === workId)
    if (issues.some(issue => issue.status === 'open')) throw new Error('Respond to open complaints before verifying the service.')
    if (issues.some(issue => evidence.uploaded_at < issue.created_at)) throw new Error('Attach fresh inspection evidence after the latest complaint.')
    const observed = Date.parse(input.observed_at || ''), clock = Date.parse(at)
    if (!Number.isFinite(observed) || observed > clock + 300000 || observed < Date.parse(work.completed_at!) - 300000 || clock - observed > 7 * 86400000) throw new Error('Supply a fresh inspection time after completion, not in the future (five-minute clock tolerance).')
    const value = finite(input.measured_value, 'Measured value', 0, SERVICES[work.service].ceiling)
    if (!input.functioning_confirmed || !(work.direction === 'at_least' ? value >= work.target : value <= work.target)) throw new Error('Confirm functioning and supply a measurement meeting the target.')
    work.verification = 'verified'; work.verification_record = { ...input, verified_at: at, scope: 'Demonstration review; not authenticated field validation' }
  }
  addHistory(work, input.action, actor, notes, at)
  return result
}
export function reportIssue(state: State, workId: string, description: string, at: string): State {
  const result: State = structuredClone(state), work = result.works.find(work => work.id === workId)
  if (!work) throw new Error('Work not found.')
  const notes = text(description, 'Issue description', 5)
  result.complaints.unshift({ id: id('ISSUE'), work_id: workId, cluster_id: work.cluster_id, text: notes, status: 'open', created_at: at, resolved_at: null, resolution_notes: null, synthetic: true, history: [{ at, action: 'reported', actor: 'demo resident', notes }] })
  if (work.verification === 'verified') work.verification = 'disputed'
  addHistory(work, 'issue_reported', 'demo resident', notes, at)
  return result
}
export function resolveIssue(state: State, issueId: string, actor: string, notes: string, at: string): State {
  const result: State = structuredClone(state), issue = result.complaints.find(issue => issue.id === issueId)
  if (!issue || issue.status !== 'open') throw new Error('Select an open complaint.')
  text(actor, 'Actor'); text(notes, 'Response note', 5)
  Object.assign(issue, { status: 'resolved', resolved_at: at, resolution_notes: notes.trim() })
  addHistory(issue, 'response_recorded', actor.trim(), notes.trim(), at)
  return result
}
export function overdue(work: Work, today = new Date().toISOString().slice(0, 10)) { return work.status !== 'completed' && work.due_date < today }
export function verifiedCount(state: State) { return state.works.filter(work => work.status === 'completed' && work.verification === 'verified' && !state.complaints.some(issue => issue.work_id === work.id && issue.status === 'open')).length }
