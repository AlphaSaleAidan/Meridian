import { DemoContextProvider } from '@/lib/demo-context'
import Layout from './Layout'
import BusinessTypeSelector from './BusinessTypeSelector'
import DemoHeaderBadge from './DemoHeaderBadge'
import WalkthroughEngine from './demo/WalkthroughEngine'

export default function DemoLayout() {
  return (
    <DemoContextProvider>
      <BusinessTypeSelector />
      <DemoHeaderBadge />
      <WalkthroughEngine />
      <Layout />
    </DemoContextProvider>
  )
}
