import type { Feature, FeatureCollection, Polygon } from 'geojson'

/** Reference layers never enter settlements, indicators, scores or project joins. */
export type ReferenceLayer = { id: string; year: number; geometryUrl: string; metadataUrl: string }
export const HISTORICAL_2015: ReferenceLayer = {
  id: 'mumbai-slum-reference-2015', year: 2015,
  geometryUrl: '/data/mumbai_slum_clusters_2015.geojson',
  metadataUrl: '/data/mumbai_slum_clusters_2015.metadata.json',
}
export type BoundaryMetadata = {
  schema_version: number; id: string; reference_year: number; crs: string; analysis_allowed: false;
  sha256: string; bytes: number; source_url: string; source_catalog_url: string;
  retrieved_at: string | null; publication_date: string | null; staged_at: string;
  source_attribution_key: string; licence_claim: string | null;
  source_feature_count: number; valid_feature_count: number; bounds: [number, number, number, number];
  excluded_features: { source_feature_number: number; reason: string }[];
}
export type ReferenceProperties = { polyno: string | number | null }
export type ReferenceBoundaries = {
  geometry: FeatureCollection<Polygon, ReferenceProperties>;
  metadata: BoundaryMetadata; skippedCount: number;
}
const MAX_BYTES = 10 * 1024 * 1024
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)

export function validateBoundaryMetadata(value: unknown, layer: ReferenceLayer = HISTORICAL_2015): BoundaryMetadata {
  if (!object(value) || value.schema_version !== 1 || value.id !== layer.id || value.reference_year !== layer.year || value.crs !== 'EPSG:4326' || value.analysis_allowed !== false || !/^[a-f0-9]{64}$/.test(String(value.sha256))) throw new Error('Reference boundary metadata is invalid.')
  const counts = [value.source_feature_count, value.valid_feature_count, value.bytes]
  if (!counts.every(v => finite(v) && Number.isInteger(v) && v >= 0) || Number(value.source_feature_count) > 10000 || Number(value.valid_feature_count) > Number(value.source_feature_count) || Number(value.bytes) > MAX_BYTES) throw new Error('Reference boundary metadata is invalid.')
  const bounds = value.bounds
  if (!Array.isArray(bounds) || bounds.length !== 4 || !bounds.every(finite) || bounds[0] < -180 || bounds[2] > 180 || bounds[1] < -90 || bounds[3] > 90 || bounds[0] >= bounds[2] || bounds[1] >= bounds[3]) throw new Error('Reference boundary metadata is invalid.')
  if (!Array.isArray(value.excluded_features) || value.excluded_features.some(row => !object(row) || !Number.isInteger(row.source_feature_number) || Number(row.source_feature_number) < 1 || Number(row.source_feature_number) > Number(value.source_feature_count) || typeof row.reason !== 'string')) throw new Error('Reference boundary metadata is invalid.')
  const excluded = value.excluded_features.map(row => row.source_feature_number)
  if (new Set(excluded).size !== excluded.length || Number(value.valid_feature_count) + excluded.length !== value.source_feature_count) throw new Error('Reference boundary metadata is invalid.')
  for (const key of ['source_url', 'source_catalog_url'] as const) {
    if (typeof value[key] !== 'string') throw new Error('Reference boundary metadata is invalid.')
    const url = new URL(value[key]); if (url.protocol !== 'https:' || url.username || url.password) throw new Error('Reference boundary metadata is invalid.')
  }
  if (typeof value.source_attribution_key !== 'string' || typeof value.staged_at !== 'string' || ![value.retrieved_at, value.publication_date, value.licence_claim].every(v => v === null || typeof v === 'string')) throw new Error('Reference boundary metadata is invalid.')
  return value as BoundaryMetadata
}

function validPolygon(value: unknown): value is Polygon {
  if (!object(value) || value.type !== 'Polygon' || !Array.isArray(value.coordinates) || !value.coordinates.length) return false
  return value.coordinates.every(ring => {
    if (!Array.isArray(ring) || ring.length < 4) return false
    if (!ring.every(p => Array.isArray(p) && (p.length === 2 || p.length === 3) && p.every(finite) && Math.abs(p[0]) <= 180 && Math.abs(p[1]) <= 90)) return false
    const first = ring[0], last = ring[ring.length - 1]
    return first.length === last.length && first.every((v: number, i: number) => v === last[i]) && new Set(ring.map(p => `${p[0]},${p[1]}`)).size >= 3
  })
}

/** Topology exclusions apply only to the SHA-256-verified, unmodified source file. */
export function parseReferenceBoundaries(value: unknown, metadata: BoundaryMetadata): ReferenceBoundaries {
  if (!object(value) || value.type !== 'FeatureCollection' || !Array.isArray(value.features) || value.crs) throw new Error('Reference boundaries must be a WGS84 GeoJSON FeatureCollection.')
  if (value.features.length !== metadata.source_feature_count || value.features.length > 10000) throw new Error('Reference boundary count does not match its validation metadata.')
  const excluded = new Set(metadata.excluded_features.map(row => row.source_feature_number))
  const features: Feature<Polygon, ReferenceProperties>[] = []
  value.features.forEach((feature, index) => {
    if (excluded.has(index + 1) || !object(feature) || feature.type !== 'Feature' || !object(feature.properties) || !validPolygon(feature.geometry)) return
    const polyno = feature.properties.polyno
    if (polyno !== null && polyno !== undefined && !(finite(polyno) || typeof polyno === 'string' && polyno.trim().length > 0 && polyno.length <= 100)) return
    features.push({ type: 'Feature', properties: { polyno: polyno ?? null }, geometry: feature.geometry })
  })
  return { geometry: { type: 'FeatureCollection', features }, metadata, skippedCount: value.features.length - features.length }
}

async function limitedBody(response: Response, maximum: number) {
  if (!response.ok) throw new Error('Reference boundary request failed ({status}).'.replace('{status}', String(response.status)))
  if (Number(response.headers.get('content-length')) > maximum) throw new Error('Reference boundary file exceeds the size limit.')
  const reader = response.body?.getReader()
  if (!reader) throw new Error('Reference boundary response was empty.')
  const chunks: Uint8Array[] = []; let length = 0
  try {
    while (true) {
      const next = await reader.read(); if (next.done) break
      length += next.value.byteLength
      if (length > maximum) throw new Error('Reference boundary file exceeds the size limit.')
      chunks.push(next.value)
    }
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock() }
  if (!length) throw new Error('Reference boundary response was empty.')
  const bytes = new Uint8Array(length); let offset = 0
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength }
  return bytes
}

export async function loadReferenceBoundaries(layer: ReferenceLayer = HISTORICAL_2015, fetcher: typeof fetch = fetch, timeoutMs = 20000): Promise<ReferenceBoundaries> {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const [metadataBytes, geometryBytes] = await Promise.all([
      fetcher(layer.metadataUrl, { signal: controller.signal }).then(response => limitedBody(response, 256 * 1024)),
      fetcher(layer.geometryUrl, { signal: controller.signal }).then(response => limitedBody(response, MAX_BYTES)),
    ])
    const decode = (bytes: Uint8Array) => { try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)) } catch { throw new Error('Reference boundary file is not valid JSON.') } }
    const metadata = validateBoundaryMetadata(decode(metadataBytes), layer)
    if (!globalThis.crypto?.subtle) throw new Error('Boundary integrity checks require localhost or HTTPS.')
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', geometryBytes))].map(byte => byte.toString(16).padStart(2, '0')).join('')
    if (hash !== metadata.sha256 || geometryBytes.byteLength !== metadata.bytes) throw new Error('Reference boundary checksum does not match its validation metadata.')
    return parseReferenceBoundaries(decode(geometryBytes), metadata)
  } finally { clearTimeout(timer); controller.abort() }
}
// Reuse the immutable local layer across navigation; failed loads remain retryable.
let cached: Promise<ReferenceBoundaries> | undefined
export function referenceBoundaries() {
  cached ??= loadReferenceBoundaries().catch(error => { cached = undefined; throw error })
  return cached
}
