import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {CRITERIA,isDate,safeUrl,validateDataset,haversine,walkable,buildGraph,routeToAmenities,normaliseWeights,prioritise,sensitivity,compareBudget,observationGroups,dataQuality,searchEvidence,rankingCsv,sha256,auditSchemeRecords} from '../dist/lib/engine.mjs';

const load=name=>JSON.parse(fs.readFileSync(new URL('../dist/data/'+name,import.meta.url),'utf8'));
const example=load('example.json');
const references=load('reference-points.json');
const clone=()=>structuredClone(example);
const weights={water_deficit:40,sanitation_deficit:40,waste_deficit:20};
const point=(id,coords,category='toilets')=>({type:'Feature',id,geometry:{type:'Point',coordinates:coords},properties:{name:id,category}});
const line=(id,coords,props={})=>({type:'Feature',id,geometry:{type:'LineString',coordinates:coords},properties:{highway:'footway',...props}});
const small=(roads,amenities)=>({...clone(),network:{type:'FeatureCollection',features:roads},amenities:{type:'FeatureCollection',features:amenities}});

test('real public listing audit flags ambiguity while retaining distinct records and unknowns',()=>{
  const source=load('public-schemes.json'),result=auditSchemeRecords(source.records);
  assert.equal(source.metadata.is_synthetic,false);assert.equal(result.count,3);
  assert.equal(result.exactGroups.length,1);assert.equal(result.exactGroups[0].localIds.length,2);
  assert.equal(result.candidateGroups[0].localIds.length,3);
  assert.equal(result.suppliedProposalCount,0);assert.equal(result.suppliedStatusCount,0);assert.equal(result.suppliedUpdateCount,0);assert.equal(result.automaticallyMerged,0);
});
test('shared CTS strings in different ward or village contexts are not grouped',()=>{
  const rows=structuredClone(load('public-schemes.json').records);rows[1].ward='Other ward';rows[2].locality='Other village';
  const result=auditSchemeRecords(rows);assert.equal(result.exactGroups.length,0);assert.equal(result.candidateGroups.length,0);
});
test('record audit does not mutate raw CTS, substitute retrieval dates or fill missing status',()=>{
  const source=load('public-schemes.json'),before=JSON.stringify(source.records);auditSchemeRecords(source.records);assert.equal(JSON.stringify(source.records),before);
  for(const r of source.records){assert.equal(r.project_status,null);assert.equal(r.record_updated_at,null);assert.equal(r.official_scheme_id,null);}
});

test('calendar dates are strict, including leap days and invalid normalisations',()=>{
  assert.equal(isDate('2024-02-29'),true);assert.equal(isDate('2026-02-29'),false);assert.equal(isDate('2026-02-30'),false);assert.equal(isDate('2026-10-17T00:00:00Z'),false);
});
test('only credential-free HTTPS source links are accepted',()=>{
  assert.equal(safeUrl('javascript:alert(1)'),null);assert.equal(safeUrl('http://example.org'),null);assert.equal(safeUrl('https://user:secret@example.org'),null);assert.equal(safeUrl('https://censusindia.gov.in/'),'https://censusindia.gov.in/');
});
test('reference points and synthetic inputs validate without turning unknown dates into observations',()=>{
  validateDataset(references);validateDataset(example);assert.equal(references.metadata.observed_at,null);assert.equal(references.network.features.length,0);assert.equal(example.metadata.is_synthetic,true);
});
test('future source/observation dates, out-of-range deficits and invalid coordinates are rejected',()=>{
  const a=clone();a.areas[0].observed_at='2027-01-01';assert.throws(()=>validateDataset(a),/future/);
  const b=clone();b.areas[0].water_deficit=1.01;assert.throws(()=>validateDataset(b),/0–1/);
  const c=clone();c.amenities.features[0].geometry.coordinates=[181,19];assert.throws(()=>validateDataset(c),/WGS84/);
  const d=clone();d.areas[0].waste_deficit=NaN;assert.throws(()=>validateDataset(d),/0–1/);
});
test('duplicate identities and incomplete required schema are rejected',()=>{
  const a=clone();a.areas.push({...a.areas[0]});assert.throws(()=>validateDataset(a),/Duplicate area/);
  const b=clone();delete b.metadata;assert.throws(()=>validateDataset(b),/metadata/);
  const c=clone();c.network.features.push({...c.network.features[0]});assert.throws(()=>validateDataset(c),/duplicate ID/);
});
test('personal fields and prototype-pollution keys are rejected recursively',()=>{
  const a=clone();a.areas[0].phone='private';assert.throws(()=>validateDataset(a),/personal field/);
  const b=JSON.parse(JSON.stringify(example).replace('"schema_version":"1.0"','"__proto__":{},"schema_version":"1.0"'));assert.throws(()=>validateDataset(b),/Unsafe object/);
});
test('UTF-8 byte size is checked rather than treating characters as bytes',()=>{
  const a=clone();a.network.features[0].properties.extra='🌍'.repeat(1400000);assert.throws(()=>validateDataset(a),/5 MB/);
});
test('spherical distance agrees with a known one-degree meridian length and preserves real zero',()=>{
  assert.ok(Math.abs(haversine([0,0],[0,1])-111195.08)<.1);assert.equal(haversine([72.9,19],[72.9,19]),0);
});
test('pedestrian restrictions override vehicle defaults; step avoidance is explicit',()=>{
  assert.equal(walkable({highway:'motorway',foot:'yes'}),false);
  assert.equal(walkable({highway:'residential',access:'private'}),false);
  assert.equal(walkable({highway:'residential',access:'private',foot:'yes'}),true);
  assert.equal(walkable({highway:'residential',access:'private',foot:'unknown'}),false);
  assert.equal(walkable({highway:'residential',access:'no',foot:'unrecognised'}),false);
  assert.equal(walkable({highway:'steps'},true),false);
  assert.equal(walkable({highway:'primary'}),false);
});
test('Dijkstra chooses the connected candidate, preserves disconnection and excludes private amenities',()=>{
  const r=routeToAmenities(example,[0,0],'toilets',10);
  assert.equal(r.status,'calculated');const a=r.routes.find(x=>x.id==='example-toilet-a');
  assert.equal(a.status,'candidate_route');assert.ok(Math.abs(a.distanceM-667.17048)<.5);assert.ok(a.distanceM>a.straightLineM);
  assert.equal(r.routes.find(x=>x.id==='example-toilet-b').status,'disconnected');assert.equal(r.routes.find(x=>x.id==='example-toilet-b').distanceM,null);
  assert.equal(r.routes.find(x=>x.id==='example-toilet-private').status,'access_restricted');assert.equal(r.graph.rejectedWays,1);
});
test('snap tolerance is bounded; a far origin is unavailable, not zero distance',()=>{
  const r=routeToAmenities(example,[1,1],'toilets',10);assert.equal(r.status,'origin_not_routable');assert.equal(r.originSnapM,null);
  assert.throws(()=>routeToAmenities(example,[0,0],'toilets',-1),/Snap/);
});
test('empty reference graph cannot fabricate a route or a zero-coverage result',()=>{
  const r=routeToAmenities(references,[72.91507,19.05537],'transport_stop',80);
  assert.equal(r.status,'origin_not_routable');assert.deepEqual(r.routes,[]);
});
test('grade-separated coordinate-only ways do not gain invented connections',()=>{
  const ds=small([line('ground',[[0,0],[.002,0]],{layer:0}),line('bridge',[[.002,0],[.004,0]],{layer:1,bridge:'yes'})],[point('end',[.004,0])]);
  assert.equal(routeToAmenities(ds,[0,0],'toilets',1).routes[0].status,'disconnected');
});
test('shared source node IDs connect, while contradictory coordinates fail loudly',()=>{
  const ds=small([line('one',[[0,0],[.002,0]],{node_ids:['a','b']}),line('two',[[.002,0],[.004,0]],{node_ids:['b','c'],layer:1})],[point('end',[.004,0])]);
  assert.equal(routeToAmenities(ds,[0,0],'toilets',1).routes[0].status,'candidate_route');
  ds.network.features[1].geometry.coordinates[0]=[.0021,0];assert.throws(()=>buildGraph(ds.network),/contradictory/);
});
test('oneway:foot respects walking direction without applying motor-vehicle one-way tags',()=>{
  const ds=small([line('one',[[0,0],[.002,0]],{'oneway:foot':'yes'})],[point('end',[0,0])]);
  assert.equal(routeToAmenities(ds,[.002,0],'toilets',1).routes[0].status,'disconnected');
  delete ds.network.features[0].properties['oneway:foot'];ds.network.features[0].properties.oneway='yes';assert.equal(routeToAmenities(ds,[.002,0],'toilets',1).routes[0].status,'candidate_route');
});
test('legitimate zero scores remain zero; missing values become intervals',()=>{
  const a=clone();a.areas[0].water_deficit=0;a.areas[0].sanitation_deficit=0;a.areas[0].waste_deficit=0;
  const r=prioritise(a.areas,weights);const z=r.rows.find(x=>x.id==='example-a');assert.equal(z.lower,0);assert.equal(z.upper,0);assert.equal(z.complete,true);
  const m=r.rows.find(x=>x.id==='example-c');assert.ok(Math.abs(m.lower-.42)<1e-12);assert.ok(Math.abs(m.upper-.82)<1e-12);assert.equal(m.ageDays,null);
});
test('entirely unknown areas have no deprivation rank and no invented date',()=>{
  const r=prioritise(example.areas,weights);const unknown=r.rows.find(x=>x.id==='example-d');assert.equal(unknown.rankBest,null);assert.equal(unknown.rankWorst,null);assert.equal(unknown.hasEvidence,false);assert.equal(unknown.ageDays,null);
});
test('zero/invalid weights fail, and contribution sums match score on complete data',()=>{
  assert.throws(()=>normaliseWeights({water_deficit:0,sanitation_deficit:0,waste_deficit:0}),/greater than zero/);
  assert.throws(()=>normaliseWeights({...weights,water_deficit:-1}),/nonnegative/);
  const r=prioritise(example.areas,weights);assert.ok(Math.abs(Object.values(r.weights).reduce((a,b)=>a+b,0)-1)<1e-12);
  for(const x of r.rows.filter(x=>x.complete))assert.ok(Math.abs(Object.values(x.contributions).reduce((a,b)=>a+b,0)-x.lower)<1e-12);
});
test('weight stress test detects an actual ranking reversal and excludes incomplete rows',()=>{
  const s=sensitivity(example.areas,weights);assert.equal(s.count,2);assert.equal(s.scenarios,9);assert.ok(s.rows.every(x=>x.minRank===1&&x.maxRank===2));
});
test('ties receive honest position bounds and consistent competition ranks',()=>{
  const areas=[{...example.areas[0],id:'one'},{...example.areas[0],id:'two'}];
  const r=prioritise(areas,weights);assert.ok(r.rows.every(x=>x.rankBest===1&&x.rankWorst===2));
  const s=sensitivity(areas,weights);assert.ok(s.rows.every(x=>x.baselineRank===1&&x.minRank===1&&x.maxRank===1));
});
test('exact budget comparison deduplicates overlap, excludes infeasible options and breaks ties by cost',()=>{
  const r=compareBudget(example.interventions,30000);assert.equal(r.exact.covered.length,4);assert.equal(r.exact.cost,27000);assert.deepEqual(new Set(r.exact.selected),new Set(['option-b','option-c']));assert.ok(!r.exact.selected.includes('option-x'));assert.equal(r.comparedSubsets,8);
});
test('zero budget and zero-cost options are handled without divide-by-zero or fictitious coverage',()=>{
  assert.equal(compareBudget(example.interventions,0).exact.covered.length,0);
  const r=compareBudget([{id:'free',label:'free',cost:0,coverage_ids:['unit'],feasible:true}],0);assert.equal(r.exact.cost,0);assert.equal(r.exact.covered.length,1);assert.equal(r.greedy.covered.length,1);
  assert.throws(()=>compareBudget(example.interventions,NaN),/Budget/);
});
test('oversized exact scenarios are rejected before a synchronous enumeration can lock the UI',()=>{
  const large=Array.from({length:18},(_,i)=>({id:'x'+i,label:'option',cost:1,coverage_ids:Array.from({length:1000},(_,j)=>'unit-'+i+'-'+j),feasible:true,assumption_label:'Test input'}));
  assert.throws(()=>compareBudget(large,18),/workload limit/);
  const ds=clone();ds.interventions=large;assert.throws(()=>validateDataset(ds),/workload limit/);
});
test('same-window conflicting claims survive; different-day claims are not declared contradictions',()=>{
  const r=observationGroups(example.observations);assert.equal(r.length,2);assert.equal(r[0].claims.length,2);assert.equal(r[0].disputed,true);
  const changed=structuredClone(example.observations);changed[1].observed_at='2026-10-11';assert.equal(observationGroups(changed).some(x=>x.disputed),false);
});
test('quality metrics expose absent denominators and do not claim independent validation',()=>{
  const q=dataQuality(references);assert.equal(q.areas,0);assert.deepEqual(q.fields.water_deficit,{known:0,total:0});assert.equal(q.independentlyValidated,false);
  const s=dataQuality(example);assert.deepEqual(s.fields.sanitation_deficit,{known:2,total:4});assert.equal(s.unknownDates,2);assert.equal(s.disputes,1);
});
test('source search retrieves original notes and abstains on unsupported current or personal decisions',()=>{
  const cards=load('research.json').cards;
  assert.ok(searchEvidence(cards,'PMAY project infrastructure').results.some(x=>x.id==='pmay-infrastructure'));
  for(const q of ['What is current M/E toilet reliability?','How many people live in M/E now in 2026?','Give the percentage of toilets working this month in M/E','What is the 2027 M/E population?','Is my family eligible for housing?','What impact has our prototype achieved?'])assert.equal(searchEvidence(cards,q).status,'abstained',q);
  assert.equal(searchEvidence(cards,'quasar neutrino hypervelocity').status,'abstained');
});
test('exported CSV neutralises spreadsheet formulas and preserves unknowns',()=>{
  const a=clone();a.areas[0].name='=HYPERLINK("https://bad.test")';const csv=rankingCsv(prioritise(a.areas,weights));assert.ok(csv.includes("'=HYPERLINK"));assert.ok(!csv.includes('NaN'));assert.ok(csv.includes('"example-d"'));assert.ok(csv.includes('"sanitation_deficit"'));
});
test('input hash is a genuine SHA-256 digest',async()=>{
  assert.equal(await sha256('abc'),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});
test('rankings CSV carries its own synthetic status, date, weights, licence and input hash',()=>{
  const r=prioritise(example.areas,weights),csv=rankingCsv(r,{metadata:example.metadata,reviewAsOf:'2026-10-17',inputSha256:'abc123'});
  for(const s of ['dataset_title','synthetic_test_input','review_as_of','water_weight','dataset_licence','abc123','2026-10-17'])assert.ok(csv.includes(s),s);
});
