import { lazy, Suspense, useEffect, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { ArrowRight, Check, Database, Grid2X2, Layers3, MapPinned, MessageSquarePlus, Rows3 } from 'lucide-react'
import { t, errorText, formatDate, formatNumber } from '../i18n/locale'
import { Heading, Panel, Tag } from './PlanningPages'
import { dataApi } from './publicClient'
import type { Metadata, PublicSettlement, Stats } from './publicClient'
import type { IssueSummary } from './issueClient'
import { useReferenceBoundaries } from './useReferenceBoundaries'
import type { Page } from './routing'
import CityAtlasArt from './CityAtlasArt'

const PublicMap = lazy(() => import('./PublicMap'))
const scopes = [
  { id: 'all', key: 'design.allData', Icon: Layers3 },
  { id: 'reference', key: 'design.boundaries', Icon: MapPinned },
  { id: 'register', key: 'design.register', Icon: Database },
  { id: 'issues', key: 'design.issues', Icon: MessageSquarePlus },
] as const
type Scope = typeof scopes[number]['id']

function WardDistribution({ settlements }: { settlements: PublicSettlement[] }) {
  const wards = new Map<string, number>()
  for (const row of settlements) if (row.administrative_area) wards.set(row.administrative_area, (wards.get(row.administrative_area) || 0) + 1)
  const entries = [...wards].sort(([a], [b]) => a.localeCompare(b)), maximum = Math.max(1, ...wards.values())
  if (!entries.length) return null
  return <figure className="registry-distribution">
    <figcaption>{t('design.wardChart')}<span>{t('design.wardCount', { count: formatNumber(entries.length, 0) })}</span></figcaption>
    <div className="registry-bars" role="img" aria-label={`${t('design.wardChart')}: ${entries.map(([ward, count]) => `${ward}: ${formatNumber(count, 0)}`).join(', ')}`}>
      {entries.map(([ward, count]) => <div key={ward} title={`${ward}: ${formatNumber(count, 0)}`}><i style={{ height: `${count / maximum * 100}%` }} /><span>{ward}</span></div>)}
    </div>
    <p>{t('design.wardChartNote')}</p>
  </figure>
}

export default function ProductDashboard({ metadata, stats, settlements, loading, onPage }: {
  metadata: Metadata | null; stats: Stats | null; settlements: PublicSettlement[]; loading: boolean; onPage: (page: Page, query?: string) => void
}) {
  const reference = useReferenceBoundaries()
  const [issues, setIssues] = useState<IssueSummary | null>(null), [issueError, setIssueError] = useState(''), [retry, setRetry] = useState(0)
  const [scope, setScope] = useState<Scope>('all'), [list, setList] = useState(false)
  function moveScope(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === 'ArrowRight' ? (index + 1) % scopes.length : event.key === 'ArrowLeft' ? (index + scopes.length - 1) % scopes.length : event.key === 'Home' ? 0 : event.key === 'End' ? scopes.length - 1 : null
    if (next === null) return
    event.preventDefault(); setScope(scopes[next].id)
    document.getElementById(`workspace-tab-${scopes[next].id}`)?.focus()
  }
  useEffect(() => {
    let active = true; setIssueError('')
    dataApi<IssueSummary>('/issues/summary').then(data => { if (active) setIssues(data) }).catch(problem => { if (active) setIssueError(problem.message) })
    return () => { active = false }
  }, [retry])
  const registered = metadata?.snapshot.settlement_record_type === 'published_cluster_register'
  const valid = reference.data?.geometry.features.length, total = reference.data?.metadata.source_feature_count
  const validFraction = valid != null && total ? valid / total : 0
  const unknownCount = loading ? '—' : t('dashboard.noData')
  const metrics = [
    { label: 'dashboard.boundaries', value: valid != null ? formatNumber(valid, 0) : reference.loading ? '—' : t('Unavailable'), missing: valid == null, note: 'dashboard.historicalOnly' },
    { label: registered ? 'dashboard.register' : 'Settlement records', value: stats ? formatNumber(stats.settlements_loaded, 0) : unknownCount, missing: !stats, note: registered ? 'dashboard.registerYear' : 'dashboard.importedRecords' },
    { label: 'dashboard.openIssues', value: issues ? formatNumber(issues.open, 0) : issueError ? t('dashboard.noData') : '—', missing: !issues, note: 'dashboard.selfReported' },
    { label: 'dashboard.verified', value: stats?.verified_interventions != null ? formatNumber(stats.verified_interventions, 0) : unknownCount, missing: stats?.verified_interventions == null, note: 'dashboard.recordedReview' },
    { label: 'dashboard.projectListings', value: stats ? formatNumber(stats.projects, 0) : unknownCount, missing: !stats, note: 'design.listingsNote' },
  ]
  return <>
    <section className="product-hero" aria-busy={loading || reference.loading || !issues && !issueError}>
      <CityAtlasArt />
      <div className="product-hero-copy">
        <Heading number="01" title={t('dashboard.title')} description={t('dashboard.intro')} />
        <div className="product-coverage">
          <span>{t('design.boundaryValidation')}</span>
          <div className="product-coverage-bar" role="progressbar" aria-label={t('design.boundaryValidation')} aria-valuemin={0} aria-valuemax={total} aria-valuenow={valid}>
            {Array.from({ length: 5 }, (_, index) => <span key={index}><i style={{ width: `${Math.max(0, Math.min(1, validFraction * 5 - index)) * 100}%` }} /></span>)}
          </div>
          <div className="product-coverage-values"><span>{valid != null ? formatNumber(valid, 0) : '—'}<small>{t('design.validPolygons')}</small></span><span>{total != null ? formatNumber(total, 0) : '—'}<small>{t('design.sourcePolygons')}</small></span></div>
        </div>
      </div>
      <div className="us-metrics product-metrics">{metrics.map(metric => <div className={`us-metric ${metric.missing ? 'is-missing' : ''}`} key={metric.label}>
        <span className="product-metric-marker"><Check size={10} strokeWidth={2} /></span><strong>{metric.value}</strong><span className="product-metric-label">{t(metric.label)}</span><small>{t(metric.note)}</small>
      </div>)}</div>
    </section>
    {reference.error && <div className="us-alert" role="alert">{errorText(reference.error)} <button className="us-button" onClick={reference.retry}>{t('Retry reference boundaries')}</button></div>}
    <section className={`product-board ${list ? 'list-view' : ''}`}>
      <header className="product-board-header"><h2>{t('design.workspace')}</h2>
        <div role="tablist" aria-label={t('design.filterCards')} className="product-board-tabs">{scopes.map(({ id, key, Icon }, index) => <button key={id} id={`workspace-tab-${id}`} role="tab" aria-selected={scope === id} aria-controls="workspace-card-results" tabIndex={scope === id ? 0 : -1} onKeyDown={event => moveScope(event, index)} onClick={() => setScope(id)}><Icon size={17} strokeWidth={1.5} />{t(key)}</button>)}</div>
        <button className="product-view-button" aria-label={t(list ? 'design.gridView' : 'design.listView')} aria-pressed={list} onClick={() => setList(value => !value)}>{list ? <Grid2X2 size={19} /> : <Rows3 size={19} />}</button>
      </header>
      <div id="workspace-card-results" role="tabpanel" aria-labelledby={`workspace-tab-${scope}`} className={`product-data-cards ${scope !== 'all' ? 'single-card' : ''}`}>
        {(scope === 'all' || scope === 'reference') && <section className="us-panel product-map-preview product-data-card">
          <div className="product-card-source"><MapPinned size={16} /><span>{t('design.historicalSource')}</span><span className="product-source-dot" /></div>
          <div className="product-section-heading"><h2>{t('dashboard.mapTitle')}</h2><p>{t('dashboard.mapNote')}</p></div>
          <Suspense fallback={<p role="status">{t('Loading map…')}</p>}><PublicMap preview settlements={[]} onSelect={() => {}} /></Suspense>
          <button className="us-button product-card-action" onClick={() => onPage('settlements')}>{t('dashboard.openExplorer')}<ArrowRight size={15} /></button>
        </section>}
        {(scope === 'all' || scope === 'register') && <Panel className="product-register-card product-data-card">
          <div className="product-card-source"><Database size={16} /><span>{t(registered ? 'design.registerSource' : 'dashboard.importedRecords')}</span><span className="product-source-dot" /></div>
          <h2>{t('design.registerTitle')}</h2><p className="product-card-description">{t(registered ? 'dashboard.registerYear' : 'dashboard.importedRecords')}</p>
          <div className="product-card-stat"><span>{t('design.sourceRows')}</span><strong className={!stats ? 'is-missing' : ''}>{stats ? formatNumber(stats.settlements_loaded, 0) : unknownCount}</strong></div>
          {settlements.length ? <div className="product-register-sample">{settlements.slice(0, 2).map(row => <button key={row.id} onClick={() => onPage('settlements', `?settlement=${encodeURIComponent(row.id)}`)}><span>{row.source_name === null ? t('explore.nameMissing') : row.name}<small>{row.source_id} · {row.administrative_area || t('Ward not supplied')}</small></span><ArrowRight size={14} /></button>)}</div> : <p className="product-empty">{t('dashboard.noData')}</p>}
          <WardDistribution settlements={settlements} />
          <button className="us-button product-card-action" onClick={() => onPage('settlements')}>{t('design.browseRegister')}<ArrowRight size={15} /></button>
        </Panel>}
        {(scope === 'all' || scope === 'issues') && <Panel className="product-issues-card product-data-card">
          <div className="product-card-source"><MessageSquarePlus size={16} /><span>{t('design.issueSource')}</span><span className="product-source-dot" /></div>
          <h2>{t('dashboard.recentIssues')}</h2><p className="product-card-description">{t('dashboard.selfReported')}</p>
          {issueError ? <div role="alert"><p>{errorText(issueError)}</p><button className="us-button" onClick={() => setRetry(value => value + 1)}>{t('Retry')}</button></div> : !issues ? <p role="status">{t('Loading…')}</p> : issues.recent.length ? <ul className="product-recent-issues">{issues.recent.map(issue => <li key={issue.id}><button onClick={() => onPage('report-issue', `?issue=${encodeURIComponent(issue.id)}`)}><span><b>{t(`issues.category.${issue.category}`)}</b><small>{issue.id} · {formatDate(issue.report_date)}</small></span><Tag tone="blue">{t(`issues.status.${issue.status}`)}</Tag></button><p>{issue.description}</p></li>)}</ul> : <div className="product-empty product-issues-empty"><MessageSquarePlus size={37} strokeWidth={1} /><b>{t('dashboard.noIssues')}</b><p>{t('dashboard.noIssuesNote')}</p></div>}
          <button className="us-button product-card-action" onClick={() => onPage('report-issue')}>{t('nav.issue')}<ArrowRight size={15} /></button>
        </Panel>}
      </div>
    </section>
    <section className="product-source-summary" aria-label={t('dashboard.sourceSummary')}><div><span>{t('Mapped context objects')}</span><strong>{metadata ? formatNumber(metadata.snapshot.mapped_objects_count, 0) : '—'}</strong></div><div><span>{t('Census 2011 observations')}</span><strong>{metadata ? formatNumber(metadata.snapshot.historical_observation_count ?? 0, 0) : '—'}</strong></div><p>{t('dashboard.sourceNote')}</p><button className="us-button" onClick={() => onPage('projects')}>{t('nav.projects')}<ArrowRight size={15} /></button></section>
    <p className="product-data-note">{t(registered ? (metadata?.snapshot.historical_observation_count ? 'dashboard.freshness' : 'dashboard.registerFreshness') : 'dashboard.referenceFreshness')}{metadata?.snapshot.built_at && <> {t('dashboard.snapshotBuilt', { date: formatDate(metadata.snapshot.built_at) })}</>}</p>
  </>
}
