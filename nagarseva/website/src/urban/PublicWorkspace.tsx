import { sourceUrl } from './sourceUrl'
import { LanguageSwitcher, localizedPageTitle, useLanguage } from '../i18n/LanguageProvider'
import { t, errorText, formatDate, formatNumber, statusText } from '../i18n/locale'
import { Database, LayoutDashboard, MapPinned, Menu, MessageSquarePlus, FolderOpen, Search, X } from 'lucide-react'
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { DEFAULT_WEIGHTS } from './engine'
import { dataApi, planningDataset } from './publicClient'
import type { Health, Metadata, PriorityRow, PublicProject, PublicSettlement, Stats } from './publicClient'
import { Compare, Heading, Panel } from './PlanningPages'
import { collectPages } from './pagination'
import WorkspaceData from './WorkspaceData'
import { MAIN_ROUTES, PATHS, routePage, activeSection } from './routing'
import type { Page } from './routing'
import ProductDashboard from './ProductDashboard'
import IssueReport from './IssueReport'
import ProjectsReports from './ProjectsReports'
import WorkspacePriorities from './WorkspacePriorities'

const PublicMap = lazy(() => import('./PublicMap'))
const PublicAssurance = lazy(() => import('./PublicAssurance'))
export default function PublicWorkspace({ onDemo }: { onDemo: () => void }) {
  const { language } = useLanguage()
  const [route, setRoute] = useState(() => ({ page: routePage(location.pathname,location.hash), query: location.search })), [mobile, setMobile] = useState(false)
  const page = route.page
  const [metadata, setMetadata] = useState<Metadata | null>(null), [stats, setStats] = useState<Stats | null>(null), [health, setHealth] = useState<Health | null>(null), [settlements, setSettlements] = useState<PublicSettlement[]>([])
  const [priority, setPriority] = useState<PriorityRow[]>([]), [selectedId, setSelectedId] = useState(() => new URL(location.href).searchParams.get('settlement') || ''), [search, setSearch] = useState(''), [ward, setWard] = useState(''), [village,setVillage] = useState(''), [listPage, setListPage] = useState(0)
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS), [error, setError] = useState(''), [loading, setLoading] = useState(true), [indicatorError, setIndicatorError] = useState(''), [revision, setRevision] = useState(0)
  const [key, setKey] = useState(() => sessionStorage.getItem('urbansaarthi-officer-key') || ''), [draft, setDraft] = useState<Record<string, unknown> | null>(null), [linkedProjects, setLinkedProjects] = useState<PublicProject[]>([]), [projectError, setProjectError] = useState('')
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [m, s, h, records] = await Promise.all([dataApi<Metadata>('/metadata'), dataApi<Stats>('/overview'), dataApi<Health>('/health'), collectPages<PublicSettlement>((number, size) => dataApi(`/settlements?page=${number}&page_size=${size}`))])
      setMetadata(m); setStats(s); setHealth(h); setSettlements(records); setPriority([]); setDraft(null); setSearch(''); setWard(''); setVillage(''); setListPage(0)
      setSelectedId(old => records.some(r => r.id === old) ? old : records.find(r => r.geometry)?.id || records[0]?.id || '')
      setRevision(old => old + 1)
    } catch (problem) { setError((problem as Error).message) } finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])
  useEffect(() => {
    if (!mobile) return
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') { setMobile(false); document.querySelector<HTMLButtonElement>('.us-mobile-nav')?.focus() } }
    addEventListener('keydown', close)
    return () => removeEventListener('keydown', close)
  }, [mobile])
  useEffect(() => { const listener = () => { setRoute({page:routePage(location.pathname,location.hash),query:location.search}); setMobile(false) }; addEventListener('popstate',listener);addEventListener('hashchange',listener); return()=>{removeEventListener('popstate',listener);removeEventListener('hashchange',listener)} }, [])
  const titleKey = MAIN_ROUTES.find(item=>item.id===page)?.label || ({data:'Data & access',prioritize:'Priorities',compare:'Scenarios',assurance:'Service assurance'} as Record<string,string>)[page]
  useEffect(()=>{document.title=localizedPageTitle(titleKey)},[titleKey,language])
  useEffect(() => {
    if (!metadata || !['prioritize','compare','assurance'].includes(page)) return
    let active = true; setIndicatorError('')
    dataApi<{ items: PriorityRow[] }>('/priority', { weights }).then(result => { if (active) setPriority(result.items) }).catch(problem => { if (active) { setPriority([]); setIndicatorError(problem.message) } })
    return () => { active = false }
  }, [weights, revision, metadata, page])
  useEffect(() => {
    if (page !== 'settlements' || !selectedId) return
    let active = true; setLinkedProjects([]); setProjectError('')
    collectPages<PublicProject>((number, size) => dataApi(`/projects?settlement_id=${encodeURIComponent(selectedId)}&page=${number}&page_size=${size}`)).then(rows => { if (active) setLinkedProjects(rows) }).catch(problem => { if (active) setProjectError(problem.message) })
    return () => { active = false }
  }, [page, selectedId, revision])
  const data = useMemo(() => metadata ? planningDataset(settlements, metadata, priority) : null, [metadata, settlements, priority])
  const selected = settlements.find(row => row.id === selectedId), cluster = data?.clusters.find(row => row.id === selectedId)
  const wards = [...new Set(settlements.map(row => row.administrative_area).filter(Boolean))].sort() as string[]
  const villages = [...new Set(settlements.map(row=>row.village).filter(Boolean))].sort() as string[]
  const filtered = settlements.filter(row => `${row.source_id} ${row.name} ${row.administrative_area || ''}`.toLowerCase().includes(search.toLowerCase()) && (!ward || row.administrative_area === ward) && (!village || row.village===village))
  function navigate(next:Page,query?:string) { const url=new URL(location.href);url.pathname=PATHS[next];url.hash='';url.search=query??'';const record=url.searchParams.get('settlement');if(record&&settlements.some(row=>row.id===record))setSelectedId(record);history.pushState(null,'',url);setRoute({page:next,query:url.search});setMobile(false);window.scrollTo({top:0,behavior:'instant'}) }
  function select(id: string) { if (id !== selectedId) setDraft(null); setSelectedId(id); const url = new URL(location.href); url.searchParams.set('settlement', id); history.replaceState(null, '', url) }
  function changed() { setRevision(old => old + 1); dataApi<Stats>('/overview').then(setStats).catch(problem => setError(problem.message)) }
    const needsSelection = ['prioritize', 'compare', 'assurance'].includes(page)
  const icons={dashboard:LayoutDashboard,settlements:MapPinned,'report-issue':MessageSquarePlus,projects:FolderOpen}
  return <div className={`us-shell public-workspace workspace-focused product-shell ${mobile?'navigation-expanded':''}`}>
    <a className="us-skip" href="#public-main">{t('Skip to main content')}</a>
    <aside id="product-navigation" className={`us-sidebar ${mobile?'open':''}`}>
      {mobile && <button className="product-nav-close" aria-label={t('design.closeMenu')} onClick={()=>{setMobile(false);document.querySelector<HTMLButtonElement>('.us-mobile-nav')?.focus()}}><X size={18}/></button>}
      <button className="us-brand" aria-label={t('UrbanSaarthi')} onClick={()=>navigate('dashboard')}><img className="us-brand-mark" src="/urbansaarthi-mark.svg" width="45" height="58" alt=""/><span><strong>{t('UrbanSaarthi')}</strong><small>{t('shell.subtitle')}</small></span></button>
      <nav aria-label={t('shell.navigation')}>{MAIN_ROUTES.map(item=>{const Icon=icons[item.id];return <a key={item.id} href={item.path} title={t(item.label)} aria-current={activeSection(page)===item.id?'page':undefined} className={activeSection(page)===item.id?'active':''} onClick={event=>{if(event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;event.preventDefault();navigate(item.id)}}><Icon size={23} strokeWidth={1.5}/><span>{t(item.label)}</span></a>})}</nav>
      <div className="workspace-sidebar-end"><button title={t('Data & access')} aria-label={t('Data & access')} className={`workspace-data-link ${page==='data'?'active':''}`} onClick={()=>navigate('data')}><Database size={22} strokeWidth={1.5}/><span>{t('Data & access')}</span></button><small>{t('Mumbai · Maharashtra')}</small></div>
    </aside>
    {mobile&&<button className="us-nav-backdrop" aria-label={t('Close navigation')} onClick={()=>setMobile(false)}/>}
    <div className="us-workspace"><header className="us-topbar"><div className="us-header-context"><a className="product-mobile-brand" href="/dashboard" aria-label={t('UrbanSaarthi')} onClick={event=>{event.preventDefault();navigate('dashboard')}}><img src="/urbansaarthi-mark.svg" width="30" height="39" alt=""/></a><button className="us-icon-button us-mobile-nav" aria-label={t('Toggle navigation')} aria-expanded={mobile} aria-controls="product-navigation" onClick={()=>setMobile(!mobile)}>{mobile?<X strokeWidth={1.5}/>:<Menu strokeWidth={1.5}/>}</button><span className="workspace-current-page">{t(titleKey)}</span></div><div className="us-header-actions"><form className="product-global-search" role="search" onSubmit={event=>{event.preventDefault();setListPage(0);navigate('settlements')}}><Search size={21} strokeWidth={1.5}/><input type="search" aria-label={t('design.globalSearch')} placeholder={t('design.search')} value={search} onChange={event=>{setSearch(event.target.value);setListPage(0)}}/><button type="submit" aria-label={t('design.runSearch')}><span>↵</span></button></form><LanguageSwitcher/><button className="us-button product-connect" onClick={()=>navigate('data')}>{t('Data')}</button></div></header>
      {needsSelection&&settlements.length>0&&<div className="us-context-bar"><label>{t('Settlement')}<select aria-label={t('Selected settlement')} value={selectedId} onChange={event=>select(event.target.value)}>{settlements.map(row=><option key={row.id} value={row.id}>{row.name} · {row.source_id}</option>)}</select></label><button className="us-button" onClick={()=>navigate('settlements')}>{t('View on map')}</button></div>}
      <main id="public-main" className="us-content">
        {error&&<div className="us-alert" role="alert">{errorText(error)}<button className="us-button" onClick={load}>{t('Retry data connection')}</button></div>}
        {indicatorError&&needsSelection&&<div className="us-alert" role="alert">{errorText(indicatorError)}<button className="us-button" onClick={changed}>{t('Retry indicators')}</button></div>}
        {page==='dashboard'&&<ProductDashboard metadata={metadata} stats={stats} settlements={settlements} loading={loading} onPage={navigate}/>}
        {page==='report-issue'&&<IssueReport lookupId={new URLSearchParams(route.query).get('issue')||''}/>}
        {page==='projects'&&<ProjectsReports metadata={metadata} onPage={navigate}/>}
        {page==='data'&&<WorkspaceData metadata={metadata} officerKey={key} onKey={value=>{setKey(value);sessionStorage.setItem('urbansaarthi-officer-key',value)}} onImported={load} onDemo={onDemo}/>}
            {page === 'settlements' && <>
              <Heading number="02" title={t("nav.settlements")} description={settlements.length ? t("Select a settlement to review its service needs and linked projects.") : t("View the historical reference layer. Add your own settlement data separately.")} />
              <div className={`workspace-explorer ${settlements.length ? '' : 'workspace-reference-only'}`}><div className="workspace-map-column"><Suspense fallback={<p role="status">{t("Loading map…")}</p>}><PublicMap key={metadata?.snapshot.snapshot_sha256} settlements={settlements} selected={selectedId} onSelect={select} /></Suspense></div>{settlements.length > 0 && <div className="workspace-settlement-column">
                <Panel title={t("Find a settlement")}><div className="workspace-settlement-search"><input aria-label={t("Search settlements")} placeholder={t("Name, ID or ward")} value={search} onChange={event => { setSearch(event.target.value); setListPage(0) }} /><select aria-label={t("Settlement ward")} value={ward} onChange={event => { setWard(event.target.value); setListPage(0) }}><option value="">{t("All wards")}</option>{wards.map(value => <option key={value}>{value}</option>)}</select><select aria-label={t("explore.villageFilter")} value={village} onChange={event=>{setVillage(event.target.value);setListPage(0)}}><option value="">{t("explore.allVillages")}</option>{villages.map(value=><option key={value} value={value}>{value}</option>)}</select></div><div className="workspace-settlement-list">{filtered.slice(listPage * 10, (listPage + 1) * 10).map(row => <button key={row.id} className={row.id === selectedId ? 'selected' : ''} onClick={() => select(row.id)}><b>{row.source_name===null?t("explore.nameMissing"):row.name}</b><small>{row.source_id} · {row.administrative_area || t("Ward not supplied")}</small></button>)}{!filtered.length && <p>{t("No settlements match.")}</p>}</div><div className="workspace-pagination"><span>{formatNumber(filtered.length, 0)} {t("records")}</span><button aria-label={t("Previous settlements")} disabled={!listPage} onClick={() => setListPage(listPage - 1)}>‹</button><button aria-label={t("Next settlements")} disabled={(listPage + 1) * 10 >= filtered.length} onClick={() => setListPage(listPage + 1)}>›</button></div></Panel>
                {selected && <Panel title={selected.source_name===null?t("explore.nameMissing"):selected.name}>
                  {selected.record_type==='published_cluster_register'&&<p className="product-note">{t('explore.noJoin')}</p>}
                  <dl className="us-facts"><div><dt>{t('explore.sourceId')}</dt><dd>{selected.source_id}</dd></div><div><dt>{t('Ward')}</dt><dd>{selected.administrative_area||t('Not supplied')}</dd></div><div><dt>{t('explore.village')}</dt><dd>{selected.village||t('Not supplied')}</dd></div>{selected.taluka&&<div><dt>{t('explore.taluka')}</dt><dd>{selected.taluka}</dd></div>}{selected.shape_area_sq_m!=null&&<div><dt>{t('explore.printedArea')}</dt><dd>{formatNumber(selected.shape_area_sq_m,2)} m²</dd></div>}<div><dt>{t('Source date')}</dt><dd>{formatDate(selected.source_date)}</dd></div></dl>
                  <details className="workspace-source-detail"><summary>{t('Source details')}</summary>{sourceUrl(selected.source)?<a href={sourceUrl(selected.source)} target="_blank" rel="noreferrer">{t('Source')}</a>:<span>{selected.source}</span>}{selected.source_id_unique===false&&<p>{t('This source identifier is duplicated; review before joining.')}</p>}{selected.name_overflow_in_source&&<p>{t('explore.nameReview')}</p>}</details>
                </Panel>}

              </div>}</div>
              {selected && <Panel title={t("Projects linked to {p0}", { p0: selected.name })}>{projectError ? <p role="alert">{errorText(projectError)}</p> : linkedProjects.length ? <div className="us-table-wrap"><table><thead><tr><th>{t("Project")}</th><th>{t("Status")}</th><th>{t("Source date")}</th></tr></thead><tbody>{linkedProjects.map(project => <tr key={project.id}><td>{project.scheme_name}</td><td>{statusText(project.project_status)}</td><td>{formatDate(project.source_date)}</td></tr>)}</tbody></table></div> : <p className="us-small">{t("No projects are linked to this settlement.")}</p>}</Panel>}
            </>}
        {needsSelection&&loading&&!metadata?<p role="status">{t('Loading workspace…')}</p>:<>
            {needsSelection && !selected && <Panel title={t("Add a settlement to begin")}><p>{t("Import your settlement records and boundaries from Data & access.")}</p><button className="us-button primary" onClick={() => navigate('data')}>{t("Import data")}</button></Panel>}
            {page === 'prioritize' && data && cluster && <WorkspacePriorities data={data} selected={cluster} weights={weights} onWeights={setWeights} onSelect={select} onCompare={() => navigate('compare')} />}
            {page === 'compare' && data && cluster && <Compare key={selectedId} data={data} selected={cluster} mode="server" apiPrefix="/data" onPlan={value => { setDraft(value); navigate('assurance') }} />}
            {page === 'assurance' && selected && health && <Suspense fallback={<p role="status">{t("Loading service assurance…")}</p>}><PublicAssurance key={selectedId} selected={selected} officerKey={key} health={health} draft={draft} onChanged={changed} onClearDraft={() => setDraft(null)} onAccess={() => navigate('data')} /></Suspense>}
        </>}
      </main><footer className="us-footer"><span>{t('UrbanSaarthi')}</span><span>{t('shell.footer')}</span></footer>
    </div>
  </div>
}
