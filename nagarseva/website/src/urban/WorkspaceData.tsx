import { FileInput } from '../i18n/LanguageProvider'
import { t, errorText, formatDate, formatNumber } from '../i18n/locale'
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
    const value = { title: t('My housing workspace'), source: t('Replace with your data source'), source_date: null,
      settlements: { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { id: '', name: '', administrative_area: '', households: null }, geometry: null }] }, observations: [], projects: [], spatial: { type: 'FeatureCollection', features: [] } }
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' })), link = document.createElement('a')
    link.href = url; link.download = 'urbansaarthi-workspace-template.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <>
    <Heading number="06" title={t("Data & access")} description={t("Load your settlement data and configure access to operational records.")} />
    <div className="workspace-data-grid">
      <Panel title={t("Import your dataset")} note={t("GeoJSON settlement boundaries, or a workspace JSON containing settlements, observations, projects and context layers.")}>
        <button className="us-button" onClick={template}><Download size={16} /> {t("Download template")}</button>
        <Field label={t("Dataset file")}><FileInput fileName={filename} aria-label={t("Dataset file")} accept=".json,.geojson,application/json,application/geo+json" disabled={busy} onChange={event => read(event.target.files?.[0])} /></Field>
        <p className="us-small">{t("Use stable settlement IDs to link observations and projects. Coordinates must be WGS84 longitude, latitude. Unknown values remain null.")}</p>
        {!officerKey && <p className="us-note">{t("Connect officer access to validate and import a dataset.")}</p>}
        <button className="us-button primary" disabled={!dataset || !officerKey || busy} onClick={() => submit(false)}><Upload size={16} /> {busy ? t("Checking dataset…") : t("Validate file")}</button>
        {error && <p role="alert" className="us-alert">{errorText(error)}</p>}
        {preview && <div className="workspace-import-preview"><h3>{preview.title}</h3><p>{filename}</p><dl className="us-facts"><div><dt>{t("Settlements / boundaries")}</dt><dd>{formatNumber(preview.settlements, 0)} / {formatNumber(preview.polygons, 0)}</dd></div><div><dt>{t("Observations")}</dt><dd>{formatNumber(preview.observations, 0)}</dd></div><div><dt>{t("Projects / context objects")}</dt><dd>{formatNumber(preview.projects, 0)} / {formatNumber(preview.context_features, 0)}</dd></div></dl>{preview.warnings.map(w => <p key={w}>{t(w)}</p>)}<p>{t("Import replaces the active dataset. Existing intervention and inspection records are retained.")}</p><button className="us-button primary" disabled={busy} onClick={() => submit(true)}>{t("Import validated dataset")}</button></div>}
        {message && <p className="us-success" role="status">{t(message)}</p>}
      </Panel>
      <div>
        <Panel title={t("Officer access")}><form onSubmit={event => { event.preventDefault(); onKey(key); setPreview(null) }}><Field label={t("Officer key")}><input aria-label={t("Public data officer key")} type="password" autoComplete="off" value={key} onChange={event => setKey(event.target.value)} /></Field><button className="us-button" type="submit">{t("Apply officer key")}</button><p className="us-small">{t("Required for imports, interventions, inspections and complaints. Stored for this browser session.")}</p></form></Panel>
        <Panel title={t("Active dataset")}><h3>{metadata?.snapshot.snapshot_sha256 ? metadata.snapshot.title : t("No dataset loaded")}</h3><p>{metadata?.snapshot.snapshot_sha256 ? metadata.snapshot.source_label || metadata.snapshot.geographic_scope : t("Import your data to begin.")}</p><dl className="us-facts"><div><dt>{t("Source date")}</dt><dd>{formatDate(metadata?.snapshot.settlement_reference)}</dd></div><div><dt>{t("Loaded")}</dt><dd>{metadata?.snapshot.snapshot_sha256 ? formatDate(metadata.snapshot.built_at) : '—'}</dd></div></dl><button className="us-button" disabled={!metadata} onClick={() => exportPublicCsv('settlements', officerKey).catch(e => setError(e.message))}>{t("Export settlements CSV")}</button></Panel>
      </div>
    </div>
    <details className="workspace-reference" onToggle={event => setReferences(event.currentTarget.open)}><summary>{t("Reference data & demonstration")}</summary><p>{t("Optional historical reference tables and the separate synthetic workspace.")}</p><button className="us-button" onClick={onDemo}>{t("Open synthetic sandbox")}</button>{references && metadata?.snapshot.historical_observation_count ? <PublicContext /> : null}<a href="/evidence/" target="_blank" rel="noreferrer">{t("Open research workbench")}</a></details>
  </>
}
