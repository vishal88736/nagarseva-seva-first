import {lazy,Suspense,useEffect,useMemo,useState} from 'react'
import {Database,FolderOpen,Info,LayoutDashboard,MapPinned,Menu,MessageSquarePlus,PlugZap,X} from 'lucide-react'
import {LanguageSwitcher,useLanguage,localizedPageTitle} from '../i18n/LanguageProvider'
import {t} from '../i18n/locale'
import {MAIN_ROUTES,PATHS,activeSection,routePage} from '../urban/routing'
import type {Page} from '../urban/routing'
import {CivicProvider,useCivic} from './CivicProvider'
import type {CivicState} from './types'
import {Heading,Modal} from './ui'
import type {Cluster,Dataset} from '../urban/engine'
import DemoDashboard from './DemoDashboard'
const DemoSettlements=lazy(()=>import('./DemoSettlements'))
const DemoIssues=lazy(()=>import('./DemoIssues'))
const DemoProjects=lazy(()=>import('./DemoProjects'))
const DemoVisits=lazy(()=>import('./DemoVisits'))
const DemoReports=lazy(()=>import('./DemoReports'))
const DemoHousing=lazy(()=>import('./DemoHousing'))
const DemoServices=lazy(()=>import('./DemoServices'))
const DemoCommunity=lazy(()=>import('./DemoCommunity'))
const DemoManagement=lazy(()=>import('./DemoManagement'))
const Methodology=lazy(()=>import('./Methodology'))
const DataIntegration=lazy(()=>import('../integration/DataIntegration'))
const Compare=lazy(()=>import('../urban/PlanningPages').then(module=>({default:module.Compare})))
type CivicPage=Page|'integration'|'visits'|'housing'|'services'|'methodology'
function readRoute(){const pathname=location.pathname.replace(/\/+$/,'')||'/',query=new URLSearchParams(location.search)
 const aliases:Record<string,string>={'/projects/reports':'reports','/projects/community':'community'}
 if(aliases[pathname]&&!query.has('tab'))query.set('tab',aliases[pathname])
 const page:CivicPage=pathname==='/methodology'?'methodology':pathname==='/data-integration'?'integration':pathname==='/visits'?'visits':pathname==='/housing'?'housing':pathname==='/services'?'services':aliases[pathname]?'projects':routePage(pathname,location.hash)
 return {page,search:query.size?`?${query}`:''}}
const NAV=[...MAIN_ROUTES,{id:'integration',path:'/data-integration',label:'ir.nav'}] as const
function planning(state:CivicState):Dataset{
 const clusters:Cluster[]=state.settlements.map(row=>{const indicators={water:row.waterAccessPercent===null?null:100-row.waterAccessPercent,sanitation:row.sanitationAccessPercent===null?null:100-row.sanitationAccessPercent,housing:row.householdsForAssessment/row.householdEstimate*100,access:row.roadAccessPercent===null?null:100-row.roadAccessPercent,risk:({low:20,medium:50,high:80})[row.riskLevel]};return {id:row.id,name:row.name,households:row.householdEstimate,households_source:'Synthetic household estimate',node_id:'',synthetic:true,geometry:row.geometry,indicators,provenance:Object.fromEntries(Object.keys(indicators).map(key=>[key,{kind:'Synthetic fixture',source_label:'Central synthetic demo record; derived deficit',reference_date:null,unit:'deficit_0_100'}])) as Cluster['provenance']}})
 return {schema_version:'2',metadata:{title:'UrbanSaarthi synthetic planning scenarios',geographic_scope:'Illustrative Mumbai extent',synthetic:true,real_pilot_approved:false,reference_date:state.lastSavedAt,source_label:'Central synthetic demonstration store',limitations:['No official records or measurements','Scenario assumptions are hypothetical']},default_weights:{water:.3,sanitation:.25,housing:.2,access:.15,risk:.1},clusters,network:{nodes:[],edges:[]},amenities:[],relocation_node_id:''}
}
function Workspace(){
 const {language}=useLanguage(),workspace=useCivic(),{state,loading,error}=workspace
 const [route,setRoute]=useState(readRoute),[mobile,setMobile]=useState(false),[about,setAbout]=useState(false)
 const {page}=route,query=useMemo(()=>new URLSearchParams(route.search),[route.search]),projectTab=['projects','reports','visits','housing','community'].includes(query.get('tab')||'')?query.get('tab')!:'projects'
 const active=page==='methodology'?'projects':page==='integration'?'integration':page==='services'?'settlements':page==='housing'||page==='visits'?'projects':activeSection(page)
 const titleKey=NAV.find(row=>row.id===page)?.label||({methodology:'audit.methodology',data:'d.dataManagement',housing:'d.housing',visits:'d.visits',services:'d.services',prioritize:'d.services',assurance:'d.services',compare:'d.scenarios'} as Record<string,string>)[page]||'civic.dashboardTitle'
 const icons={dashboard:LayoutDashboard,settlements:MapPinned,'report-issue':MessageSquarePlus,projects:FolderOpen,integration:PlugZap}
 useEffect(()=>{document.title=localizedPageTitle(titleKey)},[language,titleKey])
 useEffect(()=>{const changed=()=>{setRoute(readRoute());setMobile(false)};addEventListener('popstate',changed);addEventListener('hashchange',changed);return()=>{removeEventListener('popstate',changed);removeEventListener('hashchange',changed)}},[])
 useEffect(()=>{if(!mobile)return
 const sidebar=document.getElementById('civic-navigation'),content=document.querySelector('.us-workspace');content?.setAttribute('inert','')
 sidebar?.querySelector<HTMLButtonElement>('button')?.focus()
 const keyboard=(event:KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();closeNavigation()}else if(event.key==='Tab'){
  const targets=Array.from(sidebar?.querySelectorAll<HTMLElement>('a[href],button:not([disabled])')||[]).filter(node=>node.getClientRects().length),first=targets[0],last=targets[targets.length-1]
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}
 }}
 addEventListener('keydown',keyboard);return()=>{content?.removeAttribute('inert');removeEventListener('keydown',keyboard)}
 },[mobile])
 function closeNavigation(){setMobile(false);requestAnimationFrame(()=>document.querySelector<HTMLButtonElement>('.us-mobile-nav')?.focus())}
 function navigate(path:string){history.pushState(null,'',path);setRoute(readRoute());setMobile(false);requestAnimationFrame(()=>document.getElementById('civic-main')?.focus({preventScroll:true}));window.scrollTo({top:0,behavior:'instant'})}
 function navLink(event:React.MouseEvent<HTMLAnchorElement>,path:string){if(event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;event.preventDefault();navigate(path)}
 const planData=useMemo(()=>state&&page==='compare'?planning(state):null,[state,page]),selectedPlan=planData?.clusters.find(row=>row.id===query.get('settlement'))||planData?.clusters[0]
 return <div className={`us-shell public-workspace workspace-focused product-shell civic-demo-shell ${mobile?'navigation-expanded':''}`}>
 <a className="us-skip" href="#civic-main">{t('Skip to main content')}</a><aside id="civic-navigation" className={`us-sidebar ${mobile?'open':''}`} role={mobile?'dialog':undefined} aria-modal={mobile||undefined} aria-label={t('shell.navigation')}>
 {mobile&&<button className="product-nav-close" aria-label={t('Close navigation')} onClick={closeNavigation}><X size={18}/></button>}
 <button className="us-brand" onClick={()=>navigate('/dashboard')} aria-label={t('UrbanSaarthi')}><img src="/urbansaarthi-mark.svg" alt="" className="us-brand-mark"/><span><strong>UrbanSaarthi</strong><small>{t('civic.tagline')}</small></span></button>
 <nav aria-label={t('shell.navigation')}>{NAV.map(item=>{const Icon=icons[item.id];return <a key={item.id} href={item.path} onClick={event=>navLink(event,item.path)} aria-current={active===item.id?'page':undefined} className={active===item.id?'active':''}><Icon size={22}/><span>{t(item.label)}</span></a>})}</nav><div className="workspace-sidebar-end"><a className="workspace-data-link" href="/methodology" aria-current={page==='methodology'?'page':undefined} onClick={event=>navLink(event,'/methodology')}>{t('audit.methodology')}</a><a className="workspace-data-link" href={PATHS.data} onClick={event=>navLink(event,PATHS.data)}><Database size={20}/>{t('d.dataManagement')}</a><small>SEVAMO96<br/>{t('d.challengeCategory')}</small></div></aside>
 {mobile&&<button className="us-nav-backdrop" tabIndex={-1} aria-label={t('Close navigation')} onClick={closeNavigation}/>}
 <div className="us-workspace"><header className="us-topbar demo-topbar"><div className="us-header-context"><button className="us-icon-button us-mobile-nav" aria-label={t(mobile?'Close navigation':'Open navigation menu')} aria-expanded={mobile} aria-controls="civic-navigation" onClick={()=>setMobile(!mobile)}>{mobile?<X/>:<Menu/>}</button><span className="workspace-current-page">{t(titleKey)}</span></div><div className="us-header-actions"><button className="demo-mode" aria-label={t('d.aboutDemo')} onClick={()=>setAbout(true)}><Info size={15}/><span>{t('d.demoMode')}</span></button><LanguageSwitcher/><a className="us-button demo-admin-link" href={PATHS.data} onClick={event=>navLink(event,PATHS.data)}>{t('d.demoAdmin')}</a></div></header>
 <main id="civic-main" tabIndex={-1} className="us-content"><p className="demo-persistent-notice">{t('audit.demoBanner')}</p>{error&&<p className="us-alert" role="alert">{t(error)} <button className="us-button" onClick={()=>void workspace.reload()}>{t('Retry')}</button></p>}
 <Suspense fallback={<p role="status">{t('Loading…')}</p>}>
 {page==='integration'?<DataIntegration/>:loading&&!state?<p role="status">{t('d.loadingDemo')}</p>:!state?<p>{t('demo.error.backend')}</p>:<div key={`${page}-${route.search}`}>
 {page==='dashboard'&&<DemoDashboard navigate={navigate}/>}
 {page==='settlements'&&<DemoSettlements navigate={navigate} initialId={query.get('settlement')||''}/>}
 {page==='report-issue'&&<DemoIssues query={query} navigate={navigate}/>}
 {page==='projects'&&<><Heading number="04" title={t('nav.projects')} description={t('d.projectHubIntro')}/><div className="product-tabs demo-hub-tabs" role="tablist" aria-label={t('d.projectViews')}>{['projects','reports','visits','housing','community','data'].map(tab=><button key={tab} role="tab" aria-selected={projectTab===tab} onClick={()=>tab==='data'?navigate(PATHS.data):navigate(`/projects?tab=${tab}`)}>{t(`d.tab.${tab}`)}</button>)}</div>{projectTab==='projects'&&<DemoProjects query={query} navigate={navigate}/>} {projectTab==='reports'&&<DemoReports/>}{projectTab==='visits'&&<DemoVisits query={query} navigate={navigate}/>} {projectTab==='housing'&&<DemoHousing query={query} navigate={navigate}/>} {projectTab==='community'&&<DemoCommunity/>}</>}
 {page==='visits'&&<><Heading number="06" title={t('d.visits')} description={t('d.visitIntro')}/><DemoVisits query={query} navigate={navigate}/></>}
 {page==='housing'&&<><Heading number="05" title={t('d.housing')} description={t('d.housingIntro')}/><DemoHousing query={query} navigate={navigate}/></>}
 {['services','prioritize','assurance'].includes(page)&&<DemoServices navigate={navigate}/>}
 {page==='compare'&&planData&&selectedPlan&&<Compare data={planData} selected={selectedPlan} mode="browser" onPlan={()=>navigate(`/projects?new=1&settlement=${selectedPlan.id}`)}/>}
 {page==='data'&&<DemoManagement/>}{page==='methodology'&&<Methodology/>}
 </div>}
 </Suspense></main><footer className="us-footer"><span>UrbanSaarthi · SEVAMO96</span><span>{t('d.footer')}</span></footer></div>
 {about&&<Modal title={t('d.demoMode')} onClose={()=>setAbout(false)}><p>{t('d.demoNotice')}</p><p>{t('ir.capability')}</p><button className="us-button" onClick={()=>{setAbout(false);navigate('/data-integration')}}>{t('ir.nav')}</button></Modal>}
 </div>
}
export default function CivicWorkspace(){return <CivicProvider><Workspace/></CivicProvider>}
