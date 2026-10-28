import { messages as legacy } from './catalog.ts'
import en from './locales/en.ts'
import hi from './locales/hi.ts'
import mr from './locales/mr.ts'

export type Message = { en?: string; hi: string; mr: string }
const product: Record<string, Message> = Object.fromEntries(Object.keys(en).map(key=>[key,{en:en[key as keyof typeof en],hi:hi[key as keyof typeof hi],mr:mr[key as keyof typeof mr]}]))
// Existing screens use English source keys; aliases let them share feature dictionaries.
const aliases=Object.fromEntries(Object.values(product).filter(entry=>!legacy[entry.en!]).map(entry=>[entry.en!,entry]))
export const messages: Record<string,Message> = {...legacy,...aliases,...product}
