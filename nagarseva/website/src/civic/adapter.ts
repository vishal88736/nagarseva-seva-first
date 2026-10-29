import {assertWorkspace} from './analytics.ts'
import type {CivicAdapter,CivicState,DemoHealth,Mutation,MutationResult} from './types.ts'
const BASE=(import.meta.env?.VITE_API_BASE_URL||'/api').replace(/\/$/,'')
export class RequestError extends Error {code:string;details?:unknown;constructor(code:string,details?:unknown){super(code);this.code=code;this.details=details}}
export async function jsonRequest<T>(path:string,body?:unknown,key=''):Promise<T> {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000)
  try {
    const response=await fetch(`${BASE}/urban${path}`,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-Officer-Key':key},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal})
    let result:Record<string,unknown>
    try{result=await response.json()}catch{throw new RequestError('demo.error.backend')}
    if(!response.ok){if(response.status===401)throw new RequestError('demo.error.permission');if(response.status===503&&String(result.detail).startsWith('Configure'))throw new RequestError('d.configureAdmin');const detail=result.detail;throw new RequestError(typeof detail==='string'?detail:detail&&typeof detail==='object'&&!Array.isArray(detail)&&'code' in detail?String(detail.code):'demo.error.fields',detail)}
    return result as T
  } catch(error){if(error instanceof RequestError)throw error;throw new RequestError('demo.error.backend')} finally{clearTimeout(timer)}
}
/** The only active domain adapter. A future verified adapter implements this contract. */
export const sqliteDemoAdapter:CivicAdapter={
  load:()=>jsonRequest<CivicState>('/demo/workspace').then(assertWorkspace),
  health:()=>jsonRequest<DemoHealth>('/demo/health'),
  mutate:(command:Mutation,key:string)=>jsonRequest<MutationResult>('/demo/commands',command,key).then(result=>({...result,state:assertWorkspace(result.state)})),
}
export const publicUrl=(path:string)=>`${BASE}/urban${path}`
