import { repTier, useSalesAuth } from '@/lib/sales-auth'
import AdSpotConsole, { type AdSpotTheme } from '@/components/adspot/AdSpotConsole'

// Canada portal palette (pm-canada-* design tokens).
const CANADA_THEME: AdSpotTheme = {
  surface: 'bg-pm-canada-surface',
  bg: 'bg-pm-canada-bg',
  border: 'border-pm-canada-border',
  muted: 'text-pm-canada-text-muted',
  faint: 'text-pm-canada-text-faint',
  accent: 'text-pm-accent',
  accentBg: 'bg-pm-accent/10',
  accentBorder: 'border-pm-accent/30',
  warn: 'text-pm-amber-orange',
}

export default function CanadaPortalAdSpotsPage() {
  const { rep } = useSalesAuth()
  // Reps see their own spots; admins see the queue. Same rule the rest of the
  // portal follows — a rep has no reason to browse another rep's deliverables.
  const scopeToRep = repTier(rep) === 'admin' ? undefined : rep?.rep_id || undefined
  return <AdSpotConsole theme={CANADA_THEME} repId={scopeToRep} />
}
