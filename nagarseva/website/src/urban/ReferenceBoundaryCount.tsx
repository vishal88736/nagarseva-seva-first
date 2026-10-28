import { t, formatNumber } from '../i18n/locale'
import { useReferenceBoundaries } from './useReferenceBoundaries'

/** Count the validated local reference layer, independently of register joins. */
export default function ReferenceBoundaryCount() {
  const {data,error,loading}=useReferenceBoundaries()
  return <span role="status">{data?t('{valid} valid / {original} source polygons',{valid:formatNumber(data.geometry.features.length,0),original:formatNumber(data.metadata.source_feature_count,0)}):loading?t('Loading…'):error?t('Unavailable'):t('No reference boundaries available.')}</span>
}
