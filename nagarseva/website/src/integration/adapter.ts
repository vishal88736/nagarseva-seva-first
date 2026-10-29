import {jsonRequest,publicUrl,RequestError} from '../civic/adapter.ts'
export const CATEGORIES=['boundaries','identifiers','housing','services','projects','issues','visits'] as const
export type Category=typeof CATEGORIES[number]
export type FileDraft={filename:string;contentBase64:string;permissionAccepted:boolean;sheetName?:string|null}
export type Finding={code:string;row:number|null;field:string|null;detail?:string|null}
export type Inspection={filename:string;bytes:number;format:string;recordCount:number;columns:string[];sha256:string;inspectedAt:string;stored:false;errors:Finding[];errorCount:number;bounds:number[]|null;suggestions:Record<Category,Record<string,string>>;sheets?:string[];sheet?:string;excelPercentColumns?:string[]}
export type Validation=Omit<Inspection,'suggestions'|'inspectedAt'>&{valid:boolean;completenessPercent:number;requiredCompletenessPercent:number;category:Category;missingRequiredFields:string[];warnings:Finding[];preview:Record<string,unknown>[];validatedAt:string;mapping:Record<string,string>;status:string}
export type MappingRequest=FileDraft&{category:Category;mapping:Record<string,string>;crsConfirmed:boolean;settlementBatchId:string|null}
export type ImportReceipt={id:string;category:Category;status:'imported_demo'|'rolled_back';filename:string;bytes:number;format:string;recordCount:number;sha256:string;columns:string[];bounds:number[]|null;validatedAt:string;mapping:Record<string,string>;importedAt:string;sourceVerified:false;stored:true;active:false;settlementBatchId:string|null;provenance:{sourceName:string;publisher:string;sourceUrl:string|null;sourceDate?:string;licence?:string;publicationYear:number|null;coverage:string};replayed?:boolean;dataClass?:'demo'|'manually_provided';is_synthetic?:boolean;completenessPercent?:number;rolledBackAt?:string;history?:{action:string;createdAt:string;reason?:string}[]}
export type ImportRequest=MappingRequest&{confirm:boolean;expectedSha256:string;sourceName:string;publisher:string;sourceUrl:string;publicationYear:number|null;coverage:string;sourceDate:string;licence:string;dataClass:'demo'|'manually_provided'}
export type Readiness={activeAdapter:string;externalConnected:false;categories:{category:Category;status:string;importedBatches:number;recordCount:number}[]}
export type Schema={fields:Record<Category,Record<string,string>>;required:Record<Category,string[]>;maxBytes:number;maxRows:number;formats:string[]}
const object=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value)
const strings=(value:unknown):value is string[]=>Array.isArray(value)&&value.every(item=>typeof item==='string')
function requireResponse(condition:unknown):asserts condition {if(!condition)throw new RequestError('ir.error.response')}
function checkMetadata(value:unknown):asserts value is Inspection {
 requireResponse(object(value));requireResponse(typeof value.filename==='string'&&typeof value.format==='string'&&['CSV','GeoJSON','XLSX'].includes(value.format)&&typeof value.sha256==='string'&&/^[a-f0-9]{64}$/.test(value.sha256))
 requireResponse(Number.isInteger(value.bytes)&&Number(value.bytes)>0&&Number(value.bytes)<=5242880&&Number.isInteger(value.recordCount)&&Number(value.recordCount)>=0&&Number(value.recordCount)<=5000&&strings(value.columns))
 requireResponse(value.bounds===null||Array.isArray(value.bounds)&&value.bounds.length===4&&value.bounds.every(v=>typeof v==='number'&&Number.isFinite(v)))
}
function checkFindings(value:unknown):asserts value is Finding[] {requireResponse(Array.isArray(value)&&value.every(row=>object(row)&&typeof row.code==='string'&&(row.row===null||Number.isInteger(row.row))&&(row.field===null||typeof row.field==='string')))}
function inspection(value:unknown):Inspection {
 checkMetadata(value);requireResponse(value.stored===false&&Number.isFinite(Date.parse(value.inspectedAt)));checkFindings(value.errors);requireResponse(Number.isInteger(value.errorCount)&&value.errorCount>=value.errors.length&&object(value.suggestions))
 for(const category of CATEGORIES){const mapping=value.suggestions[category];requireResponse(object(mapping)&&Object.values(mapping).every(column=>typeof column==='string'&&value.columns.includes(column)))}
 return value
}
function validation(value:unknown):Validation {
 checkMetadata(value);const row=value as unknown as Validation
 requireResponse(row.stored===false&&typeof row.valid==='boolean'&&row.status===(row.valid?'validation_passed':'validation_failed')&&Number.isFinite(Date.parse(row.validatedAt))&&CATEGORIES.includes(row.category)&&Array.isArray(row.preview)&&row.preview.every(object)&&strings(row.missingRequiredFields))
 checkFindings(row.errors);checkFindings(row.warnings);requireResponse(Number.isInteger(row.errorCount)&&row.errorCount>=row.errors.length&&(!row.valid||row.errorCount===0))
 return row
}
function receipt(value:unknown,request?:ImportRequest):ImportReceipt {
 checkMetadata(value);const row=value as unknown as ImportReceipt
 requireResponse(typeof row.id==='string'&&/^IMPORT-[A-F0-9]{16}$/.test(row.id)&&['imported_demo','rolled_back'].includes(row.status)&&row.stored===true&&row.active===false&&row.sourceVerified===false&&row.recordCount>0&&CATEGORIES.includes(row.category)&&object(row.provenance)&&typeof row.provenance.sourceName==='string'&&typeof row.provenance.publisher==='string'&&typeof row.provenance.coverage==='string'&&Number.isFinite(Date.parse(row.importedAt))&&Number.isFinite(Date.parse(row.validatedAt))&&object(row.mapping))
 if(request)requireResponse(row.sha256===request.expectedSha256&&row.category===request.category)
 return row
}
/** Controlled import adapter. It never changes the active synthetic domain adapter. */
export const controlledImportAdapter={
 schema:async()=>{const row=await jsonRequest<Schema>('/integration/schema');requireResponse(object(row)&&object(row.fields)&&object(row.required)&&CATEGORIES.every(category=>object(row.fields[category])&&strings(row.required[category]))&&row.maxBytes===5242880&&row.maxRows===5000);return row},
 readiness:async()=>{const row=await jsonRequest<Readiness>('/integration/readiness');requireResponse(object(row)&&row.activeAdapter==='sqlite-synthetic'&&row.externalConnected===false&&Array.isArray(row.categories)&&row.categories.length===7&&CATEGORIES.every(category=>row.categories.filter(r=>r.category===category&&['not_provided','imported_demo'].includes(r.status)&&Number.isInteger(r.recordCount)&&r.recordCount>=0&&Number.isInteger(r.importedBatches)&&r.importedBatches>=0).length===1));return row},
 inspect:(file:FileDraft)=>jsonRequest<unknown>('/integration/inspect',file).then(inspection),
 validate:(file:MappingRequest,key:string)=>jsonRequest<unknown>('/integration/validate',file,key).then(validation),
 import:(request:ImportRequest,key:string)=>jsonRequest<unknown>('/integration/imports',request,key).then(row=>receipt(row,request)),
 receipts:async(key:string)=>{const response=await jsonRequest<{items:unknown[]}>('/integration/imports',undefined,key);requireResponse(object(response)&&Array.isArray(response.items));return {items:response.items.map(item=>receipt(item))}},
 rollback:(id:string,reason:string,key:string)=>jsonRequest<unknown>(`/integration/imports/${encodeURIComponent(id)}/rollback`,{confirm:true,reason},key).then(row=>receipt(row)),
 download:async(id:string,key:string)=>{const response=await fetch(publicUrl(`/integration/imports/${encodeURIComponent(id)}/original`),{headers:{'X-Officer-Key':key}});if(!response.ok)throw new RequestError('ir.error.download');return response.blob()},
}
