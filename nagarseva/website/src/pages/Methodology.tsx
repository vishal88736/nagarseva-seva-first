import { BookOpen, CheckCircle2, Database, Fingerprint, GitBranch, Scale, ShieldCheck, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Badge, Note, Panel, SectionTitle } from '../components/Shared'
import { useI18n } from '../i18n'
import { getModelCards, ModelCards } from '../lib/api'

export function Methodology() {
  const { t } = useI18n()
  const [models, setModels] = useState<ModelCards | null>(null)
  useEffect(() => { let active = true; getModelCards().then(value => { if (active) setModels(value) }).catch(() => { if (active) setModels(null) }); return () => { active = false } }, [])
  const value = (name: string, field: string) => { const number = models?.cards[name]?.metrics[field]; return typeof number === 'number' ? number.toFixed(3) : '—' }
  const cards = [
    ['priority', t('priorityScore'), t('methodPriorityNote'), `R² ${value('priority', 'r2')} · MAE ${value('priority', 'mae')} · rank correlation ${value('priority', 'rank_correlation')}`],
    ['intervention', t('interventionModel'), t('interventionModelDesc'), `Macro-F1 ${value('intervention', 'intervention_macro_f1')}`],
    ['service', t('serviceGapModel'), t('methodServiceNote'), t('datedMeasurements')],
    ['grievance', t('grievanceNlp'), t('methodNlpNote'), `Macro-F1 ${value('grievance', 'macro_f1')} · ${t('syntheticHoldout')}`],
    ['cost', t('costBenchmark'), t('costBenchmarkDesc'), `R² ${value('cost', 'cost_r2')} · MAE ₹${value('cost', 'cost_mae')}/sq ft · ${t('delayBenchmark')} ${value('cost', 'delay_mae_months')}`],
  ]
  return <div className="page-pad"><SectionTitle eyebrow={t('methodologyEyebrow')} title={t('methodologyTitle')} description={t('methodologyDesc')} action={<Badge><BookOpen size={14} /> {t('modelCards')}</Badge>} /><div className="method-hero"><div><h2>{t('aiDecides')}</h2><p>{t('methodologyHero')}</p></div><div className="method-icons"><div><Users /><span>{t('residentVoice')}</span></div><div><Scale /><span>{t('fairnessChecks')}</span></div><div><ShieldCheck /><span>{t('dataMin')}</span></div></div></div><div className="method-grid"><Panel title={t('modelCards')} subtitle={t('syntheticHoldout')}><div className="model-card-list">{cards.map(([id, name, method, metric]) => <div key={id}><div className="model-card-icon"><GitBranch size={17} /></div><div><b>{name}</b><span>{method}</span><small>{metric}</small>{models?.cards[id]?.source && <small>{t('source')}: {models.cards[id].source}</small>}</div>{(id === 'service' || models?.cards[id]?.loaded) && <CheckCircle2 size={16} />}</div>)}</div></Panel><Panel title={t('fairnessLimitations')}><div className="limitations"><div><Scale size={16} /><p><b>{t('wardSplit')}</b> {t('wardSplitDesc')}</p></div><div><Database size={16} /><p><b>{t('syntheticCalibration')}</b> {t('syntheticCalibrationDesc')}</p></div><div><Fingerprint size={16} /><p><b>{t('privacyApproach')}</b> {t('privacyDesc')}</p></div></div></Panel></div><Panel title={t('policyBridge')} subtitle={t('policyBridgeDesc')}><div className="policy-chips"><span>PMAY-U 2.0</span><span>Maharashtra SRA</span><span>SBM-Urban</span><span>AMRUT</span><span>SDG 6</span><span>SDG 11</span></div><Note>{t('realDataPlug')}</Note></Panel></div>
}
