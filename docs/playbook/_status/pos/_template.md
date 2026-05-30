# [POS Name]

**Registry key:** `[system_key]` — see `src/services/pos_connectors/registry.py`

## Status
[LIVE | READY (config exists, needs customer-facing UI) | NEEDS PARTNERSHIP | CSV ONLY | OUTDATED CONFIG | DEAD API | UNCERTAIN]

## What it is
[1-sentence merchant-facing description: who uses it, what vertical, what hardware/form factor.]

## Vertical & market
- **Primary vertical:** [restaurant / retail / automotive / cannabis / salon / multi-vertical / etc.]
- **Estimated NA market presence:** [Small / Medium / Large / Dominant]
- **Typical merchant profile:** [e.g. "single-location coffee shop" or "multi-unit franchise restaurant"]
- **Geographic concentration:** [US / Canada / international / global]

## How to spot the merchant uses it
- [Visual cue 1: terminal hardware brand/look]
- [Visual cue 2: app icon / login URL]
- [Visual cue 3: receipt footer text]
- [Conversational tell: "we use X" or terminology they use]

## Auth method
[OAuth 2.0 / OAuth client_credentials / API key (header) / API key (query) / Basic auth / CSV upload only / partner-only]

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | ✓/✗ | | |
| Catalog / items | ✓/✗ | | |
| Customers | ✓/✗ | | |
| Employees | ✓/✗ | | |
| Inventory | ✓/✗ | | |
| Refunds | ✓/✗ | | |

## Partner program / access requirements
- **Partner program required:** [Yes / No]
- **Sign-up URL:** [URL or N/A]
- **Approval timeline:** [Self-service / 1-2 weeks / 4-8 weeks / Enterprise sales cycle]
- **Cost / revenue share:** [Free / Developer fee / Rev share / Unknown]

## Sandbox / test environment
- **Available:** [Yes / No]
- **URL:** [sandbox URL or N/A]
- **Notes:** [test credentials process, etc.]

## Rate limits
[e.g. "200 req/10 sec" or "Unknown — not documented" or "No limits"]

## Webhook / sync model
[Real-time webhooks / Poll-only / Hybrid / N/A]

## Connect flow (what the merchant does)
1. [Step 1 with exact button/menu labels]
2. [Step 2]
3. ...

## Estimated effort to go LIVE (config → production-ready)
[S (1-3 days) / M (1-2 weeks) / L (1+ months) / XL (custom partnership required)]

## What blocks LIVE status today
- [Specific blocker 1: e.g., "no customer-facing OAuth UI built"]
- [Specific blocker 2: e.g., "config has wrong endpoint paths — needs API doc validation"]
- [Specific blocker 3: e.g., "partner program approval pending"]

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "X" → **Likely cause:** [...] → **Fix:** [...]
- **Symptom:** "Y" → **Likely cause:** [...] → **Fix:** [...]

## Strategic notes
[Free-form: market dynamics, competitive considerations, anything a rep should know that doesn't fit elsewhere.]

## Recommendation
[BUILD NOW / WAIT / DEFER / DEPRECATE]

**Reasoning:** [1-2 sentences why.]

## Sources consulted
- [URL 1]
- [URL 2]
- Live API docs accessed: [Yes / No / Stale]
