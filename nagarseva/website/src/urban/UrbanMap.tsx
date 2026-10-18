import { useEffect, useMemo } from 'react'
import { CircleMarker, GeoJSON, MapContainer, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { score } from './engine'
import type { Cluster, Dataset, Key, Weights } from './engine'

function Fit({ clusters }: { clusters: Cluster[] }) {
  const map = useMap()
  const bounds = useMemo(() => clusters.flatMap(cluster => {
    if (!cluster.geometry) return []
    const rings = cluster.geometry.type === 'Polygon' ? cluster.geometry.coordinates : cluster.geometry.coordinates.flat()
    return rings.flat().map(([lon, lat]) => [lat, lon] as [number, number])
  }), [clusters])
  useEffect(() => {
    if (bounds.length) map.fitBounds(bounds, { padding: [35, 35], maxZoom: 16, animate: false })
    const timer = setTimeout(() => map.invalidateSize({ animate: false }), 50)
    return () => clearTimeout(timer)
  }, [map, bounds])
  return null
}
export default function UrbanMap({ data, clusters, selected, onSelect, weights, layer = 'priority', roads = true, amenities = true, basemap = false, compact = false }: {
  data: Dataset; clusters: Cluster[]; selected: string; onSelect: (id: string) => void; weights: Weights; layer?: Key | 'priority'; roads?: boolean; amenities?: boolean; basemap?: boolean; compact?: boolean
}) {
  const nodes = new Map(data.network.nodes.map(node => [node.id, node]))
  const tileUrl = import.meta.env.VITE_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
  return <div className={`us-map ${compact ? 'compact' : ''}`}>
    <MapContainer center={[19.057, 72.920]} zoom={15} scrollWheelZoom={false} zoomAnimation={false} fadeAnimation={false} markerZoomAnimation={false} aria-label="Synthetic settlement cluster map">
      {basemap && <TileLayer url={tileUrl} attribution={import.meta.env.VITE_TILE_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'} />}
      <Fit clusters={clusters} />
      {roads && data.network.edges.filter(edge => edge.walkable).map((edge, index) => { const a = nodes.get(edge.from)!, b = nodes.get(edge.to)!; return <Polyline key={index} positions={[[a.lat, a.lon], [b.lat, b.lon]]} pathOptions={{ color: '#8b9e98', weight: 3, opacity: .6, dashArray: '5 5' }}><Tooltip>Demonstration walking edge</Tooltip></Polyline> })}
      {clusters.filter(cluster => cluster.geometry).map(cluster => {
        const value = layer === 'priority' ? score(cluster.indicators, weights).score : cluster.indicators[layer]
        const color = value === null ? '#7e8c90' : value >= 60 ? '#c56c49' : value >= 45 ? '#c49a4d' : '#4b8b76'
        return <GeoJSON key={`${cluster.id}-${cluster.id === selected}-${color}`} data={cluster.geometry!} style={{ color: cluster.id === selected ? '#173f3b' : color, fillColor: color, fillOpacity: cluster.id === selected ? .68 : .36, weight: cluster.id === selected ? 3 : 1.5 }} eventHandlers={{ click: () => onSelect(cluster.id) }}>
          <Tooltip direction="center" permanent className="us-map-label">{cluster.id}<span>{value === null ? 'Unassessed' : value.toFixed(1)}</span></Tooltip>
        </GeoJSON>
      })}
      {amenities && data.amenities.map(amenity => { const node = nodes.get(amenity.node_id)!; return <CircleMarker key={amenity.id} center={[node.lat, node.lon]} radius={6} pathOptions={{ color: '#fff', weight: 2, fillColor: '#294b5a', fillOpacity: 1 }}><Tooltip>{amenity.name} · synthetic</Tooltip></CircleMarker> })}
    </MapContainer>
    <div className="us-map-caption"><span><i className="us-dot rust" />Higher demo deficit</span><span><i className="us-dot green" />Lower demo deficit</span><span><i className="us-dot gray" />Missing data</span><b>Synthetic boundaries & routes</b></div>
  </div>
}
