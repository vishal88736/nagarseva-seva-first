import { useState } from 'react'
import { Download, Upload } from 'lucide-react'
import type { Metadata } from './publicClient'
import { dataApi, exportPublicCsv } from './publicClient'
import { Field, Heading, Panel } from './PlanningPages'
import PublicContext from './PublicContext'

type Preview = { dataset_id: string; title: string; settlements: number; polygons: number; projects: number; observations: number; context_features: number; warnings: string[]; expected_snapshot: string | null }

export default function WorkspaceData({ metadata, officerKey, onKey, onImported, onDemo }: { metadata: Metadata | null; officerKey: string; onKey: (key: string) => void; onImported: () => Promise<void>; onDemo: () => void }) {
  const [key, setKey] = useState(officerKey), [dataset, setDataset] = useState<Record<string, unknown> | null>(null), [filename, setFilename] = useState('')
  const [preview, setPreview] = useState<Preview | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState(''), [references, setReferences] = useState(false)
  async function read(file?: File) {
    setDataset(null); setPreview(null); setError(''); setMessage(''); setFilename(file?.name || '')
    if (!file) return
    try {
      if (file.size > 10 * 1024 * 1024) throw new Error('Choose a JSON or GeoJSON file up to 10 MiB.')
      const value = JSON.parse(await file.text())
      if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('The file must contain a JSON object.')
      setDataset(value)
    } catch (problem) { setError((problem as Error).message) }
  }
  async function submit(apply: boolean) {
    if (!dataset || busy) return
    setBusy(true); setError(''); setMessage('')
    try {
      if (apply) {
        if (!preview) return
        await dataApi('/workspace/import', { dataset, expected_snapshot: preview.expected_snapshot }, officerKey)
        await onImported(); setPreview(null); setMessage('Dataset imported. Open the settlement map to begin.')
      } else setPreview(await dataApi<Preview>('/workspace/preview', { dataset }, officerKey))
    } catch (problem) { setError((problem as Error).message); if (apply) setPreview(null) } finally { setBusy(false) }
  }
  function template() {
    const value = { title: 'My housing workspace', source: 'Replace with your data source', source_date: null,
      settlements: { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { id: '', name: '', administrative_area: '', households: null, source: '', source_date: null }, geometry: null }] }, observations: [], projects: [], spatial: { type: 'FeatureCollection', features: [] } }
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' })), link = document.createElement('a')
    link.href = url; link.download = 'urbansaarthi-workspace-template.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <>
    <Heading number="06" title="Data & access" description="Load your settlement data and configure access to operational records." />
    <div className="workspace-data-grid">
      <Panel title="Import your dataset" note="GeoJSON settlement boundaries, or a workspace JSON containing settlements, observations, projects and context layers.">
        <button className="us-button" onClick={template}><Download size={16} /> Download template</button>
        <Field label="Dataset file"><input aria-label="Dataset file" type="file" accept=".json,.geojson,application/json,application/geo+json" disabled={busy} onChange={event => read(event.target.files?.[0])} /></Field>
        <p className="us-small">Use stable settlement IDs to link observations and projects. Coordinates must be WGS84 longitude, latitude. Unknown values remain null.</p>
        {!officerKey && <p className="us-note">Connect officer access to validate and import a dataset.</p>}
        <button className="us-button primary" disabled={!dataset || !officerKey || busy} onClick={() => submit(false)}><Upload size={16} /> {busy ? 'Checking dataset…' : 'Validate file'}</button>
        {error && <p role="alert" className="us-alert">{error}</p>}
        {preview && <div className="workspace-import-preview"><h3>{preview.title}</h3><p>{filename}</p><dl className="us-facts"><div><dt>Settlements / boundaries</dt><dd>{preview.settlements} / {preview.polygons}</dd></div><div><dt>Observations</dt><dd>{preview.observations}</dd></div><div><dt>Projects / context objects</dt><dd>{preview.projects} / {preview.context_features}</dd></div></dl>{preview.warnings.map(w => <p key={w}>{w}</p>)}<p>Import replaces the active dataset. Existing intervention and inspection records are retained.</p><button className="us-button primary" disabled={busy} onClick={() => submit(true)}>Import validated dataset</button></div>}
        {message && <p className="us-success" role="status">{message}</p>}
      </Panel>
      <div>
        <Panel title="Officer access"><form onSubmit={event => { event.preventDefault(); onKey(key); setPreview(null) }}><Field label="Officer key"><input aria-label="Public data officer key" type="password" autoComplete="off" value={key} onChange={event => setKey(event.target.value)} /></Field><button className="us-button" type="submit">Apply officer key</button><p className="us-small">Required for imports, interventions, inspections and complaints. Stored for this browser session.</p></form></Panel>
        <Panel title="Active dataset"><h3>{metadata?.snapshot.title || 'No dataset loaded'}</h3><p>{metadata?.snapshot.source_label || metadata?.snapshot.geographic_scope}</p><dl className="us-facts"><div><dt>Source date</dt><dd>{metadata?.snapshot.settlement_reference || 'Not supplied'}</dd></div><div><dt>Loaded</dt><dd>{metadata?.snapshot.built_at?.slice(0, 10) || '—'}</dd></div></dl><button className="us-button" disabled={!metadata} onClick={() => exportPublicCsv('settlements', officerKey).catch(e => setError(e.message))}>Export settlements CSV</button></Panel>
      </div>
    </div>
    <details className="workspace-reference" onToggle={event => setReferences(event.currentTarget.open)}><summary>Reference data & demonstration</summary><p>Optional historical reference tables and the separate synthetic workspace.</p><button className="us-button" onClick={onDemo}>Open synthetic sandbox</button>{references && metadata?.snapshot.historical_observation_count ? <PublicContext /> : null}<a href="/evidence/" target="_blank" rel="noreferrer">Open research workbench</a></details>
  </>
}
