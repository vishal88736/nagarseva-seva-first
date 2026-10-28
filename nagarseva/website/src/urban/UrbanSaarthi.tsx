import { LanguageSwitcher, localizedPageTitle, useLanguage } from '../i18n/LanguageProvider'
import { t, errorText } from '../i18n/locale'
import { Activity, ArrowDownToLine, ArrowUpRight, BookOpen, Building2, ChevronDown, Info, LayoutDashboard, LockKeyhole, MapPinned, Menu, ShieldCheck, SlidersHorizontal, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ScenarioResult } from './engine'
import { DEFAULT_WEIGHTS, DEMO_HIGH_PRIORITY_THRESHOLD, prioritize } from './engine'
import { api, downloadJson, useWorkspace } from './client'
import { Compare, Explore, Overview, Prioritize } from './PlanningPages'
import { AssurancePage } from './AssurancePage'

const PAGES = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'explore', label: 'Explore Settlements', icon: MapPinned },
  { id: 'prioritize', label: 'Prioritize Needs', icon: SlidersHorizontal },
  { id: 'compare', label: 'Compare Scenarios', icon: Activity },
  { id: 'assurance', label: 'Service Assurance', icon: ShieldCheck },
] as const
type Page = typeof PAGES[number]['id']
function route(): Page { const id = location.hash.slice(1).split('/')[0]; return PAGES.some(page => page.id === id) ? id as Page : 'overview' }

export default function UrbanSaarthi() {
  const { language } = useLanguage()
  const workspace = useWorkspace(), { data, state, mode } = workspace
  const [page, setPage] = useState<Page>(route), [selectedId, setSelectedId] = useState('US-A'), [weights, setWeights] = useState(DEFAULT_WEIGHTS)
  const [menu, setMenu] = useState(false), [keyDraft, setKeyDraft] = useState(workspace.officerKey)
  const [draft, setDraft] = useState<Record<string, unknown> | null>(null), [scenarios, setScenarios] = useState<ScenarioResult | null>(null)
  const [calculation, setCalculation] = useState('Browser calculation')
  const selected = data.clusters.find(cluster => cluster.id === selectedId) || data.clusters[0]
  const report = useMemo(() => prioritize(data.clusters, weights), [data.clusters, weights])
  const reportChanged = useCallback((result: ScenarioResult | null) => setScenarios(result), [])
  useEffect(() => { const changed = () => setPage(route()); addEventListener('hashchange', changed); return () => removeEventListener('hashchange', changed) }, [])
  useEffect(() => { document.title = localizedPageTitle(PAGES.find(item => item.id === page)?.label || '') }, [page, language])
  useEffect(() => {
    if (mode !== 'server') { setCalculation('Browser calculation'); return }
    let active = true
    setCalculation('Checking Python calculation…')
    const timer = setTimeout(() => { api<ReturnType<typeof prioritize>>('/priority', { weights }).then(result => {
      if (!active) return
      const same = report.items.every(row => { const other = result.items.find(item => item.id === row.id); return other && (other.score === null && row.score === null || other.score !== null && row.score !== null && Math.abs(other.score - row.score) < .00001) && Math.abs(other.lower - row.lower) < .00001 && Math.abs(other.upper - row.upper) < .00001 && other.rank === row.rank })
      setCalculation(same ? 'Python calculation checked' : 'Calculation mismatch · review needed')
      if (!same) workspace.setError('Python and browser scoring disagree. Do not use this ranking until the discrepancy is reviewed.')
    }).catch(problem => { if (active) { setCalculation('Python check unavailable'); workspace.setError(`Priority check failed: ${(problem as Error).message}`) } }) }, 250)
    return () => { active = false; clearTimeout(timer) }
  }, [mode, report, weights, workspace.setError])
  function open(value: string) { const next = PAGES.some(item => item.id === value) ? value as Page : 'overview'; setPage(next); setMenu(false); location.hash = next; scrollTo({ top: 0, behavior: 'smooth' }) }
  function select(id: string) { setSelectedId(id); setScenarios(null); setDraft(null) }
  function exportBrief() {
    downloadJson(`urbansaarthi-${selected.id}-brief.json`, { project: 'UrbanSaarthi', generated_at: new Date().toISOString(), mode, scope: 'Demonstration; not a government decision or field validation', data_metadata: data.metadata,
      selected_cluster: selected, priority_report: report, high_priority_rule: { threshold: DEMO_HIGH_PRIORITY_THRESHOLD, eligible: 'rankable clusters only', basis: 'illustrative design assumption; not official policy' }, python_priority_check: calculation, scenario_comparison: scenarios?.cluster_id === selected.id ? scenarios : null,
      works: state.works.filter(work => work.cluster_id === selected.id), evidence: state.evidence.filter(item => item.cluster_id === selected.id).map(({ content_base64: _, ...metadata }) => metadata),
      reported_issues: state.complaints.filter(issue => issue.cluster_id === selected.id), next_steps: ['Obtain permitted boundaries and current service observations.', 'Validate weights with the responsible government body and residents.', 'Review costs, engineering and livelihood implications.', 'Configure authenticated roles and independent field inspection before a real pilot.'] })
  }
  const common = { data, selected, weights, onSelect: select }
  return <div className="us-shell">
    <a className="us-skip" href="#us-main">{t("Skip to main content")}</a>
    <aside className={`us-sidebar ${menu ? 'open' : ''}`}>
      <button className="us-brand" onClick={() => open('overview')} aria-label={t("UrbanSaarthi home")}><span className="us-brand-mark"><Building2 size={23} /></span><span><strong>{t("UrbanSaarthi")}<span>●</span></strong><small>{t("PLANNING WITH PURPOSE")}</small></span></button>
      <div className="us-workspace-label">{t("URBAN DEVELOPMENT")} <span>01</span></div>
      <nav aria-label={t("Planning workflow")}>{PAGES.map((item, index) => <button key={item.id} aria-label={t(item.label)} aria-current={page === item.id ? 'page' : undefined} className={page === item.id ? 'active' : ''} onClick={() => open(item.id)}><item.icon size={18} /><span>{t(item.label)}</span><small>{String(index + 1).padStart(2, '0')}</small></button>)}</nav>
      <div className="us-sidebar-note"><span className="us-sidebar-note-icon"><ShieldCheck size={20} /></span><h3>{t("Evidence before decisions.")}</h3><p>{t("Transparent inputs. Visible assumptions. A separate check for functioning services.")}</p><a href="/evidence/" target="_blank" rel="noreferrer">{t("Research workbench")} <ArrowUpRight size={14} /></a></div>
      <div className="us-sidebar-bottom"><span className="us-dot amber" /><div><b>{t("Demonstration only")}</b><small>{t("No government system connected")}</small></div></div>
    </aside>
    {menu && <button className="us-nav-backdrop" aria-label={t("Close navigation")} onClick={() => setMenu(false)} />}
    <div className="us-workspace">
      <header className="us-topbar"><div className="us-header-context"><button className="us-icon-button us-mobile-nav" aria-label={menu ? t("Close navigation menu") : t("Open navigation menu")} onClick={() => setMenu(value => !value)}>{menu ? <X size={21} /> : <Menu size={21} />}</button><div><div className="us-breadcrumb">{t("Urban Development")} <span>/</span> <b>{t(PAGES.find(item => item.id === page)?.label || '')}</b></div><div className="us-study-label"><MapPinned size={13} /> {t("Mumbai demonstration extent")} <span>·</span> {t("Pilot location not approved")}</div></div></div><div className="us-header-actions"><LanguageSwitcher /><div className={`us-connection ${mode}`}><span className={`us-dot ${mode === 'server' ? 'green' : 'amber'}`} /><span>{mode === 'server' ? t("API + SQLite · demo") : mode === 'browser' ? t("Browser sandbox") : t("Checking connection…")}</span></div><button className="us-button" onClick={exportBrief}><ArrowDownToLine size={16} /><span>{t("Export brief")}</span></button></div></header>
      <div className="us-context-bar"><label>{t("Selected cluster")} <select aria-label={t("Selected settlement cluster")} value={selected.id} onChange={event => select(event.target.value)}>{data.clusters.map(cluster => <option value={cluster.id} key={cluster.id}>{cluster.id} — {cluster.name}</option>)}</select><ChevronDown size={14} /></label><div><span className="us-small">{t(calculation)}</span><details className="us-access-details"><summary><LockKeyhole size={14} /> {t("Officer access")}</summary><form onSubmit={event => { event.preventDefault(); workspace.setKey(keyDraft) }}><label className="us-field"><span>{t("API officer key (session only)")}</span><input aria-label={t("API officer key")} type="password" autoComplete="off" value={keyDraft} onChange={event => setKeyDraft(event.target.value)} /></label><button className="us-button" type="submit">{t("Apply key")}</button><p>{t("No key is required for the default local demo. Production roles and identity verification are not implemented.")}</p></form></details></div></div>
      {mode === 'browser' && <div className="us-sandbox-banner"><Info size={16} /><span>{t("API unavailable. This is a browser-only demonstration; saved records stay in this browser and are not synced to the server.")}</span></div>}
      <main id="us-main" className="us-content">
        {workspace.error && page !== 'assurance' && <div className="us-alert" role="alert">{errorText(workspace.error)}</div>}
        {page === 'overview' && <Overview {...common} state={state} onPage={open} />}
        {page === 'explore' && <Explore {...common} onPage={open} />}
        {page === 'prioritize' && <Prioritize {...common} onWeights={setWeights} onPage={open} />}
        {page === 'compare' && <Compare key={selected.id} data={data} selected={selected} onReport={reportChanged} onPlan={snapshot => { setDraft(snapshot); open('assurance') }} mode={mode} />}
        {page === 'assurance' && <AssurancePage key={selected.id} selected={selected} workspace={workspace} scenario={draft} onClearScenario={() => setDraft(null)} />}
      </main>
      <footer className="us-footer"><span><Building2 size={14} /><b>{t("UrbanSaarthi")}</b> {t("· Seva First project prototype")}</span><span>{t("No automated eligibility or relocation decisions.")}</span><a href="/evidence/" target="_blank" rel="noreferrer"><BookOpen size={14} /> {t("Sources & research")}</a></footer>
    </div>
  </div>
}
