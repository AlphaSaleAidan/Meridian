import { useState, useEffect, type ReactNode } from 'react'
import { getAuthHeaders } from '@/lib/supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface PendingDoc {
  document_type: string
  version: string
  content: string
}

interface ComplianceGateProps {
  userId: string
  userType?: string
  hasCamera?: boolean
  province?: string
  portalContext?: string
  children: ReactNode
}

export default function ComplianceGate({
  userId,
  userType = 'customer',
  hasCamera = false,
  province = '',
  portalContext = '',
  children,
}: ComplianceGateProps) {
  const [pending, setPending] = useState<PendingDoc[]>([])
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState(false)
  const [currentIdx, setCurrentIdx] = useState(0)

  useEffect(() => {
    if (!userId) {
      setLoading(false)
      return
    }

    const params = new URLSearchParams({
      user_type: userType,
      has_camera: String(hasCamera),
      province,
    })

    const fetchPending = async () => {
      try {
        const headers = await getAuthHeaders()
        const resp = await fetch(
          `${API_BASE}/api/compliance/pending/${userId}?${params}`,
          { headers }
        )
        if (resp.ok) {
          const data = await resp.json()
          setPending(data.pending || [])
        }
      } catch (err) {
        console.error('[ComplianceGate] Failed to fetch pending docs:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchPending()
  }, [userId, userType, hasCamera, province])

  const handleAccept = async () => {
    const doc = pending[currentIdx]
    if (!doc) return

    setAccepting(true)
    try {
      const headers = await getAuthHeaders()
      const resp = await fetch(`${API_BASE}/api/compliance/accept`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          user_type: userType,
          document_type: doc.document_type,
          document_version: doc.version,
          ip_address: '',
          user_agent: navigator.userAgent,
          portal_context: portalContext,
        }),
      })

      if (resp.ok) {
        if (currentIdx < pending.length - 1) {
          setCurrentIdx(currentIdx + 1)
        } else {
          setPending([])
        }
      }
    } catch (err) {
      console.error('[ComplianceGate] Failed to accept document:', err)
    } finally {
      setAccepting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
        <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/15 border border-[#1A8FD6]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#1A8FD6] font-bold text-sm">M</span>
        </div>
      </div>
    )
  }

  if (pending.length === 0) {
    return <>{children}</>
  }

  const doc = pending[currentIdx]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-2xl rounded-xl border border-zinc-700 bg-zinc-900 shadow-2xl">
        <div className="border-b border-zinc-700 px-6 py-4">
          <h2 className="text-lg font-semibold text-white">
            {doc.document_type.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
          </h2>
          <p className="mt-1 text-sm text-zinc-400">
            Version {doc.version} -- Please review and accept to continue.
            {pending.length > 1 && ` (${currentIdx + 1} of ${pending.length})`}
          </p>
        </div>

        <div className="max-h-[60vh] overflow-y-auto px-6 py-4">
          <div className="prose prose-invert prose-sm max-w-none text-zinc-300 whitespace-pre-wrap">
            {doc.content}
          </div>
        </div>

        <div className="border-t border-zinc-700 px-6 py-4 flex justify-end">
          <button
            onClick={handleAccept}
            disabled={accepting}
            className="rounded-lg bg-[#1A8FD6] px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#1A8FD6]/90 disabled:opacity-50"
          >
            {accepting ? 'Recording...' : 'I Accept'}
          </button>
        </div>
      </div>
    </div>
  )
}
