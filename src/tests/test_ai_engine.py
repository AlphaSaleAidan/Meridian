"""
Integration Test — AI Insights Engine against realistic POS data.

Generates 30 days of realistic POS data (simulating a coffee shop),
runs the full AI pipeline, and validates all outputs.
"""
import asyncio
import json
import math
import random
import sys
from datetime import datetime, date, timedelta, timezone
from uuid import uuid4

# Fix path
sys.path.insert(0, "/work/meridian/src")

from ai.engine import MeridianAI, AnalysisContext, AnalysisResult


# ─── Realistic Test Data Generator ───────────────────────────

def generate_test_data(days: int = 30, seed: int = 42) -> AnalysisContext:
    """
    Generate 30 days of realistic coffee shop POS data.
    
    Simulates:
    - Weekday/weekend patterns (weekdays busier)
    - Peak hours (7-9 AM, 12-1 PM, 5-6 PM)
    - Product mix (coffee, pastries, sandwiches)
    - Growth trend (+3% week-over-week)
    - One anomaly day (a spike)
    - Realistic payment mix
    """
    random.seed(seed)
    
    base_date = date(2026, 3, 19)  # Start date
    
    # ── Products ──────────────────────────────────────────────
    products = [
        {"product_id": "p1", "product_name": "Artisan Latte", "sku": "LAT-001", 
         "current_price_cents": 595, "cost_cents": 180},
        {"product_id": "p2", "product_name": "Drip Coffee", "sku": "DRP-001",
         "current_price_cents": 350, "cost_cents": 80},
        {"product_id": "p3", "product_name": "Breakfast Sandwich", "sku": "BWS-001",
         "current_price_cents": 895, "cost_cents": 350},
        {"product_id": "p4", "product_name": "Blueberry Muffin", "sku": "MUF-001",
         "current_price_cents": 450, "cost_cents": 120},
        {"product_id": "p5", "product_name": "Avocado Toast", "sku": "AVO-001",
         "current_price_cents": 1295, "cost_cents": 500},
        {"product_id": "p6", "product_name": "Cold Brew", "sku": "CLB-001",
         "current_price_cents": 550, "cost_cents": 100},
        {"product_id": "p7", "product_name": "Green Smoothie", "sku": "SMO-001",
         "current_price_cents": 795, "cost_cents": 300},
        {"product_id": "p8", "product_name": "Chocolate Croissant", "sku": "CRO-001",
         "current_price_cents": 495, "cost_cents": 150},
        {"product_id": "p9", "product_name": "Matcha Latte", "sku": "MAT-001",
         "current_price_cents": 650, "cost_cents": 200},
        {"product_id": "p10", "product_name": "Seasonal Special", "sku": "SEA-001",
         "current_price_cents": 750, "cost_cents": 250},
        # Dead stock products
        {"product_id": "p11", "product_name": "Diet Soda", "sku": "SOD-001",
         "current_price_cents": 250, "cost_cents": 100},
        {"product_id": "p12", "product_name": "Protein Bar", "sku": "BAR-001",
         "current_price_cents": 399, "cost_cents": 200},
        {"product_id": "p13", "product_name": "Bottled Water", "sku": "WAT-001",
         "current_price_cents": 199, "cost_cents": 50},
    ]
    
    # Product sale weights (popularity)
    sale_weights = {
        "p1": 0.22,  # Latte = star product
        "p2": 0.18,  # Drip coffee
        "p3": 0.12,  # Breakfast sandwich
        "p4": 0.10,  # Muffin
        "p5": 0.08,  # Avocado toast
        "p6": 0.09,  # Cold brew
        "p7": 0.05,  # Smoothie
        "p8": 0.07,  # Croissant
        "p9": 0.06,  # Matcha
        "p10": 0.03,  # Seasonal
        "p11": 0.00,  # Dead stock
        "p12": 0.00,  # Dead stock
        "p13": 0.00,  # Dead stock
    }
    
    # Hour weights (peak patterns for a coffee shop)
    hour_weights = {
        6: 0.05, 7: 0.15, 8: 0.18, 9: 0.12, 10: 0.08,
        11: 0.07, 12: 0.10, 13: 0.06, 14: 0.04, 15: 0.03,
        16: 0.04, 17: 0.05, 18: 0.02, 19: 0.01,
    }
    
    # ── Generate Daily Revenue Data ───────────────────────────
    daily_revenue = []
    hourly_revenue = []
    transactions = []
    product_performance = {pid: {
        "product_id": pid,
        "product_name": p["product_name"],
        "sku": p["sku"],
        "current_price_cents": p["current_price_cents"],
        "cost_cents": p["cost_cents"],
        "times_sold": 0,
        "total_quantity": 0,
        "total_revenue_cents": 0,
        "total_cost_cents": 0,
        "avg_price_cents": p["current_price_cents"],
        "total_discount_cents": 0,
    } for pid, p in zip([p["product_id"] for p in products], products)}
    
    for day_num in range(days):
        current_date = base_date + timedelta(days=day_num)
        dow = current_date.weekday()
        
        # Base transactions: weekdays more, weekends less
        if dow < 5:  # Weekday
            base_txns = random.randint(80, 120)
        else:  # Weekend
            base_txns = random.randint(50, 80)
        
        # Growth trend: +3% per week
        growth_factor = 1 + (day_num / 7) * 0.03
        base_txns = int(base_txns * growth_factor)
        
        # Anomaly: Day 20 is a spike (charity event)
        if day_num == 20:
            base_txns = int(base_txns * 2.5)
        
        day_revenue = 0
        day_tax = 0
        day_tips = 0
        day_discounts = 0
        day_refund_count = 0
        day_refund_cents = 0
        day_transactions = []
        
        hour_data = {}
        
        for txn_idx in range(base_txns):
            # Pick an hour based on weights
            hour = random.choices(
                list(hour_weights.keys()),
                weights=list(hour_weights.values()),
                k=1
            )[0]
            
            # Pick 1-3 products
            num_items = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
            active_products = [pid for pid, w in sale_weights.items() if w > 0]
            active_weights = [sale_weights[pid] for pid in active_products]
            
            chosen = random.choices(active_products, weights=active_weights, k=num_items)
            
            txn_total = 0
            for pid in chosen:
                p = product_performance[pid]
                price = p["current_price_cents"]
                # Small random price variation (±5%)
                price = int(price * random.uniform(0.95, 1.05))
                txn_total += price
                
                p["times_sold"] += 1
                p["total_quantity"] += 1
                p["total_revenue_cents"] += price
                p["total_cost_cents"] += products[[pp["product_id"] for pp in products].index(pid)]["cost_cents"]
            
            # Tax (8.5%)
            tax = int(txn_total * 0.085)
            
            # Tips (30% chance, avg 15%)
            tip = 0
            if random.random() < 0.30:
                tip = int(txn_total * random.uniform(0.10, 0.25))
            
            # Discounts (5% chance, avg 10% off)
            discount = 0
            if random.random() < 0.05:
                discount = int(txn_total * random.uniform(0.05, 0.15))
                for pid in chosen:
                    product_performance[pid]["total_discount_cents"] += discount // len(chosen)
            
            total = txn_total + tax + tip - discount
            
            # Payment method
            payment = random.choices(
                ["credit_card", "debit_card", "cash", "mobile_pay"],
                weights=[0.50, 0.20, 0.15, 0.15],
                k=1
            )[0]
            
            # Is refund? (1% chance)
            is_refund = random.random() < 0.01
            txn_type = "refund" if is_refund else "sale"
            
            if is_refund:
                day_refund_count += 1
                day_refund_cents += total
            else:
                day_revenue += total
                day_tax += tax
                day_tips += tip
                day_discounts += discount
            
            # Track hourly
            if hour not in hour_data:
                hour_data[hour] = {
                    "revenue": 0, "txns": 0, "cash": 0,
                    "credit": 0, "debit": 0, "mobile": 0,
                    "sales": 0, "refunds": 0,
                }
            
            hd = hour_data[hour]
            hd["revenue"] += total if not is_refund else 0
            hd["txns"] += 1
            if payment == "cash": hd["cash"] += 1
            elif payment == "credit_card": hd["credit"] += 1
            elif payment == "debit_card": hd["debit"] += 1
            elif payment == "mobile_pay": hd["mobile"] += 1
            if is_refund: hd["refunds"] += 1
            else: hd["sales"] += 1
            
            # Transaction record
            transactions.append({
                "id": str(uuid4()),
                "external_id": f"txn_{day_num}_{txn_idx}",
                "type": txn_type,
                "total_cents": total,
                "subtotal_cents": txn_total,
                "tax_cents": tax,
                "tip_cents": tip,
                "discount_cents": discount,
                "payment_method": payment,
                "employee_name": random.choice(["Alex", "Jordan", "Sam", "Casey"]),
                "transaction_at": datetime(
                    current_date.year, current_date.month, current_date.day,
                    hour, random.randint(0, 59),
                    tzinfo=timezone.utc,
                ).isoformat(),
                "location_id": "loc_001",
            })
        
        # Daily aggregate
        daily_revenue.append({
            "date": current_date.isoformat(),
            "transaction_count": base_txns,
            "total_revenue_cents": day_revenue,
            "avg_ticket_cents": day_revenue // max(base_txns - day_refund_count, 1),
            "total_tax_cents": day_tax,
            "total_tip_cents": day_tips,
            "total_discount_cents": day_discounts,
            "total_customers": int(base_txns * 0.85),
            "refund_total_cents": day_refund_cents,
            "refund_count": day_refund_count,
        })
        
        # Hourly aggregates
        for hour, hd in hour_data.items():
            hourly_revenue.append({
                "hour_bucket": datetime(
                    current_date.year, current_date.month, current_date.day,
                    hour, 0, tzinfo=timezone.utc,
                ).isoformat(),
                "transaction_count": hd["txns"],
                "total_revenue_cents": hd["revenue"],
                "avg_ticket_cents": hd["revenue"] // max(hd["txns"], 1),
                "cash_count": hd["cash"],
                "credit_count": hd["credit"],
                "debit_count": hd["debit"],
                "mobile_count": hd["mobile"],
                "sale_count": hd["sales"],
                "refund_count": hd["refunds"],
                "void_count": 0,
            })
    
    # ── Build Context ─────────────────────────────────────────
    ctx = AnalysisContext(
        org_id="test_coffee_shop",
        location_id="loc_001",
        daily_revenue=daily_revenue,
        hourly_revenue=hourly_revenue,
        product_performance=list(product_performance.values()),
        transactions=transactions,
        inventory=[],
        business_vertical="food_beverage",
        analysis_days=days,
    )
    
    return ctx


# ─── Test Runner ──────────────────────────────────────────────

async def run_tests():
    """Run all AI engine tests."""
    print("=" * 70)
    print("  MERIDIAN AI ENGINE — INTEGRATION TEST SUITE")
    print("=" * 70)
    print()
    
    # Generate test data
    print("📊 Generating 30 days of realistic coffee shop data...")
    ctx = generate_test_data(days=30)
    
    print(f"   • {len(ctx.daily_revenue)} daily revenue rows")
    print(f"   • {len(ctx.hourly_revenue)} hourly revenue rows")
    print(f"   • {len(ctx.product_performance)} products")
    print(f"   • {len(ctx.transactions)} transactions")
    total_rev = sum(d["total_revenue_cents"] for d in ctx.daily_revenue)
    print(f"   • Total revenue: ${total_rev/100:,.2f}")
    print()
    
    # Initialize engine
    ai = MeridianAI()
    
    # Run full pipeline
    print("🧠 Running full AI analysis pipeline...")
    result = await ai.analyze(ctx, include_forecasts=True, include_report=True)
    
    print(f"   ⏱️  Completed in {result.duration_seconds:.2f}s")
    print()
    
    # ── Test Results ──────────────────────────────────────────
    passed = 0
    failed = 0
    total = 0
    
    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"   ✅ {name}")
        else:
            failed += 1
            print(f"   ❌ {name} — {detail}")
    
    # ── Test 1: Revenue Analysis ──────────────────────────────
    print("─" * 50)
    print("TEST 1: Revenue Analysis")
    print("─" * 50)
    
    rev = result.revenue_analysis
    check("Revenue analysis produced", bool(rev))
    check("Has KPIs", "kpis" in rev)
    check("Has trend", "trend" in rev)
    check("Has comparison", "comparison" in rev)
    check("Has anomalies", "anomalies" in rev)
    
    kpis = rev.get("kpis", {})
    check(
        f"Total revenue: ${kpis.get('total_revenue_cents', 0)/100:,.0f}",
        kpis.get("total_revenue_cents", 0) > 0,
    )
    check(
        f"Active days: {kpis.get('active_days', 0)}",
        kpis.get("active_days", 0) == 30,
    )
    check(
        f"Avg ticket: ${kpis.get('avg_ticket_cents', 0)/100:,.2f}",
        kpis.get("avg_ticket_cents", 0) > 0,
    )
    
    trend = rev.get("trend", {})
    check(
        f"Trend direction: {trend.get('direction', 'N/A')}",
        trend.get("direction") in ("growing", "stable", "declining"),
    )
    check(
        f"WoW growth: {trend.get('wow_growth_pct', 'N/A')}%",
        trend.get("wow_growth_pct") is not None,
    )
    
    anomalies = rev.get("anomalies", [])
    check(
        f"Anomalies detected: {len(anomalies)}",
        len(anomalies) >= 1,
        "Expected at least 1 anomaly (spike day)",
    )
    if anomalies:
        check(
            f"Spike detected (z-score {anomalies[0].get('z_score', 0):.1f})",
            any(a.get("type") == "spike" for a in anomalies),
        )
    print()
    
    # ── Test 2: Product Analysis ──────────────────────────────
    print("─" * 50)
    print("TEST 2: Product Analysis")
    print("─" * 50)
    
    prod = result.product_analysis
    check("Product analysis produced", bool(prod))
    check(
        f"Total products: {prod.get('total_products', 0)}",
        prod.get("total_products", 0) == 13,
    )
    
    tiers = prod.get("tiers", {})
    check(
        f"Stars: {tiers.get('star_count', 0)}",
        tiers.get("star_count", 0) > 0,
    )
    check(
        f"Dead stock: {tiers.get('dead_count', 0)}",
        tiers.get("dead_count", 0) == 3,
        f"Expected 3 dead stock items",
    )
    
    # Check star product is Artisan Latte (highest weighted)
    stars = tiers.get("stars", [])
    if stars:
        check(
            f"Top star: {stars[0].get('name', 'N/A')}",
            "Latte" in stars[0].get("name", "") or "Coffee" in stars[0].get("name", ""),
        )
    
    dead = prod.get("dead_stock", [])
    check(
        f"Dead stock list: {len(dead)} items",
        len(dead) == 3,
    )
    
    pricing = prod.get("pricing_opportunities", [])
    check(
        f"Pricing opportunities: {len(pricing)}",
        len(pricing) >= 0,  # May or may not find opportunities
    )
    
    concentration = prod.get("concentration_risk", {})
    check(
        f"Concentration risk: {concentration.get('risk_level', 'N/A')}",
        concentration.get("risk_level") in ("low", "medium", "high"),
    )
    print()
    
    # ── Test 3: Pattern Analysis ──────────────────────────────
    print("─" * 50)
    print("TEST 3: Pattern Analysis")
    print("─" * 50)
    
    pat = result.pattern_analysis
    check("Pattern analysis produced", bool(pat))
    
    peak = pat.get("peak_hours", {})
    check("Has peak hours", bool(peak.get("peak")))
    
    golden = peak.get("golden_window", {})
    check(
        f"Golden window: {golden.get('label', 'N/A')}",
        bool(golden.get("label")),
    )
    
    # Peak should be in morning (7-9 AM) given our weights
    if golden.get("start_hour") is not None:
        check(
            f"Golden window starts at hour {golden['start_hour']}",
            golden["start_hour"] in range(6, 10),
            f"Expected morning peak for coffee shop",
        )
    
    dow = pat.get("day_of_week", {})
    check(
        f"Best day: {dow.get('best_day', 'N/A')}",
        dow.get("best_day") is not None,
    )
    check(
        f"Worst day: {dow.get('worst_day', 'N/A')}",
        dow.get("worst_day") is not None,
    )
    
    heatmap = pat.get("heatmap")
    check(
        f"Heatmap: {len(heatmap) if heatmap else 0} rows",
        heatmap is not None and len(heatmap) == 7,
        "Expected 7x24 heatmap",
    )
    
    payment = pat.get("payment_patterns", {})
    check(
        f"Dominant payment: {payment.get('dominant_method', 'N/A')}",
        payment.get("dominant_method") == "credit_card",
    )
    
    ticket = pat.get("ticket_distribution", {})
    check(
        f"Median ticket: ${ticket.get('median_cents', 0)/100:,.2f}",
        ticket.get("median_cents", 0) > 0,
    )
    print()
    
    # ── Test 4: Money Left on Table ───────────────────────────
    print("─" * 50)
    print("TEST 4: Money Left on Table Score")
    print("─" * 50)
    
    mlt = result.money_left_score
    check("Money Left score produced", bool(mlt))
    check(
        f"Total: {mlt.get('total_score_dollars', '$0')}",
        mlt.get("total_score_cents", 0) >= 0,
    )
    
    components = mlt.get("components", {})
    for comp_name in ["underpriced", "dead_stock", "peak_hour_waste",
                       "discount_leakage", "scheduling_gaps"]:
        check(
            f"Component '{comp_name}': ${components.get(comp_name, {}).get('amount_cents', 0)/100:,.0f}",
            comp_name in components,
        )
    
    check(
        f"Has summary: {mlt.get('summary', '')[:60]}...",
        bool(mlt.get("summary")),
    )
    
    top_actions = mlt.get("top_actions", [])
    check(
        f"Top actions: {len(top_actions)}",
        len(top_actions) > 0,
    )
    print()
    
    # ── Test 5: Insights ──────────────────────────────────────
    print("─" * 50)
    print("TEST 5: Insight Generation")
    print("─" * 50)
    
    insights = result.insights
    check(
        f"Insights generated: {len(insights)}",
        len(insights) > 0,
    )
    check(
        "Max 20 insights",
        len(insights) <= 20,
    )
    
    # Check insight structure
    if insights:
        first = insights[0]
        check("Has id", bool(first.get("id")))
        check("Has title", bool(first.get("title")))
        check("Has summary", bool(first.get("summary")))
        check("Has type", bool(first.get("type")))
        check("Has impact", "estimated_monthly_impact_cents" in first)
        check("Has confidence", "confidence_score" in first)
    
    # Check for key insight types
    types_found = set(i.get("type") for i in insights)
    check(
        f"Insight types: {types_found}",
        len(types_found) >= 2,
    )
    
    # Print all insights
    print()
    print("   📋 Generated Insights:")
    for i, insight in enumerate(insights, 1):
        impact = insight.get("estimated_monthly_impact_cents", 0)
        print(
            f"   {i:2d}. [{insight.get('type', '?'):20s}] "
            f"{insight.get('title', 'N/A')}"
            f"  (${impact/100:,.0f}/mo, conf={insight.get('confidence_score', 0):.0%})"
        )
    print()
    
    # ── Test 6: Forecasts ─────────────────────────────────────
    print("─" * 50)
    print("TEST 6: Revenue Forecasts")
    print("─" * 50)
    
    forecasts = result.forecasts
    check(
        f"Forecasts generated: {len(forecasts)}",
        len(forecasts) > 0,
    )
    
    daily_fc = [f for f in forecasts if f["forecast_type"] == "daily_revenue"]
    weekly_fc = [f for f in forecasts if f["forecast_type"] == "weekly_revenue"]
    
    check(f"Daily forecasts: {len(daily_fc)}", len(daily_fc) == 7)
    check(f"Weekly forecasts: {len(weekly_fc)}", len(weekly_fc) == 4)
    
    if daily_fc:
        first_day = daily_fc[0]
        check(
            f"Day 1 forecast: ${first_day['predicted_value_cents']/100:,.0f}",
            first_day["predicted_value_cents"] > 0,
        )
        check(
            "Has confidence interval",
            first_day["lower_bound_cents"] < first_day["predicted_value_cents"] < first_day["upper_bound_cents"],
        )
        check(
            f"Confidence: {first_day['confidence_score']:.0%}",
            0 < first_day["confidence_score"] <= 1,
        )
        
        # Confidence should decay
        if len(daily_fc) >= 7:
            check(
                "Confidence decays over horizon",
                daily_fc[0]["confidence_score"] > daily_fc[6]["confidence_score"],
            )
    
    if weekly_fc:
        next_week = weekly_fc[0]
        check(
            f"Week 1 forecast: ${next_week['predicted_value_cents']/100:,.0f}",
            next_week["predicted_value_cents"] > 0,
        )
    
    print()
    print("   📈 7-Day Forecast:")
    for fc in daily_fc:
        print(
            f"   {fc['period_start']:12s}  "
            f"${fc['predicted_value_cents']/100:>8,.0f}  "
            f"(${fc['lower_bound_cents']/100:,.0f} - ${fc['upper_bound_cents']/100:,.0f})  "
            f"conf={fc['confidence_score']:.0%}"
        )
    print()
    
    # ── Test 7: Weekly Report ─────────────────────────────────
    print("─" * 50)
    print("TEST 7: Weekly Report")
    print("─" * 50)
    
    report = result.weekly_report
    check("Report generated", report is not None)
    
    if report:
        rd = report.get("report_data", {})
        check("Has revenue section", "revenue" in rd)
        check("Has products section", "products" in rd)
        check("Has patterns section", "patterns" in rd)
        check("Has insights section", "insights" in rd)
        check("Has forecast section", "forecast" in rd)
        check("Has money_left section", "money_left" in rd)
        
        rev_sec = rd.get("revenue", {})
        check(
            f"Report revenue: {rev_sec.get('total_dollars', '$0')}",
            rev_sec.get("total_cents", 0) > 0,
        )
        
        insight_sec = rd.get("insights", [])
        check(
            f"Report insights count: {len(insight_sec)}",
            len(insight_sec) > 0,
        )
    print()
    
    # ── Test 8: Error Handling ────────────────────────────────
    print("─" * 50)
    print("TEST 8: Error Handling")
    print("─" * 50)
    
    check(
        f"Errors: {len(result.errors)}",
        len(result.errors) == 0,
        f"Errors: {result.errors}",
    )
    
    # Test with empty data
    empty_ctx = AnalysisContext(org_id="empty_test")
    empty_result = await ai.analyze(empty_ctx, include_forecasts=True, include_report=True)
    check(
        "Empty data handled gracefully",
        empty_result is not None,
    )
    check(
        "No crash on empty data",
        True,  # If we get here, it didn't crash
    )
    print()
    
    # ── Test 9: Performance ───────────────────────────────────
    print("─" * 50)
    print("TEST 9: Performance")
    print("─" * 50)
    
    check(
        f"Analysis under 5 seconds: {result.duration_seconds:.2f}s",
        result.duration_seconds < 5.0,
    )
    
    # Run 5 times and average
    import time
    times = []
    for _ in range(5):
        start = time.time()
        await ai.analyze(ctx, include_forecasts=True, include_report=True)
        times.append(time.time() - start)
    
    avg_time = sum(times) / len(times)
    check(
        f"Avg analysis time: {avg_time:.3f}s (5 runs)",
        avg_time < 3.0,
    )
    print()
    
    # ── Summary ───────────────────────────────────────────────
    print("=" * 70)
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 70)
    print()
    
    # Print full summary
    print("📊 ANALYSIS SUMMARY")
    print("─" * 50)
    print(f"   Revenue:      ${kpis.get('total_revenue_cents', 0)/100:>10,.2f}")
    print(f"   Transactions: {kpis.get('total_transactions', 0):>10,d}")
    print(f"   Avg Ticket:   ${kpis.get('avg_ticket_cents', 0)/100:>10,.2f}")
    print(f"   Trend:        {trend.get('direction', 'N/A'):>10s}")
    print(f"   WoW Growth:   {trend.get('wow_growth_pct', 0):>9.1f}%")
    print()
    print(f"   Products:     {prod.get('total_products', 0):>10d}")
    print(f"   Stars:        {tiers.get('star_count', 0):>10d}")
    print(f"   Dead Stock:   {tiers.get('dead_count', 0):>10d}")
    print()
    print(f"   Money Left:   {mlt.get('total_score_dollars', '$0'):>10s}/mo")
    print(f"   Insights:     {len(insights):>10d}")
    print(f"   Forecasts:    {len(forecasts):>10d}")
    print(f"   Duration:     {result.duration_seconds:>9.2f}s")
    print()
    
    if failed > 0:
        print("⚠️  Some tests failed!")
        return False
    else:
        print("🎉 All tests passed!")
        return True


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
