"""Regime gating for asset selection (currently NoOp stubs).

This module provides a `RegimeGate` class for modifying asset selection based
on macroeconomic conditions. The current implementation is a NoOp (No Operation)
stub, meaning it serves as a placeholder and does not perform any actual
filtering or scoring adjustments. It always returns neutral signals and leaves
the asset selection unchanged, regardless of configuration.

This placeholder design allows the surrounding system to be built with regime
gating in mind, with the expectation that functional logic will be added in
the future without requiring changes to the system's interface.

Key Classes:
- `RegimeGate`: Applies NoOp regime rules to an asset selection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from portfolio_management.assets.selection import SelectedAsset
    from portfolio_management.macro.models import RegimeConfig

LOGGER = logging.getLogger(__name__)


class RegimeGate:
    """Apply regime-based gating to asset selection (currently NoOp).

    This class is designed to apply rules to an asset selection based on
    macroeconomic conditions. However, the current implementation is a NoOp
    stub. It always returns neutral signals and leaves the selection unchanged,
    irrespective of the provided configuration. This ensures that the system
    is ready for future regime logic without affecting current workflows.

    Attributes:
        config (RegimeConfig): A configuration object that defines the rules for
                               regime detection. Currently, this configuration
                               is logged but not used for any logic.

    Example:
        >>> from portfolio_management.macro.models import RegimeConfig
        >>> from portfolio_management.macro.regime import RegimeGate
        >>>
        >>> # Mock asset class for the example
        >>> class MockAsset:
        ...     def __init__(self, symbol):
        ...         self.symbol = symbol
        >>>
        >>> assets = [MockAsset("AAPL"), MockAsset("GOOG")]
        >>> config = RegimeConfig(enable_gating=True)
        >>> gate = RegimeGate(config)
        >>>
        >>> # The apply_gating method returns the original assets without changes.
        >>> filtered_assets = gate.apply_gating(assets)
        >>> assert filtered_assets is assets
    """

    def __init__(self, config: RegimeConfig) -> None:
        """Initialize the RegimeGate.

        Args:
            config: A `RegimeConfig` object that defines the gating rules.
                    This is stored for future use but does not affect the
                    current NoOp behavior.
        """
        self.config = config
        LOGGER.info(
            "Initialized RegimeGate (gating_enabled=%s, mode=NoOp)",
            config.is_enabled(),
        )

    def apply_gating(
        self,
        assets: list[SelectedAsset],
        date: str | None = None,
    ) -> list[SelectedAsset]:
        """Apply regime gating to selected assets (currently a NoOp).

        This method is intended to filter an asset list based on the prevailing
        macroeconomic regime. In its current implementation, it acts as a
        pass-through, returning the original list of assets without any
        modifications.

        Args:
            assets: A list of `SelectedAsset` objects to potentially filter.
            date: An optional date for regime evaluation (e.g., "YYYY-MM-DD").
                  This parameter is currently ignored.

        Returns:
            The original list of assets, unchanged.
        """
        if not self.config.is_enabled():
            LOGGER.debug(
                "Regime gating disabled, passing through %d assets unchanged",
                len(assets),
            )
            return assets

        # Even if enabled, current implementation is NoOp
        LOGGER.debug(
            "Regime gating enabled but NoOp implementation active, "
            "passing through %d assets unchanged",
            len(assets),
        )
        return assets

    def get_current_regime(self, date: str | None = None) -> dict[str, str]:
        """Get the current regime classification (always returns 'neutral').

        This method is designed to return the current market regime. As a NoOp,
        it consistently returns a dictionary indicating a 'neutral' state for
        all regime types.

        Args:
            date: An optional date for which to determine the regime. This
                  parameter is currently ignored.

        Returns:
            A dictionary with predefined neutral regime classifications.

        Example:
            >>> from portfolio_management.macro.models import RegimeConfig
            >>> from portfolio_management.macro.regime import RegimeGate
            >>>
            >>> config = RegimeConfig()
            >>> gate = RegimeGate(config)
            >>> regime = gate.get_current_regime()
            >>> print(regime)
            {'recession': 'neutral', 'risk_sentiment': 'neutral', 'mode': 'noop'}
        """
        # NoOp: always return neutral regime
        regime = {
            "recession": "neutral",
            "risk_sentiment": "neutral",
            "mode": "noop",
        }

        LOGGER.debug(
            "Current regime (NoOp): %s (date=%s)",
            regime,
            date if date else "current",
        )
        return regime

    def filter_by_asset_class(
        self,
        assets: list[SelectedAsset],
        allowed_classes: list[str] | None = None,
    ) -> list[SelectedAsset]:
        """Filter assets by asset class based on regime (currently a NoOp).

        In a future implementation, this method could filter assets by their
        class (e.g., exclude equities during a risk-off regime). Currently,
        it returns the original list of assets without any filtering.

        Args:
            assets: A list of `SelectedAsset` objects to filter.
            allowed_classes: An optional list of asset classes to permit. This
                             parameter is currently ignored.

        Returns:
            The original list of assets, unchanged.
        """
        # NoOp: always pass through unchanged
        LOGGER.debug(
            "Asset class filtering (NoOp): passing through %d assets unchanged",
            len(assets),
        )
        return assets

    def adjust_selection_scores(
        self,
        assets: list[SelectedAsset],
        date: str | None = None,
    ) -> list[tuple[SelectedAsset, float]]:
        """Adjust selection scores based on regime (currently a NoOp).

        This method is intended to adjust asset scores based on regime
        conditions. In its current NoOp implementation, it returns all assets
        with a neutral score of 1.0.

        Args:
            assets: A list of `SelectedAsset` objects.
            date: An optional date for regime evaluation. This parameter is
                  currently ignored.

        Returns:
            A list of tuples, where each tuple contains the original asset and
            a neutral score of 1.0.
        """
        # NoOp: return all assets with neutral score
        scored_assets = [(asset, 1.0) for asset in assets]
        LOGGER.debug(
            "Score adjustment (NoOp): returning %d assets with neutral score 1.0",
            len(scored_assets),
        )
        return scored_assets
