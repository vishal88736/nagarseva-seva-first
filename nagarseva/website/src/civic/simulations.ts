import type {CivicState,Settlement,Project,Service} from './types.ts'
import {METRICS,SERVICES} from './types.ts'
import {priority,gap,indiaDay,unresolved} from './analytics.ts'
export function anomalies(row:Settlement){
 const rules:string[]=[]
 if(row.householdEstimate>0&&row.populationEstimate/row.householdEstimate>8)rules.push('household_ratio')
 if(SERVICES.some(key=>typeof row[METRICS[key]]==='number'&&Number(row[METRICS[key]])<10))rules.push('low_coverage')
 if(SERVICES.some(key=>row[METRICS[key]]===null||row[METRICS[key]]===undefined))rules.push('missing_coverage')
 return rules
}
export function plantedCheck(state:CivicState){return state.anomalyFixtures.map(fixture=>{const original=state.settlements.find(row=>row.id===fixture.settlementId);return {id:fixture.id,expected:fixture.expectedRule,caught:!!original&&anomalies({...original,...fixture.overrides}).includes(fixture.expectedRule)}})}
export function grievanceTarget(issue:CivicState['issues'][number],at=new Date()){
 const days=({high:2,medium:7,low:14})[issue.priority],start=Date.parse(issue.createdAt),end=unresolved(issue.status)?at.getTime():Date.parse(issue.resolvedAt||'')
 const elapsed=Number.isFinite(start)&&Number.isFinite(end)&&end>=start?(end-start)/86400000:null
 return {days,elapsed,overdue:elapsed===null?null:elapsed>days}
}
export function delayRisk(project:Project,state:CivicState,at=new Date()){
 const day=indiaDay(at),valid=(value:string)=>/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value))
 if(!valid(project.expectedCompletionDate))return 'unavailable'
 if(['completed','cancelled'].includes(project.status))return 'clear'
 if(project.expectedCompletionDate<day)return 'high'
 return state.milestones.some(row=>row.projectId===project.id&&!['completed','cancelled'].includes(row.status)&&valid(row.plannedDate)&&row.plannedDate<day)?'watch':'clear'
}
export function allocateBudget(state:CivicState,service:Service,budget:number,unitCost:number,at=new Date()){
 if(!Number.isFinite(budget)||budget<0||!Number.isFinite(unitCost)||unitCost<.01)throw new Error('demo.error.range')
 let remaining=Math.floor(budget*100),skipped=0;const cents=Math.round(unitCost*100)
 const ranked=state.settlements.map(row=>({row,result:priority(row,state,at)})).sort((a,b)=>(b.result.score??-Infinity)-(a.result.score??-Infinity)||a.row.id.localeCompare(b.row.id))
 const rows=ranked.flatMap(({row,result})=>{const deficit=gap(row,service,state.targets);if(deficit===null||result.score===null){skipped++;return []}
  const need=Math.ceil(row.householdEstimate*deficit/100),households=Math.min(need,Math.floor(remaining/cents)),cost=households*cents;remaining-=cost
  return [{id:row.id,name:row.name,need,households,cost:cost/100,partial:result.partial,score:result.score}]
 })
 return {rows,remaining:remaining/100,allocated:(Math.floor(budget*100)-remaining)/100,skipped}
}
