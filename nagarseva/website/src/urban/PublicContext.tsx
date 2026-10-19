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
  return <Panel title="Historical Census context" note="Published aggregates keep their original geography and 2011 reference year. These are not current settlement measurements.">
    {error ? <div className="us-alert" role="alert">{error}<button className="us-button" onClick={() => setAttempt(n => n + 1)}>Retry historical data</button></div>
      : !context ? <p role="status">Loading historical table observations…</p>
        : !context.observations.length ? <p className="us-empty">No numerical historical tables loaded. Missing observations are not zero.</p>
          : <>
            <div className="us-toolbar"><Field label="Original Census geography"><select aria-label="Original Census geography" value={selected} onChange={event => setSelected(event.target.value)}>{context.geographic_units.map(row => <option key={row.id} value={row.id}>{row.name} · {row.resolution} · {row.reference_year}</option>)}</select></Field><button className="us-button" onClick={() => exportPublicCsv('historical', '').catch(e => setError(e.message))}>Historical observations CSV</button></div>
            {unit && <><Tag tone="amber">Historical · {unit.reference_year} · {unit.resolution}</Tag><p><b>{unit.name}</b> · original source code {unit.source_id}. Source labels including “(Part)” are retained. No current boundary equivalence is assumed.</p></>}
            <div className="us-table-wrap"><table><thead><tr><th>Published measure / category</th><th>Value</th><th>Original source and universe</th></tr></thead><tbody>{observations.map(row => <tr key={row.id}><td>{row.source_label || row.indicator_type}<small>{row.source_field || row.indicator_type}</small></td><td>{row.value === null ? 'Missing in source' : row.value.toLocaleString('en-IN')}<small>{row.unit} · {row.reference_year}</small></td><td><a href={row.source} target="_blank" rel="noreferrer">Original Census table</a><small>{row.universe || 'See source table definition'}</small>{(row.denominator ?? row.denominator_households) !== undefined && <small>Source denominator: {(row.denominator ?? row.denominator_households)?.toLocaleString('en-IN')} households</small>}</td></tr>)}</tbody></table></div>
            <p>{context.limitations} PCA and Houselisting table universes differ; their household denominators cannot be interchanged.</p>
          </>}
  </Panel>
}
