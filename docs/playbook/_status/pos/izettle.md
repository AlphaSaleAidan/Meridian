# iZettle (legacy key)

**Registry key:** `izettle` — see `src/services/pos_connectors/registry.py` line 1098. **LEGACY DUPLICATE** of `paypal-zettle` (line 366).

## Status
OUTDATED CONFIG (duplicate of `paypal-zettle`).

The `izettle` key and the `paypal-zettle` key point at the same product, the same vendor, and the same base URL (`https://purchase.izettle.com`). They are two registry entries for one integration target. iZettle was acquired by PayPal in 2018 and rebranded "Zettle by PayPal," and is now being rebranded again to "PayPal Point of Sale." All three names route to the same APIs.

## How the two entries differ in the registry
| Field | `izettle` | `paypal-zettle` |
|-------|-----------|-----------------|
| `base_url` | `https://purchase.izettle.com` | `https://purchase.izettle.com` |
| `auth_type` | `bearer` | `bearer` |
| `test_endpoint` | `/users/self` | `/users/self` |
| `transactions_endpoint` | `/purchases/v2` | `/purchases/v2` |
| `catalog_endpoint` | `/organizations/{org_id}/products` | `/organizations/{org_id}/products` |
| `data_key` | `purchases` | `purchases` |
| `category` | `retail` | `retail` |
| `supports_orders` | `False` | `False` |
| `date_format` | not set | `%Y-%m-%dT%H:%M:%S.000Z` |
| `start_date_param` | not set | `startDate` |
| `end_date_param` | not set | `endDate` |

The `paypal-zettle` entry is the more complete record — it carries the date-window params needed for backfills. The `izettle` entry is missing those fields, so any sync routed through the legacy key will likely fail at the date-range step.

## Why both exist
Historical drift. The `izettle` key predates the PayPal rebrand; `paypal-zettle` was added later without removing the original. Nothing has been verified as actively reading from the `izettle` key in this audit.

## Rep guidance
Treat any merchant who says "iZettle," "Zettle," "Zettle by PayPal," or "PayPal Point of Sale" as a single integration target. See `paypal-zettle.md` for the full product, market, auth, and partner-program writeup. Do not surface the `izettle` key to merchants in any UI.

## Recommendation
DEPRECATE the `izettle` registry key in favor of `paypal-zettle`. Consolidate to one canonical key.

**Reasoning:** Two keys for one vendor invite routing bugs and split telemetry. The `paypal-zettle` entry already carries the date-param fields the legacy entry is missing, so it is the safer canonical record.

**Suggested migration:** add an alias map (`izettle` → `paypal-zettle`) in the registry loader, then remove the standalone `izettle` dict after one release cycle.

## Sources consulted
- `src/services/pos_connectors/registry.py` (entries `izettle` line 1098, `paypal-zettle` line 366) — read directly
- `docs/playbook/_status/pos/paypal-zettle.md` — companion entry
- Live API docs accessed: No (config diff only; live probes already covered in `paypal-zettle.md`)
