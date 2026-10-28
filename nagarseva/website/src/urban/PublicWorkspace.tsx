import { LanguageSwitcher, localizedPageTitle, useLanguage } from '../i18n/LanguageProvider'
import { formatDecimal, t, errorText, formatDate, formatNumber, statusText } from '../i18n/locale'
import { Activity, Building2, Database, LayoutDashboard, MapPinned, Menu, ShieldCheck, SlidersHorizontal, X } from 'lucide-react'
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { DEFAULT_WEIGHTS, INDICATORS, KEYS, prioritize } from './engine'
import { dataApi, planningDataset } from './publicClient'
import type { Health, Metadata, PriorityRow, PublicProject, PublicSettlement, Stats } from './publicClient'
import { Compare, Heading, Panel, Tag } from './PlanningPages'
import { collectPages } from './pagination'
import WorkspaceData from './WorkspaceData'
import WorkspacePriorities from './WorkspacePriorities'

const PublicMap = lazy(() => import('./PublicMap'))
const PublicAssurance = lazy(() => import('./PublicAssurance'))
const PAGES = [{ id: 'overview', label: 'Overview', icon: LayoutDashboard }, { id: 'explore', label: 'Settlement map', icon: MapPinned }, { id: 'prioritize', label: 'Priorities', icon: SlidersHorizontal }, { id: 'compare', label: 'Scenarios', icon: Activity }, { id: 'assurance', label: 'Service assurance', icon: ShieldCheck }] as const
type Page = typeof PAGES[number]['id'] | 'data'
function route(): Page { const id = location.hash.slice(1); return id === 'data' || PAGES.some(p => p.id === id) ? id as Page : 'overview' }

export default function PublicWorkspace({ onDemo }: { onDemo: () => void }) {
  const { language } = useLanguage()
  const [page, setPage] = useState<Page>(route), [mobile, setMobile] = useState(false)
  const [metadata, setMetadata] = useState<Metadata | null>(null), [stats, setStats] = useState<Stats | null>(null), [health, setHealth] = useState<Health | null>(null), [settlements, setSettlements] = useState<PublicSettlement[]>([])
  const [priority, setPriority] = useState<PriorityRow[]>([]), [selectedId, setSelectedId] = useState(() => new URL(location.href).searchParams.get('settlement') || ''), [search, setSearch] = useState(''), [ward, setWard] = useState(''), [listPage, setListPage] = useState(0)
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS), [error, setError] = useState(''), [loading, setLoading] = useState(true), [indicatorError, setIndicatorError] = useState(''), [revision, setRevision] = useState(0)
  const [key, setKey] = useState(() => sessionStorage.getItem('urbansaarthi-officer-key') || ''), [draft, setDraft] = useState<Record<string, unknown> | null>(null), [linkedProjects, setLinkedProjects] = useState<PublicProject[]>([]), [projectError, setProjectError] = useState('')
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [m, s, h, records] = await Promise.all([dataApi<Metadata>('/metadata'), dataApi<Stats>('/overview'), dataApi<Health>('/health'), collectPages<PublicSettlement>((number, size) => dataApi(`/settlements?page=${number}&page_size=${size}`))])
      setMetadata(m); setStats(s); setHealth(h); setSettlements(records); setPriority([]); setDraft(null); setSearch(''); setWard(''); setListPage(0)
      setSelectedId(old => records.some(r => r.id === old) ? old : records.find(r => r.geometry)?.id || records[0]?.id || '')
      setRevision(old => old + 1)
    } catch (problem) { setError((problem as Error).message) } finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])
  useEffect(() => { const listener = () => { setPage(route()); setMobile(false) }; addEventListener('hashchange', listener); return () => removeEventListener('hashchange', listener) }, [])
  useEffect(() => { document.title = localizedPageTitle(page === 'data' ? 'Data & access' : PAGES.find(p => p.id === page)?.label || '') }, [page, language])
  useEffect(() => {
    if (!metadata) return
    let active = true; setIndicatorError('')
    dataApi<{ items: PriorityRow[] }>('/priority', { weights }).then(result => { if (active) setPriority(result.items) }).catch(problem => { if (active) { setPriority([]); setIndicatorError(problem.message) } })
    return () => { active = false }
  }, [weights, revision, metadata])
  useEffect(() => {
    if (page !== 'explore' || !selectedId) return
    let active = true; setLinkedProjects([]); setProjectError('')
    collectPages<PublicProject>((number, size) => dataApi(`/projects?settlement_id=${encodeURIComponent(selectedId)}&page=${number}&page_size=${size}`)).then(rows => { if (active) setLinkedProjects(rows) }).catch(problem => { if (active) setProjectError(problem.message) })
    return () => { active = false }
  }, [page, selectedId, revision])
  const data = useMemo(() => metadata ? planningDataset(settlements, metadata, priority) : null, [metadata, settlements, priority])
  const ranking = useMemo(() => data ? prioritize(data.clusters, weights) : null, [data, weights])
  const selected = settlements.find(row => row.id === selectedId), cluster = data?.clusters.find(row => row.id === selectedId), current = ranking?.items.find(row => row.id === selectedId)
  const wards = [...new Set(settlements.map(row => row.administrative_area).filter(Boolean))].sort() as string[]
  const filtered = settlements.filter(row => `${row.source_id} ${row.name} ${row.administrative_area || ''}`.toLowerCase().includes(search.toLowerCase()) && (!ward || row.administrative_area === ward))
  function navigate(next: Page) { setPage(next); setMobile(false); location.hash = next; window.scrollTo({ top: 0, behavior: 'instant' }) }
  function select(id: string) { if (id !== selectedId) setDraft(null); setSelectedId(id); const url = new URL(location.href); url.searchParams.set('settlement', id); history.replaceState(null, '', url) }
  function changed() { setRevision(old => old + 1); dataApi<Stats>('/overview').then(setStats).catch(problem => setError(problem.message)) }
  const ready = ranking?.items.filter(row => row.rankable).length || 0
  const needsSelection = ['prioritize', 'compare', 'assurance'].includes(page)
  return <div className="us-shell public-workspace workspace-focused">
    <a className="us-skip" href="#public-main">{t("Skip to main content")}</a>
    <aside className={`us-sidebar ${mobile ? 'open' : ''}`}>
      <button className="us-brand" onClick={() => navigate('overview')}><span className="us-brand-mark"><Building2 size={23} /></span><span><strong>{t("UrbanSaarthi")}</strong><small>{t("HOUSING & BASIC SERVICES")}</small></span></button>
      <nav aria-label={t("Planning workflow")}>{PAGES.map(item => <button key={item.id} aria-label={t(item.label)} className={page === item.id ? 'active' : ''} aria-current={page === item.id ? 'page' : undefined} onClick={() => navigate(item.id)}><item.icon size={19} /><span>{t(item.label)}</span></button>)}</nav>
      <div className="workspace-sidebar-end"><button className={`workspace-data-link ${page === 'data' ? 'active' : ''}`} onClick={() => navigate('data')}><Database size={18} /> {t("Data & access")}</button><small>{t("Mumbai · Maharashtra")}</small></div>
    </aside>
    {mobile && <button className="us-nav-backdrop" aria-label={t("Close navigation")} onClick={() => setMobile(false)} />}
    <div className="us-workspace">
      <header className="us-topbar"><div className="us-header-context"><button className="us-icon-button us-mobile-nav" aria-label={t("Toggle navigation")} onClick={() => setMobile(!mobile)}>{mobile ? <X /> : <Menu />}</button><span className="workspace-current-page">{page === 'data' ? t("Data & access") : t(PAGES.find(item => item.id === page)?.label || '')}</span></div><div className="us-header-actions"><LanguageSwitcher /><span className="workspace-dataset-name">{metadata?.snapshot.snapshot_sha256 ? metadata.snapshot.title : t("No dataset loaded")}</span><button className="us-button" onClick={() => navigate('data')}><Database size={15} /> {t("Data")}</button></div></header>
      {needsSelection && settlements.length > 0 && <div className="us-context-bar"><label>{t("Settlement")}<select aria-label={t("Selected settlement")} value={selectedId} onChange={event => select(event.target.value)}>{settlements.map(row => <option key={row.id} value={row.id}>{row.name} · {row.source_id}</option>)}</select></label><button className="us-button" onClick={() => navigate('explore')}>{t("View on map")}</button></div>}
      <main id="public-main" className="us-content">
        {loading && !metadata && page !== 'explore' ? <div className="us-empty" role="status">{t("Loading workspace…")}</div> : <>
          {error && <div className="us-alert" role="alert">{errorText(error)}<button className="us-button" onClick={load}>{t("Retry data connection")}</button></div>}
          {indicatorError && page !== 'data' && <div className="us-alert" role="alert">{t("Indicators could not load:")} {errorText(indicatorError)}<button className="us-button" onClick={changed}>{t("Retry indicators")}</button></div>}
          {page === 'data' ? <WorkspaceData metadata={metadata} officerKey={key} onKey={value => { setKey(value); sessionStorage.setItem('urbansaarthi-officer-key', value) }} onImported={load} onDemo={onDemo} /> : !metadata || !stats ? page === 'explore' ? <><Heading number="02" title={t("Settlement map")} description={t("View the historical reference layer. Add your own settlement data separately.")} /><Suspense fallback={<p role="status">{t("Loading map…")}</p>}><PublicMap settlements={[]} onSelect={select} /></Suspense></> : <Panel title={t("Connect your workspace")}><p>{t("Start the API or open Data to load your dataset.")}</p><button className="us-button primary" onClick={() => navigate('data')}>{t("Open Data & access")}</button></Panel> : <>
            {page === 'overview' && <>
              <Heading number="01" title={t("Settlement planning")} description={t("Review service needs, compare interventions and track delivery.")}><button className="us-button primary" onClick={() => navigate(settlements.length ? 'explore' : 'data')}>{settlements.length ? t("Open settlement map") : t("Import your data")}</button></Heading>
              <div className="us-metrics">{[[settlements.length, t("Settlement records")], [ready, t("Ready to rank")], [settlements.length - ready, t("Needs assessment")], [stats.documented_deficits, t("Recorded deficit indices")], [stats.projects, t("Redevelopment projects")], [stats.awaiting_verification, t("Awaiting verification")]].map(([value, label]) => <div className="us-metric" key={String(label)}><span>{t(String(label))}</span><strong>{formatNumber(Number(value))}</strong></div>)}</div>
              <div className="workspace-overview-grid"><Panel title={t("Next steps")}><div className="workspace-next-actions"><button onClick={() => navigate(stats.settlements_with_geometry ? 'explore' : 'data')}><MapPinned size={20} /><span><b>{stats.settlements_with_geometry ? t("Explore settlement boundaries") : t("Add settlement boundaries")}</b><small>{stats.settlements_with_geometry ? t(stats.settlements_with_geometry === 1 ? "{count} settlement mapped" : "{count} settlements mapped", { count: formatNumber(stats.settlements_with_geometry, 0) }) : t("Import GeoJSON to connect records to the map")}</small></span><span>→</span></button><button onClick={() => navigate('prioritize')}><SlidersHorizontal size={20} /><span><b>{t("Review priorities")}</b><small>{ready ? t(ready === 1 ? "{count} settlement ready for ranking" : "{count} settlements ready for ranking", { count: formatNumber(ready, 0) }) : t("Add reviewed service observations to calculate scores")}</small></span><span>→</span></button><button onClick={() => navigate('assurance')}><ShieldCheck size={20} /><span><b>{t("Track service delivery")}</b><small>{stats.overdue_interventions ? t("{p0} interventions overdue", { p0: stats.overdue_interventions }) : t("Plan work, inspect evidence and record verification")}</small></span><span>→</span></button></div></Panel><Panel title={t("Workspace coverage")}><dl className="us-facts"><div><dt>{t("Settlement boundaries")}</dt><dd>{formatNumber(stats.settlements_with_geometry, 0)} / {formatNumber(settlements.length, 0)}</dd></div><div><dt>{t("Reviewed indicator coverage")}</dt><dd>{formatNumber(ready, 0)} / {formatNumber(settlements.length, 0)}</dd></div><div><dt>{t("Mapped context objects")}</dt><dd>{formatNumber(metadata.snapshot.mapped_objects_count)}</dd></div><div><dt>{t("Source date")}</dt><dd>{formatDate(metadata.snapshot.settlement_reference)}</dd></div></dl><p className="us-small">{t("Missing observations require assessment. They are not counted as zero deficit.")}</p><button className="us-button" onClick={() => navigate('data')}>{t("Manage data")}</button></Panel></div>
            </>}
            {page === 'explore' && <>
              <Heading number="02" title={t("Settlement map")} description={t("Select a settlement to review its service needs and linked projects.")} />
              <div className="workspace-explorer"><div className="workspace-map-column"><Suspense fallback={<p role="status">{t("Loading map…")}</p>}><PublicMap key={metadata.snapshot.snapshot_sha256} settlements={settlements} selected={selectedId} onSelect={select} /></Suspense></div><div className="workspace-settlement-column">
                <Panel title={t("Find a settlement")}><div className="workspace-settlement-search"><input aria-label={t("Search settlements")} placeholder={t("Name, ID or ward")} value={search} onChange={event => { setSearch(event.target.value); setListPage(0) }} /><select aria-label={t("Settlement ward")} value={ward} onChange={event => { setWard(event.target.value); setListPage(0) }}><option value="">{t("All wards")}</option>{wards.map(value => <option key={value}>{value}</option>)}</select></div><div className="workspace-settlement-list">{filtered.slice(listPage * 10, (listPage + 1) * 10).map(row => <button key={row.id} className={row.id === selectedId ? 'selected' : ''} onClick={() => select(row.id)}><b>{row.name}</b><small>{row.source_id} · {row.administrative_area || t("Ward not supplied")}</small></button>)}{!filtered.length && <p>{t("No settlements match.")}</p>}</div><div className="workspace-pagination"><span>{formatNumber(filtered.length, 0)} {t("records")}</span><button aria-label={t("Previous settlements")} disabled={!listPage} onClick={() => setListPage(listPage - 1)}>‹</button><button aria-label={t("Next settlements")} disabled={(listPage + 1) * 10 >= filtered.length} onClick={() => setListPage(listPage + 1)}>›</button></div></Panel>
                {selected && <Panel title={selected.name}><div className="workspace-score-summary"><Tag tone={current?.rankable ? 'green' : 'amber'}>{current?.score !== null && current?.score !== undefined ? `${formatDecimal(current.score, 1)} / 100` : t("Needs assessment")}</Tag><span>{selected.source_id}</span></div><dl className="us-facts"><div><dt>{t("Ward")}</dt><dd>{selected.administrative_area || t("Not supplied")}</dd></div><div><dt>{t("Households")}</dt><dd>{(selected.households == null ? undefined : formatNumber(selected.households)) ?? t("Not supplied")}</dd></div><div><dt>{t("Boundary")}</dt><dd>{selected.geometry ? t("Available") : t("Not supplied")}</dd></div></dl><div className="workspace-indicator-grid">{KEYS.map(indicator => <div key={indicator}><span>{t(INDICATORS[indicator].label)}</span><b>{cluster?.indicators[indicator] == null ? '—' : formatNumber(cluster.indicators[indicator])}</b></div>)}</div><div className="us-button-row"><button className="us-button" onClick={() => navigate('prioritize')}>{t("Priority breakdown")}</button><button className="us-button primary" onClick={() => navigate('compare')}>{t("Compare scenarios")}</button></div><details className="workspace-source-detail"><summary>{t("Source details")}</summary><p>{selected.source}</p><p>{formatDate(selected.source_date)}</p>{selected.source_id_unique === false && <p>{t("This source identifier is duplicated; review before joining.")}</p>}</details></Panel>}
              </div></div>
              {selected && <Panel title={t("Projects linked to {p0}", { p0: selected.name })}>{projectError ? <p role="alert">{errorText(projectError)}</p> : linkedProjects.length ? <div className="us-table-wrap"><table><thead><tr><th>{t("Project")}</th><th>{t("Status")}</th><th>{t("Source date")}</th></tr></thead><tbody>{linkedProjects.map(project => <tr key={project.id}><td>{project.scheme_name}</td><td>{statusText(project.project_status)}</td><td>{formatDate(project.source_date)}</td></tr>)}</tbody></table></div> : <p className="us-small">{t("No projects are linked to this settlement.")}</p>}</Panel>}
            </>}
            {needsSelection && !selected && <Panel title={t("Add a settlement to begin")}><p>{t("Import your settlement records and boundaries from Data & access.")}</p><button className="us-button primary" onClick={() => navigate('data')}>{t("Import data")}</button></Panel>}
            {page === 'prioritize' && data && cluster && <WorkspacePriorities data={data} selected={cluster} weights={weights} onWeights={setWeights} onSelect={select} onCompare={() => navigate('compare')} />}
            {page === 'compare' && data && cluster && <Compare key={selectedId} data={data} selected={cluster} mode="server" apiPrefix="/data" onPlan={value => { setDraft(value); navigate('assurance') }} />}
            {page === 'assurance' && selected && health && <Suspense fallback={<p role="status">{t("Loading service assurance…")}</p>}><PublicAssurance key={selectedId} selected={selected} officerKey={key} health={health} draft={draft} onChanged={changed} onClearDraft={() => setDraft(null)} onAccess={() => navigate('data')} /></Suspense>}
          </>}
        </>}
      </main><footer className="us-footer"><span>{t("UrbanSaarthi")}</span><span>{t("Completion requires a separate verification record.")}</span></footer>
    </div>
  </div>
}
