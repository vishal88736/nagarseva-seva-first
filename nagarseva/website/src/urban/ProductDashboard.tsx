import { lazy, Suspense, useEffect, useState } from 'react'
import { ArrowRight, Building2, Database, FileText, MapPinned, MessageCircleWarning } from 'lucide-react'
import { t, errorText, formatDate, formatNumber } from '../i18n/locale'
import { Heading } from './PlanningPages'
import { dataApi } from './publicClient'
import type { Metadata, PublicSettlement, Stats } from './publicClient'
import type { IssueSummary } from './issueClient'
import { useReferenceBoundaries } from './useReferenceBoundaries'
import ReferencePolygonTable from './ReferencePolygonTable'
import type { Page } from './routing'

const PublicMap = lazy(() => import('./PublicMap'))
export default function ProductDashboard({ metadata, stats, loading, onPage }: {
  metadata: Metadata | null; stats: Stats | null; settlements: PublicSettlement[]; loading: boolean; onPage: (page: Page, query?: string) => void
}) {
  const reference = useReferenceBoundaries()
  const [issues,setIssues] = useState<IssueSummary | null>(null), [issueError,setIssueError] = useState(''), [retry,setRetry] = useState(0)
  const [selected,setSelected] = useState<number | null>(null)
  useEffect(()=>{
    let active = true; setIssueError('')
    dataApi<IssueSummary>('/issues/summary').then(result=>{if(active)setIssues(result)}).catch(problem=>{if(active)setIssueError(problem.message)})
    return ()=>{active=false}
  },[retry])
  const registered = metadata?.snapshot.settlement_record_type === 'published_cluster_register' && (stats?.settlements_loaded ?? 0)>0
  const status = (present: boolean, pending = 'civic.importPending') => loading ? 'Loading…' : !metadata ? 'Error' : present ? 'civic.verificationPending' : pending
  const coverage = [
    { Icon: MapPinned, label: 'civic.boundaries', state: reference.loading?'Loading…':reference.error?'Error':reference.data?'Available':'No records', tone: reference.data?'green':'amber' },
    { Icon: FileText, label: 'civic.sra', state: status(registered), tone: 'amber' },
    { Icon: Database, label: 'civic.census', state: metadata?'Not linked':loading?'Loading…':'Error', tone: 'gray' },
    { Icon: MessageCircleWarning, label: 'civic.issueReports', state: issueError?'Error':!issues?'Loading…':issues.total?'Available':'No records', tone: issues?.total?'green':'gray' },
    { Icon: Building2, label: 'civic.redevelopment', state: status(!!stats?.projects,'No records'), tone: 'amber' },
  ]
  return <>
    <Heading number="01" title={t('civic.dashboardTitle')} description={t('civic.dashboardIntro')}/>
    <div className="civic-dashboard-top">
      <section className="us-panel civic-overview" aria-busy={loading||reference.loading}>
        <h2>{t('civic.overview')}</h2><p>{t('civic.overviewIntro')}</p>
        <div className="civic-overview-grid">
          <article className="civic-summary-card blue"><span className="civic-card-icon"><MapPinned size={33}/></span><div><h3>{t('civic.boundaryCard')}</h3>{reference.data?<><strong className="civic-count">{formatNumber(reference.data.summary.featureCount,0)}</strong><span> {t('civic.sourcePolygons')}</span><p>{t('civic.displayCount',{valid:formatNumber(reference.data.geometry.features.length,0),excluded:formatNumber(reference.data.skippedCount,0)})}</p></>:<p role="status">{reference.loading?t('Loading…'):t('Unavailable')}</p>}<small>OpenCity · 2015</small></div></article>
          <article className="civic-summary-card amber"><span className="civic-card-icon"><FileText size={33}/></span><div><h3>{t('civic.sraCard')}</h3><span className="us-tag amber">{t(status(registered))}</span><p>{loading?t('Loading…'):!metadata?t('Unavailable'):registered?t('civic.sraImported',{count:formatNumber(stats!.settlements_loaded,0)}):t('civic.sraPending')}</p><button className="civic-text-button" onClick={()=>onPage('settlements')}>{t('civic.browseRecords')} <ArrowRight size={14}/></button></div></article>
          <article className="civic-summary-card rose"><span className="civic-card-icon"><MessageCircleWarning size={33}/></span><div><h3>{t('civic.issueReports')}</h3>{issueError?<p role="alert">{errorText(issueError)}</p>:<p>{!issues?t('Loading…'):issues.total?t('civic.issueCount',{count:formatNumber(issues.total,0)}):t('civic.noIssues')}</p>}<button className="civic-text-button" onClick={()=>onPage('report-issue')}>{t('nav.issue')} <ArrowRight size={14}/></button></div></article>
          <article className="civic-summary-card mint"><span className="civic-card-icon"><Building2 size={33}/></span><div><h3>{t('civic.redevelopment')}</h3><p>{loading?t('Loading…'):!metadata?t('Unavailable'):t('civic.noProjects')}</p>{!!stats?.projects&&<small>{t('civic.publishedListings',{count:formatNumber(stats.projects,0)})}</small>}<button className="civic-text-button" onClick={()=>onPage('projects')}>{t('civic.viewListings')} <ArrowRight size={14}/></button></div></article>
        </div>
      </section>
      <div className="civic-coverage-column"><section className="us-panel civic-data-coverage"><h2>{t('civic.coverage')}</h2><p>{t('civic.coverageIntro')}</p><ul>{coverage.map(({Icon,label,state,tone})=><li key={label}><Icon size={23}/><span>{t(label)}</span><span className={`coverage-status ${tone}`}><i/>{t(state)}</span></li>)}</ul><small>{t('civic.censusNote')}</small></section>
        <section className="us-panel civic-activity"><div className="civic-section-heading"><h2>{t('civic.recentActivity')}</h2><button className="civic-text-button" onClick={()=>onPage('projects')}>{t('civic.viewReports')} <ArrowRight size={14}/></button></div>{issueError?<div role="alert"><p>{errorText(issueError)}</p><button className="us-button" onClick={()=>setRetry(value=>value+1)}>{t('Retry')}</button></div>:!issues?<p role="status">{t('Loading…')}</p>:issues.recent.length?<ul className="civic-activity-list">{issues.recent.slice(0,3).map(issue=><li key={issue.id}><button className="civic-text-button" onClick={()=>onPage('report-issue',`?issue=${encodeURIComponent(issue.id)}`)}>{t(`issues.category.${issue.category}`)}</button><small>{issue.id} · {formatDate(issue.reported_at,true)}</small><span className="us-tag blue">{t(`issues.status.${issue.status}`)}</span></li>)}</ul>:<div className="civic-empty"><FileText size={31}/><b>{t('civic.noActivity')}</b><p>{t('civic.activityNote')}</p></div>}</section>
      </div>
      <div className="civic-dashboard-map"><Suspense fallback={<p role="status">{t('Loading map…')}</p>}><PublicMap preview referenceOnly settlements={[]} onSelect={()=>{}} selectedReference={selected} onReferenceSelect={setSelected}/></Suspense><button className="civic-text-button" onClick={()=>onPage('settlements')}>{t('dashboard.openExplorer')} <ArrowRight size={15}/></button></div>
    </div>
    {reference.error&&<div className="us-alert" role="alert">{errorText(reference.error)} <button className="us-button" onClick={reference.retry}>{t('Retry reference boundaries')}</button></div>}
    {reference.data&&<ReferencePolygonTable compact data={reference.data} selected={selected} onSelect={number=>onPage('settlements',`?reference=${number}`)}/>}
  </>
}
