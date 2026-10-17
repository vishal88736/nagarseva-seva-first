import { browserStorageAvailable, localStore } from './lib/storage'
import { Activity, Building2, ChevronDown, Database, Globe2, Info, LayoutDashboard, Menu, Moon, Play, Shield, Sun, UserRound, X } from 'lucide-react'
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { I18nProvider, Language, useI18n } from './i18n'
import { getPocket, getPockets, getSummary, offline, Pocket, sampleSummary, Summary } from './lib/api'
import { Landing } from './pages/Landing'
const Admin = lazy(() => import('./pages/Admin').then(m => ({ default: m.Admin })))
const Assurance = lazy(() => import('./pages/Assurance').then(m => ({ default: m.Assurance })))
const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })))
const Methodology = lazy(() => import('./pages/Methodology').then(m => ({ default: m.Methodology })))
const Optimizer = lazy(() => import('./pages/Optimizer').then(m => ({ default: m.Optimizer })))
const PocketDetail = lazy(() => import('./pages/PocketDetail').then(m => ({ default: m.PocketDetail })))
const Resident = lazy(() => import('./pages/Resident').then(m => ({ default: m.Resident })))
const Simulator = lazy(() => import('./pages/Simulator').then(m => ({ default: m.Simulator })))
const Pilot = lazy(() => import('./pages/Pilot').then(m => ({ default: m.Pilot })))
const Sources = lazy(() => import('./pages/Sources').then(m => ({ default: m.Sources })))
type Page = 'home' | 'dashboard' | 'pocket' | 'simulator' | 'optimizer' | 'assurance' | 'resident' | 'admin' | 'methodology' | 'pilot' | 'sources'
const validPages: Page[] = ['home', 'dashboard', 'pocket', 'simulator', 'optimizer', 'assurance', 'resident', 'admin', 'methodology', 'pilot', 'sources']
function route(): { page: Page; id?: string } {
  const [page, id] = window.location.hash.slice(1).split('/')
  return { page: validPages.includes(page as Page) ? page as Page : 'home', id: id ? decodeURIComponent(id) : undefined }
}
function AppContent() {
  const { language, setLanguage, t } = useI18n()
  const [page, setPage] = useState<Page>(() => route().page)
  const [pockets, setPockets] = useState<Pocket[]>([])
  const [summary, setSummary] = useState<Summary>(sampleSummary)
  const [selectedId, setSelectedId] = useState(() => route().id || localStore.getItem('nagarseva-project') || 'NS-0766')
  const [project, setProject] = useState<Pocket | null>(null)
  const [dark, setDark] = useState(false), [menu, setMenu] = useState(false), [demo, setDemo] = useState(false), [demoStep, setDemoStep] = useState(0)
  const [storageLimited, setStorageLimited] = useState(!browserStorageAvailable)
  const [isOffline, setIsOffline] = useState(offline), [revision, setRevision] = useState(0), [error, setError] = useState('')
  useEffect(() => {
    getPockets().then(data => setPockets(data.items)).catch(e => setError(e.message)); getSummary().then(setSummary).catch(e => setError(e.message))
    const changed = (event: Event) => { setRevision(v => v + 1); getSummary().then(setSummary).catch(e => setError(e.message)); if ((event as CustomEvent<string>).detail === '/pilot/locations') getPockets().then(data => setPockets(data.items)).catch(e => setError(e.message)) }
    const storageFailed = () => setStorageLimited(true)
    window.addEventListener('nagarseva-storage-limited', storageFailed)
    const connected = (event: Event) => setIsOffline((event as CustomEvent<boolean>).detail)
    const hash = () => { const next = route(); setPage(next.page); if (next.id) setSelectedId(next.id) }
    window.addEventListener('nagarseva-data-changed', changed); window.addEventListener('nagarseva-connection', connected); window.addEventListener('hashchange', hash)
    return () => { window.removeEventListener('nagarseva-storage-limited', storageFailed); window.removeEventListener('nagarseva-data-changed', changed); window.removeEventListener('nagarseva-connection', connected); window.removeEventListener('hashchange', hash) }
  }, [])
  useEffect(() => { document.documentElement.dataset.theme = dark ? 'dark' : 'light' }, [dark])
  useEffect(() => {
    let current = true
    localStore.setItem('nagarseva-project', selectedId)
    setProject(old => old?.pocket_id === selectedId ? old : null); setError('')
    getPocket(selectedId).then(p => { if (current) setProject(p) }).catch(e => { if (current) setError(e.message) })
    return () => { current = false }
  }, [selectedId, revision])
  const open = (next: string, id = selectedId) => {
    const destination = validPages.includes(next as Page) ? next as Page : 'home'
    setPage(destination); setSelectedId(id); setMenu(false)
    window.location.hash = `${destination}/${encodeURIComponent(id)}`
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const select = (id: string) => open('pocket', id)
  const active = (key: Page) => page === key ? 'active' : ''
  const navigation = [
    { key: 'dashboard' as Page, label: t('dashboard'), icon: <LayoutDashboard size={16} /> },
    { key: 'simulator' as Page, label: t('simulator'), icon: <Activity size={16} /> },
    { key: 'optimizer' as Page, label: t('optimizer'), icon: <Building2 size={16} /> },
    { key: 'assurance' as Page, label: t('assurance'), icon: <Shield size={16} /> },
  ]
  const people = [{ key: 'resident' as Page, label: t('resident'), icon: <UserRound size={16} /> }, { key: 'admin' as Page, label: t('admin'), icon: <Shield size={16} /> }, { key: 'pilot' as Page, label: t('pilot'), icon: <Database size={16} /> }, { key: 'sources' as Page, label: t('sources'), icon: <Globe2 size={16} /> }, { key: 'methodology' as Page, label: t('methodology'), icon: <Info size={16} /> }]
  const currentTitle = useMemo(() => ({ home: t('missionControl'), dashboard: t('priorityMap'), pocket: t('pocketDetail'), simulator: t('simulator'), optimizer: t('optimizer'), assurance: t('assurance'), resident: t('resident'), admin: t('officerView'), methodology: t('methodology'), pilot: t('pilot'), sources: t('sources') }[page]), [page, t])
  const demoPages: Page[] = ['dashboard', 'pocket', 'simulator', 'resident', 'admin', 'assurance']
  const moveDemo = (step: number) => { setDemoStep(step); open(demoPages[step]) }
  return <div className="app-shell">
    <header className="topbar"><button className="brand" onClick={() => open('home')}><span className="brand-mark"><span /><span /><span /></span><span><b>{t('brand')}</b><small>{t('tagline')}</small></span></button>
      <nav className="desktop-nav">{navigation.map(item => <button key={item.key} className={active(item.key)} onClick={() => open(item.key)}>{item.icon}{item.label}</button>)}</nav>
      <div className="top-actions"><button className="demo-button" aria-label={demo ? t('demoStep', { step: demoStep + 1 }) : t('demoMode')} aria-pressed={demo} onClick={() => { if (demo) setDemo(false); else { setDemo(true); moveDemo(0) } }}><Play size={13} /><span className="demo-label">{demo ? t('demoStep', { step: demoStep + 1 }) : t('demoMode')}</span></button><div className="lang-select"><Globe2 size={15} /><select value={language} onChange={e => setLanguage(e.target.value as Language)} aria-label={t('language')}><option value="en">EN</option><option value="hi">हिन्दी</option><option value="mr">मराठी</option></select><ChevronDown size={13} /></div><button className="theme-button" aria-label={t('toggleDark')} onClick={() => setDark(v => !v)}>{dark ? <Sun size={17} /> : <Moon size={17} />}</button><button className="menu-button" aria-label={t('openMenu')} onClick={() => setMenu(v => !v)}>{menu ? <X /> : <Menu />}</button></div>
    </header>
    {menu && <div className="mobile-menu">{[...navigation, ...people].map(item => <button key={item.key} onClick={() => open(item.key)}>{item.icon}{item.label}</button>)}</div>}
    <div className="body-layout"><aside className="sidebar"><div className="side-label">{t('workspace')}</div><button className={active('home')} onClick={() => open('home')}><Activity size={17} />{t('overview')}</button>{navigation.map(item => <button key={item.key} className={active(item.key)} onClick={() => open(item.key)}>{item.icon}{item.label}</button>)}<div className="side-separator" /><div className="side-label">{t('peopleTrust')}</div>{people.map(item => <button key={item.key} className={active(item.key)} onClick={() => open(item.key)}>{item.icon}{item.label}</button>)}<div className="sidebar-bottom"><div className="network-status"><span className={`live-dot ${isOffline ? 'offline-dot' : ''}`} /><div><b>{t(isOffline ? 'offlinePreview' : 'apiConnected')}</b><small>{t('dataSynthetic')}</small></div></div><div className="side-policy"><small>{t('alignedTo')}</small><b>PMAY-U 2.0 · SRA · SBM-U</b></div></div></aside>
      <main className="main-content"><div className="breadcrumb"><span>{t('brand')}</span><b>/</b><span>{currentTitle}</span><span className="crumb-demo">{t(project?.synthetic === false && page !== 'home' ? 'approvedLocation' : 'dataSynthetic')}</span></div>
        {demo && <div className="demo-guide"><div><b>{t('demoStep', { step: demoStep + 1 })}</b><p>{t(`demoGuide${demoStep}`)}</p></div><div className="button-row"><button className="button outline" disabled={demoStep === 0} onClick={() => moveDemo(demoStep - 1)}>{t('previous')}</button><button className="button primary" onClick={() => demoStep === 5 ? setDemo(false) : moveDemo(demoStep + 1)}>{t(demoStep === 5 ? 'endDemo' : 'next')}</button></div></div>}
        {page !== 'home' && <div className="project-context"><label><span>{t('projectContext')}</span><select aria-label={t('selectProject')} value={selectedId} onChange={e => open(page, e.target.value)}>{!pockets.some(p => p.pocket_id === selectedId) && <option value={selectedId}>{selectedId}</option>}{pockets.map(p => <option value={p.pocket_id} key={p.pocket_id}>{p.pocket_id} · {p.city} · {p.ward}</option>)}</select></label><span className={`connection-label ${isOffline ? 'offline' : ''}`}>{t(isOffline ? 'offlinePreview' : 'apiConnected')}</span></div>}
        {storageLimited && <div className="note app-error" role="status">{t('storageLimited')}</div>}
        {error && <div className="error-note app-error" role="alert">{error}</div>}
        <Suspense fallback={<div className="empty-state" role="status">{t('loading')}</div>}>
          {page === 'home' && <Landing summary={summary} onOpen={open} />}
          {page === 'dashboard' && <Dashboard pockets={pockets} summary={summary} onSelect={select} />}
          {page === 'pocket' && project && <PocketDetail pocket={project} onBack={() => open('dashboard')} onOpen={open} />}
          {page === 'simulator' && project && <Simulator key={selectedId} pocket={project} />}
          {page === 'optimizer' && <Optimizer pockets={pockets} onSelect={select} />}
          {page === 'assurance' && project && <Assurance pocket={project} summary={summary} revision={revision} onSelect={select} />}
          {page === 'resident' && project && <Resident key={selectedId} pocket={project} revision={revision} />}
          {page === 'admin' && <Admin pocketId={selectedId} summary={summary} revision={revision} />}
          {page === 'pilot' && project && <Pilot key={selectedId} pocket={project} revision={revision} />}
          {page === 'methodology' && <Methodology />}
          {page === 'sources' && <Sources pocket={project} />}
          {['pocket', 'simulator', 'assurance', 'resident', 'pilot'].includes(page) && !project && !error && <div className="empty-state" role="status">{t('loading')}</div>}
        </Suspense>
      </main></div>
    <footer className="site-footer"><span>{t('footerCopyright')}</span><span><Info size={13} />{t('sourceFootnote')}</span><span>{t('footerRegion')}</span></footer>
  </div>
}
export default function App() { return <I18nProvider><AppContent /></I18nProvider> }
