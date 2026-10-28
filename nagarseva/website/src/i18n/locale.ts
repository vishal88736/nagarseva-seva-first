import { messages } from './catalog.ts'

export const LANGUAGES = ['en', 'hi', 'mr'] as const
export type Language = typeof LANGUAGES[number]
export const LOCALE: Record<Language, string> = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' }
export const LANGUAGE_LABELS: Record<Language, string> = { en: 'English', hi: 'हिंदी', mr: 'मराठी' }
export const LANGUAGE_KEY = 'urbansaarthi-language'
export function validLanguage(value: unknown): value is Language { return LANGUAGES.includes(value as Language) }
let currentLanguage: Language = 'en'
export function getLanguage() { return currentLanguage }
export function storedLanguage(): Language { try { const value = localStorage.getItem(LANGUAGE_KEY); return validLanguage(value) ? value : 'en' } catch { return 'en' } }
export function setLanguage(language: Language) { currentLanguage = language; try { localStorage.setItem(LANGUAGE_KEY, language) } catch { /* A language change still works without persistent storage. */ } }
export type Params = Record<string, string | number | null | undefined>
const patterns = Object.keys(messages).filter(key => /\{\w+\}/.test(key)).map(key => {
  const names: string[] = []
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\\\{(\w+)\\\}/g, (_match, name: string) => { names.push(name); return '(.+?)' })
  return { key, names, regex: new RegExp('^' + escaped + '$', 's') }
})
export function translate(language: Language, key: string, params: Params = {}): string {
  let values = params, entry = messages[key]
  if (!entry && language !== 'en') {
    for (const pattern of patterns) {
      const match = pattern.regex.exec(key)
      if (match) { entry = messages[pattern.key]; values = { ...Object.fromEntries(pattern.names.map((name, i) => [name, match[i + 1]])), ...params }; break }
    }
  }
  const text = language === 'en' ? key : entry?.[language] || key
  return text.replace(/\{(\w+)\}/g, (original, name: string) => values[name] === undefined || values[name] === null ? original : String(values[name]))
}
export const t = (key: string, params?: Params) => translate(currentLanguage, key, params)
export function formatNumber(value: number | null | undefined, digits = 1, minimumIntegerDigits = 1) { return value === null || value === undefined ? t('Unavailable') : new Intl.NumberFormat(LOCALE[currentLanguage], { maximumFractionDigits: digits, minimumIntegerDigits }).format(value) }
export function formatDecimal(value: number | null | undefined, digits = 1) { return value === null || value === undefined ? t('Unavailable') : new Intl.NumberFormat(LOCALE[currentLanguage], { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value) }
export function formatMoney(value: number) { return new Intl.NumberFormat(LOCALE[currentLanguage], { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value) }
export function formatDate(value: string | null | undefined, time = false) {
  if (!value) return t('Not supplied')
  if (/^\d{4}$/.test(value)) return formatNumber(Number(value), 0).replace(/[,٬]/g, '')
  const instant = new Date(value)
  if (!Number.isFinite(instant.getTime())) return value
  return new Intl.DateTimeFormat(LOCALE[currentLanguage], { year: 'numeric', month: 'short', day: 'numeric', ...(time ? { hour: '2-digit', minute: '2-digit' } as const : {}), ...(/^\d{4}-\d{2}-\d{2}$/.test(value) ? { timeZone: 'UTC' } : {}) }).format(instant)
}
export function errorText(value: string): string {
  if (!value) return ''
  if (/Unexpected token|Unexpected end of JSON|JSON\.parse|not valid JSON/i.test(value)) return t('The file is not valid JSON. Check its format and try again.')
  if (/Failed to fetch|NetworkError|Load failed|fetch failed/i.test(value)) return t('Cannot connect to the API. Check the connection and retry.')
  if (/aborted|AbortError|timed out/i.test(value)) return t('The request timed out. Please retry.')
  const translated = t(value.replace(/^Value error, /, ''))
  if (currentLanguage !== 'en' && translated === value && /[a-zA-Z]{3}/.test(value) && !messages[value]) return t('The request could not be completed. Check the supplied values and retry.')
  return translated
}
const STATUS_LABELS: Record<string, string> = {
  planned:'Planned',in_progress:'In progress',reported_complete:'Reported complete',awaiting_verification:'Awaiting verification',verified:'Verified',requiring_reinspection:'Requires reinspection',cancelled:'Cancelled',completed:'Physically completed',unverified:'Unverified',disputed:'Disputed',open:'Open',resolved:'Resolved',reopened:'Reopened',reported:'Reported',field_verified:'Field reviewed',historical_published:'Historical published',rejected:'Rejected',passed:'Passed target review',reinspection_required:'Requires reinspection',water:'Water',sanitation:'Sanitation',drainage:'Drainage',waste:'Waste',housing:'Housing',other:'Other',access:'Access',risk:'Risk',country:'Country',state:'State',district:'District',city:'City',town:'Town',ward:'Ward',settlement:'Settlement',start:'Start work',report_complete:'Report physical completion',request_verification:'Request verification',verify:'Verify',reopen:'Reopen work',at_least:'At least',at_most:'At most',inspection:'Inspection',reinspection:'Reinspection',not_observed:'Not observed',functioning:'Functioning',partly_functioning:'Partly functioning',not_functioning:'Not functioning',clear:'Clear',partly_blocked:'Partly blocked',blocked:'Blocked',school:'School',health:'Health',transport:'Transport',toilets:'Toilets',employment:'Employment'
}
Object.assign(STATUS_LABELS, {
  created: 'Created', plan_updated: 'Plan updated', complaint_requires_reinspection: 'Complaint requires reinspection',
  complaint_reopened: 'Complaint reopened', complaint_resolved: 'Complaint resolved', evidence_attached: 'Evidence attached',
  evidence_reference_recorded: 'Evidence reference recorded', complete: 'Reported complete',
  authorized_manual: 'Authorized manual observation', water_deficit: 'Water-service deficit',
  sanitation_deficit: 'Sanitation and drainage deficit', housing_deficit: 'Housing-condition deficit',
  access_deficit: 'Essential-amenity access deficit', risk_index: 'Environmental or infrastructure risk',
  proposed: 'Proposed', approved: 'Approved', ongoing: 'Ongoing', unknown: 'Unknown',
})
export function statusText(value: string) { return t(STATUS_LABELS[value] || value.replaceAll('_', ' ')) }
