# Backfill Stuck

The 18-month historical backfill is taking longer than expected (or appears stuck).

## Expected timeline

| Volume | Expected backfill time |
|--------|------------------------|
| Small (< 100 txn/day, low SKU count) | 1–3 hours |
| Medium (100–500 txn/day) | 3–8 hours |
| Large (500–2000 txn/day) | 8–24 hours |
| Very large (>2000 txn/day, large catalog) | 24–48 hours |

If you're inside the expected window, the merchant probably just needs reassurance. Show them the progress bar moving.

## Symptom: "Backfill is at 0% and hasn't moved"

| Cause | Fix |
|-------|-----|
| Connection actually failed (silent) | Check Settings → POS Connections for error state; may need reconnect |
| Backfill job didn't enqueue | Engineering escalation (rare) |
| POS returned empty initial response | If merchant has very few transactions, "backfill done at 0%" can be correct |

## Symptom: "Stuck at the same percentage for hours"

| Cause | Fix |
|-------|-----|
| POS rate limit, auto-throttling | Expected for high-volume merchants; just slow |
| Specific page of data is failing repeatedly | Engineering escalation; check logs |
| POS-side downtime (Toast, Clover, etc. occasionally have outages) | Wait; status pages of the POS vendor will confirm |

Hard threshold: if stuck >2 hours at the same percentage with no errors logged → engineering escalation.

## Symptom: "Backfill says 100% complete but I'm missing data from [date]"

| Cause | Fix |
|-------|-----|
| POS only returned ~12 months even though we asked for 18 | Some POSes cap historical access (Clover often caps at 12 months for older merchants) |
| Date gap due to a paused POS subscription | If their POS account was paused/cancelled and restarted, gap is real |
| Webhook missed events around the cutover from backfill to live | Run a manual reconciliation via Settings → Re-sync date range |

## Symptom: "Restarted backfill, now it's slower than the first one"

| Cause | Fix |
|-------|-----|
| First backfill cached partial data; restart re-validates everything | Expected; restarts take 1.5x first-run time |
| POS rate-limits are tighter on repeat requests | Self-resolves; backfill auto-throttles |

## When to manually restart

Almost never. The only reasons:

- The backfill is stuck >2 hours at same percentage AND logs show no error (engineering decision)
- The merchant insists they need to recover from a specific date and the auto re-sync hasn't worked

To restart: **Settings → POS Connections → [POS] → Re-sync from [date]**. Warning: this can take as long as the original backfill.

## What to tell the merchant

For active backfills inside expected window:

> "Backfill is in progress — 18 months of transactions takes time, especially if you're high-volume. Expected window for your volume is [X] hours. The progress bar updates every 5 minutes. Insights start appearing on the dashboard as data lands; you don't have to wait for 100%."

For stuck backfills:

> "Looks like backfill paused. I'm pinging engineering now to check. In the meantime, the live data is still flowing — anything from today is being captured. We'll catch up the historical gap once we resolve."

## Escalation

| Situation | Action |
|-----------|--------|
| Stuck >2 hours at same % | Medium ticket + engineering ping |
| Customer was promised insights and they're not landing | High ticket; check Settings for live data first — often live works while backfill struggles |
| Multi-day stuck | Critical; senior engineering |

---

_Last updated: 2026-05-31_
_Sourced from: src/errors.py + docs/customer-sop.md (Step 6 POS Data Connection + timeline tables) + general backfill patterns_
