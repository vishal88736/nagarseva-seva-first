import assert from 'node:assert/strict'
import {test} from 'node:test'
import {coverage,gap,priority,filterSettlements,EMPTY_FILTERS,dashboard,assertWorkspace,indiaDay} from '../src/civic/analytics.ts'
import {reportRows,reportCsv} from '../src/civic/services.ts'
import {messages} from '../src/i18n/messages.ts'
import {readFile,readdir} from 'node:fs/promises'
const settlement=(id,households,water)=>({id,sourceType:'synthetic',name:`Demo Settlement ${id.slice(-3)}`,wardId:'DEMO-WARD-01',locality:'Demo Locality 01',populationEstimate:households*4,householdEstimate:households,householdsForAssessment:10,waterAccessPercent:water,sanitationAccessPercent:80,drainageCoveragePercent:80,wasteCollectionPercent:80,electricityAccessPercent:80,roadAccessPercent:80,riskLevel:id.endsWith('1')?'high':'low',redevelopmentStatus:'assessment',housingCondition:'needs_repair',latitude:19,longitude:72.9,geometry:{type:'Polygon',coordinates:[[[72.9,19],[72.91,19],[72.91,19.01],[72.9,19.01],[72.9,19]]]},indicatorHistory:[]})
const baseData=()=>({schemaVersion:1,sourceType:'synthetic',revision:1,seed:96,lastSavedAt:'2026-10-29T00:00:00Z',settlements:[settlement('DEMO-SET-001',100,20),settlement('DEMO-SET-002',300,80)],wards:[{id:'DEMO-WARD-01',sourceType:'synthetic',name:'Demo Ward 01',settlementCount:2}],issues:[{id:'DEMO-ISS-001',sourceType:'synthetic',settlementId:'DEMO-SET-001',category:'water',status:'open',title:'=TEST ONLY formula',priority:'high',createdAt:'2026-10-14T00:00:00Z',updatedAt:'2026-10-14T00:00:00Z',history:[],attachment:null}],projects:[],milestones:[],visits:[],assessments:[],feedback:[],activity:[],dataSources:[],targets:{water:90,sanitation:90,drainage:90,waste:90,electricity:90,access:90},weights:{gap:.5,priority:.2,unresolved:.2,age:.1}})
const data=()=>{const state=baseData();state.is_synthetic=true;state.anomalyFixtures=[];for(const value of Object.values(state))if(Array.isArray(value))for(const row of value)if(row&&typeof row==='object')row.is_synthetic=true;return state}
test('Coverage is household-weighted; missing coverage has no invented zero or denominator',()=>{
 const state=data();assert.equal(coverage(state.settlements,'water'),65);assert.equal(coverage([],'water'),null)
 state.settlements[1].waterAccessPercent=null;assert.equal(coverage(state.settlements,'water'),20)
 assert.equal(gap(state.settlements[0],'water',state.targets),70);assert.equal(gap(state.settlements[1],'water',state.targets),null)
})
test('Combined filters, reset, sorting and map records use stable IDs from one collection',()=>{
 const state=data();assert.equal(filterSettlements(state,{...EMPTY_FILTERS,search:'001',risk:'high',ward:'DEMO-WARD-01',service:'water',redevelopment:'assessment'}).length,1)
 assert.equal(filterSettlements(state,{...EMPTY_FILTERS,search:'001',risk:'low'}).length,0)
 assert.equal(filterSettlements(state,{...EMPTY_FILTERS,sort:'population'})[0].id,'DEMO-SET-002')
 assert.equal(filterSettlements(state,EMPTY_FILTERS).length,2)
 assert.equal(filterSettlements(state,EMPTY_FILTERS)[0],state.settlements[0])
})
test('Demo priority factors match a hand-worked 37-point example',()=>{
 const state=data(),result=priority(state.settlements[0],state,new Date('2026-10-29T00:00:00Z'))
 assert.deepEqual(result.factors,{gap:20,priority:100,unresolved:10,age:50});assert.ok(Math.abs(result.score-37)<1e-10)
})
test('Dashboard updates derive from the issue collection; visits use the India calendar',()=>{
 const state=data();assert.equal(dashboard(state,new Date('2026-10-29T00:00:00Z')).open,1)
 state.issues[0].status='resolved';assert.equal(dashboard(state).open,0);assert.equal(dashboard(state).resolved,1)
 assert.equal(indiaDay(new Date('2026-10-29T22:00:00Z')),'2026-10-30')
})
test('Report filters and actual CSV preserve notices, missing values and formula safety',()=>{
 const state=data();assert.equal(reportRows(state,'issues','DEMO-SET-002').length,0)
 assert.equal(reportRows(state,'issues','','2026-10-15').length,0)
 const rows=reportRows(state,'issues','DEMO-SET-001'),csv=reportCsv(rows)
 assert.ok(csv.includes('Synthetic demonstration data. Not official government records'))
 assert.ok(csv.includes("'=TEST ONLY formula"));assert.ok(csv.includes('DEMO-ISS-001'))
 assert.ok(reportCsv([]).includes('export_notice'))
 assert.equal(reportRows(state,'coverage').length,12)
 assert.ok(reportRows(state,'coverage').every(row=>row.is_synthetic===true))
 assert.ok(csv.includes('Demo data')&&csv.includes('source_date')&&csv.includes('source_date_type'))
})
test('Incoming workspace rejects duplicates, orphaned relationships and invalid coverage',()=>{
 assert.equal(assertWorkspace(data()).settlements.length,2)
 for(const change of [s=>s.settlements.push(s.settlements[0]),s=>s.issues[0].settlementId='missing',s=>s.settlements[0].waterAccessPercent=101,s=>s.settlements[0].wardId='missing']){const state=data();change(state);assert.throws(()=>assertWorkspace(state),/corrupt/)}
})
test('Every literal translation key in the new main flows exists in all three languages',async()=>{
 for(const folder of ['civic','integration'])for(const name of await readdir(new URL(`../src/${folder}/`,import.meta.url))){if(!name.endsWith('.tsx'))continue;const source=await readFile(new URL(`../src/${folder}/${name}`,import.meta.url),'utf8');for(const [,key] of source.matchAll(/\bt\(['"]([^'"\n]+)['"]/g)){assert.ok(messages[key],`${name}: ${key}`);assert.ok(messages[key].hi);assert.ok(messages[key].mr)}}
 for(const value of ['boundaries','identifiers','housing','services','projects','issues','visits'])assert.ok(messages[`ir.category.${value}`])
 for(const value of ['not_provided','awaiting_configuration','file_received','validation_failed','validation_passed','imported_demo','connected_authorized','unknown'])assert.ok(messages[`ir.status.${value}`])
})

test('Visible localized settlement names and stable IDs are both searchable',async()=>{
 const {setLanguage,t}=await import('../src/i18n/locale.ts')
 try{
  for(const language of ['en','hi','mr']){
   setLanguage(language)
   const name=t('Demo Settlement 001')
   assert.equal(filterSettlements(data(),{...EMPTY_FILTERS,search:name})[0]?.id,'DEMO-SET-001')
   assert.equal(filterSettlements(data(),{...EMPTY_FILTERS,search:'  DEMO-SET-001  '}).length,1)
  }
 }finally{setLanguage('en')}
})

test('Issue status editor exposes only the backend-supported transitions',async()=>{
 const {ISSUE_TRANSITIONS}=await import('../src/civic/analytics.ts')
 assert.deepEqual(ISSUE_TRANSITIONS.closed,['closed','open'])
 assert.ok(!ISSUE_TRANSITIONS.open.includes('closed'))
 assert.ok(ISSUE_TRANSITIONS.resolved.includes('closed'))
})
