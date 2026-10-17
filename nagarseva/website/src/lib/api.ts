import { localStore, sessionStore } from './storage'
import fallback from '../data/fallback.json'

export type Observation = {
  observation_id: string; pocket_id: string; service: string; value: number; observed_at: string;
  source_label: string; unit?: string; evidence_url: string | null; notes: string; synthetic: boolean; consent: boolean;
  verification: string; created_at: string; complaint_id?: string | null;
  history: { at: string; action: string; actor: string; notes: string }[]
}
export type ObservationInput = Pick<Observation, 'service' | 'value' | 'observed_at' | 'source_label' | 'evidence_url' | 'notes' | 'synthetic' | 'consent'>
export type ServiceRecord = {
  pocket_id: string; assurance_index: number | null; field_verified_services: number; known_services: number;
  synthetic: boolean; updated_at: string; index_description: string;
  services: Record<string, { value: number | null; unit: string; score: number | null; status: string; meets_target: boolean | null;
    target: number; target_direction: string; standard_source: string; standard_url?: string | null; standard_synthetic?: boolean; department: string; observed_at: string | null;
    source_label: string; source_url: string | null; verification: string; synthetic: boolean; stale: boolean; history: Observation[] }>
}
type NullablePocketField = 'priority_score' | 'flood_risk_score' | 'fire_risk_score' | 'structural_risk_score' | 'tenure_security_score' | 'water_hours_per_day' | 'toilets_per_100_people' | 'outage_hours_per_week' | 'waste_collection_frequency'
export type Pocket = Omit<typeof fallback.items[number], NullablePocketField> & Record<NullablePocketField, number | null> & {
  area_sqm?: number; avg_household_income_inr?: number | null; synthetic?: boolean;
  source_label?: string; source_url?: string; licence?: string; approved_by?: string;
  years_since_settlement?: number; clinic_within_1km?: number; anganwadi_within_500m?: number;
  priority_reasons?: { feature: string; label: string; contribution: number }[];
  intervention?: { top_options: { type: string; probability: number }[]; reasons: string[] };
  service_assurance?: Record<string, number | null>; service_record?: ServiceRecord
}
export type Summary = {
  pockets_prioritised: number; households_covered: number; critical_pockets: number; service_gaps_flagged: number;
  avg_assurance_index: number | null; resident_verified_closures: number; open_complaints: number; sla_breaches: number;
  urgent_complaints: number; within_sla_pct: number | null; median_response_days: number | null;
  known_services: number; field_verified_services: number; real_observations: number; updated_at: string | null;
  wards: { ward: string; city: string; compliance: number | null; assurance_index: number | null; gaps: number; field_verified_services: number }[];
  data_scope: string; synthetic: boolean
}
export type FeasibilityInput = {
  land_area_sqm: number; fsi: number; eligible_households: number; rehab_area_sqft: number;
  construction_cost_per_sqft: number; market_sale_rate_per_sqft: number; tdr_value_per_sqft: number;
  premiums_and_fees_pct: number; sales_share_pct: number; cost_inflation_pct?: number
}
export type FeasibilityResult = {
  gross_built_up_area_sqft: number; free_rehab_area_sqft: number; saleable_area_sqft: number;
  construction_cost_inr: number; fees_inr: number; tdr_support_inr: number; gross_sales_support_inr: number;
  developer_profit_inr: number; developer_margin_pct: number; indicative_irr_pct: number;
  break_even_market_rate_per_sqft: number | null; verdict: string; physically_feasible: boolean; rehab_area_shortfall_sqft: number
}
export type Classification = { category: string; urgency: string; confidence: number | null; expected_resolution_days: number; classification_method: string }
export type Complaint = Classification & {
  complaint_id: string; text: string; pocket_id: string; language: string; status: string; synthetic: boolean;
  consent: boolean; created_at: string; due_at: string; assigned_to: string | null; department: string;
  assigned_at: string | null; resolved_at: string | null; sla_breached: boolean; escalation_required: boolean;
  escalations: number; pending_observation_id: string | null; history: { at: string; action: string; actor: string; notes: string }[]
  repair_observation?: Observation | null
}
export type Receipt = { complaint_id: string; receipt_token: string }
export type ComplaintAction = { action: 'assign' | 'start' | 'complete' | 'escalate'; officer: string; notes: string; department?: string; category?: string; urgency?: string; observation?: ObservationInput }
export type Plan = {
  status: string; optimal: boolean; message: string; spent_inr: number; impact_people: number; population_reached: number;
  vulnerable_share: number; ward_coverage: number; ward_counts: Record<string, number>;
  selected: { pocket_id: string; city: string; ward: string; priority_score: number; cost_inr: number; impact: number }[]
}
export type Optimisation = Plan & {
  solver: string; budget_inr: number; constraints: { min_vulnerable_share: number; min_wards: number };
  baseline: Plan & { method: string }; pareto: { budget_inr: number; impact_people: number | null; spent_inr: number; status: string }[];
  impact_description: string
}
export type Eligibility = {
  eligible_schemes: string[]; reasons: string[]; documents_required: string[]; next_steps: string[]; disclaimer: string;
  source_url: string; policy_version: string; reviewed_on: string; income_band: string; screening_status: string
}
export type EvaluationInput = {
  participant_ref: string; task: string; language: string; baseline_seconds: number | null; app_seconds: number | null;
  completed: boolean; expected_category: string | null; predicted_category: string | null; feedback: string; synthetic: boolean; consent: boolean
}
export type Evidence = {
  locations: (Record<string, unknown> & { pocket_id: string })[]; commitments: Record<string, unknown>[];
  observations: Observation[]; evaluations: (EvaluationInput & { evaluation_id: string; created_at: string })[];
  description: string; metrics: { real_observations: number; field_verified_observations: number; real_evaluations: number;
    paired_sample_size: number; median_seconds_saved: number | null; completion_rate: number | null; usability_sample_size: number;
    real_reports: number; real_verified_closures: number;
    classification_by_language: Record<string, { sample_size: number; accuracy: number | null }> }
}
export type ModelCards = { cards: Record<string, { loaded: boolean; source: string | null; metrics: Record<string, unknown> }>; synthetic: boolean; scope: string }

export const API_BASE = ((import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
export let offline = false
function connection(isOffline: boolean) {
  offline = isOffline
  window.dispatchEvent(new CustomEvent('nagarseva-connection', { detail: isOffline }))
}
class ApiError extends Error { constructor(message: string, public status: number) { super(message) } }
export async function request<T>(path: string, fallbackValue?: () => T, body?: unknown, headers?: Record<string, string>, write = false): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), path === '/optimize' ? 25000 : 12000)
  try {
    const response = await fetch(`${API_BASE}${path}`, { method: body === undefined ? 'GET' : 'POST',
      headers: { 'Content-Type': 'application/json', ...headers }, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal })
    connection(false)
    if (!response.ok) {
      const problem = await response.json().catch(() => ({}))
      const message = typeof problem.detail === 'string' ? problem.detail : Array.isArray(problem.detail) ? problem.detail.map((e: { msg: string }) => e.msg).join('; ') : `Request failed (${response.status})`
      throw new ApiError(message, response.status)
    }
    const result = await response.json() as T
    if (write) window.dispatchEvent(new CustomEvent('nagarseva-data-changed', { detail: path }))
    return result
  } catch (error) {
    if (error instanceof ApiError && error.status < 500) throw error
    connection(true)
    if (!write && fallbackValue) return fallbackValue()
    throw new Error('The server could not confirm this request. Your form is preserved; reconnect and refresh the record before trying again.')
  } finally { window.clearTimeout(timeout) }
}
const officerHeaders = () => ({ 'X-Officer-Key': sessionStore.getItem('nagarseva-officer-key') || '' })
export const health = () => request<{ status: string; mode: string; officer_auth_required: boolean }>('/health')
export const getModelCards = () => request<ModelCards>('/models/cards', () => ({ cards: {}, synthetic: true, scope: 'Model benchmarks are unavailable offline.' }))
export type WeatherContext = {
  pocket_id: string; provider: string; source_url: string; licence: string; licence_url: string; terms_url: string;
  synthetic: false; location_synthetic: boolean; timezone: string; coordinate_scope: string;
  status: 'live' | 'cached' | 'stale' | 'unavailable' | 'disabled'; fetched_at: string | null; cache_age_seconds: number | null;
  requested_coordinates?: { lat: number; lon: number }; grid_coordinates?: { lat: number; lon: number };
  days: { date: string; precipitation_mm: number | null; precipitation_probability_pct: number | null; max_temperature_c: number | null }[]
}
export const getWeather = (id: string) => request<WeatherContext>(`/context/${encodeURIComponent(id)}/weather`)
export const getPockets = () => request<{ items: Pocket[]; total: number }>('/pockets', () => ({ items: fallback.items, total: fallback.items.length }))
export const getPocket = (id: string) => request<Pocket>(`/pockets/${encodeURIComponent(id)}`, () => {
  const pocket = fallback.items.find(p => p.pocket_id === id)
  if (!pocket) throw new Error('This project is unavailable in the offline sample. Reconnect or select an available project.')
  return pocket
})
export function localServiceRecord(p: Pocket): ServiceRecord {
  const definitions = [['water', 'water_hours_per_day', 'hours/day', 4, true], ['sanitation', 'toilets_per_100_people', 'toilets/100 people', 15, true], ['power', 'outage_hours_per_week', 'outage hours/week', 12, false], ['waste', 'waste_collection_frequency', 'collections/week', 3, true], ['health', 'clinic_within_1km', 'clinic within 1 km (0/1)', 1, true]] as const
  const services: ServiceRecord['services'] = {}
  for (const [name, field, unit, target, higher] of definitions) {
    const raw = p[field as keyof Pocket]
    const value = typeof raw === 'number' && Number.isFinite(raw) ? raw : null
    const meets = value === null ? null : higher ? value >= target : value <= target
    const score = value === null ? null : Math.min(100, higher ? value / target * 100 : value <= target ? 100 : target / value * 100)
    services[name] = { value, unit, target, target_direction: higher ? 'at_least' : 'at_most', score, status: value === null ? 'unknown' : meets ? 'compliant' : 'breach', meets_target: meets,
      department: name, standard_source: 'NagarSeva demo planning target; replace with an approved project commitment', observed_at: null,
      source_label: 'Offline synthetic sample; no field observation', source_url: null, verification: value === null ? 'unknown' : 'synthetic', synthetic: true, stale: false, history: [] }
  }
  const scores = Object.values(services).map(s => s.score).filter((x): x is number => x !== null)
  return { pocket_id: p.pocket_id, services, assurance_index: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null, field_verified_services: 0, known_services: scores.length, synthetic: true, updated_at: new Date().toISOString(), index_description: 'Average attainment of explicit demo planning targets; offline sample only.' }
}
export const getServiceRecord = (p: Pocket) => request<ServiceRecord>(`/service/${encodeURIComponent(p.pocket_id)}/assurance`, () => localServiceRecord(p))
export function sampleSummary(): Summary {
  const records = fallback.items.map(localServiceRecord)
  const scores = records.map(r => r.assurance_index).filter((v): v is number => v !== null)
  const wardMap = new Map<string, Summary['wards'][number] & { known: number; compliant: number; scores: number[] }>()
  records.forEach((record, i) => {
    const p = fallback.items[i], key = `${p.city} / ${p.ward}`
    const ward = wardMap.get(key) || { city: p.city, ward: p.ward, compliance: null, assurance_index: null, gaps: 0, field_verified_services: 0, known: 0, compliant: 0, scores: [] }
    const services = Object.values(record.services)
    ward.known += record.known_services; ward.compliant += services.filter(s => s.status === 'compliant').length
    ward.gaps += Number(services.some(s => s.status === 'breach'))
    if (record.assurance_index !== null) ward.scores.push(record.assurance_index)
    wardMap.set(key, ward)
  })
  return { pockets_prioritised: fallback.items.length, households_covered: fallback.items.reduce((n, p) => n + p.households, 0), critical_pockets: fallback.items.filter(p => p.priority_score >= 75).length,
    service_gaps_flagged: records.filter(r => Object.values(r.services).some(s => s.status === 'breach')).length,
    avg_assurance_index: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
    resident_verified_closures: 0, open_complaints: 0, sla_breaches: 0, urgent_complaints: 0, within_sla_pct: null, median_response_days: null,
    known_services: records.reduce((sum, r) => sum + r.known_services, 0), field_verified_services: 0, real_observations: 0, updated_at: null, synthetic: true,
    wards: [...wardMap.values()].map(w => ({ ...w, compliance: w.known ? w.compliant / w.known * 100 : null, assurance_index: w.scores.length ? w.scores.reduce((a, b) => a + b, 0) / w.scores.length : null })),
    data_scope: 'Offline synthetic sample only; operational records require the server' }
}
export const getSummary = () => request<Summary>('/stats/summary', sampleSummary)

export function localFeasibility(p: FeasibilityInput): FeasibilityResult {
  const gross = p.land_area_sqm * 10.7639 * p.fsi, rehab = p.eligible_households * p.rehab_area_sqft, sale = Math.max(gross - rehab, 0)
  const cost = gross * p.construction_cost_per_sqft * (1 + (p.cost_inflation_pct || 0) / 100), fees = cost * p.premiums_and_fees_pct
  const tdr = gross * p.tdr_value_per_sqft, revenue = sale * p.market_sale_rate_per_sqft * p.sales_share_pct, profit = revenue + tdr - cost - fees
  const irr = (Math.max(revenue + tdr, 1) / Math.max(cost + fees, 1)) ** (1 / 3) - 1
  const areaShortfall = Math.max(rehab - gross, 0), physicallyFeasible = areaShortfall === 0, salesArea = sale * p.sales_share_pct
  return { physically_feasible: physicallyFeasible, rehab_area_shortfall_sqft: Math.round(areaShortfall), gross_built_up_area_sqft: Math.round(gross), free_rehab_area_sqft: Math.round(rehab), saleable_area_sqft: Math.round(sale), construction_cost_inr: Math.round(cost), fees_inr: Math.round(fees),
    tdr_support_inr: Math.round(tdr), gross_sales_support_inr: Math.round(revenue), developer_profit_inr: Math.round(profit), developer_margin_pct: Math.round(profit / Math.max(revenue + tdr, 1) * 1000) / 10,
    indicative_irr_pct: Math.round(irr * 1000) / 10, break_even_market_rate_per_sqft: physicallyFeasible && salesArea > 0 ? Math.round(Math.max(cost + fees - tdr, 0) / salesArea) : null, verdict: !physicallyFeasible ? 'Not viable' : profit >= 0 && irr >= .08 ? 'Viable' : profit >= -cost * .1 ? 'Borderline' : 'Not viable' }
}
export function localSensitivity(p: FeasibilityInput) {
  return [['Market rate', 'market_sale_rate_per_sqft', -.2], ['Market rate', 'market_sale_rate_per_sqft', .2], ['Construction inflation', 'cost_inflation_pct', 10], ['FSI', 'fsi', -.3], ['FSI', 'fsi', .3]].map(([name, key, delta]) => {
    const field = key as keyof FeasibilityInput, d = delta as number
    const input = { ...p, [field]: field === 'cost_inflation_pct' ? (p[field] || 0) + d : (p[field] || 0) * (1 + d) }
    const value = localFeasibility(input)
    return { factor: `${name} ${d > 0 ? '+' : ''}${field === 'cost_inflation_pct' ? d : Math.round(d * 100)}%`, profit_inr: value.developer_profit_inr, margin_pct: value.developer_margin_pct, verdict: value.verdict }
  }).sort((a, b) => a.profit_inr - b.profit_inr)
}
export const simulate = (p: FeasibilityInput) => request<{ result: FeasibilityResult; sensitivity: ReturnType<typeof localSensitivity> }>('/feasibility/simulate', () => ({ result: localFeasibility(p), sensitivity: localSensitivity(p) }), p)
export const optimise = (budget: number, vulnerable: number, wards: number, _pockets?: Pocket[]) => request<Optimisation>('/optimize', undefined, { budget_inr: budget, min_vulnerable_share: vulnerable, min_wards: wards })
export const checkEligibility = (inputs: Record<string, unknown>) => request<Eligibility>('/eligibility/check', undefined, inputs)
export const classify = (text: string, language: string) => request<Classification>('/grievance/classify', () => {
  const terms: Record<string, string[]> = { water: ['water', 'paani', 'पानी', 'पाणी'], sanitation: ['toilet', 'शौचालय'], power: ['power', 'light', 'bijli', 'बिजली'], waste: ['garbage', 'kachra', 'कचरा'], drainage: ['drain', 'nala', 'नाला'], health: ['fever', 'clinic'], safety: ['unsafe', 'fire'], housing: ['sra', 'housing'] }
  const category = Object.keys(terms).find(key => terms[key].some(term => text.toLowerCase().includes(term))) || 'other'
  const urgency = /fire|unsafe|fever|danger|गंदा|आग|धोका|खतरा/.test(text.toLowerCase()) ? 'urgent' : 'standard'
  return { category, urgency, confidence: null, expected_resolution_days: urgency === 'urgent' ? 2 : 7, classification_method: 'Offline keyword rules' }
}, { text, language })
function savedReceipts(): Receipt[] {
  try { const value = JSON.parse(localStore.getItem('nagarseva-receipts') || '[]'); return Array.isArray(value) ? value.filter(r => typeof r.complaint_id === 'string' && typeof r.receipt_token === 'string') : [] } catch { return [] }
}
export function saveReceipt(receipt: Receipt) {
  localStore.setItem('nagarseva-receipts', JSON.stringify([receipt, ...savedReceipts().filter(r => r.complaint_id !== receipt.complaint_id)]))
}
export const submitComplaint = async (text: string, language: string, pocket_id: string, synthetic: boolean, consent: boolean) => {
  const result = await request<Complaint & Receipt>('/grievances', undefined, { text, language, pocket_id, synthetic, consent }, undefined, true)
  saveReceipt({ complaint_id: result.complaint_id, receipt_token: result.receipt_token })
  return result
}
export const getComplaints = (pocket_id?: string) => request<{ items: Complaint[]; total: number }>(`/grievances${pocket_id ? `?pocket_id=${encodeURIComponent(pocket_id)}` : ''}`, undefined, undefined, officerHeaders())
export const trackComplaint = (receipt: Receipt) => request<Complaint>(`/grievances/${encodeURIComponent(receipt.complaint_id)}`, undefined, undefined, { 'X-Receipt-Token': receipt.receipt_token })
export const getMyComplaints = async () => {
  const receipts = savedReceipts()
  const results = await Promise.allSettled(receipts.map(trackComplaint))
  const items = results.flatMap(r => r.status === 'fulfilled' ? [r.value] : [])
  const errors = results.filter(r => r.status === 'rejected')
  return { items, receipts, unavailable: errors.length }
}
export const confirmComplaint = (id: string, resolved: boolean, notes: string) => {
  const receipt = savedReceipts().find(r => r.complaint_id === id)
  if (!receipt) return Promise.reject(new Error('Restore the original receipt before confirming this report.'))
  return request<Complaint>(`/grievances/${encodeURIComponent(id)}/confirm`, undefined, { resolved, notes }, { 'X-Receipt-Token': receipt.receipt_token }, true)
}
export const actOnComplaint = (id: string, action: ComplaintAction) => request<Complaint>(`/grievances/${encodeURIComponent(id)}/action`, undefined, action, officerHeaders(), true)
export const addObservation = (id: string, observation: ObservationInput) => request<Observation>(`/service/${encodeURIComponent(id)}/observations`, undefined, observation, officerHeaders(), true)
export const verifyObservation = (id: string, reviewer: string, notes: string) => request<Observation>(`/observations/${encodeURIComponent(id)}/verify`, undefined, { reviewer, notes }, officerHeaders(), true)
export const getEvidence = () => request<Evidence>('/pilot/evidence', undefined, undefined, officerHeaders())
export const addEvaluation = (input: EvaluationInput) => request<EvaluationInput>('/pilot/evaluations', undefined, input, officerHeaders(), true)
export const importLocation = (input: Record<string, unknown>) => request<Record<string, unknown>>('/pilot/locations', undefined, input, officerHeaders(), true)
export const setCommitment = (pocketId: string, input: Record<string, unknown>) => request<Record<string, unknown>>(`/service/${encodeURIComponent(pocketId)}/commitment`, undefined, input, officerHeaders(), true)
export const estimateCost = (p: Pocket) => request<{ construction_cost_per_sqft: number; cost_interval: number[]; expected_delay_months: number; delay_interval: number[] }>('/cost/estimate', undefined, { units: Math.max(1, Math.round(p.households)), land_value_per_sqm: 40000, FSI: 2.7, cross_subsidy_ratio: .5 })

export function downloadJson(name: string, value: unknown) { download(name, JSON.stringify(value, null, 2), 'application/json') }
export function downloadCsv(name: string, rows: Record<string, unknown>[]) {
  if (!rows.length) return
  const keys = [...new Set(rows.flatMap(row => Object.keys(row)))]
  const cell = (value: unknown) => {
    const raw = value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value)
    const safe = /^[\s]*[=+@\-\t\r]/.test(raw) ? `'${raw}` : raw
    return `"${safe.replaceAll('"', '""')}"`
  }
  download(name, [keys.map(cell).join(','), ...rows.map(row => keys.map(k => cell(row[k])).join(','))].join('\r\n'), 'text/csv;charset=utf-8')
}
function download(name: string, contents: string, type: string) {
  const url = URL.createObjectURL(new Blob([contents], { type }))
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
const currentLocale = () => document.documentElement.lang === 'hi' ? 'hi-IN' : document.documentElement.lang === 'mr' ? 'mr-IN' : 'en-IN'
export const money = (n: number | null | undefined) => n == null || !Number.isFinite(n) ? '—' : Math.abs(n) >= 1e7 ? `₹${(n / 1e7).toLocaleString(currentLocale(), { maximumFractionDigits: 1 })} Cr` : Math.abs(n) >= 1e5 ? `₹${(n / 1e5).toLocaleString(currentLocale(), { maximumFractionDigits: 1 })} L` : `₹${n.toLocaleString(currentLocale(), { maximumFractionDigits: 0 })}`
export const number = (n: number | null | undefined) => n == null || !Number.isFinite(n) ? '—' : Math.round(n).toLocaleString(currentLocale())
export const dateTime = (value: string | null | undefined) => value ? new Date(value).toLocaleString(currentLocale(), { dateStyle: 'medium', timeStyle: 'short' }) : '—'
