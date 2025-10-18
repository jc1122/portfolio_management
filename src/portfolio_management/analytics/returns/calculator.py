"""Return calculation engine."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ...core.exceptions import InsufficientDataError, ReturnCalculationError
from .config import ReturnConfig
from .loaders import PriceLoader
from .models import ReturnSummary

if TYPE_CHECKING:
    from ...assets.selection.selection import SelectedAsset

logger = logging.getLogger(__name__)


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
                f"Invalid return configuration: {exc}",
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
                prices,
                config.max_forward_fill_days,
            )
        elif config.handle_missing == "drop":
            handled = self._handle_missing_drop(prices)
        elif config.handle_missing == "interpolate":
            handled = self._handle_missing_interpolate(
                prices,
                config.max_forward_fill_days,
            )
        else:  # pragma: no cover - validated earlier
            raise ValueError(
                f"Unknown missing data handling method: {config.handle_missing}",
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
