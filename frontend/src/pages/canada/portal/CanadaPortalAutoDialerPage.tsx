// Canada SR portal — Auto Dialer tab. All behavior lives in the shared
// AutoDialerScreen (components/dialer/); this page just binds the market.
import { AutoDialerScreen } from '@/components/dialer/AutoDialerScreen'

export default function CanadaPortalAutoDialerPage() {
  return <AutoDialerScreen market="canada" />
}
