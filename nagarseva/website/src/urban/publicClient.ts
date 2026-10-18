import type { FeatureCollection, Polygon, MultiPolygon } from 'geojson'
import type { Cluster, Dataset, Key } from './engine'
import { DEFAULT_WEIGHTS, KEYS } from './engine'

const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
export type SourceRow = { dataset_name: string; publisher: string; source_url: string; retrieved_at: string; observation_date: string; publication_date: string; record_count: string; access_status: string; validation_status: string; limitations: string }
export type PublicSettlement = { id: string; source_id: string; name: string; geometry: Polygon | MultiPolygon | null; administrative_area: string | null; source: string; source_date: string | null; source_date_basis: string; retrieved_at: string; record_type: string; limitations: string[] }
export type PublicProject = { id: string; scheme_name: string; administrative_area: string; cts_raw: string; village: string; source_url: string; source_date: string | null; project_status: string; settlement_id: string | null }
export type Metadata = { snapshot: { title: string; built_at: string; settlement_record_type: string; geographic_scope: string; settlement_geometry_count: number; mapped_objects_count: number; mapped_object_categories: Record<string, number>; limitations: string[] }; datasets: SourceRow[] }
export type Stats = { settlements_loaded: number; settlements_with_geometry: number; sufficient_indicator_coverage: number; documented_deficits: number; requires_assessment: number; projects: number; awaiting_verification: number; overdue_interventions: number }
export type Health = { status: string; snapshot_loaded: boolean; evidence_storage: boolean }
export type PriorityRow = { id: string; indicators: Record<Key, number | null>; indicator_sources: Partial<Record<Key, { source: string; observation_date: string; verification_status: string }>> }
export type Intervention = { id: string; settlement_id: string; intervention_type: string; description: string; planned_start: string; planned_end: string; estimated_cost: number | null; status: string; target_value: number | null; measurement_unit: string | null; target_direction: string; overdue: boolean; completed_at: string | null; history: { at: string; action: string; actor: string; notes: string }[] }
export type Evidence = { id: string; intervention_id: string; filename?: string; evidence_reference?: string; actor: string; recorded_at: string; notes: string; storage: string }
export type Complaint = { id: string; settlement_id: string; intervention_id: string | null; service_type: string; description: string; reported_at: string; status: string; resolution_details: string | null }
export type Verification = { id: string; intervention_id: string; outcome: string; verifier_reference: string; observed_at: string; measured_value: number; measurement_unit: string | null; notes: string }
export type Spatial = FeatureCollection & { total: number; offset: number; limit: number }

export async function dataApi<T>(path: string, body?: unknown, key = '', method?: string): Promise<T> {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 20000)
  try {
    const response = await fetch(`${BASE}/urban/data${path}`, { method: method || (body === undefined ? 'GET' : 'POST'), headers: { 'Content-Type': 'application/json', 'X-Officer-Key': key }, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : Array.isArray(result.detail) ? result.detail.map((r: { msg: string }) => r.msg).join('; ') : `Request failed (${response.status})`)
    return result as T
  } finally { clearTimeout(timer) }
}

export async function exportPublicCsv(kind: string, key: string) {
  const response = await fetch(`${BASE}/urban/data/reports/${kind}.csv`, { headers: { 'X-Officer-Key': key } })
  if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Export failed') }
  const url = URL.createObjectURL(await response.blob()), link = document.createElement('a')
  link.href = url; link.download = `urbansaarthi-${kind}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function planningDataset(settlements: PublicSettlement[], metadata: Metadata, rows: PriorityRow[]): Dataset {
  const scores = new Map(rows.map(r => [r.id, r]))
  const clusters: Cluster[] = settlements.map(row => {
    const current = scores.get(row.id)
    return { id: row.id, name: row.name, node_id: '', households: null, households_source: 'No verified settlement household count acquired; enter a hypothetical scenario count.', synthetic: false, geometry: row.geometry,
      indicators: current?.indicators || Object.fromEntries(KEYS.map(key => [key, null])) as Record<Key, number | null>,
      provenance: Object.fromEntries(KEYS.map(key => { const source = current?.indicator_sources[key]; return [key, { kind: source ? 'Reviewed user observation' : 'Missing observation', source_label: source?.source || 'No acquired current settlement service index', reference_date: source?.observation_date || null, unit: 'deficit_0_100' }] })) as Cluster['provenance'] }
  })
  return { schema_version: '2', metadata: { title: metadata.snapshot.title, geographic_scope: metadata.snapshot.geographic_scope, synthetic: false, real_pilot_approved: false, reference_date: metadata.snapshot.built_at, source_label: 'Acquired source records; per-indicator provenance retained', limitations: metadata.snapshot.limitations }, default_weights: DEFAULT_WEIGHTS,
    clusters, network: { nodes: [], edges: [] }, amenities: [], relocation_node_id: '' }
}
