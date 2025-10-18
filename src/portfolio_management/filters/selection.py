"""Filtering logic for asset selection."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from src.portfolio_management.exceptions import DataValidationError

if TYPE_CHECKING:
    from src.portfolio_management.selection import FilterCriteria


def _parse_severity(data_flags: str | float | None) -> str | None:
    """Extract zero_volume_severity value from data_flags string."""
    if not data_flags or (isinstance(data_flags, float)):
        return None

    data_flags_str = str(data_flags).strip()
    if not data_flags_str:
        return None

    flags = data_flags_str.split(";")
    for flag in flags:
        if "zero_volume_severity=" in flag:
            parts = flag.split("=")
            if len(parts) == 2:
                return parts[1].strip()

    return None


def filter_by_data_quality(
    df: pd.DataFrame,
    criteria: FilterCriteria,
) -> pd.DataFrame:
    """Filter assets by data quality metrics."""
    logger = logging.getLogger(__name__)

    if df.empty:
        logger.warning("Empty input DataFrame to filter_by_data_quality")
        return df

    required_cols = {"data_status", "data_flags"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        logger.error("Missing columns for data quality filter: %s", missing)
        raise DataValidationError(
            f"Match report missing required columns for data quality filter: {missing}",
        )

    initial_count = len(df)
    logger.debug(f"Starting with {initial_count} assets")

    status_mask = df["data_status"].isin(criteria.data_status)
    df_status = df[status_mask].copy()
    status_count = len(df_status)
    logger.debug(
        f"After data_status filter: {status_count} assets "
        f"(removed {initial_count - status_count})",
    )

    if criteria.zero_volume_severity is not None:
        severity_list = criteria.zero_volume_severity

        def check_severity(row: pd.Series[str]) -> bool:
            severity = _parse_severity(row["data_flags"])
            return severity in severity_list

        severity_mask = df_status.apply(check_severity, axis=1)
        df_result = df_status[severity_mask].copy()
        severity_count = len(df_result)
        logger.debug(
            f"After zero_volume_severity filter: {severity_count} assets "
            f"(removed {status_count - severity_count})",
        )
    else:
        df_result = df_status.copy()
        logger.debug("Skipping zero_volume_severity filter (not specified)")

    return df_result


def _calculate_history_days(price_start: str | None, price_end: str | None) -> int:
    """Calculate the number of days between price_start and price_end."""
    if not price_start or not price_end:
        return 0

    try:
        start = pd.to_datetime(price_start)
        end = pd.to_datetime(price_end)

        if start > end:
            return 0

        delta = end - start
        return int(delta.days)
    except (ValueError, TypeError):
        return 0


def filter_by_history(
    df: pd.DataFrame,
    criteria: FilterCriteria,
) -> pd.DataFrame:
    """Filter assets by price history requirements."""
    logger = logging.getLogger(__name__)

    if df.empty:
        logger.warning("Empty input DataFrame to filter_by_history")
        return df

    required_cols = {"price_start", "price_end", "price_rows"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        logger.error("Missing columns for history filter: %s", missing)
        raise DataValidationError(
            f"Match report missing required columns for history filter: {missing}",
        )

    initial_count = len(df)
    logger.debug(f"Starting with {initial_count} assets")

    df_copy = df.copy()

    def calculate_row_history(row: pd.Series[str]) -> int:
        return _calculate_history_days(
            row["price_start"],
            row["price_end"],
        )

    df_copy["_history_days"] = df_copy.apply(calculate_row_history, axis=1)

    history_mask = df_copy["_history_days"] >= criteria.min_history_days
    df_history = df_copy[history_mask].copy()
    history_count = len(df_history)
    logger.debug(
        f"After min_history_days filter ({criteria.min_history_days} days): "
        f"{history_count} assets (removed {initial_count - history_count})",
    )

    rows_mask = df_history["price_rows"] >= criteria.min_price_rows
    df_result = df_history[rows_mask].copy()
    rows_count = len(df_result)
    logger.debug(
        f"After min_price_rows filter ({criteria.min_price_rows} rows): "
        f"{rows_count} assets (removed {history_count - rows_count})",
    )

    if "_history_days" in df_result.columns:
        df_result = df_result.drop(columns=["_history_days"])

    return df_result


def filter_by_characteristics(
    df: pd.DataFrame,
    criteria: FilterCriteria,
) -> pd.DataFrame:
    """Filter assets by market, region, currency, and category characteristics."""
    logger = logging.getLogger(__name__)

    if df.empty:
        logger.warning("Empty input DataFrame to filter_by_characteristics")
        return df

    required_cols = {"market", "region", "resolved_currency", "category"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        logger.error("Missing columns for characteristics filter: %s", missing)
        raise DataValidationError(
            f"Match report missing required columns for characteristics filter: {missing}",
        )

    initial_count = len(df)
    df_result = df.copy()

    if criteria.markets:
        market_mask = df_result["market"].isin(criteria.markets)
        df_result = df_result[market_mask]
        logger.debug(
            f"After market filter: {len(df_result)} assets "
            f"(removed {initial_count - len(df_result)})",
        )

    if criteria.regions:
        region_mask = df_result["region"].isin(criteria.regions)
        df_result = df_result[region_mask]
        logger.debug(
            f"After region filter: {len(df_result)} assets "
            f"(removed {initial_count - len(df_result)})",
        )

    if criteria.currencies:
        currency_mask = df_result["resolved_currency"].isin(criteria.currencies)
        df_result = df_result[currency_mask]
        logger.debug(
            f"After currency filter: {len(df_result)} assets "
            f"(removed {initial_count - len(df_result)})",
        )

    if criteria.categories:
        category_mask = df_result["category"].isin(criteria.categories)
        df_result = df_result[category_mask]
        logger.debug(
            f"After category filter: {len(df_result)} assets "
            f"(removed {initial_count - len(df_result)})",
        )

    return df_result
