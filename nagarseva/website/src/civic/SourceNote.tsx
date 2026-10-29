import {useContext} from 'react'
import {CivicContext} from './CivicProvider'
import {completeness} from './analytics'
import {t,formatDate,formatNumber} from '../i18n/locale'
export function SourceNote({kind:requestedKind='demo',source,date,availability=false}:{kind?:'demo'|'manual'|'none';source?:string;date?:string|null;availability?:boolean}){
 const state=useContext(CivicContext)?.state,kind=state||requestedKind!=='demo'?requestedKind:'none',known=state?completeness(state.settlements):null
 return <span className="audit-source" role="note">{kind!=='none'&&<b className={`audit-badge ${kind}`}>{t(kind==='demo'?'audit.demo':'audit.manual')}</b>}<span>{t('audit.source')}: {source||t(kind==='demo'?'audit.generator':'audit.interfaceSource')}</span><span>{t(kind==='demo'&&date===undefined?'audit.saved':'audit.sourceDate')}: {formatDate(date===undefined&&kind==='demo'?state?.lastSavedAt:date,true)}</span>{availability&&<span title={t('audit.coverageRule')}>{t('audit.serviceCompleteness',{value:formatNumber(known)})}</span>}</span>
}
