import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFile } from 'node:fs/promises'
import { HISTORICAL_2015, loadReferenceBoundaries, parseReferenceBoundaries, validateBoundaryMetadata } from '../src/urban/historicalBoundaries.ts'

const root = new URL('../public/data/', import.meta.url)
const raw = await readFile(new URL('mumbai_slum_clusters_2015.geojson', root))
const metadata = JSON.parse(await readFile(new URL('mumbai_slum_clusters_2015.metadata.json', root), 'utf8'))
const dataset = JSON.parse(raw)
const fetcher = async url => new Response(url.endsWith('.metadata.json') ? JSON.stringify(metadata) : raw)
const square = () => ({type:'Feature',properties:{polyno:null},geometry:{type:'Polygon',coordinates:[[[72.9,19.0],[72.91,19.0],[72.91,19.01],[72.9,19.01],[72.9,19.0]]]}})
const manifest = (count = 1) => ({...metadata,source_feature_count:count,valid_feature_count:count,excluded_features:[]})

test('Exact supplied bytes, full counts, Mumbai WGS84 extent and explicit topology exclusions load', async () => {
  const result = await loadReferenceBoundaries(HISTORICAL_2015, fetcher)
  assert.equal(result.metadata.source_feature_count, 2542)
  assert.equal(result.geometry.features.length, 2517)
  assert.equal(result.skippedCount, 25)
  assert.equal(result.metadata.coordinate_count, 70404)
  assert.equal(result.metadata.polyno_non_null_count, 0)
  assert.equal(result.metadata.sha256, '4c83541ace7197e2193584438c31a9684c91bb4776aa7d94772a4d72e5e5970d')
  assert.deepEqual(result.metadata.bounds, [72.78274625762192,18.90863286362999,72.97183173366705,19.26385248981887])
  assert.equal(result.metadata.analysis_allowed, false)
  assert.equal(result.metadata.reference_year, 2015)
  for (const feature of result.geometry.features) {
    assert.deepEqual(feature.properties, {polyno:null})
    assert.equal(feature.geometry.type, 'Polygon')
    assert.equal(feature.id, undefined)
  }
})

test('Empty collections, malformed structure and changed source counts remain explicit', () => {
  assert.equal(parseReferenceBoundaries({type:'FeatureCollection',features:[]}, manifest(0)).geometry.features.length,0)
  for (const value of [null,{},[],{type:'FeatureCollection',features:null},{type:'FeatureCollection',features:[],crs:{name:'EPSG:32643'}}]) assert.throws(()=>parseReferenceBoundaries(value,manifest()), /WGS84/)
  assert.throws(()=>parseReferenceBoundaries({type:'FeatureCollection',features:[]},manifest()), /count/)
})

test('Invalid coordinates, open rings, empty geometries and unknown features are excluded without invented values', () => {
  const features = [square(), square(), square(), square(), square(), {type:'Feature',properties:{},geometry:null}]
  features[1].geometry.coordinates[0][0] = [19,720]
  features[2].geometry.coordinates[0].pop()
  features[3].geometry.coordinates = []
  features[4].geometry.coordinates[0][0] = [true,19]
  const result = parseReferenceBoundaries({type:'FeatureCollection',features},manifest(features.length))
  assert.equal(result.geometry.features.length,1); assert.equal(result.skippedCount,5)
  const technical = square(); technical.properties.polyno = 0
  assert.equal(parseReferenceBoundaries({type:'FeatureCollection',features:[technical]},manifest()).geometry.features[0].properties.polyno,0)
})

test('Metadata cannot promote the layer to current observations or change its source identity', () => {
  for (const patch of [{reference_year:2024},{analysis_allowed:true},{crs:'EPSG:32643'},{source_url:'javascript:alert(1)'},{source_url:'https://user:secret@example.test/'},{valid_feature_count:2542},{excluded_features:[metadata.excluded_features[0],metadata.excluded_features[0]]},{bounds:[19,73,18,72]},{sha256:'wrong'}]) assert.throws(()=>validateBoundaryMetadata({...metadata,...patch}), /metadata/)
})

test('Failed requests, empty/oversize responses, malformed JSON and checksum changes fail safely', async () => {
  await assert.rejects(loadReferenceBoundaries(HISTORICAL_2015,async()=>new Response('',{status:404})), /404/)
  await assert.rejects(loadReferenceBoundaries(HISTORICAL_2015,async()=>new Response('')), /empty/)
  await assert.rejects(loadReferenceBoundaries(HISTORICAL_2015,async()=>new Response('{}',{headers:{'content-length':'99999999'}})), /limit/)
  await assert.rejects(loadReferenceBoundaries(HISTORICAL_2015,async()=>new Response('not JSON')), /valid JSON/)
  await assert.rejects(loadReferenceBoundaries(HISTORICAL_2015,async url=>new Response(url.endsWith('.metadata.json')?JSON.stringify(metadata):'{}')), /checksum/)
  await assert.rejects(loadReferenceBoundaries(HISTORICAL_2015,async(_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')))),5), /Aborted/)
})
