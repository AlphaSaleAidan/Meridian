import { DemoContextProvider } from '@/lib/demo-context'
import SEO from './SEO'
import MerchantLayout from './MerchantLayout'

/**
 * Public demo wrapper for the Canada merchant portal. Renders the trimmed
 * merchant UI (same layout + pillars as /canada/merchant) under /canada/demo
 * with no auth gate. Demo mode is path-driven (useOrgId → 'demo'), so all
 * pages self-serve synthetic CAD data. No WalkthroughEngine, so there is no
 * "Take a Tour" banner here.
 */
export default function MerchantDemoLayout() {
  return (
    <DemoContextProvider>
      <SEO
        title="Meridian Intelligence — Interactive Demo"
        description="Explore Meridian's AI-powered POS intelligence with live demo data. Recoverable revenue, inventory, scheduling and phone-call insights in action."
        path="/canada/demo"
        noindex
      />
      <MerchantLayout />
    </DemoContextProvider>
  )
}
