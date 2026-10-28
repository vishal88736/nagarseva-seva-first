import { useState } from 'react'
import { useLanguage } from './i18n/LanguageProvider'
import { t } from './i18n/locale'
import UrbanSaarthi from './urban/UrbanSaarthi'
import PublicWorkspace from './urban/PublicWorkspace'

export default function App() {
  useLanguage()
  const [scope, setScope] = useState<'real' | 'demo'>('real')
  return scope === 'real' ? <PublicWorkspace onDemo={() => setScope('demo')} /> : <><div className="public-demo-return"><b>{t('Synthetic sandbox · all planning fixtures are invented')}</b><button className="us-button" onClick={() => setScope('real')}>{t('Return to workspace')}</button></div><UrbanSaarthi /></>
}
