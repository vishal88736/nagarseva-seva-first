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
  useEffect(() => { document.title = `UrbanSaarthi · ${page === 'data' ? 'Data & access' : PAGES.find(p => p.id === page)?.label}` }, [page])
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
    <a className="us-skip" href="#public-main">Skip to main content</a>
    <aside className={`us-sidebar ${mobile ? 'open' : ''}`}>
      <button className="us-brand" onClick={() => navigate('overview')}><span className="us-brand-mark"><Building2 size={23} /></span><span><strong>UrbanSaarthi</strong><small>HOUSING & BASIC SERVICES</small></span></button>
      <nav aria-label="Planning workflow">{PAGES.map(item => <button key={item.id} aria-label={item.label} className={page === item.id ? 'active' : ''} aria-current={page === item.id ? 'page' : undefined} onClick={() => navigate(item.id)}><item.icon size={19} /><span>{item.label}</span></button>)}</nav>
      <div className="workspace-sidebar-end"><button className={`workspace-data-link ${page === 'data' ? 'active' : ''}`} onClick={() => navigate('data')}><Database size={18} /> Data & access</button><small>Mumbai · Maharashtra</small></div>
    </aside>
    {mobile && <button className="us-nav-backdrop" aria-label="Close navigation" onClick={() => setMobile(false)} />}
    <div className="us-workspace">
      <header className="us-topbar"><div className="us-header-context"><button className="us-icon-button us-mobile-nav" aria-label="Toggle navigation" onClick={() => setMobile(!mobile)}>{mobile ? <X /> : <Menu />}</button><span className="workspace-current-page">{page === 'data' ? 'Data & access' : PAGES.find(item => item.id === page)?.label}</span></div><div className="us-header-actions"><span className="workspace-dataset-name">{metadata?.snapshot.title || 'Connect a dataset'}</span><button className="us-button" onClick={() => navigate('data')}><Database size={15} /> Data</button></div></header>
      {needsSelection && settlements.length > 0 && <div className="us-context-bar"><label>Settlement<select aria-label="Selected settlement" value={selectedId} onChange={event => select(event.target.value)}>{settlements.map(row => <option key={row.id} value={row.id}>{row.name} · {row.source_id}</option>)}</select></label><button className="us-button" onClick={() => navigate('explore')}>View on map</button></div>}
      <main id="public-main" className="us-content">
        {loading && !metadata ? <div className="us-empty" role="status">Loading workspace…</div> : <>
          {error && <div className="us-alert" role="alert">{error}<button className="us-button" onClick={load}>Retry data connection</button></div>}
          {indicatorError && page !== 'data' && <div className="us-alert" role="alert">Indicators could not load: {indicatorError}<button className="us-button" onClick={changed}>Retry indicators</button></div>}
          {page === 'data' ? <WorkspaceData metadata={metadata} officerKey={key} onKey={value => { setKey(value); sessionStorage.setItem('urbansaarthi-officer-key', value) }} onImported={load} onDemo={onDemo} /> : !metadata || !stats ? <Panel title="Connect your workspace"><p>Start the API or open Data to load your dataset.</p><button className="us-button primary" onClick={() => navigate('data')}>Open Data & access</button></Panel> : <>
            {page === 'overview' && <>
              <Heading number="01" title="Settlement planning" description="Review service needs, compare interventions and track delivery."><button className="us-button primary" onClick={() => navigate(settlements.length ? 'explore' : 'data')}>{settlements.length ? 'Open settlement map' : 'Import your data'}</button></Heading>
              <div className="us-metrics">{[[settlements.length, 'Settlement records'], [ready, 'Ready to rank'], [settlements.length - ready, 'Needs assessment'], [stats.documented_deficits, 'Recorded deficit indices'], [stats.projects, 'Redevelopment projects'], [stats.awaiting_verification, 'Awaiting verification']].map(([value, label]) => <div className="us-metric" key={String(label)}><span>{label}</span><strong>{Number(value).toLocaleString('en-IN')}</strong></div>)}</div>
              <div className="workspace-overview-grid"><Panel title="Next steps"><div className="workspace-next-actions"><button onClick={() => navigate(stats.settlements_with_geometry ? 'explore' : 'data')}><MapPinned size={20} /><span><b>{stats.settlements_with_geometry ? 'Explore settlement boundaries' : 'Add settlement boundaries'}</b><small>{stats.settlements_with_geometry ? `${stats.settlements_with_geometry} settlements mapped` : 'Import GeoJSON to connect records to the map'}</small></span><span>→</span></button><button onClick={() => navigate('prioritize')}><SlidersHorizontal size={20} /><span><b>Review priorities</b><small>{ready ? `${ready} settlements have enough reviewed inputs` : 'Add reviewed service observations to calculate scores'}</small></span><span>→</span></button><button onClick={() => navigate('assurance')}><ShieldCheck size={20} /><span><b>Track service delivery</b><small>{stats.overdue_interventions ? `${stats.overdue_interventions} interventions overdue` : 'Plan work, inspect evidence and record verification'}</small></span><span>→</span></button></div></Panel><Panel title="Workspace coverage"><dl className="us-facts"><div><dt>Settlement boundaries</dt><dd>{stats.settlements_with_geometry} / {settlements.length}</dd></div><div><dt>Reviewed indicator coverage</dt><dd>{ready} / {settlements.length}</dd></div><div><dt>Mapped context objects</dt><dd>{metadata.snapshot.mapped_objects_count.toLocaleString('en-IN')}</dd></div><div><dt>Source date</dt><dd>{metadata.snapshot.settlement_reference || 'Not supplied'}</dd></div></dl><p className="us-small">Missing observations require assessment. They are not counted as zero deficit.</p><button className="us-button" onClick={() => navigate('data')}>Manage data</button></Panel></div>
            </>}
            {page === 'explore' && <>
              <Heading number="02" title="Settlement map" description="Select a settlement to review its service needs and linked projects." />
              <div className="workspace-explorer"><div className="workspace-map-column"><Suspense fallback={<p role="status">Loading map…</p>}><PublicMap key={metadata.snapshot.snapshot_sha256} settlements={settlements} selected={selectedId} onSelect={select} /></Suspense></div><div className="workspace-settlement-column">
                <Panel title="Find a settlement"><div className="workspace-settlement-search"><input aria-label="Search settlements" placeholder="Name, ID or ward" value={search} onChange={event => { setSearch(event.target.value); setListPage(0) }} /><select aria-label="Settlement ward" value={ward} onChange={event => { setWard(event.target.value); setListPage(0) }}><option value="">All wards</option>{wards.map(value => <option key={value}>{value}</option>)}</select></div><div className="workspace-settlement-list">{filtered.slice(listPage * 10, (listPage + 1) * 10).map(row => <button key={row.id} className={row.id === selectedId ? 'selected' : ''} onClick={() => select(row.id)}><b>{row.name}</b><small>{row.source_id} · {row.administrative_area || 'Ward not supplied'}</small></button>)}{!filtered.length && <p>No settlements match.</p>}</div><div className="workspace-pagination"><span>{filtered.length} records</span><button aria-label="Previous settlements" disabled={!listPage} onClick={() => setListPage(listPage - 1)}>‹</button><button aria-label="Next settlements" disabled={(listPage + 1) * 10 >= filtered.length} onClick={() => setListPage(listPage + 1)}>›</button></div></Panel>
                {selected && <Panel title={selected.name}><div className="workspace-score-summary"><Tag tone={current?.rankable ? 'green' : 'amber'}>{current?.score !== null && current?.score !== undefined ? `${current.score.toFixed(1)} / 100` : 'Needs assessment'}</Tag><span>{selected.source_id}</span></div><dl className="us-facts"><div><dt>Ward</dt><dd>{selected.administrative_area || 'Not supplied'}</dd></div><div><dt>Households</dt><dd>{selected.households?.toLocaleString('en-IN') ?? 'Not supplied'}</dd></div><div><dt>Boundary</dt><dd>{selected.geometry ? 'Available' : 'Not supplied'}</dd></div></dl><div className="workspace-indicator-grid">{KEYS.map(indicator => <div key={indicator}><span>{INDICATORS[indicator].label}</span><b>{cluster?.indicators[indicator] ?? '—'}</b></div>)}</div><div className="us-button-row"><button className="us-button" onClick={() => navigate('prioritize')}>Priority breakdown</button><button className="us-button primary" onClick={() => navigate('compare')}>Compare scenarios</button></div><details className="workspace-source-detail"><summary>Source details</summary><p>{selected.source}</p><p>{selected.source_date || 'Date not supplied'}</p>{selected.source_id_unique === false && <p>This source identifier is duplicated; review before joining.</p>}</details></Panel>}
              </div></div>
              {selected && <Panel title={`Projects linked to ${selected.name}`}>{projectError ? <p role="alert">{projectError}</p> : linkedProjects.length ? <div className="us-table-wrap"><table><thead><tr><th>Project</th><th>Status</th><th>Source date</th></tr></thead><tbody>{linkedProjects.map(project => <tr key={project.id}><td>{project.scheme_name}</td><td>{project.project_status.replaceAll('_', ' ')}</td><td>{project.source_date || 'Not supplied'}</td></tr>)}</tbody></table></div> : <p className="us-small">No projects are linked to this settlement.</p>}</Panel>}
            </>}
            {needsSelection && !selected && <Panel title="Add a settlement to begin"><p>Import your settlement records and boundaries from Data & access.</p><button className="us-button primary" onClick={() => navigate('data')}>Import data</button></Panel>}
            {page === 'prioritize' && data && cluster && <WorkspacePriorities data={data} selected={cluster} weights={weights} onWeights={setWeights} onSelect={select} onCompare={() => navigate('compare')} />}
            {page === 'compare' && data && cluster && <Compare key={selectedId} data={data} selected={cluster} mode="server" apiPrefix="/data" onPlan={value => { setDraft(value); navigate('assurance') }} />}
            {page === 'assurance' && selected && health && <Suspense fallback={<p role="status">Loading service assurance…</p>}><PublicAssurance key={selectedId} selected={selected} officerKey={key} health={health} draft={draft} onChanged={changed} onClearDraft={() => setDraft(null)} onAccess={() => navigate('data')} /></Suspense>}
          </>}
        </>}
      </main><footer className="us-footer"><span>UrbanSaarthi</span><span>Completion requires a separate verification record.</span></footer>
    </div>
  </div>
}
