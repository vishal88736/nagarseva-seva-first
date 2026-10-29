import {fileURLToPath} from 'node:url'
import path from 'node:path'
import {spawnSync} from 'node:child_process'

export function apiBase(value) {
  if(!value)throw new Error('Set VITE_API_BASE_URL to the deployed persistent API prefix, ending in /api when using the hosted container. Vercel cannot persist this app’s local SQLite database.')
  let url
  try{url=new URL(value)}catch{throw new Error('VITE_API_BASE_URL must be an absolute public HTTPS URL.')}
  const host=url.hostname.toLowerCase()
  if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||host==='localhost'||host==='[::1]'||/^(127\.|10\.|192\.168\.|169\.254\.|0\.)/.test(host)||/^172\.(1[6-9]|2\d|3[01])\./.test(host)||host.endsWith('.localhost')||host.endsWith('.local'))throw new Error('Use a public HTTPS API prefix without credentials, query parameters or fragments. Local development URLs cannot be deployed.')
  if(/\/urban\/?$/.test(url.pathname))throw new Error('Supply the API prefix without /urban; the application adds /urban itself.')
  return url.toString().replace(/\/$/,'')
}

export async function preflight(value,fetcher=fetch){
  const base=apiBase(value)
  let response,health
  try{
    response=await fetcher(`${base}/urban/demo/health`,{signal:AbortSignal.timeout(15000),redirect:'error'})
    if(!response.ok)throw new Error(`HTTP ${response.status}`)
    health=await response.json()
  }catch{throw new Error('The persistent backend health check failed. Deploy and configure the backend before publishing this frontend.')}
  if(health.adapter!=='sqlite-synthetic'||health.synthetic!==true||health.externalConnected!==false||typeof health.adminConfigured!=='boolean')throw new Error('The URL did not return this UrbanSaarthi synthetic API’s expected health response.')
  return base
}

async function main(){
  const base=await preflight(process.env.VITE_API_BASE_URL)
  console.log(`Persistent UrbanSaarthi API reachable: ${base}`)
  console.log('Configure NAGARSEVA_CORS_ORIGINS on the backend for the exact Vercel production origin; verify browser writes after deployment.')
  const root=fileURLToPath(new URL('../..',import.meta.url))
  const result=spawnSync('npm',['--prefix','nagarseva/website','run','build'],{cwd:root,stdio:'inherit',env:{...process.env,VITE_API_BASE_URL:base}})
  if(result.error)throw result.error
  process.exitCode=result.status??1
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(error.message);process.exitCode=1})
