/**
 * The trade workspace, mounted as the portal's home.
 *
 * "Overview" used to be the first item in a list of pillars, which made the
 * most important surface in the product look like a tab. It is now the app:
 * the trade's money at a size nothing competes with, the day in the form that
 * trade actually works in, and the things that need a human beside it.
 *
 * DEMO SURFACE ONLY, for now. MerchantPillarPage mounts this in place of
 * MerchantHomePage on /demo and /canada/demo. A paying merchant still gets
 * the home page they had this morning, because their portal is not the place
 * to find out whether a new layout holds.
 */
import { useOrgId } from '@/hooks/useOrg'
import { useTradePack } from '@/config/moduleFlags'
import { getActiveBusinessType } from '@/lib/demo-context'
import { getBusinessName } from '@/lib/business-config'
import { BASE_LOCATION } from '@/lib/demo-bookings'
import TradeWorkspaceHost from '@/components/overview/TradeWorkspaceHost'

export default function TradeHomePage() {
  const merchantId = useOrgId()
  const pack = useTradePack()

  return (
    <TradeWorkspaceHost
      // Remount on a trade change: the whole shop is different — its
      // resources, services and hours — so keeping the old state would show
      // one trade's day under another trade's headline.
      key={pack.key}
      merchantId={merchantId}
      pack={pack}
      // The same shop name the rest of the demo uses, so the workspace and
      // the inventory screen do not disagree about whose business this is.
      shopName={getBusinessName(getActiveBusinessType())}
      // Where a mobile trade's day starts. The demo shop has one address;
      // a real merchant's comes from phone_agent_config.base_address, which
      // is wired when this page graduates past the demo.
      origin={BASE_LOCATION}
    />
  )
}
