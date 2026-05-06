import { DemoContextProvider } from '@/lib/demo-context'
import Layout from './Layout'
import BusinessTypeSelector from './BusinessTypeSelector'
import DemoHeaderBadge from './DemoHeaderBadge'

export default function DemoLayout() {
  return (
    <DemoContextProvider>
      <BusinessTypeSelector />
      <DemoHeaderBadge />
      <Layout />
    </DemoContextProvider>
  )
}
