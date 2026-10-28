import { useEffect, useState } from 'react'
import { referenceBoundaries } from './historicalBoundaries'
import type { ReferenceBoundaries } from './historicalBoundaries'

export function useReferenceBoundaries() {
  const [data,setData] = useState<ReferenceBoundaries | null>(null), [error,setError] = useState(''), [loading,setLoading] = useState(true), [attempt,setAttempt] = useState(0)
  useEffect(() => {
    let active = true; setLoading(true); setError('')
    referenceBoundaries().then(value => { if (active) setData(value) }).catch(problem => { if (active) setError(problem.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [attempt])
  return {data,error,loading,retry:()=>setAttempt(value=>value+1)}
}
