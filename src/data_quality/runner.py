"""
Data Quality Runner — Executes validation before AI analysis.

Integrates with Prefect nightly flow as the first step.
Returns pass/fail + detailed results per suite.
"""
import logging
from typing import Any

import pandas as pd
import great_expectations as gx
from great_expectations.core import ExpectationSuite

from .expectations import ALL_SUITES

logger = logging.getLogger("meridian.data_quality.runner")


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
