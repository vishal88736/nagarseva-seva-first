import assert from 'node:assert/strict'
import {test} from 'node:test'
import {cameraIntent,geometrySignature,gridStep,groupPoints} from '../src/civic/mapState.ts'
const row=(id,x=72.9)=>({id,geometry:{type:'Polygon',coordinates:[[[x,19],[x+.001,19],[x+.001,19.001],[x,19.001],[x,19]]]},latitude:19,longitude:x})
const snapshot=(changes={})=>({geometry:'actual spatial signature',selected:'',hasSelection:false,count:100,fitRequest:0,...changes})
test('Map camera fits only on initial data, spatial/filter changes, selection or explicit fit',()=>{
 const current=snapshot();assert.equal(cameraIntent(null,current),'data')
 assert.equal(cameraIntent(current,{...current}),'preserve')
 assert.equal(cameraIntent(current,snapshot({geometry:'filtered collection',count:5})),'data')
 assert.equal(cameraIntent(current,snapshot({selected:'SET-1',hasSelection:true})),'selection')
 assert.equal(cameraIntent(current,snapshot({fitRequest:1})),'data')
 assert.equal(cameraIntent(null,snapshot({selected:'SET-1',hasSelection:true})),'selection')
 assert.equal(cameraIntent(current,snapshot({count:0})),'preserve')
})
test('Unrelated record edits, translated labels and list sorting cannot reset map viewport',()=>{
 const rows=[row('S1'),row('S2',72.8)],changed=rows.map(item=>({...item,name:'Translated name',waterAccessPercent:90})).reverse()
 assert.equal(geometrySignature(rows),geometrySignature(changed))
 assert.notEqual(geometrySignature(rows),geometrySignature([row('S1',72.91),row('S2',72.8)]))
 assert.equal(cameraIntent(snapshot(),snapshot()),'preserve')
})
test('Low-zoom grouped targets count actual records, retain every stable ID and do not mutate geometry',()=>{
 const rows=[row('S1'),row('S2'),row('S3',73)],original=JSON.stringify(rows)
 const groups=groupPoints(rows,(latitude,longitude)=>({x:longitude*1000,y:latitude*1000}))
 assert.equal(groups.reduce((sum,group)=>sum+group.rows.length,0),3)
 assert.equal(groups.length,2);assert.deepEqual(groups.flatMap(group=>group.rows.map(row=>row.id)).sort(),['S1','S2','S3'])
 assert.equal(JSON.stringify(rows),original)
 assert.ok(gridStep(.2)>0);assert.equal(gridStep(0),1)
})
