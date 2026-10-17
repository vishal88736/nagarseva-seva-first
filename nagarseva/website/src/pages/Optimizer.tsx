import { Download, Target, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Badge, Metric, Note, Panel, PocketMap, SectionTitle } from '../components/Shared'
import { ErrorNote } from '../components/Records'
import { useI18n } from '../i18n'
import { downloadCsv, money, number, optimise, Optimisation, Pocket } from '../lib/api'

export function Optimizer({ pockets, onSelect }: { pockets: Pocket[]; onSelect: (id: string) => void }) {
  const { t } = useI18n()
  const [budget, setBudget] = useState(100000000), [vulnerable, setVulnerable] = useState(.3), [wards, setWards] = useState(3)
  const [result, setResult] = useState<Optimisation | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  useEffect(() => {
    let current = true
    setBusy(true); setResult(null); setError('')
    const timer = window.setTimeout(() => { optimise(budget, vulnerable, wards).then(value => { if (current) setResult(value) }).catch(e => { if (current) setError(e.message) }).finally(() => { if (current) setBusy(false) }) }, 450)
    return () => { current = false; window.clearTimeout(timer) }
  }, [budget, vulnerable, wards])
  const selected = result ? pockets.filter(p => result.selected.some(x => x.pocket_id === p.pocket_id)) : []
  return <div className="page-pad"><SectionTitle eyebrow={t('capitalAllocation')} title={t('optimizerTitle')} description={t('optimizerDesc')} action={result?.status === 'feasible' ? <Badge>{t('constraintsVerified')}</Badge> : undefined} /><ErrorNote message={error} />
    <Panel title={t('setConstraints')} subtitle={t('updatesLevers')}><div className="constraint-row"><label><span>{t('availableBudget')}</span><b>{money(budget)}</b><input aria-label={t('availableBudget')} type="range" min={25000000} max={500000000} step={5000000} value={budget} onChange={e => setBudget(Number(e.target.value))} /></label><label><span>{t('minimumVulnerable')}</span><b>{Math.round(vulnerable * 100)}%</b><input aria-label={t('minimumVulnerable')} type="range" min={0} max={1} step={.05} value={vulnerable} onChange={e => setVulnerable(Number(e.target.value))} /></label><label><span>{t('wardsRepresented')}</span><b>{wards}</b><input aria-label={t('wardsRepresented')} type="range" min={1} max={12} step={1} value={wards} onChange={e => setWards(Number(e.target.value))} /></label></div></Panel>
    {busy && <div className="empty-state" role="status">{t('loading')}</div>}
    {result && result.status !== 'feasible' && <div className="error-note" role="status"><b>{t('planUnavailable')}</b><p>{result.message}</p></div>}
    {result && <><div className="admin-metrics"><Metric label={t('peopleServed')} value={number(result.impact_people)} note={t('impactProxy')} icon={<Users size={18} />} /><Metric label={t('budgetUsed')} value={money(result.spent_inr)} /><Metric label={t('vulnerableShare')} value={`${Math.round(result.vulnerable_share * 100)}%`} icon={<Target size={18} />} /><Metric label={t('wardCoverage')} value={number(result.ward_coverage)} /></div>
      {!result.optimal && result.status === 'feasible' && <Note>{t('solverLimit')}</Note>}
      <div className="optimizer-grid"><Panel title={t('selectedPockets')} subtitle={`${result.selected.length} · ${result.solver}`} action={<button className="button outline" disabled={!result.selected.length} onClick={() => downloadCsv('nagarseva-allocation.csv', result.selected)}><Download size={15} />{t('exportCsv')}</button>}><div className="selection-map"><PocketMap pockets={selected} small onSelect={onSelect} /></div><div className="selected-list">{result.selected.map(item => <button className="selected-project" key={item.pocket_id} onClick={() => onSelect(item.pocket_id)}><b>{item.pocket_id}</b><span>{item.city} / {item.ward}</span><strong>{money(item.cost_inr)}</strong></button>)}</div></Panel>
        <Panel title={t('frontierLabel')} subtitle={t('impactProxy')}><ResponsiveContainer width="100%" height={250}><AreaChart data={result.pareto}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="budget_inr" tickFormatter={v => money(v)} tick={{ fontSize: 10 }} /><YAxis tickFormatter={v => number(v)} tick={{ fontSize: 10 }} /><Tooltip formatter={(v: number) => number(v)} /><Area type="linear" dataKey="impact_people" connectNulls={false} stroke="#159d9a" fill="#bce5df" /></AreaChart></ResponsiveContainer><div className="compare-plan"><div><span><b>{t('aiPlan')}</b><small>{result.status}</small></span><strong>{result.status === 'feasible' ? number(result.impact_people) : '—'}</strong></div><div><span><b>{t('uniformPlan')}</b><small>{result.baseline.status}</small></span><strong>{result.baseline.status === 'feasible' ? number(result.baseline.impact_people) : '—'}</strong></div></div><Note>{t('comparisonMethod')}</Note>{result.baseline.status !== 'feasible' && <p>{result.baseline.message}</p>}</Panel>
      </div></>}
  </div>
}
