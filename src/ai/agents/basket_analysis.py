from .base import BaseAgent
from collections import defaultdict

class BasketAnalysisAgent(BaseAgent):
    name = "basket_analysis"
    description = "Co-purchase pairs and bundle recommendations"
    tier = 2

    async def analyze(self) -> dict:
        avail = self.get_data_availability()
        txns = self.ctx.transactions
        products = self.ctx.product_performance

        # Choose calculation path
        if avail.is_full:
            # FULL: co-occurrence from line items
            confidence = avail.quality_score
            path = "full"
        elif avail.is_partial:
            # PARTIAL: basket size from transaction totals
            confidence = avail.quality_score
            path = "partial"
        else:
            # MINIMAL: skip — insufficient data
            confidence = min(0.4, avail.quality_score)
            path = "minimal"

        # MINIMAL: skip with note
        if path == "minimal" or len(txns) < 20:
            if len(txns) < 20 and path != "minimal":
                return self._insufficient_data("At least 20 transactions with line items")
            return self._result(
                summary="Insufficient transaction data for basket analysis",
                score=50,
                insights=[{"type": "no_basket_data", "detail": "Basket analysis requires transaction data with line items", "estimated": True}],
                recommendations=[{
                    "action": "Connect POS line-item data for precise analysis",
                    "impact": "Improves accuracy from estimated to actual values",
                    "effort": "low",
                }],
                data={"source": "minimal", "transaction_count": len(txns)},
                confidence=confidence,
                calculation_path=path,
            )

        # Group items by transaction
        baskets = defaultdict(list)
        for t in txns:
            tid = t.get("id") or t.get("transaction_id", "")
            for item in t.get("items", []):
                name = item.get("product_name") or item.get("name", "")
                if name:
                    baskets[tid].append(name)

        if not baskets:
            # PARTIAL fallback: estimate basket size from transaction totals
            avg_basket = sum(t.get("total_cents", 0) for t in txns) / max(len(txns), 1)
            avg_price = sum(p.get("price_cents", 0) for p in products) / max(len(products), 1) if products else 1
            est_items = round(avg_basket / max(avg_price, 1), 1)
            partial_recommendations = [{"action": "Ensure transaction line items are synced for basket analysis", "impact_cents": 0}]
            if path == "partial":
                partial_recommendations.append({"action": "Connect POS line-item data for precise analysis", "impact": "Improves accuracy from estimated to actual values", "effort": "low"})
            return self._result(
                summary=f"Estimated {est_items} items/basket (no line-item data for co-purchase analysis)",
                score=50,
                insights=[{"type": "no_item_data", "detail": "Line item data needed for co-purchase analysis", "estimated": True}],
                recommendations=partial_recommendations,
                data={"estimated_basket_size": est_items},
                confidence=min(confidence, 0.5),
                calculation_path="partial",
            )

        # Co-occurrence pairs (Apriori-style)
        pair_counts = defaultdict(int)
        item_counts = defaultdict(int)
        for items in baskets.values():
            unique = list(set(items))
            for item in unique:
                item_counts[item] += 1
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    pair = tuple(sorted([unique[i], unique[j]]))
                    pair_counts[pair] += 1

        total_baskets = len(baskets)
        co_purchase_pairs = []
        for pair, count in sorted(pair_counts.items(), key=lambda x: -x[1])[:20]:
            a, b = pair
            support = round(count / total_baskets * 100, 1)
            confidence_a = round(count / max(item_counts[a], 1) * 100, 1)
            confidence_b = round(count / max(item_counts[b], 1) * 100, 1)
            co_purchase_pairs.append({
                "item_a": a,
                "item_b": b,
                "co_occurrence_count": count,
                "support_pct": support,
                "confidence_a_given_b": confidence_b,
                "confidence_b_given_a": confidence_a,
            })

        basket_sizes = [len(items) for items in baskets.values()]
        avg_basket_size = round(sum(basket_sizes) / max(len(basket_sizes), 1), 1)

        score = min(100, 50 + len(co_purchase_pairs) * 3)

        insights = []
        recommendations = []
        if co_purchase_pairs:
            top = co_purchase_pairs[0]
            insights.append({"type": "top_pair", "detail": f"Most common pair: {top['item_a']} + {top['item_b']} ({top['co_occurrence_count']} times)", "estimated": path != "full"})
            recommendations.append({"action": f"Bundle {top['item_a']} + {top['item_b']} with small discount — they already sell together {top['support_pct']}% of the time", "impact_cents": 0})

        if avg_basket_size < 2.0:
            recommendations.append({"action": "Avg basket is small — add cross-sell prompts at checkout", "impact_cents": 0})

        return self._result(
            summary=f"Avg basket {avg_basket_size} items, {len(co_purchase_pairs)} co-purchase pairs found",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "avg_basket_size": avg_basket_size,
                "total_baskets": total_baskets,
                "co_purchase_pairs": co_purchase_pairs,
            },
            confidence=confidence,
            calculation_path=path,
        )
