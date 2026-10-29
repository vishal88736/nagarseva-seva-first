import { useState } from 'react'
import { t, errorText } from '../i18n/locale'
import { Heading, Panel } from './PlanningPages'
import PublicProjectRecords from './PublicProjectRecords'
import PublicContext from './PublicContext'
import DatasetReports from './DatasetReports'
import { HISTORICAL_2015 } from './historicalBoundaries'
import { exportPublicCsv, exportDataCsv } from './publicClient'
import type { Metadata } from './publicClient'
import type { Page } from './routing'

export default function ProjectsReports({metadata,onPage}:{metadata:Metadata|null;onPage:(page:Page)=>void}) {
  const [tab,setTab]=useState<'projects'|'reports'|'tools'>('projects'),[error,setError]=useState('')
  function exportCsv(kind:string){setError('');void exportPublicCsv(kind,'').catch(problem=>setError(problem.message))}
  function issueCsv(){setError('');void exportDataCsv('/issues/report.csv','urbansaarthi-reported-issues.csv').catch(problem=>setError(problem.message))}
  return <>
    <Heading number="04" title={t('nav.projects')} description={t('projects.intro')}><button className="us-button" onClick={()=>onPage('data')}>{t('Data & access')}</button></Heading>
    <div role="tablist" aria-label={t('projects.tabs')} className="product-tabs">{(['projects','reports','tools'] as const).map(key=><button role="tab" aria-selected={tab===key} key={key} onClick={()=>setTab(key)}>{t(`projects.tab.${key}`)}</button>)}</div>
    {error&&<p role="alert" className="us-alert">{errorText(error)}</p>}
    {tab==='projects'&&<Panel><PublicProjectRecords/></Panel>}
    {tab==='reports'&&<><DatasetReports metadata={metadata}/><Panel title={t('projects.exports')}><div className="product-report-list"><div><b>{t('projects.registerExport')}</b><p>{t('projects.registerExportNote')}</p><button className="us-button" onClick={()=>exportCsv('settlements')}>{t('Export settlements CSV')}</button></div><div><b>{t('projects.projectExport')}</b><p>{t('projects.projectExportNote')}</p><button className="us-button" onClick={()=>exportCsv('projects')}>{t('Export projects CSV')}</button></div><div><b>{t('projects.issueExport')}</b><p>{t('issues.prototype')}</p><button className="us-button" onClick={issueCsv}>{t('projects.downloadIssues')}</button></div><div><b>{t('2015 Reference Boundaries')}</b><p>{t('projects.boundaryExportNote')}</p><a className="us-button" href={HISTORICAL_2015.geometryUrl} download>{t('projects.downloadGeoJSON')}</a></div></div></Panel>{metadata?.snapshot.historical_observation_count?<PublicContext/>:<Panel title={t('Historical Census context')}><p>{t('projects.noCensus')}</p></Panel>}</>}
    {tab==='tools'&&<Panel title={t('projects.toolsTitle')} note={t('projects.toolsNote')}><div className="product-tools">{(['prioritize','compare','assurance','data'] as const).map(page=><button className="us-button" key={page} onClick={()=>onPage(page)}>{t(`projects.tool.${page}`)}</button>)}</div></Panel>}
  </>
}
