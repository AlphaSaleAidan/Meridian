import { Link } from 'react-router-dom'
import { Lock } from 'lucide-react'
import { useIsCommandTier, useIsDemo } from '@/hooks/useOrg'

/**
 * Client-side gate for Command-tier surfaces (the Multi-Location Hub).
 *
 * This is UX only — it hides the surface for non-Command orgs. The REAL control
 * is server-side: every /api/hub/* endpoint re-checks the org's Command tier and
 * returns 403 regardless of what the UI shows
 * (docs/multi-location-hub-journey.md §7.3). Demo mode is treated as Command so
 * the feature is showcatable.
 */
export default function CommandTierGate({ children }: { children: React.ReactNode }) {
  const isCommand = useIsCommandTier()
  const isDemo = useIsDemo()

  if (isCommand || isDemo) return <>{children}</>

  return (
    <div className="max-w-xl mx-auto mt-16 text-center card p-8">
      <div className="mx-auto w-12 h-12 rounded-full bg-[#1A8FD6]/10 flex items-center justify-center mb-4">
        <Lock className="w-6 h-6 text-[#1A8FD6]" />
      </div>
      <h2 className="text-xl font-bold text-[#F5F5F7] mb-2">Multi-Location Hub</h2>
      <p className="text-[#8E8E93] mb-6">
        The Multi-Location Hub — run every location from one command surface — is a
        Command-plan feature. Upgrade to connect and manage multiple locations
        under one login.
      </p>
      <Link to="/app/settings" className="btn-primary inline-block">
        View plans
      </Link>
    </div>
  )
}
