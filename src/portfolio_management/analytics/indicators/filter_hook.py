"""Filter hook for technical indicator-based asset filtering.

This module provides the `FilterHook`, a class that connects the technical
indicator computation with the asset selection pipeline. It uses an indicator
provider to calculate signals for assets and then filters them based on the
latest signal value.

Key Classes:
    - FilterHook: Applies indicator signals to filter a list of assets.

Usage Example:
    >>> import pandas as pd
    >>> from portfolio_management.analytics.indicators.config import IndicatorConfig
    >>> from portfolio_management.analytics.indicators.providers import NoOpIndicatorProvider
    >>> from portfolio_management.analytics.indicators.filter_hook import FilterHook
    >>>
    >>> # Setup a no-op filter (always includes all assets)
    >>> config = IndicatorConfig.noop()
    >>> provider = NoOpIndicatorProvider()
    >>> hook = FilterHook(config, provider)
    >>>
    >>> prices = pd.DataFrame({
    ...     'AAPL': [100, 101, 102],
    ...     'MSFT': [200, 201, 202]
    ... }, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
    >>> initial_assets = ['AAPL', 'MSFT']
    >>>
    >>> filtered_assets = hook.filter_assets(prices, initial_assets)
    >>> print(f"Assets before filtering: {initial_assets}")
    Assets before filtering: ['AAPL', 'MSFT']
    >>> print(f"Assets after filtering: {filtered_assets}")
    Assets after filtering: ['AAPL', 'MSFT']
"""

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

    This class serves as a bridge between a chosen indicator provider and the
    asset selection process. It computes indicator signals for each asset's
    price series and filters the asset list based on the most recent signal value.
    Assets with a 'True' or '1.0' signal are retained, while those with 'False'
    or '0.0' are excluded.

    Attributes:
        config (IndicatorConfig): The configuration object for the indicators.
        provider (IndicatorProvider): The provider instance used to compute signals.

    Example:
        >>> import pandas as pd
        >>> from .config import IndicatorConfig
        >>> from .providers import NoOpIndicatorProvider
        >>>
        >>> # Using a NoOp provider which always returns True
        >>> config = IndicatorConfig(enabled=True, provider='noop')
        >>> provider = NoOpIndicatorProvider()
        >>> hook = FilterHook(config, provider)
        >>>
        >>> prices = pd.DataFrame({'TICKER': [10, 11, 12]})
        >>> assets = ['TICKER']
        >>> result = hook.filter_assets(prices, assets)
        >>> print(result)
        ['TICKER']
    """

    def __init__(self, config: IndicatorConfig, provider: IndicatorProvider):
        """Initialize the FilterHook.

        Args:
            config (IndicatorConfig): Indicator configuration object.
            provider (IndicatorProvider): An indicator provider implementation
                (e.g., `NoOpIndicatorProvider`, `TALibIndicatorProvider`).
        """
        self.config = config
        self.provider = provider
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If the configuration is found to be invalid.
        """
        self.config.validate()

    def filter_assets(
        self,
        prices: pd.DataFrame,
        assets: list[str],
    ) -> list[str]:
        """Filter assets based on technical indicator signals.

        For each asset in the input list, this method computes its technical
        indicator signal using the configured provider. It then includes the asset
        in the output list only if the most recent signal is True (or >= 0.5 for
        floating-point signals).

        Args:
            prices (pd.DataFrame): A DataFrame of price data, with asset symbols
                as columns and dates as the index.
            assets (list[str]): The list of asset symbols to be filtered.

        Returns:
            list[str]: A new list containing only the asset symbols that passed
            the indicator filter. If indicators are disabled in the config, this
            method returns the original list of assets unmodified.
        """
        # If indicators disabled, return all assets
        if not self.config.enabled:
            logger.debug("Technical indicators disabled, returning all assets")
            return assets

        logger.info(
            f"Filtering {len(assets)} assets using {self.config.provider} provider",
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
                    logger.debug(
                        f"Asset {asset} passed filter (signal: {latest_signal})",
                    )
                else:
                    logger.debug(
                        f"Asset {asset} excluded by filter (signal: {latest_signal})",
                    )

            except Exception as e:
                logger.error(
                    f"Error computing indicator for asset {asset}: {e}, excluding",
                )
                continue

        logger.info(
            f"Technical indicator filtering: {len(assets)} -> {len(filtered_assets)} assets",
        )
        return filtered_assets