"""
Data Quality Expectations — Validation rules for POS data.

Defines expectation suites for transactions, products, and customers.
Uses Great Expectations to validate before AI agents run.
"""
import logging
from typing import Any

import great_expectations as gx
from great_expectations.core import ExpectationSuite
from great_expectations.core.expectation_configuration import ExpectationConfiguration

logger = logging.getLogger("meridian.data_quality")


def build_transaction_suite() -> ExpectationSuite:
    """Validate transaction data before AI analysis."""
    suite = ExpectationSuite(expectation_suite_name="transactions")

    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_to_exist",
        kwargs={"column": "id"},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "id"},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "total_cents"},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_between",
        kwargs={"column": "total_cents", "min_value": 0, "max_value": 100_000_00},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "transaction_at"},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "business_id"},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "status", "value_set": ["COMPLETED", "REFUNDED", "VOIDED", "PENDING"]},
    ))

    return suite


def build_product_suite() -> ExpectationSuite:
    """Validate product data."""
    suite = ExpectationSuite(expectation_suite_name="products")

    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "id"},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "name"},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_between",
        kwargs={"column": "price_cents", "min_value": 0, "max_value": 50_000_00},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "business_id"},
    ))

    return suite


def build_customer_suite() -> ExpectationSuite:
    """Validate customer data."""
    suite = ExpectationSuite(expectation_suite_name="customers")

    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "id"},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "business_id"},
    ))
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_unique",
        kwargs={"column": "id"},
    ))

    return suite


ALL_SUITES = {
    "transactions": build_transaction_suite,
    "products": build_product_suite,
    "customers": build_customer_suite,
}
