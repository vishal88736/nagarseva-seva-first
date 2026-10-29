import { useEffect, useRef } from 'react'
import { GeoJSON, Pane, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { Feature, Polygon } from 'geojson'
import { useLanguage } from '../i18n/LanguageProvider'
import { t } from '../i18n/locale'
import type { ReferenceBoundaries, ReferenceProperties } from './historicalBoundaries'
import { HISTORICAL_NOTICE, referenceLabel } from './referencePresentation'

export { HISTORICAL_NOTICE } from './referencePresentation'
export const REFERENCE_COLOR = '#2378f5'
function popup(feature: Feature<Polygon, ReferenceProperties>, data: ReferenceBoundaries, number: number) {
  const element = document.createElement('div'); element.className = 'reference-boundary-popup'; element.setAttribute('role','region'); element.setAttribute('aria-label',t('explore.historicalDetail'))
  const title = document.createElement('strong'); title.textContent = referenceLabel(number); element.append(title)
  for (const text of [t(HISTORICAL_NOTICE),t('civic.generatedReference'),t('civic.boundarySource')+': OpenCity · 2015']) {
    const paragraph = document.createElement('p'); paragraph.textContent = text; element.append(paragraph)
  }
  const properties = document.createElement('pre'); properties.textContent = JSON.stringify(feature.properties,null,2); element.append(properties)
  const link = document.createElement('a'); link.href = data.metadata.source_catalog_url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = t('Source catalogue'); element.append(link)
  return element
}
export default function HistoricalReferenceLayer({ data, selected, onSelect }: { data: ReferenceBoundaries; selected?: number | null; onSelect?: (number: number) => void }) {
  const group = useRef<L.GeoJSON>(null), { language } = useLanguage(), map = useMap()
  const onSelectRef = useRef(onSelect); onSelectRef.current = onSelect
  const selectedRef = useRef(selected); selectedRef.current = selected
  useEffect(() => {
    group.current?.eachLayer(layer => {
      const path = layer as L.Path & { feature: Feature<Polygon, ReferenceProperties> }
      const index = data.geometry.features.indexOf(path.feature), number = data.sourceFeatureNumbers[index], active = selected === number
      path.setStyle({ color: active ? '#00544f' : REFERENCE_COLOR, weight: active ? 4 : 1.3, opacity: 1, fillColor: active ? '#00a69c' : REFERENCE_COLOR, fillOpacity: active ? .35 : .07 })
      const element = path.getElement(); element?.classList.toggle('is-selected',active)
      element?.setAttribute('aria-pressed',String(active)); element?.setAttribute('aria-label',referenceLabel(number))
      if (active) path.bringToFront()
      if (path.isPopupOpen()) path.getPopup()?.setContent(popup(path.feature,data,number))
    })
  }, [language,data,selected])
  useEffect(() => {
    const index = selected == null ? -1 : data.sourceFeatureNumbers.indexOf(selected), feature = data.geometry.features[index]
    if (!feature) { map.closePopup(); return }
    const bounds = L.geoJSON(feature).getBounds()
    if (bounds.isValid()) map.fitBounds(bounds,{padding:[40,40],maxZoom:17,animate:false})
    // A selection can change the viewport after a click has opened a popup.
    // Recompute its position and auto-pan inside the actual map viewport.
    group.current?.eachLayer(layer=>{if(layer.isPopupOpen())layer.getPopup()?.update()})
  }, [selected,data,map])
  return <Pane name="historical-reference-boundaries" style={{ zIndex: 410 }}><GeoJSON ref={group} data={data.geometry} style={feature=>{const active=selected!=null&&selected===data.sourceFeatureNumbers[data.geometry.features.indexOf(feature as Feature<Polygon,ReferenceProperties>)];return {color:active?'#00544f':REFERENCE_COLOR,weight:active?4:1.3,opacity:1,fillColor:active?'#00a69c':REFERENCE_COLOR,fillOpacity:active ? .35 : .07,className:'us-reference-boundary'}}} onEachFeature={(feature, layer) => {
    const typed = feature as Feature<Polygon,ReferenceProperties>, number = data.sourceFeatureNumbers[data.geometry.features.indexOf(typed)]
    layer.bindPopup(() => popup(typed,data,number))
    layer.on('click',()=>onSelectRef.current?.(number))
    layer.on('add',()=>{
      const element = (layer as L.Path).getElement(); if (!element) return
      const active = selectedRef.current === number
      element.classList.toggle('is-selected',active); element.setAttribute('aria-pressed',String(active))
      ;(layer as L.Path).setStyle({color:active?'#00544f':REFERENCE_COLOR,weight:active?4:1.3,fillColor:active?'#00a69c':REFERENCE_COLOR,fillOpacity:active ? .35 : .07})
      element.setAttribute('aria-label',referenceLabel(number)); element.setAttribute('role','button'); element.setAttribute('tabindex','-1')
      // The paginated table provides keyboard access without 2,500 tab stops.
      element.addEventListener('keydown',event=>{if(['Enter',' '].includes((event as KeyboardEvent).key)){event.preventDefault();onSelectRef.current?.(number);layer.openPopup((layer as L.Polygon).getBounds().getCenter())}})
    })
  }}/></Pane>
}
