// US SR portal — Auto Dialer tab. Same shared screen as Canada, bound to the
// us_leads market (additive: no Canada file depends on this page).
import { AutoDialerScreen } from '@/components/dialer/AutoDialerScreen'

export default function USPortalAutoDialerPage() {
  return <AutoDialerScreen market="us" />
}
