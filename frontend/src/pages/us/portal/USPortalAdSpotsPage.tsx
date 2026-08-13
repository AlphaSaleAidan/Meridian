import { repTier, useSalesAuth } from '@/lib/sales-auth'
import AdSpotConsole, { type AdSpotTheme } from '@/components/adspot/AdSpotConsole'

// US portal palette (hex tokens, matching the rest of /us/portal).
const US_THEME: AdSpotTheme = {
  surface: 'bg-[#111113]',
  bg: 'bg-[#0A0A0B]',
  border: 'border-[#1F1F23]',
  muted: 'text-[#A1A1A8]',
  faint: 'text-[#4a5550]',
  accent: 'text-[#17C5B0]',
  accentBg: 'bg-[#17C5B0]/10',
  accentBorder: 'border-[#17C5B0]/30',
  warn: 'text-[#F59E0B]',
}

export default function USPortalAdSpotsPage() {
  const { rep } = useSalesAuth()
  // Reps see their own spots; admins see the queue. Same rule the rest of the
  // portal follows — a rep has no reason to browse another rep's deliverables.
  const scopeToRep = repTier(rep) === 'admin' ? undefined : rep?.rep_id || undefined
  return <AdSpotConsole theme={US_THEME} repId={scopeToRep} />
}
