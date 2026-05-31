# Troubleshooting — Index

Symptom-indexed. Find the symptom the merchant is reporting, follow the link.

## Connection problems

| Symptom | Doc |
|---------|-----|
| "I clicked Connect and nothing happened" / OAuth screen failed | [pos-connection-failures.md](./pos-connection-failures.md) |
| "It worked yesterday, today it says 401 / unauthorized" | [pos-connection-failures.md](./pos-connection-failures.md) (token refresh section) |
| "My camera shows offline in the dashboard" | [camera-offline.md](./camera-offline.md) |
| "My RTSP URL works in VLC but not Meridian" | [camera-offline.md](./camera-offline.md) (network section) |

## Data problems

| Symptom | Doc |
|---------|-----|
| "The numbers in Meridian don't match my POS dashboard" | [data-mismatch.md](./data-mismatch.md) |
| "I'm missing transactions / orders" | [data-mismatch.md](./data-mismatch.md) |
| "My historical backfill has been stuck for 24+ hours" | [backfill-stuck.md](./backfill-stuck.md) |
| "Backfill says 100% but I'm missing data from [date range]" | [backfill-stuck.md](./backfill-stuck.md) (range-gap section) |

## Insight problems

| Symptom | Doc |
|---------|-----|
| "Where are the insights? I've been connected 48 hours" | [insights-not-appearing.md](./insights-not-appearing.md) |
| "An agent says 'insufficient data' — what's missing?" | [insights-not-appearing.md](./insights-not-appearing.md) (data-quality section) |
| "The Money Left on Table number seems wrong" | [insights-not-appearing.md](./insights-not-appearing.md) (money-left section) |

## Billing problems

| Symptom | Doc |
|---------|-----|
| "I'm being charged USD but I'm in Canada" | [billing-issues.md](./billing-issues.md) |
| "I cancelled and was still charged" | [billing-issues.md](./billing-issues.md) |
| "My invoice doesn't match what was quoted" | [billing-issues.md](./billing-issues.md) |

## Decision tree (full diagnostic)

Lost? Start at [_decision-tree.md](./_decision-tree.md).

## Error vocabulary (from `src/errors.py`)

When a merchant or your team mentions one of these error types, that tells you which doc to start with:

| Error class | What it means | Start here |
|-------------|---------------|------------|
| `DataError` | Required data is missing, invalid, or insufficient | [data-mismatch.md](./data-mismatch.md) or [insights-not-appearing.md](./insights-not-appearing.md) |
| `IntegrationError` | POS or external service interaction failed | [pos-connection-failures.md](./pos-connection-failures.md) |
| `AuthError` | OAuth, token, or RLS auth failure | [pos-connection-failures.md](./pos-connection-failures.md) (auth section) |
| `ConfigError` | Missing or invalid configuration | Engineering escalation |

POS-specific auth errors: `ToastAuthError`, `CloverOAuthError`, `OAuthError` (Square), `CloverAPIError`, `SquareAPIError`. Each of these maps to the same root cause table in [pos-connection-failures.md](./pos-connection-failures.md).

## Escalation

| Severity | Definition | Your action | SLA |
|----------|-----------|-------------|-----|
| Critical | Dashboard down, login impossible, billing breach | Tag CS Manager immediately | 1 hour first response, 4 hour resolution |
| High | Wrong data, agent errors, sync failures | Open ticket + ping CS in Slack | 4 hour first response, 24 hour resolution |
| Medium | Feature request, UI issue, slow performance | Standard ticket | 24 hour first response, 5 business days |
| Low | Question, doc request | Standard ticket | 48 hour first response, 10 business days |

When in doubt: open a ticket, don't try to debug it yourself past the standard scripts in these docs.

---

_Last updated: 2026-05-31_
_Sourced from: src/errors.py (exception hierarchy) + docs/customer-sop.md (SLA structure) + recent fix commits (last 90 days)_
