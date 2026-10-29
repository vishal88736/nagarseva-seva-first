import {t} from '../i18n/locale.ts'
import {METRICS,SERVICES} from './types.ts'
import type {CivicState,Settlement,Service} from './types.ts'
export const ISSUE_TRANSITIONS:Record<string,string[]>={open:['open','acknowledged','in_progress','resolved'],acknowledged:['acknowledged','in_progress','resolved'],in_progress:['in_progress','resolved','open'],resolved:['resolved','closed','open'],closed:['closed','open']}
export const matchesText=(query:string,...values:string[])=>{const needle=query.trim().normalize('NFKC').toLocaleLowerCase();return !needle||values.some(value=>[value,t(value)].some(text=>text.normalize('NFKC').toLocaleLowerCase().includes(needle)))}
export const unresolved = (status:string) => !['resolved','closed'].includes(status)
export const indiaDay = (instant=new Date()) => new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(instant)
export function coverage(rows:Settlement[],key:Service) {
  const field=METRICS[key],known=rows.filter(row=>typeof row[field]==='number'&&Number.isFinite(row[field]))
  const households=known.reduce((sum,row)=>sum+row.householdEstimate,0)
  return households ? known.reduce((sum,row)=>sum+Number(row[field])*row.householdEstimate,0)/households : null
}
export function gap(row:Settlement,key:Service,targets:CivicState['targets']) {const value=row[METRICS[key]];return typeof value==='number'&&Number.isFinite(value)&&value>=0&&value<=100?Math.max(0,targets[key]-value):null}
export function meanGap(row:Settlement,targets:CivicState['targets']) {const values=SERVICES.map(key=>gap(row,key,targets)).filter((v):v is number=>v!==null);return values.length?values.reduce((a,b)=>a+b,0)/values.length:null}
export function completeness(rows:Settlement[]){const total=rows.length*SERVICES.length;return total?rows.reduce((sum,row)=>sum+SERVICES.filter(key=>typeof row[METRICS[key]]==='number'&&Number.isFinite(row[METRICS[key]])).length,0)/total*100:null}
export function priority(row:Settlement,state:CivicState,at=new Date()) {
  const issues=state.issues.filter(issue=>issue.settlementId===row.id&&unresolved(issue.status))
  const ages=issues.map(issue=>(at.getTime()-Date.parse(issue.createdAt))/86400000)
  const factors={gap:meanGap(row,state.targets),priority:issues.some(issue=>!['low','medium','high'].includes(issue.priority))?null:Math.max(0,...issues.map(issue=>({low:20,medium:50,high:100})[issue.priority])),unresolved:Math.min(10,issues.length)*10,age:ages.some(age=>!Number.isFinite(age)||age<0)?null:Math.min(30,Math.max(0,...ages))/30*100}
  const available=Object.keys(factors).filter(key=>factors[key as keyof typeof factors]!==null&&state.weights[key as keyof typeof state.weights]>0) as (keyof typeof factors)[]
  const total=available.reduce((sum,key)=>sum+state.weights[key],0)
  const contributions=Object.fromEntries(Object.entries(factors).map(([key,value])=>[key,value===null?null:total?value*state.weights[key as keyof typeof state.weights]/total:null])) as Record<keyof typeof factors,number|null>
  const partial=Object.entries(factors).some(([key,value])=>state.weights[key as keyof typeof state.weights]>0&&value===null)||(state.weights.gap>0&&SERVICES.some(key=>gap(row,key,state.targets)===null))
  return {factors,contributions,score:total?available.reduce((sum,key)=>sum+(contributions[key]??0),0):null,partial,completeness:completeness([row])}
}
export type SettlementFilters={search:string;ward:string;risk:string;redevelopment:string;service:string;sort:string}
export const EMPTY_FILTERS:SettlementFilters={search:'',ward:'',risk:'',redevelopment:'',service:'',sort:'name'}
export function filterSettlements(state:CivicState,filters:SettlementFilters) {
  return state.settlements.filter(row=>matchesText(filters.search,row.id,row.name)&&(!filters.ward||row.wardId===filters.ward)&&(!filters.risk||row.riskLevel===filters.risk)&&(!filters.redevelopment||row.redevelopmentStatus===filters.redevelopment)&&(!filters.service||(gap(row,filters.service as Service,state.targets)??0)>0)).sort((a,b)=>filters.sort==='population'?b.populationEstimate-a.populationEstimate:filters.sort==='gap'?(meanGap(b,state.targets)??0)-(meanGap(a,state.targets)??0):a.name.localeCompare(b.name))
}
export function dashboard(state:CivicState,at=new Date()) {
  return {settlements:state.settlements.length,open:state.issues.filter(row=>unresolved(row.status)).length,inProgress:state.issues.filter(row=>row.status==='in_progress').length,resolved:state.issues.filter(row=>row.status==='resolved').length,projects:state.projects.filter(row=>row.status==='active').length,visits:state.visits.filter(row=>row.status==='scheduled'&&row.scheduledDate>=indiaDay(at)).length,assessments:state.assessments.length}
}
export const groupCounts=(rows:{[key:string]:unknown}[],key:string)=>Object.fromEntries([...new Set(rows.map(row=>String(row[key])))].sort().map(value=>[value,rows.filter(row=>String(row[key])===value).length]))
export function assertWorkspace(value:unknown):CivicState {
  const state=value as CivicState
  if(!state||state.schemaVersion!==1||state.sourceType!=='synthetic'||!Number.isInteger(state.revision)||state.revision<1)throw new Error('demo.error.corrupt')
  const collections=['settlements','wards','issues','projects','milestones','visits','assessments','feedback','activity','dataSources','anomalyFixtures'] as const
  const all=new Set<string>()
  for(const key of collections){if(!Array.isArray(state[key]))throw new Error('demo.error.corrupt');for(const row of state[key]){if(!row.id?.startsWith('DEMO-')||all.has(row.id)||row.sourceType!=='synthetic'||row.is_synthetic!==true)throw new Error('demo.error.corrupt');all.add(row.id)}}
  const settlements=new Set(state.settlements.map(row=>row.id)),wards=new Set(state.wards.map(row=>row.id)),projects=new Set(state.projects.map(row=>row.id))
  if(state.settlements.some(row=>!wards.has(row.wardId)||row.householdEstimate<=0||SERVICES.some(key=>{const v=row[METRICS[key]];return v!==null&&(typeof v!=='number'||!Number.isFinite(v)||v<0||v>100)}))||[...state.issues,...state.projects,...state.visits,...state.assessments,...state.feedback].some(row=>!settlements.has(row.settlementId))||state.milestones.some(row=>!projects.has(row.projectId)))throw new Error('demo.error.corrupt')
  return state
}
