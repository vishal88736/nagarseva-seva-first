import { useEffect, useRef } from 'react'
import { GeoJSON, Pane } from 'react-leaflet'
import L from 'leaflet'
import type { Feature, Polygon } from 'geojson'
import { useLanguage } from '../i18n/LanguageProvider'
import { t } from '../i18n/locale'
import type { ReferenceBoundaries, ReferenceProperties } from './historicalBoundaries'

export const HISTORICAL_NOTICE = 'Historical reference boundaries — 2015. Not verified against the 2024 SRA cluster list.'
export const REFERENCE_COLOR = '#668894'
function popup(feature: Feature<Polygon, ReferenceProperties>, data: ReferenceBoundaries) {
  const element = document.createElement('div'); element.className = 'reference-boundary-popup'
  const title = document.createElement('strong'); title.textContent = t('2015 Reference Boundaries'); element.append(title)
  const notice = document.createElement('p'); notice.textContent = t(HISTORICAL_NOTICE); element.append(notice)
  const reference = document.createElement('p'); reference.textContent = t('Polygon technical reference: {reference}', { reference: feature.properties.polyno ?? t('Not available in the supplied GeoJSON') }); element.append(reference)
  const qualification = document.createElement('small'); qualification.textContent = t('A technical polygon reference is not an SRA cluster ID.'); element.append(qualification)
  const source = document.createElement('p'); source.textContent = t(data.metadata.source_attribution_key); element.append(source)
  const link = document.createElement('a'); link.href = data.metadata.source_catalog_url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = t('Source catalogue'); element.append(link)
  return element
}
export default function HistoricalReferenceLayer({ data }: { data: ReferenceBoundaries }) {
  const group = useRef<L.GeoJSON>(null), { language } = useLanguage()
  useEffect(() => {
    group.current?.eachLayer(layer => {
      const path = layer as L.Path & { feature?: Feature<Polygon, ReferenceProperties> }
      path.getElement()?.setAttribute('aria-label', t('2015 reference boundary'))
      if (path.isPopupOpen() && path.feature) path.getPopup()?.setContent(popup(path.feature, data))
    })
  }, [language, data])
  return <Pane name="historical-reference-boundaries" style={{ zIndex: 390 }}><GeoJSON ref={group} data={data.geometry} style={{ color: REFERENCE_COLOR, weight: 1, opacity: .8, fillColor: REFERENCE_COLOR, fillOpacity: .04, className: 'us-reference-boundary' }} onEachFeature={(feature, layer) => {
    layer.bindPopup(() => popup(feature as Feature<Polygon, ReferenceProperties>, data))
    layer.on('add', () => {
      const path = layer as L.Path, element = path.getElement()
      if (!element) return
      element.setAttribute('aria-label', t('2015 reference boundary')); element.setAttribute('role', 'button'); element.setAttribute('tabindex', '0')
      element.addEventListener('keydown', event => { if (['Enter', ' '].includes((event as KeyboardEvent).key)) { event.preventDefault(); layer.openPopup((layer as L.Polygon).getBounds().getCenter()) } })
    })
  }} /></Pane>
}
