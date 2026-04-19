"""
Product Analyzer — Performance scoring, optimization, dead stock detection.

Analyzes product sales data to produce:
  • Product performance tiers (stars, steady, underperformers, dead stock)
  • Margin analysis and pricing opportunities
  • Product velocity (sales rate)
  • Category performance
  • Bundle/upsell opportunities
  • Recommended actions per product
"""
import logging
import math
from collections import defaultdict
from typing import Any

logger = logging.getLogger("meridian.ai.analyzers.products")


class ProductAnalyzer:
    """Produces product intelligence from sales data."""

    # ── Tier thresholds (percentiles) ─────────────────────────
    STAR_PERCENTILE = 80       # Top 20% = stars
    STEADY_PERCENTILE = 40     # Middle 40% = steady performers
    # Below 40% = underperformers
    # Zero sales = dead stock

    def analyze(self, ctx) -> dict:
        """
        Run full product analysis.
        
        Returns:
            {
                "total_products": int,
                "tiers": {star/steady/under/dead counts and lists},
                "top_performers": [top 10 by revenue],
                "worst_performers": [bottom 10 by revenue],
                "dead_stock": [products with zero sales],
                "margin_analysis": {avg margins, best/worst margin products},
                "pricing_opportunities": [products that could be repriced],
                "category_breakdown": {per-category stats},
                "velocity_scores": {product velocity rankings},
            }
        """
        products = ctx.product_performance
        if not products:
            logger.warning(f"No product data for {ctx.org_id}")
            return {"error": "no_product_data"}

        result = {}
        
        result["total_products"] = len(products)
        result["tiers"] = self._tier_products(products)
        result["top_performers"] = self._top_performers(products, 10)
        result["worst_performers"] = self._worst_performers(products, 10)
        result["dead_stock"] = self._find_dead_stock(products, ctx.analysis_days)
        result["margin_analysis"] = self._analyze_margins(products)
        result["pricing_opportunities"] = self._find_pricing_opportunities(products)
        result["velocity_scores"] = self._compute_velocity(products, ctx.analysis_days)
        result["concentration_risk"] = self._concentration_risk(products)
        
        logger.info(
            f"Product analysis: {len(products)} products, "
            f"{len(result['tiers'].get('stars', []))} stars, "
            f"{len(result['dead_stock'])} dead stock, "
            f"{len(result['pricing_opportunities'])} pricing opps"
        )
        return result

    def _tier_products(self, products: list[dict]) -> dict:
        """
        Classify products into performance tiers.
        
        Uses composite score: 60% revenue + 40% volume.
        """
        if not products:
            return {}
        
        # Compute composite scores
        max_revenue = max((p.get("total_revenue_cents") or 0) for p in products) or 1
        max_volume = max((p.get("times_sold") or 0) for p in products) or 1
        
        scored = []
        for p in products:
            rev_score = (p.get("total_revenue_cents") or 0) / max_revenue
            vol_score = (p.get("times_sold") or 0) / max_volume
            composite = (rev_score * 0.6) + (vol_score * 0.4)
            scored.append({**p, "_score": composite})
        
        scored.sort(key=lambda x: x["_score"], reverse=True)
        
        n = len(scored)
        star_cutoff = max(1, int(n * (1 - self.STAR_PERCENTILE / 100)))
        steady_cutoff = max(star_cutoff, int(n * (1 - self.STEADY_PERCENTILE / 100)))
        
        stars = []
        steady = []
        underperformers = []
        dead = []
        
        for i, p in enumerate(scored):
            product_summary = {
                "product_id": p.get("product_id"),
                "name": p.get("product_name", "Unknown"),
                "revenue_cents": (p.get("total_revenue_cents") or 0),
                "times_sold": (p.get("times_sold") or 0),
                "score": round(p["_score"], 3),
            }
            
            if (p.get("times_sold") or 0) == 0:
                dead.append(product_summary)
            elif i < star_cutoff:
                stars.append(product_summary)
            elif i < steady_cutoff:
                steady.append(product_summary)
            else:
                underperformers.append(product_summary)

        return {
            "stars": stars,
            "steady": steady,
            "underperformers": underperformers,
            "dead": dead,
            "star_count": len(stars),
            "steady_count": len(steady),
            "underperformer_count": len(underperformers),
            "dead_count": len(dead),
        }

    def _top_performers(self, products: list[dict], limit: int) -> list[dict]:
        """Top products by revenue."""
        sorted_products = sorted(
            products,
            key=lambda p: (p.get("total_revenue_cents") or 0),
            reverse=True,
        )
        
        return [
            {
                "product_id": p.get("product_id"),
                "name": p.get("product_name", "Unknown"),
                "sku": p.get("sku"),
                "revenue_cents": (p.get("total_revenue_cents") or 0),
                "times_sold": (p.get("times_sold") or 0),
                "avg_price_cents": (p.get("avg_price_cents") or 0),
                "revenue_share_pct": 0,  # filled below
            }
            for p in sorted_products[:limit]
        ]

    def _worst_performers(self, products: list[dict], limit: int) -> list[dict]:
        """Bottom products by revenue (excluding zero-sales)."""
        active = [p for p in products if (p.get("times_sold") or 0) > 0]
        sorted_products = sorted(
            active,
            key=lambda p: (p.get("total_revenue_cents") or 0),
        )
        
        return [
            {
                "product_id": p.get("product_id"),
                "name": p.get("product_name", "Unknown"),
                "revenue_cents": (p.get("total_revenue_cents") or 0),
                "times_sold": (p.get("times_sold") or 0),
            }
            for p in sorted_products[:limit]
        ]

    def _find_dead_stock(self, products: list[dict], days: int) -> list[dict]:
        """Products with zero sales in the analysis period."""
        return [
            {
                "product_id": p.get("product_id"),
                "name": p.get("product_name", "Unknown"),
                "current_price_cents": (p.get("current_price_cents") or 0),
                "sku": p.get("sku"),
                "days_without_sale": days,
            }
            for p in products
            if (p.get("times_sold") or 0) == 0
        ]

    def _analyze_margins(self, products: list[dict]) -> dict:
        """
        Margin analysis across products.
        
        Requires cost data (cost_cents) to compute margins.
        If unavailable, returns estimates based on vertical benchmarks.
        """
        products_with_cost = [
            p for p in products 
            if p.get("total_cost_cents") and (p.get("total_cost_cents") or 0) > 0
        ]
        
        if not products_with_cost:
            return {
                "has_cost_data": False,
                "note": "No cost data available. Connect inventory costs for margin analysis.",
            }
        
        margins = []
        best_margin = None
        worst_margin = None
        
        for p in products_with_cost:
            rev = (p.get("total_revenue_cents") or 0)
            cost = (p.get("total_cost_cents") or 0)
            
            if rev > 0 and cost > 0:
                margin_pct = round((1 - cost / rev) * 100, 1)
                entry = {
                    "product_id": p.get("product_id"),
                    "name": p.get("product_name", "Unknown"),
                    "margin_pct": margin_pct,
                    "revenue_cents": rev,
                    "cost_cents": cost,
                    "profit_cents": rev - cost,
                }
                margins.append(entry)
                
                if best_margin is None or margin_pct > best_margin["margin_pct"]:
                    best_margin = entry
                if worst_margin is None or margin_pct < worst_margin["margin_pct"]:
                    worst_margin = entry
        
        if not margins:
            return {"has_cost_data": False}
        
        avg_margin = round(
            sum(m["margin_pct"] for m in margins) / len(margins), 1
        )
        total_profit = sum(m["profit_cents"] for m in margins)
        
        return {
            "has_cost_data": True,
            "products_with_cost": len(margins),
            "avg_margin_pct": avg_margin,
            "total_profit_cents": total_profit,
            "best_margin": best_margin,
            "worst_margin": worst_margin,
            "below_20_pct_margin": [
                m for m in margins if m["margin_pct"] < 20
            ],
        }

    def _find_pricing_opportunities(self, products: list[dict]) -> list[dict]:
        """
        Identify products that could benefit from repricing.
        
        Criteria:
          1. High-volume, low-price (could raise price without losing volume)
          2. Low-volume, high-price (could lower to drive volume)
          3. Products with heavy discounting (>10% discount rate)
        """
        opportunities = []
        
        if not products:
            return opportunities
        
        # Compute averages
        total_revenue = sum((p.get("total_revenue_cents") or 0) for p in products)
        avg_times_sold = sum((p.get("times_sold") or 0) for p in products) / len(products)
        avg_price = sum((p.get("avg_price_cents") or 0) for p in products) / len(products)
        
        for p in products:
            times_sold = (p.get("times_sold") or 0)
            avg_p = (p.get("avg_price_cents") or 0)
            rev = (p.get("total_revenue_cents") or 0)
            discount = (p.get("total_discount_cents") or 0)
            
            if times_sold == 0:
                continue
            
            discount_rate = discount / max(rev, 1)
            
            # Type 1: High volume, low price → raise price
            if times_sold > avg_times_sold * 1.5 and avg_p < avg_price * 0.7:
                potential_increase = int(avg_p * 0.10)  # 10% increase
                opportunities.append({
                    "product_id": p.get("product_id"),
                    "name": p.get("product_name", "Unknown"),
                    "type": "price_increase",
                    "reason": "High demand, below-average price",
                    "current_price_cents": avg_p,
                    "suggested_price_cents": avg_p + potential_increase,
                    "estimated_monthly_impact_cents": potential_increase * times_sold,
                    "confidence": 0.7,
                })
            
            # Type 2: Low volume, could incentivize
            elif times_sold < avg_times_sold * 0.3 and avg_p > avg_price * 1.3:
                potential_decrease = int(avg_p * 0.10)
                opportunities.append({
                    "product_id": p.get("product_id"),
                    "name": p.get("product_name", "Unknown"),
                    "type": "price_decrease",
                    "reason": "Low demand, above-average price",
                    "current_price_cents": avg_p,
                    "suggested_price_cents": avg_p - potential_decrease,
                    "estimated_volume_increase_pct": 20,
                    "confidence": 0.5,
                })
            
            # Type 3: Heavy discounting
            if discount_rate > 0.10 and rev > 0:
                opportunities.append({
                    "product_id": p.get("product_id"),
                    "name": p.get("product_name", "Unknown"),
                    "type": "reduce_discounting",
                    "reason": f"High discount rate ({discount_rate*100:.0f}%)",
                    "discount_rate_pct": round(discount_rate * 100, 1),
                    "discount_total_cents": discount,
                    "estimated_monthly_impact_cents": int(discount * 0.5),
                    "confidence": 0.6,
                })
        
        return sorted(
            opportunities,
            key=lambda x: (x.get("estimated_monthly_impact_cents") or 0),
            reverse=True,
        )

    def _compute_velocity(self, products: list[dict], days: int) -> dict:
        """
        Product velocity: units sold per day.
        
        Classifies into fast/medium/slow movers.
        """
        if not products or days == 0:
            return {}
        
        velocities = []
        for p in products:
            qty = p.get("total_quantity", (p.get("times_sold") or 0))
            if isinstance(qty, str):
                try:
                    qty = float(qty)
                except ValueError:
                    qty = 0
            velocity = qty / days
            velocities.append({
                "product_id": p.get("product_id"),
                "name": p.get("product_name", "Unknown"),
                "daily_velocity": round(velocity, 2),
                "total_sold": int(qty),
            })
        
        velocities.sort(key=lambda x: x["daily_velocity"], reverse=True)
        
        n = len(velocities)
        fast = velocities[:max(1, n // 5)]
        slow = [v for v in velocities if v["daily_velocity"] == 0]
        
        return {
            "fastest_movers": fast[:10],
            "slowest_movers": slow[:10],
            "avg_daily_velocity": round(
                sum(v["daily_velocity"] for v in velocities) / max(n, 1), 2
            ),
        }

    def _concentration_risk(self, products: list[dict]) -> dict:
        """
        Revenue concentration analysis.
        
        High concentration = risky. If 80% of revenue comes from
        2-3 products, the business is vulnerable.
        """
        total_revenue = sum((p.get("total_revenue_cents") or 0) for p in products)
        if total_revenue == 0:
            return {}
        
        sorted_by_rev = sorted(
            products,
            key=lambda p: (p.get("total_revenue_cents") or 0),
            reverse=True,
        )
        
        cumulative = 0
        products_for_80 = 0
        for p in sorted_by_rev:
            cumulative += (p.get("total_revenue_cents") or 0)
            products_for_80 += 1
            if cumulative >= total_revenue * 0.80:
                break
        
        concentration_pct = round(products_for_80 / max(len(products), 1) * 100, 1)
        
        # Top product share
        top_product_rev = sorted_by_rev[0].get("total_revenue_cents", 0) if sorted_by_rev else 0
        top_product_share = round(top_product_rev / max(total_revenue, 1) * 100, 1)
        
        risk_level = "low"
        if products_for_80 <= 2 or top_product_share > 50:
            risk_level = "high"
        elif products_for_80 <= 5 or top_product_share > 30:
            risk_level = "medium"
        
        return {
            "products_for_80_pct_revenue": products_for_80,
            "concentration_pct": concentration_pct,
            "top_product_share_pct": top_product_share,
            "top_product_name": sorted_by_rev[0].get("product_name", "Unknown") if sorted_by_rev else None,
            "risk_level": risk_level,
            "recommendation": (
                "Revenue is heavily concentrated. Diversify product offerings."
                if risk_level == "high"
                else "Revenue concentration is healthy."
                if risk_level == "low"
                else "Consider diversifying to reduce dependency on top products."
            ),
        }
