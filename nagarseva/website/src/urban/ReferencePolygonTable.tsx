import { useMemo, useState } from 'react'
import { useLanguage } from '../i18n/LanguageProvider'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Eye, Search } from 'lucide-react'
import { t, formatNumber } from '../i18n/locale'
import { HISTORICAL_NOTICE, referenceLabel, availableProperties } from './referencePresentation'
import type { ReferenceBoundaries } from './historicalBoundaries'
export default function ReferencePolygonTable({ data, selected, onSelect, compact = false }: {
  data: ReferenceBoundaries; selected?: number | null; onSelect: (number: number) => void; compact?: boolean;
}) {
  const { language } = useLanguage()
  const [search,setSearch] = useState(''), [page,setPage] = useState(0)
  const size = compact ? 5 : 10
  const rows = useMemo(() => data.geometry.features.map((feature,index) => ({ feature, number: data.sourceFeatureNumbers[index] })).filter(row => {
    // Accept the localized UI reference or its number, never pretend to search absent names.
    const normalized = search.replace(/[०-९]/g, character => String(character.charCodeAt(0)-0x0966)).trim().toLowerCase()
    return !normalized || (normalized.match(/^\d+$/) ? row.number === Number(normalized) : referenceLabel(row.number).toLowerCase().includes(search.trim().toLowerCase()))
  }), [data,search,language])
  const pages = Math.max(1,Math.ceil(rows.length/size)), current = Math.min(page,pages-1), shown = rows.slice(current*size,(current+1)*size)
  return <section className="us-panel reference-table-panel" aria-label={t('civic.polygonTable')}>
    <div className="reference-table-header"><div><h2>{t('nav.settlements')}</h2><p>{t('civic.tableIntro')}</p></div><label className="reference-search"><Search size={17}/><input type="search" aria-label={t('civic.referenceSearch')} placeholder={t('civic.referencePlaceholder')} value={search} onChange={event=>{setSearch(event.target.value);setPage(0)}}/></label></div>
    <p className="historical-disclaimer">{t(HISTORICAL_NOTICE)}</p>
    {!compact && <p className="us-small">{t('civic.noNameSearch')} {t('civic.generatedReference')}</p>}
    <div className="us-table-wrap"><table className="reference-polygon-table"><thead><tr><th scope="col">{t('civic.reference')}</th><th scope="col">{t('civic.boundarySource')}</th><th scope="col">{t('civic.sourceYear')}</th><th scope="col">{t('Verification status')}</th><th scope="col">{t('civic.sourceProperties')}</th><th scope="col">{t('Action')}</th></tr></thead><tbody>{shown.map(({feature,number})=><tr key={number} className={number===selected?'selected':''}><td>{referenceLabel(number)}</td><td>OpenCity</td><td>2015</td><td><span className="us-tag amber">{t('Historical reference')}</span></td><td>{availableProperties(feature.properties).length ? availableProperties(feature.properties).map(([key])=>key).join(', ') : t('civic.noneProvided')}</td><td><button className="reference-view" onClick={()=>onSelect(number)} aria-label={t('civic.viewReference',{reference:referenceLabel(number)})}><Eye size={18}/></button></td></tr>)}</tbody></table></div>
    {!rows.length && <p className="us-empty">{t('civic.noReferences')}</p>}
    <div className="workspace-pagination reference-pagination"><span role="status">{t('civic.showing',{start:formatNumber(rows.length?current*size+1:0,0),end:formatNumber(Math.min((current+1)*size,rows.length),0),total:formatNumber(rows.length,0)})}</span><div><button aria-label={t('civic.firstPage')} disabled={!current} onClick={()=>setPage(0)}><ChevronsLeft size={16}/></button><button aria-label={t('Previous')} disabled={!current} onClick={()=>setPage(current-1)}><ChevronLeft size={16}/></button><span>{t('Page {page} of {pages}',{page:formatNumber(current+1,0),pages:formatNumber(pages,0)})}</span><button aria-label={t('Next')} disabled={current===pages-1} onClick={()=>setPage(current+1)}><ChevronRight size={16}/></button><button aria-label={t('civic.lastPage')} disabled={current===pages-1} onClick={()=>setPage(pages-1)}><ChevronsRight size={16}/></button></div></div>
  </section>
}
