import { MapPinned, X } from 'lucide-react'
import { t } from '../i18n/locale'
import type { ReferenceBoundaries } from './historicalBoundaries'
import { referenceLabel, availableProperties, HISTORICAL_NOTICE } from './referencePresentation'

export default function ReferencePolygonDetails({ data, selected, onClose }: { data: ReferenceBoundaries; selected: number | null; onClose: () => void }) {
  const index = selected == null ? -1 : data.sourceFeatureNumbers.indexOf(selected), feature = data.geometry.features[index]
  if (!feature || selected == null) return <aside className="us-panel reference-detail"><MapPinned size={30}/><h2>{t('civic.selectPolygon')}</h2><p>{t('civic.selectionHint')}</p><p className="us-small">{t('civic.generatedReference')}</p></aside>
  const properties = availableProperties(feature.properties)
  return <aside className="us-panel reference-detail" aria-label={t('explore.historicalDetail')} aria-live="polite"><div className="reference-detail-heading"><h2>{referenceLabel(selected)}</h2><button className="us-icon-button" aria-label={t('civic.clearSelection')} onClick={onClose}><X size={18}/></button></div><p className="us-small">{t('civic.generatedReference')}</p><dl className="us-facts"><div><dt>{t('civic.boundarySource')}</dt><dd>OpenCity</dd></div><div><dt>{t('civic.sourceYear')}</dt><dd>2015</dd></div><div><dt>{t('Geometry type')}</dt><dd>{feature.geometry.type}</dd></div><div><dt>{t('civic.sourceProperties')}</dt><dd>{properties.length?properties.map(([key,value])=><div key={key}><code>{key}</code>: {typeof value==='object'?JSON.stringify(value):String(value)}</div>):t('civic.notInDataset')}</dd></div></dl><details><summary>{t('civic.rawProperties')}</summary><pre>{JSON.stringify(feature.properties,null,2)}</pre></details><p className="historical-disclaimer">{t(HISTORICAL_NOTICE)}</p><a href={data.metadata.source_catalog_url} target="_blank" rel="noreferrer">{t('Source catalogue')}</a></aside>
}
