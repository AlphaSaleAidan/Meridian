import { DemoContextProvider } from '@/lib/demo-context'
import MerchantLayout from './MerchantLayout'
import BusinessTypeSelector from './BusinessTypeSelector'
import DemoHeaderBadge from './DemoHeaderBadge'
import WalkthroughEngine from './demo/WalkthroughEngine'
import SEO from './SEO'

/**
 * Canada interactive demo — the new 3-pillar merchant portal, unauthenticated.
 *
 * Mounts MerchantLayout under /canada/demo so the demo renders the exact same
 * chrome and pages as the live /canada/merchant portal (path-based demo mode in
 * useOrg makes the pages fetch the 'demo' org with no login). Demo chrome
 * (business selector, CAD badge, tour) layers on top via DemoContextProvider.
 */
export default function MerchantDemoLayout() {
  return (
    <DemoContextProvider>
      <SEO
        title="Meridian Intelligence — Interactive Demo (Canada)"
        description="Explore the Meridian merchant portal with live demo data in Canadian dollars."
        path="/canada/demo"
        noindex
      />
      {/* First-visit vertical picker + persistent "Switch" badge so viewers can
          choose / change which business type the demo renders (data refetches
          automatically — useApi keys on businessType). */}
      <BusinessTypeSelector />
      <DemoHeaderBadge />
      <WalkthroughEngine />
      <MerchantLayout basePath="/canada/demo" />
    </DemoContextProvider>
  )
}
