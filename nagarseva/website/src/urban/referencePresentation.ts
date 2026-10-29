import { t, formatNumber } from '../i18n/locale'
import type { ReferenceProperties } from './historicalBoundaries'

export const HISTORICAL_NOTICE = 'Historical reference boundaries — 2015. Not verified against the 2024 SRA cluster list.'
export const referenceLabel = (number: number) => t('civic.referenceLabel', { number: formatNumber(number, 0, 3) })
export const availableProperties = (properties: ReferenceProperties) => Object.entries(properties).filter(([,value]) => value !== null && value !== undefined && value !== '')
