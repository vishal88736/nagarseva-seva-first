import { ReactNode, useEffect, useState } from 'react'
import { ArrowUpRight, Info } from 'lucide-react'
import { MapContainer, ImageOverlay, TileLayer, CircleMarker, Popup, ZoomControl, useMap } from 'react-leaflet'
import { Pocket, number } from '../lib/api'
import 'leaflet/dist/leaflet.css'
import { useI18n } from '../i18n'

export const tierColors: Record<string, string> = { Critical: '#dc5b50', High: '#e9a73c', Medium: '#159d9a', Low: '#698cc6', Unassessed: '#889797' }
export function Badge({ children, tone = 'teal' }: { children: ReactNode; tone?: string }) { return <span className={`badge ${tone}`}>{children}</span> }
export function SectionTitle({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) { return <div className="section-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div> }
export function Metric({ label, value, note, icon, color = 'teal' }: { label: string; value: string; note?: string; icon?: ReactNode; color?: string }) { return <div className="metric card"><div className={`metric-icon ${color}`}>{icon}</div><span>{label}</span><strong>{value}</strong><small>{note && <ArrowUpRight size={13} />}{note}</small></div> }
export function Panel({ title, subtitle, children, action, className = '' }: { title?: string; subtitle?: string; children: ReactNode; action?: ReactNode; className?: string }) { return <section className={`card panel ${className}`}>{title && <div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>}{children}</section> }
export function Note({ children }: { children: ReactNode }) { return <div className="note"><Info size={16} /><span>{children}</span></div> }
function FitLocations({ locations, small }: { locations: Pocket[]; small: boolean }) {
  const map = useMap()
  const bounds = locations.length ? [Math.min(...locations.map(p => p.lat)), Math.min(...locations.map(p => p.lon)), Math.max(...locations.map(p => p.lat)), Math.max(...locations.map(p => p.lon))] : []
  const key = bounds.join(',')
  useEffect(() => {
    if (bounds.length) map.fitBounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]], { padding: [24, 24], maxZoom: small ? 13 : 12, animate: false })
  }, [map, key, small])
  return null
}
export function PocketMap({ pockets, onSelect, mode = 'priority', small = false }: { pockets: Pocket[]; onSelect?: (id: string) => void; mode?: string; small?: boolean }) {
  const { t } = useI18n()
  const [geographic, setGeographic] = useState(navigator.onLine)
  const tileUrl = import.meta.env.VITE_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
  const cityLabels: Record<string, string> = { Mumbai: t('cityMumbai'), Thane: t('cityThane'), Kalyan: t('cityKalyan'), Ambarnath: t('cityAmbarnath'), Ulhasnagar: t('cityUlhasnagar') }
  const locations = pockets.filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lon))
  return <div className={`map-shell ${small ? 'small' : ''}`}><MapContainer center={[19.17, 73.04]} zoom={11} zoomControl={false} scrollWheelZoom={false} attributionControl={false} preferCanvas>
    {geographic ? <TileLayer url={tileUrl} maxZoom={19} eventHandlers={{ tileerror: () => setGeographic(false) }} /> : <ImageOverlay url="/mmr-map.svg" bounds={[[18.91, 72.77], [19.34, 73.29]]} />}
    <ZoomControl position="bottomright" />
    <FitLocations locations={locations} small={small} />
     {locations.map(p => {
      const risk = mode === 'flood' ? p.flood_risk_score : mode === 'fire' ? p.fire_risk_score : mode === 'services' ? p.water_hours_per_day === null ? null : 100 - p.water_hours_per_day * 8 : p.priority_score
      const color = mode === 'priority' ? tierColors[p.tier] : risk === null ? '#889797' : risk > 70 ? '#dc5b50' : risk > 45 ? '#e9a73c' : '#159d9a'
       return <CircleMarker key={p.pocket_id} center={[p.lat, p.lon]} radius={small ? 5 : 7} pathOptions={{ color: '#fff', fillColor: color, fillOpacity: .85, weight: 2 }} eventHandlers={{ click: () => onSelect?.(p.pocket_id) }}><Popup><strong>{p.pocket_id}</strong><p>{cityLabels[p.city] || p.city} · {p.ward}</p><p>{t('priorityLabel')}: {p.priority_score?.toFixed(1) ?? '—'} · {t(`tier.${p.tier.toLowerCase()}`)}</p><button onClick={() => onSelect?.(p.pocket_id)}>{t('viewPocket')} →</button></Popup></CircleMarker>
     })}
   </MapContainer><div className="map-footer"><div className="map-caption">{t(geographic ? 'mapGeographic' : 'mapSchematic')} · {number(locations.length)} {t('shownOnMap')}</div><div className="map-legend">{Object.entries(tierColors).map(([tier, color]) => <span key={tier}><i style={{ background: color }} />{t(`tier.${tier.toLowerCase()}`)}</span>)}</div><div className="map-source-row"><button className="text-button" onClick={() => setGeographic(v => !v)}>{t(geographic ? 'mapUseSchematic' : 'mapUseGeography')}</button>{geographic && <><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a><a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noopener noreferrer">{t('mapIssue')}</a></>}</div></div></div>
}
export const chartColors = { teal: '#159d9a', amber: '#e9a73c', red: '#dc5b50', navy: '#173c54' }
