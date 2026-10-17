import { localStore } from '../lib/storage'
import { Download, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Badge, Note, Panel, SectionTitle, chartColors } from '../components/Shared'
import { ErrorNote } from '../components/Records'
import { useI18n } from '../i18n'
import { householdCosts, HouseholdOption, initialHouseholdOptions } from '../lib/affordability'
import { downloadJson, FeasibilityInput, FeasibilityResult, localFeasibility, localSensitivity, money, Pocket, simulate } from '../lib/api'

function projectDefaults(pocket: Pocket): FeasibilityInput {
  return { land_area_sqm: Math.max(1, pocket.area_sqm || 10000), fsi: 2.7, eligible_households: Math.max(0, Math.round(pocket.households)), rehab_area_sqft: 300, construction_cost_per_sqft: 3200, market_sale_rate_per_sqft: 14500, tdr_value_per_sqft: 900, premiums_and_fees_pct: .12, sales_share_pct: .65, cost_inflation_pct: 0 }
}
export function Simulator({ pocket }: { pocket: Pocket }) {
  const { t } = useI18n(), storageKey = `nagarseva-scenario-${pocket.pocket_id}`
  const [saved] = useState(() => { try { return JSON.parse(localStore.getItem(storageKey) || 'null') } catch { return null } })
  const [input, setInput] = useState<FeasibilityInput>(() => ({ ...projectDefaults(pocket), ...saved?.input }))
  const [result, setResult] = useState<FeasibilityResult>(() => localFeasibility(input)), [sensitivity, setSensitivity] = useState(localSensitivity(input)), [error, setError] = useState('')
  const [income, setIncome] = useState<number>(saved?.income ?? Math.round(pocket.avg_household_income_inr || 18000)), [threshold, setThreshold] = useState<number>(saved?.threshold ?? 30)
  const [options, setOptions] = useState<HouseholdOption[]>(() => saved?.options ?? initialHouseholdOptions.map(o => ({ ...o })))
  useEffect(() => {
    let current = true
    setResult(localFeasibility(input)); setSensitivity(localSensitivity(input))
    const timer = window.setTimeout(() => { simulate(input).then(data => { if (current) { setResult(data.result); setSensitivity(data.sensitivity); setError('') } }).catch(e => { if (current) setError(e.message) }) }, 300)
    return () => { current = false; window.clearTimeout(timer) }
  }, [input])
  useEffect(() => { localStore.setItem(storageKey, JSON.stringify({ input, income, threshold, options })) }, [input, income, threshold, options])
  const set = (key: keyof FeasibilityInput, value: number) => setInput(old => ({ ...old, [key]: value }))
  const waterfall = [{ name: t('saleSupport'), value: result.gross_sales_support_inr, fill: chartColors.teal }, { name: t('tdrSupport'), value: result.tdr_support_inr, fill: chartColors.amber }, { name: t('construction'), value: -result.construction_cost_inr, fill: chartColors.red }, { name: t('fees'), value: -result.fees_inr, fill: '#9aaead' }, { name: t('margin'), value: result.developer_profit_inr, fill: chartColors.navy }]
  const fields: [keyof FeasibilityInput, string, number, number, number][] = [
    ['land_area_sqm', t('landArea'), 1, 1000000, 1], ['fsi', 'FSI', .1, 10, .1], ['eligible_households', t('eligibleRehab'), 0, 100000, 1],
    ['rehab_area_sqft', t('freeRehab'), 1, 1000, 1], ['market_sale_rate_per_sqft', t('marketRate'), 1, 100000, 100], ['construction_cost_per_sqft', t('constructionCost'), 1, 20000, 50],
    ['sales_share_pct', `${t('salesShare')} (0–1)`, 0, 1, .01], ['tdr_value_per_sqft', t('tdrValue'), 0, 10000, 50], ['premiums_and_fees_pct', `${t('fees')} (0–1)`, 0, 1, .01], ['cost_inflation_pct', `${t('constructionInflation')} (%)`, -50, 200, 1],
  ]
  const householdFields: [keyof HouseholdOption, string, number][] = [['rent_emi', 'rentEmi', 1000000], ['maintenance', 'maintenance', 1000000], ['utilities', 'utilities', 1000000], ['transport', 'transport', 1000000], ['income_loss', 'incomeLoss', 1000000], ['temporary_rent', 'temporaryRent', 1000000], ['temporary_months', 'temporaryMonths', 120], ['moving_cost', 'movingCost', 10000000]]
  const scenario = { pocket_id: pocket.pocket_id, project_assumptions: input, feasibility: result, sensitivity, household_income_inr: income,
    user_planning_limit_pct: threshold, household_options: options.map(o => ({ ...o, ...householdCosts(o, income, threshold) })),
    scope: 'Editable planning assumptions; household costs are illustrative until replaced with consented observations or verified quotes. The planning limit is not an official lending or eligibility rule.', exported_at: new Date().toISOString() }
  return <div className="page-pad"><SectionTitle eyebrow={`${pocket.pocket_id} · ${t('financialSimulator')}`} title={t('simulatorTitle')} description={t('simulatorDesc')} action={<button className="button outline" onClick={() => downloadJson(`${pocket.pocket_id}-scenario.json`, scenario)}><Download size={15} />{t('exportScenario')}</button>} /><ErrorNote message={error} />
    <div className="simulator-grid"><Panel title={t('projectAssumptions')} subtitle={t('editable')}><div className="form-grid">{fields.map(([key, label, min, max, step]) => <label className="field" key={key}><span>{label}</span><input aria-label={label} type="number" min={min} max={max} step={step} value={input[key] ?? 0} onChange={e => { const value = Number(e.target.value); if (Number.isFinite(value) && value >= min && value <= max) set(key, value) }} /></label>)}</div><Note>{t('screeningProxy')}</Note></Panel>
      <div className="sim-results"><div className={`verdict-card ${result.verdict.toLowerCase().replace(' ', '-')}`}><div><Badge tone={result.verdict === 'Viable' ? 'teal' : 'red'}>{t(result.verdict === 'Viable' ? 'viable' : result.verdict === 'Borderline' ? 'borderline' : 'notViable')}</Badge><h2>{t('developerMargin')} <strong>{result.developer_margin_pct}%</strong></h2><p>{t('indicativeIrr')} {result.indicative_irr_pct}% · {t('breakEven')} {result.break_even_market_rate_per_sqft === null ? '—' : money(result.break_even_market_rate_per_sqft)} / {t('sqFt')}</p></div><TrendingUp size={42} /></div>
        {!result.physically_feasible && <div className="error-note" role="status">{t('rehabCapacityShortfall')} {result.rehab_area_shortfall_sqft.toLocaleString()} {t('sqFt')}</div>}<div className="result-metrics"><div><span>{t('saleableArea')}</span><strong>{Math.round(result.saleable_area_sqft).toLocaleString()} {t('sqFt')}</strong></div><div><span>{t('developerProfit')}</span><strong>{money(result.developer_profit_inr)}</strong></div><div><span>{t('reservedRehab')}</span><strong>{Math.round(result.free_rehab_area_sqft).toLocaleString()} {t('sqFt')}</strong></div></div>
        <Panel title={t('projectWaterfall')} subtitle={t('supportCostFlows')}><ResponsiveContainer width="100%" height={240}><BarChart data={waterfall}><CartesianGrid vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis tickFormatter={v => `₹${Math.round(v / 1e7)}Cr`} tick={{ fontSize: 10 }} /><Tooltip formatter={(v: number) => money(v)} /><Bar dataKey="value">{waterfall.map(item => <Cell key={item.name} fill={item.fill} />)}</Bar></BarChart></ResponsiveContainer></Panel>
      </div></div>
    <Panel title={t('sensitivityTornado')} subtitle={t('sensitivityDesc')}><div className="tornado">{sensitivity.map(item => <div className="tornado-row" key={item.factor}><span>{item.factor}</span><div className="tornado-track"><i className={item.margin_pct < result.developer_margin_pct ? 'negative' : ''} style={{ width: `${Math.min(100, Math.abs(item.margin_pct))}%` }} /></div><b>{item.margin_pct.toFixed(1)}%</b></div>)}</div></Panel>
    <Panel title={t('householdAffordability')} subtitle={t('affordabilityDesc')} className="affordability-panel"><div className="form-grid household-controls"><label className="field"><span>{t('householdIncome')}</span><input type="number" min={0} max={1000000} step={100} value={income} onChange={e => setIncome(Math.max(0, Number(e.target.value)))} /></label><label className="field"><span>{t('burdenThreshold')}</span><input type="number" min={1} max={100} value={threshold} onChange={e => setThreshold(Math.max(1, Math.min(100, Number(e.target.value))))} /></label></div>
      <div className="affordability-grid">{options.map((option, index) => { const cost = householdCosts(option, income, threshold); return <article className="household-card" key={option.id}><div className="service-card-title"><h3>{t(option.id)}</h3><Badge tone={cost.exceeds_planning_limit ? 'red' : 'teal'}>{cost.burden_pct === null ? '—' : `${cost.burden_pct.toFixed(1)}%`}</Badge></div><strong className="service-reading">{money(cost.monthly_burden_inr)}<small>{t('monthlyBurden')}</small></strong><div className="record-facts"><div><span>{t('remainingIncome')}</span><b>{money(cost.remaining_income_inr)}</b></div><div><span>{t('transitionCost')}</span><b>{money(cost.transition_cost_inr)}</b></div></div><details><summary>{t('editable')}</summary><div className="form-grid">{householdFields.map(([field, label, max]) => <label className="field" key={field}><span>{t(label)}</span><input type="number" min={0} max={max} step={field === 'temporary_months' ? 1 : 100} value={option[field]} onChange={e => { const value = Math.max(0, Math.min(max, Number(e.target.value))); setOptions(old => old.map((o, i) => i === index ? { ...o, [field]: value } : o)) }} /></label>)}</div></details></article> })}</div><Note>{t('affordabilityLimit')}</Note>
    </Panel>
  </div>
}
