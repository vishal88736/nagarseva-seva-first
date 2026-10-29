// Run from website/: node --experimental-strip-types tests/check_translation_audit.mjs
// Produces review evidence; it cannot certify linguistic quality.
import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import {messages} from '../src/i18n/messages.ts'
import en from '../src/i18n/locales/en.ts'
import hi from '../src/i18n/locales/hi.ts'
import mr from '../src/i18n/locales/mr.ts'
import audit from '../src/i18n/auditMessages.ts'

const out=path.resolve('../../research/verification')
fs.mkdirSync(out,{recursive:true})
const params=s=>[...new Set(s.match(/\{\w+\}/g)||[])].sort().join(',')
const missing=[],parameterErrors=[],sameAsEnglish=[]
for(const [key,values] of Object.entries(messages))for(const language of ['hi','mr']){
  if(typeof values[language]!=='string'||!values[language].trim())missing.push({key,language})
  else if(params(values[language])!==params(values.en||key))parameterErrors.push({key,language})
  if(values[language]===(values.en||key))sameAsEnglish.push({key,language,value:values[language],reason:'Unchanged technical acronym; review allowlist'})
}
const parity=Object.fromEntries(Object.entries({hi,mr}).map(([language,resource])=>[language,{missing:Object.keys(en).filter(key=>!(key in resource)),extra:Object.keys(resource).filter(key=>!(key in en))}]))
const hardcoded=[],untranslatedCalls=[]
const proper=/^(UrbanSaarthi|SEVAMO96|UrbanSaarthi · SEVAMO96|SEVAMO96 ·|RFC 7946 · GeoJSON|OpenCity( ·( 2015)?)?|P =)\s*$/
function directory(dir){for(const item of fs.readdirSync(dir,{withFileTypes:true})){
  const file=path.join(dir,item.name)
  if(item.isDirectory()){directory(file);continue}
  if(!/\.tsx$/.test(file))continue
  const source=ts.createSourceFile(file,fs.readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX)
  function visit(node){
    const line=source.getLineAndCharacterOfPosition(node.pos).line+1
    if(ts.isJsxText(node)&&/[A-Za-z]/.test(node.text)&&!proper.test(node.text.trim()))hardcoded.push({file,line,value:node.text.trim()})
    if(ts.isJsxAttribute(node)&&node.initializer&&ts.isStringLiteral(node.initializer)&&/^(title|placeholder|aria-label|alt)$/.test(node.name.text)&&/[A-Za-z]/.test(node.initializer.text)){
      // Component `title` props are translation keys, translated by the component.
      const value=node.initializer.text
      if(!messages[value]&&!/^(https:\/\/|\d{4}-)/.test(value))hardcoded.push({file,line,value})
    }
    if(ts.isCallExpression(node)&&node.expression.getText(source)==='t'&&node.arguments[0]&&ts.isStringLiteral(node.arguments[0])&&!messages[node.arguments[0].text])untranslatedCalls.push({file,line,key:node.arguments[0].text})
    ts.forEachChild(node,visit)
  }visit(source)
}}
directory('src')
const review=Object.entries(audit).map(([key,values])=>({key,...values,review:'Native Hindi and Marathi review required; AI-assisted text, not linguistically certified'}))
const result={checkedAt:new Date().toISOString(),catalogueKeys:Object.keys(messages).length,localeFileCounts:{en:Object.keys(en).length,hi:Object.keys(hi).length,mr:Object.keys(mr).length},parity,missing,parameterErrors,sameAsEnglish,hardcoded,untranslatedCalls,nativeReviewKeys:review.map(row=>row.key),scope:'Static key, JSX and placeholder checks plus browser matrix. Source values, IDs, URLs, proper names and technical formulas remain unchanged. Does not prove native fluency.'}
fs.writeFileSync(path.join(out,'translation_audit.json'),JSON.stringify(result,null,2)+'\n')
const q=s=>'"'+String(s).replaceAll('"','""')+'"'
fs.writeFileSync(path.resolve('../../research/translation_review.csv'),'\ufeff'+[['key','English','Hindi','Marathi','Review status'],...review.map(row=>[row.key,row.en,row.hi,row.mr,row.review])].map(row=>row.map(q).join(',')).join('\r\n')+'\r\n')
const failure=missing.length+parameterErrors.length+hardcoded.length+untranslatedCalls.length+Object.values(parity).reduce((sum,p)=>sum+p.missing.length+p.extra.length,0)
console.log(JSON.stringify({status:failure?'failed':'passed',catalogueKeys:result.catalogueKeys,missing:missing.length,parameterErrors:parameterErrors.length,hardcoded:hardcoded.length,untranslatedCalls:untranslatedCalls.length,unchangedTechnicalEntries:sameAsEnglish.length,nativeReviewKeys:review.length},null,2))
if(failure)process.exitCode=1
