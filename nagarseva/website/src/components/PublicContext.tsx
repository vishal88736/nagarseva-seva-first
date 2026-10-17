import { useEffect, useState } from 'react'
import { CloudRain, Download, ExternalLink, RefreshCw } from 'lucide-react'
import { useI18n } from '../i18n'
import { dateTime, downloadJson, getWeather, Pocket, WeatherContext } from '../lib/api'
import { officialSource, publicSources } from '../lib/publicSources'
import { Badge, Note, Panel } from './Shared'

export function BenchmarkReferences() {
  const { t } = useI18n()
  const source = officialSource('slb')
  return <Panel title={t('officialBenchmarks')} subtitle={t('benchmarkContext')}>
    <div className="benchmark-reference-grid">{publicSources.benchmarks.map(benchmark => <article className="benchmark-reference" key={benchmark.id}>
      <span>{t(`benchmark_${benchmark.id}`)}</span><strong>{benchmark.value} <small>{benchmark.unit}</small></strong>
      <p>{t(benchmark.comparison === 'different_unit' ? 'benchmarkDifferentUnit' : 'benchmarkContinuity')}</p>
      <a href={source.url} target="_blank" rel="noopener noreferrer">CPHEEO · {benchmark.indicator} <ExternalLink size={13} /></a>
    </article>)}</div>
  </Panel>
}

export function OfficialChannels({ city }: { city: string }) {
  const { t } = useI18n()
  const ids = city === 'Mumbai' ? ['bmc', 'sra', 'pmay'] : ['pmay']
  return <Panel title={t('officialChannels')} subtitle={t('channelsDesc')}>
    <div className="official-channel-links">{ids.map(id => { const source = officialSource(id); return <a key={id} className="button outline" href={source.url} target="_blank" rel="noopener noreferrer">{t(`source_${id}_title`)} <ExternalLink size={14} /></a> })}</div>
  </Panel>
}

export function ForecastCard({ pocket }: { pocket: Pocket }) {
  const { t, language } = useI18n()
  const [weather, setWeather] = useState<WeatherContext | null>(null), [busy, setBusy] = useState(true), [failed, setFailed] = useState(false)
  useEffect(() => {
    let current = true
    getWeather(pocket.pocket_id).then(value => { if (current) setWeather(value) }).catch(() => { if (current) setFailed(true) }).finally(() => { if (current) setBusy(false) })
    return () => { current = false }
  }, [pocket.pocket_id])
  const reload = async () => { setBusy(true); setFailed(false); try { setWeather(await getWeather(pocket.pocket_id)) } catch { setFailed(true); setWeather(null) } finally { setBusy(false) } }
  const missing = failed || weather?.status === 'unavailable'
  const locale = language === 'hi' ? 'hi-IN' : language === 'mr' ? 'mr-IN' : 'en-IN'
  const value = (amount: number | null) => amount === null ? '—' : amount.toLocaleString(locale, { maximumFractionDigits: 1 })
  return <Panel title={t('weatherTitle')} subtitle={`${pocket.city} · ${pocket.pocket_id} · ${t('weatherDesc')}`} className="forecast-panel" action={<button className="button outline" onClick={() => { void reload() }} disabled={busy}><RefreshCw size={14} />{t('weatherReload')}</button>}>
    {busy && !weather && <p role="status">{t('loading')}</p>}
    {missing && <div className="note" role="status">{t('weatherUnavailable')}</div>}
    {weather?.status === 'disabled' && <Note>{t('weatherDisabled')}</Note>}
    {!!weather?.days.length && <>
      <div className="forecast-meta"><Badge tone={weather.status === 'stale' ? 'amber' : 'teal'}>{t(`weather_${weather.status}`)}</Badge><span>{t('weatherFetched')}: {dateTime(weather.fetched_at)}</span><span>{weather.timezone}</span></div>
      {weather.status === 'stale' && <Note>{t('weatherStale')}</Note>}
      <div className="forecast-grid">{weather.days.map(day => <article className="forecast-day" key={day.date}><b>{new Date(`${day.date}T12:00:00+05:30`).toLocaleDateString(locale, { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'Asia/Kolkata' })}</b><CloudRain size={22} /><dl>
        <div><dt>{t('weatherRain')}</dt><dd>{value(day.precipitation_mm)} mm</dd></div><div><dt>{t('weatherProbability')}</dt><dd>{value(day.precipitation_probability_pct)}%</dd></div><div><dt>{t('weatherTemperature')}</dt><dd>{value(day.max_temperature_c)} °C</dd></div>
      </dl></article>)}</div>
      <div className="forecast-coordinates"><span>{t('weatherArea')}: {weather.requested_coordinates?.lat.toFixed(1)}, {weather.requested_coordinates?.lon.toFixed(1)} (±0.05°)</span><span>{t('weatherGrid')}: {weather.grid_coordinates?.lat.toFixed(3)}, {weather.grid_coordinates?.lon.toFixed(3)}</span></div>
      <div className="source-actions"><a href={weather.source_url} target="_blank" rel="noopener noreferrer">{weather.provider} <ExternalLink size={13} /></a><a href={weather.licence_url} target="_blank" rel="noopener noreferrer">{weather.licence}</a><button className="text-button" onClick={() => downloadJson(`NagarSeva-weather-${pocket.pocket_id}.json`, weather)}><Download size={14} />{t('weatherExport')}</button></div>
      {weather.location_synthetic && <Note>{t('weatherScope')}</Note>}
    </>}
    <p className="muted source-context">{t('weatherLimits')}</p><a className="text-button" href={officialSource('imd').url} target="_blank" rel="noopener noreferrer">{t('source_imd_title')} <ExternalLink size={14} /></a>
  </Panel>
}
