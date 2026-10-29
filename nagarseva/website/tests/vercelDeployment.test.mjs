import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {apiBase,preflight} from '../../../deploy/vercel/build.mjs'
test('Vercel deployment rejects missing, private and credential-bearing API URLs',()=>{
  for(const value of ['', '/api','http://api.example.test/api','https://localhost/api','https://127.0.0.1/api','https://192.168.1.1/api','https://u:secret@api.example.test/api','https://api.example.test/api?token=x','https://api.example.test/api#x','https://api.example.test/urban'])assert.throws(()=>apiBase(value))
  assert.equal(apiBase('https://api.example.test/api/'),'https://api.example.test/api')
})
test('Deployment preflight requires actual successful synthetic API metadata, never an HTML/fake success response',async()=>{
  const good={adapter:'sqlite-synthetic',synthetic:true,externalConnected:false,adminConfigured:true}
  const result=await preflight('https://api.example.test/api',async url=>{assert.equal(url,'https://api.example.test/api/urban/demo/health');return {ok:true,json:async()=>good}})
  assert.equal(result,'https://api.example.test/api')
  for(const response of [{ok:false,status:503},{ok:true,json:async()=>{throw new Error('HTML')}},{ok:true,json:async()=>({...good,adapter:'another-app'})},{ok:true,json:async()=>({...good,synthetic:false})}])await assert.rejects(preflight('https://api.example.test/api',async()=>response))
})
test('Vercel monorepo routes preserve API/asset errors and include all current page refreshes',()=>{
  const config=JSON.parse(readFileSync(new URL('../../../vercel.json',import.meta.url)))
  assert.equal(config.outputDirectory,'nagarseva/website/dist')
  for(const path of ['/methodology','/data-integration','/housing','/services','/visits','/projects/reports'])assert.ok(config.rewrites.some(rule=>rule.source===path&&rule.destination==='/index.html'))
  assert.ok(!config.rewrites.some(rule=>rule.source.includes(':path')||rule.source.startsWith('/api')))
})
