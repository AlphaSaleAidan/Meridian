import { useState, useEffect, useCallback, useRef } from 'react'
import { useDemoContext } from '@/lib/demo-context'

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

const RETRY_DELAYS = [1000, 3000]
const isRetryable = (err: any) => {
  const s = err?.status ?? err?.response?.status
  return !(s >= 400 && s < 500)
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: any[] = []
): UseApiState<T> & { refetch: () => void } {
  const { businessType } = useDemoContext()
  const [state, setState] = useState<UseApiState<T>>({
    data: null, loading: true, error: null,
  })
  const abortRef = useRef<AbortController | null>(null)

  const fetch = useCallback(async () => {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setState(prev => ({ ...prev, loading: true, error: null }))

    for (let attempt = 0; attempt <= RETRY_DELAYS.length; attempt++) {
      try {
        const data = await fetcher()
        if (ac.signal.aborted) return
        setState({ data, loading: false, error: null })
        return
      } catch (err: any) {
        if (ac.signal.aborted) return
        const canRetry = attempt < RETRY_DELAYS.length && isRetryable(err)
        if (!canRetry) {
          // Keep the last successful data so a failed refetch surfaces the
          // error without blanking an already-populated page. Initial load
          // (prev.data === null) is unchanged.
          setState(prev => ({ data: prev.data, loading: false, error: err.message || 'Unknown error' }))
          return
        }
        await new Promise<void>(r => {
          const t = setTimeout(r, RETRY_DELAYS[attempt])
          ac.signal.addEventListener('abort', () => { clearTimeout(t); r() })
        })
        if (ac.signal.aborted) return
      }
    }
  }, [...deps, businessType]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetch()
    return () => { abortRef.current?.abort() }
  }, [fetch])

  return { ...state, refetch: fetch }
}
