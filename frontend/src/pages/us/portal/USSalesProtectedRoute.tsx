import { useState, useEffect } from 'react'
import { Navigate, useLocation, Link } from 'react-router-dom'
import { useSalesAuth } from '@/lib/sales-auth'
import { MeridianEmblem } from '@/components/MeridianLogo'
import { ShieldX } from 'lucide-react'
import { isUsAdmin } from '@/lib/us-admins'

export default function USSalesProtectedRoute({ children }: { children: React.ReactNode }) {
  const { ready, authenticated, rep } = useSalesAuth()
  const location = useLocation()

  const [showRetry, setShowRetry] = useState(false)

  useEffect(() => {
    if (!ready) {
      const timer = setTimeout(() => setShowRetry(true), 4000)
      return () => clearTimeout(timer)
    } else {
      setShowRetry(false)
    }
  }, [ready])

  if (!ready) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center gap-4">
        <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#17C5B0] font-bold text-sm">S</span>
        </div>
        {showRetry && (
          <div className="text-center">
            <p className="text-[#A1A1A8] text-xs mb-2">Taking longer than expected...</p>
            <button
              onClick={() => window.location.href = '/us/portal/login'}
              className="text-[#17C5B0] text-xs font-medium hover:text-[#17C5B0]/80 underline underline-offset-2 transition-colors"
            >
              Go to login
            </button>
          </div>
        )}
      </div>
    )
  }

  if (!authenticated) {
    return <Navigate to="/us/portal/login" state={{ from: location.pathname }} replace />
  }

  if (rep && rep.portal_context === 'canada') {
    if (!isUsAdmin(rep.email)) return <AccessDenied />
  }

  return <>{children}</>
}

function AccessDenied() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">
        <div className="flex flex-col items-center gap-1 mb-6">
          <MeridianEmblem size={36} />
          <span className="text-lg font-bold text-[#F5F5F7] mt-2">Meridian Sales</span>
          <span className="text-[10px] font-semibold text-[#17C5B0] uppercase tracking-widest flex items-center gap-1">
            US CRM {'\u{1F1FA}\u{1F1F8}'}
          </span>
        </div>

        <div className="card p-6 sm:p-8 border border-red-500/20">
          <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
            <ShieldX size={24} className="text-red-400" />
          </div>

          <h2 className="text-lg font-bold text-[#F5F5F7] mb-2">Access Denied</h2>
          <p className="text-sm text-[#A1A1A8] mb-6">
            This portal is for Meridian sales reps only. If you're a business owner, please use the customer dashboard.
          </p>

          <div className="space-y-2">
            <Link
              to="/canada/portal/dashboard"
              className="block w-full py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all text-center"
            >
              Go to Canada Portal
            </Link>
            <Link
              to="/"
              className="block w-full py-2.5 bg-[#1F1F23] text-white text-sm font-medium rounded-lg hover:bg-[#2A2A2E] transition-all text-center"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
