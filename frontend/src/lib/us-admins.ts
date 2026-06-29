// Canonical US-portal admin allowlist.
// Policy: US portal admin = Aidan Pierce only (all his addresses). Enoch Cheung
// and Aidan Nguyen are Canada/compliance admins and must NOT have US admin
// access — mirrors the backend _US_ADMIN_ALLOWLIST in src/api/routes/us.py.
// Add new admins here; every gate in the US portal reads from this list.
export const US_ADMIN_EMAILS: readonly string[] = [
  'apierce@alphasale.co',
  'aidanpierce72@gmail.com',
  'aidanpierce@meridian.tips',
]

export function isUsAdmin(email: string | null | undefined): boolean {
  if (!email) return false
  const normalized = email.toLowerCase()
  return US_ADMIN_EMAILS.some(a => a.toLowerCase() === normalized)
}
