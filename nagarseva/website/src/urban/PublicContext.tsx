import { t, errorText, formatDate, formatNumber, statusText } from '../i18n/locale'
import { useEffect, useState } from 'react'
import { dataApi, exportPublicCsv } from './publicClient'
import { Field, Panel, Tag } from './PlanningPages'

type GeographicUnit = { id: string; source_id: string; name: string; resolution: string; reference_year: number; source: string }
type PublishedObservation = {
  id: string; geographic_unit_id: string; indicator_type: string; value: number | null;
  unit: string; reference_year: number; source: string; source_label?: string; source_field?: string;
  universe?: string; denominator?: number; denominator_households?: number; limitations?: string;
}
type Context = { geographic_units: GeographicUnit[]; observations: PublishedObservation[]; limitations: string }

export default function PublicContext() {
  const [context, setContext] = useState<Context | null>(null)
  const [selected, setSelected] = useState(''), [error, setError] = useState(''), [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setError('')
    dataApi<Context>('/context').then(result => {
      if (!active) return
      setContext(result)
      setSelected(result.geographic_units.find(unit => unit.name.includes('Greater Mumbai'))?.id || result.geographic_units[0]?.id || '')
    }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [attempt])
  const unit = context?.geographic_units.find(row => row.id === selected)
  const observations = context?.observations.filter(row => row.geographic_unit_id === selected) || []
  return <Panel title={t("Historical Census context")} note={t("Published aggregates keep their original geography and 2011 reference year. These are not current settlement measurements.")}>
    {error ? <div className="us-alert" role="alert">{errorText(error)}<button className="us-button" onClick={() => setAttempt(n => n + 1)}>{t("Retry historical data")}</button></div>
      : !context ? <p role="status">{t("Loading historical table observations…")}</p>
        : !context.observations.length ? <p className="us-empty">{t("No numerical historical tables loaded. Missing observations are not zero.")}</p>
          : <>
            <div className="us-toolbar"><Field label={t("Original Census geography")}><select aria-label={t("Original Census geography")} value={selected} onChange={event => setSelected(event.target.value)}>{context.geographic_units.map(row => <option key={row.id} value={row.id}>{row.name} · {statusText(row.resolution)} · {formatDate(String(row.reference_year))}</option>)}</select></Field><button className="us-button" onClick={() => exportPublicCsv('historical', '').catch(e => setError(e.message))}>{t("Historical observations CSV")}</button></div>
            {unit && <><Tag tone="amber">{t("Historical ·")} {formatDate(String(unit.reference_year))} · {statusText(unit.resolution)}</Tag><p><b>{unit.name}</b> {t("· original source code")} {unit.source_id}{t(". Source labels including “(Part)” are retained. No current boundary equivalence is assumed.")}</p></>}
            <div className="us-table-wrap"><table><thead><tr><th>{t("Published measure / category")}</th><th>{t("Value")}</th><th>{t("Original source and universe")}</th></tr></thead><tbody>{observations.map(row => <tr key={row.id}><td>{row.source_label || statusText(row.indicator_type)}<small>{row.source_field || row.indicator_type}</small></td><td>{row.value === null ? t("Missing in source") : formatNumber(row.value)}<small>{row.unit} · {formatDate(String(row.reference_year))}</small></td><td><a href={row.source} target="_blank" rel="noreferrer">{t("Original Census table")}</a><small>{row.universe || t("See source table definition")}</small>{(row.denominator ?? row.denominator_households) !== undefined && <small>{t("Source denominator:")} {(row.denominator ?? row.denominator_households) == null ? undefined : formatNumber((row.denominator ?? row.denominator_households))} {t("households")}</small>}</td></tr>)}</tbody></table></div>
            <p>{t(context.limitations)} {t("PCA and Houselisting table universes differ; their household denominators cannot be interchanged.")}</p>
          </>}
  </Panel>
}
