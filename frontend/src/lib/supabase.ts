import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

// Custom no-op lock to prevent Web Lock API orphan issues in automated/multi-tab environments.
// The gotrue lock can get stuck when tabs navigate away mid-lock, causing blank screens.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const noLock = <R>(_name: string, _acquireTimeout: number, fn: () => Promise<R>): Promise<R> => fn()

export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey, {
          auth: {
                    lock: noLock,
          },
  })
    : null
