import { localStore } from '../lib/storage'
import { OfficialChannels } from '../components/PublicContext'
import { Download, Mic, Send, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Badge, Note, Panel, SectionTitle } from '../components/Shared'
import { ComplaintHistory, EmptyState, ErrorNote, RefreshButton } from '../components/Records'
import { Language, useI18n } from '../i18n'
import { checkEligibility, Classification, classify, Complaint, confirmComplaint, dateTime, downloadJson, Eligibility, getMyComplaints, Pocket, Receipt, saveReceipt, submitComplaint, trackComplaint } from '../lib/api'

type Answer = 'unknown' | 'yes' | 'no'
const answer = (value: Answer) => value === 'unknown' ? null : value === 'yes'
export function Resident({ pocket, revision }: { pocket: Pocket; revision: number }) {
  const { t, language } = useI18n()
  const draftKey = `nagarseva-draft-${pocket.pocket_id}`
  const [tab, setTab] = useState<'eligibility' | 'grievance' | 'status'>('grievance')
  const [text, setText] = useState(() => { try { return localStore.getItem(draftKey) || '' } catch { return '' } })
  const [complaintLanguage, setComplaintLanguage] = useState<Language>(language), [synthetic, setSynthetic] = useState(true), [consent, setConsent] = useState(false)
  const [classification, setClassification] = useState<Classification | null>(null), [complaints, setComplaints] = useState<Complaint[]>([]), [receipts, setReceipts] = useState<Receipt[]>([])
  const [newReceipt, setNewReceipt] = useState<Receipt | null>(null), [unavailable, setUnavailable] = useState(0), [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState('')
  const [restoreId, setRestoreId] = useState(''), [restoreToken, setRestoreToken] = useState(''), [feedback, setFeedback] = useState<Record<string, string>>({})
  const [income, setIncome] = useState(() => Math.round(pocket.avg_household_income_inr || 18000)), [eligibility, setEligibility] = useState<Eligibility | null>(null)
  const [answers, setAnswers] = useState<Record<string, Answer>>({ urban_resident: 'unknown', owns_pucca_house: 'unknown', received_housing_benefit_last_20_years: 'unknown', owns_buildable_land: 'unknown' })
  const [wantsRental, setWantsRental] = useState(false), [loan, setLoan] = useState(''), [property, setProperty] = useState(''), [carpet, setCarpet] = useState('')
  const refresh = async () => { const data = await getMyComplaints(); setComplaints(data.items); setReceipts(data.receipts); setUnavailable(data.unavailable) }
  useEffect(() => { refresh().catch(e => setError(e.message)) }, [revision])
  useEffect(() => { setComplaintLanguage(language) }, [language])
  useEffect(() => {
    let current = true; setClassification(null)
    if (text.trim().length < 3) return
    const timer = window.setTimeout(() => { classify(text, complaintLanguage).then(value => { if (current) setClassification(value) }).catch(e => { if (current) setError(e.message) }) }, 350)
    return () => { current = false; window.clearTimeout(timer) }
  }, [text, complaintLanguage])
  const run = async (work: () => Promise<void>) => { setBusy(true); setError(''); setNotice(''); try { await work() } catch (e) { setError((e as Error).message) } finally { setBusy(false) } }
  const send = () => run(async () => {
    const result = await submitComplaint(text.trim(), complaintLanguage, pocket.pocket_id, synthetic, consent)
    setNewReceipt({ complaint_id: result.complaint_id, receipt_token: result.receipt_token }); setComplaints(old => [result, ...old]); setText(''); localStore.removeItem(draftKey)
    setNotice(t('reportSaved')); setTab('status'); await refresh()
  })
  const confirm = (id: string, resolved: boolean) => run(async () => { await confirmComplaint(id, resolved, feedback[id] || ''); await refresh() })
  const screen = () => run(async () => {
    setEligibility(await checkEligibility({ monthly_income_inr: income, family_size: 4, ...Object.fromEntries(Object.entries(answers).map(([key, value]) => [key, answer(value)])), wants_rental: wantsRental,
      loan_amount_inr: loan ? Number(loan) : null, property_value_inr: property ? Number(property) : null, carpet_area_sqm: carpet ? Number(carpet) : null }))
  })
  const voice = () => {
    type Recognition = { lang: string; start: () => void; onresult: (event: { results: { 0: { transcript: string } }[] }) => void; onerror: () => void }
    type Ctor = new () => Recognition
    const Speech = (window as typeof window & { SpeechRecognition?: Ctor; webkitSpeechRecognition?: Ctor }).SpeechRecognition || (window as typeof window & { webkitSpeechRecognition?: Ctor }).webkitSpeechRecognition
    if (!Speech) { setNotice(t('voiceUnavailable')); return }
    const recognition = new Speech(); recognition.lang = complaintLanguage === 'hi' ? 'hi-IN' : complaintLanguage === 'mr' ? 'mr-IN' : 'en-IN'
    recognition.onresult = event => setText(event.results[0][0].transcript); recognition.onerror = () => setNotice(t('voiceError'))
    try { recognition.start() } catch { setNotice(t('voiceError')) }
  }
  const questions = [['urban_resident', 'urbanResident'], ['owns_pucca_house', 'ownsHouse'], ['received_housing_benefit_last_20_years', 'priorBenefit'], ['owns_buildable_land', 'ownsLand']]
  return <div className="page-pad resident-page">
    <SectionTitle eyebrow={t('residentEyebrow')} title={t('residentTitle')} description={t('residentDesc')} action={<Badge><ShieldCheck size={14} />{t('noIdentifiers')}</Badge>} />
    <div className="resident-tabs" role="tablist">{(['grievance', 'status', 'eligibility'] as const).map(key => <button key={key} role="tab" aria-selected={tab === key} onClick={() => { setTab(key); setError(''); setNotice('') }} className={tab === key ? 'active' : ''}>{t(key === 'grievance' ? 'grievanceTab' : key === 'status' ? 'statusTab' : 'eligibilityTab')}</button>)}</div>
    <ErrorNote message={error} />{notice && <p className="success-note" role="status">{notice}</p>}
    {tab === 'grievance' && <div className="resident-grid"><Panel title={t('tellUs')} subtitle={`${t('reportLocation')}: ${pocket.pocket_id} · ${pocket.ward}`}>
      <form onSubmit={e => { e.preventDefault(); void send() }}>
        <div className="language-pills">{[['en', 'English'], ['hi', 'हिन्दी'], ['mr', 'मराठी']].map(([key, label]) => <button type="button" key={key} className={complaintLanguage === key ? 'active' : ''} onClick={() => setComplaintLanguage(key as Language)}>{label}</button>)}</div>
        <label className="field"><span>{t('complaint')}</span><textarea aria-label={t('complaint')} required minLength={3} maxLength={2000} value={text} onChange={e => setText(e.target.value)} placeholder={complaintLanguage === 'en' ? t('exampleEn') : complaintLanguage === 'hi' ? t('exampleHi') : t('exampleMr')} /></label>
        <button type="button" className="button ghost" onClick={voice}><Mic size={16} />{t('voiceInput')}</button>
        {classification && <div className="classification"><div><span>{t('likelyCategory')}</span><b>{t(classification.category === 'other' ? 'categoryOther' : `${classification.category}Label`)}</b></div><div><span>{t('urgency')}</span><b>{t(classification.urgency === 'urgent' ? 'urgentStatus' : 'standardStatus')}</b></div><div><span>{t('confidence')}</span><b>{classification.confidence === null ? t('rulesOnly') : `${Math.round(classification.confidence * 100)}%`}</b></div></div>}
        <label className="field"><span>{t('dataScope')}</span><select value={synthetic ? 'demo' : 'real'} onChange={e => setSynthetic(e.target.value === 'demo')}><option value="demo">{t('demoReport')}</option><option value="real">{t('realReport')}</option></select></label>
        {!synthetic && <label className="check-field"><input type="checkbox" required checked={consent} onChange={e => setConsent(e.target.checked)} /><span>{t('consentReport')}</span></label>}
        <div className="button-row"><button className="button primary" type="submit" disabled={busy || text.trim().length < 3}><Send size={16} />{t(busy ? 'saving' : 'submitComplaint')}</button><button type="button" className="button outline" onClick={() => { localStore.setItem(draftKey, text); setNotice(t('draftSaved')) }}>{t('saveDraft')}</button></div>
      </form>
    </Panel><Panel title={t('whatHappens')}><ol className="workflow-list"><li>{t('routedWardDesc')}</li><li>{t('repairHelp')}</li><li>{t('reopenHelp')}</li></ol><Note>{t('confidenceLimit')}</Note></Panel></div>}
    {tab === 'status' && <>
      <div className="section-actions"><RefreshButton onClick={() => { void run(refresh) }} disabled={busy} />{newReceipt && <button className="button primary" onClick={() => downloadJson(`${newReceipt.complaint_id}-private-receipt.json`, newReceipt)}><Download size={15} />{t('downloadReceipt')}</button>}</div>
      {newReceipt && <Panel title={newReceipt.complaint_id}><Note>{t('receiptPrivate')}</Note><label className="field"><span>{t('receiptToken')}</span><input readOnly type="password" value={newReceipt.receipt_token} /></label></Panel>}
      {unavailable > 0 && <ErrorNote message={t('unavailableReceipts', { count: unavailable })} />}
      <div className="report-list">{complaints.map(complaint => <Panel key={complaint.complaint_id} title={complaint.complaint_id} subtitle={`${complaint.pocket_id} · ${t(complaint.synthetic ? 'demoReport' : 'realReport')}`} action={<Badge tone={complaint.status === 'resolved' ? 'teal' : complaint.sla_breached ? 'red' : 'amber'}>{t(`status.${complaint.status}`)}</Badge>}>
        <p className="report-text">{complaint.text}</p><div className="record-facts"><div><span>{t('deadline')}</span><b>{dateTime(complaint.due_at)}</b></div><div><span>{t('owner')}</span><b>{complaint.assigned_to || '—'}</b></div><div><span>{t('department')}</span><b>{complaint.department}</b></div></div>
        {complaint.status === 'awaiting_confirmation' && <div className="confirmation-panel"><h3>{t('awaitingConfirmation')}</h3>{complaint.repair_observation && <div className="repair-review"><b>{t(`${complaint.repair_observation.service}Label`)}: {complaint.repair_observation.value} {complaint.repair_observation.unit}</b><p>{complaint.repair_observation.notes}</p><small>{complaint.repair_observation.source_label} · {dateTime(complaint.repair_observation.observed_at)}</small>{complaint.repair_observation.evidence_url && <p><a href={complaint.repair_observation.evidence_url} target="_blank" rel="noreferrer">{t('evidence')} ↗</a></p>}</div>}<label className="field"><span>{t('confirmationNotes')}</span><textarea minLength={3} maxLength={2000} value={feedback[complaint.complaint_id] || ''} onChange={e => setFeedback(old => ({ ...old, [complaint.complaint_id]: e.target.value }))} /></label><div className="button-row"><button className="button primary" disabled={busy || (feedback[complaint.complaint_id] || '').trim().length < 3} onClick={() => { void confirm(complaint.complaint_id, true) }}>{t('confirmResolved')}</button><button className="button outline" disabled={busy || (feedback[complaint.complaint_id] || '').trim().length < 3} onClick={() => { void confirm(complaint.complaint_id, false) }}>{t('stillFailing')}</button></div><p>{t('reopenHelp')}</p></div>}
        <details><summary>{t('recordedHistory')}</summary><ComplaintHistory complaint={complaint} /></details>
        <button className="text-button" onClick={() => { const receipt = receipts.find(r => r.complaint_id === complaint.complaint_id); if (receipt) downloadJson(`${complaint.complaint_id}-private-receipt.json`, receipt) }}>{t('downloadReceipt')}</button>
      </Panel>)}</div>
      {!complaints.length && <EmptyState>{t('noOwnReports')}</EmptyState>}
      <Panel title={t('restoreReceipt')}><form onSubmit={e => { e.preventDefault(); void run(async () => { const receipt = { complaint_id: restoreId.trim(), receipt_token: restoreToken.trim() }; await trackComplaint(receipt); saveReceipt(receipt); setRestoreToken(''); await refresh() }) }}><div className="form-grid"><label className="field"><span>{t('complaint')}</span><input required value={restoreId} onChange={e => setRestoreId(e.target.value)} /></label><label className="field"><span>{t('receiptToken')}</span><input required type="password" autoComplete="off" value={restoreToken} onChange={e => setRestoreToken(e.target.value)} /></label></div><button className="button outline" type="submit" disabled={busy}>{t('restore')}</button></form></Panel>
    </>}
    {tab === 'eligibility' && <div className="resident-grid"><Panel title={t('supportTitle')} subtitle="PMAY-U 2.0"><form onSubmit={e => { e.preventDefault(); void screen() }}>
      <label className="field"><span>{t('monthlyIncome')}</span><input type="number" required min={0} max={1000000} step={100} value={income} onChange={e => setIncome(Number(e.target.value))} /><small>{t('annualIncome')}: ₹{(income * 12).toLocaleString()}</small></label>
      {questions.map(([key, label]) => <label className="field" key={key}><span>{t(label)}</span><select value={answers[key]} onChange={e => setAnswers(old => ({ ...old, [key]: e.target.value as Answer }))}><option value="unknown">{t('unknown')}</option><option value="yes">{t('yes')}</option><option value="no">{t('no')}</option></select></label>)}
      <label className="check-field"><input type="checkbox" checked={wantsRental} onChange={e => setWantsRental(e.target.checked)} /><span>{t('wantsRental')}</span></label>
      {!wantsRental && <div className="form-grid">{[[loan, setLoan, 'loanAmount'], [property, setProperty, 'propertyValue'], [carpet, setCarpet, 'carpetArea']].map(([value, setter, key]) => <label className="field" key={String(key)}><span>{t(key as string)}</span><input type="number" min={1} value={value as string} onChange={e => (setter as (value: string) => void)(e.target.value)} /></label>)}</div>}
      <button className="button primary" type="submit" disabled={busy}>{t(busy ? 'loading' : 'seeScreening')}</button>
    </form></Panel><Panel title={t('screeningOnly')}>
      {eligibility ? <><Badge tone="amber">{eligibility.screening_status === 'needs_information' ? t('needsInformation') : t('screeningOnly')}</Badge><div className="scheme-results">{eligibility.eligible_schemes.map(scheme => <div key={scheme}><b>{scheme}</b></div>)}</div><ul>{eligibility.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul><h3>{t('documentsChecklist')}</h3><ul>{eligibility.documents_required.map(doc => <li key={doc}>{doc}</li>)}</ul><Note>{eligibility.disclaimer}</Note><p><a href={eligibility.source_url} target="_blank" rel="noreferrer">{t('policySource')} ↗</a> · {t('policyReviewed')}: {eligibility.reviewed_on}</p><button className="button outline" onClick={() => downloadJson(`${pocket.pocket_id}-screening.json`, eligibility)}><Download size={15} />{t('screeningResult')}</button></> : <Note>{t('finalEligibility')}</Note>}
    </Panel></div>}
    <OfficialChannels city={pocket.city} />
  </div>
}
