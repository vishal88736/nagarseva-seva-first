import { useEffect, useState } from 'react'
import { CheckCircle2, Gauge } from 'lucide-react'
import { Metric, Panel, SectionTitle } from '../components/Shared'
import { ErrorNote, RefreshButton, ServiceRecordView } from '../components/Records'
import { useI18n } from '../i18n'
import { BenchmarkReferences } from '../components/PublicContext'
import { getServiceRecord, number, Pocket, ServiceRecord, Summary } from '../lib/api'

export function Assurance({ pocket, summary, revision, onSelect }: { pocket: Pocket; summary: Summary; revision: number; onSelect: (id: string) => void }) {
  const { t } = useI18n()
  const [record, setRecord] = useState<ServiceRecord | null>(null), [error, setError] = useState('')
  const load = () => getServiceRecord(pocket).then(value => { setRecord(value); setError('') }).catch(e => setError(e.message))
  useEffect(() => { void load() }, [pocket.pocket_id, revision])
  const wards = [...summary.wards].sort((a, b) => (b.compliance || 0) - (a.compliance || 0)).map(w => ({ ...w, label: `${w.city} / ${w.ward}` }))
  return <div className="page-pad"><SectionTitle eyebrow={t('postHandover')} title={t('assuranceTitle')} description={t('assuranceDesc')} action={<RefreshButton onClick={() => { void load() }} />} /><ErrorNote message={error} />
    <div className="admin-metrics"><Metric label={t('mmrAverage')} value={summary.avg_assurance_index === null ? '—' : summary.avg_assurance_index.toFixed(1)} note={t('dataSynthetic')} icon={<Gauge size={18} />} /><Metric label={t('verifiedClosures')} value={number(summary.resident_verified_closures)} note={t('fromStoredReports')} icon={<CheckCircle2 size={18} />} /><Metric label={t('verifiedField')} value={number(summary.field_verified_services)} note={`${t('realObservations')}: ${summary.real_observations}`} icon={<CheckCircle2 size={18} />} /><Metric label={t('withinSla')} value={summary.within_sla_pct === null ? '—' : `${summary.within_sla_pct}%`} note={t('fromStoredReports')} icon={<CheckCircle2 size={18} />} /></div>
    <Panel title={`${pocket.pocket_id} · ${t('serviceScorecards')}`} subtitle={pocket.ward} action={<button className="text-button" onClick={() => onSelect(pocket.pocket_id)}>{t('viewPocket')} →</button>}>
      {record ? <ServiceRecordView record={record} /> : <p role="status">{t('loading')}</p>}
    </Panel>
    <BenchmarkReferences />
    <Panel title={t('wardTargetBoard')} subtitle={t('wardTargetDesc')} className="ward-board"><div className="ward-target-list">{wards.map(ward => <div className="ward-target-row" key={ward.label}><span>{ward.label}</span><div className="ward-target-track" role="progressbar" aria-label={ward.label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={ward.compliance ?? undefined}><i style={{ width: `${ward.compliance ?? 0}%` }} /></div><strong>{ward.compliance === null ? '—' : `${ward.compliance.toFixed(1)}%`}</strong></div>)}</div></Panel>
  </div>
}
