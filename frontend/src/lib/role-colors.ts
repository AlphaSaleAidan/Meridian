// Single source of truth for the 7-level org-role palette.
// Used by CanadaPortalTeamPage, USPortalTeamPage and the Recruiting pipeline —
// define colors HERE, never inline. Classes are written out literally so the
// Tailwind content scan keeps them.

export type OrgRole =
  | 'admin'
  | 'vp_sales'
  | 'regional_manager'
  | 'district_manager'
  | 'office_manager'
  | 'assistant_manager'
  | 'sales_rep'

export const ORG_ROLES: OrgRole[] = [
  'admin',
  'vp_sales',
  'regional_manager',
  'district_manager',
  'office_manager',
  'assistant_manager',
  'sales_rep',
]

export const ROLE_LABELS: Record<OrgRole, string> = {
  admin: 'Admin',
  vp_sales: 'VP of Sales',
  regional_manager: 'Regional Manager',
  district_manager: 'District Manager',
  office_manager: 'Office Manager',
  assistant_manager: 'Assistant Manager',
  sales_rep: 'Sales Rep',
}

/** 1 = top of the tree. A manager must strictly outrank their report. */
export const ROLE_LEVELS: Record<OrgRole, number> = {
  admin: 1,
  vp_sales: 2,
  regional_manager: 3,
  district_manager: 4,
  office_manager: 5,
  assistant_manager: 6,
  sales_rep: 7,
}

export interface RoleBadgeClasses {
  text: string
  bg: string
  textColor: string
  border: string
}

// admin keeps the historical purple; the other six get distinct pm-* tokens.
export const ROLE_BADGES: Record<OrgRole, RoleBadgeClasses> = {
  admin: { text: 'Admin', bg: 'bg-pm-purple/10', textColor: 'text-pm-purple', border: 'border-pm-purple/20' },
  vp_sales: { text: 'VP of Sales', bg: 'bg-pm-indigo/10', textColor: 'text-pm-indigo', border: 'border-pm-indigo/20' },
  regional_manager: { text: 'Regional Manager', bg: 'bg-pm-blue/10', textColor: 'text-pm-blue', border: 'border-pm-blue/20' },
  district_manager: { text: 'District Manager', bg: 'bg-pm-teal/10', textColor: 'text-pm-teal', border: 'border-pm-teal/20' },
  office_manager: { text: 'Office Manager', bg: 'bg-pm-amber-gold/10', textColor: 'text-pm-amber-gold', border: 'border-pm-amber-gold/20' },
  assistant_manager: { text: 'Assistant Manager', bg: 'bg-pm-amber-orange/10', textColor: 'text-pm-amber-orange', border: 'border-pm-amber-orange/20' },
  sales_rep: { text: 'Sales Rep', bg: 'bg-pm-accent/10', textColor: 'text-pm-accent', border: 'border-pm-accent/20' },
}

export function isOrgRole(v: unknown): v is OrgRole {
  return typeof v === 'string' && (ORG_ROLES as string[]).includes(v)
}

export function getOrgRoleBadge(role: string | undefined | null): RoleBadgeClasses {
  if (isOrgRole(role)) return ROLE_BADGES[role]
  return ROLE_BADGES.sales_rep
}

/** Roles the given manager role may directly manage (must strictly outrank). */
export function assignableRoles(managerRole: OrgRole): OrgRole[] {
  return ORG_ROLES.filter(r => ROLE_LEVELS[r] > ROLE_LEVELS[managerRole])
}
