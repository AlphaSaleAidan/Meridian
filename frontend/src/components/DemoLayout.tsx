import { DemoContextProvider } from '@/lib/demo-context'
import Layout from './Layout'
import BusinessTypeSelector from './BusinessTypeSelector'
import DemoHeaderBadge from './DemoHeaderBadge'
import WalkthroughEngine from './demo/WalkthroughEngine'
import SEO from './SEO'

export default function DemoLayout() {
  return (
    <DemoContextProvider>
      <SEO
        title="Meridian Intelligence — Interactive Demo"
        description="Explore Meridian's AI-powered POS analytics with live demo data. See revenue insights, anomaly detection, and forecasting in action."
        path="/demo"
        noindex
      />
      <BusinessTypeSelector />
      <DemoHeaderBadge />
      <WalkthroughEngine />
      <Layout />
    </DemoContextProvider>
  )
}
