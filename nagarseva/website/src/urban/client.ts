import { useCallback, useEffect, useRef, useState } from 'react'
import fixture from '../../../shared/urban-demo.json'
import { actOnWork, emptyState, planWork, reportIssue, resolveIssue } from './engine'
import type { ActionInput, Dataset, Evidence, State, Work, WorkInput } from './engine'

const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const STORAGE_KEY = 'urbansaarthi-demo-v1'
export async function api<T>(path: string, body?: unknown, key = ''): Promise<T> {
  const controller = new AbortController(), timer = window.setTimeout(() => controller.abort(), 6000)
  try {
    const response = await fetch(`${BASE}/urban${path}`, { method: body === undefined ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json', 'X-Officer-Key': key }, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : Array.isArray(result.detail) ? result.detail.map((item: { msg: string }) => item.msg).join('; ') : `Request failed (${response.status}).`)
    return result as T
  } finally { window.clearTimeout(timer) }
}
function browserState(): State {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return emptyState()
    const data = JSON.parse(saved) as State
    if (![data.works, data.evidence, data.complaints].every(items => Array.isArray(items) && items.every(item => typeof item.id === 'string'))) throw new Error('Invalid saved sandbox.')
    return data
  } catch { return emptyState() }
}
export function useWorkspace() {
  const [data, setData] = useState(fixture as Dataset), [state, setState] = useState<State>(emptyState)
  const [mode, setMode] = useState<'connecting' | 'server' | 'browser'>('connecting')
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const [officerKey, setOfficerKey] = useState(() => { try { return sessionStorage.getItem('urbansaarthi-officer-key') || '' } catch { return '' } })
  const current = useRef(state), locked = useRef(false)
  const update = useCallback((next: State) => { current.current = next; setState(next) }, [])
  useEffect(() => {
    let active = true
    setMode('connecting'); setError(''); update(emptyState())
    api<Dataset>('/settlements').then(async result => {
      if (!active) return
      setData(result); setMode('server')
      try { const saved = await api<State>('/state', undefined, officerKey); if (active) { update(saved); setError('') } }
      catch (problem) { if (active) setError(`API connected; work records unavailable: ${(problem as Error).message}`) }
    }).catch(() => { if (active) { setMode('browser'); update(browserState()) } })
    return () => { active = false }
  }, [officerKey, update])
  function save(next: State) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)) }
    catch { throw new Error('Browser storage could not save this change. Export existing records, free storage or connect the API. This edit was not saved.') }
    update(next)
  }
  const mutate = async <T,>(operation: () => Promise<T>) => {
    if (locked.current) throw new Error('Wait for the current save to finish.')
    if (mode === 'connecting') throw new Error('Wait for the connection check to finish.')
    locked.current = true; setBusy(true); setError('')
    try { return await operation() }
    catch (problem) { const message = (problem as Error).message; setError(message); throw problem }
    finally { locked.current = false; setBusy(false) }
  }
  const refresh = async () => update(await api<State>('/state', undefined, officerKey))
  const createWork = (input: WorkInput) => mutate(async () => {
    if (!data.clusters.some(cluster => cluster.id === input.cluster_id)) throw new Error('Choose a cluster in this dataset.')
    if (mode === 'server') { const result = await api<Work>('/works', input, officerKey); await refresh(); return result.id }
    const next = planWork(current.current, input, new Date().toISOString()); save(next); return next.works[0].id
  })
  const workAction = (id: string, input: ActionInput) => mutate(async () => {
    if (mode === 'server') { await api(`/works/${encodeURIComponent(id)}/action`, input, officerKey); await refresh() }
    else save(actOnWork(current.current, id, input, new Date().toISOString()))
  })
  const addIssue = (id: string, description: string) => mutate(async () => {
    if (mode === 'server') { await api('/complaints', { work_id: id, text: description }, officerKey); await refresh() }
    else save(reportIssue(current.current, id, description, new Date().toISOString()))
  })
  const respond = (id: string, actor: string, notes: string) => mutate(async () => {
    if (mode === 'server') { await api(`/complaints/${encodeURIComponent(id)}/resolve`, { actor, notes }, officerKey); await refresh() }
    else save(resolveIssue(current.current, id, actor, notes, new Date().toISOString()))
  })
  const upload = (id: string, file: File, actor: string, notes: string) => mutate(async () => {
    if (!['image/png', 'image/jpeg', 'application/pdf', 'text/plain'].includes(file.type) || file.size === 0 || file.size > 2097152) throw new Error('Choose a nonempty PNG, JPEG, PDF or text file, at most 2 MiB.')
    if (actor.trim().length < 2 || notes.trim().length < 5) throw new Error('Supply an evidence submitter and a meaningful note.')
    const bytes = new Uint8Array(await file.arrayBuffer())
    const starts = (prefix: number[]) => prefix.every((value, i) => bytes[i] === value)
    if (file.type === 'image/png' && !starts([137,80,78,71,13,10,26,10]) || file.type === 'image/jpeg' && !starts([255,216,255]) || file.type === 'application/pdf' && !starts([37,80,68,70,45])) throw new Error('File signature does not match its declared type.')
    if (file.type === 'text/plain') { try { new TextDecoder('utf-8', { fatal: true }).decode(bytes) } catch { throw new Error('Text evidence must be UTF-8.') } }
    const encoded = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result).split(',')[1]); reader.onerror = () => reject(new Error('The file could not be read.')); reader.readAsDataURL(file) })
    const payload = { filename: file.name, content_type: file.type, content_base64: encoded, actor: actor.trim(), notes: notes.trim() }
    if (mode === 'server') { await api(`/works/${encodeURIComponent(id)}/evidence`, payload, officerKey); await refresh(); return }
    const next = structuredClone(current.current), work = next.works.find(work => work.id === id)
    if (!work) throw new Error('Work not found.')
    if (!crypto.subtle) throw new Error('File hashing requires localhost or HTTPS.')
    const hash = await crypto.subtle.digest('SHA-256', bytes)
    const at = new Date().toISOString()
    next.evidence.unshift({ ...payload, id: `EVI-${crypto.randomUUID().slice(0, 10).toUpperCase()}`, work_id: id, cluster_id: work.cluster_id, uploaded_at: at, bytes: bytes.length, sha256: [...new Uint8Array(hash)].map(value => value.toString(16).padStart(2, '0')).join(''), synthetic: true })
    work.history.push({ at, actor: payload.actor, action: 'evidence_attached', notes: payload.notes }); save(next)
  })
  const downloadEvidence = async (item: Evidence) => {
    let blob: Blob
    if (mode === 'server') {
      const response = await fetch(`${BASE}/urban/evidence/${encodeURIComponent(item.id)}/content`, { headers: { 'X-Officer-Key': officerKey } })
      if (!response.ok) throw new Error('The API could not authorize this file download.')
      blob = await response.blob()
    } else {
      if (!item.content_base64) throw new Error('File content is unavailable in this browser.')
      blob = new Blob([Uint8Array.from(atob(item.content_base64), ch => ch.charCodeAt(0))], { type: item.content_type })
    }
    const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = item.filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  function setKey(value: string) { try { sessionStorage.setItem('urbansaarthi-officer-key', value) } catch { /* A session key can remain in memory. */ } setOfficerKey(value) }
  return { data, state, mode, error, setError, busy, officerKey, setKey, createWork, workAction, addIssue, respond, upload, downloadEvidence }
}
export type Workspace = ReturnType<typeof useWorkspace>
export function downloadJson(filename: string, value: unknown) {
  const link = document.createElement('a'), url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }))
  link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
