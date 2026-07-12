import { DemoContextProvider } from '@/lib/demo-context'
import MerchantLayout from './MerchantLayout'
import BusinessTypeSelector from './BusinessTypeSelector'
import DemoHeaderBadge from './DemoHeaderBadge'
import WalkthroughEngine from './demo/WalkthroughEngine'
import SEO from './SEO'

/**
 * US interactive demo — the 3-pillar merchant portal, unauthenticated.
 *
 * Mirror of MerchantDemoLayout (Canada): mounts MerchantLayout under /demo so
 * the demo renders the exact same chrome and pages as the live /us/merchant
 * portal (path-based demo mode in useOrg makes the pages fetch the 'demo' org
 * with no login). Demo chrome (business selector, badge, tour) layers on top
 * via DemoContextProvider. USD pricing comes from the path-based currency
 * multiplier (non-/canada paths resolve to 1.0).
 */
export default function USMerchantDemoLayout() {
  return (
    <DemoContextProvider>
      <SEO
        title="Meridian Intelligence — Interactive Demo"
        description="Explore the Meridian merchant portal with live demo data."
        path="/demo"
        noindex
      />
      <BusinessTypeSelector />
      <DemoHeaderBadge />
      <WalkthroughEngine />
      <MerchantLayout basePath="/demo" />
    </DemoContextProvider>
  )
}
