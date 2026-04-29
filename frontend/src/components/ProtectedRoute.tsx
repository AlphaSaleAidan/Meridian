import { Navigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { useSalesAuth } from '@/lib/sales-auth'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import { ShieldX } from 'lucide-react'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { ready, authenticated, org, isSalesRep } = useAuth()
  const salesAuth = useSalesAuth()
  const location = useLocation()

  if (!ready) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
        <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/15 border border-[#1A8FD6]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#1A8FD6] font-bold text-sm">M</span>
        </div>
      </div>
    )
  }

  if (salesAuth.authenticated && !org) {
    return <AccessDenied type="sales-rep" />
  }

  if (isSalesRep && !org) {
    return <AccessDenied type="sales-rep" />
  }

  if (!authenticated) {
    return <Navigate to="/customer/login" state={{ from: location.pathname }} replace />
  }

  return <>{children}</>
}

function AccessDenied({ type }: { type: 'sales-rep' }) {
  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">
        <div className="flex items-center justify-center gap-2.5 mb-6">
          <MeridianEmblem size={36} />
          <MeridianWordmark className="text-xl" />
        </div>

        <div className="card p-6 sm:p-8 border border-red-500/20">
          <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
            <ShieldX size={24} className="text-red-400" />
          </div>

          <h2 className="text-lg font-bold text-[#F5F5F7] mb-2">Access Denied</h2>
          <p className="text-sm text-[#A1A1A8] mb-6">
            This portal is for Meridian business owners only. Your account is registered as a sales rep.
          </p>

          <div className="space-y-2">
            <Link
              to="/login"
              className="block w-full py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all text-center"
            >
              Go to Sales Portal
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
