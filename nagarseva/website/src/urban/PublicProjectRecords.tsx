import { useEffect, useRef, useState } from 'react'
import { sourceUrl } from './sourceUrl'
import { t, errorText, formatDate, formatNumber, statusText } from '../i18n/locale'
import { dataApi, exportPublicCsv } from './publicClient'
import type { PublicProject } from './publicClient'

type Page = { items: PublicProject[]; total: number; complete?: boolean | null; pages_retrieved?: number | null; wards?: string[] }
export default function PublicProjectRecords() {
  const [term, setTerm] = useState(''), [search, setSearch] = useState(''), [page, setPage] = useState(1), [ward,setWard] = useState(''), [selected,setSelected] = useState<PublicProject|null>(null)
  const [result, setResult] = useState<Page | null>(null), [busy, setBusy] = useState(true), [error, setError] = useState(''), [attempt, setAttempt] = useState(0)
  useEffect(() => { const timer = setTimeout(() => { setSearch(term); setPage(1) }, 250); return () => clearTimeout(timer) }, [term])
  useEffect(() => {
    let active = true; setBusy(true); setError('')
    dataApi<Page>(`/projects?search=${encodeURIComponent(search)}&page=${page}&page_size=20&ward=${encodeURIComponent(ward)}`).then(data => { if (active) setResult(data) }).catch(problem => { if (active) { setResult(null); setError(problem.message) } }).finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [page, search, ward, attempt])
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(()=>{if(selected)dialog.current?.showModal();else dialog.current?.close()},[selected])
  return <div className="workspace-project-records">
    <p className="us-small">{t('Published scheme listings are separate records. Unknown status and missing settlement links remain unknown; no match to the 2015 polygons is made.')}</p>
    <div className="us-toolbar"><input aria-label={t('Search project listings')} placeholder={t('Scheme name or ward')} value={term} onChange={event => setTerm(event.target.value)} /><select aria-label={t("projects.wardFilter")} value={ward} onChange={event=>{setWard(event.target.value);setPage(1)}}><option value="">{t("All wards")}</option>{result?.wards?.map(value=><option key={value} value={value}>{value}</option>)}</select><button className="us-button" onClick={() => exportPublicCsv('projects', '').catch(problem => setError(problem.message))}>{t('Export projects CSV')}</button></div>
    {error && <div role="alert" className="us-alert">{errorText(error)} <button className="us-button" onClick={() => setAttempt(value => value + 1)}>{t('Retry project records')}</button></div>}
    {busy && <p role="status">{t('Loading project records…')}</p>}
    {result && !busy && <><p>{t('{count} published project records', { count: formatNumber(result.total, 0) })}{result.complete === false && <> · {t('Partial source listing; acquisition did not establish a complete register.')}</>}</p>
      {result.items.length ? <div className="us-table-wrap"><table><thead><tr><th>{t('Project')}</th><th>{t('Ward / village')}</th><th>{t('Recorded status')}</th><th>{t('Settlement link')}</th><th>{t('Source date')}</th></tr></thead><tbody>{result.items.map(row => <tr key={row.id}><td><button className="us-table-button" onClick={()=>setSelected(row)}>{row.scheme_name}</button>{row.cts_raw && <small>{t('CTS (source text):')} {row.cts_raw}</small>}</td><td>{row.administrative_area || t('Not supplied')}<small>{row.village || t('Not supplied')}</small></td><td>{statusText(row.project_status)}</td><td>{row.settlement_id || t('Not linked')}</td><td>{formatDate(row.source_date)}</td></tr>)}</tbody></table></div> : <p className="us-empty">{search||ward?t('No project records match this search.'):t('projects.empty')}</p>}
      <div className="workspace-pagination"><span>{t('Page {page} of {pages}', { page: formatNumber(page, 0), pages: formatNumber(Math.max(1, Math.ceil(result.total / 20)), 0) })}</span><button className="us-button" disabled={page === 1} onClick={() => setPage(value => value - 1)}>{t('Previous')}</button><button className="us-button" disabled={page * 20 >= result.total} onClick={() => setPage(value => value + 1)}>{t('Next')}</button></div>
    </>}
    {selected && <dialog ref={dialog} aria-labelledby="project-detail-title" className="product-dialog" onCancel={()=>setSelected(null)}><button autoFocus className="us-button product-dialog-close" onClick={()=>setSelected(null)} onKeyDown={event=>{if(event.key==='Escape')setSelected(null)}}>{t('Close')}</button><h2 id="project-detail-title">{selected.scheme_name}</h2><p className="us-small">{t('projects.detailNote')}</p><dl className="us-facts"><div><dt>{t('projects.localReference')}</dt><dd>{selected.id}</dd></div><div><dt>{t('Ward / village')}</dt><dd>{selected.administrative_area||t('Not supplied')} · {selected.village||t('Not supplied')}</dd></div><div><dt>{t('CTS (source text):')}</dt><dd>{selected.cts_raw||t('Not supplied')}</dd></div><div><dt>{t('Recorded status')}</dt><dd>{statusText(selected.project_status)}</dd></div><div><dt>{t('Settlement link')}</dt><dd>{selected.settlement_id||t('Not linked')}</dd></div><div><dt>{t('Source date')}</dt><dd>{formatDate(selected.source_date)}</dd></div></dl>{sourceUrl(selected.source_url)?<a href={sourceUrl(selected.source_url)} target="_blank" rel="noreferrer">{t('Source')}</a>:<span>{selected.source_url||t('Not supplied')}</span>}</dialog>}
  </div>
}
