import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Field, Panel, Tag } from './PlanningPages'
import { dataApi, exportPublicCsv } from './publicClient'
import type { PublicSettlement } from './publicClient'

const INDICATORS = { water: 'W · Water-service deficit', sanitation: 'S · Sanitation and drainage deficit', housing: 'H · Housing-condition deficit', access: 'A · Essential-amenity access deficit', risk: 'R · Environmental or infrastructure risk' } as const

type Indicator = keyof typeof INDICATORS
type Survey = { survey_id: string; settlement_id: string; observed_at: string; water_hours_per_day: number | null; functional_toilets_observed: number | null; blocked_drain_segments_observed: number | null; sanitation_condition: string; drainage_condition: string; protocol_reference: string; verification_status: string; collection_platform: string }
type Observation = { id: string; settlement_id: string | null; indicator_type: string; value: number | null; unit: string; reference_year: number; observation_date: string | null; source: string; verification_status: string; method: string }
type SurveyDraft = { id: string; at: string; inspector: string; platform: string; protocol: string; water: string; toilets: string; drains: string; sanitation: string; drainage: string; note: string; latitude: string; longitude: string; evidence: string; consent: boolean }
type IndexDraft = { indicator: Indicator; value: string; at: string; source: string; method: string; inspector: string; reviewer: string; evidence: string; approvedMethod: boolean; evidencePermission: boolean; reviewed: boolean }
const newSurvey = (): SurveyDraft => ({ id: '', at: '', inspector: '', platform: 'authorized_manual', protocol: '', water: '', toilets: '', drains: '', sanitation: 'not_observed', drainage: 'not_observed', note: '', latitude: '', longitude: '', evidence: '', consent: false })
const newIndex = (): IndexDraft => ({ indicator: 'water', value: '', at: '', source: '', method: '', inspector: '', reviewer: '', evidence: '', approvedMethod: false, evidencePermission: false, reviewed: false })

function observationTime(value: string) {
  const text = value.trim(), time = Date.parse(text)
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/i.test(text) || !Number.isFinite(time)) throw new Error('Enter a complete observation date and time with a timezone, such as 2026-10-18T09:30:00+05:30.')
  if (time > Date.now() + 300000) throw new Error('The observation time cannot be in the future.')
  return text
}
function optionalNumber(value: string, label: string, min: number, max: number, integer = false) {
  if (!value.trim()) return null
  const number = Number(value)
  if (!Number.isFinite(number) || number < min || number > max || (integer && !Number.isInteger(number))) throw new Error(`${label} must be ${integer ? 'a whole number' : 'a number'} between ${min} and ${max}, or left blank.`)
  return number
}
function evidenceUrl(value: string) {
  const text = value.trim()
  if (!text) return null
  try { const url = new URL(text); if (url.protocol !== 'https:' || !url.hostname || url.username || url.password || /\s/.test(text)) throw new Error(); return text } catch { throw new Error('Evidence must be a valid HTTPS reference in an approved store, without embedded credentials.') }
}
const showValue = (value: number | null | undefined) => value === null || value === undefined ? 'Not observed' : String(value)
const statusLabel = (value: string) => value === 'field_verified' ? 'Field-reviewed · user-recorded' : value === 'reported' ? 'Reported · unverified' : value.replaceAll('_', ' ')

export default function PublicFieldCollection({ selected, officerKey, onChanged }: { selected: PublicSettlement; officerKey: string; onChanged: () => void }) {
  const [surveys, setSurveys] = useState<Survey[]>([]), [observations, setObservations] = useState<Observation[]>([])
  const [observationTotal, setObservationTotal] = useState(0), [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState(''), [success, setSuccess] = useState('')
  const [survey, setSurvey] = useState<SurveyDraft>(newSurvey), [index, setIndex] = useState<IndexDraft>(newIndex)
  const requestVersion = useRef(0), currentSelection = useRef(selected.id)
  currentSelection.current = selected.id
  const load = useCallback(async () => {
    const version = ++requestVersion.current
    setLoading(true); setError('')
    const query = encodeURIComponent(selected.id)
    const [surveyResult, indicatorResult] = await Promise.allSettled([
      officerKey ? dataApi<{ items: Survey[] }>(`/surveys?settlement_id=${query}`, undefined, officerKey) : Promise.resolve({ items: [] as Survey[] }),
      dataApi<{ items: Observation[]; total: number }>(`/indicators?settlement_id=${query}&page_size=1000`),
    ])
    if (version !== requestVersion.current || currentSelection.current !== selected.id) return
    const errors: string[] = []
    if (surveyResult.status === 'fulfilled') setSurveys(surveyResult.value.items.filter(row => row.settlement_id === selected.id))
    else { setSurveys([]); errors.push(`Survey records: ${surveyResult.reason instanceof Error ? surveyResult.reason.message : 'request failed'}`) }
    if (indicatorResult.status === 'fulfilled') { setObservations(indicatorResult.value.items); setObservationTotal(indicatorResult.value.total) }
    else { setObservations([]); setObservationTotal(0); errors.push(`Observations: ${indicatorResult.reason instanceof Error ? indicatorResult.reason.message : 'request failed'}`) }
    setError(errors.join(' ')); setLoading(false)
  }, [selected.id, officerKey])
  useEffect(() => {
    setSurveys([]); setObservations([]); setObservationTotal(0); setSuccess(''); setSurvey(newSurvey()); setIndex(newIndex())
    void load()
    return () => { requestVersion.current++ }
  }, [load])
  function surveyField<K extends keyof SurveyDraft>(key: K, value: SurveyDraft[K]) { setSurvey(previous => ({ ...previous, [key]: value })) }
  function indexField<K extends keyof IndexDraft>(key: K, value: IndexDraft[K]) { setIndex(previous => ({ ...previous, [key]: value })) }
  async function mutate(operation: () => Promise<unknown>, message: string) {
    if (busy) return
    const settlementId = selected.id
    setBusy(true); setError(''); setSuccess('')
    try {
      if (!officerKey) throw new Error('Enter the configured officer key before saving field records.')
      await operation(); onChanged()
      if (currentSelection.current === settlementId) { await load(); setSuccess(message) }
    } catch (caught) { if (currentSelection.current === settlementId) setError(caught instanceof Error ? caught.message : 'The record could not be saved. Retry after checking the API.') }
    finally { setBusy(false) }
  }
  async function saveSurvey(event: FormEvent) {
    event.preventDefault()
    await mutate(async () => {
      if (!/^[a-zA-Z0-9:_-]{2,100}$/.test(survey.id.trim())) throw new Error('Use a unique survey ID of 2–100 letters, numbers, colons, underscores or hyphens.')
      if (surveys.some(row => row.survey_id === survey.id.trim())) throw new Error('This survey ID is already recorded. Existing observations are immutable; choose a new ID for a new visit.')
      const latitude = optionalNumber(survey.latitude, 'Latitude', -90, 90), longitude = optionalNumber(survey.longitude, 'Longitude', -180, 180)
      if ((latitude === null) !== (longitude === null)) throw new Error('Supply both coarse GPS coordinates, or leave both blank.')
      if ([latitude, longitude].some(value => value !== null && Math.abs(value - Math.round(value * 1000) / 1000) > 1e-9)) throw new Error('GPS coordinates may have at most three decimal places. Do not enter household locations.')
      const evidence = evidenceUrl(survey.evidence)
      if (evidence && !survey.consent) throw new Error('Confirm consent and approval for the evidence store before recording its reference.')
      await dataApi('/surveys', { survey_id: survey.id.trim(), settlement_id: selected.id, observed_at: observationTime(survey.at),
        water_hours_per_day: optionalNumber(survey.water, 'Water hours', 0, 24), functional_toilets_observed: optionalNumber(survey.toilets, 'Functional toilets', 0, 10000, true), blocked_drain_segments_observed: optionalNumber(survey.drains, 'Blocked drain segments', 0, 10000, true),
        sanitation_condition: survey.sanitation, drainage_condition: survey.drainage, housing_or_infrastructure_observation: survey.note.trim(), gps_latitude: latitude, gps_longitude: longitude,
        evidence_reference: evidence, evidence_consent: survey.consent, inspector_reference: survey.inspector.trim(), verification_status: 'reported', collection_platform: survey.platform, protocol_reference: survey.protocol.trim(),
      }, officerKey)
      if (currentSelection.current === selected.id) setSurvey(newSurvey())
    }, 'Survey saved as reported. Raw observations do not create a deficit score or verify a service.')
  }
  async function saveIndex(event: FormEvent) {
    event.preventDefault()
    await mutate(async () => {
      const value = optionalNumber(index.value, 'Deficit index', 0, 100)
      if (value === null) throw new Error('A reviewed deficit index needs an explicitly supplied value; a blank is not zero.')
      if (!index.approvedMethod) throw new Error('Confirm that an approved normalization protocol supports this user-supplied index.')
      const evidence = evidenceUrl(index.evidence)
      if (!evidence || !index.evidencePermission) throw new Error('Provide an approved HTTPS evidence reference and confirm permission to use it.')
      if (index.reviewed && (index.reviewer.trim().length < 2 || index.reviewer.trim().toLocaleLowerCase() === index.inspector.trim().toLocaleLowerCase())) throw new Error('A field-reviewed index needs a reviewer reference different from the inspector reference.')
      const observedAt = observationTime(index.at)
      await dataApi('/indicators', { settlement_id: selected.id, geographic_unit_id: null, indicator_type: index.indicator, value, unit: 'deficit_0_100', reference_year: Number(observedAt.slice(0, 4)), observation_date: observedAt, geographic_resolution: 'settlement', source: index.source.trim(),
        verification_status: index.reviewed ? 'field_verified' : 'reported', inspector_reference: index.inspector.trim(), reviewer_reference: index.reviewed ? index.reviewer.trim() : null, method: index.method.trim(), evidence_reference: evidence,
      }, officerKey)
      if (currentSelection.current === selected.id) setIndex(newIndex())
    }, index.reviewed ? 'Index saved with a user-recorded field review. Source, date and completeness rules still determine ranking eligibility.' : 'Index saved as reported and excluded from reviewed prioritization inputs.')
  }
  return <Panel title="Optional field collection" note={`Selected source record: ${selected.source_id}. No personal beneficiary details are collected.`}>
    <p className="us-small">Spot readings remain unverified reports. Water-point mapping, toilet counts and one visit do not establish household coverage, reliability or a normalized deficit. Inspector and reviewer references are user supplied; this prototype does not authenticate government identity.</p>
    {error && <div className="us-alert" role="alert">{error}<button type="button" className="us-button" disabled={busy || loading} onClick={() => void load()}>Retry field records</button></div>}
    {success && <div className="us-success" role="status">{success}</div>}
    {loading && <p role="status">Loading field records…</p>}
    {!officerKey && <p className="us-note">Enter the configured officer key to view survey details, export them or record an authorized visit.</p>}
    <fieldset className="public-fieldset" disabled={!officerKey || busy}>
      <details><summary>Record an authorized field visit</summary>
        <form onSubmit={saveSurvey} aria-label="Field survey form">
          <p className="us-small">Use the approved geographic unit and survey protocol. Leave measurements blank when unobserved. Records are immutable; revisits need a new survey ID.</p>
          <div className="us-form-grid three">
            <Field label="Unique survey ID" hint="Your survey identifier, not an invented government ID."><input aria-label="Survey ID" required pattern="[a-zA-Z0-9:_-]{2,100}" maxLength={100} value={survey.id} onChange={event => surveyField('id', event.target.value)} /></Field>
            <Field label="Observation time with timezone"><input aria-label="Survey observation time" required value={survey.at} placeholder="2026-10-18T09:30:00+05:30" onChange={event => surveyField('at', event.target.value)} /></Field>
            <Field label="Pseudonymous inspector reference"><input aria-label="Survey inspector reference" required minLength={2} maxLength={80} value={survey.inspector} onChange={event => surveyField('inspector', event.target.value)} /></Field>
          </div>
          <div className="us-form-grid"><Field label="Collection platform"><select aria-label="Survey collection platform" value={survey.platform} onChange={event => surveyField('platform', event.target.value)}><option value="authorized_manual">Authorized manual observation</option><option value="KoboToolbox">KoboToolbox import reference</option><option value="ODK">ODK import reference</option></select></Field><Field label="Approved survey protocol reference"><input aria-label="Survey protocol" required minLength={5} maxLength={2000} value={survey.protocol} onChange={event => surveyField('protocol', event.target.value)} /></Field></div>
          <div className="us-form-grid three">
            <Field label="Observed water hours / day"><input aria-label="Observed water hours" type="number" min={0} max={24} step="any" value={survey.water} onChange={event => surveyField('water', event.target.value)} placeholder="Not observed" /></Field>
            <Field label="Functional toilets observed"><input aria-label="Functional toilets observed" type="number" min={0} max={10000} step={1} value={survey.toilets} onChange={event => surveyField('toilets', event.target.value)} placeholder="Not observed" /></Field>
            <Field label="Blocked drain segments observed"><input aria-label="Blocked drain segments observed" type="number" min={0} max={10000} step={1} value={survey.drains} onChange={event => surveyField('drains', event.target.value)} placeholder="Not observed" /></Field>
          </div>
          <div className="us-form-grid"><Field label="Sanitation observation"><select aria-label="Sanitation observation" value={survey.sanitation} onChange={event => surveyField('sanitation', event.target.value)}><option value="not_observed">Not observed</option><option value="functioning">Functioning</option><option value="partly_functioning">Partly functioning</option><option value="not_functioning">Not functioning</option></select></Field><Field label="Drainage observation"><select aria-label="Drainage observation" value={survey.drainage} onChange={event => surveyField('drainage', event.target.value)}><option value="not_observed">Not observed</option><option value="clear">Clear</option><option value="partly_blocked">Partly blocked</option><option value="blocked">Blocked</option></select></Field></div>
          <Field label="Housing or infrastructure observation" hint="Optional. Exclude names, household addresses and other personal details."><textarea aria-label="Infrastructure observation" maxLength={2000} value={survey.note} onChange={event => surveyField('note', event.target.value)} /></Field>
          <div className="us-form-grid"><Field label="Coarse latitude (optional)"><input aria-label="Survey latitude" type="number" min={-90} max={90} step="0.001" value={survey.latitude} onChange={event => surveyField('latitude', event.target.value)} /></Field><Field label="Coarse longitude (optional)" hint="Both coordinates or neither; at most three decimal places, about 100 m."><input aria-label="Survey longitude" type="number" min={-180} max={180} step="0.001" value={survey.longitude} onChange={event => surveyField('longitude', event.target.value)} /></Field></div>
          <Field label="Approved HTTPS evidence reference (optional)"><input aria-label="Survey evidence reference" type="url" value={survey.evidence} maxLength={2000} onChange={event => surveyField('evidence', event.target.value)} placeholder="https://approved-store.example/evidence" /></Field>
          <label className="us-check"><input aria-label="Survey evidence consent" type="checkbox" checked={survey.consent} onChange={event => surveyField('consent', event.target.checked)} />Consent and approved storage arrangements permit this evidence reference; personal details have been removed.</label>
          <button className="us-button primary" type="submit">{busy ? 'Saving…' : 'Save reported survey'}</button>
        </form>
      </details>
      <details><summary>Record a separately reviewed deficit index</summary>
        <form onSubmit={saveIndex} aria-label="Reviewed deficit index form">
          <p className="us-note">Enter an independently calculated 0–100 deficit index supported by an approved normalization method. Higher means greater need. This form does not convert raw survey readings into scores. Default prioritization weights are prototype assumptions.</p>
          <div className="us-form-grid three"><Field label="Deficit indicator"><select aria-label="Reviewed deficit indicator" value={index.indicator} onChange={event => indexField('indicator', event.target.value as Indicator)}>{Object.entries(INDICATORS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field><Field label="User-supplied deficit index (0–100)"><input aria-label="Reviewed deficit value" required type="number" min={0} max={100} step="any" value={index.value} onChange={event => indexField('value', event.target.value)} /></Field><Field label="Observation time with timezone"><input aria-label="Deficit observation time" required value={index.at} placeholder="2026-10-18T09:30:00+05:30" onChange={event => indexField('at', event.target.value)} /></Field></div>
          <Field label="Observation source"><input aria-label="Deficit source" required minLength={5} maxLength={2000} value={index.source} onChange={event => indexField('source', event.target.value)} /></Field>
          <Field label="Approved normalization method and protocol" hint="Describe the geographic scope, denominator, calculation and protocol/version; a spot measurement alone is insufficient."><textarea aria-label="Deficit normalization method" required minLength={10} maxLength={2000} value={index.method} onChange={event => indexField('method', event.target.value)} /></Field>
          <label className="us-check"><input aria-label="Normalization protocol approved" required type="checkbox" checked={index.approvedMethod} onChange={event => indexField('approvedMethod', event.target.checked)} />An approved normalization protocol supports the supplied value at this settlement's geographic resolution.</label>
          <div className="us-form-grid"><Field label="Inspector reference"><input aria-label="Deficit inspector reference" required minLength={2} maxLength={80} value={index.inspector} onChange={event => indexField('inspector', event.target.value)} /></Field><Field label="Independent reviewer reference" hint="Required for a field-reviewed record; must differ from the inspector."><input aria-label="Deficit reviewer reference" required={index.reviewed} minLength={2} maxLength={80} value={index.reviewer} onChange={event => indexField('reviewer', event.target.value)} /></Field></div>
          <Field label="Approved HTTPS supporting evidence"><input aria-label="Deficit evidence reference" required type="url" maxLength={2000} value={index.evidence} onChange={event => indexField('evidence', event.target.value)} placeholder="https://approved-store.example/review" /></Field>
          <label className="us-check"><input aria-label="Deficit evidence permission" required type="checkbox" checked={index.evidencePermission} onChange={event => indexField('evidencePermission', event.target.checked)} />Permission and approved storage arrangements allow this evidence reference.</label>
          <label className="us-check"><input aria-label="Confirm independent deficit review" type="checkbox" checked={index.reviewed} onChange={event => indexField('reviewed', event.target.checked)} />The distinct reviewer has checked the method, evidence and value. Record this as field reviewed. These references are user recorded and are not authenticated government identities.</label>
          <button className="us-button primary" type="submit">{busy ? 'Saving…' : index.reviewed ? 'Save user-recorded reviewed index' : 'Save reported index'}</button>
        </form>
      </details>
      <div className="us-button-row"><button className="us-button" type="button" onClick={() => { setError(''); void exportPublicCsv('surveys', officerKey).catch(caught => setError(caught instanceof Error ? caught.message : 'Survey export failed.')) }}>Export authorized survey CSV</button></div>
    </fieldset>
    <details><summary>Survey records for this source record ({surveys.length})</summary>{!officerKey ? <p>Officer access is required for survey details.</p> : !surveys.length ? <p className="us-empty">No field surveys recorded for this source record.</p> : <div className="us-table-wrap"><table><thead><tr><th>Survey / status</th><th>Observation date</th><th>Spot readings</th><th>Conditions / protocol</th></tr></thead><tbody>{surveys.map(row => <tr key={row.survey_id}><td><b>{row.survey_id}</b><br /><Tag tone="amber">{statusLabel(row.verification_status)}</Tag></td><td>{row.observed_at}</td><td>Water: {showValue(row.water_hours_per_day)} hours/day<br />Functional toilets: {showValue(row.functional_toilets_observed)}<br />Blocked segments: {showValue(row.blocked_drain_segments_observed)}</td><td>{row.sanitation_condition.replaceAll('_', ' ')} / {row.drainage_condition.replaceAll('_', ' ')}<br />{row.protocol_reference}<br />{row.collection_platform}</td></tr>)}</tbody></table></div>}</details>
    <details><summary>Recorded indicator observations ({observationTotal})</summary><p className="us-small">Reported values are excluded from reviewed ranking. Historical aggregates keep their original year and resolution. Reviewed entries must also meet the current-data and completeness rules.</p>{!observations.length ? <p className="us-empty">No indicator observations recorded for this source record.</p> : <div className="us-table-wrap"><table><thead><tr><th>Indicator / value</th><th>Review status</th><th>Source date / reference year</th><th>Source / method</th></tr></thead><tbody>{observations.map(row => <tr key={row.id}><td>{row.indicator_type.replaceAll('_', ' ')}<br /><b>{row.value === null ? 'Missing' : row.value}</b> {row.unit}</td><td><Tag tone={row.verification_status === 'field_verified' ? 'green' : 'amber'}>{statusLabel(row.verification_status)}</Tag></td><td>{row.observation_date || 'Observation date unavailable'}<br />Reference year: {row.reference_year}</td><td>{row.source}<br />{row.method}</td></tr>)}</tbody></table></div>}{observationTotal > observations.length && <p>Showing the first {observations.length} of {observationTotal} observations. Export or query the API for the complete record.</p>}</details>
  </Panel>
}
