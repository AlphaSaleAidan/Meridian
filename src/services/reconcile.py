"""
Reconciliation — cross-check Meridian's stored net sales against the POS truth.

After a sync, the numbers we computed (``ours``) should match what the POS
provider reports (``truth``) within a small tolerance. A persistent mismatch
means a sync gap, a mapping bug, or a double-write — surface it loudly so it can
be investigated rather than silently drifting.

This runs on the sync path (post-backfill in the worker, post-incremental in the
manual sync endpoint). It is strictly read-only and best-effort: callers wrap it
so a reconciliation failure never fails the sync.
"""
import logging

logger = logging.getLogger("meridian.services.reconcile")

# A few dollars of slack absorbs rounding / in-flight transactions without
# flagging a healthy connection.
DEFAULT_TOLERANCE_CENTS = 100


async def _ours_net_sales_cents(db, org_id: str) -> int:
    """Meridian's own net sales total for an org.

    Prefers the ``daily_revenue`` materialized view (``total_revenue_cents`` is
    the per-day net). Falls back to summing ``type='sale'`` transactions if the
    view is unavailable, so reconciliation still works on a fresh org.
    """
    try:
        rows = await db.get_daily_revenue(org_id, days=400)
        if rows is not None:
            return sum(int(r.get("total_revenue_cents", 0) or 0) for r in rows)
    except Exception as e:
        logger.warning(f"reconcile: daily_revenue read failed, summing sales: {e}")

    # Fallback: sum sale transactions directly.
    sales = await db.select(
        "transactions",
        columns="total_cents",
        filters={"org_id": f"eq.{org_id}", "type": "eq.sale"},
    )
    return sum(int(r.get("total_cents", 0) or 0) for r in (sales or []))


async def _square_truth_cents(square_client) -> int:
    """Square's authoritative net total = sum of COMPLETED payment amounts."""
    total = 0
    cursor = None
    while True:
        payments, cursor = await square_client.list_payments(cursor=cursor)
        for p in payments or []:
            if p.get("status") != "COMPLETED":
                continue
            total += int((p.get("amount_money") or {}).get("amount", 0) or 0)
        if not cursor:
            break
    return total


async def reconcile_square(
    db,
    org_id: str,
    square_client,
    tolerance_cents: int = DEFAULT_TOLERANCE_CENTS,
) -> dict:
    """Compare Meridian's net sales for ``org_id`` against Square's payment total.

    Returns a dict: ``{org_id, ours_cents, truth_cents, diff_cents, ok}`` where
    ``ok`` is ``abs(diff) <= tolerance_cents``. Logs a warning on mismatch and
    info on match. Read-only.
    """
    ours = await _ours_net_sales_cents(db, org_id)
    truth = await _square_truth_cents(square_client)
    diff = ours - truth
    ok = abs(diff) <= tolerance_cents

    report = {
        "org_id": org_id,
        "ours_cents": ours,
        "truth_cents": truth,
        "diff_cents": diff,
        "ok": ok,
    }

    if ok:
        logger.info(
            "reconcile_square OK org=%s ours=%d truth=%d diff=%d",
            org_id, ours, truth, diff,
        )
    else:
        logger.warning(
            "reconcile_square MISMATCH org=%s ours=%d truth=%d diff=%d (tol=%d)",
            org_id, ours, truth, diff, tolerance_cents,
        )

    return report
