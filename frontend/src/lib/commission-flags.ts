// Commission tracking is paused while the pay structure is finalized
// (see "Rep Commission TBD" — rates/units intentionally unresolved).
// While paused, the portal hides all commission rates, earnings math,
// and payout surfaces. Lead/rep rows still store commission_rate so
// nothing needs backfilling when tracking resumes — flip this to false.
export const COMMISSION_TRACKING_PAUSED = true
