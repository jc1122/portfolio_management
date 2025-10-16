# ruff: noqa
"""Return calculation utilities for portfolio construction.

This module turns cleaned price data into aligned return series that can be
consumed by portfolio construction engines. It provides:

* ``ReturnConfig`` – a dataclass capturing how returns should be prepared
* ``PriceLoader`` – helpers for reading individual price files safely
* ``ReturnCalculator`` – the end-to-end pipeline with missing-data handling,
  alignment, resampling, and summary statistics

The implementation mirrors the design documented in
``PHASE3_PORTFOLIO_SELECTION_PLAN.md`` Stage 3.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.portfolio_management.exceptions import (
    InsufficientDataError,
    ReturnCalculationError,
)
from src.portfolio_management.selection import SelectedAsset

logger = logging.getLogger(__name__)


@dataclass
class ReturnConfig:
    """Configuration for return preparation.

    Attributes mirror the levers described in the Stage 3 implementation plan.
    Validation keeps the pipeline defensive against misconfiguration.
    """

    method: str = "simple"  # one of: simple, log, excess
    frequency: str = "daily"  # one of: daily, weekly, monthly
    risk_free_rate: float = 0.0  # annual rate used for excess returns
    handle_missing: str = "forward_fill"  # forward_fill, drop, interpolate
    max_forward_fill_days: int = 5
    min_periods: int = 2  # minimum price observations required per asset
    align_method: str = "outer"  # outer keeps full union, inner = intersection
    reindex_to_business_days: bool = False
    min_coverage: float = 0.8  # minimum proportion of non-NaN returns per asset

    def validate(self) -> None:
        """Validate the configuration values and raise ``ValueError`` on issues."""
        if self.method not in {"simple", "log", "excess"}:
            raise ValueError(f"Invalid return method: {self.method}")
        if self.frequency not in {"daily", "weekly", "monthly"}:
            raise ValueError(f"Invalid return frequency: {self.frequency}")
        if self.handle_missing not in {"forward_fill", "drop", "interpolate"}:
            raise ValueError(
                f"Invalid missing data handling method: {self.handle_missing}",
            )
        if self.align_method not in {"outer", "inner"}:
            raise ValueError(f"Invalid align_method: {self.align_method}")
        if self.max_forward_fill_days < 0:
            raise ValueError("max_forward_fill_days must be >= 0")
        if self.min_periods <= 1:
            raise ValueError("min_periods must be greater than 1")
        if not 0 < self.min_coverage <= 1:
            raise ValueError("min_coverage must be within (0, 1]")

    @classmethod
    def default(cls) -> ReturnConfig:
        """Factory for the default (daily, simple) configuration."""
        return cls()

    @classmethod
    def monthly_simple(cls) -> ReturnConfig:
        """Factory that annualises to monthly simple returns."""
        return cls(method="simple", frequency="monthly")

    @classmethod
    def weekly_log(cls) -> ReturnConfig:
        """Factory that prepares weekly log returns."""
        return cls(method="log", frequency="weekly")


@dataclass
class ReturnSummary:
    """Summary statistics produced alongside prepared returns."""

    mean_returns: pd.Series
    volatility: pd.Series
    correlation: pd.DataFrame
    coverage: pd.Series


class PriceLoader:
    """Utilities for reading price files into pandas objects."""

    def load_price_file(self, path: Path) -> pd.Series:
        """Load a single price file into a ``Series`` indexed by date."""
        if not path.exists():
            raise FileNotFoundError(path)

        if path.suffix.lower() == ".csv":
            df = pd.read_csv(
                path,
                header=0,
                usecols=["date", "close"],
                parse_dates=["date"],
                index_col="date",
            )
        else:
            raw = pd.read_csv(path, header=0)
            if "<DATE>" in raw.columns and "<CLOSE>" in raw.columns:
                df = (
                    raw[["<DATE>", "<CLOSE>"]]
                    .copy()
                    .rename(
                        columns={"<DATE>": "date", "<CLOSE>": "close"},
                    )
                )
            elif "DATE" in raw.columns and "CLOSE" in raw.columns:
                df = (
                    raw[["DATE", "CLOSE"]]
                    .copy()
                    .rename(
                        columns={"DATE": "date", "CLOSE": "close"},
                    )
                )
            elif "date" in raw.columns and "close" in raw.columns:
                df = raw[["date", "close"]].copy()
            else:
                raise ValueError(
                    f"Unsupported price file structure for {path}: columns={list(raw.columns)}",
                )
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df.set_index("date", inplace=True)

        df.sort_index(inplace=True)

        if df.index.duplicated().any():
            duplicate_count = int(df.index.duplicated().sum())
            logger.warning(
                "%s contains %d duplicate dates; keeping latest entries",
                path,
                duplicate_count,
            )
            df = df[~df.index.duplicated(keep="last")]

        non_positive_mask = df["close"] <= 0
        if non_positive_mask.any():
            count = int(non_positive_mask.sum())
            logger.warning("Dropping %d non-positive close values from %s", count, path)
            df = df.loc[~non_positive_mask]

        if df.empty:
            logger.warning("Price file %s is empty after cleaning", path)
            return pd.Series(dtype="float64")

        if len(df.index) > 1:
            gaps = df.index.to_series().diff().dt.days.dropna()
            max_gap = int(gaps.max()) if not gaps.empty else 0
            if max_gap > 10:
                logger.warning("Detected maximum gap of %d days in %s", max_gap, path)

        return df["close"].astype(float)

    def load_multiple_prices(
        self,
        assets: list[SelectedAsset],
        prices_dir: Path,
    ) -> pd.DataFrame:
        """Load price data for many assets and align on the union of dates."""
        logger.info(
            "Loading price series for %d assets from %s", len(assets), prices_dir
        )
        all_prices: dict[str, pd.Series] = {}
        for asset in assets:
            price_path = prices_dir / asset.stooq_path
            if not price_path.exists():
                alt_name = Path(asset.stooq_path).stem.lower()
                alt_path = prices_dir / f"{alt_name}.csv"
                if alt_path.exists():
                    price_path = alt_path
                else:
                    logger.warning(
                        "Price file not found for %s (%s)",
                        asset.symbol,
                        price_path,
                    )
                    continue

            try:
                prices = self.load_price_file(price_path)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to load %s: %s", price_path, exc)
                continue

            if prices.empty:
                logger.warning(
                    "Skipping %s because the price series is empty", asset.symbol
                )
                continue

            all_prices[asset.symbol] = prices

        if not all_prices:
            logger.warning("No price files were successfully loaded")
            return pd.DataFrame()

        df = pd.DataFrame(all_prices).sort_index()
        logger.info("Loaded price matrix with shape %s", df.shape)
        return df


class ReturnCalculator:
    """Prepare aligned return series ready for portfolio construction."""

    def __init__(self, price_loader: PriceLoader | None = None):
        self.price_loader = price_loader or PriceLoader()
        self._latest_summary: ReturnSummary | None = None

    @property
    def latest_summary(self) -> ReturnSummary | None:
        """Return the summary produced by the most recent pipeline run."""
        return self._latest_summary

    def load_and_prepare(
        self,
        assets: list[SelectedAsset],
        prices_dir: Path,
        config: ReturnConfig,
    ) -> pd.DataFrame:
        """Run the complete pipeline and return an aligned returns DataFrame."""
        if assets is None:
            raise InsufficientDataError(
                "Assets for return preparation cannot be None.",
                asset_count=0,
                required_count=1,
            )
        if not assets:
            raise InsufficientDataError(
                "No assets provided for return calculation.",
                asset_count=0,
                required_count=1,
            )
        if not prices_dir.exists():
            raise ReturnCalculationError(
                f"Prices directory does not exist: {prices_dir}. "
                "Ensure price files have been exported.",
            )

        try:
            config.validate()
        except ValueError as exc:
            raise ReturnCalculationError(
                f"Invalid return configuration: {exc}"
            ) from exc

        logger.info("Preparing returns for %d assets", len(assets))

        prices = self.price_loader.load_multiple_prices(assets, prices_dir)
        if prices.empty:
            self._latest_summary = None
            raise InsufficientDataError(
                "No price data available for requested assets.",
                asset_count=len(assets),
            )

        prices = self.handle_missing_data(prices, config)
        if prices.empty:
            self._latest_summary = None
            raise InsufficientDataError(
                "All price data was removed during missing-data handling.",
                asset_count=len(assets),
            )

        returns = self.calculate_returns(prices, config)
        if returns.empty:
            self._latest_summary = None
            raise InsufficientDataError(
                "Unable to compute returns for the selected assets.",
                asset_count=len(assets),
            )

        returns = self._align_dates(returns, config)
        returns = self._resample_to_frequency(returns, config.frequency, config.method)
        returns = self._apply_coverage_filter(returns, config.min_coverage)

        if returns.empty:
            self._latest_summary = None
            raise InsufficientDataError(
                "All assets were removed by the coverage filter.",
                asset_count=len(assets),
            )

        self._latest_summary = self._summarize_returns(returns, config)
        if self._latest_summary:
            logger.info(
                "Prepared %d assets across %d periods (annualised mean %.2f%%)",
                returns.shape[1],
                returns.shape[0],
                float(self._latest_summary.mean_returns.mean()) * 100,
            )

        return returns

    def _calculate_simple_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate simple percentage returns ``r_t = (P_t / P_{t-1}) - 1``."""
        return prices.pct_change().dropna()

    def _calculate_log_returns(self, prices: pd.Series) -> pd.Series:
        r"""Calculate log returns ``r_t = \ln(P_t / P_{t-1})``."""
        return np.log(prices / prices.shift(1)).dropna()

    def _calculate_excess_returns(
        self,
        prices: pd.Series,
        risk_free_rate: float,
    ) -> pd.Series:
        """Calculate excess returns ``r_t^{ex} = r_t - r_f`` over the risk-free leg."""
        simple_returns = self._calculate_simple_returns(prices)
        daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
        return simple_returns - daily_rf

    def calculate_returns(
        self,
        prices: pd.DataFrame,
        config: ReturnConfig,
    ) -> pd.DataFrame:
        """Calculate returns for each column in *prices* according to *config*."""
        if prices.empty:
            return pd.DataFrame()

        calculators = {
            "simple": lambda series: self._calculate_simple_returns(series),
            "log": lambda series: self._calculate_log_returns(series),
            "excess": lambda series: self._calculate_excess_returns(
                series,
                config.risk_free_rate,
            ),
        }
        calculator = calculators[config.method]

        results: dict[str, pd.Series] = {}
        for column in prices.columns:
            series = prices[column].dropna()
            if len(series) < config.min_periods:
                logger.warning(
                    "Skipping %s because only %d observations available (min %d)",
                    column,
                    len(series),
                    config.min_periods,
                )
                continue

            returns_series = calculator(series)
            if returns_series.empty:
                logger.warning("No returns generated for %s; skipping", column)
                continue

            extreme = returns_series[returns_series.abs() > 1]
            if not extreme.empty:
                logger.warning(
                    "Found %d extreme returns (>100%%) for %s",
                    len(extreme),
                    column,
                )

            results[column] = returns_series

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results).sort_index()

    def _handle_missing_forward_fill(
        self,
        prices: pd.DataFrame,
        max_days: int,
    ) -> pd.DataFrame:
        """Forward fill gaps up to ``max_days`` for each asset."""
        before = int(prices.isna().sum().sum())
        filled = prices.ffill(limit=max_days)
        after = int(filled.isna().sum().sum())
        logger.info("Forward filled %d missing values", before - after)
        return filled

    def _handle_missing_drop(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Drop any row containing missing values."""
        before = len(prices)
        dropped = prices.dropna()
        logger.info("Dropped %d rows with missing values", before - len(dropped))
        return dropped

    def _handle_missing_interpolate(
        self,
        prices: pd.DataFrame,
        max_days: int,
    ) -> pd.DataFrame:
        """Linearly interpolate gaps up to ``max_days`` consecutive NaNs."""
        interpolated = prices.interpolate(
            method="linear",
            limit=max_days,
            limit_direction="both",
        )
        filled = int(interpolated.isna().sum().sum())
        logger.info("Interpolated missing values; %d NaNs remain", filled)
        return interpolated

    def handle_missing_data(
        self,
        prices: pd.DataFrame,
        config: ReturnConfig,
    ) -> pd.DataFrame:
        """Apply the configured missing-data strategy to *prices*."""
        if prices.empty:
            return prices

        initial_missing = int(prices.isna().sum().sum())
        if initial_missing == 0:
            logger.debug("No missing data detected")
            return prices

        if config.handle_missing == "forward_fill":
            handled = self._handle_missing_forward_fill(
                prices, config.max_forward_fill_days
            )
        elif config.handle_missing == "drop":
            handled = self._handle_missing_drop(prices)
        elif config.handle_missing == "interpolate":
            handled = self._handle_missing_interpolate(
                prices, config.max_forward_fill_days
            )
        else:  # pragma: no cover - validated earlier
            raise ValueError(
                f"Unknown missing data handling method: {config.handle_missing}"
            )

        remaining = int(handled.isna().sum().sum())
        if remaining > 0:
            logger.warning("%d NaNs remain after missing-data handling", remaining)

        return handled.dropna(how="all")

    def _align_dates(self, returns: pd.DataFrame, config: ReturnConfig) -> pd.DataFrame:
        """Align return dates according to the configuration."""
        if returns.empty:
            return returns

        returns = returns.sort_index()
        if config.align_method == "inner":
            aligned = returns.dropna(how="any")
        else:  # outer
            aligned = returns

        if config.reindex_to_business_days and not aligned.empty:
            business_index = pd.bdate_range(aligned.index.min(), aligned.index.max())
            aligned = aligned.reindex(business_index)

        return aligned

    def _resample_to_frequency(
        self,
        returns: pd.DataFrame,
        frequency: str,
        method: str,
    ) -> pd.DataFrame:
        """Resample the returns DataFrame to the requested frequency."""
        if returns.empty or frequency == "daily":
            return returns

        rule_map = {
            "weekly": "W-FRI",
            "monthly": "ME",
        }
        rule = rule_map.get(frequency)
        if rule is None:
            raise ValueError(f"Unsupported frequency: {frequency}")

        if method == "log":
            resampled = returns.resample(rule).sum(min_count=1)
        else:
            resampled = (1 + returns).resample(rule).prod(min_count=1) - 1

        return resampled.dropna(how="all")

    def _apply_coverage_filter(
        self,
        returns: pd.DataFrame,
        min_coverage: float,
    ) -> pd.DataFrame:
        """Remove assets that do not meet the minimum data coverage threshold."""
        if returns.empty:
            return returns

        coverage = returns.notna().mean()
        kept = coverage[coverage >= min_coverage].index.tolist()
        dropped = sorted(set(returns.columns) - set(kept))
        if dropped:
            logger.warning(
                "Dropping %d assets below %.0f%% coverage: %s",
                len(dropped),
                min_coverage * 100,
                ", ".join(dropped[:5]),
            )
        filtered = returns[kept]
        return filtered

    @staticmethod
    def export_returns(returns: pd.DataFrame, path: Path) -> None:
        """Persist prepared returns as a CSV file."""
        returns.to_csv(path)

    def _summarize_returns(
        self,
        returns: pd.DataFrame,
        config: ReturnConfig,
    ) -> ReturnSummary | None:
        """Create summary statistics for the prepared returns."""
        if returns.empty:
            return None

        annualisation = {"daily": 252, "weekly": 52, "monthly": 12}
        factor = annualisation.get(config.frequency, 252)
        mean_returns = returns.mean() * factor
        volatility = returns.std(ddof=0) * np.sqrt(factor)
        correlation = returns.corr()
        coverage = returns.notna().mean()

        logger.debug(
            "Summary stats calculated for %d assets (freq=%s)",
            returns.shape[1],
            config.frequency,
        )

        return ReturnSummary(
            mean_returns=mean_returns,
            volatility=volatility,
            correlation=correlation,
            coverage=coverage,
        )
