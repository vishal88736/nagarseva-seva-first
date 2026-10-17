import catalog from '../../../shared/public-sources.json'
export const publicSources = catalog
export const officialSource = (id: string) => catalog.sources.find(source => source.id === id)!
