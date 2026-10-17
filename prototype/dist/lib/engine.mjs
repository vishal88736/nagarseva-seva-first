/* Deterministic analysis for Seva Evidence. No external services or ML models. */
export const CRITERIA = ["water_deficit", "sanitation_deficit", "waste_deficit"];
export const CRITERIA_LABELS = {water_deficit: "Water", sanitation_deficit: "Sanitation", waste_deficit: "Waste collection"};
const MAX_BYTES = 5 * 1024 * 1024;
const MAX_SCENARIO_WORK = 5000000;
const EARTH_RADIUS_M = 6371008.8;
const ALLOWED_ROOT = new Set(["schema_version", "metadata", "network", "amenities", "origins", "areas", "observations", "interventions"]);
const PRIVATE_KEYS = /^(aadhaar|aadhar|phone|mobile|email|resident_name|household_id|caste|religion|bank_account|pan_number)$/i;
const FORBIDDEN_KEYS = new Set(["__proto__", "constructor", "prototype"]);
const CLASSES = new Set(["toilets", "clinic", "school", "water_point", "transport_stop"]);
const WAY_TYPES = new Set(["footway", "pedestrian", "path", "steps", "residential", "living_street", "service", "unclassified", "tertiary", "tertiary_link", "secondary", "secondary_link", "primary", "primary_link"]);

export function ensure(condition, message) { if (!condition) throw new Error(message); }
export function isDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(value + "T00:00:00Z");
  return Number.isFinite(d.getTime()) && d.toISOString().slice(0, 10) === value;
}
export function safeUrl(value) {
  try { const u = new URL(value); return u.protocol === "https:" && !u.username && !u.password ? u.href : null; } catch { return null; }
}
function text(value, label, limit = 200) {
  ensure(typeof value === "string" && value.trim().length > 0 && value.length <= limit, `${label} must be nonempty text (maximum ${limit} characters).`);
  return value.trim();
}
function coordinate(value, label) {
  ensure(Array.isArray(value) && value.length >= 2 && value.length <= 3 && value.every(Number.isFinite), `${label}: coordinates must be finite numbers.`);
  ensure(Math.abs(value[0]) <= 180 && Math.abs(value[1]) <= 90, `${label}: longitude/latitude outside WGS84 range.`);
}
function inspectObject(value, depth = 0) {
  ensure(depth < 32, "Input nesting exceeds the supported depth.");
  if (!value || typeof value !== "object") return;
  for (const key of Object.keys(value)) {
    ensure(!FORBIDDEN_KEYS.has(key), "Unsafe object key in input.");
    ensure(!PRIVATE_KEYS.test(key), `Remove personal field '${key}'. The prototype accepts public/aggregate evidence only.`);
    inspectObject(value[key], depth + 1);
  }
}
function collection(value, name, type, maximum) {
  ensure(value && value.type === "FeatureCollection" && Array.isArray(value.features), `${name} must be a GeoJSON FeatureCollection.`);
  ensure(value.features.length <= maximum, `${name} exceeds ${maximum} features.`);
  const ids = new Set();
  let vertices = 0;
  for (const f of value.features) {
    ensure(f && f.type === "Feature" && f.geometry?.type === type && f.properties && typeof f.properties === "object", `${name}: invalid ${type} feature.`);
    const id = text(String(f.id ?? f.properties.id ?? ""), `${name} feature ID`, 150);
    ensure(!ids.has(id), `${name}: duplicate ID '${id}'.`); ids.add(id);
    if (type === "Point") coordinate(f.geometry.coordinates, name);
    else {
      ensure(Array.isArray(f.geometry.coordinates) && f.geometry.coordinates.length >= 2, `${name}: a line needs two coordinates.`);
      f.geometry.coordinates.forEach(c => coordinate(c, name));
      vertices += f.geometry.coordinates.length;
      const nodes = f.properties.node_ids;
      ensure(!nodes || (Array.isArray(nodes) && nodes.length === f.geometry.coordinates.length && nodes.every(n => typeof n === "string" || Number.isSafeInteger(n))), `${name}: node_ids must match line vertices.`);
    }
  }
  ensure(vertices <= 30000, `${name}: too many vertices (maximum 30000).`);
}
function checkScenarioWork(interventions) {
  const feasible = interventions.filter(x => x.feasible);
  const visits = feasible.length ? 2 ** (feasible.length - 1) * feasible.reduce((n, x) => n + x.coverage_ids.length, 0) : 0;
  ensure(visits <= MAX_SCENARIO_WORK, "Scenario exceeds the browser workload limit. Reduce the number of options or coverage IDs before comparing.");
}
export function validateDataset(raw, asOf = "2026-10-17") {
  ensure(isDate(asOf), "Invalid analysis date.");
  ensure(raw && typeof raw === "object" && !Array.isArray(raw), "Input must be a JSON object.");
  ensure(new TextEncoder().encode(JSON.stringify(raw)).byteLength <= MAX_BYTES, "Input exceeds the 5 MB prototype limit.");
  inspectObject(raw);
  ensure(Object.keys(raw).every(k => ALLOWED_ROOT.has(k)), "Unknown top-level field. Use the documented schema.");
  ensure(raw.schema_version === "1.0", "Supported schema_version is '1.0'.");
  const m = raw.metadata;
  ensure(m && typeof m === "object", "metadata is required.");
  ["title", "publisher", "licence", "geographic_scope"].forEach(k => text(m[k], `metadata.${k}`, 600));
  ensure(typeof m.is_synthetic === "boolean", "metadata.is_synthetic must be true or false.");
  ensure(m.is_synthetic || safeUrl(m.source_url), "Imported non-synthetic data requires an HTTPS source_url.");
  for (const k of ["observed_at", "retrieved_at"]) {
    ensure(m[k] === null || isDate(m[k]), `metadata.${k} must be YYYY-MM-DD or null for unknown.`);
    ensure(m[k] === null || m[k] <= asOf, `metadata.${k} is after the analysis date.`);
  }
  collection(raw.network, "network", "LineString", 3000);
  collection(raw.amenities, "amenities", "Point", 500);
  collection(raw.origins, "origins", "Point", 100);
  for (const f of raw.amenities.features) {
    text(f.properties.name, "Amenity name");
    ensure(CLASSES.has(f.properties.category), "Amenity category must be toilets, clinic, school, water_point or transport_stop.");
  }
  ensure(Array.isArray(raw.areas) && raw.areas.length <= 1000, "areas must be an array (maximum 1000).");
  const areaIds = new Set();
  for (const a of raw.areas) {
    text(a.id, "Area ID", 100); text(a.name, "Area label");
    ensure(!areaIds.has(a.id), "Duplicate area ID."); areaIds.add(a.id);
    for (const c of CRITERIA) ensure(a[c] === null || (Number.isFinite(a[c]) && a[c] >= 0 && a[c] <= 1), `${a.id}: ${c} must be 0–1, or null for unknown.`);
    ensure(a.observed_at === null || (isDate(a.observed_at) && a.observed_at <= asOf), `${a.id}: invalid/future observation date.`);
    text(a.method, `${a.id}: method`, 1000);
    ensure(m.is_synthetic || safeUrl(a.source_url), `${a.id}: an HTTPS source_url is required.`);
  }
  ensure(Array.isArray(raw.observations) && raw.observations.length <= 1000, "observations must be an array (maximum 1000).");
  const obsIds = new Set();
  for (const o of raw.observations) {
    text(o.id, "Observation ID"); ensure(!obsIds.has(o.id), "Duplicate observation ID."); obsIds.add(o.id);
    text(o.asset_id, "Observation asset ID"); text(o.service_type, "Observation service type");
    ensure(isDate(o.observed_at) && o.observed_at <= asOf, "Observation date must be valid and not future.");
    ensure(["working", "not_working", "unknown"].includes(o.value), "Observation value must be working, not_working or unknown.");
    ensure(["official_record", "operator_claim", "independent_observation", "resident_report"].includes(o.evidence_type), "Unknown observation evidence_type.");
    ensure(m.is_synthetic || safeUrl(o.source_url), "Observation requires an HTTPS source_url.");
    ensure(!o.note || (typeof o.note === "string" && o.note.length <= 1000), "Observation note too long.");
  }
  ensure(Array.isArray(raw.interventions) && raw.interventions.length <= 18, "interventions must be an array (maximum 18 for exact comparison).");
  const choices = new Set();
  for (const o of raw.interventions) {
    text(o.id, "Intervention ID"); text(o.label, "Intervention label"); text(o.assumption_label, "Cost/coverage assumption", 1000);
    ensure(!choices.has(o.id), "Duplicate intervention ID."); choices.add(o.id);
    ensure(Number.isFinite(o.cost) && o.cost >= 0 && o.cost <= 1e10, "Intervention cost must be finite and nonnegative.");
    ensure(typeof o.feasible === "boolean", "Intervention feasibility must be explicit.");
    ensure(Array.isArray(o.coverage_ids) && o.coverage_ids.length <= 1000 && o.coverage_ids.every(x => typeof x === "string" && x.length > 0 && x.length <= 100), "Intervention coverage_ids must be unit IDs.");
  }
  checkScenarioWork(raw.interventions);
  return raw;
}

export function haversine(a, b) {
  const rad = x => x * Math.PI / 180;
  const dlat = rad(b[1] - a[1]), dlon = rad(b[0] - a[0]);
  const v = Math.sin(dlat / 2) ** 2 + Math.cos(rad(a[1])) * Math.cos(rad(b[1])) * Math.sin(dlon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(Math.max(0, Math.min(1, v))));
}
export function walkable(p, avoidSteps = false) {
  const highway = String(p.highway || "");
  if (!WAY_TYPES.has(highway) || (avoidSteps && highway === "steps")) return false;
  const foot = String(p.foot || "").toLowerCase();
  const affirmative = ["yes", "designated", "permissive", "official"].includes(foot);
  const general = String(p.access || "").toLowerCase();
  if (["no", "private", "use_sidepath", "permit", "customers"].includes(foot)) return false;
  if (!affirmative && ["no", "private", "permit", "customers"].includes(general)) return false;
  if (["primary", "primary_link"].includes(highway) && !affirmative) return false;
  return true;
}
export function buildGraph(network, avoidSteps = false) {
  const nodes = new Map(), adjacency = new Map();
  let acceptedWays = 0, rejectedWays = 0, assumedTopologyWays = 0;
  const addNode = (id, point) => {
    if (nodes.has(id)) ensure(haversine(nodes.get(id), point) < 0.05, `Node ${id} has contradictory coordinates.`);
    else { nodes.set(id, point.slice(0, 2)); adjacency.set(id, []); }
  };
  const edge = (from, to, length, featureId) => adjacency.get(from).push({to, length, featureId});
  for (const f of network.features) {
    const p = f.properties;
    if (!walkable(p, avoidSteps)) { rejectedWays++; continue; }
    acceptedWays++;
    const coords = f.geometry.coordinates, ids = p.node_ids;
    if (!ids) assumedTopologyWays++;
    const level = String(p.layer ?? (p.bridge === "yes" ? "bridge" : p.tunnel === "yes" ? "tunnel" : "0"));
    const key = (c, i) => ids ? `id:${ids[i]}` : `xy:${level}:${c[0]},${c[1]}`;
    for (let i = 0; i < coords.length; i++) addNode(key(coords[i], i), coords[i]);
    const direction = String(p["oneway:foot"] ?? p.oneway_foot ?? "no");
    for (let i = 1; i < coords.length; i++) {
      const a = key(coords[i - 1], i - 1), b = key(coords[i], i), length = haversine(coords[i - 1], coords[i]);
      if (direction !== "-1") edge(a, b, length, f.id ?? p.id);
      if (!["yes", "1", "true"].includes(direction)) edge(b, a, length, f.id ?? p.id);
    }
  }
  return {nodes, adjacency, acceptedWays, rejectedWays, assumedTopologyWays};
}
function nearest(graph, point, maxSnap) {
  let best = null;
  for (const [id, c] of graph.nodes) {
    const distance = haversine(point, c);
    if ((!best || distance < best.distance) && distance <= maxSnap) best = {id, distance};
  }
  return best;
}
function shortestPaths(graph, start) {
  const distances = new Map([[start, 0]]), previous = new Map();
  const heap = [];
  const push = entry => { let i = heap.push(entry) - 1; while (i) {const p = (i - 1) >> 1; if (heap[p][0] <= entry[0]) break; heap[i] = heap[p]; i = p;} heap[i] = entry; };
  const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) {let i = 0; while (i * 2 + 1 < heap.length) {let child = i * 2 + 1; if (child + 1 < heap.length && heap[child + 1][0] < heap[child][0]) child++; if (heap[child][0] >= last[0]) break; heap[i] = heap[child]; i = child;} heap[i] = last;} return top; };
  push([0, start]);
  while (heap.length) {
    const [d, id] = pop(); if (d !== distances.get(id)) continue;
    for (const e of graph.adjacency.get(id)) {
      const next = d + e.length;
      if (!distances.has(e.to) || next < distances.get(e.to)) {distances.set(e.to, next); previous.set(e.to, id); push([next, e.to]);}
    }
  }
  return {distances, previous};
}
export function routeToAmenities(dataset, origin, category, maxSnap = 80, avoidSteps = false) {
  coordinate(origin, "Origin");
  ensure(CLASSES.has(category), "Unknown amenity category.");
  ensure(Number.isFinite(maxSnap) && maxSnap >= 0 && maxSnap <= 1000, "Snap limit must be 0–1000 metres.");
  const graph = buildGraph(dataset.network, avoidSteps), start = nearest(graph, origin, maxSnap);
  const base = {origin, category, graph: {nodes: graph.nodes.size, acceptedWays: graph.acceptedWays, rejectedWays: graph.rejectedWays, assumedTopologyWays: graph.assumedTopologyWays}, maxSnap, avoidSteps};
  if (!start) return {...base, status: "origin_not_routable", routes: [], originSnapM: null};
  const {distances, previous} = shortestPaths(graph, start.id);
  const candidates = dataset.amenities.features.filter(f => f.properties.category === category);
  const routes = candidates.map(f => {
    const p = f.properties, point = f.geometry.coordinates;
    const summary = {id: String(f.id ?? p.id), name: p.name, amenity: point, straightLineM: haversine(origin, point)};
    if (["private", "no"].includes(String(p.access || ""))) return {...summary, status: "access_restricted", distanceM: null, path: []};
    const end = nearest(graph, point, maxSnap);
    if (!end) return {...summary, status: "amenity_not_routable", distanceM: null, amenitySnapM: null, path: []};
    if (!distances.has(end.id)) return {...summary, status: "disconnected", distanceM: null, amenitySnapM: end.distance, path: []};
    const path = []; let cursor = end.id;
    while (cursor !== undefined) {path.unshift(graph.nodes.get(cursor)); cursor = previous.get(cursor);}
    return {...summary, status: "candidate_route", distanceM: distances.get(end.id) + start.distance + end.distance, networkM: distances.get(end.id), amenitySnapM: end.distance, path: [origin, ...path, point]};
  }).sort((a, b) => (a.distanceM ?? Infinity) - (b.distanceM ?? Infinity) || a.id.localeCompare(b.id));
  return {...base, status: candidates.length ? "calculated" : "no_mapped_candidates", originSnapM: start.distance, routes};
}

export function normaliseWeights(raw) {
  ensure(raw && CRITERIA.every(c => Number.isFinite(raw[c]) && raw[c] >= 0), "All weights must be finite and nonnegative.");
  const total = CRITERIA.reduce((s, c) => s + raw[c], 0);
  ensure(Number.isFinite(total) && total > 0, "At least one weight must be greater than zero.");
  return Object.fromEntries(CRITERIA.map(c => [c, raw[c] / total]));
}
export function prioritise(areas, rawWeights, asOf = "2026-10-17") {
  ensure(isDate(asOf), "Invalid analysis date.");
  const weights = normaliseWeights(rawWeights);
  const rows = areas.map(a => {
    const contributions = {}, missing = CRITERIA.filter(c => a[c] === null);
    let lower = 0, unknown = 0;
    for (const c of CRITERIA) {
      const x = a[c];
      ensure(x === null || (Number.isFinite(x) && x >= 0 && x <= 1), `${a.id}: invalid deficit.`);
      contributions[c] = x === null ? null : weights[c] * x;
      if (x === null) unknown += weights[c]; else lower += contributions[c];
    }
    const ageDays = a.observed_at && isDate(a.observed_at) ? Math.round((Date.parse(asOf) - Date.parse(a.observed_at)) / 86400000) : null;
    const hasEvidence = CRITERIA.some(c => a[c] !== null && weights[c] > 0);
    return {...a, contributions, missing, lower, upper: Math.min(1, lower + unknown), complete: missing.length === 0, hasEvidence, ageDays};
  });
  const eligible = rows.filter(r => r.hasEvidence);
  for (const r of rows) {
    r.rankBest = r.hasEvidence ? 1 + eligible.filter(o => o.id !== r.id && o.lower > r.upper + 1e-12).length : null;
    r.rankWorst = r.hasEvidence ? 1 + eligible.filter(o => o.id !== r.id && o.upper >= r.lower - 1e-12).length : null;
    r.needsVerification = !r.complete || r.observed_at === null;
  }
  return {weights, rows: rows.sort((a,b) => Number(b.hasEvidence) - Number(a.hasEvidence) || b.lower - a.lower || a.id.localeCompare(b.id))};
}
function ranksForComplete(rows, weights) {
  const scored = rows.map(a => ({id:a.id, score:CRITERIA.reduce((s,c)=>s+weights[c]*a[c],0)}));
  return scored.map(a => ({...a, rank:1+scored.filter(b=>b.score>a.score+1e-12).length}));
}
export function sensitivity(areas, rawWeights, perturbation = 0.2) {
  ensure(Number.isFinite(perturbation) && perturbation >= 0 && perturbation <= 1, "Perturbation must be between 0 and 1.");
  const complete = areas.filter(a => CRITERIA.every(c => Number.isFinite(a[c]) && a[c] >= 0 && a[c] <= 1));
  const base = normaliseWeights(rawWeights);
  if (!complete.length) return {count:0, perturbation, scenarios:0, rows:[]};
  const groups = [ranksForComplete(complete, base)];
  for (let mask=0; mask<8; mask++) {
    const w=Object.fromEntries(CRITERIA.map((c,j)=>[c,base[c]*(1+(mask&(1<<j)?perturbation:-perturbation))]));
    if (Object.values(w).some(x=>x>0)) groups.push(ranksForComplete(complete, normaliseWeights(w)));
  }
  return {count:complete.length, perturbation, scenarios:groups.length, rows:complete.map(a=>{
    const ranks=groups.map(g=>g.find(x=>x.id===a.id).rank);
    return {id:a.id, name:a.name, baselineRank:ranks[0], minRank:Math.min(...ranks), maxRank:Math.max(...ranks)};
  })};
}

export function compareBudget(interventions, budget) {
  ensure(Number.isFinite(budget) && budget >= 0 && budget <= 1e10, "Budget must be a finite nonnegative number.");
  ensure(interventions.length <= 18, "Exact comparison supports at most 18 options.");
  checkScenarioWork(interventions);
  const feasible = interventions.filter(x=>x.feasible);
  let best={selected:[], cost:0, covered:[]};
  for (let mask=0; mask<(1<<feasible.length); mask++) {
    const selected=[], covered=new Set(); let cost=0;
    for (let i=0;i<feasible.length;i++) if(mask&(1<<i)) {const v=feasible[i];cost+=v.cost;selected.push(v.id);v.coverage_ids.forEach(x=>covered.add(x));}
    if(cost>budget+1e-9) continue;
    if(covered.size>best.covered.length || (covered.size===best.covered.length && cost<best.cost)) best={selected,cost,covered:[...covered].sort()};
  }
  const greedy={selected:[],cost:0,covered:[]}; const seen=new Set(),remaining=[...feasible];
  while(remaining.length) {
    const candidates=remaining.filter(x=>greedy.cost+x.cost<=budget+1e-9).map(x=>({x,gain:x.coverage_ids.filter((id,i,arr)=>!seen.has(id)&&arr.indexOf(id)===i).length})).filter(x=>x.gain>0).sort((a,b)=>(b.x.cost===0?Infinity:b.gain/b.x.cost)-(a.x.cost===0?Infinity:a.gain/a.x.cost)||a.x.id.localeCompare(b.x.id));
    if(!candidates.length)break; const v=candidates[0].x;greedy.selected.push(v.id);greedy.cost+=v.cost;v.coverage_ids.forEach(x=>seen.add(x));remaining.splice(remaining.indexOf(v),1);
  }
  greedy.covered=[...seen].sort();
  return {budget, exact:best, greedy, units:"distinct coverage units supplied by the dataset; not verified households", comparedSubsets:1<<feasible.length};
}
export function observationGroups(observations) {
  const grouped = new Map();
  for (const o of observations) {
    const key=JSON.stringify([o.asset_id,o.service_type,o.observed_at]);
    if(!grouped.has(key)) grouped.set(key,{assetId:o.asset_id,service:o.service_type,date:o.observed_at,claims:[]});
    grouped.get(key).claims.push(o);
  }
  return [...grouped.values()].map(g=>({...g,disputed:new Set(g.claims.filter(c=>c.value!=="unknown").map(c=>c.value)).size>1}));
}
export function dataQuality(dataset) {
  const fields=Object.fromEntries(CRITERIA.map(c=>[c,{known:dataset.areas.filter(a=>a[c]!==null).length,total:dataset.areas.length}]));
  return {networkFeatures:dataset.network.features.length,amenityFeatures:dataset.amenities.features.length,areas:dataset.areas.length,observations:dataset.observations.length,fields,unknownDates:dataset.areas.filter(a=>a.observed_at===null).length,disputes:observationGroups(dataset.observations).filter(g=>g.disputed).length,independentlyValidated:false};
}

// Diagnostic for the attributed public-listing snapshot, never an automatic join.
export function auditSchemeRecords(records) {
  ensure(Array.isArray(records), "Public case records must be an array.");
  const groups = (normalise) => {
    const result = new Map();
    for (const r of records) {
      if (![r.ward,r.locality,r.cts_raw].every(x=>typeof x==='string' && x.trim())) continue;
      const cts = normalise ? r.cts_raw.toUpperCase().replace(/[ -]/g,'') : r.cts_raw;
      if (!cts) continue;
      const key = JSON.stringify([r.ward,r.locality,cts]);
      if (!result.has(key)) result.set(key,{ward:r.ward,locality:r.locality,key:cts,localIds:[]});
      result.get(key).localIds.push(r.local_id);
    }
    return [...result.values()].filter(g=>g.localIds.length>1);
  };
  return {count:records.length,exactGroups:groups(false),candidateGroups:groups(true),
    suppliedProposalCount:records.filter(r=>typeof r.proposal_number==='string'&&r.proposal_number.trim()&&r.proposal_number.trim()!=='-').length,
    suppliedStatusCount:records.filter(r=>typeof r.project_status==='string'&&r.project_status.trim()).length,
    suppliedUpdateCount:records.filter(r=>isDate(r.record_updated_at)).length,
    automaticallyMerged:0,scope:'Selected listing records only; no official duplicate, delay or service conclusion.'};
}

export function tokenize(s) {
  return (String(s).toLowerCase().match(/[\p{L}\p{N}]+/gu)||[]).filter(t=>t.length>1&&!new Set(["the","and","does","have","what","with","this","that","are","for","from","can","how","which","was","will","into","all","has"]).has(t));
}
export function searchEvidence(cards, query, limit=5) {
  ensure(typeof query === "string" && query.length <= 600, "Query must be at most 600 characters.");
  const tokens=tokenize(query), docs=cards.map(c=>({card:c,terms:tokenize(`${c.title} ${c.text} ${(c.keywords||[]).join(" ")}`)}));
  if(!tokens.length)return {status:"empty",results:[],answer:"Enter a question or search term."};
  const mean=docs.reduce((s,d)=>s+d.terms.length,0)/(docs.length||1);
  const ranked=docs.map(d=>{
    let score=0;const matched=[];
    for(const token of new Set(tokens)) {
      const tf=d.terms.filter(t=>t===token).length;if(!tf)continue;
      matched.push(token);const df=docs.filter(x=>x.terms.includes(token)).length;
      const idf=Math.log(1+(docs.length-df+0.5)/(df+0.5));
      score+=idf*(tf*2.2)/(tf+1.2*(0.25+0.75*d.terms.length/mean));
    }
    return {...d.card,score,matched};
  }).filter(c=>c.score>0).sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id)).slice(0,limit);
  const reviewYear=Math.max(2026,...cards.map(c=>Number(String(c.access_date||'').slice(0,4))||0));
  const futureOrReviewYear=(query.match(/\b(?:19|20|21)\d{2}\b/g)||[]).some(y=>Number(y)>=reviewYear);
  const wantsCurrent=/\b(current|currently|today|now|live|latest|present)\b|\bthis\s+(month|week|year)\b|\bat\s+present\b/i.test(query)||futureOrReviewYear;
  const wantsEligibility=/\b(eligible|eligibility|relocat(?:e|ion)|entitlement)\b/i.test(query)&&/\b(i|my|we|our|household|family|resident|decide|who)\b/i.test(query);
  const wantsEffect=/\b(accuracy|performance|saved|savings|reduced|reduction|impact|sroi)\b/i.test(query)&&/\b(prototype|platform|tool|model|our|your|achieved)\b/i.test(query);
  const localMetric=/\b(reliability|coverage|households|percentage|percent|rate|uptime|without|toilet|toilets|water|waste|population|people|persons|residents)\b/i.test(query);
  const abstain=wantsEligibility||wantsEffect||(wantsCurrent&&localMetric);
  if(abstain) return {status:"abstained",results:ranked,answer:wantsEligibility?"This prototype cannot decide household eligibility, entitlement or relocation. Consult the competent authority and applicable current documents.":wantsEffect?"No field impact or independently validated predictive performance has been established for this prototype.":"The research does not establish a current local service/population measurement. Historical figures and mapped assets cannot answer that question."};
  if(!ranked.length) return {status:"abstained",results:[],answer:"No matching evidence in the curated research cards. This is not a search of every government document."};
  return {status:"evidence_found",results:ranked,answer:"Matching source notes are shown below. Each note retains its source, date and evidence limits; no answer is generated beyond these cards."};
}
export function csvCell(value) {
  let s=value===null||value===undefined?"":String(value);
  if(/^[=+\-@\t\r]/.test(s))s="'"+s;
  return '"'+s.replaceAll('"','""')+'"';
}
export function rankingCsv(result, context = {}) {
  const m=context.metadata||{};
  const header=["dataset_title","data_kind","synthetic","review_as_of","dataset_licence","input_sha256","water_weight","sanitation_weight","waste_weight","area_id","area_name","lower_score","upper_score","best_position_bound","worst_position_bound","missing_criteria","observed_at","source_url"];
  const prefix=[m.title??'Unknown',m.is_synthetic===true?'synthetic_test_input':m.is_synthetic===false?'user_supplied_unverified':'Unknown',m.is_synthetic??'Unknown',context.reviewAsOf??'Unknown',m.licence??'Unknown',context.inputSha256??'Unavailable',...CRITERIA.map(c=>result.weights[c])];
  return [header,...result.rows.map(r=>[...prefix,r.id,r.name,r.lower,r.upper,r.rankBest,r.rankWorst,r.missing.join("; "),r.observed_at,r.source_url])].map(r=>r.map(csvCell).join(",")).join("\r\n")+"\r\n";
}
export async function sha256(textValue) {
  if (!globalThis.crypto?.subtle) return null;
  const digest=await globalThis.crypto.subtle.digest("SHA-256",new TextEncoder().encode(textValue));
  return [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,"0")).join("");
}
