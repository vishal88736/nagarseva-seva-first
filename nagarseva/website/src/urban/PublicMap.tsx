import { useEffect, useMemo, useState } from 'react'
import { GeoJSON, ImageOverlay, MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { Feature, FeatureCollection } from 'geojson'
import 'leaflet/dist/leaflet.css'
import { dataApi, dataAssetUrl } from './publicClient'
import type { PublicSettlement, Spatial } from './publicClient'

const COLORS: Record<string, string> = { road: '#809891', building: '#b1a5a0', amenity: '#246f88', transport: '#ba8040', water_infrastructure: '#387da3', residential_context: '#9da58c', settlement: '#cb6c48', project: '#8663a0' }
type Raster = { available: boolean; bounds?: [number,number,number,number]; source_url?: string; source_date?: string; reason?: string; limitations?: string[] }
function SizeMap() { const map = useMap(); useEffect(() => { map.invalidateSize(); map.fitBounds([[19.04,72.90],[19.08,72.94]], { animate: false }) }, [map]); return null }
function describe(feature: Feature, layer: L.Layer) {
  const element = document.createElement('div'), props = feature.properties || {}
  const title = document.createElement('strong'); title.textContent = props.name || props.source_id || 'Mapped object'; element.appendChild(title)
  const detail = document.createElement('p'); detail.textContent = `${props.category || 'Source geometry'} · ${props.source_id || ''}\n${JSON.stringify(props.tags || {})}\nOSM edit: ${props.osm_edit_timestamp || 'unknown'}; field observation date unknown. Mapping does not prove operation.`; element.appendChild(detail)
  if (typeof props.source_url === 'string' && /^https:\/\/(www\.)?openstreetmap.org\//.test(props.source_url)) { const link = document.createElement('a'); link.href = props.source_url; link.textContent = 'Open source object'; link.target = '_blank'; link.rel = 'noreferrer'; element.appendChild(link) }
  layer.bindPopup(element)
}
export default function PublicMap({ settlements, onSelect }: { settlements: PublicSettlement[]; onSelect: (id: string) => void }) {
  const [layers, setLayers] = useState(['road', 'amenity', 'transport', 'water_infrastructure', 'settlement', 'project']), [basemap, setBasemap] = useState(false)
  const [spatial, setSpatial] = useState<Spatial | null>(null), [projects, setProjects] = useState<FeatureCollection | null>(null), [error, setError] = useState('')
  const [loading, setLoading] = useState(true), [term, setTerm] = useState('')
  const [raster, setRaster] = useState<Raster | null>(null), [showRaster, setShowRaster] = useState(false), [opacity, setOpacity] = useState(.65)
  const vectorLayers = layers.filter(c => !['settlement', 'project'].includes(c)).sort().join(',')
  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    const load = vectorLayers ? dataApi<Spatial>(`/spatial?category=${encodeURIComponent(vectorLayers)}&limit=10000`) : Promise.resolve({ type: 'FeatureCollection', features: [], total: 0, offset: 0, limit: 10000 } as Spatial)
    load.then(result => { if (active) setSpatial(result) }).catch(e => { if (active) { setSpatial(null); setError(e.message) } }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [vectorLayers])
  useEffect(() => { let active = true; dataApi<FeatureCollection>('/spatial?category=project').then(result => { if (active) setProjects(result) }).catch(e => { if (active) setError(e.message) }); return () => { active = false } }, [])
  useEffect(() => { let active = true; dataApi<Raster>('/map-overlay').then(result => { if (active) setRaster(result) }).catch(e => { if (active) setError(e.message) }); return () => { active = false } }, [])
  const filtered = useMemo(() => ({ type: 'FeatureCollection' as const, features: spatial?.features.filter(f => !term || JSON.stringify(f.properties).toLocaleLowerCase().includes(term.toLocaleLowerCase())) || [] }), [spatial, term])
  function toggle(name: string) { setLayers(old => old.includes(name) ? old.filter(k => k !== name) : [...old, name]) }
  const renderer = useMemo(() => L.canvas({ padding: .5 }), [])
  return <section className="us-panel us-map-panel">
    <div className="us-layer-row public-layer-row">{Object.keys(COLORS).map(name => <label key={name}><input aria-label={`${name} layer`} type="checkbox" checked={layers.includes(name)} onChange={() => toggle(name)} /><i style={{ background: COLORS[name] }} />{name.replaceAll('_', ' ')}</label>)}<label><input type="checkbox" checked={basemap} onChange={e => setBasemap(e.target.checked)} />Online OSM basemap</label></div>
    <div className="us-layer-row"><label><input aria-label="Historical SRA raster layer" type="checkbox" disabled={!raster?.available} checked={showRaster} onChange={event => setShowRaster(event.target.checked)} />Historical SRA map · 2024{!raster?.available && ' · unavailable'}</label>{showRaster && <label>Image opacity<input aria-label="Historical map opacity" type="range" min="0.2" max="1" step="0.05" value={opacity} onChange={event => setOpacity(Number(event.target.value))} /></label>}</div>
    {showRaster && <p className="us-note">Historical georeferenced source imagery for visual context. This layer supplies no analytical settlement polygons or current boundary confirmation. {raster?.source_url && <a href={raster.source_url} target="_blank" rel="noreferrer">Original SRA map</a>}</p>}
    <div className="us-toolbar"><label className="us-field">Search mapped names or tags<input aria-label="Search mapped objects" value={term} onChange={e => setTerm(e.target.value)} placeholder="school, hospital, toilets, name…" /></label><p role="status">{loading ? 'Loading mapped features…' : `${filtered.features.length.toLocaleString()} mapped objects shown`} {spatial && spatial.total > spatial.features.length ? '· Response truncated: narrow the map categories.' : ''}</p></div>
    {error && <div className="us-alert" role="alert">Map data could not load: {error}</div>}
    <div className="us-map"><MapContainer center={[19.06,72.92]} zoom={14} scrollWheelZoom={false} preferCanvas renderer={renderer} aria-label="Acquired OpenStreetMap context map"><SizeMap />
      {basemap && <TileLayer url={import.meta.env.VITE_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'} attribution={import.meta.env.VITE_TILE_ATTRIBUTION || '&copy; OpenStreetMap contributors'} />}
      {showRaster && raster?.available && raster.bounds && <ImageOverlay url={dataAssetUrl('/map-overlay/image')} bounds={[[raster.bounds[1],raster.bounds[0]],[raster.bounds[3],raster.bounds[2]]]} opacity={opacity} attribution="SRA Mumbai / DSLR GIS Cell · 2024 source map" />}
      {spatial && <GeoJSON key={`${vectorLayers}-${term}-${spatial.features.length}`} data={filtered} style={feature => ({ color: COLORS[feature?.properties?.category] || '#888', weight: feature?.properties?.category === 'road' ? 1.3 : 1, fillOpacity: .2 })} pointToLayer={(_feature, latlng) => L.circleMarker(latlng, { radius: 4, fillColor: COLORS[_feature.properties.category] || '#246f88', color: '#fff', weight: 1, fillOpacity: .95 })} onEachFeature={describe} />}
      {layers.includes('settlement') && settlements.filter(s => s.geometry).map(s => <GeoJSON key={s.id} data={s.geometry!} style={{ color: COLORS.settlement, weight: 2 }} eventHandlers={{ click: () => onSelect(s.id) }} />)}
      {layers.includes('project') && projects && <GeoJSON data={projects} style={{ color: COLORS.project }} onEachFeature={describe} />}
    </MapContainer><div className="us-map-caption"><span>© OpenStreetMap contributors · ODbL 1.0</span><b>Mapped context; service operation unknown</b></div></div>
    {!loading && !filtered.features.length && <p className="us-note">No acquired mapped objects match these layers and search. This is not evidence that facilities do not exist.</p>}
    <p className="us-note">{settlements.filter(s => s.geometry).length} analytical settlement polygons and {projects?.features.length || 0} project geometries acquired. Published register rows have no feature coordinates; historical map imagery does not create vector boundaries. Residential polygons are context, not official slum boundaries.</p>
  </section>
}
