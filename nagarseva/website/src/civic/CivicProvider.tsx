import {createContext,useCallback,useContext,useEffect,useRef,useState} from 'react'
import type {ReactNode} from 'react'
import {sqliteDemoAdapter} from './adapter'
import type {CivicAdapter,CivicState,DemoHealth} from './types'
export const operationId=():string=>globalThis.crypto?.randomUUID?.()||'demo-operation-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2)
type Context={state:CivicState|null;health:DemoHealth|null;loading:boolean;busy:boolean;error:string;key:string;setKey:(key:string)=>void;reload:()=>Promise<void>;run:(kind:string,payload:Record<string,unknown>,entityId?:string,operation?:string)=>Promise<string>}
export const CivicContext=createContext<Context|null>(null)
export function useCivic(){const value=useContext(CivicContext);if(!value)throw new Error('CivicProvider required');return value}
export function CivicProvider({children,adapter=sqliteDemoAdapter}:{children:ReactNode;adapter?:CivicAdapter}) {
  const [state,setState]=useState<CivicState|null>(null),[health,setHealth]=useState<DemoHealth|null>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState('')
  const [key,updateKey]=useState(()=>{try{return sessionStorage.getItem('urbansaarthi-officer-key')||''}catch{return ''}})
  const current=useRef(state),locked=useRef(false)
  const reload=useCallback(async()=>{setLoading(true);setError('');try{const [next,h]=await Promise.all([adapter.load(),adapter.health()]);current.current=next;setState(next);setHealth(h)}catch(e){setError((e as Error).message)}finally{setLoading(false)}},[adapter])
  useEffect(()=>{void reload()},[reload])
  function setKey(next:string){updateKey(next);try{sessionStorage.setItem('urbansaarthi-officer-key',next)}catch{/* Session-only memory still supports a permitted operation. */}}
  async function run(kind:string,payload:Record<string,unknown>,entityId?:string,operation=operationId()) {
    if(locked.current||!current.current)throw new Error('demo.error.busy')
    locked.current=true;setBusy(true);setError('')
    try{const result=await adapter.mutate({kind,payload,entityId,expectedRevision:current.current.revision,operationId:operation},key);current.current=result.state;setState(result.state);return result.entityId}
    catch(e){setError((e as Error).message);if((e as Error).message==='demo.error.revision')await reload();throw e}finally{locked.current=false;setBusy(false)}
  }
  return <CivicContext.Provider value={{state,health,loading,busy,error,key,setKey,reload,run}}>{children}</CivicContext.Provider>
}
