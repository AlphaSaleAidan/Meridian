// Canonical US-portal admin allowlist.
// Add new admins here; every gate in the US portal reads from this list.
export const US_ADMIN_EMAILS: readonly string[] = [
  'apierce@alphasale.co',
  'aidanpierce72@gmail.com',
  'aidanpierce@meridian.tips',
  'cheungenochmgmt@gmail.com',
  'aidanvietnguyen@gmail.com',
]

export function isUsAdmin(email: string | null | undefined): boolean {
  if (!email) return false
  const normalized = email.toLowerCase()
  return US_ADMIN_EMAILS.some(a => a.toLowerCase() === normalized)
}
