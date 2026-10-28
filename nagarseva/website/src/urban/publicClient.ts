import type { FeatureCollection, Polygon, MultiPolygon } from 'geojson'
import type { Cluster, Dataset, Key } from './engine'
import { DEFAULT_WEIGHTS, KEYS } from './engine'

const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
export const dataAssetUrl = (path: string) => `${BASE}/urban/data${path}`
export type SourceRow = { dataset_name: string; publisher: string; source_url: string; retrieved_at: string; observation_date: string; publication_date: string; record_count: string; access_status: string; validation_status: string; limitations: string }
export type PublicSettlement = { id: string; source_id: string; name: string; geometry: Polygon | MultiPolygon | null; administrative_area: string | null; source: string; source_date: string | null; source_date_basis: string; retrieved_at: string; record_type: string; limitations: string[]; households?: number | null; households_source?: string; village?: string | null; taluka?: string | null; shape_area_sq_m?: number | null; source_name?: string | null; source_id_unique?: boolean; name_overflow_in_source?: boolean }
export type PublicProject = { id: string; scheme_name: string; administrative_area: string; cts_raw: string; village: string; source_url: string; source_date: string | null; project_status: string; settlement_id: string | null }
export type Metadata = { snapshot: { title: string; source_type?: string; source_label?: string; snapshot_sha256?: string; built_at: string; settlement_record_type: string; geographic_scope: string; settlement_geometry_count: number; settlement_count?: number; projects_count?: number; mapped_objects_count: number; mapped_object_categories: Record<string, number>; limitations: string[]; historical_observation_count?: number; geographic_unit_count?: number; register_identifier_links?: number; settlement_reference?: string; project_acquisition?: { complete?: boolean; pages_retrieved?: number; pagination_error?: string | null; scope?: string } }; datasets: SourceRow[] }
export type Stats = { settlements_loaded: number; settlements_with_geometry: number; sufficient_indicator_coverage: number; documented_deficits: number; requires_assessment: number; projects: number; awaiting_verification: number; overdue_interventions: number; verified_interventions?: number }
export type Health = { status: string; snapshot_loaded: boolean; evidence_storage: boolean }
export type PriorityRow = { id: string; indicators: Record<Key, number | null>; indicator_sources: Partial<Record<Key, { source: string; observation_date: string; verification_status: string }>> }
export type Intervention = { id: string; settlement_id: string; intervention_type: string; description: string; planned_start: string; planned_end: string; estimated_cost: number | null; status: string; target_value: number | null; measurement_unit: string | null; target_direction: string; overdue: boolean; completed_at: string | null; history: { at: string; action: string; actor: string; notes: string }[] }
export type Evidence = { id: string; intervention_id: string; filename?: string; evidence_reference?: string; actor: string; recorded_at: string; notes: string; storage: string }
export type Complaint = { id: string; settlement_id: string; intervention_id: string | null; service_type: string; description: string; reported_at: string; status: string; resolution_details: string | null }
export type Verification = { id: string; intervention_id: string; outcome: string; verifier_reference: string; observed_at: string; measured_value: number; measurement_unit: string | null; notes: string }
export type Spatial = FeatureCollection & { total: number; offset: number; limit: number }

export async function dataApi<T>(path: string, body?: unknown, key = '', method?: string, extraHeaders: Record<string,string> = {}): Promise<T> {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 20000)
  try {
    const response = await fetch(`${BASE}/urban/data${path}`, { method: method || (body === undefined ? 'GET' : 'POST'), headers: { 'Content-Type': 'application/json', 'X-Officer-Key': key, ...extraHeaders }, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : Array.isArray(result.detail) ? result.detail.map((r: { msg: string }) => r.msg).join('; ') : `Request failed (${response.status})`)
    return result as T
  } finally { clearTimeout(timer) }
}

export async function exportDataCsv(path:string,filename:string,key='') {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000)
  try {
    const response=await fetch(dataAssetUrl(path),{headers:{'X-Officer-Key':key},signal:controller.signal})
    if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(error.detail||'Export failed')}
    const url=URL.createObjectURL(await response.blob()),link=document.createElement('a')
    link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
  } finally{clearTimeout(timer)}
}
export function exportPublicCsv(kind:string,key:string){return exportDataCsv(`/reports/${kind}.csv`,`urbansaarthi-${kind}.csv`,key)}

export function planningDataset(settlements: PublicSettlement[], metadata: Metadata, rows: PriorityRow[]): Dataset {
  const scores = new Map(rows.map(r => [r.id, r]))
  const clusters: Cluster[] = settlements.map(row => {
    const current = scores.get(row.id)
    return { id: row.id, name: row.name, node_id: '', households: row.households ?? null, households_source: row.households !== null && row.households !== undefined ? `${row.households_source || row.source} · ${row.source_date || 'date not supplied'}` : 'Enter a household count for this scenario.', synthetic: false, geometry: row.geometry,
      indicators: current?.indicators || Object.fromEntries(KEYS.map(key => [key, null])) as Record<Key, number | null>,
      provenance: Object.fromEntries(KEYS.map(key => { const source = current?.indicator_sources[key]; return [key, { kind: source ? 'Reviewed user observation' : 'Missing observation', source_label: source?.source || 'No acquired current settlement service index', reference_date: source?.observation_date || null, unit: 'deficit_0_100' }] })) as Cluster['provenance'] }
  })
  return { schema_version: '2', metadata: { title: metadata.snapshot.title, geographic_scope: metadata.snapshot.geographic_scope, synthetic: false, real_pilot_approved: false, reference_date: metadata.snapshot.built_at, source_label: metadata.snapshot.source_label || 'Source records; per-indicator provenance retained', limitations: metadata.snapshot.limitations }, default_weights: DEFAULT_WEIGHTS,
    clusters, network: { nodes: [], edges: [] }, amenities: [], relocation_node_id: '' }
}
