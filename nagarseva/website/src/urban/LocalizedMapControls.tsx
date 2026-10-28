import L from 'leaflet'
import { useEffect } from 'react'
import { useMap, ZoomControl } from 'react-leaflet'
import { useLanguage } from '../i18n/LanguageProvider'
import { t } from '../i18n/locale'

/** Update native Leaflet labels while keeping one map/control and its viewport. */
export default function LocalizedMapControls({ label }: { label: string }) {
  const map = useMap(), { language } = useLanguage()
  useEffect(() => {
    const container = map.getContainer()
    container.setAttribute('aria-label', t(label))
    const update = () => {
      for (const [selector, message] of [['.leaflet-control-zoom-in', 'Zoom in'], ['.leaflet-control-zoom-out', 'Zoom out'], ['.leaflet-popup-close-button', 'Close popup']]) {
        const button = container.querySelector(selector)
        button?.setAttribute('title', t(message)); button?.setAttribute('aria-label', t(message))
      }
    }
    update(); map.on('popupopen', update)
    if (!import.meta.env.VITE_TILE_ATTRIBUTION) {
      map.eachLayer(layer => {
        if (!(layer instanceof L.TileLayer)) return
        const previous = layer.getAttribution?.(), next = t('map.attribution')
        if (previous === next) return
        if (previous) map.attributionControl.removeAttribution(previous)
        layer.options.attribution = next
        map.attributionControl.addAttribution(next)
      })
    }
    return () => { map.off('popupopen', update) }
  }, [map, language, label])
  return <ZoomControl />
}
