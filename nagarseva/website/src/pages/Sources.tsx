import { Download, ExternalLink } from 'lucide-react'
import { Badge, Panel, SectionTitle } from '../components/Shared'
import { BenchmarkReferences, ForecastCard } from '../components/PublicContext'
import { useI18n } from '../i18n'
import { downloadJson, Pocket } from '../lib/api'
import { publicSources } from '../lib/publicSources'

export function Sources({ pocket }: { pocket: Pocket | null }) {
  const { t } = useI18n()
  return <div className="page-pad"><SectionTitle eyebrow={t('sourceLibrary')} title={t('sourcesTitle')} description={t('sourcesDesc')} action={<button className="button outline" onClick={() => downloadJson('NagarSeva-public-sources.json', publicSources)}><Download size={14} />{t('exportEvidence')}</button>} />
    <p className="muted">{t('sourceReviewed')}: {publicSources.reviewed_at}</p>
    {pocket ? <ForecastCard key={pocket.pocket_id} pocket={pocket} /> : <p role="status">{t('loading')}</p>}
    <BenchmarkReferences />
    <Panel title={t('sourceLibrary')}><div className="source-library-grid">{publicSources.sources.map(source => <article className="source-entry" key={source.id}>
      <Badge tone={source.reuse === 'permission_required' ? 'amber' : 'teal'}>{t(source.reuse === 'permission_required' ? 'sourcePermission' : 'sourceReference')}</Badge>
      <h3>{t(`source_${source.id}_title`)}</h3><p>{t(`source_${source.id}_desc`)}</p><small>{source.publisher}</small>
      <dl><div><dt>{t('sourceScope')}</dt><dd>{source.scope}</dd></div><div><dt>{t('sourcePeriod')}</dt><dd>{source.data_period}</dd></div></dl>
      {source.availability === 'publisher_unreachable' && <p className="source-availability">{t('sourceLimited')}</p>}
      <div className="source-actions"><a href={source.url} target="_blank" rel="noopener noreferrer">{t('sourceOpen')} <ExternalLink size={13} /></a><a href={source.terms_url} target="_blank" rel="noopener noreferrer">{t('sourceTerms')} <ExternalLink size={13} /></a></div>
    </article>)}</div></Panel>
  </div>
}
