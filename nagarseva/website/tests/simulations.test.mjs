import {test} from 'node:test'
import assert from 'node:assert/strict'
import {priority} from '../src/civic/analytics.ts'
import {anomalies,allocateBudget,grievanceTarget,delayRisk} from '../src/civic/simulations.ts'
const demo=()=>({id:'DEMO-TEST-1',name:'Demo data settlement',sourceType:'synthetic',is_synthetic:true,populationEstimate:400,householdEstimate:100,waterAccessPercent:50,sanitationAccessPercent:50,drainageCoveragePercent:50,wasteCollectionPercent:50,electricityAccessPercent:50,roadAccessPercent:50})
const state=()=>({settlements:[demo()],issues:[],milestones:[],targets:{water:90,sanitation:90,drainage:90,waste:90,electricity:90,access:90},weights:{gap:1,priority:0,unresolved:0,age:0}})
test('Missing inputs produce Partial or unavailable scores rather than an invented zero',()=>{
 const s=state();s.settlements[0].waterAccessPercent=null
 assert.equal(priority(s.settlements[0],s).partial,true);assert.equal(priority(s.settlements[0],s).score,40)
 for(const key of ['waterAccessPercent','sanitationAccessPercent','drainageCoveragePercent','wasteCollectionPercent','electricityAccessPercent','roadAccessPercent'])s.settlements[0][key]=null
 assert.equal(priority(s.settlements[0],s).score,null)
})
test('Planted demo anomalies are detected by documented independent predicates',()=>{
 const row=demo();assert.deepEqual(anomalies(row),[])
 assert.ok(anomalies({...row,populationEstimate:900}).includes('household_ratio'))
 assert.ok(anomalies({...row,waterAccessPercent:5}).includes('low_coverage'))
 assert.ok(anomalies({...row,sanitationAccessPercent:null}).includes('missing_coverage'))
})
test('Budget allocation conserves funds, skips unknown coverage and never changes records',()=>{
 const s=state(),before=JSON.stringify(s),result=allocateBudget(s,'water',105,10)
 assert.equal(result.allocated,100);assert.equal(result.remaining,5);assert.equal(result.rows[0].households,10);assert.equal(JSON.stringify(s),before)
 s.settlements[0].waterAccessPercent=null;assert.equal(allocateBudget(s,'water',105,10).skipped,1)
 assert.throws(()=>allocateBudget(s,'water',105,0));assert.equal(allocateBudget(state(),'water',0,10).allocated,0)
})
test('SLA uses valid source dates, preserves missing resolution and handles priorities',()=>{
 const now=new Date('2026-10-29T00:00:00Z'),issue={priority:'high',status:'open',createdAt:'2026-10-25T00:00:00Z',resolvedAt:null}
 assert.equal(grievanceTarget(issue,now).elapsed,4);assert.equal(grievanceTarget(issue,now).overdue,true)
 assert.equal(grievanceTarget({...issue,status:'resolved'},now).elapsed,null)
 assert.equal(grievanceTarget({...issue,createdAt:'bad'},now).overdue,null)
})
test('Project delay flags follow real stored dates and milestone statuses',()=>{
 const at=new Date('2026-10-29T00:00:00Z'),project={id:'DEMO-PROJ-1',status:'active',expectedCompletionDate:'2026-10-28'}
 assert.equal(delayRisk(project,state(),at),'high')
 assert.equal(delayRisk({...project,expectedCompletionDate:'bad'},state(),at),'unavailable')
 assert.equal(delayRisk({...project,status:'completed'},state(),at),'clear')
 const s=state();s.milestones=[{projectId:project.id,status:'planned',plannedDate:'2026-10-01'}]
 assert.equal(delayRisk({...project,expectedCompletionDate:'2027-10-28'},s,at),'watch')
})
