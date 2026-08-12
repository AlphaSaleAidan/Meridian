// Canonical Canada-portal admin allowlist (transition fallback alongside the
// sales_reps role plane — same doctrine as lib/us-admins.ts). Mirrors the
// arrays currently inlined in CanadaSalesLayout / SalesPortalMobileNav /
// CanadaPortalTeamPage; new Canada surfaces should import from here instead
// of pasting a fourth copy. Backend mirror: ADMIN_EMAILS in src/api/auth.py.
export const CANADA_ADMIN_EMAILS: readonly string[] = [
  'apierce@alphasale.co',
  'aidanpierce72@gmail.com',
  'aidanpierce@meridian.tips',
  'cheungenochmgmt@gmail.com',
  'aidanvietnguyen@gmail.com',
]

export function isCanadaAdmin(email: string | null | undefined): boolean {
  if (!email) return false
  const normalized = email.toLowerCase()
  return CANADA_ADMIN_EMAILS.some(a => a.toLowerCase() === normalized)
}
