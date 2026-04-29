import { Navigate, useLocation, Link } from 'react-router-dom'
import { useSalesAuth } from '@/lib/sales-auth'
import { useAuth } from '@/lib/auth'
import { MeridianEmblem } from '@/components/MeridianLogo'
import { ShieldX } from 'lucide-react'

export default function SalesProtectedRoute({ children }: { children: React.ReactNode }) {
  const { ready, authenticated, rep } = useSalesAuth()
  const customerAuth = useAuth()
  const location = useLocation()

  if (!ready) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
        <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#17C5B0] font-bold text-sm">S</span>
        </div>
      </div>
    )
  }

  if (customerAuth.authenticated && customerAuth.org && !rep) {
    return <AccessDenied />
  }

  if (!authenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
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
          <span className="text-[10px] font-semibold text-[#17C5B0] uppercase tracking-widest">Internal CRM</span>
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
              to="/customer/login"
              className="block w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 transition-all text-center"
            >
              Go to Customer Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
