/* Template/contract checks in a minimal document harness, NOT browser QA. */
import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import * as engine from '../dist/lib/engine.mjs';
const load=async n=>JSON.parse(await fs.readFile(new URL('../dist/data/'+n,import.meta.url),'utf8'));
const [research,refs,example]=await Promise.all(['research.json','reference-points.json','example.json'].map(load));
const source=await fs.readFile(new URL('../dist/app.mjs',import.meta.url),'utf8');
const boundary=source.indexOf("document.addEventListener('click'");assert.ok(boundary>0);
const code=source.slice(0,boundary).replace(/^import .* from .*;\n/m,'')+'\nglobalThis.ui={state,renderOverview,renderAccess,renderPriorities,renderEvidence,renderScenarios,renderLibrary,mapLegend,markerDetail,invalidateRoute,exportObject,briefMarkdown};';
const elements=new Map();let removed=0;
function element(key){if(!elements.has(key))elements.set(key,{innerHTML:'',textContent:'',showModal(){},remove(){removed++;}});return elements.get(key);}
const context=vm.createContext({...engine,document:{querySelector:element},window:{},location:{hash:''},URL,structuredClone,console});
vm.runInContext(code,context,{filename:'app-render-contract.mjs'});
const ui=context.ui;ui.state.research=research;ui.state.references=refs;ui.state.examples=example;
const html=[];const checks=[];
for(const [mode,dataset]of [['research',refs],['sandbox',example]]){
  ui.state.mode=mode;ui.state.dataset=structuredClone(dataset);ui.state.origin=dataset.origins.features[0]?.geometry.coordinates||null;ui.state.lastRoute=null;
  for(const name of ['Overview','Access','Priorities','Evidence','Scenarios','Library']){
    const rendered=ui['render'+name]();assert.ok(rendered.includes('<h1'),mode+name);html.push({name:mode+'-'+name,html:rendered});
  }
  checks.push('All six view templates execute in '+mode+' mode');
}
ui.state.dataset=structuredClone(refs);ui.state.mode='research';const prior=ui.renderPriorities();assert.match(prior,/No comparable service observations/);assert.doesNotMatch(prior,/Example area A/);checks.push('Real-reference priorities withhold scores without area observations');
ui.state.dataset=structuredClone(example);ui.state.mode='sandbox';ui.state.origin=[0,0];ui.state.lastRoute=engine.routeToAmenities(example,[0,0],'toilets',10);assert.match(ui.renderAccess(),/667/);ui.state.maxSnap=4;ui.invalidateRoute();assert.equal(ui.state.lastRoute,null);assert.match(element('#route-results').innerHTML,/Parameters changed/);assert.equal(removed,2);checks.push('Snap-setting invalidation clears result text, route path and legend contract');
ui.state.mode='imported';ui.state.dataset=structuredClone(refs);ui.state.dataset.metadata.title='Municipal test import <img src=x onerror=bad>';ui.state.dataset.metadata.publisher='Municipal test publisher';ui.state.dataset.metadata.licence='Permission not independently verified';assert.doesNotMatch(ui.mapLegend(),/OpenStreetMap/);assert.match(ui.mapLegend(),/Supplied publisher/);const imported=ui.renderAccess();assert.match(imported,/USER-SUPPLIED/);assert.doesNotMatch(imported,/<img src=x/);checks.push('Generic imports preserve their own provenance and escape labels');
ui.markerDetail('osm-node-3205733664');assert.match(element('#dialog-content').innerHTML,/User-supplied point/);assert.doesNotMatch(element('#dialog-content').innerHTML,/Secondary reference location/);checks.push('Generic imported marker detail is not mislabelled as a secondary source');
ui.state.dataset=structuredClone(example);ui.state.mode='sandbox';ui.state.search=engine.searchEvidence(research.cards,'What is the 2027 M/E population?');assert.match(ui.renderEvidence(),/does not establish a current/);checks.push('Unsupported future/current measurement shows the abstention template');
ui.state.weights={water_deficit:0,sanitation_deficit:0,waste_deficit:0};assert.match(ui.renderPriorities(),/No ranking is calculated/);checks.push('All-zero weights render an unavailable result rather than stale scores');
ui.state.weights={water_deficit:40,sanitation_deficit:40,waste_deficit:20};ui.state.dataset=structuredClone(example);ui.state.dataset.metadata.publisher='Export provenance fixture';ui.state.dataset.metadata.licence='Supplied test restrictions';ui.state.dataset.metadata.source_url='https://example.org/aggregate-source';ui.state.hash='fixture-hash';const exported=ui.exportObject();assert.equal(exported.maintenanceInputs.length,example.interventions.length);assert.equal(exported.maintenanceInputs[0].assumption_label,example.interventions[0].assumption_label);const brief=ui.briefMarkdown(exported);for(const expected of ['Export provenance fixture','Supplied test restrictions','https://example.org/aggregate-source','fixture-hash','Raw service weights','Normalised weights',example.interventions[0].assumption_label,'Service claims','not adjudicated'])assert.ok(brief.includes(expected),expected);checks.push('Markdown and JSON exports retain input provenance, parameters, claim conflicts and maintenance assumptions');
ui.state.libraryTab='record-case';const realCase=ui.renderLibrary();for(const expected of ['REAL PUBLIC LISTING CASE','Bharti CHS','Universal CHS','Navi Disha','Unknown / Unknown','Records merged automatically','uninspected detail records'])assert.ok(realCase.includes(expected),expected);html.push({name:'real-public-record-case',html:realCase});checks.push('Real-record audit preserves distinct schemes, provenance and unknown status without a delay claim');
await fs.mkdir(new URL('../test-artifacts/',import.meta.url),{recursive:true});
await fs.writeFile(new URL('../test-artifacts/rendered-templates.json',import.meta.url),JSON.stringify(html,null,2)+'\n');
await fs.writeFile(new URL('../test-artifacts/template-checks.json',import.meta.url),JSON.stringify({status:'passed',checks,renderedViews:html.length,generated_at:new Date().toISOString(),boundary:'Minimal document harness executes real render functions; no browser layout, real DOM interactions or accessibility certification.'},null,2)+'\n');
console.log(JSON.stringify({status:'passed',checks:checks.length,renderedViews:html.length,browserValidated:false}));
