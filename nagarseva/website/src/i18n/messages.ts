import auditMessages from './auditMessages.ts'
import demoMessages from './demoMessages.ts'
import integrationMessages from './integrationMessages.ts'
import { messages as legacy } from './catalog.ts'
import en from './locales/en.ts'
import hi from './locales/hi.ts'
import mr from './locales/mr.ts'

export type Message = { en?: string; hi: string; mr: string }
const product: Record<string, Message> = Object.fromEntries(Object.keys(en).map(key=>[key,{en:en[key as keyof typeof en],hi:hi[key as keyof typeof hi],mr:mr[key as keyof typeof mr]}]))
// Existing screens use English source keys; aliases let them share feature dictionaries.
const aliases=Object.fromEntries(Object.values(product).filter(entry=>!legacy[entry.en!]).map(entry=>[entry.en!,entry]))
const extensions: Record<string,Message> = {...demoMessages,...integrationMessages,...auditMessages}
const extensionAliases=Object.fromEntries(Object.values(extensions).filter(entry=>entry.en).map(entry=>[entry.en!,entry]))
// Source record values stay unchanged; reserved fixture patterns only affect display.
const recordNameAliases: Record<string, Message> = Object.fromEntries([
  ['Demo Settlement {number}', 'd.name.settlement'],
  ['Demo Ward {number}', 'd.name.ward'],
  ['Demo Locality {number}', 'd.name.locality'],
  ['Demo Issue {number}', 'd.name.issue'],
  ['Demo Project {number}', 'd.name.project'],
  ['Demo Milestone {number}', 'd.name.milestone'],
  ['Demo Officer {number}', 'd.name.officer'],
  ['Demo Development Team {number}', 'd.name.team'],
].map(([source,key])=>[source,extensions[key]]))
export const messages: Record<string,Message> = {...legacy,...aliases,...product,...extensionAliases,...extensions,...recordNameAliases}
