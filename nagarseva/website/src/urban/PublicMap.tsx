import { useEffect, useMemo, useState } from 'react'
import { GeoJSON, ImageOverlay, MapContainer, Pane, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import 'leaflet/dist/leaflet.css'
import { dataApi, dataAssetUrl } from './publicClient'
import type { PublicSettlement, Spatial } from './publicClient'

const COLORS: Record<string, string> = { settlement: '#d17143', project: '#8663a0', road: '#809891', amenity: '#246f88', transport: '#ba8040', water_infrastructure: '#387da3', building: '#b1a5a0', residential_context: '#9da58c' }
const LABELS: Record<string, string> = { settlement: 'Settlements', project: 'Projects', road: 'Roads', amenity: 'Amenities', transport: 'Transport', water_infrastructure: 'Water infrastructure', building: 'Buildings', residential_context: 'Residential context' }
type Raster = { available: boolean; bounds?: [number,number,number,number]; source_url?: string }
function FitMap({ geometry, fallback }: { geometry: Geometry[]; fallback: FeatureCollection | null }) {
  const map = useMap()
  useEffect(() => {
    const source = geometry.length ? { type: 'FeatureCollection' as const, features: geometry.map(value => ({ type: 'Feature' as const, geometry: value, properties: {} })) } : fallback
    if (!source?.features.length) return
    const bounds = L.geoJSON(source).getBounds()
    if (bounds.isValid()) map.fitBounds(bounds, { animate: false, padding: [28, 28], maxZoom: 17 })
  }, [map, geometry, fallback])
  useEffect(() => { const observer = new ResizeObserver(() => map.invalidateSize()); observer.observe(map.getContainer()); return () => observer.disconnect() }, [map])
  return null
}
function describe(feature: Feature, layer: L.Layer) {
  const element = document.createElement('div'), props = feature.properties || {}
  const title = document.createElement('strong'); title.textContent = props.name || props.scheme_name || props.source_id || 'Mapped object'; element.appendChild(title)
  const detail = document.createElement('p'); detail.textContent = LABELS[props.category] || props.project_status || 'Context feature'; element.appendChild(detail)
  if (props.osm_edit_timestamp) { const source = document.createElement('small'); source.textContent = `OSM edit: ${props.osm_edit_timestamp.slice(0, 10)}`; element.appendChild(source) }
  layer.bindPopup(element)
}
export default function PublicMap({ settlements, selected, onSelect }: { settlements: PublicSettlement[]; selected?: string; onSelect: (id: string) => void }) {
  const [layers, setLayers] = useState(['road', 'amenity', 'transport', 'water_infrastructure', 'settlement', 'project']), [basemap, setBasemap] = useState(true)
  const [spatial, setSpatial] = useState<Spatial | null>(null), [projects, setProjects] = useState<FeatureCollection | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(true), [term, setTerm] = useState('')
  const [raster, setRaster] = useState<Raster | null>(null), [showRaster, setShowRaster] = useState(false)
  const vectorLayers = layers.filter(c => !['settlement', 'project'].includes(c)).sort().join(',')
  useEffect(() => {
    let active = true; setLoading(true); setError('')
    const load = vectorLayers ? dataApi<Spatial>(`/spatial?category=${encodeURIComponent(vectorLayers)}&limit=10000`) : Promise.resolve({ type: 'FeatureCollection', features: [], total: 0, offset: 0, limit: 10000 } as Spatial)
    load.then(result => { if (active) setSpatial(result) }).catch(problem => { if (active) { setSpatial(null); setError(problem.message) } }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [vectorLayers])
  useEffect(() => { let active = true; dataApi<FeatureCollection>('/spatial?category=project&limit=10000').then(result => { if (active) setProjects(result) }).catch(problem => { if (active) setError(problem.message) }); return () => { active = false } }, [])
  useEffect(() => { let active = true; dataApi<Raster>('/map-overlay').then(result => { if (active) setRaster(result) }).catch(problem => { if (active) setError(problem.message) }); return () => { active = false } }, [])
  const filtered = useMemo(() => ({ type: 'FeatureCollection' as const, features: spatial?.features.filter(f => !term || `${f.properties?.name || ''} ${JSON.stringify(f.properties?.tags || {})}`.toLowerCase().includes(term.toLowerCase())) || [] }), [spatial, term])
  const selectedRow = settlements.find(row => row.id === selected)
  const focus = useMemo(() => selectedRow?.geometry ? [selectedRow.geometry] : settlements.flatMap(row => row.geometry ? [row.geometry] : []), [selectedRow?.geometry, settlements])
  function toggle(name: string) { setLayers(old => old.includes(name) ? old.filter(value => value !== name) : [...old, name]) }
  return <section className="us-panel us-map-panel workspace-map">
    <div className="workspace-map-toolbar"><input aria-label="Search mapped objects" placeholder="Search mapped amenities" value={term} onChange={event => setTerm(event.target.value)} /><details><summary>Layers</summary><div className="workspace-layer-options">{Object.keys(COLORS).map(name => <label key={name}><input aria-label={`${name} layer`} type="checkbox" checked={layers.includes(name)} onChange={() => toggle(name)} /><i style={{ background: COLORS[name] }} />{LABELS[name]}</label>)}<label><input type="checkbox" checked={basemap} onChange={event => setBasemap(event.target.checked)} />Street basemap</label>{raster?.available && <label><input aria-label="Historical SRA raster layer" type="checkbox" checked={showRaster} onChange={event => setShowRaster(event.target.checked)} />Historical SRA map (2024)</label>}</div></details></div>
    {error && <p className="us-alert" role="alert">Map data could not load: {error}</p>}
    <div className="us-map"><MapContainer center={[19.08,72.88]} zoom={12} scrollWheelZoom preferCanvas={false} aria-label="Settlement map"><FitMap geometry={focus} fallback={spatial} />
      {basemap && <TileLayer url={import.meta.env.VITE_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'} attribution={import.meta.env.VITE_TILE_ATTRIBUTION || '&copy; OpenStreetMap contributors'} />}
      {showRaster && raster?.available && raster.bounds && <ImageOverlay url={dataAssetUrl('/map-overlay/image')} bounds={[[raster.bounds[1],raster.bounds[0]],[raster.bounds[3],raster.bounds[2]]]} opacity={.65} attribution="SRA Mumbai · 2024 historical imagery" />}
      <Pane name="workspace-context" style={{ zIndex: 420 }}>{spatial && <GeoJSON pane="workspace-context" key={`${vectorLayers}-${term}-${spatial.features.length}`} data={filtered} style={feature => ({ color: COLORS[feature?.properties?.category] || '#888', weight: feature?.properties?.category === 'road' ? 1.3 : 1, fillOpacity: .15 })} pointToLayer={(feature, latlng) => L.circleMarker(latlng, { radius: 5, fillColor: COLORS[feature.properties.category] || '#246f88', color: '#fff', weight: 1, fillOpacity: .95 })} onEachFeature={describe} />}</Pane>
      {layers.includes('settlement') && settlements.filter(row => row.geometry).map(row => <GeoJSON key={`${row.id}-${selected === row.id}`} data={row.geometry!} style={{ color: selected === row.id ? '#193f35' : COLORS.settlement, weight: selected === row.id ? 3 : 2, fillColor: COLORS.settlement, fillOpacity: selected === row.id ? .38 : .15 }} eventHandlers={{ click: () => onSelect(row.id) }} onEachFeature={(_feature, layer) => { layer.bindTooltip(row.name); layer.on('add', () => { const element = (layer as L.Path).getElement?.(); if (element) { element.setAttribute('aria-label', `Settlement boundary ${row.name}`); element.setAttribute('role', 'button'); element.setAttribute('tabindex', '0'); element.addEventListener('keydown', event => { if ((event as KeyboardEvent).key === 'Enter') onSelect(row.id) }) } }) }} />)}
      {layers.includes('project') && projects && <GeoJSON data={projects} style={{ color: COLORS.project }} onEachFeature={describe} />}
    </MapContainer></div>
    <div className="workspace-map-legend"><span><i style={{ background: COLORS.settlement }} />Settlement</span><span><i style={{ background: '#193f35' }} />Selected</span><span><i style={{ background: COLORS.amenity }} />Amenity</span><span role="status">{loading ? 'Loading context…' : `${filtered.features.length.toLocaleString()} context objects`}</span></div>
    {selectedRow && !selectedRow.geometry && <p className="workspace-map-note">No boundary supplied for {selectedRow.name}. Add its GeoJSON geometry from Data.</p>}
    {showRaster && <p className="workspace-map-note">Historical map imagery is for visual reference. {raster?.source_url && <a href={raster.source_url} target="_blank" rel="noreferrer">Source</a>}</p>}
    {!loading && term && !filtered.features.length && <p className="workspace-map-note">No mapped objects match this search.</p>}
  </section>
}
