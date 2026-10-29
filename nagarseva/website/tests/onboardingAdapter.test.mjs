import assert from 'node:assert/strict'
import {test} from 'node:test'
import {controlledImportAdapter} from '../src/integration/adapter.ts'
const hash='a'.repeat(64)
const request={filename:'TEST-ONLY.csv',contentBase64:'aWQsbmFtZQpYLERlbW8=',permissionAccepted:true,category:'identifiers',mapping:{id:'id',name:'name'},crsConfirmed:false,settlementBatchId:null,confirm:true,expectedSha256:hash,sourceName:'Synthetic test only',publisher:'Test suite',sourceUrl:null,publicationYear:null,coverage:'Test scope'}
const stored={id:'IMPORT-0123456789ABCDEF',category:'identifiers',status:'imported_demo',filename:'TEST-ONLY.csv',bytes:16,format:'CSV',recordCount:1,sha256:hash,columns:['id','name'],bounds:null,validatedAt:'2026-10-29T00:00:00Z',mapping:request.mapping,importedAt:'2026-10-29T00:00:01Z',sourceVerified:false,stored:true,active:false,settlementBatchId:null,provenance:{sourceName:request.sourceName,publisher:request.publisher,sourceUrl:null,publicationYear:null,coverage:'Test scope'}}
async function usingFetch(response,run,status=200){const previous=globalThis.fetch;globalThis.fetch=async()=>new Response(JSON.stringify(response),{status,headers:{'Content-Type':'application/json'}});try{return await run()}finally{globalThis.fetch=previous}}
test('Controlled import rejects unexpected HTTP-success bodies instead of showing a save',async()=>{
 for(const body of [{success:true},{...stored,stored:false},{...stored,active:true},{...stored,sourceVerified:true},{...stored,sha256:'b'.repeat(64)},{...stored,id:undefined}])await usingFetch(body,()=>assert.rejects(()=>controlledImportAdapter.import(request,'test-key'),/ir.error.response/))
 const receipt=await usingFetch(stored,()=>controlledImportAdapter.import(request,'test-key'))
 assert.equal(receipt.id,stored.id);assert.equal(receipt.active,false);assert.equal(receipt.sourceVerified,false)
})
test('Inspection and import errors remain errors without accepting malformed metadata',async()=>{
 await usingFetch({detail:'ir.error.duplicateImported'},()=>assert.rejects(()=>controlledImportAdapter.import(request,'test-key'),/ir.error.duplicateImported/),409)
 await usingFetch({stored:true,recordCount:100},()=>assert.rejects(()=>controlledImportAdapter.inspect(request),/ir.error.response/))
 await usingFetch({activeAdapter:'sqlite-synthetic',externalConnected:true,categories:[]},()=>assert.rejects(()=>controlledImportAdapter.readiness(),/ir.error.response/))
})
