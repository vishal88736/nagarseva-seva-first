import { lazy, Suspense, useEffect, useState } from 'react'
import { ArrowRight, MapPinned } from 'lucide-react'
import { t, errorText, formatDate, formatNumber } from '../i18n/locale'
import { Heading, Panel, Tag } from './PlanningPages'
import { dataApi } from './publicClient'
import type { Metadata, Stats } from './publicClient'
import type { IssueSummary } from './issueClient'
import { useReferenceBoundaries } from './useReferenceBoundaries'
import type { Page } from './routing'

const PublicMap=lazy(()=>import('./PublicMap'))
export default function ProductDashboard({metadata,stats,onPage}:{metadata:Metadata|null;stats:Stats|null;onPage:(page:Page,query?:string)=>void}) {
  const reference=useReferenceBoundaries(),[issues,setIssues]=useState<IssueSummary|null>(null),[issueError,setIssueError]=useState(''),[retry,setRetry]=useState(0)
  useEffect(()=>{let active=true;setIssueError('');dataApi<IssueSummary>('/issues/summary').then(data=>{if(active)setIssues(data)}).catch(problem=>{if(active)setIssueError(problem.message)});return()=>{active=false}},[retry])
  const registered=metadata?.snapshot.settlement_record_type==='published_cluster_register'
  const metrics=[
    {label:'dashboard.boundaries',value:reference.data?formatNumber(reference.data.geometry.features.length,0):reference.loading?t('Loading…'):t('Unavailable'),note:'dashboard.historicalOnly'},
    {label:registered?'dashboard.register':'Settlement records',value:stats?formatNumber(stats.settlements_loaded,0):t('dashboard.noData'),note:registered?'dashboard.registerYear':'dashboard.importedRecords'},
    {label:'dashboard.openIssues',value:issues?formatNumber(issues.open,0):t('dashboard.noData'),note:'dashboard.selfReported'},
    {label:'dashboard.verified',value:stats?.verified_interventions!=null?formatNumber(stats.verified_interventions,0):t('dashboard.noData'),note:'dashboard.recordedReview'},
  ]
  return <>
    <Heading number="01" title={t('dashboard.title')} description={t('dashboard.intro')}><button className="us-button primary" onClick={()=>onPage('report-issue')}>{t('nav.issue')}<ArrowRight size={16}/></button></Heading>
    <div className="us-metrics product-metrics">{metrics.map(metric=><div className="us-metric" key={metric.label}><span>{t(metric.label)}</span><strong>{metric.value}</strong><small>{t(metric.note)}</small></div>)}</div>
    {reference.error&&<div className="us-alert" role="alert">{errorText(reference.error)} <button className="us-button" onClick={reference.retry}>{t('Retry reference boundaries')}</button></div>}
    <section className="us-panel product-map-preview"><div className="product-section-heading"><div><h2>{t('dashboard.mapTitle')}</h2><p>{t('dashboard.mapNote')}</p></div><button className="us-button" onClick={()=>onPage('settlements')}><MapPinned size={16}/>{t('dashboard.openExplorer')}</button></div><Suspense fallback={<p role="status">{t('Loading map…')}</p>}><PublicMap preview settlements={[]} onSelect={()=>{}}/></Suspense></section>
    <div className="product-dashboard-bottom"><Panel title={t('dashboard.recentIssues')}>
      {issueError?<div role="alert"><p>{errorText(issueError)}</p><button className="us-button" onClick={()=>setRetry(value=>value+1)}>{t('Retry')}</button></div>:!issues?<p role="status">{t('Loading…')}</p>:issues.recent.length?<ul className="product-recent-issues">{issues.recent.map(issue=><li key={issue.id}><button onClick={()=>onPage('report-issue',`?issue=${encodeURIComponent(issue.id)}`)}><span><b>{t(`issues.category.${issue.category}`)}</b><small>{issue.id} · {formatDate(issue.report_date)}</small></span><Tag tone="blue">{t(`issues.status.${issue.status}`)}</Tag></button><p>{issue.description}</p></li>)}</ul>:<div className="product-empty"><b>{t('dashboard.noIssues')}</b><p>{t('dashboard.noIssuesNote')}</p><button className="us-button" onClick={()=>onPage('report-issue')}>{t('nav.issue')}</button></div>}
    </Panel><Panel title={t('dashboard.sourceSummary')}><dl className="us-facts"><div><dt>{t('dashboard.projectListings')}</dt><dd>{stats?formatNumber(stats.projects,0):t('dashboard.noData')}</dd></div><div><dt>{t('Mapped context objects')}</dt><dd>{metadata?formatNumber(metadata.snapshot.mapped_objects_count,0):t('dashboard.noData')}</dd></div><div><dt>{t('Census 2011 observations')}</dt><dd>{metadata?formatNumber(metadata.snapshot.historical_observation_count??0,0):t('dashboard.noData')}</dd></div></dl><p className="us-small">{t('dashboard.sourceNote')}</p><button className="us-button" onClick={()=>onPage('projects')}>{t('nav.projects')}</button></Panel></div>
    <p className="product-data-note">{t(registered?(metadata?.snapshot.historical_observation_count?'dashboard.freshness':'dashboard.registerFreshness'):'dashboard.referenceFreshness')}{metadata?.snapshot.built_at&&<> {t('dashboard.snapshotBuilt',{date:formatDate(metadata.snapshot.built_at)})}</>}</p>
  </>
}
