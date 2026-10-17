import { sessionStore } from '../lib/storage'
import { useEffect, useState } from 'react'
import { CheckCircle2, KeyRound, RefreshCw } from 'lucide-react'
import { useI18n } from '../i18n'
import { Complaint, dateTime, health, ObservationInput, ServiceRecord } from '../lib/api'
import { Badge, Note, Panel } from './Shared'

export const serviceNames = ['water', 'sanitation', 'power', 'waste', 'health']
export function blankObservation(service = 'water', synthetic = true): ObservationInput {
  return { service, value: 0, observed_at: new Date().toISOString(), source_label: '', evidence_url: null, notes: '', synthetic, consent: false }
}
function localDate(value: string) {
  const date = new Date(value)
  return Number.isFinite(date.getTime()) ? new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16) : ''
}
export function ObservationFields({ input, onChange, serviceLocked = false, scopeLocked = false }: { input: ObservationInput; onChange: (input: ObservationInput) => void; serviceLocked?: boolean; scopeLocked?: boolean }) {
  const { t } = useI18n()
  const set = <K extends keyof ObservationInput>(key: K, value: ObservationInput[K]) => onChange({ ...input, [key]: value })
  const units: Record<string, string> = { water: 'h/day', sanitation: '/100 people', power: 'h/week', waste: '/week', health: '0 / 1' }
  const maximum: Record<string, number> = { water: 24, sanitation: 100, power: 168, waste: 21, health: 1 }
  return <div className="form-grid">
    <label className="field"><span>{t('service')}</span><select aria-label={t('service')} value={input.service} disabled={serviceLocked} onChange={e => onChange({ ...input, service: e.target.value, value: 0 })}>{serviceNames.map(name => <option value={name} key={name}>{t(`${name}Label`)}</option>)}</select></label>
    <label className="field"><span>{t('measurement')} ({units[input.service]})</span><input type="number" min={0} max={maximum[input.service]} step={input.service === 'health' ? 1 : .1} required value={input.value} onChange={e => set('value', Number(e.target.value))} /></label>
    <label className="field"><span>{t('observedAt')}</span><input type="datetime-local" required value={localDate(input.observed_at)} max={localDate(new Date().toISOString())} onChange={e => set('observed_at', e.target.value ? new Date(e.target.value).toISOString() : '')} /></label>
    <label className="field"><span>{t('sourceLabel')}</span><input required minLength={3} maxLength={200} placeholder={t('sourcePlaceholder')} value={input.source_label} onChange={e => set('source_label', e.target.value)} /></label>
    <label className="field full-field"><span>{t('evidenceUrl')}</span><input type="url" value={input.evidence_url || ''} placeholder="https://" onChange={e => set('evidence_url', e.target.value || null)} /></label>
    <label className="field full-field"><span>{t('evidence')}</span><textarea required minLength={3} maxLength={2000} value={input.notes} placeholder={t('notesPlaceholder')} onChange={e => set('notes', e.target.value)} /></label>
    {!scopeLocked && <label className="field"><span>{t('dataScope')}</span><select aria-label={t('dataScope')} value={input.synthetic ? 'demo' : 'real'} onChange={e => set('synthetic', e.target.value === 'demo')}><option value="demo">{t('demoReport')}</option><option value="real">{t('realReport')}</option></select></label>}
    {!input.synthetic && <label className="check-field full-field"><input type="checkbox" checked={input.consent} onChange={e => set('consent', e.target.checked)} required /><span>{t('consentEvidence')}</span></label>}
  </div>
}
export function ComplaintHistory({ complaint }: { complaint: Complaint }) {
  const { t } = useI18n()
  const label = (action: string) => ({ assign: t('assign'), start: t('startWork'), complete: t('submitRepair'), escalate: t('escalate') }[action] || t(`status.${action}`))
  return <ol className="record-history">{complaint.history.map((event, index) => <li key={`${event.at}-${index}`}><span className="history-marker" /><div><b>{label(event.action)}</b><small>{dateTime(event.at)} · {event.actor}</small><p>{event.notes}</p></div></li>)}</ol>
}
export function ServiceRecordView({ record }: { record: ServiceRecord }) {
  const { t } = useI18n()
  return <>
    <div className="service-record-grid">{Object.entries(record.services).map(([name, service]) => <section className={`service-record-card ${service.status}`} key={name}>
      <div className="service-card-title"><h3>{t(`${name}Label`)}</h3><Badge tone={service.status === 'compliant' ? 'teal' : service.status === 'breach' ? 'red' : 'amber'}>{t(`serviceStatus.${service.status}`)}</Badge></div>
      <strong className="service-reading">{service.value === null ? '—' : service.value.toLocaleString()}<small>{service.unit}</small></strong>
      <p>{t('target')}: {service.target_direction === 'at_least' ? '≥' : '≤'} {service.target} {service.unit}</p>
      <p className="standard-source">{service.standard_source}{service.standard_url && <> · <a href={service.standard_url} target="_blank" rel="noreferrer">{t('policySource')} ↗</a></>}</p><dl className="record-meta"><div><dt>{t('verification')}</dt><dd>{t(`verification.${service.verification}`)}{service.synthetic && service.verification !== 'synthetic' && <small>{t('demoReport')}</small>}</dd></div><div><dt>{t('source')}</dt><dd>{service.source_label}</dd></div><div><dt>{t('observedAt')}</dt><dd>{service.observed_at ? dateTime(service.observed_at) : t('sourceDateUnknown')}</dd></div><div><dt>{t('department')}</dt><dd>{service.department}</dd></div></dl>
      {service.source_url && <a href={service.source_url} target="_blank" rel="noreferrer">{t('evidence')} ↗</a>}
      <details className="observation-history"><summary>{t('observationHistory')} ({service.history.length})</summary>{!service.history.length && <p>{t('noObservations')}</p>}{service.history.map(observation => <article key={observation.observation_id}><b>{observation.value} {service.unit}</b><Badge tone={observation.verification === 'disputed' ? 'red' : 'amber'}>{t(`verification.${observation.verification}`)}</Badge><small>{dateTime(observation.observed_at)} · {observation.source_label}</small><p>{observation.notes}</p><small>{observation.synthetic ? t('demoReport') : t('realReport')}</small></article>)}</details>
    </section>)}</div>
    <Note>{t(Object.values(record.services).some(s => s.standard_synthetic !== false) ? 'localTargets' : 'approvedTargets')} {t('staleHelp')}</Note>
  </>
}
export function OfficerAccess({ onUnlock }: { onUnlock: () => void }) {
  const { t } = useI18n()
  const [key, setKey] = useState(() => sessionStore.getItem('nagarseva-officer-key') || '')
  const [required, setRequired] = useState<boolean | null>(null)
  useEffect(() => { health().then(value => setRequired(value.officer_auth_required)).catch(() => setRequired(null)) }, [])
  return <details className="officer-access" open={required === true && !key}><summary><KeyRound size={15} />{t('officerAccess')}</summary>{required === false && <p>{t('localDemoAccess')}</p>}<form className="inline-form" onSubmit={e => { e.preventDefault(); sessionStore.setItem('nagarseva-officer-key', key); onUnlock() }}><label className="field"><span>{t('officerKey')}</span><input type="password" autoComplete="off" value={key} onChange={e => setKey(e.target.value)} /></label><button className="button outline" type="submit">{t('unlock')}</button></form></details>
}
export function ErrorNote({ message }: { message: string }) { return message ? <div className="error-note" role="alert">{message}</div> : null }
export function EmptyState({ children }: { children: React.ReactNode }) { return <div className="empty-state"><CheckCircle2 size={25} /><p>{children}</p></div> }
export function RefreshButton({ onClick, disabled = false }: { onClick: () => void; disabled?: boolean }) { const { t } = useI18n(); return <button className="button outline" onClick={onClick} disabled={disabled}><RefreshCw size={15} />{t('refresh')}</button> }
