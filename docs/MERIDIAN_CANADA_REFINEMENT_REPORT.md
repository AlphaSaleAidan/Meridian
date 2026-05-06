# Meridian Canada — Refinement Report

**Date:** 2026-05-06
**Scope:** Demo fix, symbol replacement, portal clone cleanup, recruiter section

---

## 1. Demo Fix

**Root cause:** The "Live Demo" and "See Live Demo" buttons on `CanadaLandingPage.tsx` navigated to `/canada` (the landing page itself), creating an infinite loop instead of opening the demo.

**Fix:** Changed both demo buttons to navigate to `/demo`, which is the existing auth-free demo route that renders the full customer dashboard with mock POS data. The `/demo` route is defined in `App.tsx` (line 182) and works identically for both US and Canadian visitors.

**Status:** Fixed. Both buttons now open the demo correctly.

**Note on CAD in demo:** The `/demo` route uses `demo-data.ts` which shows USD amounts from "Sunrise Coffee Co." This is the shared product demo — not a region-specific portal. A Canada-specific demo would require duplicating the demo data module with CAD amounts, which is deferred as a future enhancement.

---

## 2. Symbol Replacement (Maple Leaf -> CN Tower)

All instances of the maple leaf (emoji, unicode, text) replaced with CN Tower:

| File | Line | Before | After |
|------|------|--------|-------|
| `CanadaLandingPage.tsx` | 67 | `🍁` | `🗼` |
| `CanadaLandingPage.tsx` | 278 | `🍁` | `🗼` |
| `CanadaCareersPage.tsx` | 79 | `&#127809;` (maple leaf) | `&#128508;` (tower) |
| `CanadaPortalLoginPage.tsx` | 41 | `\u{1F341}` | `\u{1F5FC}` |
| `CanadaPortalSignupPage.tsx` | 42 | `\u{1F341}` | `\u{1F5FC}` |
| `CanadaSalesLayout.tsx` | 63, 173 | `\u{1F341}` (2 occurrences) | `\u{1F5FC}` |
| `CanadaPortalCreateCustomerPage.tsx` | placeholder | "Maple Leaf Bistro" | "Queen Street Bistro" |
| `CanadaPortalCreateCustomerPage.tsx` | placeholder | "sarah@mapleleaf.ca" | "sarah@queenstreet.ca" |

**Verification:** `grep -rn` across all `.tsx`/`.ts` files confirms zero remaining maple leaf references.

---

## 3. Portal Clone — Demo Data Removed, Empty States Added

### Files updated:

**`CanadaPortalDashboardPage.tsx`** — Complete rewrite
- Removed `salesDemoData` import
- Now queries Supabase `deals` table filtered by `country = 'CA'` and `rep_id`
- Shows proper empty state with "Add Your First Lead" CTA when no data exists
- All currency formatted as `CA$` with `en-CA` locale

**`CanadaPortalLeadsPage.tsx`** — Complete rewrite
- Removed `salesDemoData` import
- Now queries Supabase `deals` table filtered by `country = 'CA'` and `rep_id`
- Starts with empty pipeline, "New Lead" form still functional
- Empty state message: "No leads yet — add your first Canadian prospect."

**`CanadaPortalAccountsPage.tsx`** — Complete rewrite
- Removed `salesDemoData` import
- Now queries Supabase `clients` table filtered by `country = 'CA'` and `rep_id`
- Empty state with Building2 icon and "Go to Leads" CTA

**`CanadaPortalTeamPage.tsx`** — Updated
- Removed hardcoded `DEMO_TEAM` array (Aidan Pierce, Enoch Cheung demo entries)
- Starts with empty array, only shows Supabase `sales_reps` data when available

**`CanadaPortalCreateCustomerPage.tsx`** — Already correct
- Plan prices: Starter CA$339, Growth CA$675, Enterprise CA$1,350
- `formatCAD()` function, `currency: 'CAD'` in data payload
- Routes to `/canada/portal/leads`

### Data isolation notes:

All Canada portal queries filter by `country = 'CA'`. For full data isolation, the following tables need a `country` column or `region` scope:
- `deals` — needs `country` column (used in dashboard + leads queries)
- `clients` — needs `country` column (used in accounts query)
- `sales_reps` — could use `region` column for Canada-only rep views

**Migration needed:** Add `country` column to `deals` and `clients` tables with RLS policies. Provided as a separate migration for Aidan's review before running.

---

## 4. Recruiter Section

**Location:** `CanadaCareersPage.tsx`, placed between "Open Positions" and "Apply Now" sections.

**Implementation:**
- Loads recruiter data from Supabase `recruiters` table (filtered by `region = 'canada'`, `active = true`)
- Falls back to hardcoded Enoch Cheung card if table doesn't exist yet
- Responsive grid: 1 column on mobile, 2 columns on desktop (handles 1-4+ recruiters)
- "Connect with Enoch" button (LinkedIn icon, links to `linkedin_url` or `mailto:email`)

**Database migration:** `supabase/migrations/20260506_recruiters.sql`
- Creates `recruiters` table with fields: id, name, title, company, bio, linkedin_url, email, photo_url, region, active, display_order
- RLS: public read for active recruiters, service role full access
- Seeds Enoch Cheung as first Canada recruiter

**Card displays:**
- Initials avatar (gradient background) or photo if `photo_url` is set
- Name, title, company
- Bio text
- "Connect with [FirstName]" button

---

## 5. Decisions Needed from Aidan

1. **Enoch's real LinkedIn URL** — Currently placeholder `''` in both the fallback data and the migration seed. Replace with real URL.
2. **Enoch's contact email** — Same, currently empty.
3. **Recruiter photo** — If available, upload to Supabase Storage and set `photo_url` in the recruiters table.
4. **Supabase migrations to run:**
   - `20260506_recruiters.sql` — Creates recruiters table + seeds Enoch
   - A `country` column migration for `deals` and `clients` tables (not yet created — needs discussion on how existing data should be tagged)
5. **Canada-specific demo** — The `/demo` route shows USD data from the shared demo. A future enhancement would create a CAD version. Confirm if this is needed now or later.
6. **SMTP credentials** — For automated email notifications on career applications (currently logged to careers table but no email sent).

---

## 6. Next Steps (Priority Order)

1. Run the `20260506_recruiters.sql` migration in Supabase
2. Update Enoch's LinkedIn URL and email in the recruiters table
3. Add `country` column to `deals` and `clients` tables for full data isolation
4. Add RLS policies to enforce Canada/US data separation
5. Build a CAD-specific demo flow (optional, lower priority)
6. Wire up SMTP for career application notifications
