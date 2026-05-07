# Meridian POS Connector Report

## 1. Research Summary

### Supported (Integrated) — 3 Systems

| System | Auth | API | Canada | Dev Docs |
|--------|------|-----|--------|----------|
| **Square** | OAuth2 | Full public API | Yes | developer.squareup.com |
| **Toast** | OAuth2 | Full API, partner required | Yes | doc.toasttab.com |
| **Clover** | OAuth2 | Full public API | Yes | docs.clover.com |

### Coming Soon — 16 Systems

| System | Auth | Public API | Partner Required | Canada | Dev Docs |
|--------|------|-----------|-----------------|--------|----------|
| **Lightspeed Restaurant** | OAuth2 | Yes | Yes | Yes (HQ: Montreal) | api-portal.lsk.lightspeed.app |
| **Lightspeed Retail** | OAuth2 | Yes | No (marketplace requires it) | Yes | developers.lightspeedhq.com |
| **SpotOn** | Unknown | No public docs found | Likely | No (US only) | developer.spoton.com (DNS failure) |
| **Revel Systems** | API key | Acquired by Shift4 (2024) | Contact Shift4 | Unconfirmed | revelsystems.com → shift4.com |
| **TouchBistro** | Unknown | No public API | Yes (partnership-driven) | Yes (HQ: Toronto) | developer.touchbistro.com (DNS failure) |
| **Aloha (NCR Voyix)** | API key + HMAC | Yes | Yes | Yes | developer.ncrvoyix.com |
| **MICROS/Simphony** | OAuth2 | Yes (Oracle Cloud) | Yes (OPN required) | Yes (global) | docs.oracle.com/food-beverage |
| **Heartland** | API key | Yes (certification required) | Yes | Yes | developer.heartlandpaymentsystems.com |
| **Tekmetric** | API key (Bearer) | Yes | No | Limited (US-focused) | api.tekmetric.com |
| **Shop-Ware** | API key | Yes | Unknown | US-focused | api.shop-ware.com |
| **ShopMonkey** | Unknown | No public docs | Unknown | US-focused | No docs found |
| **Qu POS** | Unknown | No public docs | Unknown | Unknown | Brand may be defunct |
| **SkyTab (Shift4)** | API key | Yes (payments API) | Likely for POS | Limited | dev.shift4.com |
| **Upserve** | Deprecated | Absorbed into Lightspeed | N/A | N/A | Use Lightspeed K-Series |
| **Dutchie POS** | Unknown | No public docs (Cloudflare protected) | Likely required | Yes (ON, AB, BC) | dutchie.com (403) |
| **Shopify POS** | OAuth2 | **Full public API** | No | Yes (HQ: Ottawa) | shopify.dev |

### Manual Import — 12 Systems

| System | Has API? | Reclassify? | Canada |
|--------|----------|-------------|--------|
| **Shopify POS** | **Yes — full REST/GraphQL** | **Recommend → coming_soon** | Yes |
| **Stripe Terminal** | **Yes — full API + SDK** | **Recommend → coming_soon** | Yes |
| **PayPal Zettle** | **Yes — OAuth2** | **Recommend → coming_soon** (US only, no CA) | No |
| **SumUp** | **Yes — OAuth2** | **Recommend → coming_soon** (no CA) | No |
| **Lavu** | Developer docs down | Keep manual_import | US-focused |
| **CAKE POS** | Brand appears defunct (→ BlueCart) | Keep manual_import | Unknown |
| **Mitchell1** | No public API (partnership-driven) | Keep manual_import | Yes |
| **Harbortouch** | Shift4-owned, no separate API | Keep manual_import | Unknown |
| **Aldelo** | No public API found | Keep manual_import | Unknown |
| Others | No public APIs | Keep manual_import | Varies |

## 2. Logos

- **35 SVG files** created in `frontend/src/assets/pos-logos/`
- 3 existing (square.svg, toast.svg, clover.svg) — kept as-is
- 32 new SVGs created with consistent style: 64x64 viewBox, rx=12 rounded backgrounds, white icon marks
- Fallback: `POSLogo` component renders colored initial avatars using `logoInitials` or auto-computed from name
- Dynamic import via `import.meta.glob` — no manual import maintenance needed

## 3. Component

### POSSystemPicker (Unified)
- **Location:** `frontend/src/components/POSSystemPicker.tsx`
- **Props:** `value`, `onChange`, `mode`, `portalContext`, `currency`, `className`
- **Themes:** US (#0F0F12/#1A8FD6) and Canada (#0f1512/#00d4aa) via `portalContext` prop
- **Features:** Searchable dropdown, 4-tier grouping, detail cards per status, credential inputs, waitlist, file upload, SR notes
- **Wired into:**
  - US portal: `pages/sales/CreateCustomerPage.tsx` (mode="new-customer", portalContext="us")
  - Canada Lead Detail: `pages/canada/portal/CanadaPortalLeadDetailPage.tsx` (mode="lead-detail", portalContext="canada")
  - Canada New Customer: `pages/canada/portal/CanadaPortalCreateCustomerPage.tsx` (mode="new-customer", portalContext="canada")
- **TypeScript:** 0 errors

### Legacy Components (Retained)
- `POSSelectorPanel.tsx` — still used by existing US customer portal pages
- `PortalPOSPicker.tsx` — can be removed once all Canada pages use POSSystemPicker

## 4. Migration

- **File:** `src/db/migrations/006_pos_connection_tracking.sql`
- **Tables affected:** `leads`, `merchants`
- **New columns:** `pos_system_id`, `pos_connection_status`, `pos_credentials` (JSONB, encrypted)
- **Status:** Flagged for Aidan review — DO NOT auto-run

## 5. Decisions Needed from Aidan

1. **Reclassify Shopify POS and Stripe Terminal?** Both have full public APIs with OAuth2. Recommend promoting from `contingency` to `coming_soon`.

2. **Reclassify PayPal Zettle and SumUp?** Both have OAuth2 APIs but are NOT available in Canada. Promote to `coming_soon` with `canadaAvailable: false`?

3. **Upserve status?** Absorbed by Lightspeed — mark as `unsupported` with redirect note?

4. **Revel Systems status?** Acquired by Shift4 — merge with SkyTab entry or mark deprecated?

5. **Credential encryption approach:** Recommend AES-256-GCM with `POS_CREDENTIAL_ENCRYPTION_KEY` env var. Never store plaintext API keys in `pos_credentials` JSONB column.

6. **Partner program applications:** These systems require formal partner approval:
   - Toast (partner program)
   - Lightspeed Restaurant (partner application)
   - Aloha/NCR Voyix (developer program)
   - MICROS/Oracle (Oracle PartnerNetwork)
   - Heartland (certification process)
   - Mitchell1 (partnership program)
   
   Should Meridian apply now?

7. **Missing POS systems?** Are there any systems used by current/target merchants not in the 80-system registry?

## 6. Next Steps — Integration Priority

Based on merchant demand and API readiness:

1. **Shopify POS** — Full API, huge merchant base, Canada-native
2. **Stripe Terminal** — Full API, widely used, self-service
3. **Lightspeed Restaurant** — Strong in Canada, OAuth2 ready (needs partner approval)
4. **Lightspeed Retail** — Same vendor, shared auth infrastructure
5. **Tekmetric** — Top automotive POS, API available
6. **PayPal Zettle** — Full OAuth2 API (US only)
7. **SumUp** — Full OAuth2 API (US only)

## Data Schema Extensions

Added to `POSSystem` interface:
- `authMethod` — OAuth2, API key, manual export, etc.
- `developerDocsUrl` — verified developer portal URL
- `partnerProgramRequired` / `partnerProgramUrl`
- `merchantRequirements[]` — form field definitions for SR credential collection
- `setupSteps[]` — step-by-step with SR-specific actions
- `estimatedSetupMinutes`
- `canadaAvailable`
- `notesForSR`
- `category`
- `logoInitials` — 2-char fallback for avatar rendering
