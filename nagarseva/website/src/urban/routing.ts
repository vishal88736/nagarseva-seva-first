export const MAIN_ROUTES = [
  { id: 'dashboard', path: '/dashboard', label: 'nav.dashboard' },
  { id: 'settlements', path: '/settlements', label: 'nav.settlements' },
  { id: 'report-issue', path: '/report-issue', label: 'nav.issue' },
  { id: 'projects', path: '/projects', label: 'nav.projects' },
] as const
export type MainPage = typeof MAIN_ROUTES[number]['id']
export type Page = MainPage | 'data' | 'prioritize' | 'compare' | 'assurance'
const LEGACY: Record<string, Page> = { overview: 'dashboard', explore: 'settlements', prioritize: 'prioritize', compare: 'compare', assurance: 'assurance', data: 'data' }
export const PATHS: Record<Page, string> = { dashboard: '/dashboard', settlements: '/settlements', 'report-issue': '/report-issue', projects: '/projects', data: '/projects/data', prioritize: '/projects/priorities', compare: '/projects/scenarios', assurance: '/projects/assurance' }
export function routePage(pathname: string, hash = ''): Page {
  const legacy = LEGACY[hash.replace(/^#/, '')]
  return legacy || (Object.keys(PATHS) as Page[]).find(key => PATHS[key] === pathname.replace(/\/$/, '')) || 'dashboard'
}
export function activeSection(page: Page): MainPage { return ['data','prioritize','compare','assurance'].includes(page) ? 'projects' : page as MainPage }
