import {encodeCsv} from '../urban/csv.ts'
import {METRICS,SERVICES} from './types.ts'
import type {CivicState} from './types.ts'
import {t,getLanguage} from '../i18n/locale.ts'
import {messages} from '../i18n/messages.ts'
import {indiaDay,unresolved} from './analytics.ts'
export type ReportKind='settlements'|'coverage'|'issues'|'projects'|'housing'|'visits'
export function reportRows(state:CivicState,kind:ReportKind,settlement='',from='',to=''):Record<string,unknown>[] {
  const allowed=(id:string)=>!settlement||id===settlement
  const within=(day:string)=>{const d=day.includes('T')?indiaDay(new Date(day)):day.slice(0,10);return (!from||d>=from)&&(!to||d<=to)}
  switch(kind){
    case 'settlements':return state.settlements.filter(row=>allowed(row.id)).map(({geometry,indicatorHistory,...row})=>({...row,geometryType:geometry.type}))
    case 'coverage':return state.settlements.filter(row=>allowed(row.id)).flatMap(row=>SERVICES.map(service=>({is_synthetic:true,settlementId:row.id,service,coverage:row[METRICS[service]],target:state.targets[service],gap:typeof row[METRICS[service]]==='number'?Math.max(0,state.targets[service]-Number(row[METRICS[service]])):null,measurementType:'synthetic_percent',method:'Household-weighted coverage for aggregate; max(0, target - coverage) for settlement gap'})))
    case 'issues':return state.issues.filter(row=>allowed(row.settlementId)&&unresolved(row.status)&&within(row.createdAt)).map(({history,attachment,...row})=>({...row,historyEvents:history.length,hasAttachment:!!attachment}))
    case 'projects':return state.projects.filter(row=>allowed(row.settlementId)&&within(row.startDate)).map(({history,...row})=>({...row,milestones:state.milestones.filter(m=>m.projectId===row.id).length,completedMilestones:state.milestones.filter(m=>m.projectId===row.id&&m.status==='completed').length}))
    case 'housing':return state.assessments.filter(row=>allowed(row.settlementId)&&within(row.assessmentDate)).map(({history,...row})=>({...row,historyEvents:history.length,eligibility:'No official eligibility determination'}))
    case 'visits':return state.visits.filter(row=>allowed(row.settlementId)&&within(row.scheduledDate)).map(({history,...row})=>({...row,historyEvents:history.length}))
  }
}
export function reportCsv(rows:Record<string,unknown>[],state?:CivicState) {
  const notice='Demo data. Synthetic demonstration data. Not official government records or verified measurements.'
  const exportedAt=new Date().toISOString(),source=t('audit.generator'),sourceDate=state?.lastSavedAt||'',language=getLanguage()
  const metadata={synthetic:true,is_synthetic:true,synthetic_disclaimer:notice,watermark:'Demo data',language,source,source_date:sourceDate,source_date_type:'workspace_save',exported_at:exportedAt,source_link:'/methodology'}
  const headers=Object.fromEntries([...new Set(rows.flatMap(row=>Object.keys(row)))].map(key=>[key,messages[`d.field.${key}`]?t(`d.field.${key}`):key]))
  return encodeCsv([{...metadata,rowType:'export_notice',recordCount:rows.length}, {...metadata,...headers,rowType:'localized_headers'},...rows.map(row=>({...row,...metadata,rowType:'record'}))])
}
export function downloadText(filename:string,text:string,type='text/csv;charset=utf-8') {
  const url=URL.createObjectURL(new Blob([text],{type})),link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
