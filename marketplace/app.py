"""
Meridian Intelligence Data Marketplace — Streamlit preview app.

Displays sample anonymized benchmark data and links to Square checkout.
Deploy free on Streamlit Cloud, custom domain: data.meridian.tips
"""
import os
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Meridian Intelligence — Data Marketplace",
    layout="wide",
)

st.title("Meridian Intelligence Data Marketplace")
st.subheader(
    "Real POS + camera intelligence from US and Canadian businesses. "
    "Fully anonymized. Updated monthly."
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Merchants", "500+")
col2.metric("Business Types", "5")
col3.metric("Data Points/Month", "15M+")
col4.metric("Updated", "Monthly")

st.divider()

# Sample data preview
st.header("Sample Benchmark Data")
st.caption("Showing anonymized sample rows. Purchase for full dataset.")

sample_path = Path("./data/parquet/benchmarks/sample.parquet")
if sample_path.exists():
    try:
        import duckdb
        sample = duckdb.query(f"""
            SELECT business_type, region, month,
                   round(avg_transaction, 2) as avg_transaction,
                   round(avg_daily_revenue, 0) as avg_daily_revenue,
                   peak_hour,
                   merchant_count
            FROM read_parquet('{sample_path}')
            LIMIT 20
        """).df()
        st.dataframe(sample, use_container_width=True)
    except ImportError:
        import pandas as pd
        st.dataframe(pd.read_parquet(sample_path).head(20), use_container_width=True)
else:
    st.info("Sample dataset not yet generated. Run the nightly pipeline first.")

st.divider()

# Pricing tiers
st.header("Purchase Options")
col1, col2, col3, col4 = st.columns(4)

SQUARE_LINKS = {
    "benchmarks": os.getenv("SQUARE_LINK_BENCHMARKS", "#"),
    "foot_traffic": os.getenv("SQUARE_LINK_FOOT_TRAFFIC", "#"),
    "full_suite": os.getenv("SQUARE_LINK_FULL_SUITE", "#"),
    "archive": os.getenv("SQUARE_LINK_ARCHIVE", "#"),
}

with col1:
    st.markdown("### Industry Benchmarks")
    st.markdown("Monthly anonymized KPIs by business type and region")
    st.metric("Price", "$299/mo")
    st.link_button("Buy Benchmarks", SQUARE_LINKS["benchmarks"])

with col2:
    st.markdown("### Foot Traffic Intelligence")
    st.markdown("Hourly patterns, dwell time, conversion by zone")
    st.metric("Price", "$499/mo")
    st.link_button("Buy Foot Traffic", SQUARE_LINKS["foot_traffic"])

with col3:
    st.markdown("### Full Analytics Suite")
    st.markdown("All datasets, API access, monthly updates")
    st.metric("Price", "$799/mo")
    st.link_button("Buy Full Suite", SQUARE_LINKS["full_suite"])

with col4:
    st.markdown("### Historical Archive")
    st.markdown("Full historical dataset, all types, all regions")
    st.metric("Price", "$2,999/yr")
    st.link_button("Buy Archive", SQUARE_LINKS["archive"])

st.divider()
st.caption(
    "All data is fully anonymized. No merchant names, addresses, "
    "or identifying information is included. Minimum 5 merchants "
    "per data cell (k-anonymity compliance). PIPEDA compliant."
)
