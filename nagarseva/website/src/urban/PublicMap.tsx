import { t, errorText, formatDate, formatNumber, statusText, getLanguage } from '../i18n/locale'
import { useEffect, useMemo, useRef, useState } from 'react'
import { GeoJSON, ImageOverlay, MapContainer, Pane, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import HistoricalReferenceLayer, { HISTORICAL_NOTICE, REFERENCE_COLOR } from './HistoricalReferenceLayer'
import { useReferenceBoundaries } from './useReferenceBoundaries'
import type { ReferenceBoundaries } from './historicalBoundaries'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import 'leaflet/dist/leaflet.css'
import LocalizedMapControls from './LocalizedMapControls'
import { dataApi, dataAssetUrl } from './publicClient'
import type { PublicSettlement, Spatial } from './publicClient'

const COLORS: Record<string, string> = { settlement: '#d17143', project: '#8663a0', road: '#809891', amenity: '#246f88', transport: '#ba8040', water_infrastructure: '#387da3', building: '#b1a5a0', residential_context: '#9da58c' }
const LABELS: Record<string, string> = { settlement: 'Settlements', project: 'Projects', road: 'Roads', amenity: 'Amenities', transport: 'Transport', water_infrastructure: 'Water infrastructure', building: 'Buildings', residential_context: 'Residential context' }
type Raster = { available: boolean; bounds?: [number,number,number,number]; source_url?: string }
function FitMap({ geometry, fallback, reference, selected, fitRequest }: { geometry: Geometry[]; fallback: FeatureCollection | null; reference: ReferenceBoundaries | null; selected?: string; fitRequest: number }) {
  const map = useMap(), fittedReference = useRef(false), previousSelection = useRef(selected)
  useEffect(() => {
    if (!reference?.geometry.features.length || fittedReference.current) return
    const [west, south, east, north] = reference.summary.bounds || reference.metadata.bounds
    map.fitBounds([[south, west], [north, east]], { animate: false, padding: [18, 18] })
    fittedReference.current = true
  }, [map, reference])
  useEffect(() => {
    const selectionChanged = previousSelection.current !== selected
    previousSelection.current = selected
    // Initial view belongs to the reference extent. Explicit settlement choices
    // still focus imported geometry; filters and language changes never refit it.
    if (!selectionChanged && (reference || fittedReference.current)) return
    if(selectionChanged && selected && !geometry.length) return
    const source = geometry.length ? { type: 'FeatureCollection' as const, features: geometry.map(value => ({ type: 'Feature' as const, geometry: value, properties: {} })) } : fallback
    if (!source?.features.length) return
    const bounds = L.geoJSON(source).getBounds()
    if (bounds.isValid()) map.fitBounds(bounds, { animate: false, padding: [28, 28], maxZoom: 17 })
  }, [map, geometry, fallback, reference, selected])
  useEffect(() => {
    if (!fitRequest || !reference?.geometry.features.length) return
    const [west, south, east, north] = reference.summary.bounds || reference.metadata.bounds
    map.fitBounds([[south, west], [north, east]], { animate: false, padding: [18, 18] })
  }, [map, reference, fitRequest])
  useEffect(() => { const observer = new ResizeObserver(() => map.invalidateSize()); observer.observe(map.getContainer()); return () => observer.disconnect() }, [map])
  return null
}
function describe(feature: Feature, layer: L.Layer) {
  const element = document.createElement('div'), props = feature.properties || {}
  const title = document.createElement('strong'); title.textContent = props.name || props.scheme_name || props.source_id || t('Mapped object'); element.appendChild(title)
  const detail = document.createElement('p'); detail.textContent = props.category ? t(LABELS[props.category] || 'Context feature') : statusText(props.project_status || 'Context feature'); element.appendChild(detail)
  if (props.osm_edit_timestamp) { const source = document.createElement('small'); source.textContent = t('OSM edit: {date}', { date: formatDate(props.osm_edit_timestamp) }); element.appendChild(source) }
  layer.bindPopup(element)
}
export default function PublicMap({ settlements, selected, onSelect, preview=false, referenceOnly=false, selectedReference, onReferenceSelect }: { preview?: boolean; referenceOnly?: boolean; settlements: PublicSettlement[]; selected?: string; onSelect: (id: string) => void; selectedReference?: number | null; onReferenceSelect?: (number: number) => void }) {
  const [layers, setLayers] = useState(preview?['settlement']:['road', 'amenity', 'transport', 'water_infrastructure', 'settlement', 'project']), [basemap, setBasemap] = useState(true)
  const [spatial, setSpatial] = useState<Spatial | null>(null), [projects, setProjects] = useState<FeatureCollection | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(true), [term, setTerm] = useState('')
  const {data:reference,error:referenceError,loading:referenceLoading,retry:retryReference}=useReferenceBoundaries()
  const [showReference,setShowReference]=useState(true),[fitRequest,setFitRequest]=useState(0)
  const [raster, setRaster] = useState<Raster | null>(null), [showRaster, setShowRaster] = useState(false)
  const vectorLayers = referenceOnly ? '' : layers.filter(c => !['settlement', 'project'].includes(c)).sort().join(',')
  useEffect(() => {
    let active = true; setLoading(true); setError('')
    const load = vectorLayers ? dataApi<Spatial>(`/spatial?category=${encodeURIComponent(vectorLayers)}&limit=10000`) : Promise.resolve({ type: 'FeatureCollection', features: [], total: 0, offset: 0, limit: 10000 } as Spatial)
    load.then(result => { if (active) setSpatial(result) }).catch(problem => { if (active) { setSpatial(null); setError(problem.message) } }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [vectorLayers])
  useEffect(() => { if(preview||referenceOnly)return; let active = true; dataApi<FeatureCollection>('/spatial?category=project&limit=10000').then(result => { if (active) setProjects(result) }).catch(problem => { if (active) setError(problem.message) }); return () => { active = false } }, [preview,referenceOnly])
  useEffect(() => { if(preview||referenceOnly)return; let active = true; dataApi<Raster>('/map-overlay').then(result => { if (active) setRaster(result) }).catch(problem => { if (active) setError(problem.message) }); return () => { active = false } }, [preview,referenceOnly])
  const filtered = useMemo(() => ({ type: 'FeatureCollection' as const, features: spatial?.features.filter(f => !term || `${f.properties?.name || ''} ${JSON.stringify(f.properties?.tags || {})}`.toLowerCase().includes(term.toLowerCase())) || [] }), [spatial, term])
  const selectedRow = settlements.find(row => row.id === selected)
  const focus = useMemo(() => selectedRow ? selectedRow.geometry ? [selectedRow.geometry] : [] : settlements.flatMap(row => row.geometry ? [row.geometry] : []), [selectedRow, settlements])
  function toggle(name: string) { setLayers(old => old.includes(name) ? old.filter(value => value !== name) : [...old, name]) }
  return <section className={`us-panel us-map-panel workspace-map ${preview?'product-preview':''}`}>
    {!preview&&<div className="workspace-map-toolbar">{!referenceOnly&&<input aria-label={t("Search mapped objects")} placeholder={t("Search mapped amenities")} value={term} onChange={event => setTerm(event.target.value)} />}<details><summary>{t("Layers")}</summary><div className="workspace-layer-options"><label><input aria-label={t("2015 Reference Boundaries")} type="checkbox" checked={showReference} onChange={event => setShowReference(event.target.checked)} /><i style={{ background: REFERENCE_COLOR }} />{t("2015 Reference Boundaries")}</label>{!referenceOnly&&Object.keys(COLORS).map(name => <label key={name}><input aria-label={t("{p0} layer", { p0: t(LABELS[name]) })} type="checkbox" checked={layers.includes(name)} onChange={() => toggle(name)} /><i style={{ background: COLORS[name] }} />{t(LABELS[name])}</label>)}<label><input type="checkbox" checked={basemap} onChange={event => setBasemap(event.target.checked)} />{t("Street basemap")}</label>{raster?.available && <label><input aria-label={t("Historical SRA raster layer")} type="checkbox" checked={showRaster} onChange={event => setShowRaster(event.target.checked)} />{t("Historical SRA map (2024)")}</label>}</div></details><button className="us-button" onClick={()=>{setFitRequest(value=>value+1);setShowReference(true);setTerm('');onReferenceSelect?.(0)}}>{t('explore.resetView')}</button></div>}
    {error && <p className="us-alert" role="alert">{t("Map data could not load:")} {errorText(error)}</p>}
    <div className="us-map"><MapContainer center={[19.08,72.88]} zoom={12} zoomSnap={.25} scrollWheelZoom zoomControl={false} fadeAnimation={false} preferCanvas={false} aria-label={t("Settlement map")}><LocalizedMapControls label="Settlement map" /><FitMap geometry={focus} fallback={spatial} reference={reference} selected={selected} fitRequest={fitRequest} />
      {showReference && reference && <HistoricalReferenceLayer data={reference} selected={selectedReference} onSelect={onReferenceSelect} />}
      {basemap && <TileLayer url={import.meta.env.VITE_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'} attribution={import.meta.env.VITE_TILE_ATTRIBUTION || t('map.attribution')} />}
      {showRaster && raster?.available && raster.bounds && <ImageOverlay url={dataAssetUrl('/map-overlay/image')} bounds={[[raster.bounds[1],raster.bounds[0]],[raster.bounds[3],raster.bounds[2]]]} opacity={.65} attribution={t("SRA Mumbai · 2024 historical imagery")} />}
      <Pane name="workspace-context" style={{ zIndex: 420 }}>{spatial && <GeoJSON pane="workspace-context" key={`${getLanguage()}-${vectorLayers}-${term}-${spatial.features.length}`} data={filtered} style={feature => ({ color: COLORS[feature?.properties?.category] || '#888', weight: feature?.properties?.category === 'road' ? 1.3 : 1, fillOpacity: .15 })} pointToLayer={(feature, latlng) => L.circleMarker(latlng, { radius: 5, fillColor: COLORS[feature.properties.category] || '#246f88', color: '#fff', weight: 1, fillOpacity: .95 })} onEachFeature={describe} />}</Pane>
      {layers.includes('settlement') && settlements.filter(row => row.geometry).map(row => <GeoJSON key={`${getLanguage()}-${row.id}-${selected === row.id}`} data={row.geometry!} style={{ color: selected === row.id ? '#193f35' : COLORS.settlement, weight: selected === row.id ? 3 : 2, fillColor: COLORS.settlement, fillOpacity: selected === row.id ? .38 : .15 }} eventHandlers={{ click: () => onSelect(row.id) }} onEachFeature={(_feature, layer) => { layer.bindTooltip(row.name); layer.on('add', () => { const element = (layer as L.Path).getElement?.(); if (element) { element.setAttribute('aria-label', t('Settlement boundary {name}', { name: row.name })); element.setAttribute('role', 'button'); element.setAttribute('tabindex', '0'); element.addEventListener('keydown', event => { if ((event as KeyboardEvent).key === 'Enter') onSelect(row.id) }) } }) }} />)}
      {layers.includes('project') && projects && <GeoJSON key={`project-${getLanguage()}`} data={projects} style={{ color: COLORS.project }} onEachFeature={describe} />}
    </MapContainer></div>
    <div className="workspace-map-legend">{showReference && reference && <span><i style={{ background: REFERENCE_COLOR }} />{t("2015 Reference Boundaries")}</span>}{settlements.some(row => row.geometry) && <span><i style={{ background: COLORS.settlement }} />{t("Settlement")}</span>}{selectedRow?.geometry && <span><i style={{ background: '#193f35' }} />{t("Selected")}</span>}{spatial?.features.some(feature => feature.properties?.category === 'amenity') && <span><i style={{ background: COLORS.amenity }} />{t("Amenity")}</span>}<span role="status">{referenceOnly ? t('civic.historicalLayer') : loading ? t("Loading context…") : t("{p0} context objects", { p0: formatNumber(filtered.features.length) })}</span></div>
    <div className="workspace-reference-layer" aria-label={t("Historical boundary information")}>
      <p className="workspace-reference-notice">{t(HISTORICAL_NOTICE)}</p>
      <div className="workspace-reference-status"><span role="status">{referenceLoading ? t("Loading 2015 reference boundaries…") : referenceError ? t("2015 reference boundaries are unavailable.") : reference?.geometry.features.length ? showReference ? t("{shown} of {total} reference polygons displayed", { shown: formatNumber(reference.geometry.features.length, 0), total: formatNumber(reference.metadata.source_feature_count, 0) }) : t("Reference boundary layer hidden") : t("No reference boundaries available.")}</span>{reference && <button className="us-button" disabled={!reference.geometry.features.length} onClick={() => { setShowReference(true); setFitRequest(old => old + 1) }}>{t("Fit reference boundaries")}</button>}</div>
      {referenceError && <div role="alert" className="workspace-reference-error">{errorText(referenceError)} <button className="us-button" onClick={() => retryReference()}>{t("Retry reference boundaries")}</button></div>}
      {!preview && reference && <details><summary>{t("Boundary source & limitations")}</summary><p>{t(reference.metadata.source_attribution_key)} · <a href={reference.metadata.source_catalog_url} target="_blank" rel="noreferrer">{t("Source catalogue")}</a></p><p>{t("Source year: 2015. Original retrieval date: {date}.", { date: reference.metadata.retrieved_at ? formatDate(reference.metadata.retrieved_at) : t("Unknown") })}</p>{reference.skippedCount > 0 && <p>{t("{count} invalid polygons excluded without repair. The original file is preserved.", { count: formatNumber(reference.skippedCount, 0) })}</p>}<p>{t("These boundaries do not establish current conditions, housing eligibility, redevelopment progress or service coverage.")}</p><p>{t("No match to 2024 records or Census aggregates; polyno is only a technical source reference when present.")}</p><p>{t("Licence: Public Domain according to the supplied OpenCity catalogue; SRA reuse terms have not been independently verified.")}</p></details>}
    </div>
    {!preview && selectedRow && !selectedRow.geometry && <p className="workspace-map-note">{t("No boundary supplied for {name}. Add its GeoJSON geometry from Data.", {name: selectedRow.name})}</p>}
    {showRaster && <p className="workspace-map-note">{t("Historical map imagery is for visual reference.")} {raster?.source_url && <a href={raster.source_url} target="_blank" rel="noreferrer">{t("Source")}</a>}</p>}
    {!loading && term && !filtered.features.length && <p className="workspace-map-note">{t("No mapped objects match this search.")}</p>}
  </section>
}
