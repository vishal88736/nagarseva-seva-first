import { useState } from 'react'
import UrbanSaarthi from './urban/UrbanSaarthi'
import PublicWorkspace from './urban/PublicWorkspace'

export default function App() {
  const [scope, setScope] = useState<'real' | 'demo'>('real')
  return scope === 'real' ? <PublicWorkspace onDemo={() => setScope('demo')} /> : <><div className="public-demo-return"><b>Synthetic sandbox · all planning fixtures are invented</b><button className="us-button" onClick={() => setScope('real')}>Return to acquired public data</button></div><UrbanSaarthi /></>
}
