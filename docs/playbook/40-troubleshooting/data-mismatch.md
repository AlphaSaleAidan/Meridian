# Data Mismatch

"The numbers in Meridian don't match my POS dashboard." Most common support ticket pattern after POS connection.

## Triage flow

1. Confirm the **date range** they're comparing — Meridian uses the merchant's timezone; POS dashboards sometimes use UTC
2. Confirm they're comparing **net vs gross** consistently (Meridian shows net by default; some POS dashboards show gross)
3. Confirm **refunds and voids** are handled the same way in both views
4. Confirm the **POS connection is current** (not paused, not in failed state)

## Common patterns

### "My yesterday revenue is off by ~5–10%"

| Cause | Fix |
|-------|-----|
| Timezone mismatch (UTC vs merchant local) | Meridian uses merchant TZ; verify in Settings → Account → Timezone |
| Tips included vs excluded | Meridian excludes tips from revenue (industry standard); their POS may include |
| Refunds timing | Meridian deducts refunds on the refund date; some POSes deduct on the original transaction date |
| Pending transactions | Meridian only counts settled; POS may show pending |

### "Specific transactions are missing"

| Cause | Fix |
|-------|-----|
| Backfill in progress | See [backfill-stuck.md](./backfill-stuck.md) |
| Connection paused | Check Settings → POS Connections; if paused, resume |
| Webhook delivery failed | We retry hourly via poll; usually self-heals within 1 hour |
| Transaction void/refund after import | Refund processed as separate event with same date stamp |
| Date range filter wrong in Meridian | Confirm the filter dates |

### "Item names / categories don't match"

| Cause | Fix |
|-------|-----|
| POS auto-categorizes; we use what they send | Re-categorize in their POS, syncs daily |
| Item renamed in POS, old name lingers in Meridian | Catalog re-sync daily; will update within 24 hours |
| Item deleted in POS but appears in our historical | Expected — historical transactions reference deleted items |

### "My customer count doesn't match my POS"

| Cause | Fix |
|-------|-----|
| Definition difference | We count unique customer IDs in the date range; POS may count transactions |
| Anonymous transactions | If most transactions have no customer ID, our customer count appears low — true |
| Customer record deduplication | We dedupe by phone/email; POS may not |

### "Employee performance numbers seem wrong"

| Cause | Fix |
|-------|-----|
| Employee ID assignment varies by POS | Some POSes only attribute the closer of the transaction; we may show different attribution |
| Voids/refunds | We subtract voids/refunds from the original employee; some POSes don't |
| Tip-pooling vs individual | We show individual; merchant's payroll may net via tip pool |

### "Camera analytics numbers don't match my observation"

| Cause | Fix |
|-------|-----|
| Camera angle | If camera can't see the whole entrance, counts will be low — reposition |
| Concurrent viewers in their camera app reducing stream quality | Close other viewers |
| Detection confidence threshold | Default 0.35; some lighting conditions need tuning |
| Single-person re-id appears as 2 people | Rare; happens if person changes clothing or our tracker loses them — usually self-corrects |

## What to say to the merchant

For the 80% of cases that are timezone / tips / refunds:

> "Quick check — when you look at the discrepancy, are we comparing the same timezone, same treatment of tips, and same handling of refunds? Those three together explain ~90% of mismatches we see. If we line those up and there's still a gap, that's a real issue and I'll escalate to engineering."

This frames it correctly and usually closes the ticket in 5 minutes.

## When to escalate

| Pattern | Action |
|---------|--------|
| Gap >15% after timezone/tips/refunds reconciled | High ticket, engineering review |
| Specific transactions missing despite no backfill issue | High ticket |
| Camera counts vary wildly day-to-day with no change in setup | Medium ticket, camera diagnostic |
| Customer says "this has been wrong for weeks and you keep telling me to wait" | Critical; escalate immediately |

---

_Last updated: 2026-05-31_
_Sourced from: src/errors.py (DataError) + docs/customer-sop.md (data ingestion section) + recent fix commits related to data accuracy_
