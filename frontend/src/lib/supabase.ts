import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

// Custom no-op lock to prevent Web Lock API orphan issues in automated/multi-tab environments.
// The gotrue lock can get stuck when tabs navigate away mid-lock, causing blank screens.
const noLock = (_name: string, _acquireTimeout: number, fn: () => Promise<unknown>) => fn()

export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey, {
          auth: {
                    lock: noLock,
          },
  })
    : null
