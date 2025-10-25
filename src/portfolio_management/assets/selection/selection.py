"""Performs preselection and filtering of assets for universe construction.

This module provides the tools to filter a large list of tradeable assets
down to a smaller, high-quality subset suitable for portfolio construction.
It acts as the first-pass filter before more detailed analysis, such as
classification or return calculation, is performed.

Pipeline Position:
    Raw Asset Data -> **Asset Selection/Preselection** -> Asset Classification

    1.  **Input**: A DataFrame of raw asset metadata (e.g., from
       `tradeable_matches.csv`).
    2.  **Process**: The `AssetSelector` applies a series of filters defined by
       a `FilterCriteria` object. These filters check for data quality,
       sufficient historical data, and specific market characteristics.
    3.  **Output**: A list of `SelectedAsset` objects representing the assets
       that passed all filtering stages.

Key Components:
    - `AssetSelector`: The main engine that runs the filtering pipeline.
    - `FilterCriteria`: A dataclass that defines all filtering parameters.
    - `SelectedAsset`: A dataclass representing a single asset that has
      passed the selection process.

Example:
    >>> import pandas as pd
    >>> from portfolio_management.assets.selection import AssetSelector, FilterCriteria

    # 1. Assume 'matches_df' is a DataFrame loaded from 'tradeable_matches.csv'
    # For this example, we'll create a dummy DataFrame.
    >>> matches_df = pd.DataFrame({
    ...     'symbol': ['AAPL.US', 'BAD.UK'], 'isin': ['US0378331005', 'GB00B1XFGM60'],
    ...     'name': ['Apple Inc', 'Bad Data PLC'], 'market': ['US', 'UK'],
    ...     'region': ['North America', 'Europe'], 'currency': ['USD', 'GBP'],
    ...     'category': ['Stock', 'Stock'], 'price_start': ['2010-01-01', '2023-01-01'],
    ...     'price_end': ['2023-12-31', '2023-12-31'], 'price_rows': [3522, 252],
    ...     'data_status': ['ok', 'error'], 'data_flags': ['', 'missing_data'],
    ...     'stooq_path': ['path/aapl.us.txt', 'path/bad.uk.txt'],
    ...     'resolved_currency': ['USD', 'GBP'], 'currency_status': ['matched', 'matched']
    ... })

    # 2. Define the filtering criteria
    >>> criteria = FilterCriteria(
    ...     min_history_days=365 * 2,  # Require at least 2 years of history
    ...     data_status=['ok'],         # Only accept assets with 'ok' status
    ...     markets=['US']              # Only include assets from the US market
    ... )

    # 3. Initialize the selector and run the selection process
    >>> selector = AssetSelector()
    >>> selected_assets = selector.select_assets(matches_df, criteria)

    # 4. Review the results
    >>> print(f"Selected {len(selected_assets)} asset(s).")
    Selected 1 asset(s).
    >>> if selected_assets:
    ...     print(f"Selected asset symbol: {selected_assets[0].symbol}")
    Selected asset symbol: AAPL.US
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from ...core.exceptions import AssetSelectionError, DataValidationError

if TYPE_CHECKING:
    from portfolio_management.macro.models import RegimeConfig


@dataclass
class FilterCriteria:
    """Defines the parameters for filtering assets.

    This dataclass holds all configurable parameters used by the `AssetSelector`
    to filter the tradeable universe. It allows for detailed control over data
    quality, history requirements, market characteristics, and inclusion/exclusion lists.

    Attributes:
        data_status: List of acceptable data quality status values (e.g., ["ok"]).
        min_history_days: The minimum number of calendar days of price history required.
        max_gap_days: Maximum allowed gap in days between consecutive price points.
        min_price_rows: The minimum number of data rows (e.g., trading days) required.
        zero_volume_severity: Filters assets based on the severity of zero-volume
            trading days (e.g., ["low", "medium"]). If None, this filter is disabled.
        markets: A list of market codes to include (e.g., ["US", "UK"]). If None,
            assets from all markets are considered.
        regions: A list of geographic regions to include (e.g., ["North America"]).
            If None, assets from all regions are considered.
        currencies: A list of currency codes to include (e.g., ["USD", "EUR"]).
            If None, assets in all currencies are considered.
        categories: A list of asset categories to include (e.g., ["Stock", "ETF"]).
            If None, assets of all categories are considered.
        allowlist: A set of symbols or ISINs to include, bypassing other filters.
            These assets will be included if they exist in the input data.
        blocklist: A set of symbols or ISINs to explicitly exclude from the output.
            Blocklisted assets are removed regardless of whether they pass other filters.
        regime_config: Configuration for macroeconomic regime-based filtering.
            If None, no regime-based gating is applied.

    Example:
        >>> # Create a strict filter for US large-cap stocks
        >>> criteria = FilterCriteria(
        ...     min_history_days=365 * 5,
        ...     data_status=['ok'],
        ...     markets=['US'],
        ...     categories=['Stock'],
        ...     blocklist={'DO-NOT-TRADE.US'}
        ... )
        >>> criteria.validate()  # No error raised
    """

    data_status: list[str] = field(default_factory=lambda: ["ok"])
    min_history_days: int = 252
    max_gap_days: int = 10
    min_price_rows: int = 252
    zero_volume_severity: list[str] | None = None
    markets: list[str] | None = None
    regions: list[str] | None = None
    currencies: list[str] | None = None
    categories: list[str] | None = None
    allowlist: set[str] | None = None
    blocklist: set[str] | None = None
    regime_config: RegimeConfig | None = None

    def validate(self) -> None:
        """Validate filter criteria parameters.

        Raises:
            ValueError: If any parameter is invalid (e.g., negative values,
                empty required lists).

        Example:
            >>> # This will raise a ValueError because min_history_days is negative.
            >>> # criteria = FilterCriteria(min_history_days=-1)
            >>> # criteria.validate()

        """
        if self.min_history_days <= 0:
            raise ValueError(
                f"min_history_days must be positive, got {self.min_history_days}",
            )

        if self.min_price_rows <= 0:
            raise ValueError(
                f"min_price_rows must be positive, got {self.min_price_rows}",
            )

        if self.max_gap_days < 0:
            raise ValueError(
                f"max_gap_days must be non-negative, got {self.max_gap_days}",
            )

        if not self.data_status:
            raise ValueError("data_status must not be empty")

    @classmethod
    def default(cls) -> FilterCriteria:
        """Create default filter criteria suitable for most portfolios.

        Returns:
            FilterCriteria with conservative defaults:
            - Require "ok" data status
            - Minimum 1 year of history (252 trading days)
            - Maximum 10-day gaps
            - No filtering by market, region, currency, or category
            - No allow/block lists
            - No regime gating

        Example:
            >>> criteria = FilterCriteria.default()
            >>> criteria.min_history_days
            252

        """
        return cls(
            data_status=["ok"],
            min_history_days=252,
            max_gap_days=10,
            min_price_rows=252,
            zero_volume_severity=None,
            markets=None,
            regions=None,
            currencies=None,
            categories=None,
            allowlist=None,
            blocklist=None,
            regime_config=None,
        )


@dataclass
class SelectedAsset:
    """Represents a selected asset with metadata from the match report.

    This dataclass captures all relevant information about an asset that has
    passed filtering criteria. It combines instrument metadata (symbol, ISIN,
    name) with market information (market, region, currency, category) and
    data quality metrics (date ranges, row counts, status flags).

    Attributes:
        symbol: Stooq ticker symbol (e.g., "1pas.uk", "aapl.us").
        isin: International Securities Identification Number.
        name: Human-readable asset name.
        market: Market code (e.g., "UK", "US", "DE").
        region: Geographic region (e.g., "Europe", "North America").
        currency: Trading currency code (e.g., "GBP", "USD", "EUR").
        category: Asset category (e.g., "ETF", "Stock", "Bond").
        price_start: First available price date as ISO string (YYYY-MM-DD).
        price_end: Last available price date as ISO string (YYYY-MM-DD).
        price_rows: Total number of price observations available.
        data_status: Overall data quality status ("ok", "warning", "error").
        data_flags: Pipe-separated flags with additional quality information.
            Example: "zero_volume_severity=low|other_flag=value"
        stooq_path: Relative path to price file in Stooq data directory.
        resolved_currency: Currency after harmonization/resolution logic.
        currency_status: Status of currency resolution ("matched", "resolved", etc.).

    Example:
        >>> asset = SelectedAsset(
        ...     symbol="1pas.uk",
        ...     isin="GB00BD3RYZ16",
        ...     name="iShares Core MSCI Asia ex Japan UCITS ETF",
        ...     market="UK",
        ...     region="Europe",
        ...     currency="GBP",
        ...     category="ETF",
        ...     price_start="2020-01-02",
        ...     price_end="2025-10-15",
        ...     price_rows=1500,
        ...     data_status="ok",
        ...     data_flags="zero_volume_severity=low",
        ...     stooq_path="d_uk_txt/data/daily/uk/1pas.txt",
        ...     resolved_currency="GBP",
        ...     currency_status="matched"
        ... )

    """

    symbol: str
    isin: str
    name: str
    market: str
    region: str
    currency: str
    category: str
    price_start: str
    price_end: str
    price_rows: int
    data_status: str
    data_flags: str
    stooq_path: str
    resolved_currency: str
    currency_status: str


class AssetSelector:
    """Filters a universe of assets based on a set of criteria.

    This class acts as a preselection engine, applying a multi-stage filtering
    pipeline to a DataFrame of asset metadata. It is stateless and its primary
    entry point is the `select_assets` method.

    The filtering pipeline is executed in a specific order to ensure that the
    most efficient filters are applied first.

    Filtering Stages:
        1.  **Data Quality**: Removes assets with unacceptable `data_status` or
            `zero_volume_severity`.
        2.  **History**: Enforces minimum data history (`min_history_days`) and
            row count (`min_price_rows`).
        3.  **Characteristics**: Filters by market, region, currency, and category.
        4.  **Allow/Block Lists**: Applies manual overrides to include or exclude
            specific assets.

    Example:
        >>> import pandas as pd
        >>> from portfolio_management.assets.selection import AssetSelector, FilterCriteria
        >>>
        >>> # Assume 'matches_df' is a DataFrame with asset metadata.
        >>> matches_df = pd.DataFrame({
        ...     'symbol': ['AAPL.US', 'BAD.UK'], 'isin': ['US0378331005', 'GB00B1XFGM60'],
        ...     'name': ['Apple Inc', 'Bad Data PLC'], 'market': ['US', 'UK'],
        ...     'region': ['North America', 'Europe'], 'currency': ['USD', 'GBP'],
        ...     'category': ['Stock', 'Stock'], 'price_start': ['2010-01-01', '2023-01-01'],
        ...     'price_end': ['2023-12-31', '2023-12-31'], 'price_rows': [3522, 252],
        ...     'data_status': ['ok', 'error'], 'data_flags': ['' , ''],
        ...     'stooq_path': ['' , ''], 'resolved_currency': ['USD', 'GBP'],
        ...     'currency_status': ['matched', 'matched']
        ... })
        >>>
        >>> criteria = FilterCriteria(data_status=['ok'], markets=['US'])
        >>> selector = AssetSelector()
        >>> selected_assets = selector.select_assets(matches_df, criteria)
        >>> print(selected_assets[0].symbol)
        AAPL.US
    """

    def __init__(self) -> None:
        """Initialize the AssetSelector."""

    @staticmethod
    def _parse_severity(data_flags: str | float | None) -> str | None:
        """Extract zero_volume_severity value from data_flags string.

        Parses semicolon-separated flags to find the zero_volume_severity
        value. Flags are formatted as "key=value;key=value".

        Args:
            data_flags: Flags string, potentially containing zero_volume_severity.
                Example: "zero_volume=10;zero_volume_ratio=0.05;zero_volume_severity=low"
                Can also be None or NaN (float).

        Returns:
            The severity level string (e.g., "low", "moderate", "high") if found,
            None otherwise.

        Example:
            >>> AssetSelector._parse_severity("zero_volume=10;zero_volume_severity=high")
            'high'
            >>> AssetSelector._parse_severity("other_flag=value")
            >>> AssetSelector._parse_severity("")
            >>> AssetSelector._parse_severity(None)

        """
        if not data_flags or (isinstance(data_flags, float)):
            # Handle NaN and None values
            return None

        data_flags_str = str(data_flags).strip()
        if not data_flags_str:
            return None

        # Split by semicolon and look for zero_volume_severity
        flags = data_flags_str.split(";")
        for flag in flags:
            if "zero_volume_severity=" in flag:
                # Extract the value after the equals sign
                parts = flag.split("=")
                if len(parts) == 2:
                    return parts[1].strip()

        return None

    @staticmethod
    def _parse_severity_vectorized(data_flags_series: pd.Series) -> pd.Series:
        """Vectorized version of _parse_severity for entire Series.

        Args:
            data_flags_series: Series of data_flags strings.

        Returns:
            Series of severity levels (str or None).

        """
        # Replace NaN and empty strings with None
        flags = data_flags_series.fillna("").astype(str)

        # Extract severity using string operations
        # Look for pattern "zero_volume_severity=X" where X is the severity
        severity = flags.str.extract(r"zero_volume_severity=([^;]+)", expand=False)

        # Strip whitespace from extracted values
        severity = severity.str.strip()

        # Replace empty strings with None
        severity = severity.replace("", None)

        return severity

    def _filter_by_data_quality(
        self,
        df: pd.DataFrame,
        criteria: FilterCriteria,
    ) -> pd.DataFrame:
        """Filter assets by data quality metrics.

        Applies two-stage quality filtering:
        1. Filter by data_status (e.g., "ok", "warning")
        2. Filter by zero_volume_severity if specified in criteria

        Args:
            df: DataFrame with columns 'data_status' and 'data_flags'.
            criteria: FilterCriteria containing data_status and zero_volume_severity.

        Returns:
            Filtered DataFrame with only assets meeting quality criteria.

        Example:
            >>> import pandas as pd
            >>> selector = AssetSelector()
            >>> df = pd.DataFrame({
            ...     'data_status': ['ok', 'ok', 'error', 'ok'],
            ...     'data_flags': ['', 'zero_volume_severity=high', '', 'zero_volume_severity=low']
            ... })
            >>> criteria = FilterCriteria(data_status=['ok'], zero_volume_severity=['low'])
            >>> filtered = selector._filter_by_data_quality(df, criteria)
            >>> len(filtered)
            1

        """
        import logging

        logger = logging.getLogger(__name__)

        if df.empty:
            logger.warning("Empty input DataFrame to _filter_by_data_quality")
            return df

        # Check required columns
        required_cols = {"data_status", "data_flags"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            logger.error("Missing columns for data quality filter: %s", missing)
            raise DataValidationError(
                f"Match report missing required columns for data quality filter: {missing}",
            )

        initial_count = len(df)
        logger.debug(f"Starting with {initial_count} assets")

        # Stage 1: Filter by data_status
        status_mask = df["data_status"].isin(criteria.data_status)
        df_status = df[status_mask].copy()
        status_count = len(df_status)
        logger.debug(
            f"After data_status filter: {status_count} assets "
            f"(removed {initial_count - status_count})",
        )

        # Stage 2: Filter by zero_volume_severity if specified (vectorized)
        if criteria.zero_volume_severity is not None:
            severity_list = criteria.zero_volume_severity

            # Use vectorized version to extract severity from all rows at once
            severity_series = self._parse_severity_vectorized(df_status["data_flags"])
            severity_mask = severity_series.isin(severity_list)

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

    @staticmethod
    def _calculate_history_days(price_start: str | None, price_end: str | None) -> int:
        """Calculate the number of days between price_start and price_end.

        Handles invalid dates gracefully by returning 0.

        Args:
            price_start: Start date as ISO string (YYYY-MM-DD) or None.
            price_end: End date as ISO string (YYYY-MM-DD) or None.

        Returns:
            Number of days between dates if both are valid, 0 otherwise.

        Example:
            >>> AssetSelector._calculate_history_days("2020-01-01", "2025-10-15")
            2114
            >>> AssetSelector._calculate_history_days("invalid", "2025-10-15")
            0
            >>> AssetSelector._calculate_history_days(None, "2025-10-15")
            0

        """
        if not price_start or not price_end:
            return 0

        try:
            start = pd.to_datetime(price_start)
            end = pd.to_datetime(price_end)

            # Check for invalid dates (e.g., future dates, reversed order)
            if start > end:
                return 0

            delta = end - start
            return int(delta.days)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _calculate_history_days_vectorized(
        price_start_series: pd.Series,
        price_end_series: pd.Series,
    ) -> pd.Series:
        """Vectorized version of _calculate_history_days for entire Series.

        Args:
            price_start_series: Series of start dates.
            price_end_series: Series of end dates.

        Returns:
            Series of history days (int), with 0 for invalid dates.

        """
        # Convert to datetime with explicit format to avoid inference warning
        # Most dates are in YYYY-MM-DD format from CSV files
        start_dates = pd.to_datetime(
            price_start_series,
            errors="coerce",
            format="ISO8601",
        )
        end_dates = pd.to_datetime(price_end_series, errors="coerce", format="ISO8601")

        # Calculate timedelta
        deltas = end_dates - start_dates

        # Convert to days, handling NaT by replacing with 0
        days = deltas.dt.days.fillna(0).astype(int)

        # Handle reversed dates (start > end) by setting to 0
        days = days.where(days >= 0, 0)

        return days

    def _filter_by_history(
        self,
        df: pd.DataFrame,
        criteria: FilterCriteria,
    ) -> pd.DataFrame:
        """Filter assets by price history requirements.

        Applies two-stage history filtering:
        1. Filter by minimum history length in days (price_end - price_start)
        2. Filter by minimum price row count

        Args:
            df: DataFrame with columns 'price_start', 'price_end', 'price_rows'.
            criteria: FilterCriteria with min_history_days and min_price_rows.

        Returns:
            Filtered DataFrame with only assets meeting history criteria.

        Example:
            >>> import pandas as pd
            >>> selector = AssetSelector()
            >>> df = pd.DataFrame({
            ...     'price_start': ['2020-01-01', '2022-01-01', '2023-01-01'],
            ...     'price_end': ['2023-01-01', '2023-01-01', '2023-06-01'],
            ...     'price_rows': [756, 252, 126]
            ... })
            >>> criteria = FilterCriteria(min_history_days=365, min_price_rows=200)
            >>> filtered = selector._filter_by_history(df, criteria)
            >>> len(filtered)
            2

        """
        logger = logging.getLogger(__name__)

        if df.empty:
            logger.warning("Empty input DataFrame to _filter_by_history")
            return df

        # Check required columns
        required_cols = {"price_start", "price_end", "price_rows"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            logger.error("Missing columns for history filter: %s", missing)
            raise DataValidationError(
                f"Match report missing required columns for history filter: {missing}",
            )

        initial_count = len(df)
        logger.debug(f"Starting with {initial_count} assets")

        # Stage 1: Calculate and filter by history days (vectorized)
        df_copy = df.copy()

        # Use vectorized calculation
        df_copy["_history_days"] = self._calculate_history_days_vectorized(
            df_copy["price_start"],
            df_copy["price_end"],
        )

        history_mask = df_copy["_history_days"] >= criteria.min_history_days
        df_history = df_copy[history_mask].copy()
        history_count = len(df_history)
        logger.debug(
            f"After min_history_days filter ({criteria.min_history_days} days): "
            f"{history_count} assets (removed {initial_count - history_count})",
        )

        # Stage 2: Filter by minimum price rows
        rows_mask = df_history["price_rows"] >= criteria.min_price_rows
        df_result = df_history[rows_mask].copy()
        rows_count = len(df_result)
        logger.debug(
            f"After min_price_rows filter ({criteria.min_price_rows} rows): "
            f"{rows_count} assets (removed {history_count - rows_count})",
        )

        # Drop the temporary column
        if "_history_days" in df_result.columns:
            df_result = df_result.drop(columns=["_history_days"])

        return df_result

    def _filter_by_characteristics(
        self,
        df: pd.DataFrame,
        criteria: FilterCriteria,
    ) -> pd.DataFrame:
        """Filter assets by market, region, currency, and category characteristics.

        Applies four optional filtering stages (each applied only if specified):
        1. Filter by market (if criteria.markets is not None)
        2. Filter by region (if criteria.regions is not None)
        3. Filter by currency (if criteria.currencies is not None)
        4. Filter by category (if criteria.categories is not None)

        All specified filters are combined with AND logic.

        Args:
            df: DataFrame with columns 'market', 'region', 'resolved_currency', 'category'.
            criteria: FilterCriteria with optional market/region/currency/category filters.

        Returns:
            Filtered DataFrame with only assets matching all specified characteristics.

        Example:
            >>> import pandas as pd
            >>> selector = AssetSelector()
            >>> df = pd.DataFrame({
            ...     'market': ['US', 'US', 'UK', 'DE'],
            ...     'region': ['North America', 'North America', 'Europe', 'Europe'],
            ...     'resolved_currency': ['USD', 'USD', 'GBP', 'EUR'],
            ...     'category': ['Stock', 'ETF', 'Stock', 'ETF']
            ... })
            >>> criteria = FilterCriteria(markets=['UK', 'US'], currencies=['GBP', 'USD'])
            >>> filtered = selector._filter_by_characteristics(df, criteria)
            >>> len(filtered)
            3

        """
        logger = logging.getLogger(__name__)

        if df.empty:
            logger.warning("Empty input DataFrame to _filter_by_characteristics")
            return df

        # Check required columns
        required_cols = {"market", "region", "resolved_currency", "category"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            logger.error("Missing columns for characteristic filter: %s", missing)
            raise DataValidationError(
                f"Match report missing required columns for characteristic filter: {missing}",
            )

        initial_count = len(df)
        logger.debug(f"Starting with {initial_count} assets")

        df_result = df.copy()

        # Filter by market if specified
        if criteria.markets is not None:
            market_mask = df_result["market"].isin(criteria.markets)
            df_result = df_result[market_mask].copy()
            market_count = len(df_result)
            logger.debug(
                f"After market filter ({criteria.markets}): {market_count} assets "
                f"(removed {initial_count - market_count})",
            )
            initial_count = market_count
        else:
            logger.debug("Skipping market filter (not specified)")

        # Filter by region if specified
        if criteria.regions is not None:
            region_mask = df_result["region"].isin(criteria.regions)
            df_result = df_result[region_mask].copy()
            region_count = len(df_result)
            logger.debug(
                f"After region filter ({criteria.regions}): {region_count} assets "
                f"(removed {initial_count - region_count})",
            )
            initial_count = region_count
        else:
            logger.debug("Skipping region filter (not specified)")

        # Filter by currency if specified
        if criteria.currencies is not None:
            currency_mask = df_result["resolved_currency"].isin(criteria.currencies)
            df_result = df_result[currency_mask].copy()
            currency_count = len(df_result)
            logger.debug(
                f"After currency filter ({criteria.currencies}): {currency_count} assets "
                f"(removed {initial_count - currency_count})",
            )
            initial_count = currency_count
        else:
            logger.debug("Skipping currency filter (not specified)")

        # Filter by category if specified
        if criteria.categories is not None:
            category_mask = df_result["category"].isin(criteria.categories)
            df_result = df_result[category_mask].copy()
            category_count = len(df_result)
            logger.debug(
                f"After category filter ({criteria.categories}): {category_count} assets "
                f"(removed {initial_count - category_count})",
            )
        else:
            logger.debug("Skipping category filter (not specified)")

        return df_result

    @staticmethod
    def _is_in_list(symbol: str, isin: str, asset_list: set[str]) -> bool:
        """Check if asset is in list by symbol or ISIN.

        Args:
            symbol: Asset symbol.
            isin: Asset ISIN.
            asset_list: Set of symbols/ISINs to check against.

        Returns:
            True if symbol or isin is in asset_list, False otherwise.

        Example:
            >>> AssetSelector._is_in_list("AAPL.US", "US0378331005", {"AAPL.US"})
            True
            >>> AssetSelector._is_in_list("AAPL.US", "US0378331005", {"US0378331005"})
            True
            >>> AssetSelector._is_in_list("MSFT.US", "US0378331005", {"AAPL.US"})
            False

        """
        return symbol in asset_list or isin in asset_list

    def _apply_lists(
        self,
        df: pd.DataFrame,
        criteria: FilterCriteria,
    ) -> pd.DataFrame:
        """Apply allowlist and blocklist filtering.

        Applies two-stage list-based filtering:
        1. Remove rows where symbol/isin is in blocklist (if specified)
        2. Keep only rows where symbol/isin is in allowlist (if specified)

        If both lists are specified:
        - Blocklist is applied first (more restrictive)
        - Allowlist is applied second
        - The effective filter is: NOT in blocklist AND in allowlist

        Args:
            df: DataFrame with columns 'symbol' and 'isin'.
            criteria: FilterCriteria with optional allowlist/blocklist.

        Returns:
            Filtered DataFrame after applying list-based filters.

        Example:
            >>> import pandas as pd
            >>> selector = AssetSelector()
            >>> df = pd.DataFrame({
            ...     'symbol': ['AAPL.US', 'MSFT.US', 'GOOG.US'],
            ...     'isin': ['US0378331005', 'US5949181045', 'US02079K3059']
            ... })
            >>> criteria = FilterCriteria(allowlist={'AAPL.US', 'MSFT.US'})
            >>> filtered = selector._apply_lists(df, criteria)
            >>> sorted(filtered['symbol'].tolist())
            ['AAPL.US', 'MSFT.US']

        """
        logger = logging.getLogger(__name__)

        if df.empty:
            logger.warning("Empty input DataFrame to _apply_lists")
            return df

        # Check required columns
        required_cols = {"symbol", "isin"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            logger.error("Missing columns for allow/block list filter: %s", missing)
            raise DataValidationError(
                f"Match report missing required columns for allow/block list filter: {missing}",
            )

        initial_count = len(df)
        logger.debug(f"Starting with {initial_count} assets")

        df_result = df.copy()

        # Stage 1: Apply blocklist if specified (vectorized)
        if criteria.blocklist is not None:
            blocklist = criteria.blocklist

            # Vectorized check: row is NOT in blocklist if both symbol AND isin are not in blocklist
            symbol_blocked = df_result["symbol"].isin(blocklist)
            isin_blocked = df_result["isin"].isin(blocklist)
            in_blocklist = symbol_blocked | isin_blocked

            blocklist_mask = ~in_blocklist
            df_result = df_result[blocklist_mask].copy()
            blocklist_count = len(df_result)
            logger.debug(
                f"After blocklist filter ({len(blocklist)} items): "
                f"{blocklist_count} assets (removed {initial_count - blocklist_count})",
            )
            initial_count = blocklist_count
        else:
            logger.debug("Skipping blocklist filter (not specified)")

        # Stage 2: Apply allowlist if specified (vectorized)
        if criteria.allowlist is not None:
            allowlist = criteria.allowlist

            # Vectorized check: row is in allowlist if symbol OR isin is in allowlist
            symbol_allowed = df_result["symbol"].isin(allowlist)
            isin_allowed = df_result["isin"].isin(allowlist)
            in_allowlist = symbol_allowed | isin_allowed

            allowlist_mask = in_allowlist
            df_result = df_result[allowlist_mask].copy()
            allowlist_count = len(df_result)
            logger.debug(
                f"After allowlist filter ({len(allowlist)} items): "
                f"{allowlist_count} assets (removed {initial_count - allowlist_count})",
            )
        else:
            logger.debug("Skipping allowlist filter (not specified)")

        # Warn if both lists overlap
        if criteria.blocklist is not None and criteria.allowlist is not None:
            overlap = criteria.blocklist & criteria.allowlist
            if overlap:
                logger.warning(
                    f"Allowlist and blocklist overlap ({len(overlap)} items): {overlap}. "
                    f"These items will be excluded (blocklist takes precedence).",
                )

        return df_result

    @staticmethod
    def _df_to_selected_assets(df: pd.DataFrame) -> list[SelectedAsset]:
        """Convert a DataFrame to a list of SelectedAsset objects.

        Uses to_dict("records") for efficient conversion instead of iterrows.
        """
        logger = logging.getLogger(__name__)

        # Convert DataFrame to list of dicts for faster iteration
        records = df.to_dict("records")

        assets = []
        for record in records:
            try:
                asset = SelectedAsset(
                    symbol=record["symbol"],
                    isin=record["isin"],
                    name=record["name"],
                    market=record["market"],
                    region=record["region"],
                    currency=record["currency"],
                    category=record["category"],
                    price_start=record["price_start"],
                    price_end=record["price_end"],
                    price_rows=int(record["price_rows"]),
                    data_status=record["data_status"],
                    data_flags=record.get("data_flags", ""),
                    stooq_path=record["stooq_path"],
                    resolved_currency=record["resolved_currency"],
                    currency_status=record["currency_status"],
                )
                assets.append(asset)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(
                    f"Skipping asset due to conversion error: {e} in record {record}",
                )
        return assets

    def select_assets(
        self,
        matches_df: pd.DataFrame,
        criteria: FilterCriteria,
    ) -> list[SelectedAsset]:
        """Runs the full asset selection pipeline on a DataFrame of assets.

        This is the main entry point for the `AssetSelector`. It takes a DataFrame
        of asset metadata and a `FilterCriteria` object, then applies the
        entire filtering pipeline in sequence.

        Args:
            matches_df: A DataFrame containing the raw metadata for all assets
                to be considered for selection. Must include columns specified
                in `FilterCriteria` and `SelectedAsset`.
            criteria: A `FilterCriteria` object that defines the rules for the
                selection process.

        Returns:
            A list of `SelectedAsset` objects, each representing an asset that
            passed all stages of the filtering pipeline. Returns an empty list
            if no assets pass the filters.

        Raises:
            DataValidationError: If `matches_df` is None or is missing required
                columns, or if the `criteria` object is invalid.
            AssetSelectionError: If an allowlist is provided but no assets are
                selected, indicating a potential configuration issue.
        """
        logger = logging.getLogger(__name__)

        if matches_df is None:
            raise DataValidationError(
                "Asset selection requires a non-null matches DataFrame.",
            )

        try:
            criteria.validate()
        except ValueError as exc:
            raise DataValidationError(f"Invalid filter criteria: {exc}") from exc

        required_cols = {
            "symbol",
            "isin",
            "name",
            "market",
            "region",
            "currency",
            "category",
            "price_start",
            "price_end",
            "price_rows",
            "data_status",
            "data_flags",
            "stooq_path",
            "resolved_currency",
            "currency_status",
        }
        if not required_cols.issubset(matches_df.columns):
            missing = required_cols - set(matches_df.columns)
            raise DataValidationError(
                f"Input DataFrame is missing required columns: {missing}",
            )

        initial_count = len(matches_df)
        logger.info(f"Starting asset selection for {initial_count} assets.")

        if matches_df.empty:
            logger.warning("Input DataFrame is empty. No assets to select.")
            return []

        df = matches_df.copy()

        # Apply filters in sequence
        df = self._filter_by_data_quality(df, criteria)
        df = self._filter_by_history(df, criteria)
        df = self._filter_by_characteristics(df, criteria)
        df = self._apply_lists(df, criteria)

        final_count = len(df)
        logger.info(
            f"Finished asset selection. Selected {final_count} of {initial_count} assets.",
        )

        if final_count == 0:
            logger.warning("No assets were selected after filtering.")
            if criteria.allowlist:
                raise AssetSelectionError(
                    "No assets matched the provided allowlist and filter criteria.",
                )
            return []

        # Add summary logging
        percentage_selected = (
            (final_count / initial_count) * 100 if initial_count > 0 else 0
        )
        logger.info(f"Selected {percentage_selected:.2f}%% of the initial universe.")

        market_breakdown = df["market"].value_counts().to_dict()
        region_breakdown = df["region"].value_counts().to_dict()
        logger.info(f"Breakdown by market: {market_breakdown}")
        logger.info(f"Breakdown by region: {region_breakdown}")

        return self._df_to_selected_assets(df)
