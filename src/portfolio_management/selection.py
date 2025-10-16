# ruff: noqa
"""Asset selection and filtering for portfolio construction.

This module provides data models and filtering logic for selecting assets
from the tradeable universe based on data quality, history, and user-defined
criteria. It serves as the foundation for portfolio construction by ensuring
only high-quality, appropriate assets are included in the investment universe.

Key components:
- FilterCriteria: Configuration dataclass for asset selection parameters
- SelectedAsset: Data model representing a selected asset with metadata
- AssetSelector: Main filtering and selection logic (to be implemented)

Example:
    >>> from src.portfolio_management.selection import FilterCriteria, SelectedAsset
    >>> criteria = FilterCriteria.default()
    >>> criteria.min_history_days = 504  # Require 2 years of data
    >>> criteria.markets = ["UK", "US"]  # Focus on UK and US markets

"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

from src.portfolio_management.exceptions import AssetSelectionError, DataValidationError


@dataclass
class FilterCriteria:
    """Configuration for asset filtering and selection.

    This dataclass defines the criteria used to filter assets from the tradeable
    universe. It supports filtering by data quality, history requirements, market
    characteristics, and explicit allow/block lists.

    Attributes:
        data_status: List of acceptable data status values (default: ["ok"]).
            Typically "ok" for clean data, may include "warning" for less strict filtering.
        min_history_days: Minimum number of days of price history required (default: 252).
            252 trading days ≈ 1 year of data.
        max_gap_days: Maximum allowed gap in days between consecutive prices (default: 10).
            Helps ensure data continuity without excessive missing periods.
        min_price_rows: Minimum number of price rows required (default: 252).
            Should align with min_history_days for daily data.
        zero_volume_severity: Optional filter for zero-volume severity levels.
            If None, no filtering on zero-volume. Otherwise, filters to assets
            with severity in the provided list (e.g., ["low", "medium"]).
        markets: Optional list of market codes to include (e.g., ["UK", "US"]).
            If None, all markets are included.
        regions: Optional list of region codes to include (e.g., ["Europe", "North America"]).
            If None, all regions are included.
        currencies: Optional list of currency codes to include (e.g., ["GBP", "USD"]).
            If None, all currencies are included.
        categories: Optional list of asset categories to include (e.g., ["ETF", "Stock"]).
            If None, all categories are included.
        allowlist: Optional set of symbols that must be included regardless of other filters.
            Useful for forcing inclusion of specific assets.
        blocklist: Optional set of symbols that must be excluded regardless of other filters.
            Useful for excluding specific assets known to have issues.

    Example:
        >>> criteria = FilterCriteria(
        ...     data_status=["ok"],
        ...     min_history_days=504,  # 2 years
        ...     markets=["UK", "US"],
        ...     currencies=["GBP", "USD", "EUR"],
        ...     blocklist={"BADTICKER.UK"}
        ... )
        >>> criteria.validate()  # Raises ValueError if invalid

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

    def validate(self) -> None:
        """Validate filter criteria parameters.

        Raises:
            ValueError: If any parameter is invalid (e.g., negative values,
                empty required lists).

        Example:
            >>> criteria = FilterCriteria(min_history_days=-1)
            >>> criteria.validate()  # Raises ValueError

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
    """Select assets from a tradeable universe based on filtering criteria.

    This class implements a multi-stage filtering pipeline to select high-quality
    assets suitable for portfolio construction. Each filtering stage can be applied
    independently or as part of the full selection pipeline.

    Filtering stages (applied in order):
    1. Data Quality: Filter by data_status and zero_volume_severity
    2. History: Filter by minimum price history and row counts
    3. Characteristics: Filter by market, region, currency, category
    4. Allow/Block Lists: Apply explicit inclusion/exclusion rules

    Attributes:
        None (stateless class)

    Example:
        >>> import pandas as pd
        >>> from src.portfolio_management.selection import AssetSelector, FilterCriteria
        >>> selector = AssetSelector()
        >>> matches_df = pd.read_csv('data/metadata/tradeable_matches.csv')
        >>> criteria = FilterCriteria(markets=['UK', 'US'])
        >>> selected = selector.select_assets(matches_df, criteria)
        >>> print(f"Selected {len(selected)} assets")

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
            >>> selector = AssetSelector()
            >>> criteria = FilterCriteria(data_status=['ok'])
            >>> filtered = selector._filter_by_data_quality(df, criteria)

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

        # Stage 2: Filter by zero_volume_severity if specified
        if criteria.zero_volume_severity is not None:
            severity_list = criteria.zero_volume_severity

            def check_severity(row: pd.Series[str]) -> bool:
                severity = self._parse_severity(row["data_flags"])
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
            2119
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
            >>> selector = AssetSelector()
            >>> criteria = FilterCriteria(min_history_days=252)
            >>> filtered = selector._filter_by_history(df, criteria)

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

        # Stage 1: Calculate and filter by history days
        df_copy = df.copy()

        def calculate_row_history(row: pd.Series[str]) -> int:
            return self._calculate_history_days(
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
            >>> selector = AssetSelector()
            >>> criteria = FilterCriteria(markets=['UK', 'US'], currencies=['GBP', 'USD'])
            >>> filtered = selector._filter_by_characteristics(df, criteria)

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
            >>> selector = AssetSelector()
            >>> criteria = FilterCriteria(allowlist={'AAPL.US', 'MSFT.US'})
            >>> filtered = selector._apply_lists(df, criteria)

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

        # Stage 1: Apply blocklist if specified
        if criteria.blocklist is not None:
            blocklist = criteria.blocklist

            def not_in_blocklist(row: pd.Series[str]) -> bool:
                return not self._is_in_list(row["symbol"], row["isin"], blocklist)

            blocklist_mask = df_result.apply(not_in_blocklist, axis=1)
            df_result = df_result[blocklist_mask].copy()
            blocklist_count = len(df_result)
            logger.debug(
                f"After blocklist filter ({len(blocklist)} items): "
                f"{blocklist_count} assets (removed {initial_count - blocklist_count})",
            )
            initial_count = blocklist_count
        else:
            logger.debug("Skipping blocklist filter (not specified)")

        # Stage 2: Apply allowlist if specified
        if criteria.allowlist is not None:
            allowlist = criteria.allowlist

            def in_allowlist(row: pd.Series[str]) -> bool:
                return self._is_in_list(row["symbol"], row["isin"], allowlist)

            allowlist_mask = df_result.apply(in_allowlist, axis=1)
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
        """Convert a DataFrame to a list of SelectedAsset objects."""
        assets = []
        for _, row in df.iterrows():
            try:
                asset = SelectedAsset(
                    symbol=row["symbol"],
                    isin=row["isin"],
                    name=row["name"],
                    market=row["market"],
                    region=row["region"],
                    currency=row["currency"],
                    category=row["category"],
                    price_start=row["price_start"],
                    price_end=row["price_end"],
                    price_rows=int(row["price_rows"]),
                    data_status=row["data_status"],
                    data_flags=row.get("data_flags", ""),
                    stooq_path=row["stooq_path"],
                    resolved_currency=row["resolved_currency"],
                    currency_status=row["currency_status"],
                )
                assets.append(asset)
            except (KeyError, TypeError, ValueError) as e:
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Skipping asset due to conversion error: {e} in row {row}",
                )
        return assets

    def select_assets(
        self,
        matches_df: pd.DataFrame,
        criteria: FilterCriteria,
    ) -> list[SelectedAsset]:
        """Run the full asset selection pipeline.

        Args:
            matches_df: DataFrame of matched assets.
            criteria: Filtering criteria.

        Returns:
            A list of SelectedAsset objects that pass all filters.

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
