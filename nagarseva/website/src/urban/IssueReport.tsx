import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { CheckCircle2, Send } from 'lucide-react'
import { FileInput } from '../i18n/LanguageProvider'
import { t, errorText, formatDate } from '../i18n/locale'
import { Field, Heading, Panel, Tag } from './PlanningPages'
import { dataApi } from './publicClient'
import { ISSUE_CATEGORIES, confirmedIssue } from './issueClient'
import type { CitizenIssue, IssueCategory } from './issueClient'

const requestKey=()=>globalThis.crypto?.randomUUID?.()||'request-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2)
const today = () => new Date(Date.now()+330*60000).toISOString().slice(0,10)
export default function IssueReport({ lookupId = '' }: { lookupId?: string }) {
  const [category,setCategory] = useState<IssueCategory | ''>(''), [description,setDescription] = useState(''), [ward,setWard] = useState(''), [location,setLocation] = useState('')
  const [date,setDate] = useState(today), [latitude,setLatitude] = useState(''), [longitude,setLongitude] = useState(''), [file,setFile] = useState<File | null>(null), [consent,setConsent] = useState(false)
  const [saved,setSaved] = useState<CitizenIssue | null>(null), [error,setError] = useState(''), [busy,setBusy] = useState(false), [imageEnabled,setImageEnabled] = useState<boolean | null>(null)
  const submissionKey = useRef(''), locked = useRef(false)
  if(!submissionKey.current)submissionKey.current=requestKey()
  useEffect(() => { let active=true; dataApi<{evidence_storage:boolean}>('/health').then(data=>{if(active)setImageEnabled(data.evidence_storage)}).catch(()=>{if(active){setImageEnabled(false);setError('civic.persistenceUnavailable')}}); return()=>{active=false} }, [])
  useEffect(() => { if(!lookupId)return; let active=true;dataApi<CitizenIssue>(`/issues/${encodeURIComponent(lookupId)}`).then(data=>{if(active)setSaved(confirmedIssue(data))}).catch(problem=>{if(active)setError(problem.message)});return()=>{active=false} },[lookupId])
  async function submit(event: FormEvent) {
    event.preventDefault(); if(locked.current)return
    setError(''); locked.current=true;setBusy(true)
    try {
      if(!category) throw new Error('civic.chooseCategory')
      if(!location.trim()) throw new Error('civic.locationRequired')
      if(description.trim().length<10) throw new Error('issues.error.description')
      if(!!latitude.trim()!==!!longitude.trim()) throw new Error('issues.error.coordinates')
      if(date>today()) throw new Error('issues.error.future')
      let attachment = null
      if(file) {
        if(!['image/png','image/jpeg'].includes(file.type)||!file.size||file.size>2097152)throw new Error('issues.error.image')
        if(!consent)throw new Error('issues.error.consent')
        const content=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('The file could not be read.'));reader.readAsDataURL(file)})
        attachment={filename:file.name,content_type:file.type,content_base64:content,consent:true}
      }
      const result=await dataApi<CitizenIssue>('/issues',{category,description:description.trim(),ward:ward.trim()||null,location:location.trim()||null,report_date:date,latitude:latitude.trim()?Number(latitude):null,longitude:longitude.trim()?Number(longitude):null,attachment},'','POST',{'Idempotency-Key':submissionKey.current})
      const confirmed = confirmedIssue(result)
      setSaved(confirmed);const url=new URL(window.location.href);url.searchParams.set('issue',confirmed.id);history.replaceState(null,'',url)
    } catch(problem){setError((problem as Error).message)} finally {locked.current=false;setBusy(false)}
  }
  function reset(){const url=new URL(window.location.href);url.searchParams.delete('issue');history.replaceState(null,'',url);submissionKey.current=requestKey();setSaved(null);setCategory('');setDescription('');setWard('');setLocation('');setLatitude('');setLongitude('');setFile(null);setConsent(false);setDate(today());setError('')}
  return <>
    <Heading number="03" title={t('issues.title')} description={t('issues.intro')} />
    {error && <div className="us-alert" role="alert">{errorText(error)}</div>}
    {saved ? <Panel className="product-issue-confirmation"><CheckCircle2 size={28}/><h2>{t('issues.saved')}</h2><p>{t('issues.savedNote')}</p><dl className="us-facts"><div><dt>{t('issues.reference')}</dt><dd><code>{saved.id}</code></dd></div><div><dt>{t('Status')}</dt><dd><Tag tone="blue">{t(`issues.status.${saved.status}`)}</Tag></dd></div><div><dt>{t('Category')}</dt><dd>{t(`issues.category.${saved.category}`)}</dd></div><div><dt>{t('issues.reportDate')}</dt><dd>{formatDate(saved.report_date)}</dd></div></dl><p>{saved.description}</p>{saved.resolution_note&&<p>{saved.resolution_note}</p>}<button className="us-button primary" onClick={reset}>{t('issues.another')}</button></Panel> :
    <Panel className="product-issue-form"><form aria-label={t('issues.form')} onSubmit={submit}>
      <p className="product-note">{t('issues.prototype')}</p>
      <fieldset disabled={busy} className="public-fieldset">
        <div className="us-form-grid"><Field label={t('Category')}><select aria-label={t('issues.categoryLabel')} value={category} required onChange={event=>setCategory(event.target.value as IssueCategory)}><option value="">{t('civic.chooseCategory')}</option>{ISSUE_CATEGORIES.map(value=><option key={value} value={value}>{t(`issues.category.${value}`)}</option>)}</select></Field><Field label={t('issues.reportDate')}><input aria-label={t('issues.reportDate')} type="date" required max={today()} value={date} onChange={event=>setDate(event.target.value)}/></Field></div>
        <Field label={t('Description')} hint={t('issues.descriptionHint')}><textarea aria-label={t('issues.descriptionLabel')} required minLength={10} maxLength={2000} rows={5} value={description} onChange={event=>setDescription(event.target.value)}/></Field>
        <div className="us-form-grid"><Field label={t('issues.ward')}><input aria-label={t('issues.ward')} maxLength={120} value={ward} onChange={event=>setWard(event.target.value)}/></Field><Field label={t('issues.location')}><input aria-label={t('issues.location')} required maxLength={300} value={location} onChange={event=>setLocation(event.target.value)}/></Field></div>
        <details className="product-optional"><summary>{t('issues.optionalLocation')}</summary><p className="us-small">{t('issues.locationHint')}</p><div className="us-form-grid"><Field label={t('Latitude')}><input aria-label={t('Latitude')} type="number" min={-90} max={90} step="0.001" value={latitude} onChange={event=>setLatitude(event.target.value)}/></Field><Field label={t('Longitude')}><input aria-label={t('Longitude')} type="number" min={-180} max={180} step="0.001" value={longitude} onChange={event=>setLongitude(event.target.value)}/></Field></div></details>
        {imageEnabled===null&&<p role="status">{t('Checking connection…')}</p>}
        {imageEnabled===false&&<p className="us-small">{t('civic.imageUnavailable')}</p>}
        {imageEnabled && <details className="product-optional"><summary>{t('issues.optionalImage')}</summary><p className="us-small">{t('issues.imageHint')}</p><FileInput fileName={file?.name||''} aria-label={t('issues.imageLabel')} accept="image/png,image/jpeg" onChange={event=>setFile(event.target.files?.[0]||null)}/>{file&&<label className="us-check"><input type="checkbox" checked={consent} onChange={event=>setConsent(event.target.checked)}/>{t('issues.imageConsent')}</label>}</details>}
        <button className="us-button primary" type="submit"><Send size={16}/>{busy?t('Saving…'):t('issues.submit')}</button>
      </fieldset>
    </form></Panel>}
  </>
}
