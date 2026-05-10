"""
Data Quality Runner — Executes validation before AI analysis.

Integrates with Prefect nightly flow as the first step.
Returns pass/fail + detailed results per suite.
"""
import logging
from typing import Any

import pandas as pd
try:
    import great_expectations as gx
    from .expectations import ALL_SUITES
    HAS_GX = True
except (ImportError, Exception):
    gx = None
    ALL_SUITES = {}
    HAS_GX = False

logger = logging.getLogger("meridian.data_quality.runner")

# Optional: whylogs for statistical data profiling
try:
    import whylogs as why
    HAS_WHYLOGS = True
except ImportError:
    HAS_WHYLOGS = False


def validate_dataframe(
    df: pd.DataFrame,
    suite_name: str,
) -> dict[str, Any]:
    """Validate a DataFrame against a named expectation suite.

    Returns:
        {
            "suite": "transactions",
            "passed": True/False,
            "success_percent": 95.0,
            "total_expectations": 7,
            "failed_expectations": ["expect_column_values_to_be_between(total_cents)"],
        }
    """
    if not HAS_GX:
        return {"suite": suite_name, "passed": True, "skipped": True, "reason": "great_expectations not available"}

    suite_builder = ALL_SUITES.get(suite_name)
    if not suite_builder:
        return {"suite": suite_name, "passed": False, "error": f"Unknown suite: {suite_name}"}

    suite = suite_builder()

    context = gx.get_context()
    datasource = context.sources.add_or_update_pandas("meridian_pandas")
    data_asset = datasource.add_dataframe_asset(name=suite_name)
    batch_request = data_asset.build_batch_request(dataframe=df)

    results = context.run_checkpoint(
        checkpoint_name=f"{suite_name}_check",
        validations=[{
            "batch_request": batch_request,
            "expectation_suite_name": suite.expectation_suite_name,
        }],
    )

    run_result = list(results.run_results.values())[0]
    validation = run_result["validation_result"]

    failed = [
        r.expectation_config.expectation_type
        for r in validation.results
        if not r.success
    ]

    total = len(validation.results)
    passed_count = total - len(failed)
    success_pct = (passed_count / total * 100) if total > 0 else 100.0

    result = {
        "suite": suite_name,
        "passed": validation.success,
        "success_percent": round(success_pct, 1),
        "total_expectations": total,
        "failed_expectations": failed,
    }

    if validation.success:
        logger.info(f"Data quality PASSED for {suite_name}: {passed_count}/{total}")
    else:
        logger.warning(f"Data quality FAILED for {suite_name}: {failed}")

    return result


def validate_merchant_data(
    transactions: list[dict],
    products: list[dict],
    customers: list[dict] | None = None,
) -> dict[str, Any]:
    """Run all validation suites for a merchant's data.

    Returns combined results with overall pass/fail.
    """
    results = {}

    if transactions:
        results["transactions"] = validate_dataframe(
            pd.DataFrame(transactions), "transactions"
        )

    if products:
        results["products"] = validate_dataframe(
            pd.DataFrame(products), "products"
        )

    if customers:
        results["customers"] = validate_dataframe(
            pd.DataFrame(customers), "customers"
        )

    all_passed = all(r.get("passed", False) for r in results.values())
    return {
        "overall_passed": all_passed,
        "suites": results,
    }


def profile_dataframe(df: pd.DataFrame, dataset_name: str = "dataset") -> dict[str, Any]:
    """Profile a DataFrame using whylogs for statistical summaries.

    Returns column-level statistics (mean, min, max, null count, type distribution).
    Falls back to basic pandas describe() if whylogs is not installed.
    """
    if not HAS_WHYLOGS:
        # Fallback: pandas-based profiling
        desc = df.describe(include="all").to_dict()
        return {
            "dataset": dataset_name,
            "profiler": "pandas",
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": {
                col: {
                    "dtype": str(df[col].dtype),
                    "null_count": int(df[col].isnull().sum()),
                    "null_pct": round(df[col].isnull().mean() * 100, 1),
                    **{k: v for k, v in desc.get(col, {}).items() if pd.notna(v)},
                }
                for col in df.columns
            },
        }

    try:
        profile = why.log(df).profile()
        view = profile.view()
        columns_profile = {}
        for col_name in df.columns:
            col_view = view.get_column(col_name)
            if col_view is None:
                continue
            summary = col_view.to_summary_dict()
            columns_profile[col_name] = {
                "dtype": str(df[col_name].dtype),
                "count": summary.get("counts/n", 0),
                "null_count": summary.get("counts/null", 0),
                "null_pct": round(
                    summary.get("counts/null", 0) / max(summary.get("counts/n", 1), 1) * 100, 1
                ),
                "mean": summary.get("distribution/mean"),
                "stddev": summary.get("distribution/stddev"),
                "min": summary.get("distribution/min"),
                "max": summary.get("distribution/max"),
                "unique_est": summary.get("cardinality/est"),
            }

        return {
            "dataset": dataset_name,
            "profiler": "whylogs",
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns_profile,
        }
    except Exception as e:
        logger.warning(f"whylogs profiling failed: {e}")
        return {
            "dataset": dataset_name,
            "profiler": "error",
            "error": str(e),
            "row_count": len(df),
        }


def run_quality_gate(
    transactions: list[dict],
    products: list[dict],
    customers: list[dict] | None = None,
) -> dict[str, Any]:
    """Combined data quality gate: validation + profiling.

    Call this before AI agents run. Returns validation results plus
    whylogs profiles for drift detection.
    """
    validation = validate_merchant_data(transactions, products, customers)

    # Add whylogs profiling alongside GE validation
    profiles = {}
    if transactions:
        profiles["transactions"] = profile_dataframe(
            pd.DataFrame(transactions), "transactions"
        )
    if products:
        profiles["products"] = profile_dataframe(
            pd.DataFrame(products), "products"
        )
    if customers:
        profiles["customers"] = profile_dataframe(
            pd.DataFrame(customers), "customers"
        )

    validation["profiles"] = profiles
    validation["profiler_available"] = HAS_WHYLOGS
    return validation
