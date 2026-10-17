import {CRITERIA,CRITERIA_LABELS,validateDataset,safeUrl,routeToAmenities,prioritise,sensitivity,compareBudget,observationGroups,dataQuality,searchEvidence,rankingCsv,sha256,walkable,auditSchemeRecords} from './lib/engine.mjs';

const $=s=>document.querySelector(s);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const plain=value=>String(value??'').replace(/\[([^\]]+)\]\([^)]+\)/g,'$1').replace(/\*\*|`/g,'');
const fmt=value=>Number.isFinite(value)?new Intl.NumberFormat('en-IN',{maximumFractionDigits:0}).format(value):'Unknown';
const pct=value=>Number.isFinite(value)?(value*100).toFixed(1)+'%':'Unknown';
const link=(url,label='Read source ↗')=>safeUrl(url)?`<a class="source-link" href="${esc(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`:'<span class="fine-print">Source not verified</span>';
const pill=(label,kind='neutral')=>`<span class="pill ${kind}">${esc(label)}</span>`;
const empty=(title,message,action='')=>`<div class="empty"><div class="empty-icon" aria-hidden="true">⌁</div><h3>${esc(title)}</h3><p>${esc(message)}</p>${action}</div>`;
const sandboxButton='<button class="button secondary" data-action="sandbox">Explore synthetic sandbox ↗</button>';
const views=new Set(['overview','access','priorities','evidence','scenarios','library']);
const state={view:views.has(location.hash.slice(1))?location.hash.slice(1):'overview',mode:'research',dataset:null,research:null,examples:null,references:null,asOf:'2026-10-17',weights:{water_deficit:40,sanitation_deficit:40,waste_deficit:20},category:'toilets',maxSnap:80,avoidSteps:false,origin:null,lastRoute:null,routeInvalidated:false,zoom:1,pickingOrigin:false,query:'',search:null,budget:30000,libraryTab:'reports',datasetFilter:'',hash:null,fileName:null,mapProjection:null};
let toastTimer;
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('#toast').hidden=true;},5000);}
function heading(kicker,title,intro){return `<div class="page-heading"><div><div class="kicker">${esc(kicker)}</div><h1 id="view-title" tabindex="-1">${esc(title)}</h1><p class="intro">${esc(intro)}</p></div><div class="heading-side">${pill('Desk research · 17 Oct 2026')}<div style="margin-top:8px">No approved government pilot</div></div></div>`;}
function getRanking(){return prioritise(state.dataset.areas,state.weights,state.asOf);}
function modeText(){return state.dataset.metadata.is_synthetic?'Synthetic test inputs':state.mode==='imported'?'User-supplied · unverified':'Secondary reference records';}
async function setDataset(dataset,mode,textValue,fileName){
  validateDataset(dataset,state.asOf);
  state.dataset=dataset;state.mode=mode;state.origin=dataset.origins.features[0]?.geometry.coordinates.slice(0,2)||null;state.lastRoute=null;state.routeInvalidated=false;state.zoom=1;state.pickingOrigin=false;state.fileName=fileName;state.hash=null;
  const current=dataset;render();
  const hash=await sha256(textValue??JSON.stringify(dataset));if(state.dataset===current){state.hash=hash;}
}
function render(){
  if(!state.dataset||!state.research)return;
  document.title=`Seva Evidence · ${{overview:'Overview',access:'Service access',priorities:'Inspection priorities',evidence:'Evidence search',scenarios:'Scenario lab',library:'Research library'}[state.view]}`;
  for(const b of document.querySelectorAll('[data-view]')){const selected=b.dataset.view===state.view;b.classList.toggle('active',selected);b.setAttribute('aria-pressed',String(selected));}
  $('#data-mode').value=state.mode;
  const synthetic=state.dataset.metadata.is_synthetic;
  $('#location-label').textContent=synthetic?'Synthetic grid · no real locality':state.mode==='imported'?state.dataset.metadata.title:'Mumbai · M/E research context';
  const banner=$('#mode-banner');banner.className='mode-banner'+(synthetic?' synthetic':state.mode==='imported'?' imported':'');
  banner.innerHTML=synthetic?'<strong>SYNTHETIC SANDBOX</strong> · All roads, deficits, claims and costs here are test inputs. Calculated outputs are not Maharashtra service findings.':state.mode==='imported'?'<strong>IMPORTED DATA</strong> · User-supplied records, not independently verified. Data stay in this browser tab.':'<strong>RESEARCH REFERENCES</strong> · Three secondary OSM-derived transport points. No road network or current service baseline has been acquired.';
  const renderer={overview:renderOverview,access:renderAccess,priorities:renderPriorities,evidence:renderEvidence,scenarios:renderScenarios,library:renderLibrary}[state.view];
  $('#main').innerHTML=renderer();
}
function navigate(view){state.view=views.has(view)?view:'overview';history.replaceState(null,'','#'+state.view);render();$('#view-title')?.focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});}

function mapMarkup(compact=false){
  const ds=state.dataset,points=[];
  ds.network.features.forEach(f=>points.push(...f.geometry.coordinates));ds.amenities.features.forEach(f=>points.push(f.geometry.coordinates));if(state.origin)points.push(state.origin);
  const W=960,H=compact?480:550,M=65;
  if(!points.length)return empty('No spatial records imported','Import a permitted network and amenity file, or explore the labelled synthetic dataset.',sandboxButton);
  let minX=Math.min(...points.map(p=>p[0])),maxX=Math.max(...points.map(p=>p[0])),minY=Math.min(...points.map(p=>p[1])),maxY=Math.max(...points.map(p=>p[1]));
  if(maxX-minX<1e-8){minX-=.001;maxX+=.001;}if(maxY-minY<1e-8){minY-=.001;maxY+=.001;}
  const cosine=Math.max(.05,Math.cos((minY+maxY)/2*Math.PI/180));
  const scale=Math.min((W-2*M)/((maxX-minX)*cosine),(H-2*M)/(maxY-minY));
  const cx=(minX+maxX)/2,cy=(minY+maxY)/2;
  const project=c=>[W/2+(c[0]-cx)*cosine*scale,H/2-(c[1]-cy)*scale];
  state.mapProjection={unproject:([x,y])=>[cx+(x-W/2)/(scale*cosine),cy-(y-H/2)/scale]};
  const path=coords=>coords.map((c,i)=>{const [x,y]=project(c);return `${i?'L':'M'}${x.toFixed(3)},${y.toFixed(3)}`;}).join(' ');
  const roads=ds.network.features.map(f=>`<path d="${path(f.geometry.coordinates)}" class="${walkable(f.properties,state.avoidSteps)?'road':'blocked-road'}"><title>${esc(f.properties.name||f.id)}</title></path>`).join('');
  const route=state.lastRoute?.routes.find(r=>r.status==='candidate_route');
  const markers=ds.amenities.features.map(f=>{const [x,y]=project(f.geometry.coordinates);const name=f.properties.name;const right=x>W-270;return `<g><circle cx="${x}" cy="${y}" r="10" class="marker" data-marker="${esc(f.id??f.properties.id)}" tabindex="0" role="button" aria-label="Source for ${esc(name)}"><title>${esc(name)}</title></circle><text x="${x+(right?-17:17)}" y="${y-15}" text-anchor="${right?'end':'start'}">${esc(name.length>34?name.slice(0,32)+'…':name)}</text></g>`;}).join('');
  const origin=state.origin?(()=>{const [x,y]=project(state.origin);return `<circle class="origin" cx="${x}" cy="${y}" r="9"><title>Selected analysis origin; not a household</title></circle><text x="${x+15}" y="${y+25}">Analysis origin</text>`;})():'';
  const zoom=state.zoom,viewWidth=W/zoom,viewHeight=H/zoom;
  return `<svg class="map-svg ${state.pickingOrigin?'picking':''}" data-map="true" viewBox="${(W-viewWidth)/2} ${(H-viewHeight)/2} ${viewWidth} ${viewHeight}" role="group" aria-label="${ds.metadata.is_synthetic?'Synthetic test network and facilities':state.mode==='imported'?'User-supplied spatial inputs; completeness and boundary status unverified':'Reference location display; no road network or settlement boundary'}"><defs><pattern id="grid" width="42" height="42" patternUnits="userSpaceOnUse"><path d="M 42 0 L 0 0 0 42" fill="none" stroke="#e5eadd" stroke-width="1"/></pattern></defs><rect width="960" height="${H}" fill="url(#grid)"/><text x="28" y="32" class="map-eyebrow">${ds.metadata.is_synthetic?'ABSTRACT TEST GRID':state.mode==='imported'?'USER-SUPPLIED SPATIAL INPUTS':'ATTRIBUTED REFERENCE POINTS'}</text>${roads}${route?`<path class="route" d="${path(route.path)}"/>`:''}${markers}${origin}${!ds.network.features.length?`<text x="28" y="${H-25}" class="map-eyebrow">NO ROAD NETWORK · NO COVERAGE INFERENCE</text>`:''}</svg>`;
}
function dsTitle(){return state.dataset.metadata.title;}
function mapLegend(){
  const synthetic=state.dataset.metadata.is_synthetic;
  const attribution=synthetic?'Invented geometry':state.mode==='imported'?'<button class="button ghost small" data-action="metadata">Supplied publisher / licence ↗</button>':'<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors · ODbL</a>';
  return `<div class="map-legend"><span><i class="legend-symbol"></i>${synthetic?'Example facility':state.mode==='imported'?'Supplied point':'Reference location'}</span><span><i class="legend-symbol" style="background:#1d5744"></i>Selected origin</span>${state.lastRoute?.routes.some(r=>r.status==='candidate_route')?'<span data-route-legend><i class="legend-line"></i>Candidate graph route</span>':''}<span>${attribution}</span></div>`;
}
function invalidateRoute(){
  state.routeInvalidated=Boolean(state.lastRoute)||state.routeInvalidated;state.lastRoute=null;
  const target=$('#route-results');if(target)target.innerHTML=routeResults();
  document.querySelector('svg[data-map] .route')?.remove();document.querySelector('[data-route-legend]')?.remove();
}

function renderOverview(){
  const c=state.research.counts,q=dataQuality(state.dataset),synthetic=state.dataset.metadata.is_synthetic;
  return heading('Evidence before intervention','What can we verify before the next inspection?','Bring sources, places and uncertainty into one review. Compare access and evidence without turning old statistics or mapped assets into claims about today’s service.')+
    `<div class="stats-grid"><div class="stat"><div class="stat-label">Publications reviewed</div><div class="stat-number">${c.publications}</div><div class="stat-sub">Access depth marked for each paper</div></div><div class="stat"><div class="stat-label">Dataset / input candidates</div><div class="stat-number">${c.dataset_candidates}</div><div class="stat-sub">Access and licence limits recorded</div></div><div class="stat"><div class="stat-label">${synthetic?'Example map points':state.mode==='imported'?'Supplied map points':'Reference map points'}</div><div class="stat-number">${q.amenityFeatures}</div><div class="stat-sub">${synthetic?'Synthetic · not a real service inventory':'Not a complete amenity inventory'}</div></div><div class="stat"><div class="stat-label">${synthetic?'Example evidence claims':'Supplied service observations'}</div><div class="stat-number">${q.observations}</div><div class="stat-sub">${synthetic?'For testing the evidence workflow':'Independent field validation unavailable'}</div></div></div>
    <div class="policy-strip"><div><strong>Real public-record demonstration</strong><p>Inspect three attributed SRA listing rows. Shared CTS strings trigger review flags while every scheme stays separate and current status stays unknown.</p></div><button class="button" data-action="open-public-case">Open the record case ↗</button></div>
    <div class="two-col"><section class="card"><div class="card-head"><div><h2>${synthetic?'Try the analytical workflow':state.mode==='imported'?'Inspect the supplied spatial inputs':'Start with a bounded geography'}</h2><p class="card-subtitle">${synthetic?'Test routes, missing evidence and conflicting claims':state.mode==='imported'?esc(dsTitle()):'Govandi–Baiganwadi · three reference locations'}</p></div><button class="button ghost" data-view="access">Open map ↗</button></div><div class="small-map-wrap">${mapMarkup(true)}${mapLegend()}</div><p class="map-note">${synthetic?'This is an invented grid. Route distances are computed from the test geometry and do not describe Mumbai.':state.mode==='imported'?esc(state.dataset.metadata.limitations||'User-supplied geometry and source/permission claims have not been independently validated.'):'Coordinates were transcribed from secondary OSM-derived records. These are reference locations, not verified entrances, a ward boundary or measured service access.'}</p></section>
    <section class="card"><div class="card-head"><div><h2>Historical ward context</h2><p class="card-subtitle">M/E households · Census 2011</p></div>${pill('Historical','amber')}</div><div class="callout amber">Separate research context. These figures are ward-wide, not slum-only, and are never used as current scoring inputs.</div><div class="evidence-line"><div><h3>Treated tap water</h3><p>Access category reported in the census table</p></div><div class="evidence-value">82.8<span style="font-size:16px">%</span></div></div><div class="evidence-line"><div><h3>Tap within premises</h3><p>Different from no access to water</p></div><div class="evidence-value">53.6<span style="font-size:16px">%</span></div></div><div class="evidence-line"><div><h3>Latrine within premises</h3><p>Shared toilet access is a separate question</p></div><div class="evidence-value">35.8<span style="font-size:16px">%</span></div></div><div class="context-footer">Source: BMC Climate Action Plan 2022, Table 5, p.68; underlying Census 2011.<br>${link('https://www.mcgm.gov.in/irj/go/km/docs/documents/Environment/Climate/Mumbai%20Climate%20Action%20Plan.pdf','Read the historical source ↗')}</div></section></div>
    <div class="policy-strip"><div><strong>Existing systems already do much of this.</strong><p>SRA has GIS. SBM-U 2.0 specifies functional-asset monitoring. Swachhata supports confirmation and reopening. The question to test is whether this evidence workflow improves a specific local review.</p></div><button class="button" data-view="evidence">Inspect the evidence ↗</button></div>
    <section class="card"><div class="card-head"><div><h2>Three gates before an operational pilot</h2><p class="card-subtitle">A working prototype is the beginning of validation.</p></div>${pill('Adoption unvalidated','neutral')}</div><div class="next-steps"><div class="next-step"><span class="step-index">01</span><div><h3>Acquire the minimum lawful data</h3><p>Obtain a usable network, approved area and dated asset records. Missing data remain unknown.</p></div></div><div class="next-step"><span class="step-index">02</span><div><h3>Check the actual workflow</h3><p>Review one inspection with the ward, service department and operator. Establish what existing systems already answer.</p></div></div><div class="next-step"><span class="step-index">03</span><div><h3>Validate the incremental value</h3><p>Compare evidence quality and review effort. No time saving or service improvement has been demonstrated.</p></div></div></div></section>`;
}

function renderAccess(){
  const ds=state.dataset;
  return heading('Access is more than proximity','Follow the path. Keep the limits visible.','Calculate candidate walking distances on an imported graph. Unmapped facilities, barriers, opening hours and actual service availability remain separate questions.')+
  `<section class="card"><div class="controls"><div class="field"><label for="amenity-category">Mapped amenity</label><select id="amenity-category">${[['toilets','Toilets'],['water_point','Water points'],['clinic','Clinics'],['school','Schools'],['transport_stop','Transport stops']].map(([v,t])=>`<option value="${v}" ${state.category===v?'selected':''}>${t}</option>`).join('')}</select></div><div class="field"><label for="snap-limit">Maximum node snap (metres)</label><input id="snap-limit" type="number" min="0" max="1000" value="${state.maxSnap}"></div><label class="check-field"><input class="checkbox" type="checkbox" id="avoid-steps" ${state.avoidSteps?'checked':''}> Avoid mapped steps</label><button class="button secondary" data-action="pick-origin">${state.pickingOrigin?'Click on the map…':'Set origin on map'}</button><button class="button primary" data-action="calculate-route">Calculate access ↗</button></div>
  ${!ds.network.features.length?'<div class="callout amber">No road network is present. Distances and coverage are unavailable; three reference markers cannot establish walking access. Import a lawful dataset or use the labelled sandbox.</div>':'<div class="callout">Candidate routes follow supplied graph connections and walking tags. Snapping to nodes can overestimate distance and create unverified connector segments; inspect every route. Avoiding steps is not a wheelchair-accessibility certification.</div>'}
  <div class="access-layout"><div><div class="card-head"><div><h2 style="font-size:21px">${esc(ds.metadata.title)}</h2><p class="card-subtitle">${state.origin?'Origin: '+state.origin.map(x=>x.toFixed(5)).join(', ')+' · chosen analysis point':'No analysis origin selected'}</p></div><div class="map-tools"><button class="icon-button" aria-label="Zoom out" data-action="zoom-out">−</button><button class="icon-button" aria-label="Zoom in" data-action="zoom-in">+</button></div></div><div class="small-map-wrap">${mapMarkup()}${mapLegend()}</div><p class="map-note">Select a marker to inspect its source. ${esc(ds.metadata.limitations||'Source completeness, entrances, access conditions and service performance require independent checks.')}</p><div class="inline-actions">${sandboxButton}<button class="button ghost" data-action="metadata">Inspect data provenance ↗</button></div></div><div id="route-results">${routeResults()}</div></div></section>`;
}
function routeResults(){
  const r=state.lastRoute;
  if(!r)return empty(state.routeInvalidated?'Parameters changed — recalculate':'No access calculation yet','Choose an origin and calculate. Empty or unconnected inputs produce an explicit unavailable result.');
  if(r.status==='origin_not_routable')return `<div class="callout amber">Origin is not routable within the snap limit. This does not mean residents have no access; the graph may be missing or incomplete.</div><p class="fine-print">Accepted walking ways: ${r.graph.acceptedWays}. Excluded ways: ${r.graph.rejectedWays}. Network nodes: ${r.graph.nodes}.</p>`;
  if(r.status==='no_mapped_candidates')return `<div class="callout amber">No candidate of this category is mapped in the supplied data. Coverage is unknown, not zero.</div>`;
  return `<h3>Candidate access results</h3><p class="fine-print">Origin-to-node connector: ${fmt(r.originSnapM)} m. ${r.graph.assumedTopologyWays?'Some ways use coordinate/layer topology; source node IDs were absent.':''}</p>${r.routes.map(x=>`<div class="route-item"><h3>${esc(x.name)}</h3>${x.status==='candidate_route'?`${pill('Candidate graph route','blue')}<div class="route-distance">${fmt(x.distanceM)} <span style="font:12px sans-serif">m</span></div><p>Straight line: ${fmt(x.straightLineM)} m · destination snap: ${fmt(x.amenitySnapM)} m</p><p>Includes unverified origin/destination connectors. Availability, fees, hours and route safety are unknown.</p>`:`${pill(({disconnected:'Disconnected in supplied graph',access_restricted:'Mapped access restriction',amenity_not_routable:'Destination not routable'})[x.status]||x.status,'amber')}<p style="margin-top:9px">Distance unavailable. This is not a zero-distance trip or a verified lack of service.</p>`}</div>`).join('')}`;
}
function calculateRoute(){try{if(!state.origin)throw new Error('Set an analysis origin on the map first.');state.lastRoute=routeToAmenities(state.dataset,state.origin,state.category,state.maxSnap,state.avoidSteps);state.routeInvalidated=false;render();}catch(e){toast(e.message);}}

function renderPriorities(){
  return heading('Explainable inspection support','Show the score. Show what is missing.','Compare source-supplied 0–1 service deficits. Weights are choices, not objective truths. Unknown values produce bounds; no housing eligibility or relocation is decided.')+
  `<section class="card" style="margin-bottom:20px"><div class="card-head"><div><h2>Review criteria</h2><p class="card-subtitle">Normalised deficits must come from a documented, comparable measurement method.</p></div>${pill(modeText(),state.dataset.metadata.is_synthetic?'amber':'neutral')}</div><div class="weight-grid">${CRITERIA.map(c=>`<div class="weight"><label for="weight-${c}">${CRITERIA_LABELS[c]}<output id="label-${c}">${fmt(state.weights[c])}</output></label><input id="weight-${c}" data-weight="${c}" type="range" min="0" max="100" value="${state.weights[c]}" aria-label="${CRITERIA_LABELS[c]} weight"></div>`).join('')}</div><div class="weights-footer"><p class="fine-print" style="margin:0">Weights are normalised to sum to one. Missing criteria are not silently replaced or dropped.</p><div class="field"><label for="analysis-date">Review as of</label><input id="analysis-date" type="date" value="${state.asOf}"></div><button class="button secondary small" data-action="reset-weights">Reset weights</button></div></section><div id="priority-results">${priorityResults()}</div>`;
}
function priorityResults(){
  if(!state.dataset.areas.length)return `<section class="card">${empty('No comparable service observations','Historical ward percentages and reference points cannot be converted into current area deficits. Import observations with a source, method and date, or try the synthetic examples.',sandboxButton)}</section>`;
  let result,stress;try{result=getRanking();stress=sensitivity(state.dataset.areas,state.weights);}catch(e){return `<div class="callout red" role="alert">${esc(e.message)} No ranking is calculated.</div>`;}
  const groups=observationGroups(state.dataset.observations);
  return `<div class="callout blue">Weights: ${CRITERIA.map(c=>`${CRITERIA_LABELS[c]} ${pct(result.weights[c])}`).join(' · ')}. Score bounds use 0–1 for each unknown criterion. Position bounds include uncertainty and ties; they are not approved intervention orders.</div><section class="card" style="margin-bottom:20px"><div class="card-head"><div><h2>Observed deficits and evidence gaps</h2><p class="card-subtitle">Table order uses the lower score bound; inspect the whole interval.</p></div><button class="button secondary small" data-action="download-rankings">Download CSV</button></div><div class="table-wrap"><table><thead><tr><th>Analysis area</th><th>Score interval</th><th>Possible position</th><th>Evidence</th></tr></thead><tbody>${result.rows.map(r=>`<tr><td><strong>${esc(r.name)}</strong><span class="sub">${esc(r.method)}</span></td><td>${r.hasEvidence?`${r.lower.toFixed(3)}${Math.abs(r.upper-r.lower)>1e-12?' – '+r.upper.toFixed(3):''}`:'Not ranked'}<div class="score-bar">${CRITERIA.map((c,i)=>r.contributions[c]===null?'':`<span class="${['water','sanitation','waste'][i]}" style="width:${r.contributions[c]*100}%" title="${CRITERIA_LABELS[c]} contribution ${r.contributions[c].toFixed(3)}"></span>`).join('')}</div>${r.missing.length?`<span class="missing-chip">Unknown: ${r.missing.map(c=>CRITERIA_LABELS[c]).join(', ')}</span>`:''}</td><td>${r.rankBest===null?'Insufficient evidence':r.rankBest+(r.rankWorst!==r.rankBest?' – '+r.rankWorst:'')}<span class="sub">${r.complete?'All three criteria supplied':'Verification needed'}</span></td><td>${r.observed_at?esc(r.observed_at):pill('Date unknown','amber')}<span class="sub">${r.ageDays!==null?r.ageDays+' days before review':'Age cannot be assessed'}</span>${state.dataset.metadata.is_synthetic?'<span class="fine-print">Authored fixture</span>':link(r.source_url)}</td></tr>`).join('')}</tbody></table></div><div class="context-footer">The prototype has not established that source-supplied deficits are accurate, representative or comparable. No measured household coverage or legal entitlement follows from a score.</div></section>
  <div class="two-col equal"><section class="card"><div class="card-head"><div><h2>Weight sensitivity</h2><p class="card-subtitle">Baseline plus ±20% factor combinations, renormalised</p></div>${pill(stress.scenarios+' test settings','blue')}</div>${stress.rows.length?`<div class="table-wrap"><table><thead><tr><th>Complete-data area</th><th>Baseline rank</th><th>Tested rank range</th></tr></thead><tbody>${stress.rows.map(r=>`<tr><td>${esc(r.name)}</td><td>${r.baselineRank}</td><td>${r.minRank} – ${r.maxRank} ${r.minRank!==r.maxRank?pill('Unstable','amber'):pill('Stable in test')}</td></tr>`).join('')}</tbody></table></div>`:'<p class="fine-print">No complete-data rows are available for this sensitivity test.</p>'}<div class="context-footer">A software stress test, not a validated preference distribution, fairness proof or confidence interval. Complete rows only; ties use competition ranks.</div></section><section class="card"><div class="card-head"><div><h2>Claim conflicts stay visible</h2><p class="card-subtitle">Grouped by asset, service and observation date</p></div></div>${groups.length?groups.map(g=>`<div class="claim"><p><strong>${esc(g.assetId)}</strong> · ${esc(g.service)}</p><small>${esc(g.date)} ${g.disputed?pill('Conflicting reports','red'):pill('No recorded conflict')}</small>${g.claims.map(c=>`<p class="fine-print" style="margin-top:8px">${esc(c.evidence_type.replaceAll('_',' '))}: <strong>${esc(c.value.replaceAll('_',' '))}</strong><br>${esc(c.note||'')}</p>`).join('')}</div>`).join(''):'<p class="fine-print">No observation claims supplied. The absence of records is not evidence of a working service.</p>'}<div class="context-footer">Different days or services are not automatically disputes. No report is silently overwritten or certified as the truth.</div></section></div>`;
}

function renderEvidence(){return heading('Curated, source-grounded search','Ask the evidence. Accept the unknowns.','Search a small set of reviewed source notes. This is lexical retrieval over evidence cards, not an LLM, a full-document corpus or an authority for current household decisions.')+
 `<section class="search-panel"><form id="evidence-form" class="search-form"><label class="visually-hidden" for="evidence-query">Evidence question</label><input id="evidence-query" maxlength="600" placeholder="Does PMAY-U 2.0 include project infrastructure?" value="${esc(state.query)}"><button type="submit" class="button primary">Search ↗</button></form><div class="suggestions">${['PMAY completed project infrastructure','Swachhata citizen reopening','SBM functional asset monitoring','Current M/E toilet reliability'].map(q=>`<button class="suggestion" data-search="${esc(q)}">${esc(q)}</button>`).join('')}</div></section><div id="evidence-results">${evidenceResults()}</div>`;}
function evidenceResults(){
  if(!state.search)return `<div class="two-col equal"><section class="card"><h2 style="font-size:23px">Every result has a source trail</h2><p class="fine-print">${state.research.cards.length} curated cards retain publisher, observation period, section/table and access date. Follow the original document before operational use.</p></section><section class="card"><h2 style="font-size:23px">Some questions need a different answer</h2><p class="fine-print">Current local service measurements, household eligibility, relocation and prototype impact are not established by this corpus. The workbench abstains on these requests.</p></section></div>`;
  const s=state.search;
  return `<div class="callout ${s.status==='abstained'?'amber':'blue'}" id="search-answer">${esc(s.answer)}</div>${s.status==='abstained'&&s.results.length?'<p class="search-status">Related background only. These notes do not establish the missing current fact.</p>':`<p class="search-status">${s.results.length} matching source notes · BM25-style lexical retrieval</p>`}${s.results.map(c=>`<article class="result-card"><div class="result-meta">${pill(c.kind==='secondary_reference'?'Secondary reference':'Reviewed source note',c.kind==='secondary_reference'?'amber':'neutral')}<span>${esc(c.id)}</span><span>Matched: ${esc(c.matched.join(', '))}</span></div><h3>${esc(c.title)}</h3><p>${esc(c.text)}</p><div class="result-meta"><span>${esc(c.publisher)}</span><span>·</span><span>${esc(c.observation_period)}</span></div><div class="result-source"><span>${esc(c.locator)} · accessed ${esc(c.access_date)}</span>${link(c.source_url)}</div></article>`).join('')}${!s.results.length?empty('No supported source note','Try a narrower question about the reviewed policies or consult the competent authority for missing information.'):''}`;
}
function runSearch(query){state.query=query;state.search=searchEvidence(state.research.cards,query);if(state.view!=='evidence')navigate('evidence');else{$('#evidence-results').innerHTML=evidenceResults();$('#evidence-query').value=query;}}

function renderScenarios(){return heading('A bounded, hypothetical comparison','Compare the trade-offs. Keep people out of the solver.','Compare maintenance options under a stated budget. Costs, feasibility and coverage must be supplied. The prototype does not allocate housing, choose residents or recommend relocation.')+
  `${!state.dataset.interventions.length?`<section class="card">${empty('No verified intervention costs or options','Real costs, O&M, land constraints and resident preferences have not been acquired. Explore an explicitly hypothetical maintenance example or import supported inputs.',sandboxButton)}</section>`:`<div class="callout amber">${state.dataset.metadata.is_synthetic?'All options and rupee amounts below are invented test inputs.':'Imported estimates and feasibility labels are user-supplied and unverified.'} Coverage units are abstract IDs, not independently counted households. O&M, service quality and causal impact are not modelled.</div><section class="card" style="margin-bottom:20px"><div class="controls"><div class="field"><label for="scenario-budget">Hypothetical budget (INR)</label><input id="scenario-budget" type="number" min="0" max="10000000000" value="${state.budget}"></div><p class="fine-print" style="margin:0 0 8px">Exact enumeration of up to 18 options; overlapping coverage IDs counted once.</p></div><div id="scenario-results">${scenarioResults()}</div></section><section class="card"><div class="card-head"><h2>Supplied option assumptions</h2></div><div class="table-wrap"><table><thead><tr><th>Option</th><th>Input cost</th><th>Coverage IDs</th><th>Feasibility</th></tr></thead><tbody>${state.dataset.interventions.map(x=>`<tr><td><strong>${esc(x.label)}</strong><span class="sub">${esc(x.assumption_label)}</span></td><td>₹${fmt(x.cost)}</td><td>${esc([...new Set(x.coverage_ids)].join(', '))}</td><td>${pill(x.feasible?'Input: feasible':'Input: excluded',x.feasible?'neutral':'amber')}</td></tr>`).join('')}</tbody></table></div></section>`}`;}
function scenarioResults(){
  let r;try{r=compareBudget(state.dataset.interventions,state.budget);}catch(e){return `<div class="callout red" role="alert">${esc(e.message)}</div>`;}
  return `<div class="two-col equal" style="margin-bottom:0"><div><span class="section-label">Exact conditional solution</span><div class="scenario-total">${r.exact.covered.length} <span style="font:12px sans-serif">distinct units</span></div><p class="fine-print">Input cost: ₹${fmt(r.exact.cost)} of ₹${fmt(r.budget)}<br>Selected: ${esc(r.exact.selected.join(', ')||'None')}<br>Covered: ${esc(r.exact.covered.join(', ')||'None')}</p></div><div><span class="section-label">Greedy gain-per-cost comparator</span><div class="scenario-total">${r.greedy.covered.length} <span style="font:12px sans-serif">distinct units</span></div><p class="fine-print">Input cost: ₹${fmt(r.greedy.cost)}<br>Selected: ${esc(r.greedy.selected.join(', ')||'None')}<br>${r.comparedSubsets} feasible-option subsets considered by the exact search.</p></div></div><div class="context-footer">The exact method maximises distinct supplied coverage units, then prefers lower cost. This is optimal only under those input assumptions; it is not proof of social fairness, legal feasibility or service improvement.</div>`;
}

function renderLibrary(){return heading('Research you can inspect','Trace the claim back to the source.','Read the literature, inspect access failures and download the research package. Public-source notes are distinguished from primary documents, secondary references and prospective data.')+
 `<div class="tabs" aria-label="Research sections">${[['reports','Reports & audit'],['record-case','Real record case'],['papers','14 publications'],['datasets','Data inventory'],['cards','Source cards']].map(([v,t])=>`<button class="tab-button ${state.libraryTab===v?'active':''}" data-library="${v}" aria-pressed="${state.libraryTab===v}">${esc(t)}</button>`).join('')}</div><div id="library-content">${libraryContent()}</div>`;}
function publicCaseMarkup(){
 const c=state.research.publicCase;if(!c)return empty('Public case not loaded','The source snapshot is unavailable; no record audit was calculated.');
 const a=auditSchemeRecords(c.records);
 const describe=groups=>groups.map(g=>`${g.ward} / ${g.locality} / ${g.key}: ${g.localIds.length} distinct records`).join('; ')||'None in this sample';
 return `<div class="callout blue"><strong>REAL PUBLIC LISTING CASE</strong> · Three deliberately selected primary-source rows. This case is independent of the spatial dataset selector. Current project status and service conditions remain unknown.</div><section class="card"><div class="card-head"><div><h2>${esc(c.metadata.title)}</h2><p class="card-subtitle">Retrieved ${esc(c.metadata.accessed_at)}. Retrieval is not an observation or update date.</p></div><button class="button secondary" data-action="download-public-case">Export case (.json)</button></div><p>${link(c.metadata.source_url,'Check the primary SRA listing ↗')}</p><div class="table-wrap"><table><thead><tr><th>Source row / scheme</th><th>Ward / village</th><th>Raw CTS</th><th>Raw proposal</th><th>Current status / update date</th></tr></thead><tbody>${c.records.map(r=>`<tr><td><strong>${esc(r.listing_serial)} · ${esc(r.name)}</strong><span class="sub">Local snapshot key: ${esc(r.local_id)}</span></td><td>${esc(r.ward)} / ${esc(r.locality)}</td><td>${esc(r.cts_raw)}</td><td>${esc(r.proposal_raw)}</td><td>Unknown / Unknown</td></tr>`).join('')}</tbody></table></div><div class="context-footer">Serial positions and local snapshot keys are not verified durable official scheme IDs. The inspected listing has no status/update-date columns; those may exist in uninspected detail records or other systems.</div></section><section class="card subsection"><h2>Computed checks on these ${a.count} records</h2><dl class="metadata-list"><dt>Exact CTS-context collision</dt><dd>${esc(describe(a.exactGroups))}</dd><dt>Tentative formatting association</dt><dd>${esc(describe(a.candidateGroups))}. Uppercase and remove ASCII spaces/hyphens for review only. This is not a validated cadastral equivalence rule.</dd><dt>Non-placeholder proposals</dt><dd>${a.suppliedProposalCount} / ${a.count}</dd><dt>Listing status / update dates</dt><dd>${a.suppliedStatusCount} / ${a.count} and ${a.suppliedUpdateCount} / ${a.count} supplied. Unknowns are not delay findings.</dd><dt>Records merged automatically</dt><dd>${a.automaticallyMerged}. All source records remain separate.</dd></dl><div class="callout amber">Next evidence required: authoritative project IDs and a permitted crosswalk, relevant detail/status records, reuse terms and an officer's workflow review. A spreadsheet can perform this audit; incremental product value is unvalidated.</div><p class="fine-print">${esc(c.metadata.selection)} ${esc(c.metadata.reuse_caveat)}</p><p class="fine-print">No geometry, household data or current service observations were acquired for these schemes.</p></section>`;
}
function libraryContent(){
  const r=state.research;
  if(state.libraryTab==='record-case')return publicCaseMarkup();
  if(state.libraryTab==='papers')return `<section class="card"><div class="card-head"><div><h2>Fourteen journal publications</h2><p class="card-subtitle">Methods, samples, limitations and access depth are marked in the review.</p></div></div>${r.papers.map(p=>`<details class="paper-detail"><summary>${esc(p.id)} · ${esc(p.title)}</summary><p>${esc(plain(p.metadata))}</p><dl class="paper-fields">${Object.entries(p.fields).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(plain(v))}</dd>`).join('')}</dl>${p.url?link(p.url,'Publication / DOI ↗'):''}</details>`).join('')}<div class="context-footer">Full-text access varies. L14's 2019 author manuscript was read in full; final 2021 journal metadata/abstract were verified separately. One additional government impact report is documented in the full review.</div></section>`;
  if(state.libraryTab==='datasets')return `<section class="card"><div class="card-head"><div><h2>${r.datasets.length} dataset and input candidates</h2><p class="card-subtitle">A documented download route is not a successful data acquisition.</p></div></div><div class="field" style="margin-bottom:16px"><label for="dataset-filter">Filter by source, use or access status</label><input id="dataset-filter" value="${esc(state.datasetFilter)}" placeholder="Try Census, partner, roads, metadata…"></div><div id="dataset-table">${datasetTable()}</div></section>`;
  if(state.libraryTab==='cards')return `<section class="card"><h2>Reviewed source notes</h2><p class="fine-print">These are curated paraphrases with source locations, not the complete government documents. They support the evidence search.</p>${r.cards.map(c=>`<details class="paper-detail"><summary>${esc(c.title)}</summary><p>${esc(c.text)}</p><p>${esc(c.publisher)} · ${esc(c.observation_period)} · ${esc(c.locator)}</p>${link(c.source_url)}</details>`).join('')}</section>`;
  return `<div class="callout">Research separates verified facts, reasonable inferences and untested hypotheses. The prototype is working software; service outcomes and government adoption remain unvalidated.</div><div class="file-list">${r.files.map(f=>{const inner=`<span class="file-icon" aria-hidden="true">▤</span><span><span class="file-title">${esc(f.name)}</span><br><small>${fmt(f.bytes)} bytes · SHA-256 recorded</small></span>`;return window.__SEVA_FILES__?`<button class="file-item" data-action="download-report" data-report="${esc(f.name)}">${inner}</button>`:`<a class="file-item" href="${esc(f.url)}" download="${esc(f.name)}">${inner}</a>`;}).join('')}</div><section class="card subsection"><div class="card-head"><div><h2>Current data quality</h2><p class="card-subtitle">Checks describe the loaded inputs, not a field-validated service model.</p></div><button class="button ghost" data-action="metadata">View provenance ↗</button></div>${qualityMarkup()}</section><section class="card subsection"><h2>Public scheme listing excerpt</h2><p class="fine-print">Three locality leads from the visible SRA table; no coordinates, current milestone or operational service status established.</p><div class="table-wrap"><table><thead><tr><th>Scheme</th><th>Ward / locality</th><th>CTS</th><th>Proposal / update date</th></tr></thead><tbody>${r.schemes.map(s=>`<tr><td>${esc(s.name)}</td><td>${esc(s.ward)} · ${esc(s.locality)}</td><td>${esc(s.cts)}</td><td>Not established</td></tr>`).join('')}</tbody></table></div><div class="context-footer">${link('https://dms.sra.gov.in/SRAPUBLIC/','Original SRA listing ↗')} · Shared CTS numbers are not unique scheme identifiers.</div></section>`;
}
function datasetTable(){const filter=state.datasetFilter.toLowerCase();const rows=state.research.datasets.filter(d=>Object.values(d).some(v=>String(v).toLowerCase().includes(filter)));return `<p class="fine-print">${rows.length} matching candidates</p><div class="table-wrap"><table><thead><tr><th>Dataset / input</th><th>Observation period</th><th>Access / readiness</th><th>Licence boundary</th></tr></thead><tbody>${rows.map(d=>`<tr><td><strong>${esc(d.dataset_id)} · ${esc(d.dataset_name)}</strong><span class="sub">${esc(d.publisher)}</span>${link(d.direct_source_url)}</td><td>${esc(d.observation_period)}</td><td>${pill(d.readiness.replaceAll('_',' '),'neutral')}<span class="sub">${esc(d.access_result)}</span></td><td>${esc(d.licence)}</td></tr>`).join('')}</tbody></table></div>`;}
function qualityMarkup(){const q=dataQuality(state.dataset);return `<div class="inline-actions" style="margin-bottom:18px"><span class="data-chip">${q.networkFeatures} input network features</span><span class="data-chip">${q.amenityFeatures} input amenities</span><span class="data-chip">${q.areas} area records</span><span class="data-chip">${q.disputes} same-window claim conflicts</span></div>${q.areas?`<div class="table-wrap"><table><thead><tr><th>Supplied field</th><th>Nonmissing / records</th><th>Completeness</th></tr></thead><tbody>${CRITERIA.map(c=>`<tr><td>${CRITERIA_LABELS[c]}</td><td>${q.fields[c].known} / ${q.fields[c].total}</td><td><span class="progress-meter"><span style="width:${q.fields[c].known/q.fields[c].total*100}%"></span></span>${pct(q.fields[c].known/q.fields[c].total)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="fine-print">No current area-service records supplied; completeness cannot be calculated over an empty denominator.</p>'}<p class="fine-print">${q.unknownDates} supplied area records have unknown observation dates. No independent field-accuracy test has been performed.</p>`;}

function modal(title,html){$('#dialog-title').textContent=title;$('#dialog-content').innerHTML=html;$('#data-dialog').showModal();}
function showImport(){modal('Import a public / aggregate dataset',`<p class="fine-print">Import a JSON file using the documented schema. Files stay in this tab and are not sent to a server. Use asset/area evidence; remove household IDs, names, phone numbers and other personal fields.</p><div class="callout amber">A supplied source or licence label is not independently verified by the prototype. Mark test data as synthetic.</div><div class="drop-zone"><label for="dataset-file" class="section-label">Choose a dataset JSON · maximum 5 MB</label><p><input id="dataset-file" type="file" accept=".json,application/json"></p></div><p id="import-error" class="dialog-error" role="alert"></p><div class="inline-actions"><button class="button secondary" data-action="download-template">Download synthetic template</button><button class="button ghost" data-action="download-schema">Read / download input schema ↗</button></div>`);}
async function importFile(file){
  const status=$('#import-error');
  try{
    if(!file) return;if(file.size>5*1024*1024)throw new Error('File exceeds the 5 MB prototype limit.');
    const text=await file.text();const dataset=JSON.parse(text.replace(/^\uFEFF/,''));validateDataset(dataset,state.asOf);
    const option=$('#data-mode option[value="imported"]');option.disabled=false;
    await setDataset(dataset,'imported',text,file.name);state.imported=structuredClone(dataset);state.importedText=text;state.importedName=file.name;$('#data-dialog').close();toast('Dataset imported locally. Source claims remain independently unverified.');return true;
  }catch(e){if(status)status.textContent='Import rejected: '+e.message;const input=$('#dataset-file');if(input)input.value='';return false;}
}
function showMetadata(){const m=state.dataset.metadata;modal('Source and analysis provenance',`<div class="callout ${m.is_synthetic?'amber':'blue'}">${esc(modeText())}. ${esc(m.limitations||'The source, completeness and service performance have not been independently validated.')}</div><dl class="metadata-list">${[['Dataset',m.title],['Publisher',m.publisher],['Scope',m.geographic_scope],['Observation date',m.observed_at||'Unknown; not replaced by retrieval date'],['Retrieved',m.retrieved_at||'Unknown'],['Licence',m.licence],['Loaded file',state.fileName||'In-memory dataset'],['SHA-256',state.hash||'Unavailable / still calculating']].map(([k,v])=>`<dt>${esc(k)}</dt><dd class="${k==='SHA-256'?'monospace':''}">${esc(v)}</dd>`).join('')}</dl>${!m.is_synthetic?link(m.source_url):'<p class="fine-print">Synthetic input is authored locally, not an external source measurement.</p>'}`);}
function markerDetail(id){const f=state.dataset.amenities.features.find(f=>String(f.id??f.properties.id)===id);if(!f)return;const p=f.properties;modal(p.name,`<div class="callout ${state.dataset.metadata.is_synthetic?'amber':'blue'}">${state.dataset.metadata.is_synthetic?'Synthetic facility. No real asset, availability or service condition is represented.':state.mode==='imported'?'User-supplied point and source claims. Completeness, public entrance, operating status and accessibility have not been independently validated.':'Secondary reference location. Existence, exact entrance, current operation and accessibility need independent checks.'}</div><dl class="metadata-list"><dt>Category</dt><dd>${esc(p.category.replaceAll('_',' '))}</dd><dt>Coordinates</dt><dd>${f.geometry.coordinates.map(x=>x.toFixed(5)).join(', ')} · WGS84 longitude, latitude</dd><dt>Location type</dt><dd>${esc(p.location_type||'Supplied point; entrance/operating status not verified')}</dd><dt>Observation date</dt><dd>${esc(p.observation_date||'Unknown')}</dd></dl>${p.source_url?link(p.source_url,state.mode==='research'?'Record used for transcription ↗':'Supplied per-feature source ↗'):''}<div style="margin-top:12px">${p.osm_url?link(p.osm_url,'Reported OpenStreetMap feature ↗'):''}</div>`);}
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function exportObject(){let rank=null,stress=null,error=null;try{rank=getRanking();stress=sensitivity(state.dataset.areas,state.weights);}catch(e){error=e.message;}
 let scenario=null,scenarioError=null;try{if(state.dataset.interventions.length)scenario=compareBudget(state.dataset.interventions,state.budget);}catch(e){scenarioError=e.message;}
 return {prototype:'Seva Evidence 0.1.0',reviewAsOf:state.asOf,generatedAt:new Date().toISOString(),dataKind:modeText(),synthetic:state.dataset.metadata.is_synthetic,datasetMetadata:state.dataset.metadata,inputSha256:state.hash,inputFile:state.fileName,parameters:{rawWeights:state.weights,amenityCategory:state.category,maxNodeSnapMetres:state.maxSnap,avoidSteps:state.avoidSteps,origin:state.origin,hypotheticalBudget:Number.isFinite(state.budget)?state.budget:null},quality:dataQuality(state.dataset),ranking:rank,sensitivity:stress,analysisError:error,access:state.lastRoute,maintenanceInputs:state.dataset.interventions,maintenanceScenario:scenario,scenarioError,evidenceClaims:observationGroups(state.dataset.observations),evidenceQuery:state.query,evidenceSearch:state.search,sourceCards:state.research.cards.map(({id,source_url,observation_period,locator,access_date})=>({id,source_url,observation_period,locator,access_date})),limits:['No current service baseline or household coverage established.','No independent field validation, impact estimate or government adoption.','No eligibility, beneficiary allocation or relocation decisions.','Graph routes and scenario outputs are conditional on supplied inputs; missing evidence remains unknown.']};}
function briefMarkdown(o){
  const m=o.datasetMetadata,p=o.parameters;
  const areaSummary=o.analysisError?'Unavailable: '+o.analysisError:o.ranking?.rows.length?o.ranking.rows.map(r=>`- ${r.name}: ${r.hasEvidence?r.lower.toFixed(3)+' to '+r.upper.toFixed(3):'not ranked'}; unknown criteria: ${r.missing.join(', ')||'none'}; observation date: ${r.observed_at||'unknown'}; source: ${r.source_url||'not supplied'}`).join('\n'):'No comparable area-service observations supplied.';
  const claimSummary=o.evidenceClaims.length?o.evidenceClaims.map(g=>`- Asset ${g.assetId}; service ${g.service}; date ${g.date}; ${g.disputed?'CONFLICT — not adjudicated':'claims not independently verified'}\n${g.claims.map(c=>`  - ${c.value}; evidence type: ${c.evidence_type}; source: ${c.source_url||'synthetic / not supplied'}`).join('\n')}`).join('\n'):'No service claims supplied.';
  const optionSummary=o.maintenanceInputs.map(x=>`- ${x.id} (${x.label}): INR ${x.cost}; input feasible: ${x.feasible}; coverage IDs: ${[...new Set(x.coverage_ids)].join(', ')||'none'}; assumption: ${x.assumption_label}`).join('\n');
  return `# Seva Evidence — review brief

Review as of: ${o.reviewAsOf}

Generated: ${o.generatedAt}

Data: **${o.dataKind}**

## Input provenance

Dataset: ${m.title}

Publisher: ${m.publisher}

Scope: ${m.geographic_scope}

Source: ${m.source_url||'Synthetic input authored locally; no external source measurement'}

Licence / supplied restrictions: ${m.licence}

Observation date: ${m.observed_at||'Unknown; retrieval date is not substituted'}

Retrieved: ${m.retrieved_at||'Unknown'}

Source limitations: ${m.limitations||'Not supplied; source claims remain independently unverified'}

Loaded file: ${o.inputFile||'In-memory dataset'}

Input SHA-256: ${o.inputSha256||'Unavailable'}

## Evidence boundaries

${o.limits.map(x=>'- '+x).join('\n')}

${o.synthetic?'**All loaded spatial/service/cost inputs are synthetic test data.**\n\n':''}## Analysis parameters

Raw service weights: ${JSON.stringify(p.rawWeights)}

Normalised weights: ${o.ranking?JSON.stringify(o.ranking.weights):'Unavailable; see analysis error'}

Amenity category: ${p.amenityCategory}; maximum node snap: ${p.maxNodeSnapMetres} metres; avoid mapped steps: ${p.avoidSteps}; analysis origin: ${JSON.stringify(p.origin)}.

## Loaded input quality

${o.quality.networkFeatures} network features; ${o.quality.amenityFeatures} mapped points; ${o.quality.areas} area records; ${o.quality.observations} claims; ${o.quality.disputes} same-window conflicts.

No independent accuracy is established.

## Inspection comparison

${areaSummary}

Access calculation: ${o.access?o.access.status:'not run'}. Routes do not establish availability, safety or facility capacity. Full route calculations and sensitivity results are in the separate JSON analysis export.

## Service claims

${claimSummary}

## Hypothetical maintenance comparison

${o.scenarioError?'Unavailable: '+o.scenarioError:o.maintenanceScenario?'Input budget INR '+o.maintenanceScenario.budget+'; distinct supplied coverage units '+o.maintenanceScenario.exact.covered.length+'; input cost INR '+o.maintenanceScenario.exact.cost+'; selected options '+(o.maintenanceScenario.exact.selected.join(', ')||'none')+'. These units/costs are not verified households or impact.':'No maintenance options supplied.'}

${optionSummary}

## Research query

${o.evidenceQuery||'No query run.'}

Search status: ${o.evidenceSearch?.status||'not run'}. Search uses curated research cards, not the imported service evidence or full source documents. Inspect the separate JSON analysis for the retrieval result.

## Research source catalogue

These sources provide research context; their inclusion does not validate the imported observations or analytical results.

${o.sourceCards.map(c=>`- ${c.id}: ${c.source_url} — ${c.locator}; ${c.observation_period}; accessed ${c.access_date}`).join('\n')}

This is a review aid, not an official certification or service guarantee.
`;}
function showExport(){modal('Export a reviewable brief',`<p class="fine-print">Exports preserve dataset provenance, parameters, missingness, claims and limits. They do not send a complaint or record an official decision.</p><div class="callout ${state.dataset.metadata.is_synthetic?'amber':'blue'}">${esc(modeText())} · ${esc(state.dataset.metadata.title)}</div><div class="inline-actions"><button class="button primary" data-action="download-brief">Review brief (.md)</button><button class="button secondary" data-action="download-analysis">Analysis (.json)</button><button class="button secondary" data-action="download-rankings" ${!state.dataset.areas.length?'disabled':''}>Rankings (.csv)</button></div><p class="fine-print" style="margin-top:20px">If input evidence is restricted, keep the exported brief restricted too. The prototype has no production access-control or retention system.</p>`);}

document.addEventListener('click',async ev=>{
  const t=ev.target;
  const svg=t.closest?.('svg[data-map]');
  if(svg&&state.pickingOrigin&&state.mapProjection){const p=svg.createSVGPoint();p.x=ev.clientX;p.y=ev.clientY;const q=p.matrixTransform(svg.getScreenCTM().inverse());state.origin=state.mapProjection.unproject([q.x,q.y]);state.pickingOrigin=false;state.lastRoute=null;render();toast('Analysis origin selected. This point does not represent counted households.');return;}
  const marker=t.closest?.('[data-marker]');if(marker){markerDetail(marker.dataset.marker);return;}
  const view=t.closest?.('[data-view]');if(view){navigate(view.dataset.view);return;}
  const search=t.closest?.('[data-search]');if(search){runSearch(search.dataset.search);return;}
  const tab=t.closest?.('[data-library]');if(tab){state.libraryTab=tab.dataset.library;render();return;}
  const action=t.closest?.('[data-action]')?.dataset.action;if(!action)return;
  try{
    if(action==='sandbox'){await setDataset(structuredClone(state.examples),'sandbox',state.examplesText,'example.json');toast('Synthetic sandbox loaded. No real service conditions are represented.');}
    if(action==='pick-origin'){state.pickingOrigin=!state.pickingOrigin;render();}
    if(action==='zoom-in'||action==='zoom-out'){state.zoom=Math.max(1,Math.min(4,state.zoom*(action==='zoom-in'?1.35:1/1.35)));render();}
    if(action==='calculate-route')calculateRoute();
    if(action==='open-public-case'){state.libraryTab='record-case';navigate('library');}
    if(action==='reset-weights'){state.weights={water_deficit:40,sanitation_deficit:40,waste_deficit:20};render();}
    if(action==='metadata')showMetadata();
    if(action==='download-schema'){const content=window.__SEVA_FILES__?.['schema.md']??await(await fetch('./schema.md')).text();download('schema.md',content,'text/markdown;charset=utf-8');}
    if(action==='download-template')download('seva-synthetic-template.json',JSON.stringify(state.examples,null,2),'application/json');
    if(action==='download-public-case'){if(!state.research.publicCase)throw new Error('Public case unavailable.');download('seva-public-sra-record-case.json',JSON.stringify({...state.research.publicCase,computedAudit:auditSchemeRecords(state.research.publicCase.records)},null,2),'application/json');}
    if(action==='download-report'){const name=t.closest('[data-report]')?.dataset.report;if(window.__SEVA_FILES__&&Object.hasOwn(window.__SEVA_FILES__,name))download(name,window.__SEVA_FILES__[name],'text/plain;charset=utf-8');}
    if(action==='download-rankings'){download('seva-ranking-inputs-and-bounds.csv',rankingCsv(getRanking(),{metadata:state.dataset.metadata,reviewAsOf:state.asOf,inputSha256:state.hash}),'text/csv;charset=utf-8');toast('Ranking bounds exported with sources and unknown fields.');}
    if(action==='download-analysis')download('seva-review-analysis.json',JSON.stringify(exportObject(),null,2),'application/json');
    if(action==='download-brief')download('seva-review-brief.md',briefMarkdown(exportObject()),'text/markdown;charset=utf-8');
  }catch(e){toast(e.message);}
});
document.addEventListener('keydown',ev=>{if(ev.target.matches?.('[data-marker]')&&['Enter',' '].includes(ev.key)){ev.preventDefault();markerDetail(ev.target.dataset.marker);}});
document.addEventListener('input',ev=>{
  const t=ev.target;
  if(t.dataset.weight){state.weights[t.dataset.weight]=Number(t.value);$('#label-'+t.dataset.weight).textContent=fmt(Number(t.value));$('#priority-results').innerHTML=priorityResults();}
  if(t.id==='snap-limit'){state.maxSnap=t.value===''?NaN:Number(t.value);invalidateRoute();}
  if(t.id==='scenario-budget'){state.budget=t.value===''?NaN:Number(t.value);$('#scenario-results').innerHTML=scenarioResults();}
  if(t.id==='dataset-filter'){state.datasetFilter=t.value;$('#dataset-table').innerHTML=datasetTable();}
});
document.addEventListener('change',async ev=>{
  const t=ev.target;
  if(t.id==='data-mode'){
    if(t.value==='research')await setDataset(structuredClone(state.references),'research',state.referencesText,'reference-points.json');
    else if(t.value==='sandbox')await setDataset(structuredClone(state.examples),'sandbox',state.examplesText,'example.json');
    else if(state.imported)await setDataset(structuredClone(state.imported),'imported',state.importedText,state.importedName);
  }
  if(t.id==='dataset-file'){const f=t.files[0];if(f)await importFile(f);}
  if(t.id==='amenity-category'){state.category=t.value;state.lastRoute=null;render();}
  if(t.id==='snap-limit'){state.maxSnap=t.value===''?NaN:Number(t.value);invalidateRoute();}
  if(t.id==='avoid-steps'){state.avoidSteps=t.checked;state.lastRoute=null;render();}
  if(t.id==='analysis-date'){
    try{validateDataset(state.dataset,t.value);state.asOf=t.value;$('#priority-results').innerHTML=priorityResults();}
    catch(e){t.value=state.asOf;toast('Review date unchanged: '+e.message);}
  }
});
document.addEventListener('submit',ev=>{if(ev.target.id==='evidence-form'){ev.preventDefault();runSearch($('#evidence-query').value);}});
$('#import-button').addEventListener('click',showImport);$('#export-button').addEventListener('click',showExport);$('#close-dialog').addEventListener('click',()=>$('#data-dialog').close());
$('#data-dialog').addEventListener('click',ev=>{if(ev.target===$('#data-dialog')){const r=ev.target.getBoundingClientRect();if(ev.clientX<r.left||ev.clientX>r.right||ev.clientY<r.top||ev.clientY>r.bottom)ev.target.close();}});
window.addEventListener('hashchange',()=>{const view=location.hash.slice(1);if(views.has(view)){state.view=view;render();}});

async function loadJson(path){if(window.__SEVA_EMBEDDED__&&Object.hasOwn(window.__SEVA_EMBEDDED__,path)){const text=window.__SEVA_EMBEDDED__[path];return {value:JSON.parse(text),text};}const r=await fetch(path);if(!r.ok)throw new Error(`Could not load ${path} (HTTP ${r.status}).`);const text=await r.text();return {value:JSON.parse(text),text};}
try{
  const [research,references,examples]=await Promise.all([loadJson('./data/research.json'),loadJson('./data/reference-points.json'),loadJson('./data/example.json')]);
  state.research=research.value;state.references=references.value;state.referencesText=references.text;state.examples=examples.value;state.examplesText=examples.text;state.asOf=research.value.reviewed_at;
  validateDataset(state.examples,state.asOf);await setDataset(structuredClone(state.references),'research',references.text,'reference-points.json');
}catch(e){$('#main').innerHTML=`<div class="error-page"><h1>Unable to load the workbench</h1><p>${esc(e.message)}</p><p>Serve the prototype directory over HTTP. From the project root, run <code>python3 prototype/serve.py</code> and open the printed local URL.</p></div>`;$('#mode-banner').textContent='Startup did not complete; no analysis was run.';}
