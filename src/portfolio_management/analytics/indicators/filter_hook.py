"""Filter hook for technical indicator-based asset filtering."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from .config import IndicatorConfig
    from .providers import IndicatorProvider

logger = logging.getLogger(__name__)


class FilterHook:
    """Hook for filtering assets based on technical indicator signals.

    This class provides a filtering mechanism that can be plugged into
    the asset selection pipeline to include/exclude assets based on
    technical indicator signals.

    The hook computes indicator signals for each asset's price series
    and filters assets based on the most recent signal value. Assets
    with True/1.0 signals are included, while False/0.0 signals exclude
    the asset.

    Example:
        >>> from portfolio_management.analytics.indicators import (
        ...     FilterHook, NoOpIndicatorProvider, IndicatorConfig
        ... )
        >>> config = IndicatorConfig.noop()
        >>> provider = NoOpIndicatorProvider()
        >>> hook = FilterHook(config, provider)
        >>> prices = pd.DataFrame({
        ...     'AAPL': [100, 101, 102],
        ...     'MSFT': [200, 201, 202]
        ... }, index=pd.date_range('2020-01-01', periods=3))
        >>> filtered = hook.filter_assets(prices, ['AAPL', 'MSFT'])
        >>> print(filtered)  # ['AAPL', 'MSFT'] - no-op includes all
    """

    def __init__(self, config: IndicatorConfig, provider: IndicatorProvider):
        """Initialize filter hook.

        Args:
            config: Indicator configuration
            provider: Indicator provider implementation
        """
        self.config = config
        self.provider = provider
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        self.config.validate()

    def filter_assets(
        self,
        prices: pd.DataFrame,
        assets: list[str],
    ) -> list[str]:
        """Filter assets based on technical indicator signals.

        For each asset, computes the indicator signal from its price series
        and includes it only if the most recent signal is True (or >= 0.5 for
        float signals).

        Args:
            prices: Price DataFrame with assets as columns, dates as index
            assets: List of asset symbols to filter

        Returns:
            Filtered list of asset symbols that pass indicator filter.
            If indicators are disabled, returns all input assets unchanged.

        Example:
            >>> hook = FilterHook(IndicatorConfig.noop(), NoOpIndicatorProvider())
            >>> prices = pd.DataFrame({
            ...     'AAPL': [100, 101, 102],
            ...     'MSFT': [200, 201, 202]
            ... }, index=pd.date_range('2020-01-01', periods=3))
            >>> filtered = hook.filter_assets(prices, ['AAPL', 'MSFT'])
            >>> print(filtered)  # ['AAPL', 'MSFT']
        """
        # If indicators disabled, return all assets
        if not self.config.enabled:
            logger.debug("Technical indicators disabled, returning all assets")
            return assets

        logger.info(
            f"Filtering {len(assets)} assets using {self.config.provider} provider"
        )

        filtered_assets = []
        for asset in assets:
            if asset not in prices.columns:
                logger.warning(f"Asset {asset} not found in price data, excluding")
                continue

            # Get price series for this asset
            price_series = prices[asset].dropna()

            if len(price_series) == 0:
                logger.warning(f"Asset {asset} has no valid price data, excluding")
                continue

            # Compute indicator signal
            try:
                signal = self.provider.compute(price_series, self.config.params)

                # Get most recent signal value
                latest_signal = signal.iloc[-1] if len(signal) > 0 else False

                # Include asset if signal is True (or >= 0.5 for float values)
                if isinstance(latest_signal, bool):
                    include = latest_signal
                else:
                    include = float(latest_signal) >= 0.5

                if include:
                    filtered_assets.append(asset)
                    logger.debug(f"Asset {asset} passed filter (signal: {latest_signal})")
                else:
                    logger.debug(f"Asset {asset} excluded by filter (signal: {latest_signal})")

            except Exception as e:
                logger.error(
                    f"Error computing indicator for asset {asset}: {e}, excluding"
                )
                continue

        logger.info(
            f"Technical indicator filtering: {len(assets)} -> {len(filtered_assets)} assets"
        )
        return filtered_assets
